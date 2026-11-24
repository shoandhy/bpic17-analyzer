"""Dialog About: versi Python, PM4Py, pandas, PySide6 (Instruksi 7.1, reproduktibilitas).

Pemilik: Anggota A (feat/a-loader).
"""

from __future__ import annotations

from PySide6.QtWidgets import QDialog


class AboutDialog(QDialog):
    """Pemilik: Anggota A."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        raise NotImplementedError("Anggota A: app.panels.about_dialog.AboutDialog")
