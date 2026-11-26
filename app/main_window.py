"""Jendela utama aplikasi.

Pemilik: Anggota E (feat/e-shell-explorer).

Alur wajib (Instruksi Bagian 6): Impor XES -> Overview -> pilih latihan (sidebar) ->
jalankan -> lihat jawaban -> periksa case -> ekspor. Status bar + progress bar + dialog error.

Tanggung jawab MainWindow:
    * memuat XES di worker: ``core.loader.load_xes`` -> ``(df, LoadedLog)`` lalu
      ``core.durations.compute_case_durations``;
    * memanggil ``panel.set_log(df, durations)`` lalu ``panel.set_loaded(loaded)`` (kontrak v2)
      pada setiap panel setelah log dimuat;
    * ``panel.open_case_for(case_id, code)`` -> ``CaseExplorer.show_case_for`` (bukti hasil
      ``code`` disorot); ``panel.open_case(case_id)`` (v1) tetap didukung;
    * ``panel.results_ready`` -> tabel "Hasil & Ekspor", Case Explorer, dan ekspor CSV;
    * Re-run per analisis memakai ``run(df, durations, **result.params)`` (kontrak v2), Jalankan
      semua, Reset hasil, dan Muat ulang file tanpa dialog.

Panel milik anggota lain yang belum selesai (masih ``NotImplementedError``) diganti
placeholder sehingga aplikasi tetap bisa dibuka.
"""

from __future__ import annotations

import importlib
from functools import partial
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.panels.base import BasePanel
from app.panels.case_explorer import CaseExplorer, DataFrameModel
from app.theme import apply_theme
from app.worker import run_in_background
from core.loaded_log import LoadedLog
from core.result import AnalysisResult
from export import csv_export

APP_TITLE = "BPIC17 Event Log Analyzer"

#: (modul, kelas, judul sidebar, pemilik) — urutan = urutan alur kerja.
PANEL_SPECS: list[tuple[str, str, str, str]] = [
    ("app.panels.dataset_panel", "DatasetPanel", "Impor Dataset", "A"),
    ("app.panels.overview_panel", "OverviewPanel", "Ringkasan Log", "A"),
    ("app.panels.ex117_panel", "Ex117Panel", "11.7 · Status Aplikasi", "B"),
    ("app.panels.ex1115_1118_panel", "Ex1115_1118Panel", "11.15 & 11.18 · Cek Fraud Berulang", "C"),
    ("app.panels.ex1122_panel", "Ex1122Panel", "11.22 · Batal lalu Diterima", "D"),
]

#: Modul analisis dalam urutan "Jalankan semua".
ANALYSIS_MODULES: list[str] = [
    "analyses.ex_11_7", "analyses.ex_11_15_18", "analyses.ex_11_22", "analyses.optional",
]


def module_for_code(code: str) -> Optional[str]:
    """Modul analisis yang menghasilkan ``code`` (untuk tombol Re-run)."""
    if code.startswith("11.7"):
        return "analyses.ex_11_7"
    if code in ("11.15", "11.18"):
        return "analyses.ex_11_15_18"
    if code.startswith("11.22"):
        return "analyses.ex_11_22"
    if code.startswith("OPT"):
        return "analyses.optional"
    return None


def _as_list(results: Any) -> list[AnalysisResult]:
    if isinstance(results, AnalysisResult):
        return [results]
    return [r for r in (results or []) if isinstance(r, AnalysisResult)]


def _load_pipeline(path: str, progress: Callable[[int, str], None]):
    """Dijalankan di worker: impor XES lalu hitung durasi seluruh case."""
    from core.durations import compute_case_durations
    from core.loader import load_xes

    progress(0, "Membaca file XES…")
    df, loaded = load_xes(path, progress=progress)
    progress(95, "Menghitung durasi case…")
    durations = compute_case_durations(df)
    progress(100, "Selesai")
    return df, loaded, durations


def _run_analysis(module_name: str, df: pd.DataFrame, durations: pd.Series,
                  params: Optional[dict[str, Any]] = None) -> list[AnalysisResult]:
    """Dijalankan di worker: ``run(df, durations, **params)``; params kosong = default modul."""
    module = importlib.import_module(module_name)
    return _as_list(module.run(df, durations, **(params or {})))


class PlaceholderPanel(BasePanel):
    """Pengganti panel anggota lain yang belum diimplementasikan."""

    def __init__(self, title: str, owner: str, reason: str, parent=None) -> None:
        super().__init__(parent)
        self.title = title
        label = QLabel(
            f"<h3>{title}</h3><p>Panel ini belum tersedia (milik Anggota {owner}).</p>"
            f"<p style='color:gray'>{reason}</p>"
        )
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.addWidget(label)

    def set_log(self, df: pd.DataFrame, durations: pd.Series) -> None:
        pass


class MainWindow(QMainWindow):
    """Shell aplikasi. Pemilik: Anggota E."""

    def __init__(self) -> None:
        super().__init__()
        apply_theme(QApplication.instance())
        self.setWindowTitle(APP_TITLE)
        self.resize(1320, 820)
        self._df: Optional[pd.DataFrame] = None
        self._durations: Optional[pd.Series] = None
        self._source: Optional[str] = None
        self._path: Optional[Path] = None
        self._loaded: Optional[LoadedLog] = None
        self._results: dict[str, AnalysisResult] = {}
        self._panel_codes: dict[int, list[str]] = {}
        self._tasks = 0
        self._loading = False
        self.panels: list[BasePanel] = []

        self._build_actions()
        self._build_ui()
        self._build_statusbar()
        self._update_actions()

    # ==================================================================== UI =========
    def _build_actions(self) -> None:
        self.act_open = QAction("&Buka XES…", self, shortcut=QKeySequence.StandardKey.Open)
        self.act_open.triggered.connect(self.open_xes_dialog)
        self.act_reload = QAction("&Muat ulang file", self, shortcut=QKeySequence("Ctrl+R"))
        self.act_reload.triggered.connect(self.reload_file)
        self.act_run_all = QAction("&Jalankan semua analisis", self, shortcut=QKeySequence("F5"))
        self.act_run_all.triggered.connect(self.run_all)
        self.act_reset = QAction("&Reset hasil", self)
        self.act_reset.triggered.connect(self.reset_results)
        self.act_export_all = QAction("&Ekspor semua CSV ke folder…", self,
                                      shortcut=QKeySequence("Ctrl+E"))
        self.act_export_all.triggered.connect(self.export_all_dialog)
        self.act_quit = QAction("&Keluar", self, shortcut=QKeySequence.StandardKey.Quit)
        self.act_quit.triggered.connect(self.close)
        self.act_about = QAction("&Tentang aplikasi", self)
        self.act_about.triggered.connect(self.show_about)

        bar = self.menuBar()
        m_file = bar.addMenu("&File")
        for act in (self.act_open, self.act_reload, None, self.act_export_all, None, self.act_quit):
            m_file.addSeparator() if act is None else m_file.addAction(act)
        m_an = bar.addMenu("&Analisis")
        m_an.addAction(self.act_run_all)
        m_an.addAction(self.act_reset)
        bar.addMenu("Ban&tuan").addAction(self.act_about)

        tb = self.addToolBar("Utama")
        tb.setMovable(False)
        for act in (self.act_open, self.act_run_all, self.act_reset, self.act_export_all):
            tb.addAction(act)

    def _build_ui(self) -> None:
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sidebar.setMinimumWidth(240)
        self.sidebar.setMaximumWidth(260)
        self.stack = QStackedWidget()

        for modname, clsname, title, owner in PANEL_SPECS:
            self._add_page(self._make_panel(modname, clsname, title, owner), title)

        self.explorer = CaseExplorer()
        self._add_page(self.explorer, self.explorer.title)
        self.results_page = self._build_results_page()
        self.sidebar.addItem("Hasil & Ekspor")
        self.stack.addWidget(self.results_page)

        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.sidebar.setCurrentRow(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.sidebar)
        splitter.addWidget(self.stack)
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)

    def _make_panel(self, modname: str, clsname: str, title: str, owner: str) -> BasePanel:
        try:
            cls = getattr(importlib.import_module(modname), clsname)
            panel = cls()
        except NotImplementedError as exc:
            return PlaceholderPanel(title, owner, f"Belum diimplementasikan: {exc}")
        except Exception as exc:  # panel rusak tidak boleh menjatuhkan aplikasi
            return PlaceholderPanel(title, owner, f"Gagal dibuat: {type(exc).__name__}: {exc}")
        if not panel.title:
            panel.title = title
        return panel

    def _add_page(self, panel: BasePanel, title: str) -> None:
        if panel.layout() is not None:
            panel.layout().setContentsMargins(16, 12, 16, 12)
            panel.layout().setSpacing(12)
        self.panels.append(panel)
        self.sidebar.addItem(title)
        self.stack.addWidget(panel)
        if panel is not getattr(self, "explorer", None):
            panel.open_case.connect(partial(self._on_open_case, panel))
            panel.open_case_for.connect(self._on_open_case_for)
            panel.results_ready.connect(partial(self._on_panel_results, panel))

    def _build_results_page(self) -> QWidget:
        page = QWidget()
        self.results_model = DataFrameModel(headers={
            "code": "Kode", "title": "Judul", "rule_text": "Aturan filter",
            "n_cases": "Jumlah case", "denominator": "Denominator",
            "percentage": "Persentase (%)", "mean_cycle_days": "Rata-rata cycle time (hari)",
        })
        self.results_view = QTableView()
        self.results_view.setModel(self.results_model)
        self.results_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_view.verticalHeader().setVisible(False)
        self.results_view.setWordWrap(True)
        self.results_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.results_view.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.results_view.doubleClicked.connect(self._on_result_double_clicked)

        self.btn_rerun = QPushButton("Re-run analisis terpilih")
        self.btn_rerun.clicked.connect(self.rerun_selected)
        self.btn_open = QPushButton("Buka case di Case Explorer")
        self.btn_open.clicked.connect(self._open_selected_in_explorer)
        self.btn_run_all = QPushButton("Jalankan semua")
        self.btn_run_all.setProperty("variant", "primary")
        self.btn_run_all.clicked.connect(self.run_all)
        self.btn_reset = QPushButton("Reset hasil")
        self.btn_reset.clicked.connect(self.reset_results)
        self.btn_exp_summary = QPushButton("Simpan ringkasan CSV…")
        self.btn_exp_summary.clicked.connect(partial(self.export_dialog, "ringkasan"))
        self.btn_exp_cases = QPushButton("Simpan daftar case CSV…")
        self.btn_exp_cases.clicked.connect(partial(self.export_dialog, "daftar_case"))
        self.btn_exp_evidence = QPushButton("Simpan evidence CSV…")
        self.btn_exp_evidence.clicked.connect(partial(self.export_dialog, "evidence"))

        row1 = QHBoxLayout()
        for b in (self.btn_rerun, self.btn_open, self.btn_run_all, self.btn_reset):
            row1.addWidget(b)
        row1.addStretch(1)
        row2 = QHBoxLayout()
        for b in (self.btn_exp_summary, self.btn_exp_cases, self.btn_exp_evidence):
            row2.addWidget(b)
        row2.addStretch(1)

        info = QLabel("Semua angka dihitung dari log aktif. Klik dua kali baris untuk melihat "
                      "daftar case hasil tersebut di Case Explorer.")
        info.setWordWrap(True)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        layout.addWidget(QLabel("<h3>Hasil analisis & ekspor</h3>"))
        layout.addWidget(info)
        layout.addWidget(self.results_view, 1)
        layout.addLayout(row1)
        layout.addLayout(row2)
        return page

    def _build_statusbar(self) -> None:
        self.log_label = QLabel("Belum ada log dimuat")
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(220)
        self.progress.setTextVisible(True)
        self.progress.hide()
        sb = self.statusBar()
        sb.addPermanentWidget(self.log_label)
        sb.addPermanentWidget(self.progress)
        sb.showMessage("Buka file XES lewat File → Buka XES… (Ctrl+O)")

    # ============================================================ Status & error =====
    def _start_busy(self, message: str) -> None:
        self._tasks += 1
        self.progress.setRange(0, 0)  # mode sibuk sampai ada progress nyata
        self.progress.show()
        self.statusBar().showMessage(message)
        self._update_actions()

    def _end_busy(self) -> None:
        self._tasks = max(0, self._tasks - 1)
        if self._tasks == 0:
            self.progress.hide()
            self.progress.setRange(0, 100)
        self._update_actions()

    def _on_progress(self, percent: int, message: str) -> None:
        self.progress.setRange(0, 100)
        self.progress.setValue(percent)
        if message:
            self.statusBar().showMessage(message)

    def _show_error(self, title: str, message: str, details: str = "") -> None:
        """Dialog error (di-override/monkeypatch di test)."""
        box = QMessageBox(QMessageBox.Icon.Critical, title, message, parent=self)
        if details:
            box.setDetailedText(details)
        box.exec()

    def _show_info(self, title: str, message: str) -> None:
        QMessageBox.information(self, title, message)

    def _report_error(self, title: str, message: str, details: str, quiet_not_impl: bool = False) -> None:
        if message.startswith("NotImplementedError"):
            self.statusBar().showMessage(f"Belum tersedia — {message}", 10000)
            if quiet_not_impl:
                return
            message = "Fitur ini belum diimplementasikan oleh pemilik modulnya.\n\n" + message
        else:
            self.statusBar().showMessage(f"Gagal — {message}", 10000)
        self._show_error(title, message, details)

    def _update_actions(self) -> None:
        has_log = self._df is not None
        has_results = bool(self._results)
        self.act_open.setEnabled(not self._loading)
        self.act_reload.setEnabled(self._path is not None and not self._loading)
        for w in (self.act_run_all, self.btn_run_all, self.btn_rerun):
            w.setEnabled(has_log and not self._loading)
        for w in (self.act_reset, self.btn_reset, self.btn_open, self.act_export_all,
                  self.btn_exp_summary, self.btn_exp_cases, self.btn_exp_evidence):
            w.setEnabled(has_results)

    # ================================================================ Impor log =====
    def open_xes_dialog(self) -> None:
        start = str(self._path.parent if self._path else Path.cwd() / "data")
        path, _ = QFileDialog.getOpenFileName(
            self, "Buka event log XES", start, "Event log XES (*.xes *.xes.gz);;Semua file (*)"
        )
        if path:
            self.load_xes_file(path)

    def reload_file(self) -> None:
        """Impor ulang file terakhir (uji reproduktibilitas) tanpa dialog."""
        if self._path is not None:
            self.load_xes_file(self._path)

    def load_xes_file(self, path: str | Path) -> None:
        if self._loading:
            return
        path = Path(path)
        self._loading = True
        self._start_busy(f"Memuat {path.name}…")
        run_in_background(
            _load_pipeline, str(path),
            on_progress=self._on_progress,
            on_finished=partial(self._on_loaded, path),
            on_error=self._on_load_error,
        )

    def _on_loaded(self, path: Path, payload: Any) -> None:
        self._loading = False
        self._end_busy()
        df, loaded, durations = payload
        self._path = path
        self.set_log(df, durations, source=path.name, loaded=loaded)
        if loaded.warnings:
            self._show_info("Peringatan impor", "\n".join(loaded.warnings))

    def _on_load_error(self, message: str, details: str) -> None:
        self._loading = False
        self._end_busy()
        self._report_error("Gagal memuat XES", message, details)

    def set_log(self, df: pd.DataFrame, durations: pd.Series, source: str = "",
                loaded: Optional[LoadedLog] = None) -> None:
        """Pasang log aktif ke semua panel (dipakai setelah impor dan oleh mode demo).

        Urutan per panel: ``set_log(df, durations)`` lalu, jika ada, ``set_loaded(loaded)``.
        """
        self._df, self._durations, self._source = df, durations, source
        self._loaded = loaded
        self._results.clear()
        self._panel_codes.clear()
        n_cases, n_events = int(df["case_id"].nunique()), len(df)
        for panel in self.panels:
            self._safe_panel_call(panel, "set_log", df, durations)
        if loaded is not None:
            for panel in self.panels:
                self._safe_panel_call(panel, "set_loaded", loaded)
        self._refresh_results()
        self.log_label.setText(f"{source} · {n_cases} case · {n_events} event")
        self.setWindowTitle(f"{APP_TITLE} — {source}" if source else APP_TITLE)
        self.statusBar().showMessage(f"Log dimuat: {n_cases} case, {n_events} event", 8000)
        self._update_actions()
        if self.sidebar.currentRow() == 0:
            self.sidebar.setCurrentRow(1)  # lanjut ke Overview

    def _safe_panel_call(self, panel: BasePanel, method: str, *args: Any) -> None:
        try:
            getattr(panel, method)(*args)
        except NotImplementedError as exc:
            self.statusBar().showMessage(f"{panel.title}: belum diimplementasikan ({exc})", 8000)
        except Exception as exc:
            import traceback

            self._show_error(f"Error di panel {panel.title}", f"{type(exc).__name__}: {exc}",
                             traceback.format_exc())

    # ================================================================== Hasil ========
    def add_results(self, results: AnalysisResult | Iterable[AnalysisResult]) -> list[str]:
        """Simpan/menimpa hasil berdasarkan ``code``. Mengembalikan kode yang diperbarui."""
        items = _as_list(results)
        for r in items:
            self._results[r.code] = r
        self._refresh_results()
        return [r.code for r in items]

    def results(self) -> list[AnalysisResult]:
        return list(self._results.values())

    def reset_results(self) -> None:
        """Kosongkan semua hasil tanpa membuka ulang file."""
        self._results.clear()
        self._panel_codes.clear()
        for panel in self.panels:
            if panel is not self.explorer:
                self._safe_panel_call(panel, "reset")
        self._refresh_results()
        self.statusBar().showMessage("Hasil analisis di-reset (log tetap dimuat).", 6000)

    def _refresh_results(self) -> None:
        results = self.results()
        self.results_model.set_frame(csv_export.summary_frame(results))
        self.results_view.resizeRowsToContents()
        self.explorer.set_results(results)
        self._update_actions()

    def _on_panel_results(self, panel: BasePanel, results: Any) -> None:
        codes = self.add_results(results)
        self._panel_codes[id(panel)] = codes

    def _on_open_case(self, panel: BasePanel, case_id: str) -> None:
        """Buka case dari panel; highlight bukti hasil panel itu yang PALING spesifik.

        Sinyal open_case hanya membawa case_id, jadi dipilih hasil milik panel pengirim
        dengan jumlah case paling sedikit yang memuat case tersebut (mis. 11.7E, bukan
        11.7A yang memuat semua case). Kolom "Bukti untuk" tetap menampilkan semua kode.
        """
        case_id = str(case_id)
        candidates = [
            r for code in self._panel_codes.get(id(panel), [])
            if (r := self._results.get(code)) is not None and case_id in {str(c) for c in r.case_ids}
        ]
        focus = min(candidates, key=lambda r: r.n_cases) if candidates else None
        self.explorer.show_case(case_id, focus)
        self.sidebar.setCurrentRow(self.stack.indexOf(self.explorer))

    def _on_open_case_for(self, case_id: str, code: str) -> None:
        """Kontrak v2: panel menyebut kode hasil secara eksplisit, jadi tidak perlu menebak."""
        self.explorer.show_case_for(str(case_id), str(code))
        self.sidebar.setCurrentRow(self.stack.indexOf(self.explorer))

    def _selected_codes(self) -> list[str]:
        rows = sorted({i.row() for i in self.results_view.selectionModel().selectedRows()})
        frame = self.results_model.frame()
        return [str(frame.iloc[r]["code"]) for r in rows]

    def _on_result_double_clicked(self, index) -> None:
        code = str(self.results_model.frame().iloc[index.row()]["code"])
        self.explorer.select_source(code)
        self.sidebar.setCurrentRow(self.stack.indexOf(self.explorer))

    def _open_selected_in_explorer(self) -> None:
        codes = self._selected_codes()
        if codes:
            self.explorer.select_source(codes[0])
            self.sidebar.setCurrentRow(self.stack.indexOf(self.explorer))

    # ======================================================== Jalankan / Re-run =====
    def rerun_selected(self) -> None:
        codes = self._selected_codes()
        if not codes:
            self._show_info("Re-run", "Pilih minimal satu baris hasil terlebih dahulu.")
            return
        self.rerun_codes(codes)

    def rerun_codes(self, codes: Iterable[str]) -> None:
        """Jalankan ulang modul analisis untuk kode-kode tersebut dengan ``**result.params``.

        Kontrak v2: ``params`` berisi argumen efektif, sehingga re-run memberi hasil identik
        selama log sama. Satu modul dijalankan sekali walau beberapa kodenya dipilih.
        """
        modules: dict[str, dict[str, Any]] = {}
        for code in codes:
            mod = module_for_code(code)
            if mod and mod not in modules:
                r = self._results.get(code)
                modules[mod] = dict(r.params) if r is not None else {}
        for mod, params in modules.items():
            self._run_module(mod, quiet_not_impl=False, params=params)

    def run_all(self) -> None:
        """Jalankan semua modul; params hasil sebelumnya dipakai ulang bila ada.

        Modul yang belum siap (NotImplementedError) hanya dilaporkan di status bar.
        """
        for mod in ANALYSIS_MODULES:
            self._run_module(mod, quiet_not_impl=True, params=self._params_for_module(mod))

    def _params_for_module(self, module_name: str) -> dict[str, Any]:
        for code, r in self._results.items():
            if module_for_code(code) == module_name:
                return dict(r.params)
        return {}

    def _run_module(self, module_name: str, quiet_not_impl: bool,
                    params: Optional[dict[str, Any]] = None) -> None:
        if self._df is None or self._durations is None:
            self._show_info("Belum ada log", "Muat file XES terlebih dahulu.")
            return
        short = module_name.split(".")[-1]
        self._start_busy(f"Menjalankan {short}…")

        def done(results: Any) -> None:
            self._end_busy()
            codes = self.add_results(results)
            self.statusBar().showMessage(f"{short} selesai: {', '.join(codes) or '-'}", 6000)

        def failed(message: str, details: str) -> None:
            self._end_busy()
            self._report_error(f"Analisis {short} gagal", message, details, quiet_not_impl)

        run_in_background(_run_analysis, module_name, self._df, self._durations, params or {},
                          on_finished=done, on_error=failed)

    # ================================================================== Ekspor ========
    _EXPORTERS = {
        "ringkasan": csv_export.export_summary,
        "daftar_case": csv_export.export_case_lists,
        "evidence": csv_export.export_evidence,
    }

    def _default_export_dir(self) -> Path:
        return Path.cwd() / "exports"

    def export_dialog(self, kind: str) -> None:
        if not self._results:
            self._show_info("Ekspor", "Belum ada hasil analisis untuk diekspor.")
            return
        stamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        default = self._default_export_dir() / f"{kind}_{stamp}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "Simpan CSV", str(default), "CSV (*.csv)")
        if path:
            self.export_to(kind, path)

    def export_to(self, kind: str, path: str | Path) -> None:
        """Tulis satu jenis CSV di worker (evidence BPIC17 bisa besar)."""
        exporter = self._EXPORTERS[kind]
        self._start_busy(f"Menyimpan {kind}…")
        run_in_background(exporter, self.results(), str(path),
                          on_finished=self._on_exported, on_error=self._on_export_error)

    def export_all_dialog(self) -> None:
        if not self._results:
            self._show_info("Ekspor", "Belum ada hasil analisis untuk diekspor.")
            return
        directory = QFileDialog.getExistingDirectory(self, "Pilih folder ekspor",
                                                     str(self._default_export_dir()))
        if directory:
            self.export_all_to(directory)

    def export_all_to(self, directory: str | Path) -> None:
        self._start_busy("Menyimpan semua CSV…")
        run_in_background(csv_export.export_all, self.results(), str(directory),
                          on_finished=self._on_exported, on_error=self._on_export_error)

    def _on_exported(self, written: Any) -> None:
        self._end_busy()
        paths = list(written.values()) if isinstance(written, dict) else [written]
        self.statusBar().showMessage("Tersimpan: " + ", ".join(str(p) for p in paths), 10000)

    def _on_export_error(self, message: str, details: str) -> None:
        self._end_busy()
        self._report_error("Ekspor gagal", message, details)

    # ================================================================== Lainnya =======
    def show_about(self) -> None:
        try:
            from app.panels.about_dialog import AboutDialog

            AboutDialog(self).exec()
        except NotImplementedError:
            self._show_info("Tentang", f"{APP_TITLE}\n\nDialog About belum diimplementasikan (Anggota A).")
