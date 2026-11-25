"""Panel Overview (F02): total case/event, frekuensi aktivitas, rentang waktu, mean cycle
time, tabel durasi per case yang bisa dicari.

Pemilik: Anggota A (feat/a-loader).
"""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd
from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.panels.base import BasePanel
from app.panels.case_explorer import DataFrameModel
from core.durations import compute_overview


class OverviewPanel(BasePanel):
    """Menampilkan metrik ringkasan log, frekuensi aktivitas, dan tabel durasi per case."""

    title = "Overview"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._overview: Optional[dict[str, Any]] = None
        self._case_table: pd.DataFrame = pd.DataFrame(
            columns=["case_id", "n_events", "duration_days"]
        )

        # --- Metrik ringkasan ---
        metrics_box = QGroupBox("Ringkasan Event Log")
        metrics_row = QHBoxLayout(metrics_box)
        self.lbl_cases = QLabel("Total Case: -")
        self.lbl_events = QLabel("Total Event: -")
        self.lbl_range = QLabel("Rentang Waktu: -")
        self.lbl_mean_cycle = QLabel("Mean Cycle Time: -")
        for lbl in (self.lbl_cases, self.lbl_events, self.lbl_range, self.lbl_mean_cycle):
            lbl.setWordWrap(True)
            metrics_row.addWidget(lbl, 1)

        # --- Kiri: Frekuensi Aktivitas ---
        act_widget = QWidget()
        act_layout = QVBoxLayout(act_widget)
        act_header = QHBoxLayout()
        act_header.addWidget(QLabel("<b>Frekuensi Aktivitas</b>"))
        self.chk_lifecycle = QCheckBox("Sertakan lifecycle")
        self.chk_lifecycle.toggled.connect(self._refresh_activity_table)
        act_header.addStretch(1)
        act_header.addWidget(self.chk_lifecycle)

        self.act_model = DataFrameModel(
            headers={
                "activity": "Aktivitas",
                "lifecycle": "Lifecycle",
                "count": "Jumlah Event",
                "percentage": "Persentase (%)",
            }
        )
        self.act_view = QTableView()
        self.act_view.setModel(self.act_model)
        self.act_view.setSortingEnabled(True)
        self.act_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.act_view.verticalHeader().setVisible(False)
        self.act_view.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.act_view.horizontalHeader().setStretchLastSection(True)

        act_layout.addLayout(act_header)
        act_layout.addWidget(self.act_view, 1)

        # --- Kanan: Tabel Durasi per Case (bisa dicari) ---
        case_widget = QWidget()
        case_layout = QVBoxLayout(case_widget)
        case_header = QHBoxLayout()
        case_header.addWidget(QLabel("<b>Durasi per Case (hari)</b>"))
        self.search_case = QLineEdit()
        self.search_case.setPlaceholderText("Cari Case ID…")
        self.search_case.setClearButtonEnabled(True)
        self.search_case.textChanged.connect(self._filter_cases)
        case_header.addWidget(self.search_case, 1)

        self.case_model = DataFrameModel(
            headers={
                "case_id": "Case ID",
                "n_events": "Jumlah Event",
                "duration_days": "Durasi (hari)",
            }
        )
        self.case_view = QTableView()
        self.case_view.setModel(self.case_model)
        self.case_view.setSortingEnabled(True)
        self.case_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.case_view.verticalHeader().setVisible(False)
        self.case_view.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.case_view.horizontalHeader().setStretchLastSection(True)
        self.case_view.doubleClicked.connect(self._on_case_double_clicked)

        hint = QLabel("Klik dua kali baris case untuk membuka rinciannya di Case Explorer.")
        hint.setStyleSheet("color: gray;")

        case_layout.addLayout(case_header)
        case_layout.addWidget(self.case_view, 1)
        case_layout.addWidget(hint)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(act_widget)
        splitter.addWidget(case_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h3>Overview Event Log (F02)</h3>"))
        layout.addWidget(metrics_box)
        layout.addWidget(splitter, 1)

    def set_log(self, df: pd.DataFrame, durations: pd.Series) -> None:
        """Hitung dan tampilkan ringkasan overview dari DataFrame kanonik & durasi."""
        ov = compute_overview(df, durations)
        self._overview = ov
        self._case_table = ov["case_table"]

        self.lbl_cases.setText(f"Total Case:\n<b>{ov['total_cases']:,}</b>")
        self.lbl_events.setText(f"Total Event:\n<b>{ov['total_events']:,}</b>")

        if ov["min_timestamp"] is not None and ov["max_timestamp"] is not None:
            t0 = ov["min_timestamp"].isoformat(sep=" ", timespec="seconds")
            t1 = ov["max_timestamp"].isoformat(sep=" ", timespec="seconds")
            self.lbl_range.setText(f"Rentang Waktu (UTC):\n<b>{t0}</b> s/d <b>{t1}</b>")
        else:
            self.lbl_range.setText("Rentang Waktu:\n-")

        if ov["mean_cycle_days"] is not None:
            self.lbl_mean_cycle.setText(
                f"Mean Cycle Time:\n<b>{ov['mean_cycle_days']:.3f} hari</b>"
            )
        else:
            self.lbl_mean_cycle.setText("Mean Cycle Time:\n-")

        self._refresh_activity_table()
        self._filter_cases(self.search_case.text())

    def _refresh_activity_table(self) -> None:
        if self._overview is None:
            self.act_model.set_frame(pd.DataFrame())
            return
        if self.chk_lifecycle.isChecked():
            self.act_model.set_frame(self._overview["activity_lifecycle_freq"])
        else:
            self.act_model.set_frame(self._overview["activity_freq"])

    def _filter_cases(self, text: str) -> None:
        df = self._case_table
        query = text.strip()
        if query and not df.empty:
            mask = df["case_id"].astype(str).str.contains(query, case=False, regex=False)
            df = df.loc[mask]
        self.case_model.set_frame(df)

    def _on_case_double_clicked(self, index: QModelIndex) -> None:
        if not index.isValid():
            return
        case_id = self.case_model.raw(index.row(), 0)
        if case_id is not None:
            self.open_case.emit(str(case_id))

    def reset(self) -> None:
        """Bersihkan pencarian tabel case (data overview tetap mengikuti log aktif)."""
        self.search_case.clear()
