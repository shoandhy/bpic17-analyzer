"""Panel Exercise 11.7 A–E (F03): lima hasil + aturan filter, daftar case ID, tombol buka case.

Pemilik: Anggota B (feat/b-117). Memanggil ``analyses.ex_11_7.run`` lewat app/worker.py.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from analyses import ex_11_7
from app.panels.base import BasePanel
from app.panels.case_explorer import DataFrameModel
from app.worker import run_in_background
from core.result import AnalysisResult


class _ResultCard(QFrame):
    """Kartu ringkasan satu sub-soal 11.7 (klik untuk memilih daftar case-nya)."""

    def __init__(self, code: str, title: str, on_select, parent=None) -> None:
        super().__init__(parent)
        self.code = code
        self._on_select = on_select
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.lbl_code = QLabel(f"<b>{code}</b> — {title}")
        self.lbl_code.setWordWrap(True)
        self.lbl_value = QLabel("—")
        self.lbl_value.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.lbl_cycle = QLabel("Rata-rata cycle time: —")
        self.lbl_rule = QLabel("")
        self.lbl_rule.setWordWrap(True)
        self.lbl_rule.setStyleSheet("color: palette(mid); font-size: 11px;")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.addWidget(self.lbl_code)
        lay.addWidget(self.lbl_value)
        lay.addWidget(self.lbl_cycle)
        lay.addWidget(self.lbl_rule, 1)

    def set_result(self, result: Optional[AnalysisResult]) -> None:
        if result is None:
            self.lbl_value.setText("—")
            self.lbl_cycle.setText("Rata-rata cycle time: —")
            self.lbl_rule.setText("")
            return
        if result.code == "11.7B":
            val = (
                f"{result.mean_cycle_days:.3f} hari"
                if result.mean_cycle_days is not None
                else "—"
            )
            self.lbl_value.setText(val)
            self.lbl_cycle.setText(f"Dari {result.n_cases} case")
        else:
            self.lbl_value.setText(f"{result.n_cases} case")
            cyc = (
                f"{result.mean_cycle_days:.3f} hari"
                if result.mean_cycle_days is not None
                else "—"
            )
            self.lbl_cycle.setText(f"Rata-rata cycle time: {cyc}")
        self.lbl_rule.setText(result.rule_text)

    def set_selected(self, selected: bool) -> None:
        if selected:
            self.setStyleSheet("_ResultCard { border: 2px solid palette(highlight); }")
        else:
            self.setStyleSheet("")

    def mousePressEvent(self, event) -> None:
        self._on_select(self.code)
        super().mousePressEvent(event)


class Ex117Panel(BasePanel):
    """Panel Exercise 11.7 A–E. Pemilik: Anggota B."""

    title = "Exercise 11.7"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._df: Optional[pd.DataFrame] = None
        self._durations: Optional[pd.Series] = None
        self._results: dict[str, AnalysisResult] = {}
        self._active_code: str = "11.7C"
        self._running = False
        self._cards: dict[str, _ResultCard] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        header = QLabel(
            "<h3>Exercise 11.7 A–E — Jumlah Case, Cycle Time, &amp; Outcome</h3>"
            "<p>Semua angka dihitung di level case (satu case sekali). "
            "Rata-rata cycle time diambil dari durasi seluruh event case.</p>"
        )
        header.setWordWrap(True)

        # Parameter aktivitas (dropdown dari aktivitas yang ada di log)
        param_box = QGroupBox("Parameter Aktivitas")
        form = QFormLayout(param_box)
        self.cmb_accepted = QComboBox()
        self.cmb_refused = QComboBox()
        self.cmb_cancelled = QComboBox()
        for cmb, default_key in (
            (self.cmb_accepted, "accepted_activity"),
            (self.cmb_refused, "refused_activity"),
            (self.cmb_cancelled, "cancelled_activity"),
        ):
            cmb.setEditable(True)
            cmb.addItem(ex_11_7.DEFAULT_PARAMS[default_key])
            cmb.setCurrentText(ex_11_7.DEFAULT_PARAMS[default_key])

        form.addRow("11.7C (Accepted):", self.cmb_accepted)
        form.addRow("11.7D (Refused):", self.cmb_refused)
        form.addRow("11.7E (Cancelled):", self.cmb_cancelled)

        self.btn_run = QPushButton("Jalankan 11.7 A–E")
        self.btn_run.setEnabled(False)
        self.btn_run.clicked.connect(self.run_analysis)

        self.lbl_status = QLabel("Belum ada log dimuat.")
        self.lbl_status.setStyleSheet("color: palette(mid);")

        ctrl_row = QHBoxLayout()
        ctrl_row.addWidget(param_box, 1)
        btn_col = QVBoxLayout()
        btn_col.addWidget(self.btn_run)
        btn_col.addWidget(self.lbl_status)
        btn_col.addStretch(1)
        ctrl_row.addLayout(btn_col)

        # 5 kartu hasil
        card_specs = [
            ("11.7A", "Total Case"),
            ("11.7B", "Mean Cycle Time"),
            ("11.7C", "Successful"),
            ("11.7D", "Unsuccessful"),
            ("11.7E", "Canceled (Endpoint)"),
        ]
        cards_grid = QGridLayout()
        for idx, (code, label) in enumerate(card_specs):
            card = _ResultCard(code, label, self._select_code)
            self._cards[code] = card
            cards_grid.addWidget(card, idx // 3, idx % 3)

        # Pemilih sub-soal + tabel case terpilih
        self.cmb_result = QComboBox()
        for code, label in card_specs:
            self.cmb_result.addItem(f"{code} — {label}", code)
        self.cmb_result.setCurrentIndex(2)  # default 11.7C
        self.cmb_result.currentIndexChanged.connect(self._on_result_combo_changed)

        self.btn_open_case = QPushButton("Buka di Case Explorer")
        self.btn_open_case.setEnabled(False)
        self.btn_open_case.clicked.connect(self._open_selected_case)

        table_bar = QHBoxLayout()
        table_bar.addWidget(QLabel("Daftar case untuk:"))
        table_bar.addWidget(self.cmb_result)
        table_bar.addStretch(1)
        table_bar.addWidget(self.btn_open_case)

        self.case_model = DataFrameModel(
            headers={
                "case_id": "Case ID",
                "duration_days": "Durasi (hari)",
                "n_matching_events": "Jumlah event pemicu",
            }
        )
        self.case_table = QTableView()
        self.case_table.setModel(self.case_model)
        self.case_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.case_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.case_table.verticalHeader().setVisible(False)
        self.case_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.case_table.horizontalHeader().setStretchLastSection(True)
        self.case_table.setSortingEnabled(True)
        self.case_table.doubleClicked.connect(self._on_row_double_clicked)

        layout = QVBoxLayout(self)
        layout.addWidget(header)
        layout.addLayout(ctrl_row)
        layout.addLayout(cards_grid)
        layout.addLayout(table_bar)
        layout.addWidget(self.case_table, 1)

        self._select_code(self._active_code)

    # --- Kontrak BasePanel ---------------------------------------------------------------
    def set_log(self, df: pd.DataFrame, durations: pd.Series) -> None:
        self._df = df
        self._durations = durations
        activities = sorted({str(a) for a in df["activity"].dropna().unique()}) if not df.empty else []
        self._populate_activity_combo(self.cmb_accepted, activities, ex_11_7.DEFAULT_PARAMS["accepted_activity"])
        self._populate_activity_combo(self.cmb_refused, activities, ex_11_7.DEFAULT_PARAMS["refused_activity"])
        self._populate_activity_combo(self.cmb_cancelled, activities, ex_11_7.DEFAULT_PARAMS["cancelled_activity"])
        self.reset()
        self.btn_run.setEnabled(not df.empty)
        self.lbl_status.setText(f"Log siap ({df['case_id'].nunique()} case).")

    def reset(self) -> None:
        self._results.clear()
        for card in self._cards.values():
            card.set_result(None)
        self.case_model.set_frame(pd.DataFrame())
        self.btn_open_case.setEnabled(False)
        if self._df is not None:
            self.lbl_status.setText("Hasil di-reset. Klik Jalankan untuk menghitung ulang.")

    # --- Eksekusi analisis ---------------------------------------------------------------
    def _populate_activity_combo(
        self, combo: QComboBox, activities: list[str], default_val: str
    ) -> None:
        current = combo.currentText().strip() or default_val
        combo.blockSignals(True)
        combo.clear()
        items = list(activities)
        if default_val not in items:
            items.insert(0, default_val)
        combo.addItems(items)
        combo.setCurrentText(current if current in items else default_val)
        combo.blockSignals(False)

    def current_params(self) -> dict[str, str]:
        return {
            "accepted_activity": self.cmb_accepted.currentText().strip(),
            "refused_activity": self.cmb_refused.currentText().strip(),
            "cancelled_activity": self.cmb_cancelled.currentText().strip(),
        }

    def run_analysis(self) -> None:
        if self._df is None or self._durations is None or self._running:
            return
        self._running = True
        self.btn_run.setEnabled(False)
        self.lbl_status.setText("Menjalankan Exercise 11.7 A–E…")
        params = self.current_params()
        run_in_background(
            ex_11_7.run,
            self._df,
            self._durations,
            on_finished=self._on_finished,
            on_error=self._on_error,
            **params,
        )

    def _on_finished(self, results: list[AnalysisResult]) -> None:
        self._running = False
        self.btn_run.setEnabled(self._df is not None)
        self._results = {r.code: r for r in results}
        for code, card in self._cards.items():
            card.set_result(self._results.get(code))
        self._refresh_table()
        self.lbl_status.setText("Selesai menjalankan Exercise 11.7 A–E.")
        self.results_ready.emit(results)

    def _on_error(self, message: str, details: str) -> None:
        self._running = False
        self.btn_run.setEnabled(self._df is not None)
        self.lbl_status.setText(f"Gagal: {message}")
        box = QMessageBox(QMessageBox.Icon.Critical, "Error Exercise 11.7", message, parent=self)
        if details:
            box.setDetailedText(details)
        box.exec()

    # --- Navigasi hasil & buka Case Explorer ---------------------------------------------
    def _select_code(self, code: str) -> None:
        self._active_code = code
        for c, card in self._cards.items():
            card.set_selected(c == code)
        idx = self.cmb_result.findData(code)
        if idx >= 0 and self.cmb_result.currentIndex() != idx:
            self.cmb_result.blockSignals(True)
            self.cmb_result.setCurrentIndex(idx)
            self.cmb_result.blockSignals(False)
        self._refresh_table()

    def _on_result_combo_changed(self, _index: int) -> None:
        code = self.cmb_result.currentData()
        if code:
            self._select_code(str(code))

    def _refresh_table(self) -> None:
        res = self._results.get(self._active_code)
        if res is None:
            self.case_model.set_frame(pd.DataFrame())
            self.btn_open_case.setEnabled(False)
            return
        self.case_model.set_frame(res.per_case)
        self.btn_open_case.setEnabled(not res.per_case.empty)

    def _on_row_double_clicked(self, index) -> None:
        if not index.isValid():
            return
        case_id = str(self.case_model.raw(index.row(), 0))
        self.open_case_for.emit(case_id, self._active_code)
        self.open_case.emit(case_id)

    def _open_selected_case(self) -> None:
        sel = self.case_table.selectionModel().selectedRows()
        if not sel:
            if self.case_model.rowCount() > 0:
                case_id = str(self.case_model.raw(0, 0))
            else:
                return
        else:
            case_id = str(self.case_model.raw(sel[0].row(), 0))
        self.open_case_for.emit(case_id, self._active_code)
        self.open_case.emit(case_id)
