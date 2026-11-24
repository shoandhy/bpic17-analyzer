"""Panel Dataset & status (F01): file XES aktif, status impor, jumlah case/event, atribut.

Pemilik: Anggota A (feat/a-loader).
"""

from __future__ import annotations

import pandas as pd

from app.panels.base import BasePanel


class DatasetPanel(BasePanel):
    """Pemilik: Anggota A."""

    title = "Dataset"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        raise NotImplementedError("Anggota A: app.panels.dataset_panel.DatasetPanel")

    def set_log(self, df: pd.DataFrame, durations: pd.Series) -> None:
        raise NotImplementedError("Anggota A: DatasetPanel.set_log")
