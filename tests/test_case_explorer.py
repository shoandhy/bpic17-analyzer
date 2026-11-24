"""Test Case Explorer (Anggota E) dengan log sintetis dan hasil dummy."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt

from app.panels.case_explorer import ALL_CASES, CaseExplorer


@pytest.fixture
def explorer(qtbot, tiny_log, tiny_durs, dummy_results):
    w = CaseExplorer()
    qtbot.addWidget(w)
    w.set_log(tiny_log, tiny_durs)
    w.set_results(dummy_results)
    return w


def _result(results, code):
    return next(r for r in results if r.code == code)


def test_lists_all_cases_and_search(explorer):
    assert explorer.case_model.rowCount() == 6
    explorer.search_edit.setText("C5")  # tidak peka huruf besar/kecil
    assert explorer.case_model.frame()["case_id"].tolist() == ["c5"]
    assert explorer.count_label.text() == "1 / 6 case"


def test_case_table_sorted_ascending_and_by_number(explorer):
    assert explorer.case_model.frame()["case_id"].tolist() == ["c1", "c2", "c3", "c4", "c5", "c6"]
    explorer.case_view.sortByColumn(2, Qt.SortOrder.DescendingOrder)  # durasi, numerik
    durs = explorer.case_model.frame()["duration_days"].tolist()
    assert durs == sorted(durs, reverse=True)
    explorer.search_edit.setText("c")  # filter ulang tetap mempertahankan urutan
    assert explorer.case_model.frame()["duration_days"].tolist() == durs


def test_source_filters_case_list(explorer, dummy_results):
    explorer.select_source("11.18")
    assert explorer.case_model.frame()["case_id"].tolist() == _result(dummy_results, "11.18").case_ids
    explorer.select_source(ALL_CASES)
    assert explorer.case_model.rowCount() == 6


def test_show_case_lists_events_in_canonical_order(explorer, tiny_log):
    explorer.show_case("c6")
    frame = explorer.event_model.frame()
    expected = tiny_log[tiny_log["case_id"] == "c6"]
    assert frame["event_pos"].tolist() == expected["event_pos"].tolist()
    assert frame["activity"].tolist() == expected["activity"].tolist()


def test_highlight_matches_evidence_of_focused_result(explorer, dummy_results, tiny_log):
    r = _result(dummy_results, "11.7E")
    explorer.show_case("c6", r)
    events = tiny_log[tiny_log["case_id"] == "c6"].reset_index(drop=True)
    ev_idx = set(r.evidence.loc[r.evidence["case_id"] == "c6", "orig_idx"])
    expected_rows = set(events.index[events["orig_idx"].isin(ev_idx)])
    assert explorer.event_model.highlighted_rows() == expected_rows
    assert "11.7E" in explorer.membership_label.text()


def test_evidence_column_names_all_results(explorer, dummy_results):
    explorer.show_case("c6")
    tagged = [c for c in explorer.event_model.frame()["bukti_untuk"] if c]
    codes = {code for c in tagged for code in c}
    expected = {r.code for r in dummy_results if "c6" in r.case_ids}
    assert codes == expected


def test_show_case_switches_source_and_clears_search(explorer):
    explorer.select_source("11.18")          # hanya c6
    explorer.search_edit.setText("c6")
    explorer.show_case("c2")
    assert explorer.current_source() == ALL_CASES
    assert explorer.search_edit.text() == ""
    assert "c2" in explorer.case_header.text()


def test_unknown_case_does_not_crash(explorer):
    explorer.show_case("tidak-ada")
    assert "tidak ditemukan" in explorer.case_header.text()
    assert explorer.event_model.rowCount() == 0


def test_reset_clears_results(explorer):
    explorer.reset()
    assert explorer.results() == []
    assert explorer.source_combo.count() == 1
