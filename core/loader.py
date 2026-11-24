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

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

#: Callback progres: (persen 0-100, pesan). Disediakan oleh app/worker.py.
ProgressCallback = Callable[[int, str], None]


class LogValidationError(ValueError):
    """File XES rusak atau atribut wajib (case ID, concept:name, time:timestamp) tidak ada.

    Pesan harus jelas dan berbahasa Indonesia karena ditampilkan apa adanya di dialog error.
    """


@dataclass
class LoadedLog:
    """Hasil impor XES. Pemilik: Anggota A."""

    df: pd.DataFrame                      # DataFrame kanonik (lihat docstring modul)
    path: Path                            # path file XES
    n_cases: int
    n_events: int
    attributes: list[str] = field(default_factory=list)  # atribut event yang tersedia
    has_lifecycle: bool = False
    has_resource: bool = False
    warnings: list[str] = field(default_factory=list)    # peringatan non-fatal


def load_xes(path: str | Path, progress: Optional[ProgressCallback] = None) -> LoadedLog:
    """Impor file XES dengan PM4Py lalu ubah ke DataFrame kanonik.

    Pemilik: Anggota A. Dipanggil lewat app/worker.py (bukan di thread UI).
    Raise ``LogValidationError`` untuk file rusak / atribut wajib hilang.
    """
    raise NotImplementedError("Anggota A: core.loader.load_xes")


def to_canonical(raw: pd.DataFrame) -> pd.DataFrame:
    """Ubah DataFrame hasil ``pm4py.read_xes`` / ``convert_to_dataframe`` ke bentuk kanonik.

    Pemilik: Anggota A. Fungsi murni (tanpa I/O) agar mudah diuji dengan log sintetis.
    Harus lolos ``core.schema.check_canonical``.
    """
    raise NotImplementedError("Anggota A: core.loader.to_canonical")
