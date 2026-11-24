"""Durasi (cycle time) per case.

Pemilik: Anggota A (feat/a-loader). Dipakai F02 dan semua analisis.

Kontrak:
    * Input: DataFrame kanonik UTUH (seluruh event, belum difilter).
    * Output: ``pd.Series`` float, index = case_id (unik, semua case di log),
      name = ``core.schema.DURATION_NAME`` ("duration_days").
    * Nilai = (timestamp maksimum - timestamp minimum) case, dalam HARI
      (``total_seconds() / 86400``). Case dengan satu event -> 0.0.
    * Analisis WAJIB memakai Series ini untuk mean cycle time, bukan menghitung ulang
      dari event hasil filter (filter level-event dapat memperpendek durasi secara keliru).
"""

from __future__ import annotations

import pandas as pd


def compute_case_durations(df: pd.DataFrame) -> pd.Series:
    """Hitung durasi tiap case dalam hari dari seluruh event case. Pemilik: Anggota A."""
    raise NotImplementedError("Anggota A: core.durations.compute_case_durations")
