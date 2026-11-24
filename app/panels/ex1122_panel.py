"""Panel Exercise 11.22 (F06): jumlah, persentase + denominator, pasangan event bukti,
timeline case.

Pemilik: Anggota D (feat/d-1122-fixtures). Memanggil ``analyses.ex_11_22.run`` lewat
app/worker.py.
"""

from __future__ import annotations

import pandas as pd

from app.panels.base import BasePanel


class Ex1122Panel(BasePanel):
    """Pemilik: Anggota D."""

    title = "Exercise 11.22"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        raise NotImplementedError("Anggota D: app.panels.ex1122_panel.Ex1122Panel")

    def set_log(self, df: pd.DataFrame, durations: pd.Series) -> None:
        raise NotImplementedError("Anggota D: Ex1122Panel.set_log")
