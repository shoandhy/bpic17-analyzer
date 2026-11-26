"""Panel Dataset & status (F01): file XES aktif, status impor, jumlah case/event, atribut.

Pemilik: Anggota A (feat/a-loader).
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QListWidget,
    QVBoxLayout,
)

from app.panels.base import BasePanel
from app.theme import INK, LAUNCH_ORANGE, SLATE
from core.loaded_log import LoadedLog


class DatasetPanel(BasePanel):
    """Menampilkan metadata file XES aktif, status impor, dan atribut yang tersedia."""

    title = "Dataset"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._df: Optional[pd.DataFrame] = None
        self._loaded: Optional[LoadedLog] = None

        kicker = QLabel("F01 · DATASET & VALIDASI SKEMA")
        kicker.setStyleSheet(f"color: {LAUNCH_ORANGE}; font-size: 11px; font-weight: 600;")
        heading = QLabel("Dataset & Status Impor")
        heading.setStyleSheet(f"color: {INK}; font-size: 22px; font-weight: 600;")
        subtitle = QLabel(
            "Informasi file XES aktif, rentang waktu UTC, dan atribut yang terdeteksi."
        )
        subtitle.setStyleSheet(f"color: {SLATE}; font-size: 13px;")
        subtitle.setWordWrap(True)

        self.lbl_file = QLabel("Belum ada file XES dimuat")
        self.lbl_file.setWordWrap(True)
        self.lbl_status = QLabel("Menunggu impor file XES (File → Buka XES…)")
        self.lbl_status.setWordWrap(True)
        self.lbl_cases = QLabel("-")
        self.lbl_events = QLabel("-")
        self.lbl_timerange = QLabel("-")
        self.lbl_lifecycle = QLabel("-")
        self.lbl_resource = QLabel("-")

        info_box = QGroupBox("Informasi Dataset Aktif")
        form = QFormLayout(info_box)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setVerticalSpacing(10)
        form.addRow("Nama file:", self.lbl_file)
        form.addRow("Status:", self.lbl_status)
        form.addRow("Jumlah case:", self.lbl_cases)
        form.addRow("Jumlah event:", self.lbl_events)
        form.addRow("Rentang waktu (UTC):", self.lbl_timerange)
        form.addRow("Atribut lifecycle:transition:", self.lbl_lifecycle)
        form.addRow("Atribut org:resource:", self.lbl_resource)

        attr_box = QGroupBox("Atribut Event Tersedia")
        attr_layout = QVBoxLayout(attr_box)
        self.attr_list = QListWidget()
        attr_layout.addWidget(self.attr_list)

        warn_box = QGroupBox("Peringatan Impor")
        warn_layout = QVBoxLayout(warn_box)
        self.lbl_warnings = QLabel("Tidak ada peringatan.")
        self.lbl_warnings.setStyleSheet(f"color: {SLATE};")
        self.lbl_warnings.setWordWrap(True)
        warn_layout.addWidget(self.lbl_warnings)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        layout.addWidget(kicker)
        layout.addWidget(heading)
        layout.addWidget(subtitle)
        layout.addWidget(info_box)
        layout.addWidget(attr_box, 1)
        layout.addWidget(warn_box)

    def set_log(self, df: pd.DataFrame, durations: pd.Series) -> None:
        """Perbarui ringkasan dataset dari DataFrame kanonik yang baru dimuat."""
        self._df = df
        n_cases = int(df["case_id"].nunique()) if len(df) else 0
        n_events = int(len(df))

        self.lbl_cases.setText(f"{n_cases:,}")
        self.lbl_events.setText(f"{n_events:,}")

        if n_events > 0:
            t_min = df["timestamp"].min().isoformat(sep=" ", timespec="seconds")
            t_max = df["timestamp"].max().isoformat(sep=" ", timespec="seconds")
            self.lbl_timerange.setText(f"{t_min}  s/d  {t_max}")
        else:
            self.lbl_timerange.setText("-")

        has_lifecycle = bool(df["lifecycle"].notna().any()) if n_events else False
        if has_lifecycle:
            lc_vals = sorted(df["lifecycle"].dropna().astype(str).unique().tolist())
            self.lbl_lifecycle.setText(f"Tersedia ({', '.join(lc_vals)})")
        else:
            self.lbl_lifecycle.setText("Tidak tersedia / kosong")

        n_res = int(df["resource"].dropna().nunique()) if n_events else 0
        if n_res > 0:
            self.lbl_resource.setText(f"Tersedia ({n_res:,} resource unik)")
        else:
            self.lbl_resource.setText("Tidak tersedia / seluruhnya NA")

        if self._loaded is None:
            self.lbl_file.setText("(Log sintetis / memori)")
            self.lbl_status.setText("Log aktif dimuat")
            self.attr_list.clear()
            self.attr_list.addItems([str(c) for c in df.columns])

    def set_loaded(self, loaded: LoadedLog) -> None:
        """Perbarui nama file, status, daftar atribut asli XES, dan peringatan."""
        self._loaded = loaded
        self.lbl_file.setText(f"{loaded.path.name} ({loaded.path})")
        self.lbl_status.setText("Berhasil dimuat ke skema kanonik")
        self.lbl_cases.setText(f"{loaded.n_cases:,}")
        self.lbl_events.setText(f"{loaded.n_events:,}")

        self.attr_list.clear()
        if loaded.attributes:
            self.attr_list.addItems(loaded.attributes)

        if loaded.warnings:
            self.lbl_warnings.setText("\n".join(f"• {w}" for w in loaded.warnings))
        else:
            self.lbl_warnings.setText("Tidak ada peringatan.")

    def reset(self) -> None:
        """Kosongkan tampilan peringatan/status hasil tanpa menghapus log aktif."""
        if self._df is None:
            self.lbl_file.setText("Belum ada file XES dimuat")
            self.lbl_status.setText("Menunggu impor file XES (File → Buka XES…)")
            self.lbl_cases.setText("-")
            self.lbl_events.setText("-")
            self.lbl_timerange.setText("-")
            self.lbl_lifecycle.setText("-")
            self.lbl_resource.setText("-")
            self.attr_list.clear()
            self.lbl_warnings.setText("Tidak ada peringatan.")
