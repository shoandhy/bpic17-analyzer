"""Dialog About: versi Python, PM4Py, pandas, PySide6 (Instruksi 7.1, reproduktibilitas).

Pemilik: Anggota A (feat/a-loader).
"""

from __future__ import annotations

import platform

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QLabel,
    QVBoxLayout,
)

from app.theme import INK, SLATE


def _get_versions() -> dict[str, str]:
    import numpy as np
    import pandas as pd
    import pm4py
    import PySide6

    return {
        "Python": platform.python_version(),
        "PM4Py": getattr(pm4py, "__version__", "tidak diketahui"),
        "pandas": getattr(pd, "__version__", "tidak diketahui"),
        "numpy": getattr(np, "__version__", "tidak diketahui"),
        "PySide6": getattr(PySide6, "__version__", "tidak diketahui"),
    }


class AboutDialog(QDialog):
    """Menampilkan informasi aplikasi dan versi pustaka utama untuk reproduktibilitas."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Tentang Aplikasi — BPIC17 Event Log Analyzer")
        self.setMinimumWidth(420)

        versions = _get_versions()

        title = QLabel("BPIC17 Event Log Analyzer")
        title.setStyleSheet(f"color: {INK}; font-size: 20px; font-weight: 600;")
        desc = QLabel(
            "Aplikasi desktop analisis event log BPIC 2017 berbasis Python, PM4Py, "
            "pandas, dan PySide6."
        )
        desc.setStyleSheet(f"color: {SLATE}; font-size: 13px;")
        desc.setWordWrap(True)

        card = QFrame()
        card.setProperty("card", True)
        form = QFormLayout(card)
        form.setContentsMargins(20, 16, 20, 16)
        form.setVerticalSpacing(8)
        for name, ver in versions.items():
            form.addRow(f"{name}:", QLabel(ver))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(desc)
        layout.addWidget(card)
        layout.addWidget(buttons)
