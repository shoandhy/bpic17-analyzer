"""Fitur opsional: fast cases (< ambang hari) vs slow cases (>= ambang hari).

Pemilik: Anggota D (feat/d-1122-fixtures). Mengacu Example 11.10 (ambang default 45 hari).

Hasil ``run`` (list berisi 2 AnalysisResult): "OPT.fast" dan "OPT.slow".
Fitur ini tidak menggantikan soal wajib dan hanya dikerjakan setelah 11.22 selesai.
"""

from __future__ import annotations

import pandas as pd

from core.result import AnalysisResult

DEFAULT_PARAMS: dict[str, float] = {"threshold_days": 45.0}


def run(df: pd.DataFrame, durations: pd.Series, **params) -> list[AnalysisResult]:
    """Bagi case menjadi fast/slow berdasarkan durasi. Pemilik: Anggota D."""
    raise NotImplementedError("Anggota D: analyses.optional.run")
