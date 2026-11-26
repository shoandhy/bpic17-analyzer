"""Panel Exercise 11.15 & 11.18 (F04, F05): repeated-complete dan same-resource, tabel bukti,
tombol buka case.

Pemilik: Anggota C (feat/c-1115-1118). Memanggil ``analyses.ex_11_15_18.run`` lewat
app/worker.py.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from analyses.ex_11_15_18 import DEFAULT_PARAMS, run as run_ex_11_15_18
from app.panels.base import BasePanel
from app.worker import run_in_background
from core.result import AnalysisResult


class Ex1115_1118Panel(BasePanel):
    """Panel GUI untuk Exercise 11.15 dan Exercise 11.18."""

    title = "Exercise 11.15 & 11.18"

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._df: Optional[pd.DataFrame] = None
        self._durations: Optional[pd.Series] = None
        self._results: list[AnalysisResult] = []
        self._request_seq: int = 0

        self._build_ui()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        # Baris parameter & tombol jalankan ulang
        param_layout = QHBoxLayout()
        param_layout.addWidget(QLabel("Aktivitas:"))
        self._activity_input = QLineEdit(str(DEFAULT_PARAMS["target_activity"]))
        self._activity_input.setMinimumWidth(210)
        param_layout.addWidget(self._activity_input)

        param_layout.addWidget(QLabel("Lifecycle:"))
        self._lifecycle_combo = QComboBox()
        self._lifecycle_combo.addItems(["auto (complete)", "complete"])
        param_layout.addWidget(self._lifecycle_combo)

        param_layout.addWidget(QLabel("Min count:"))
        self._min_count_spin = QSpinBox()
        self._min_count_spin.setRange(1, 999)
        self._min_count_spin.setValue(int(DEFAULT_PARAMS["min_count"]))
        param_layout.addWidget(self._min_count_spin)

        self._run_btn = QPushButton("Jalankan")
        self._run_btn.setEnabled(False)
        self._run_btn.clicked.connect(self._trigger_run)
        param_layout.addWidget(self._run_btn)

        param_layout.addStretch()
        root_layout.addLayout(param_layout)

        # Label status & ringkasan
        self._status_label = QLabel("Belum ada log dimuat.")
        self._status_label.setWordWrap(True)
        root_layout.addWidget(self._status_label)

        self._summary_label = QLabel("")
        self._summary_label.setWordWrap(True)
        root_layout.addWidget(self._summary_label)

        # Tab untuk 11.15 dan 11.18
        self._tabs = QTabWidget()
        self._tab_1115, self._table_1115, self._rule_1115 = self._create_result_tab("11.15")
        self._tab_1118, self._table_1118, self._rule_1118 = self._create_result_tab("11.18")
        self._tabs.addTab(self._tab_1115, "Exercise 11.15")
        self._tabs.addTab(self._tab_1118, "Exercise 11.18")
        root_layout.addWidget(self._tabs, stretch=1)

        # Baris aksi buka Case Explorer
        action_layout = QHBoxLayout()
        self._open_case_btn = QPushButton("Buka Case di Explorer")
        self._open_case_btn.setEnabled(False)
        self._open_case_btn.clicked.connect(self._emit_open_selected_case)
        action_layout.addWidget(self._open_case_btn)
        action_layout.addStretch()
        root_layout.addLayout(action_layout)

    def _create_result_tab(
        self, code: str
    ) -> tuple[QWidget, QTableWidget, QLabel]:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        rule_lbl = QLabel(f"Aturan ({code}): -")
        rule_lbl.setWordWrap(True)
        layout.addWidget(rule_lbl)

        table = QTableWidget(0, 0)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        table.itemSelectionChanged.connect(self._update_open_case_button)
        table.cellDoubleClicked.connect(lambda _r, _c: self._emit_open_selected_case())
        layout.addWidget(table, stretch=1)

        return tab, table, rule_lbl

    def _current_params(self) -> dict[str, object]:
        act_text = self._activity_input.text().strip() or str(DEFAULT_PARAMS["target_activity"])
        lc_choice = self._lifecycle_combo.currentText()
        lc_val: Optional[str] = None if lc_choice.startswith("auto") else lc_choice
        return {
            "target_activity": act_text,
            "complete_lifecycle": lc_val,
            "min_count": int(self._min_count_spin.value()),
        }

    def set_log(self, df: pd.DataFrame, durations: pd.Series) -> None:
        """Terima DataFrame kanonik dan durasi per case dari MainWindow."""
        self._df = df
        self._durations = durations
        self._run_btn.setEnabled(df is not None and not df.empty)
        if df is None or df.empty:
            self.reset()
            self._status_label.setText("Log kosong.")
            return
        self._trigger_run()

    def _trigger_run(self) -> None:
        if self._df is None or self._durations is None:
            return
        self._request_seq += 1
        seq = self._request_seq
        params = self._current_params()
        self._status_label.setText("Menghitung Exercise 11.15 & 11.18...")
        self._run_btn.setEnabled(False)

        run_in_background(
            run_ex_11_15_18,
            self._df,
            self._durations,
            on_finished=lambda res, s=seq: self._on_finished(s, res),
            on_error=lambda msg, tb, s=seq: self._on_error(s, msg, tb),
            **params,
        )

    def _on_finished(self, seq: int, results: object) -> None:
        if seq != self._request_seq:
            return
        self._run_btn.setEnabled(self._df is not None and not self._df.empty)
        if not isinstance(results, list):
            self._status_label.setText("Format hasil tidak sesuai.")
            return

        self._results = results
        by_code = {r.code: r for r in results if isinstance(r, AnalysisResult)}

        r15 = by_code.get("11.15")
        r18 = by_code.get("11.18")

        parts: list[str] = []
        if r15 is not None:
            self._populate_table(self._table_1115, r15.per_case)
            self._rule_1115.setText(f"Aturan 11.15: {r15.rule_text}")
            dur_str = f"{r15.mean_cycle_days:.2f} hari" if r15.mean_cycle_days is not None else "-"
            parts.append(f"11.15: {r15.n_cases}/{r15.denominator} case (rata-rata durasi: {dur_str})")
        if r18 is not None:
            self._populate_table(self._table_1118, r18.per_case)
            self._rule_1118.setText(f"Aturan 11.18: {r18.rule_text}")
            dur_str = f"{r18.mean_cycle_days:.2f} hari" if r18.mean_cycle_days is not None else "-"
            parts.append(f"11.18: {r18.n_cases}/{r18.denominator} case (rata-rata durasi: {dur_str})")

        self._summary_label.setText(" | ".join(parts))
        self._status_label.setText("Analisis selesai.")
        self._update_open_case_button()
        self.results_ready.emit(results)

    def _on_error(self, seq: int, message: str, _traceback_text: str) -> None:
        if seq != self._request_seq:
            return
        self._run_btn.setEnabled(self._df is not None and not self._df.empty)
        self._status_label.setText(f"Gagal menjalankan analisis: {message}")

    def _populate_table(self, table: QTableWidget, df_rows: pd.DataFrame) -> None:
        table.clear()
        if df_rows is None or df_rows.empty:
            table.setRowCount(0)
            table.setColumnCount(0)
            return

        cols = list(df_rows.columns)
        table.setColumnCount(len(cols))
        table.setHorizontalHeaderLabels(cols)
        table.setRowCount(len(df_rows))

        for row_idx, (_, row) in enumerate(df_rows.iterrows()):
            for col_idx, col in enumerate(cols):
                val = row[col]
                if pd.isna(val):
                    text = ""
                elif isinstance(val, float):
                    text = f"{val:.4f}"
                else:
                    text = str(val)
                item = QTableWidgetItem(text)
                if col == "case_id":
                    item.setData(Qt.ItemDataRole.UserRole, str(val))
                table.setItem(row_idx, col_idx, item)

    def _active_code_and_table(self) -> tuple[str, QTableWidget]:
        if self._tabs.currentIndex() == 1:
            return "11.18", self._table_1118
        return "11.15", self._table_1115

    def _selected_case_id(self) -> Optional[str]:
        _, table = self._active_code_and_table()
        row = table.currentRow()
        if row < 0:
            return None
        for col in range(table.columnCount()):
            header = table.horizontalHeaderItem(col)
            if header is not None and header.text() == "case_id":
                item = table.item(row, col)
                if item is not None:
                    val = item.data(Qt.ItemDataRole.UserRole) or item.text()
                    return str(val).strip() or None
        first_item = table.item(row, 0)
        return str(first_item.text()).strip() if first_item and first_item.text().strip() else None

    def _update_open_case_button(self) -> None:
        self._open_case_btn.setEnabled(self._selected_case_id() is not None)

    def _emit_open_selected_case(self) -> None:
        case_id = self._selected_case_id()
        if not case_id:
            return
        code, _ = self._active_code_and_table()
        self.open_case_for.emit(case_id, code)

    def reset(self) -> None:
        """Kosongkan hasil yang ditampilkan (log tetap dimuat)."""
        self._request_seq += 1
        self._results = []
        self._summary_label.setText("")
        self._rule_1115.setText("Aturan 11.15: -")
        self._rule_1118.setText("Aturan 11.18: -")
        self._table_1115.clear()
        self._table_1115.setRowCount(0)
        self._table_1115.setColumnCount(0)
        self._table_1118.clear()
        self._table_1118.setRowCount(0)
        self._table_1118.setColumnCount(0)
        self._update_open_case_button()
        if self._df is not None and not self._df.empty:
            self._status_label.setText("Hasil direset (log masih dimuat).")