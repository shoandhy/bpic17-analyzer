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
    QFrame,
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
from app.theme import INK, LAUNCH_ORANGE, SLATE
from core.durations import compute_overview


def _metric_card(label: QLabel) -> QFrame:
    card = QFrame()
    card.setProperty("card", True)
    lay = QVBoxLayout(card)
    lay.setContentsMargins(14, 12, 14, 12)
    label.setWordWrap(True)
    lay.addWidget(label)
    return card


class OverviewPanel(BasePanel):
    """Menampilkan metrik ringkasan log, frekuensi aktivitas, dan tabel durasi per case."""

    title = "Overview"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._overview: Optional[dict[str, Any]] = None
        self._case_table: pd.DataFrame = pd.DataFrame(
            columns=["case_id", "n_events", "duration_days"]
        )

        kicker = QLabel("F02 · RINGKASAN EVENT LOG")
        kicker.setStyleSheet(f"color: {LAUNCH_ORANGE}; font-size: 11px; font-weight: 600;")
        heading = QLabel("Overview Event Log")
        heading.setStyleSheet(f"color: {INK}; font-size: 22px; font-weight: 600;")

        # --- Metrik ringkasan (kartu putih datar di atas Studio Mist) ---
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(12)
        self.lbl_cases = QLabel("Total Case\n-")
        self.lbl_events = QLabel("Total Event\n-")
        self.lbl_range = QLabel("Rentang Waktu (UTC)\n-")
        self.lbl_mean_cycle = QLabel("Mean Cycle Time\n-")
        for lbl in (self.lbl_cases, self.lbl_events, self.lbl_range, self.lbl_mean_cycle):
            metrics_row.addWidget(_metric_card(lbl), 1)

        # --- Kiri: Frekuensi Aktivitas ---
        act_widget = QFrame()
        act_widget.setProperty("card", True)
        act_layout = QVBoxLayout(act_widget)
        act_layout.setContentsMargins(14, 12, 14, 12)
        act_layout.setSpacing(8)
        act_header = QHBoxLayout()
        act_title = QLabel("Frekuensi Aktivitas")
        act_title.setStyleSheet(f"color: {INK}; font-size: 15px; font-weight: 600;")
        act_header.addWidget(act_title)
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
        self.act_view.setAlternatingRowColors(True)
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
        case_widget = QFrame()
        case_widget.setProperty("card", True)
        case_layout = QVBoxLayout(case_widget)
        case_layout.setContentsMargins(14, 12, 14, 12)
        case_layout.setSpacing(8)
        case_header = QHBoxLayout()
        case_title = QLabel("Durasi per Case (hari)")
        case_title.setStyleSheet(f"color: {INK}; font-size: 15px; font-weight: 600;")
        case_header.addWidget(case_title)
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
        self.case_view.setAlternatingRowColors(True)
        self.case_view.setSortingEnabled(True)
        self.case_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.case_view.verticalHeader().setVisible(False)
        self.case_view.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.case_view.horizontalHeader().setStretchLastSection(True)
        self.case_view.doubleClicked.connect(self._on_case_double_clicked)

        hint = QLabel("Klik dua kali baris case untuk membuka rinciannya di Case Explorer.")
        hint.setStyleSheet(f"color: {SLATE}; font-size: 12px;")

        case_layout.addLayout(case_header)
        case_layout.addWidget(self.case_view, 1)
        case_layout.addWidget(hint)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(12)
        splitter.addWidget(act_widget)
        splitter.addWidget(case_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        layout.addWidget(kicker)
        layout.addWidget(heading)
        layout.addLayout(metrics_row)
        layout.addWidget(splitter, 1)

    def set_log(self, df: pd.DataFrame, durations: pd.Series) -> None:
        """Hitung dan tampilkan ringkasan overview dari DataFrame kanonik & durasi."""
        ov = compute_overview(df, durations)
        self._overview = ov
        self._case_table = ov["case_table"]

        self.lbl_cases.setText(
            f"<span style='color:{SLATE};font-size:12px;'>Total Case</span><br>"
            f"<span style='font-size:20px;font-weight:600;'>{ov['total_cases']:,}</span>"
        )
        self.lbl_events.setText(
            f"<span style='color:{SLATE};font-size:12px;'>Total Event</span><br>"
            f"<span style='font-size:20px;font-weight:600;'>{ov['total_events']:,}</span>"
        )

        if ov["min_timestamp"] is not None and ov["max_timestamp"] is not None:
            t0 = ov["min_timestamp"].isoformat(sep=" ", timespec="seconds")
            t1 = ov["max_timestamp"].isoformat(sep=" ", timespec="seconds")
            self.lbl_range.setText(
                f"<span style='color:{SLATE};font-size:12px;'>Rentang Waktu (UTC)</span><br>"
                f"<span style='font-size:13px;font-weight:600;'>{t0}<br>s/d {t1}</span>"
            )
        else:
            self.lbl_range.setText("Rentang Waktu:\n-")

        if ov["mean_cycle_days"] is not None:
            self.lbl_mean_cycle.setText(
                f"<span style='color:{SLATE};font-size:12px;'>Mean Cycle Time</span><br>"
                f"<span style='font-size:20px;font-weight:600;'>{ov['mean_cycle_days']:.3f} hari</span>"
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
