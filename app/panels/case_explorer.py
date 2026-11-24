"""Case Explorer (F07): tabel case (semua atau hasil analisis tertentu), pencarian ID,
rincian event (event_pos, timestamp, activity, lifecycle, resource) dengan highlight baris
yang ada di ``AnalysisResult.evidence`` (dicocokkan lewat ``orig_idx``).

Pemilik: Anggota E (feat/e-shell-explorer).

Juga berisi ``DataFrameModel`` (model tabel Qt berbasis DataFrame) yang dipakai MainWindow.
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
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
from core.result import AnalysisResult
from core.schema import DURATION_NAME

ALL_CASES = "__all__"
EVENT_COLUMNS = ["event_pos", "timestamp", "activity", "lifecycle", "resource"]
EVIDENCE_COLUMN = "bukti_untuk"
HIGHLIGHT_BG = QColor(255, 224, 130)
HIGHLIGHT_FG = QColor(0, 0, 0)


def _is_missing(value: Any) -> bool:
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def format_cell(value: Any, decimals: int = 3, na_text: str = "") -> str:
    """Format nilai untuk tampilan tabel (tidak mengubah data)."""
    if isinstance(value, (list, tuple)):
        return ", ".join(map(str, value))
    if _is_missing(value):
        return na_text
    if isinstance(value, pd.Timestamp):
        return value.isoformat(sep=" ", timespec="milliseconds")
    if isinstance(value, (float, np.floating)):
        return f"{value:.{decimals}f}"
    return str(value)


class DataFrameModel(QAbstractTableModel):
    """Model tabel read-only di atas DataFrame, dengan dukungan highlight baris.

    ``Qt.UserRole`` mengembalikan nilai mentah (dipakai untuk sorting).
    """

    def __init__(
        self,
        df: Optional[pd.DataFrame] = None,
        headers: Optional[dict[str, str]] = None,
        na_text: Optional[dict[str, str]] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._headers = headers or {}
        self._na_text = na_text or {}
        self._columns: list[str] = []
        self._values: list[np.ndarray] = []
        self._n_rows = 0
        self._highlight: set[int] = set()
        self._tooltips: dict[int, str] = {}
        self._sort: Optional[tuple[int, Qt.SortOrder]] = None
        self.set_frame(df if df is not None else pd.DataFrame())

    # --- data ---
    def set_frame(self, df: pd.DataFrame, highlight: Optional[set[int]] = None,
                  tooltips: Optional[dict[int, str]] = None) -> None:
        """Ganti isi tabel. Urutan sort terakhir (jika ada) diterapkan ulang."""
        df = df.reset_index(drop=True)
        highlight = set(highlight or ())
        tooltips = dict(tooltips or {})
        if self._sort is not None and self._sort[0] < len(df.columns) and len(df):
            df, highlight, tooltips = self._sorted(df, *self._sort, highlight, tooltips)
        self.beginResetModel()
        self._frame = df
        self._columns = list(df.columns)
        self._values = [df[c].to_numpy(dtype=object) for c in self._columns]
        self._n_rows = len(df)
        self._highlight = highlight
        self._tooltips = tooltips
        self.endResetModel()

    @staticmethod
    def _sorted(df: pd.DataFrame, column: int, order: Qt.SortOrder,
                highlight: set[int], tooltips: dict[int, str]):
        """Sort vektor dengan pandas (bukan perbandingan Python per baris)."""
        key = df.iloc[:, column]
        if key.map(lambda v: isinstance(v, (list, tuple))).any():
            key = key.map(format_cell)
        asc = order == Qt.SortOrder.AscendingOrder
        try:
            new_order = key.sort_values(kind="stable", ascending=asc, na_position="last").index
        except TypeError:
            new_order = key.astype(str).sort_values(kind="stable", ascending=asc).index
        old_to_new = {int(old): new for new, old in enumerate(new_order)}
        return (
            df.loc[new_order].reset_index(drop=True),
            {old_to_new[r] for r in highlight if r in old_to_new},
            {old_to_new[r]: t for r, t in tooltips.items() if r in old_to_new},
        )

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        """Dipanggil QTableView saat header diklik (setSortingEnabled)."""
        self._sort = (column, order)
        if self._n_rows and column < len(self._columns):
            self.set_frame(self._frame, self._highlight, self._tooltips)

    def frame(self) -> pd.DataFrame:
        return self._frame

    def highlighted_rows(self) -> set[int]:
        return set(self._highlight)

    def raw(self, row: int, col: int) -> Any:
        return self._values[col][row]

    # --- Qt API ---
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: B008
        return 0 if parent.isValid() else self._n_rows

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: B008
        return 0 if parent.isValid() else len(self._columns)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        row, col = index.row(), index.column()
        name = self._columns[col]
        value = self._values[col][row]
        if role == Qt.ItemDataRole.DisplayRole:
            return format_cell(value, na_text=self._na_text.get(name, ""))
        if role == Qt.ItemDataRole.UserRole:
            return value
        if row in self._highlight:
            if role == Qt.ItemDataRole.BackgroundRole:
                return QBrush(HIGHLIGHT_BG)
            if role == Qt.ItemDataRole.ForegroundRole:
                return QBrush(HIGHLIGHT_FG)
            if role == Qt.ItemDataRole.FontRole:
                font = QFont()
                font.setBold(True)
                return font
        if role == Qt.ItemDataRole.ToolTipRole and row in self._tooltips:
            return self._tooltips[row]
        return None

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal and 0 <= section < len(self._columns):
            name = self._columns[section]
            return self._headers.get(name, name)
        if orientation == Qt.Orientation.Vertical:
            return str(section + 1)
        return None


class CaseExplorer(BasePanel):
    """Penelusuran case dan event bukti. Pemilik: Anggota E."""

    title = "Case Explorer"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._df: Optional[pd.DataFrame] = None
        self._all_cases = pd.DataFrame(columns=["case_id", "n_events", DURATION_NAME])
        self._durations_by_case = pd.Series(dtype="float64")
        self._case_rows: dict[str, np.ndarray] = {}
        self._results: dict[str, AnalysisResult] = {}
        self._case_sets: dict[str, set[str]] = {}
        self._evidence_idx: dict[str, np.ndarray] = {}
        self._current_case: Optional[str] = None
        self._focus_code: Optional[str] = None
        self._build_ui()

    # --- UI ------------------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.source_combo = QComboBox()
        self.source_combo.setMinimumWidth(260)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Cari case ID…")
        self.search_edit.setClearButtonEnabled(True)
        self.count_label = QLabel()

        top = QHBoxLayout()
        top.addWidget(QLabel("Sumber:"))
        top.addWidget(self.source_combo)
        top.addSpacing(12)
        top.addWidget(QLabel("Cari ID:"))
        top.addWidget(self.search_edit, 1)
        top.addWidget(self.count_label)

        self.case_model = DataFrameModel(
            headers={"case_id": "Case ID", "n_events": "Jumlah event",
                     DURATION_NAME: "Durasi (hari)"},
        )
        self.case_view = QTableView()
        self.case_view.setModel(self.case_model)
        self.case_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.case_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        header = self.case_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        self.case_view.verticalHeader().setVisible(False)
        self.case_view.setSortingEnabled(True)  # memanggil DataFrameModel.sort
        self.case_view.sortByColumn(0, Qt.SortOrder.AscendingOrder)

        self.case_header = QLabel("Pilih case di kiri untuk melihat urutan event.")
        self.case_header.setWordWrap(True)
        self.membership_label = QLabel()
        self.membership_label.setWordWrap(True)
        self.event_model = DataFrameModel(
            headers={"event_pos": "Pos", "timestamp": "Timestamp (UTC)",
                     "activity": "Activity", "lifecycle": "Lifecycle",
                     "resource": "Resource", EVIDENCE_COLUMN: "Bukti untuk"},
            na_text={"resource": "(kosong)", "lifecycle": "(tidak ada)"},
        )
        self.event_view = QTableView()
        self.event_view.setModel(self.event_model)
        self.event_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.event_view.verticalHeader().setVisible(False)
        self.event_view.horizontalHeader().setStretchLastSection(True)
        legend = QLabel("Baris disorot = event yang menjadi bukti (evidence) hasil analisis.")
        legend.setStyleSheet("color: palette(mid);")

        right = QWidget()
        rlay = QVBoxLayout(right)
        rlay.setContentsMargins(0, 0, 0, 0)
        rlay.addWidget(self.case_header)
        rlay.addWidget(self.membership_label)
        rlay.addWidget(self.event_view, 1)
        rlay.addWidget(legend)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.case_view)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)
        splitter.setSizes([450, 850])

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(splitter, 1)

        self.search_edit.textChanged.connect(self._on_search)
        self.source_combo.currentIndexChanged.connect(self._refresh_case_table)
        self.case_view.selectionModel().currentRowChanged.connect(self._on_case_selected)
        self._rebuild_source_combo()

    # --- Kontrak panel -------------------------------------------------------------------
    def set_log(self, df: pd.DataFrame, durations: pd.Series) -> None:
        """Simpan log aktif dan bangun indeks posisi event per case (sekali per impor)."""
        self._df = df
        self._case_rows = {str(k): v for k, v in df.groupby("case_id", sort=False).indices.items()}
        n_events = df["case_id"].value_counts()
        cases = pd.DataFrame({"case_id": n_events.index.astype(str),
                              "n_events": n_events.to_numpy(dtype="int64")})
        dur = durations.copy()
        dur.index = dur.index.astype(str)
        cases[DURATION_NAME] = cases["case_id"].map(dur)
        self._all_cases = cases.sort_values("case_id", kind="stable").reset_index(drop=True)
        self._durations_by_case = self._all_cases.set_index("case_id")[DURATION_NAME]
        self.set_results([])
        self._clear_details("Log dimuat. Pilih case di kiri untuk melihat urutan event.")

    def reset(self) -> None:
        self.set_results([])
        self._clear_details("Hasil analisis di-reset.")

    # --- Hasil analisis ------------------------------------------------------------------
    def set_results(self, results: list[AnalysisResult]) -> None:
        """Simpan hasil analisis terakhir (untuk sumber daftar case & highlight evidence)."""
        self._results = {r.code: r for r in results}
        self._case_sets = {r.code: {str(c) for c in r.case_ids} for r in results}
        self._evidence_idx = {}
        for r in results:
            ev = r.evidence
            if ev is not None and not ev.empty and "orig_idx" in ev.columns:
                self._evidence_idx[r.code] = np.unique(ev["orig_idx"].to_numpy(dtype="int64"))
        self._rebuild_source_combo()
        if self._current_case is not None:
            self._render_case(self._current_case)

    def results(self) -> list[AnalysisResult]:
        return list(self._results.values())

    def select_source(self, code: str) -> None:
        """Tampilkan hanya case milik hasil ``code`` (atau semua case jika tidak dikenal)."""
        idx = self.source_combo.findData(code)
        self.source_combo.setCurrentIndex(idx if idx >= 0 else 0)

    def current_source(self) -> str:
        return self.source_combo.currentData() or ALL_CASES

    # --- Slot untuk sinyal open_case -----------------------------------------------------
    def show_case(self, case_id: str, result: Optional[AnalysisResult] = None) -> None:
        """Tampilkan rincian ``case_id``; jika ``result`` diberikan, highlight bukti hasil itu."""
        case_id = str(case_id)
        if self._df is None:
            self._clear_details("Belum ada log yang dimuat.")
            return
        if case_id not in self._case_rows:
            self._clear_details(f"Case <b>{case_id}</b> tidak ditemukan di log aktif.")
            return
        source = self.current_source()
        if source != ALL_CASES and case_id not in self._case_sets.get(source, set()):
            self.select_source(ALL_CASES)
        if self.search_edit.text() and self.search_edit.text().lower() not in case_id.lower():
            self.search_edit.clear()
        self._focus_code = result.code if result is not None else None
        self._select_case_row(case_id)
        self._render_case(case_id)

    # --- Internal ------------------------------------------------------------------------
    def _rebuild_source_combo(self) -> None:
        previous = self.source_combo.currentData()
        self.source_combo.blockSignals(True)
        self.source_combo.clear()
        self.source_combo.addItem(f"Semua case ({len(self._all_cases)})", ALL_CASES)
        for code, r in self._results.items():
            self.source_combo.addItem(f"{code} — {r.title} ({r.n_cases} case)", code)
        idx = self.source_combo.findData(previous) if previous else 0
        self.source_combo.setCurrentIndex(max(idx, 0))
        self.source_combo.blockSignals(False)
        self._refresh_case_table()

    def _source_frame(self) -> pd.DataFrame:
        source = self.current_source()
        if source == ALL_CASES or source not in self._results:
            return self._all_cases
        ids = [str(c) for c in self._results[source].case_ids]
        return self._all_cases.set_index("case_id").reindex(ids).rename_axis("case_id").reset_index()

    def _refresh_case_table(self) -> None:
        """Isi tabel case = sumber terpilih, difilter teks pencarian (vektor pandas)."""
        base = self._source_frame()
        text = self.search_edit.text().strip()
        frame = base
        if text and len(base):
            mask = base["case_id"].astype(str).str.contains(text, case=False, regex=False)
            frame = base[mask.to_numpy()]
        self.case_model.set_frame(frame)
        self.count_label.setText(f"{len(frame)} / {len(base)} case")

    def _on_search(self, _text: str) -> None:
        self._refresh_case_table()

    def _on_case_selected(self, current: QModelIndex, _previous: QModelIndex) -> None:
        if not current.isValid():
            return
        case_id = str(self.case_model.raw(current.row(), 0))
        if case_id != self._current_case:
            self._focus_code = None
        self._render_case(case_id)

    def _select_case_row(self, case_id: str) -> None:
        frame = self.case_model.frame()
        hits = np.flatnonzero(frame["case_id"].astype(str).to_numpy() == case_id) if len(frame) else []
        if len(hits) == 0:
            return
        idx = self.case_model.index(int(hits[0]), 0)
        sel = self.case_view.selectionModel()
        sel.blockSignals(True)
        self.case_view.setCurrentIndex(idx)
        sel.blockSignals(False)
        self.case_view.scrollTo(idx)

    def _evidence_codes(self, orig_idx: np.ndarray) -> list[list[str]]:
        """Untuk tiap orig_idx, daftar kode hasil yang memuatnya sebagai evidence."""
        codes: list[list[str]] = [[] for _ in range(len(orig_idx))]
        for code, arr in self._evidence_idx.items():
            if len(arr) == 0:
                continue
            pos = np.searchsorted(arr, orig_idx)
            hit = arr[np.minimum(pos, len(arr) - 1)] == orig_idx
            for i in np.flatnonzero(hit):
                codes[i].append(code)
        return codes

    def _render_case(self, case_id: str) -> None:
        assert self._df is not None
        self._current_case = case_id
        events = self._df.iloc[self._case_rows[case_id]]
        orig = events["orig_idx"].to_numpy(dtype="int64")
        codes = self._evidence_codes(orig)
        table = events[EVENT_COLUMNS].reset_index(drop=True).copy()
        table[EVIDENCE_COLUMN] = codes
        focus = self._focus_code
        highlight = {i for i, c in enumerate(codes) if (focus in c if focus else c)}
        tips = {i: "Bukti untuk: " + ", ".join(c) for i, c in enumerate(codes) if c}
        self.event_model.set_frame(table, highlight=highlight, tooltips=tips)
        self.event_view.resizeColumnsToContents()

        duration = self._durations_by_case.get(case_id)
        dur_txt = "-" if _is_missing(duration) else f"{duration:.3f} hari"
        self.case_header.setText(
            f"<b>Case {case_id}</b> — {len(events)} event, durasi {dur_txt}"
        )
        member = [code for code, s in self._case_sets.items() if case_id in s]
        focus_txt = f" · disorot: bukti <b>{focus}</b>" if focus else ""
        self.membership_label.setText(
            ("Termasuk hasil: " + ", ".join(member) if member else "Tidak termasuk hasil analisis mana pun.")
            + focus_txt
        )

    def _clear_details(self, message: str) -> None:
        self._current_case = None
        self._focus_code = None
        self.event_model.set_frame(pd.DataFrame(columns=[*EVENT_COLUMNS, EVIDENCE_COLUMN]))
        self.case_header.setText(message)
        self.membership_label.setText("")
