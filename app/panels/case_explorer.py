"""Case Explorer (F07): tabel case (semua atau hasil analisis terakhir), pencarian ID,
rincian event (event_pos, timestamp, activity, lifecycle, resource) dengan highlight baris
yang ada di ``AnalysisResult.evidence`` (dicocokkan lewat ``orig_idx``).

Pemilik: Anggota E (feat/e-shell-explorer).
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from app.panels.base import BasePanel
from core.result import AnalysisResult


class CaseExplorer(BasePanel):
    """Pemilik: Anggota E."""

    title = "Case Explorer"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        raise NotImplementedError("Anggota E: app.panels.case_explorer.CaseExplorer")

    def set_log(self, df: pd.DataFrame, durations: pd.Series) -> None:
        raise NotImplementedError("Anggota E: CaseExplorer.set_log")

    def set_results(self, results: list[AnalysisResult]) -> None:
        """Simpan hasil analisis terakhir (untuk filter daftar case & highlight evidence)."""
        raise NotImplementedError("Anggota E: CaseExplorer.set_results")

    def show_case(self, case_id: str, result: Optional[AnalysisResult] = None) -> None:
        """Slot untuk sinyal ``open_case`` dari semua panel."""
        raise NotImplementedError("Anggota E: CaseExplorer.show_case")
