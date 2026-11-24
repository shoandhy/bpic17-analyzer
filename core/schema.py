"""Skema DataFrame kanonik — KONTRAK BERSAMA (pemilik: kelompok, dijaga Anggota E).

Perubahan file ini harus disepakati kelompok dulu (lihat AGENTS.md). Penjelasan lengkap
kontrak ada di docstring ``core/loader.py``; file ini hanya berisi konstanta dan
pemeriksa (validator) yang dipakai test semua anggota.
"""

from __future__ import annotations

import pandas as pd

#: Urutan kolom kanonik. Kolom tambahan boleh ada, tetapi tujuh kolom ini wajib.
CANONICAL_COLUMNS: list[str] = [
    "case_id",    # str
    "activity",   # str, dari concept:name
    "timestamp",  # datetime64[*, UTC] (satuan ns/us bebas)
    "lifecycle",  # str lowercase, atau None bila atribut lifecycle:transition tidak ada
    "resource",   # str atau pd.NA (string kosong -> NA)
    "orig_idx",   # int, urutan asli event di file XES (0-based, unik di seluruh log)
    "event_pos",  # int, posisi 0-based event di dalam trace setelah sort kanonik
]

#: Kunci sort kanonik (stabil). Lihat docstring core/loader.py untuk aturan tie-break.
SORT_KEYS: list[str] = ["case_id", "timestamp", "orig_idx"]

#: Nama Series durasi per case (hari, float).
DURATION_NAME = "duration_days"


class SchemaError(ValueError):
    """DataFrame tidak memenuhi kontrak kanonik."""


def check_canonical(df: pd.DataFrame) -> None:
    """Lempar ``SchemaError`` jika ``df`` melanggar kontrak kanonik.

    Dipakai di test (bukan di jalur panas aplikasi). Tidak memeriksa nama aktivitas.
    """
    missing = [c for c in CANONICAL_COLUMNS if c not in df.columns]
    if missing:
        raise SchemaError(f"Kolom wajib tidak ada: {missing}")

    ts = df["timestamp"]
    if not isinstance(ts.dtype, pd.DatetimeTZDtype) or str(ts.dt.tz) != "UTC":
        raise SchemaError(f"timestamp harus datetime tz-aware UTC, didapat {ts.dtype}")

    for col in ("orig_idx", "event_pos"):
        if not pd.api.types.is_integer_dtype(df[col]):
            raise SchemaError(f"{col} harus bertipe integer, didapat {df[col].dtype}")

    if df["orig_idx"].duplicated().any():
        raise SchemaError("orig_idx harus unik di seluruh log")

    if df["case_id"].isna().any() or df["activity"].isna().any():
        raise SchemaError("case_id dan activity tidak boleh kosong")

    res = df["resource"].dropna()
    if (res.astype(str).str.strip() == "").any():
        raise SchemaError("resource string kosong harus diubah menjadi NA")

    lc = df["lifecycle"].dropna()
    if (lc.astype(str) != lc.astype(str).str.lower()).any():
        raise SchemaError("lifecycle harus lowercase")

    expected = df.sort_values(SORT_KEYS, kind="stable")
    if not expected.index.equals(df.index):
        raise SchemaError("Baris belum terurut stabil per (case_id, timestamp, orig_idx)")

    pos = df.groupby("case_id", sort=False).cumcount()
    if not (pos.to_numpy() == df["event_pos"].to_numpy()).all():
        raise SchemaError("event_pos harus 0,1,2,... di dalam setiap case")
