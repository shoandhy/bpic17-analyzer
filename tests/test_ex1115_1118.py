from __future__ import annotations

import pandas as pd

from analyses.ex_11_15_18 import complete_events, run
from core.result import AnalysisResult


def _sample_log() -> tuple[pd.DataFrame, pd.Series]:
    rows = [
        # Case C1: 2x complete oleh UserA -> lolos 11.15 dan 11.18 (schedule & start diabaikan)
        {
            "case_id": "C1",
            "activity": "W_Assess potential fraud",
            "timestamp": pd.Timestamp("2026-01-01 08:00:00"),
            "lifecycle": "schedule",
            "resource": "UserA",
            "orig_idx": 0,
            "event_pos": 0,
        },
        {
            "case_id": "C1",
            "activity": "W_Assess potential fraud",
            "timestamp": pd.Timestamp("2026-01-01 09:00:00"),
            "lifecycle": "start",
            "resource": "UserA",
            "orig_idx": 1,
            "event_pos": 1,
        },
        {
            "case_id": "C1",
            "activity": "W_Assess potential fraud",
            "timestamp": pd.Timestamp("2026-01-01 10:00:00"),
            "lifecycle": "complete",
            "resource": "UserA",
            "orig_idx": 2,
            "event_pos": 2,
        },
        {
            "case_id": "C1",
            "activity": "W_Assess potential fraud",
            "timestamp": pd.Timestamp("2026-01-02 10:00:00"),
            "lifecycle": "complete",
            "resource": "UserA",
            "orig_idx": 3,
            "event_pos": 3,
        },
        # Case C2: 2x complete tapi beda resource (UserA & UserB) -> lolos 11.15, gagal 11.18
        {
            "case_id": "C2",
            "activity": "W_Assess potential fraud",
            "timestamp": pd.Timestamp("2026-01-01 11:00:00"),
            "lifecycle": "complete",
            "resource": "UserA",
            "orig_idx": 4,
            "event_pos": 0,
        },
        {
            "case_id": "C2",
            "activity": "W_Assess potential fraud",
            "timestamp": pd.Timestamp("2026-01-02 11:00:00"),
            "lifecycle": "complete",
            "resource": "UserB",
            "orig_idx": 5,
            "event_pos": 1,
        },
        # Case C3: 2x event dengan resource NA/kosong -> tidak boleh dianggap satu resource sama
        {
            "case_id": "C3",
            "activity": "W_Assess potential fraud",
            "timestamp": pd.Timestamp("2026-01-01 12:00:00"),
            "lifecycle": "complete",
            "resource": pd.NA,
            "orig_idx": 6,
            "event_pos": 0,
        },
        {
            "case_id": "C3",
            "activity": "W_Assess potential fraud",
            "timestamp": pd.Timestamp("2026-01-02 12:00:00"),
            "lifecycle": "complete",
            "resource": None,
            "orig_idx": 7,
            "event_pos": 1,
        },
        # Case C4: hanya 1x complete + 1x ate_abort -> gagal 11.15 dan 11.18
        {
            "case_id": "C4",
            "activity": "W_Assess potential fraud",
            "timestamp": pd.Timestamp("2026-01-01 13:00:00"),
            "lifecycle": "complete",
            "resource": "UserC",
            "orig_idx": 8,
            "event_pos": 0,
        },
        {
            "case_id": "C4",
            "activity": "W_Assess potential fraud",
            "timestamp": pd.Timestamp("2026-01-02 13:00:00"),
            "lifecycle": "ate_abort",
            "resource": "UserC",
            "orig_idx": 9,
            "event_pos": 1,
        },
    ]
    df = pd.DataFrame(rows)
    durations = pd.Series(
        {"C1": 4.0, "C2": 6.0, "C3": 8.0, "C4": 2.0},
        name="duration_days",
    )
    return df, durations


def test_complete_events_filters_lifecycle_and_case_insensitive_activity() -> None:
    df, _ = _sample_log()
    comp = complete_events(df, "W_Assess Potential Fraud", "complete")

    assert len(comp) == 7
    assert set(comp["lifecycle"].str.lower()) == {"complete"}


def test_run_1115_and_1118_logic_and_na_handling() -> None:
    df, durations = _sample_log()
    results = run(df, durations, min_count=2)

    assert len(results) == 2
    r15, r18 = results
    assert isinstance(r15, AnalysisResult)
    assert isinstance(r18, AnalysisResult)

    assert r15.code == "11.15"
    assert r15.denominator == 4
    assert r15.case_ids == ["C1", "C2", "C3"]
    assert r15.n_cases == 3
    assert set(r15.per_case.columns) >= {"case_id", "duration_days", "n_complete"}

    assert r18.code == "11.18"
    assert r18.denominator == 4
    assert r18.case_ids == ["C1"]
    assert r18.n_cases == 1
    assert r18.per_case.iloc[0]["resource"] == "UserA"
    assert int(r18.per_case.iloc[0]["n_complete_by_resource"]) == 2


def test_run_reproducible_with_effective_params() -> None:
    df, durations = _sample_log()
    first = run(df, durations, min_count=2)
    second = run(df, durations, **first[0].params)

    assert [r.case_ids for r in first] == [r.case_ids for r in second]
    assert [r.n_cases for r in first] == [r.n_cases for r in second]