"""Panel Exercise 11.22 (F06): jumlah, persentase + denominator, tabel case,
timeline event case terpilih (Matplotlib), analisis tambahan level OfferID,
serta fitur opsional Fast vs Slow Cases + histogram durasi.

Pemilik: Anggota D (feat/d-1122-fixtures). Memanggil ``analyses.ex_11_22`` dan
``analyses.optional`` lewat ``app/worker.py`` (tidak pernah memblokir thread UI).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib
import numpy as np
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from analyses import ex_11_22, optional
from app.panels.base import BasePanel
from app.panels.case_explorer import DataFrameModel
from app.worker import run_in_background
from core.loaded_log import LoadedLog
from core.result import AnalysisResult
from core.schema import DURATION_NAME

# Pastikan backend QtAgg dipakai secara eksplisit (aman di QT_QPA_PLATFORM=offscreen).
matplotlib.use("QtAgg")


class _MetricCard(QFrame):
    """Kartu ringkasan satu metrik numerik + keterangan."""

    def __init__(self, heading: str, parent=None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)

        self.lbl_heading = QLabel(f"<b>{heading}</b>")
        self.lbl_value = QLabel("—")
        self.lbl_value.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.lbl_sub = QLabel("")
        self.lbl_sub.setWordWrap(True)
        self.lbl_sub.setStyleSheet("color: palette(mid); font-size: 11px;")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.addWidget(self.lbl_heading)
        lay.addWidget(self.lbl_value)
        lay.addWidget(self.lbl_sub, 1)

    def set_values(self, value: str, sub: str = "") -> None:
        self.lbl_value.setText(value)
        self.lbl_sub.setText(sub)

    def clear(self) -> None:
        self.lbl_value.setText("—")
        self.lbl_sub.setText("")


class Ex1122Panel(BasePanel):
    """Panel Exercise 11.22 (level case) + tab tambahan OfferID & fitur opsional Fast/Slow.

    Pemilik: Anggota D.
    """

    title = "Exercise 11.22"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._df: Optional[pd.DataFrame] = None
        self._durations: Optional[pd.Series] = None
        self._offer_col: Optional[str] = None

        self._result_1122: Optional[AnalysisResult] = None
        self._result_offer: Optional[AnalysisResult] = None
        self._results_opt: dict[str, AnalysisResult] = {}

        self._running_1122 = False
        self._running_offer = False
        self._running_opt = False

        self._build_ui()

    # ======================================================================== UI =========
    def _build_ui(self) -> None:
        self.lbl_file = QLabel("Belum ada log dimuat.")
        self.lbl_file.setStyleSheet("color: palette(mid);")

        self.tabs = QTabWidget()
        self.tab_case = self._build_case_level_tab()
        self.tab_offer = self._build_offer_level_tab()
        self.tab_opt = self._build_optional_tab()

        self.tabs.addTab(self.tab_case, "Exercise 11.22 (Level Case — Wajib)")
        self.tabs.addTab(self.tab_offer, "Tambahan: Level OfferID")
        self.tabs.addTab(self.tab_opt, "Opsional: Fast vs Slow & Histogram")

        root = QVBoxLayout(self)
        root.addWidget(self.lbl_file)
        root.addWidget(self.tabs, 1)

    def _build_case_level_tab(self) -> QWidget:
        page = QWidget()

        banner = QLabel(
            "<h3>Exercise 11.22 (F06) — Analisis Urutan Event (<i>Level Case</i>)</h3>"
            "<p><b>Scope: Analisis level case (jawaban wajib)</b> — bukan level OfferID "
            "dan bukan syarat event terakhir <code>O_Cancelled</code>. "
            "Case lolos jika ada posisi <code>i &lt; j</code> (<code>event_pos</code>) dengan "
            "event <code>i</code> = aktivitas pertama dan event <code>j</code> = aktivitas berikutnya "
            "(tidak harus bertetangga).</p>"
        )
        banner.setWordWrap(True)

        # Parameter aktivitas
        param_box = QGroupBox("Parameter Urutan Aktivitas (Level Case)")
        form = QFormLayout(param_box)
        self.cmb_first = QComboBox()
        self.cmb_then = QComboBox()
        for cmb, key in (
            (self.cmb_first, "first_activity"),
            (self.cmb_then, "then_activity"),
        ):
            cmb.setEditable(True)
            cmb.addItem(ex_11_22.DEFAULT_PARAMS[key])
            cmb.setCurrentText(ex_11_22.DEFAULT_PARAMS[key])
        form.addRow("Aktivitas pertama (i):", self.cmb_first)
        form.addRow("Diikuti aktivitas (j > i):", self.cmb_then)

        self.btn_run = QPushButton("Jalankan Exercise 11.22")
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

        # Kartu ringkasan: jumlah, persentase + rumus + denominator, rata-rata cycle time
        self.card_count = _MetricCard("Jumlah Case Lolos (Level Case)")
        self.card_pct = _MetricCard("Persentase & Denominator")
        self.card_cycle = _MetricCard("Rata-rata Cycle Time")
        cards_row = QHBoxLayout()
        cards_row.addWidget(self.card_count, 1)
        cards_row.addWidget(self.card_pct, 2)
        cards_row.addWidget(self.card_cycle, 1)

        self.lbl_rule = QLabel("Aturan filter akan ditampilkan setelah analisis dijalankan.")
        self.lbl_rule.setWordWrap(True)
        self.lbl_rule.setStyleSheet("color: palette(mid); font-size: 11px;")

        # Kiri: tabel case + tombol buka Case Explorer
        self.case_model = DataFrameModel(
            headers={
                "case_id": "Case ID",
                DURATION_NAME: "Durasi (hari)",
                "first_pos": "Pos a (pertama)",
                "first_timestamp": "Timestamp a (UTC)",
                "then_pos": "Pos b (terakhir)",
                "then_timestamp": "Timestamp b (UTC)",
                "gap_events": "Event di antara",
            }
        )
        self.case_table = QTableView()
        self.case_table.setModel(self.case_model)
        self.case_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.case_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.case_table.verticalHeader().setVisible(False)
        self.case_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.case_table.horizontalHeader().setStretchLastSection(True)
        self.case_table.setSortingEnabled(True)
        self.case_table.doubleClicked.connect(self._on_case_double_clicked)
        self.case_table.selectionModel().currentRowChanged.connect(self._on_case_row_changed)

        self.btn_open_case = QPushButton("Buka di Case Explorer")
        self.btn_open_case.setEnabled(False)
        self.btn_open_case.clicked.connect(self._open_selected_case)

        left_box = QWidget()
        left_lay = QVBoxLayout(left_box)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_bar = QHBoxLayout()
        left_bar.addWidget(QLabel("<b>Daftar Case Lolos & Pasangan Bukti</b>"))
        left_bar.addStretch(1)
        left_bar.addWidget(self.btn_open_case)
        left_lay.addLayout(left_bar)
        left_lay.addWidget(self.case_table, 1)

        # Kanan: timeline event case terpilih (Matplotlib)
        self.lbl_pair_summary = QLabel("Pilih satu case di tabel kiri untuk melihat timeline event.")
        self.lbl_pair_summary.setWordWrap(True)
        self.timeline_fig = Figure(figsize=(5.5, 3.4), dpi=96)
        self.timeline_canvas = FigureCanvasQTAgg(self.timeline_fig)

        right_box = QWidget()
        right_lay = QVBoxLayout(right_box)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.addWidget(QLabel("<b>Timeline Event Case Terpilih</b>"))
        right_lay.addWidget(self.lbl_pair_summary)
        right_lay.addWidget(self.timeline_canvas, 1)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_box)
        splitter.addWidget(right_box)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 3)

        lay = QVBoxLayout(page)
        lay.addWidget(banner)
        lay.addLayout(ctrl_row)
        lay.addLayout(cards_row)
        lay.addWidget(self.lbl_rule)
        lay.addWidget(splitter, 1)

        self._draw_empty_timeline("Jalankan analisis lalu pilih case untuk melihat timeline.")
        return page

    def _build_offer_level_tab(self) -> QWidget:
        page = QWidget()
        banner = QLabel(
            "<h3>Analisis Tambahan — Level OfferID (Terpisah dari Jawaban Wajib)</h3>"
            "<p><b>Catatan (Instruksi Bag. 7.3):</b> Ini adalah analisis <b>tambahan</b> "
            "dengan kode <code>11.22-offer</code> untuk memeriksa apakah <code>O_Cancelled</code> "
            "diikuti <code>O_Accepted</code> pada <b>OfferID yang sama</b> dalam satu case. "
            "Hasil ini tidak dicampurkan dengan jawaban soal wajib Exercise 11.22 (level case).</p>"
        )
        banner.setWordWrap(True)

        self.lbl_offer_status = QLabel("Belum ada log dimuat.")
        self.lbl_offer_status.setWordWrap(True)
        self.btn_run_offer = QPushButton("Jalankan Analisis Tambahan (Level OfferID)")
        self.btn_run_offer.setEnabled(False)
        self.btn_run_offer.clicked.connect(self.run_offer_analysis)

        top = QHBoxLayout()
        top.addWidget(self.btn_run_offer)
        top.addWidget(self.lbl_offer_status, 1)

        self.card_offer_count = _MetricCard("[Tambahan] Jumlah Case (OfferID Sama)")
        self.card_offer_pct = _MetricCard("[Tambahan] Persentase & Denominator")
        cards = QHBoxLayout()
        cards.addWidget(self.card_offer_count, 1)
        cards.addWidget(self.card_offer_pct, 2)

        self.offer_model = DataFrameModel(
            headers={
                "case_id": "Case ID",
                DURATION_NAME: "Durasi (hari)",
                "offer_id": "OfferID cocok",
                "first_pos": "Pos a",
                "first_timestamp": "Timestamp a (UTC)",
                "then_pos": "Pos b",
                "then_timestamp": "Timestamp b (UTC)",
                "gap_events": "Event di antara",
            }
        )
        self.offer_table = QTableView()
        self.offer_table.setModel(self.offer_model)
        self.offer_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.offer_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.offer_table.verticalHeader().setVisible(False)
        self.offer_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.offer_table.horizontalHeader().setStretchLastSection(True)
        self.offer_table.doubleClicked.connect(self._on_offer_double_clicked)

        self.btn_open_offer = QPushButton("Buka di Case Explorer")
        self.btn_open_offer.setEnabled(False)
        self.btn_open_offer.clicked.connect(self._open_selected_offer_case)

        bar = QHBoxLayout()
        bar.addWidget(QLabel("<b>Case Lolos (Level OfferID — Tambahan)</b>"))
        bar.addStretch(1)
        bar.addWidget(self.btn_open_offer)

        lay = QVBoxLayout(page)
        lay.addWidget(banner)
        lay.addLayout(top)
        lay.addLayout(cards)
        lay.addLayout(bar)
        lay.addWidget(self.offer_table, 1)
        return page

    def _build_optional_tab(self) -> QWidget:
        page = QWidget()
        banner = QLabel(
            "<h3>Fitur Opsional — Fast vs Slow Cases &amp; Histogram Durasi (Example 11.10)</h3>"
            "<p>Membagi seluruh case berdasarkan durasi utuh case: "
            "<b>Fast</b> (&lt; ambang hari, kode <code>OPT.fast</code>) dan "
            "<b>Slow</b> (&ge; ambang hari, kode <code>OPT.slow</code>), dilengkapi "
            "perbandingan karakteristik serta histogram distribusi durasi.</p>"
        )
        banner.setWordWrap(True)

        self.spin_threshold = QDoubleSpinBox()
        self.spin_threshold.setRange(0.0, 10000.0)
        self.spin_threshold.setDecimals(1)
        self.spin_threshold.setSuffix(" hari")
        self.spin_threshold.setValue(float(optional.DEFAULT_PARAMS["threshold_days"]))

        self.btn_run_opt = QPushButton("Jalankan Fast vs Slow")
        self.btn_run_opt.setEnabled(False)
        self.btn_run_opt.clicked.connect(self.run_optional_analysis)

        self.lbl_opt_status = QLabel("Belum ada log dimuat.")
        self.lbl_opt_status.setStyleSheet("color: palette(mid);")

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("Ambang batas:"))
        ctrl.addWidget(self.spin_threshold)
        ctrl.addWidget(self.btn_run_opt)
        ctrl.addWidget(self.lbl_opt_status, 1)

        self.card_fast = _MetricCard("Fast Cases (OPT.fast)")
        self.card_slow = _MetricCard("Slow Cases (OPT.slow)")
        cards = QHBoxLayout()
        cards.addWidget(self.card_fast, 1)
        cards.addWidget(self.card_slow, 1)

        # Tabel perbandingan karakteristik
        self.compare_model = DataFrameModel(
            headers={
                "group": "Kelompok",
                "n_cases": "Jumlah case",
                "percentage": "Persentase (%)",
                "mean_duration_days": "Mean durasi (hari)",
                "median_duration_days": "Median durasi (hari)",
                "mean_events": "Mean event/case",
                "accepted_rate_pct": "O_Accepted (%)",
                "refused_rate_pct": "O_Refused (%)",
            }
        )
        self.compare_table = QTableView()
        self.compare_table.setModel(self.compare_model)
        self.compare_table.verticalHeader().setVisible(False)
        self.compare_table.setMaximumHeight(110)
        self.compare_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.compare_table.horizontalHeader().setStretchLastSection(True)

        # Splitter: kiri histogram durasi, kanan daftar case fast/slow
        self.hist_fig = Figure(figsize=(5.5, 3.2), dpi=96)
        self.hist_canvas = FigureCanvasQTAgg(self.hist_fig)

        self.cmb_opt_group = QComboBox()
        self.cmb_opt_group.addItem("OPT.fast — Fast cases", "OPT.fast")
        self.cmb_opt_group.addItem("OPT.slow — Slow cases", "OPT.slow")
        self.cmb_opt_group.currentIndexChanged.connect(self._refresh_opt_case_table)

        self.btn_open_opt_case = QPushButton("Buka di Case Explorer")
        self.btn_open_opt_case.setEnabled(False)
        self.btn_open_opt_case.clicked.connect(self._open_selected_opt_case)

        self.opt_case_model = DataFrameModel(
            headers={
                "case_id": "Case ID",
                DURATION_NAME: "Durasi (hari)",
                "n_events": "Jumlah event",
            }
        )
        self.opt_case_table = QTableView()
        self.opt_case_table.setModel(self.opt_case_model)
        self.opt_case_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.opt_case_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.opt_case_table.verticalHeader().setVisible(False)
        self.opt_case_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.opt_case_table.horizontalHeader().setStretchLastSection(True)
        self.opt_case_table.setSortingEnabled(True)
        self.opt_case_table.doubleClicked.connect(self._on_opt_double_clicked)

        right = QWidget()
        rlay = QVBoxLayout(right)
        rlay.setContentsMargins(0, 0, 0, 0)
        rbar = QHBoxLayout()
        rbar.addWidget(self.cmb_opt_group)
        rbar.addStretch(1)
        rbar.addWidget(self.btn_open_opt_case)
        rlay.addLayout(rbar)
        rlay.addWidget(self.opt_case_table, 1)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.hist_canvas)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        lay = QVBoxLayout(page)
        lay.addWidget(banner)
        lay.addLayout(ctrl)
        lay.addLayout(cards)
        lay.addWidget(self.compare_table)
        lay.addWidget(splitter, 1)

        self._draw_empty_histogram("Jalankan Fast vs Slow untuk menampilkan histogram durasi.")
        return page

    # ================================================================ Kontrak BasePanel ===
    def set_log(self, df: pd.DataFrame, durations: pd.Series) -> None:
        self._df = df
        self._durations = durations
        self._offer_col = ex_11_22.find_offer_column(df)

        activities = (
            sorted({str(a) for a in df["activity"].dropna().unique()}) if not df.empty else []
        )
        self._populate_combo(self.cmb_first, activities, ex_11_22.DEFAULT_PARAMS["first_activity"])
        self._populate_combo(self.cmb_then, activities, ex_11_22.DEFAULT_PARAMS["then_activity"])

        self.reset()

        has_data = not df.empty
        self.btn_run.setEnabled(has_data)
        self.btn_run_opt.setEnabled(has_data)

        n_cases = int(df["case_id"].nunique()) if has_data else 0
        self.lbl_file.setText(f"Log aktif: {n_cases} case · {len(df)} event")
        self.lbl_status.setText(f"Log siap ({n_cases} case).")
        self.lbl_opt_status.setText(f"Log siap ({n_cases} case).")

        if has_data and self._offer_col is not None:
            self.btn_run_offer.setEnabled(True)
            self.lbl_offer_status.setText(
                f"Kolom OfferID terdeteksi: '{self._offer_col}'. Siap dijalankan."
            )
        else:
            self.btn_run_offer.setEnabled(False)
            self.lbl_offer_status.setText(
                "Log aktif tidak memuat kolom OfferID — analisis tambahan level OfferID tidak berlaku."
            )

    def set_loaded(self, loaded: LoadedLog) -> None:
        self.lbl_file.setText(
            f"File: <b>{Path(loaded.path).name}</b> · {loaded.n_cases} case · {loaded.n_events} event"
        )

    def reset(self) -> None:
        self._result_1122 = None
        self._result_offer = None
        self._results_opt.clear()

        self.card_count.clear()
        self.card_pct.clear()
        self.card_cycle.clear()
        self.lbl_rule.setText("Aturan filter akan ditampilkan setelah analisis dijalankan.")
        self.case_model.set_frame(pd.DataFrame())
        self.btn_open_case.setEnabled(False)
        self.lbl_pair_summary.setText("Pilih satu case di tabel kiri untuk melihat timeline event.")
        self._draw_empty_timeline("Hasil di-reset. Jalankan analisis untuk melihat timeline.")

        self.card_offer_count.clear()
        self.card_offer_pct.clear()
        self.offer_model.set_frame(pd.DataFrame())
        self.btn_open_offer.setEnabled(False)

        self.card_fast.clear()
        self.card_slow.clear()
        self.compare_model.set_frame(pd.DataFrame())
        self.opt_case_model.set_frame(pd.DataFrame())
        self.btn_open_opt_case.setEnabled(False)
        self._draw_empty_histogram("Hasil di-reset. Jalankan Fast vs Slow untuk melihat histogram.")

        if self._df is not None:
            self.lbl_status.setText("Hasil di-reset. Klik Jalankan untuk menghitung ulang.")
            self.lbl_opt_status.setText("Hasil di-reset. Klik Jalankan untuk menghitung ulang.")

    # ================================================================ Helper UI ===========
    @staticmethod
    def _populate_combo(combo: QComboBox, activities: list[str], default_val: str) -> None:
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
            "first_activity": self.cmb_first.currentText().strip(),
            "then_activity": self.cmb_then.currentText().strip(),
        }

    def _emit_open_case(self, case_id: str, code: str) -> None:
        # Emit v1 dulu, lalu v2 agar MainWindow menyorot kode hasil yang persis tepat.
        self.open_case.emit(case_id)
        self.open_case_for.emit(case_id, code)

    def _show_error(self, title: str, message: str, details: str) -> None:
        box = QMessageBox(QMessageBox.Icon.Critical, title, message, parent=self)
        if details:
            box.setDetailedText(details)
        box.exec()

    # ======================================================= Eksekusi 11.22 (Level Case) ==
    def run_analysis(self) -> None:
        if self._df is None or self._durations is None or self._running_1122:
            return
        self._running_1122 = True
        self.btn_run.setEnabled(False)
        self.lbl_status.setText("Menjalankan Exercise 11.22 (level case)…")
        params = self.current_params()
        run_in_background(
            ex_11_22.run,
            self._df,
            self._durations,
            on_finished=self._on_1122_finished,
            on_error=self._on_1122_error,
            **params,
        )

    def _on_1122_finished(self, result: AnalysisResult) -> None:
        self._running_1122 = False
        self.btn_run.setEnabled(self._df is not None and not self._df.empty)
        self._result_1122 = result

        self.card_count.set_values(
            f"{result.n_cases} case",
            f"Dari total {result.denominator} case aktif (level case)",
        )
        if result.percentage is not None:
            pct_text = f"{result.percentage:.2f}%"
            formula = (
                f"Rumus: n_cases / denominator × 100% = "
                f"{result.n_cases} / {result.denominator} × 100%"
            )
        else:
            pct_text = "—"
            formula = f"Denominator: {result.denominator} case"
        self.card_pct.set_values(pct_text, formula)

        cyc_text = (
            f"{result.mean_cycle_days:.3f} hari"
            if result.mean_cycle_days is not None
            else "—"
        )
        self.card_cycle.set_values(cyc_text, "Mean durasi utuh case lolos")
        self.lbl_rule.setText(result.rule_text)

        self.case_model.set_frame(result.per_case)
        has_rows = self.case_model.rowCount() > 0
        self.btn_open_case.setEnabled(has_rows)
        if has_rows:
            first_idx = self.case_model.index(0, 0)
            self.case_table.setCurrentIndex(first_idx)
            self._render_case_timeline(str(self.case_model.raw(0, 0)))
        else:
            self.lbl_pair_summary.setText("Tidak ada case yang memenuhi pola pada log aktif.")
            self._draw_empty_timeline("Tidak ada case yang lolos filter Exercise 11.22.")

        self.lbl_status.setText("Selesai menjalankan Exercise 11.22.")
        self.results_ready.emit([result])

    def _on_1122_error(self, message: str, details: str) -> None:
        self._running_1122 = False
        self.btn_run.setEnabled(self._df is not None and not self._df.empty)
        self.lbl_status.setText(f"Gagal: {message}")
        self._show_error("Error Exercise 11.22", message, details)

    def _on_case_row_changed(self, current: QModelIndex, _previous: QModelIndex) -> None:
        if not current.isValid():
            return
        case_id = str(self.case_model.raw(current.row(), 0))
        self._render_case_timeline(case_id)

    def _on_case_double_clicked(self, index: QModelIndex) -> None:
        if not index.isValid():
            return
        case_id = str(self.case_model.raw(index.row(), 0))
        self._emit_open_case(case_id, "11.22")

    def _open_selected_case(self) -> None:
        sel = self.case_table.selectionModel().selectedRows()
        if sel:
            case_id = str(self.case_model.raw(sel[0].row(), 0))
        elif self.case_model.rowCount() > 0:
            case_id = str(self.case_model.raw(0, 0))
        else:
            return
        self._emit_open_case(case_id, "11.22")

    # ======================================================= Timeline Matplotlib ==========
    def _draw_empty_timeline(self, message: str) -> None:
        self.timeline_fig.clear()
        ax = self.timeline_fig.add_subplot(111)
        ax.text(0.5, 0.5, message, ha="center", va="center", color="gray", wrap=True)
        ax.set_axis_off()
        self.timeline_canvas.draw_idle()

    def _render_case_timeline(self, case_id: str) -> None:
        if self._df is None or self._result_1122 is None:
            return
        trace = (
            self._df.loc[self._df["case_id"].astype(str) == case_id]
            .sort_values(["event_pos", "orig_idx"], kind="stable")
            .reset_index(drop=True)
        )
        if trace.empty:
            self._draw_empty_timeline(f"Trace untuk case '{case_id}' kosong.")
            return

        ev = self._result_1122.evidence
        case_ev = (
            ev.loc[ev["case_id"].astype(str) == case_id]
            .sort_values(["event_pos", "orig_idx"], kind="stable")
        )
        first_act = self._result_1122.params.get("first_activity", "O_Cancelled")
        then_act = self._result_1122.params.get("then_activity", "O_Accepted")

        first_row = case_ev.iloc[0] if len(case_ev) >= 1 else None
        last_row = case_ev.iloc[-1] if len(case_ev) >= 2 else None
        first_orig = int(first_row["orig_idx"]) if first_row is not None else -1
        last_orig = int(last_row["orig_idx"]) if last_row is not None else -1

        if first_row is not None and last_row is not None:
            t1 = first_row["timestamp"].isoformat(sep=" ", timespec="seconds")
            t2 = last_row["timestamp"].isoformat(sep=" ", timespec="seconds")
            gap = int(last_row["event_pos"]) - int(first_row["event_pos"]) - 1
            self.lbl_pair_summary.setText(
                f"<b>Case {case_id}</b> ({len(trace)} event) · "
                f"Bukti pertama: <b>{first_act}</b> [pos {int(first_row['event_pos'])}, {t1}] → "
                f"Bukti terakhir: <b>{then_act}</b> [pos {int(last_row['event_pos'])}, {t2}] "
                f"(selisih {gap} event di antara)."
            )
        else:
            self.lbl_pair_summary.setText(f"<b>Case {case_id}</b> ({len(trace)} event)")

        self.timeline_fig.clear()
        ax = self.timeline_fig.add_subplot(111)

        t0 = trace["timestamp"].iloc[0]
        elapsed_days = (trace["timestamp"] - t0).dt.total_seconds().to_numpy() / 86400.0
        positions = trace["event_pos"].to_numpy(dtype="int64")
        origs = trace["orig_idx"].to_numpy(dtype="int64")

        ax.plot(positions, elapsed_days, color="#90a4ae", linewidth=1.4, zorder=1)

        colors = []
        sizes = []
        for oid in origs:
            if oid == first_orig:
                colors.append("#e53935")  # merah: first_activity (O_Cancelled)
                sizes.append(95)
            elif oid == last_orig:
                colors.append("#2e7d32")  # hijau: then_activity (O_Accepted)
                sizes.append(95)
            else:
                colors.append("#1e88e5")  # biru: aktivitas lain
                sizes.append(42)

        ax.scatter(positions, elapsed_days, c=colors, s=sizes, zorder=3, edgecolors="white")

        # Anotasi semua event untuk trace ringkas, atau event bukti saja untuk trace panjang.
        annotate_all = len(trace) <= 15
        for idx, row in trace.iterrows():
            oid = int(row["orig_idx"])
            pos = int(row["event_pos"])
            day = float(elapsed_days[idx])
            is_ev = oid in (first_orig, last_orig)
            if annotate_all or is_ev:
                label = f"[{pos}] {row['activity']}"
                ax.annotate(
                    label,
                    (pos, day),
                    textcoords="offset points",
                    xytext=(0, 8 if idx % 2 == 0 else -14),
                    ha="center",
                    fontsize=7.5 if not is_ev else 8.5,
                    fontweight="bold" if is_ev else "normal",
                    color="#b71c1c" if oid == first_orig else ("#1b5e20" if oid == last_orig else "#37474f"),
                )

        # Panah penghubung bukti i -> j
        if first_row is not None and last_row is not None:
            p1 = int(first_row["event_pos"])
            p2 = int(last_row["event_pos"])
            d1 = float((first_row["timestamp"] - t0).total_seconds() / 86400.0)
            d2 = float((last_row["timestamp"] - t0).total_seconds() / 86400.0)
            ax.annotate(
                "",
                xy=(p2, d2),
                xytext=(p1, d1),
                arrowprops=dict(arrowstyle="->", color="#ef6c00", lw=1.8, ls="--"),
                zorder=2,
            )

        ax.set_title(f"Timeline Event — Case {case_id}", fontsize=10)
        ax.set_xlabel("Posisi Event dalam Trace (event_pos)")
        ax.set_ylabel("Waktu sejak awal case (hari)")
        ax.grid(True, linestyle=":", alpha=0.5)
        self.timeline_fig.tight_layout()
        self.timeline_canvas.draw_idle()

    # ======================================================= Eksekusi Level OfferID =======
    def run_offer_analysis(self) -> None:
        if (
            self._df is None
            or self._durations is None
            or self._offer_col is None
            or self._running_offer
        ):
            return
        self._running_offer = True
        self.btn_run_offer.setEnabled(False)
        self.lbl_offer_status.setText("Menjalankan analisis tambahan level OfferID…")
        params = self.current_params()
        run_in_background(
            ex_11_22.run_offer_level,
            self._df,
            self._durations,
            offer_col=self._offer_col,
            on_finished=self._on_offer_finished,
            on_error=self._on_offer_error,
            **params,
        )

    def _on_offer_finished(self, result: AnalysisResult) -> None:
        self._running_offer = False
        self.btn_run_offer.setEnabled(self._offer_col is not None)
        self._result_offer = result

        self.card_offer_count.set_values(
            f"{result.n_cases} case",
            f"OfferID sama · dari {result.denominator} case aktif",
        )
        pct_text = f"{result.percentage:.2f}%" if result.percentage is not None else "—"
        self.card_offer_pct.set_values(
            pct_text,
            f"Rumus: {result.n_cases} / {result.denominator} × 100% (tambahan, bukan jawaban wajib)",
        )
        self.offer_model.set_frame(result.per_case)
        self.btn_open_offer.setEnabled(self.offer_model.rowCount() > 0)
        self.lbl_offer_status.setText("Selesai menjalankan analisis tambahan level OfferID.")
        self.results_ready.emit([result])

    def _on_offer_error(self, message: str, details: str) -> None:
        self._running_offer = False
        self.btn_run_offer.setEnabled(self._offer_col is not None)
        self.lbl_offer_status.setText(f"Gagal: {message}")
        self._show_error("Error Analisis Level OfferID", message, details)

    def _on_offer_double_clicked(self, index: QModelIndex) -> None:
        if not index.isValid():
            return
        case_id = str(self.offer_model.raw(index.row(), 0))
        self._emit_open_case(case_id, "11.22-offer")

    def _open_selected_offer_case(self) -> None:
        sel = self.offer_table.selectionModel().selectedRows()
        if sel:
            case_id = str(self.offer_model.raw(sel[0].row(), 0))
        elif self.offer_model.rowCount() > 0:
            case_id = str(self.offer_model.raw(0, 0))
        else:
            return
        self._emit_open_case(case_id, "11.22-offer")

    # ======================================================= Eksekusi Opsional Fast/Slow ==
    def run_optional_analysis(self) -> None:
        if self._df is None or self._durations is None or self._running_opt:
            return
        self._running_opt = True
        self.btn_run_opt.setEnabled(False)
        threshold = float(self.spin_threshold.value())
        self.lbl_opt_status.setText(f"Menjalankan Fast vs Slow (ambang {threshold:g} hari)…")
        run_in_background(
            self._run_optional_bundle,
            self._df,
            self._durations,
            threshold,
            on_finished=self._on_opt_finished,
            on_error=self._on_opt_error,
        )

    @staticmethod
    def _run_optional_bundle(
        df: pd.DataFrame, durations: pd.Series, threshold_days: float
    ) -> tuple[list[AnalysisResult], pd.DataFrame, dict]:
        results = optional.run(df, durations, threshold_days=threshold_days)
        compare_df = optional.compare_fast_slow(df, durations, threshold_days=threshold_days)
        hist_data = optional.duration_histogram(durations, bins=20, threshold_days=threshold_days)
        return results, compare_df, hist_data

    def _on_opt_finished(self, payload: tuple[list[AnalysisResult], pd.DataFrame, dict]) -> None:
        self._running_opt = False
        self.btn_run_opt.setEnabled(self._df is not None and not self._df.empty)
        results, compare_df, hist_data = payload
        self._results_opt = {r.code: r for r in results}

        fast = self._results_opt.get("OPT.fast")
        slow = self._results_opt.get("OPT.slow")
        if fast is not None:
            pct = f"{fast.percentage:.2f}%" if fast.percentage is not None else "—"
            cyc = f"{fast.mean_cycle_days:.2f} hari" if fast.mean_cycle_days is not None else "—"
            self.card_fast.set_values(
                f"{fast.n_cases} case ({pct})",
                f"{fast.n_cases} / {fast.denominator} × 100% · Mean: {cyc}",
            )
        if slow is not None:
            pct = f"{slow.percentage:.2f}%" if slow.percentage is not None else "—"
            cyc = f"{slow.mean_cycle_days:.2f} hari" if slow.mean_cycle_days is not None else "—"
            self.card_slow.set_values(
                f"{slow.n_cases} case ({pct})",
                f"{slow.n_cases} / {slow.denominator} × 100% · Mean: {cyc}",
            )

        self.compare_model.set_frame(compare_df)
        self._render_histogram(hist_data)
        self._refresh_opt_case_table()
        self.lbl_opt_status.setText("Selesai menjalankan Fast vs Slow & histogram durasi.")
        self.results_ready.emit(results)

    def _on_opt_error(self, message: str, details: str) -> None:
        self._running_opt = False
        self.btn_run_opt.setEnabled(self._df is not None and not self._df.empty)
        self.lbl_opt_status.setText(f"Gagal: {message}")
        self._show_error("Error Fitur Opsional", message, details)

    def _refresh_opt_case_table(self) -> None:
        code = str(self.cmb_opt_group.currentData() or "OPT.fast")
        res = self._results_opt.get(code)
        if res is None:
            self.opt_case_model.set_frame(pd.DataFrame())
            self.btn_open_opt_case.setEnabled(False)
            return
        self.opt_case_model.set_frame(res.per_case)
        self.btn_open_opt_case.setEnabled(not res.per_case.empty)

    def _on_opt_double_clicked(self, index: QModelIndex) -> None:
        if not index.isValid():
            return
        code = str(self.cmb_opt_group.currentData() or "OPT.fast")
        case_id = str(self.opt_case_model.raw(index.row(), 0))
        self._emit_open_case(case_id, code)

    def _open_selected_opt_case(self) -> None:
        code = str(self.cmb_opt_group.currentData() or "OPT.fast")
        sel = self.opt_case_table.selectionModel().selectedRows()
        if sel:
            case_id = str(self.opt_case_model.raw(sel[0].row(), 0))
        elif self.opt_case_model.rowCount() > 0:
            case_id = str(self.opt_case_model.raw(0, 0))
        else:
            return
        self._emit_open_case(case_id, code)

    # ======================================================= Histogram Matplotlib =========
    def _draw_empty_histogram(self, message: str) -> None:
        self.hist_fig.clear()
        ax = self.hist_fig.add_subplot(111)
        ax.text(0.5, 0.5, message, ha="center", va="center", color="gray", wrap=True)
        ax.set_axis_off()
        self.hist_canvas.draw_idle()

    def _render_histogram(self, hist_data: dict) -> None:
        counts = hist_data["counts"]
        edges = hist_data["bin_edges"]
        threshold = hist_data["threshold_days"]

        self.hist_fig.clear()
        ax = self.hist_fig.add_subplot(111)

        if len(counts) == 0:
            ax.text(0.5, 0.5, "Tidak ada data durasi.", ha="center", va="center", color="gray")
            ax.set_axis_off()
            self.hist_canvas.draw_idle()
            return

        starts = edges[:-1]
        widths = np.diff(edges)
        midpoints = starts + widths / 2.0
        colors = ["#26a69a" if m < threshold else "#ef5350" for m in midpoints]

        ax.bar(starts, counts, width=widths, align="edge", color=colors, edgecolor="white", alpha=0.9)
        ax.axvline(
            threshold,
            color="#37474f",
            linestyle="--",
            linewidth=1.6,
            label=f"Ambang {threshold:g} hari",
        )
        ax.set_title(
            f"Distribusi Durasi Case — Fast: {hist_data['n_fast']} | Slow: {hist_data['n_slow']}",
            fontsize=10,
        )
        ax.set_xlabel("Durasi Case (hari)")
        ax.set_ylabel("Jumlah Case")
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(True, axis="y", linestyle=":", alpha=0.5)
        self.hist_fig.tight_layout()
        self.hist_canvas.draw_idle()
