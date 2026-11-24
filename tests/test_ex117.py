"""Unit test Exercise 11.7 A–E (Anggota B): logika analisis dan panel GUI."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt

from analyses import ex_11_7
from app.panels.ex117_panel import Ex117Panel
from core.schema import CANONICAL_COLUMNS
from tests.fixtures.tiny_log import EXPECTED
from tests.test_contract import check_params_contract


def _by_code(results):
    return {r.code: r for r in results}


def test_ex117_tiny_log_counts_and_case_ids(tiny_log, tiny_durs):
    results = _by_code(ex_11_7.run(tiny_log, tiny_durs))
    assert list(results) == ["11.7A", "11.7B", "11.7C", "11.7D", "11.7E"]

    assert results["11.7A"].n_cases == 6
    assert set(results["11.7A"].case_ids) == EXPECTED["11.7A"]
    assert results["11.7B"].mean_cycle_days == pytest.approx(float(tiny_durs.mean()))

    # c1 punya O_Accepted 2x -> tetap dihitung 1 case
    assert set(results["11.7C"].case_ids) == EXPECTED["11.7C"]
    assert results["11.7C"].n_cases == len(EXPECTED["11.7C"])

    # c3 punya O_Refused dan O_Accepted -> masuk C dan D (tidak saling eksklusif)
    assert set(results["11.7D"].case_ids) == EXPECTED["11.7D"]
    assert "c3" in results["11.7C"].case_ids and "c3" in results["11.7D"].case_ids

    # c2 punya O_Cancelled di tengah lalu W_Validate application -> TIDAK masuk 11.7E
    assert set(results["11.7E"].case_ids) == EXPECTED["11.7E"]
    assert "c2" not in results["11.7E"].case_ids


def test_ex117_mean_cycle_uses_full_case_durations(tiny_log, tiny_durs):
    results = _by_code(ex_11_7.run(tiny_log, tiny_durs))
    for code in ("11.7C", "11.7D", "11.7E"):
        r = results[code]
        expected_mean = float(tiny_durs.loc[r.case_ids].mean())
        assert r.mean_cycle_days == pytest.approx(expected_mean)


def test_ex117_evidence_has_canonical_columns_and_matching_cases(tiny_log, tiny_durs):
    results = _by_code(ex_11_7.run(tiny_log, tiny_durs))
    for code in ("11.7C", "11.7D", "11.7E"):
        ev = results[code].evidence
        assert set(CANONICAL_COLUMNS) <= set(ev.columns)
        assert set(ev["case_id"]) <= set(results[code].case_ids)
    # 11.7E evidence harus event terakhir tiap case
    ev_e = results["11.7E"].evidence
    assert (ev_e["activity"] == "O_Cancelled").all()
    assert len(ev_e) == results["11.7E"].n_cases


def test_ex117_helpers_contains_and_endpoint(tiny_log):
    assert ex_11_7.filter_contains(tiny_log, "O_Accepted") == EXPECTED["11.7C"]
    assert ex_11_7.filter_endpoint(tiny_log, "O_Cancelled", position="last") == EXPECTED["11.7E"]
    assert ex_11_7.filter_endpoint(tiny_log, "A_Create Application", position="first") == EXPECTED["11.7A"]


def test_ex117_params_contract(tiny_log, tiny_durs):
    check_params_contract(ex_11_7, tiny_log, tiny_durs)


def test_ex117_panel_runs_and_emits_signals(qtbot, tiny_log, tiny_durs):
    panel = Ex117Panel()
    qtbot.addWidget(panel)
    panel.set_log(tiny_log, tiny_durs)
    assert panel.btn_run.isEnabled()

    with qtbot.waitSignal(panel.results_ready, timeout=5000) as blocker:
        panel.run_analysis()
    results = blocker.args[0]
    assert [r.code for r in results] == ["11.7A", "11.7B", "11.7C", "11.7D", "11.7E"]

    panel._select_code("11.7E")
    assert panel.case_model.rowCount() == len(EXPECTED["11.7E"])

    idx = panel.case_model.index(0, 0)
    with qtbot.waitSignal(panel.open_case_for, timeout=1000) as open_blocker:
        panel._on_row_double_clicked(idx)
    assert open_blocker.args[1] == "11.7E"
    assert open_blocker.args[0] in EXPECTED["11.7E"]
