"""Panel Exercise 11.15 & 11.18 (F04, F05): repeated-complete dan same-resource, tabel bukti,
tombol buka case.

Pemilik: Anggota C (feat/c-1115-1118). Memanggil ``analyses.ex_11_15_18.run`` lewat
app/worker.py.
"""

from __future__ import annotations

import pandas as pd

from app.panels.base import BasePanel


class Ex1115_1118Panel(BasePanel):
    """Pemilik: Anggota C."""

    title = "Exercise 11.15 & 11.18"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        raise NotImplementedError("Anggota C: app.panels.ex1115_1118_panel.Ex1115_1118Panel")

    def set_log(self, df: pd.DataFrame, durations: pd.Series) -> None:
        raise NotImplementedError("Anggota C: Ex1115_1118Panel.set_log")
