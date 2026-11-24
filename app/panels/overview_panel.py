"""Panel Overview (F02): total case/event, frekuensi aktivitas, rentang waktu, mean cycle
time, tabel durasi per case yang bisa dicari.

Pemilik: Anggota A (feat/a-loader).
"""

from __future__ import annotations

import pandas as pd

from app.panels.base import BasePanel


class OverviewPanel(BasePanel):
    """Pemilik: Anggota A."""

    title = "Overview"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        raise NotImplementedError("Anggota A: app.panels.overview_panel.OverviewPanel")

    def set_log(self, df: pd.DataFrame, durations: pd.Series) -> None:
        raise NotImplementedError("Anggota A: OverviewPanel.set_log")
