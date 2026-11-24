"""Kontrak panel GUI — KONTRAK BERSAMA v2 (ubah hanya lewat kesepakatan kelompok).

Setiap panel:
    * adalah QWidget (subclass ``BasePanel``);
    * memancarkan ``open_case_for(case_id, code)`` untuk membuka Case Explorer dengan bukti
      hasil ``code`` (mis. "11.7E") disorot — DIUTAMAKAN sejak v2;
    * boleh memancarkan ``open_case(case_id)`` (v1, tetap didukung) bila kode hasil tidak
      relevan; Case Explorer lalu memilih hasil panel itu yang paling spesifik;
    * memancarkan ``results_ready(object)`` berisi ``list[AnalysisResult]`` setiap kali
      analisisnya selesai dijalankan (dipakai Case Explorer dan ekspor CSV);
    * menerima log lewat ``set_log(df, durations)`` (dipanggil MainWindow setelah impor);
    * OPSIONAL menerima metadata file lewat ``set_loaded(loaded)`` (``core.loaded_log.LoadedLog``;
      dipanggil MainWindow setelah ``set_log``; default tidak melakukan apa pun);
    * mengosongkan tampilan hasil lewat ``reset()``;
    * menjalankan komputasi berat lewat ``app.worker.run_in_background`` (bukan di thread UI).
"""

from __future__ import annotations

import pandas as pd
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from core.loaded_log import LoadedLog


class BasePanel(QWidget):
    """Kelas dasar semua panel. Subclass WAJIB meng-override ``set_log``."""

    #: case_id — buka case tanpa menyebut hasil (v1).
    open_case = Signal(str)
    #: (case_id, code) — buka case dan sorot bukti hasil ``code`` (v2).
    open_case_for = Signal(str, str)
    #: list[AnalysisResult] — hasil analisis panel ini.
    results_ready = Signal(object)

    #: Judul untuk sidebar/tab.
    title: str = ""

    def set_log(self, df: pd.DataFrame, durations: pd.Series) -> None:
        """Terima DataFrame kanonik dan durasi per case dari MainWindow."""
        raise NotImplementedError(f"{type(self).__name__}.set_log")

    def set_loaded(self, loaded: LoadedLog) -> None:
        """Terima metadata file XES aktif. Opsional; default tidak melakukan apa pun."""

    def reset(self) -> None:
        """Kosongkan hasil yang ditampilkan (log tetap dimuat). Default: tidak melakukan apa pun."""
