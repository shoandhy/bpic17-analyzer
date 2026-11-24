"""Panel Exercise 11.7 A–E (F03): lima hasil + aturan filter, daftar case ID, tombol buka case.

Pemilik: Anggota B (feat/b-117). Memanggil ``analyses.ex_11_7.run`` lewat app/worker.py.
"""

from __future__ import annotations

import pandas as pd

from app.panels.base import BasePanel


class Ex117Panel(BasePanel):
    """Pemilik: Anggota B."""

    title = "Exercise 11.7"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        raise NotImplementedError("Anggota B: app.panels.ex117_panel.Ex117Panel")

    def set_log(self, df: pd.DataFrame, durations: pd.Series) -> None:
        raise NotImplementedError("Anggota B: Ex117Panel.set_log")
