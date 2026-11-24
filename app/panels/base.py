"""Kontrak panel GUI — KONTRAK BERSAMA (ubah hanya lewat kesepakatan kelompok).

Setiap panel:
    * adalah QWidget (subclass ``BasePanel``);
    * memancarkan ``open_case(str)`` dengan case_id untuk membuka Case Explorer;
    * memancarkan ``results_ready(object)`` berisi ``list[AnalysisResult]`` setiap kali
      analisisnya selesai dijalankan (dipakai Case Explorer dan ekspor CSV);
    * menerima log lewat ``set_log(df, durations)`` (dipanggil MainWindow setelah impor);
    * mengosongkan tampilan hasil lewat ``reset()``;
    * menjalankan komputasi berat lewat ``app.worker.run_in_background`` (bukan di thread UI).
"""

from __future__ import annotations

import pandas as pd
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget


class BasePanel(QWidget):
    """Kelas dasar semua panel. Subclass WAJIB meng-override ``set_log``."""

    open_case = Signal(str)
    results_ready = Signal(object)

    #: Judul untuk sidebar/tab.
    title: str = ""

    def set_log(self, df: pd.DataFrame, durations: pd.Series) -> None:
        """Terima DataFrame kanonik dan durasi per case dari MainWindow."""
        raise NotImplementedError(f"{type(self).__name__}.set_log")

    def reset(self) -> None:
        """Kosongkan hasil yang ditampilkan (log tetap dimuat). Default: tidak melakukan apa pun."""
