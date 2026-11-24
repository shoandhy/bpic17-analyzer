"""Test ekspor CSV (Anggota E) memakai AnalysisResult dummy dari tests/fixtures."""

from __future__ import annotations

import pandas as pd

from core.result import AnalysisResult
from core.schema import CANONICAL_COLUMNS
from export import csv_export


def _read(path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def test_summary_csv_has_exact_columns_and_values(dummy_results, tmp_path):
    path = csv_export.export_summary(dummy_results, tmp_path / "out" / "ringkasan.csv")
    df = _read(path)
    assert list(df.columns) == csv_export.SUMMARY_COLUMNS
    assert len(df) == len(dummy_results)
    by_code = df.set_index("code")
    for r in dummy_results:
        row = by_code.loc[r.code]
        assert int(row["n_cases"]) == r.n_cases
        assert int(row["denominator"]) == r.denominator
        assert row["rule_text"] == r.rule_text


def test_summary_none_becomes_empty_cell(dummy_results, tmp_path):
    df = _read(csv_export.export_summary(dummy_results, tmp_path / "s.csv")).set_index("code")
    assert df.loc["11.7C", "percentage"] == ""          # soal tanpa persentase
    assert float(df.loc["11.22", "percentage"]) > 0      # 11.22 punya persentase


def test_case_list_one_row_per_case_per_analysis(dummy_results, tmp_path):
    df = _read(csv_export.export_case_lists(dummy_results, tmp_path / "c.csv"))
    assert list(df.columns) == csv_export.CASE_LIST_COLUMNS
    assert len(df) == sum(r.n_cases for r in dummy_results)
    for r in dummy_results:
        assert df.loc[df["code"] == r.code, "case_id"].tolist() == [str(c) for c in r.case_ids]


def test_evidence_csv_columns_and_iso_timestamp(dummy_results, tmp_path):
    df = _read(csv_export.export_evidence(dummy_results, tmp_path / "e.csv"))
    assert list(df.columns[: 1 + len(CANONICAL_COLUMNS)]) == ["code", *CANONICAL_COLUMNS]
    assert len(df) == sum(len(r.evidence) for r in dummy_results)
    assert df["timestamp"].str.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$").all()


def test_evidence_keeps_extra_columns_and_empty_resource(tiny_log, tmp_path):
    ev = tiny_log[tiny_log["case_id"] == "c5"].copy()
    ev["role"] = "bukti"
    r = AnalysisResult("X", "x", "x", n_cases=1, denominator=6, case_ids=["c5"], evidence=ev)
    df = _read(csv_export.export_evidence([r], tmp_path / "e.csv"))
    assert df.columns[-1] == "role"
    assert "" in df["resource"].tolist()  # resource NA ditulis sebagai sel kosong


def test_export_all_writes_three_files(dummy_results, tmp_path):
    paths = csv_export.export_all(dummy_results, tmp_path, stamp="T")
    assert {p.name for p in paths.values()} == {"ringkasan_T.csv", "daftar_case_T.csv", "evidence_T.csv"}
    assert all(p.exists() for p in paths.values())


def test_empty_results_still_write_headers(tmp_path):
    assert list(_read(csv_export.export_summary([], tmp_path / "s.csv")).columns) == csv_export.SUMMARY_COLUMNS
    assert "code" in _read(csv_export.export_evidence([], tmp_path / "e.csv")).columns
