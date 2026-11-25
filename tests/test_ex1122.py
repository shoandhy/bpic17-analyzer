"""Unit test milik Anggota D: Exercise 11.22 (F06), fitur opsional Fast/Slow + histogram,
generator log sintetis XES + expected.json, dan panel GUI Ex1122Panel.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from analyses import ex_11_7, ex_11_22, optional
from app.panels.ex1122_panel import Ex1122Panel
from core.schema import CANONICAL_COLUMNS, check_canonical
from tests.fixtures.make_synthetic import (
    EXPECTED,
    EXPECTED_CASE_DURATIONS,
    build_expected_dict,
    generate_synthetic_bundle,
    make_synthetic_log,
    synthetic_durations,
    write_expected_json,
    write_synthetic_xes,
)
from tests.fixtures.tiny_log import EXPECTED as TINY_EXPECTED
from tests.test_contract import check_params_contract


@pytest.fixture
def synth_log() -> pd.DataFrame:
    return make_synthetic_log()


@pytest.fixture
def synth_durs(synth_log: pd.DataFrame) -> pd.Series:
    return synthetic_durations(synth_log)


# --- 1. Exercise 11.22: eventually_follows & run() ---------------------------------------

def test_eventually_follows_core_semantics(synth_log):
    matched = ex_11_22.eventually_follows(synth_log, a="O_Cancelled", b="O_Accepted")
    assert matched == EXPECTED["11.22"]

    # O_Cancelled -> aktivitas lain -> O_Accepted LOLOS (tidak harus bertetangga)
    assert "cancel_then_other_then_accepted" in matched
    # Beberapa O_Cancelled dan O_Accepted tetap lolos dan dihitung sekali
    assert "cancel_multi_then_accepted" in matched
    # O_Accepted mendahului O_Cancelled tanpa accepted sesudahnya TIDAK lolos
    assert "accepted_before_cancel_only" not in matched
    # Case berakhir O_Cancelled tanpa O_Accepted tidak otomatis lolos
    assert "ends_with_cancel_only" not in matched
    # Timestamp sama dengan O_Accepted lebih dulu di file TIDAK lolos
    assert "same_timestamp_tiebreak" not in matched
    # O_Cancelled di tengah tanpa O_Accepted TIDAK lolos
    assert "cancel_middle" not in matched


def test_ex1122_result_metrics_and_evidence(synth_log, synth_durs):
    res = ex_11_22.run(synth_log, synth_durs)
    assert res.code == "11.22"
    assert res.denominator == 12
    assert res.n_cases == 2
    assert set(res.case_ids) == EXPECTED["11.22"]
    assert res.percentage == pytest.approx(2 / 12 * 100.0)
    assert "denominator" in res.rule_text.lower() or "/ 12" in res.rule_text
    assert res.mean_cycle_days == pytest.approx(float(synth_durs.loc[res.case_ids].mean()))

    # Evidence wajib punya 7 kolom kanonik + role, berisi tepat 2 event per case lolos
    assert set(CANONICAL_COLUMNS) <= set(res.evidence.columns)
    assert "role" in res.evidence.columns
    assert len(res.evidence) == 2 * res.n_cases

    # Untuk cancel_multi_then_accepted: bukti = O_Cancelled PERTAMA (pos 1) & O_Accepted TERAKHIR (pos 5)
    ev_multi = res.evidence[res.evidence["case_id"] == "cancel_multi_then_accepted"].sort_values("event_pos")
    assert len(ev_multi) == 2
    assert list(ev_multi["activity"]) == ["O_Cancelled", "O_Accepted"]
    assert list(ev_multi["role"]) == ["cancelled", "accepted"]
    assert list(ev_multi["event_pos"]) == [1, 5]
    assert ev_multi["timestamp"].iloc[0] < ev_multi["timestamp"].iloc[1]

    # per_case memuat kolom wajib + pasangan posisi/timestamp
    assert {"case_id", "duration_days", "first_pos", "first_timestamp", "then_pos", "then_timestamp", "gap_events"} <= set(res.per_case.columns)
    row_non_adj = res.per_case.set_index("case_id").loc["cancel_then_other_then_accepted"]
    assert int(row_non_adj["gap_events"]) == 1


def test_ex1122_tiny_log_and_params_contract(tiny_log, tiny_durs):
    res = ex_11_22.run(tiny_log, tiny_durs)
    assert set(res.case_ids) == TINY_EXPECTED["11.22"]
    assert res.denominator == 6
    assert res.percentage == pytest.approx(1 / 6 * 100.0)
    check_params_contract(ex_11_22, tiny_log, tiny_durs)


def test_ex1122_empty_and_no_match(synth_log, synth_durs):
    empty_df = synth_log.iloc[0:0].copy()
    res_empty = ex_11_22.run(empty_df, synth_durs.iloc[0:0])
    assert res_empty.n_cases == 0
    assert res_empty.denominator == 0
    assert res_empty.percentage is None
    assert set(CANONICAL_COLUMNS) <= set(res_empty.evidence.columns)

    res_none = ex_11_22.run(synth_log, synth_durs, first_activity="TIDAK_ADA")
    assert res_none.n_cases == 0
    assert res_none.denominator == 12
    assert res_none.percentage == pytest.approx(0.0)
    assert res_none.mean_cycle_days is None


def test_ex1122_does_not_mutate_input(synth_log, synth_durs):
    before = synth_log.copy(deep=True)
    ex_11_22.run(synth_log, synth_durs)
    pd.testing.assert_frame_equal(synth_log, before)


def test_ex1122_offer_level_is_separate_from_case_level(synth_log, synth_durs):
    df_offer = synth_log.copy()
    # Pada cancel_then_other_then_accepted, O_Cancelled = Offer_1, O_Accepted = Offer_2 (offer beda)
    # Pada cancel_multi_then_accepted, kedua event memakai Offer_X (offer sama)
    df_offer["OfferID"] = pd.NA
    m1 = df_offer["case_id"] == "cancel_then_other_then_accepted"
    df_offer.loc[m1 & (df_offer["activity"] == "O_Cancelled"), "OfferID"] = "Offer_1"
    df_offer.loc[m1 & (df_offer["activity"] == "O_Accepted"), "OfferID"] = "Offer_2"

    m2 = df_offer["case_id"] == "cancel_multi_then_accepted"
    df_offer.loc[m2 & df_offer["activity"].isin(["O_Cancelled", "O_Accepted"]), "OfferID"] = "Offer_X"

    res_case = ex_11_22.run(df_offer, synth_durs)
    res_offer = ex_11_22.run_offer_level(df_offer, synth_durs)
    assert res_case.code == "11.22"
    assert res_offer.code == "11.22-offer"
    assert res_case.n_cases == 2
    assert res_offer.case_ids == ["cancel_multi_then_accepted"]
    assert res_offer.n_cases == 1


# --- 2. Fitur Opsional: Fast vs Slow + Histogram -----------------------------------------

def test_optional_fast_vs_slow_boundary_and_contract(synth_log, synth_durs):
    results = optional.run(synth_log, synth_durs)
    assert [r.code for r in results] == ["OPT.fast", "OPT.slow"]
    by_code = {r.code: r for r in results}

    # fraud_missing_resource tepat 45.0 hari -> masuk OPT.slow (>= 45), bukan OPT.fast (< 45)
    assert set(by_code["OPT.fast"].case_ids) == EXPECTED["OPT.fast"]
    assert set(by_code["OPT.slow"].case_ids) == EXPECTED["OPT.slow"]
    assert "fraud_missing_resource" in by_code["OPT.slow"].case_ids
    assert "fraud_missing_resource" not in by_code["OPT.fast"].case_ids

    assert by_code["OPT.fast"].n_cases + by_code["OPT.slow"].n_cases == 12
    assert by_code["OPT.fast"].percentage == pytest.approx(9 / 12 * 100.0)
    assert by_code["OPT.slow"].percentage == pytest.approx(3 / 12 * 100.0)
    assert set(CANONICAL_COLUMNS) <= set(by_code["OPT.fast"].evidence.columns)
    assert set(CANONICAL_COLUMNS) <= set(by_code["OPT.slow"].evidence.columns)

    check_params_contract(optional, synth_log, synth_durs)


def test_optional_histogram_and_comparison(synth_log, synth_durs):
    hist = optional.duration_histogram(synth_durs, bins=10, threshold_days=45.0)
    assert int(hist["counts"].sum()) == len(synth_durs)
    assert hist["n_fast"] == 9
    assert hist["n_slow"] == 3
    assert hist["min"] == pytest.approx(4.0)
    assert hist["max"] == pytest.approx(60.0)
    assert {"bin_start", "bin_end", "count", "group"} <= set(hist["table"].columns)

    comp = optional.compare_fast_slow(synth_log, synth_durs, threshold_days=45.0)
    assert len(comp) == 2
    assert list(comp["n_cases"]) == [9, 3]


# --- 3. Generator Log Sintetis & expected.json -------------------------------------------

def test_synthetic_log_is_canonical_and_matches_ex117_and_expected(synth_log, synth_durs):
    check_canonical(synth_log)
    assert list(synth_log.columns) == CANONICAL_COLUMNS
    assert synth_log["case_id"].nunique() == 12

    for cid, exp_days in EXPECTED_CASE_DURATIONS.items():
        assert synth_durs.loc[cid] == pytest.approx(exp_days)

    # Cross-check langsung terhadap modul Anggota B (ex_11_7)
    r117 = {r.code: r for r in ex_11_7.run(synth_log, synth_durs)}
    for code in ("11.7A", "11.7B", "11.7C", "11.7D", "11.7E"):
        assert set(r117[code].case_ids) == EXPECTED[code]


def test_synthetic_xes_roundtrip_and_expected_json(tmp_path):
    xes_path, json_path = generate_synthetic_bundle(tmp_path)
    assert xes_path.exists() and xes_path.stat().st_size > 0
    assert json_path.exists()

    # Validasi isi expected.json
    loaded_json = json.loads(json_path.read_text(encoding="utf-8"))
    assert loaded_json["n_cases"] == 12
    assert set(loaded_json["exercises"]) >= {
        "11.7A", "11.7B", "11.7C", "11.7D", "11.7E", "11.15", "11.18", "11.22", "OPT.fast", "OPT.slow"
    }
    assert set(loaded_json["exercises"]["11.22"]["case_ids"]) == EXPECTED["11.22"]

    # Baca kembali file XES lewat PM4Py untuk memastikan valid & jumlah case/event utuh
    import pm4py

    raw = pm4py.read_xes(str(xes_path))
    assert raw["case:concept:name"].nunique() == 12
    assert len(raw) == len(make_synthetic_log())


def test_committed_expected_json_matches_generator():
    expected_file = (
        write_expected_json.__globals__["Path"](__file__).resolve().parent
        / "fixtures"
        / "expected.json"
    )
    assert expected_file.exists(), "tests/fixtures/expected.json harus tersedia untuk semua anggota"
    on_disk = json.loads(expected_file.read_text(encoding="utf-8"))
    assert on_disk == build_expected_dict()


# --- 4. Panel GUI Ex1122Panel ------------------------------------------------------------

def test_ex1122_panel_runs_renders_timeline_and_emits_signals(qtbot, synth_log, synth_durs):
    panel = Ex1122Panel()
    qtbot.addWidget(panel)
    panel.set_log(synth_log, synth_durs)
    assert panel.btn_run.isEnabled()
    assert panel.btn_run_opt.isEnabled()
    assert not panel.btn_run_offer.isEnabled()  # log sintetis tanpa kolom OfferID

    with qtbot.waitSignal(panel.results_ready, timeout=5000) as blocker:
        panel.run_analysis()
    results = blocker.args[0]
    assert len(results) == 1 and results[0].code == "11.22"
    assert panel.case_model.rowCount() == 2
    assert "2 case" in panel.card_count.lbl_value.text()
    assert "16.67%" in panel.card_pct.lbl_value.text()
    assert "/ 12" in panel.card_pct.lbl_sub.text()
    assert panel.btn_open_case.isEnabled()

    # Double-click memancarkan open_case dan open_case_for("...", "11.22")
    idx = panel.case_model.index(0, 0)
    with qtbot.waitSignal(panel.open_case_for, timeout=1000) as open_blocker:
        panel._on_case_double_clicked(idx)
    assert open_blocker.args[1] == "11.22"
    assert open_blocker.args[0] in EXPECTED["11.22"]

    # Jalankan fitur opsional Fast vs Slow di tab 3
    with qtbot.waitSignal(panel.results_ready, timeout=5000) as opt_blocker:
        panel.run_optional_analysis()
    opt_results = opt_blocker.args[0]
    assert [r.code for r in opt_results] == ["OPT.fast", "OPT.slow"]
    assert panel.compare_model.rowCount() == 2
    assert panel.opt_case_model.rowCount() == 9  # default combobox = OPT.fast

    # Reset membersihkan hasil tanpa menghapus log
    panel.reset()
    assert panel.case_model.rowCount() == 0
    assert panel.opt_case_model.rowCount() == 0
    assert panel.btn_run.isEnabled()
