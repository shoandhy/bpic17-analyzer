"""Pemuatan XES BPIC17 -> DataFrame kanonik.

Pemilik: Anggota A (feat/a-loader). Fitur F01.

=====================================================================
KONTRAK DATAFRAME KANONIK (berlaku untuk SEMUA modul; ubah hanya lewat
kesepakatan kelompok — konstanta & validator ada di ``core/schema.py``)
=====================================================================

Satu baris = satu event. Kolom wajib:

============  =========================  ===========================================
kolom         tipe                       asal / aturan
============  =========================  ===========================================
case_id       str                        ``case:concept:name`` dari PM4Py
activity      str                        ``concept:name`` (ejaan asli dari file)
timestamp     datetime64[*, UTC]         ``time:timestamp``, dikonversi ke UTC (satuan
                                         bebas; pandas 3 + pm4py menghasilkan ``us``)
lifecycle     str lowercase / None       ``lifecycle:transition``; seluruh kolom None
                                         jika atribut tidak ada di log
resource      str / pd.NA                ``org:resource``; string kosong atau hanya
                                         spasi -> pd.NA (BUKAN "", BUKAN "nan")
orig_idx      int                        urutan asli event di file (0-based, unik,
                                         ditetapkan SEBELUM sort apa pun)
event_pos     int                        posisi 0-based event di dalam trace SETELAH
                                         sort kanonik
============  =========================  ===========================================

Urutan baris (tie-break):
    ``df.sort_values(["case_id", "timestamp", "orig_idx"], kind="stable")``.
    Event dalam satu case diurutkan menurut timestamp; jika dua event memiliki timestamp
    yang SAMA, event yang muncul lebih dulu di file (``orig_idx`` lebih kecil) dianggap
    lebih dulu. Dengan begitu urutan konsisten dengan representasi event log dan hasil
    selalu sama setiap kali file diimpor ulang. ``event_pos`` dihitung setelah sort ini,
    sehingga "event terakhir" = baris dengan ``event_pos`` maksimum, dan "i < j" pada
    eventually-follows = perbandingan ``event_pos``.

Aturan tambahan:
    * Index DataFrame: RangeIndex 0..n-1 setelah sort (``reset_index(drop=True)``).
    * Jangan membuang event apa pun saat memuat; filter dilakukan oleh analisis.
    * Jangan mengganti/menormalkan ejaan nama aktivitas; analisis yang harus mencocokkan
      ejaan asli.

TODO(A): periksa ejaan asli nama aktivitas dan nilai lifecycle di BPIC17 (mis.
"W_Assess potential fraud" vs "W_Assess Potential Fraud"; "complete" vs "COMPLETE")
lalu bagikan daftarnya ke kelompok.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import numpy as np
import pandas as pd

from core.loaded_log import LoadedLog  # noqa: F401  (diekspor ulang; kontrak v2)
from core.schema import CANONICAL_COLUMNS, SORT_KEYS

#: Callback progres: (persen 0-100, pesan). Disediakan oleh app/worker.py.
ProgressCallback = Callable[[int, str], None]

REQUIRED_RAW_COLUMNS: tuple[str, ...] = (
    "case:concept:name",
    "concept:name",
    "time:timestamp",
)


class LogValidationError(ValueError):
    """File XES rusak atau atribut wajib (case ID, concept:name, time:timestamp) tidak ada.

    Pesan harus jelas dan berbahasa Indonesia karena ditampilkan apa adanya di dialog error.
    """


def _emit_progress(progress: Optional[ProgressCallback], percent: int, message: str) -> None:
    if progress is not None:
        progress(percent, message)


def validate(df_raw: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Validasi DataFrame mentah hasil PM4Py sebelum dipetakan ke skema kanonik.

    Mengembalikan ``(errors, warnings)`` dengan pesan ramah pengguna berbahasa Indonesia:
    - ``errors``: atribut wajib hilang (``case:concept:name``, ``concept:name``,
      ``time:timestamp``), log kosong, atau nilai wajib null/tidak valid.
    - ``warnings``: atribut opsional tidak tersedia (``lifecycle:transition``,
      ``org:resource``) atau seluruh resource kosong.
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(df_raw, pd.DataFrame):
        return (["Format data hasil pembacaan XES tidak valid (bukan tabel DataFrame)."], [])

    missing = [col for col in REQUIRED_RAW_COLUMNS if col not in df_raw.columns]
    if missing:
        errors.append(
            "Atribut wajib tidak ditemukan di file XES: " + ", ".join(missing) + "."
        )
        return errors, warnings

    if len(df_raw) == 0:
        errors.append("Event log kosong: tidak ada satu pun event di dalam file.")
        return errors, warnings

    if df_raw["case:concept:name"].isna().any():
        n_na = int(df_raw["case:concept:name"].isna().sum())
        errors.append(f"Terdapat {n_na} event tanpa Case ID (case:concept:name kosong).")

    if df_raw["concept:name"].isna().any():
        n_na = int(df_raw["concept:name"].isna().sum())
        errors.append(f"Terdapat {n_na} event tanpa nama aktivitas (concept:name kosong).")

    if df_raw["time:timestamp"].isna().any():
        n_na = int(df_raw["time:timestamp"].isna().sum())
        errors.append(f"Terdapat {n_na} event tanpa timestamp (time:timestamp kosong).")
    else:
        try:
            pd.to_datetime(df_raw["time:timestamp"], utc=True, errors="raise")
        except Exception as exc:
            errors.append(f"Format time:timestamp tidak dapat dikonversi ke UTC: {exc}")

    if "lifecycle:transition" not in df_raw.columns:
        warnings.append(
            "Atribut opsional 'lifecycle:transition' tidak ada; kolom lifecycle diisi None."
        )
    if "org:resource" not in df_raw.columns:
        warnings.append(
            "Atribut opsional 'org:resource' tidak ada; kolom resource diisi NA."
        )
    elif df_raw["org:resource"].dropna().astype(str).str.strip().eq("").all():
        warnings.append("Seluruh nilai atribut 'org:resource' kosong.")

    return errors, warnings


def to_canonical(raw: pd.DataFrame) -> pd.DataFrame:
    """Ubah DataFrame hasil ``pm4py.read_xes`` / ``convert_to_dataframe`` ke bentuk kanonik.

    Pemilik: Anggota A. Fungsi murni (tanpa I/O) agar mudah diuji dengan log sintetis.
    Harus lolos ``core.schema.check_canonical``.
    """
    errors, _warnings = validate(raw)
    if errors:
        raise LogValidationError("\n".join(errors))

    n_rows = len(raw)
    orig_idx = np.arange(n_rows, dtype="int64")

    case_id = raw["case:concept:name"].astype(str)
    activity = raw["concept:name"].astype(str)
    timestamp = pd.to_datetime(raw["time:timestamp"], utc=True, errors="raise")

    if "lifecycle:transition" in raw.columns:
        lc_raw = raw["lifecycle:transition"]
        lc_str = lc_raw.astype("string").str.lower()
        lifecycle = pd.Series(
            np.where(lc_str.isna(), None, lc_str.astype(object)),
            dtype="object",
        )
    else:
        lifecycle = pd.Series([None] * n_rows, dtype="object")

    if "org:resource" in raw.columns:
        res_raw = raw["org:resource"].astype("string")
        resource = res_raw.mask(res_raw.str.strip() == "", pd.NA)
    else:
        resource = pd.Series(pd.NA, index=range(n_rows), dtype="string")

    df = pd.DataFrame(
        {
            "case_id": case_id.to_numpy(),
            "activity": activity.to_numpy(),
            "timestamp": timestamp.to_numpy(),
            "lifecycle": lifecycle.to_numpy(),
            "resource": resource.to_numpy(),
            "orig_idx": orig_idx,
        }
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["resource"] = df["resource"].astype("string")

    df = df.sort_values(SORT_KEYS, kind="stable").reset_index(drop=True)
    df["event_pos"] = df.groupby("case_id", sort=False).cumcount().astype("int64")

    return df[CANONICAL_COLUMNS]


def load_xes(
    path: str | Path, progress: Optional[ProgressCallback] = None
) -> tuple[pd.DataFrame, LoadedLog]:
    """Impor file XES dengan PM4Py lalu ubah ke DataFrame kanonik.

    Pemilik: Anggota A. Dipanggil lewat app/worker.py (bukan di thread UI).

    Mengembalikan ``(df, loaded)``: ``df`` = DataFrame kanonik (lihat docstring modul),
    ``loaded`` = ``core.loaded_log.LoadedLog`` (path, n_cases, n_events, attributes,
    warnings) yang diteruskan MainWindow ke ``BasePanel.set_loaded``.
    Raise ``LogValidationError`` untuk file rusak / atribut wajib hilang.
    """
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise LogValidationError(f"File XES tidak ditemukan: {p}")

    _emit_progress(progress, 10, f"Membaca {p.name} dengan PM4Py…")
    try:
        import pm4py

        raw = pm4py.read_xes(str(p))
        if not isinstance(raw, pd.DataFrame):
            raw = pm4py.convert_to_dataframe(raw)
    except LogValidationError:
        raise
    except Exception as exc:
        raise LogValidationError(
            f"File XES '{p.name}' rusak atau tidak dapat dibaca oleh PM4Py: {exc}"
        ) from exc

    _emit_progress(progress, 60, "Memvalidasi dan memetakan ke skema kanonik…")
    errors, warnings = validate(raw)
    if errors:
        raise LogValidationError("\n".join(errors))

    attributes = [str(col) for col in raw.columns]
    df = to_canonical(raw)

    _emit_progress(progress, 90, "Menyusun metadata log…")
    loaded = LoadedLog(
        path=p,
        n_cases=int(df["case_id"].nunique()),
        n_events=int(len(df)),
        attributes=attributes,
        warnings=warnings,
    )
    return df, loaded
