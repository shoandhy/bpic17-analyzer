"""Test penjaga kontrak bersama. Jangan dihapus; ubah hanya bila kontrak diubah kelompok."""

from __future__ import annotations

import ast
import dataclasses
import importlib
import inspect
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from core.loaded_log import LoadedLog
from core.result import AnalysisResult
from core.schema import CANONICAL_COLUMNS, SchemaError, check_canonical

ROOT = Path(__file__).resolve().parent.parent
ANALYSIS_MODULES = ["analyses.ex_11_7", "analyses.ex_11_15_18", "analyses.ex_11_22", "analyses.optional"]


# --- DataFrame kanonik ---------------------------------------------------------------

def test_tiny_log_is_canonical(tiny_log):
    check_canonical(tiny_log)
    assert list(tiny_log.columns) == CANONICAL_COLUMNS
    assert tiny_log["case_id"].nunique() == 6


def test_tie_break_uses_orig_idx(tiny_log):
    c6 = tiny_log[tiny_log["case_id"] == "c6"]
    last_two = c6.tail(2)["activity"].tolist()
    assert last_two == ["O_Accepted", "O_Cancelled"]


def test_check_canonical_rejects_empty_resource(tiny_log):
    bad = tiny_log.copy()
    bad["resource"] = bad["resource"].astype("object")
    bad.loc[0, "resource"] = ""
    with pytest.raises(SchemaError):
        check_canonical(bad)


def test_check_canonical_rejects_unsorted(tiny_log):
    bad = tiny_log.iloc[::-1]
    with pytest.raises(SchemaError):
        check_canonical(bad)


def test_check_canonical_rejects_naive_timestamp(tiny_log):
    bad = tiny_log.copy()
    bad["timestamp"] = bad["timestamp"].dt.tz_localize(None)
    with pytest.raises(SchemaError):
        check_canonical(bad)


# --- AnalysisResult ------------------------------------------------------------------

def test_result_rejects_duplicate_case_ids():
    with pytest.raises(ValueError):
        AnalysisResult("X", "x", "x", n_cases=2, denominator=5, case_ids=["a", "a"])


def test_result_rejects_count_mismatch():
    with pytest.raises(ValueError):
        AnalysisResult("X", "x", "x", n_cases=3, denominator=5, case_ids=["a", "b"])


def test_dummy_results_are_valid(dummy_results):
    assert {r.code for r in dummy_results} >= {"11.7C", "11.15", "11.18", "11.22"}
    for r in dummy_results:
        assert {"case_id", "duration_days"} <= set(r.per_case.columns)
        assert set(CANONICAL_COLUMNS) <= set(r.evidence.columns)
        assert set(r.evidence["case_id"]) <= set(r.case_ids)


# --- Signature analisis --------------------------------------------------------------

@pytest.mark.parametrize("modname", ANALYSIS_MODULES)
def test_analysis_run_signature(modname):
    mod = importlib.import_module(modname)
    params = list(inspect.signature(mod.run).parameters.values())
    assert [p.name for p in params[:2]] == ["df", "durations"]
    assert params[-1].kind is inspect.Parameter.VAR_KEYWORD
    assert isinstance(getattr(mod, "DEFAULT_PARAMS", None), dict)


# --- Larangan import GUI di core/analyses/export ---------------------------------------

def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


@pytest.mark.parametrize("pkg", ["core", "analyses", "export"])
def test_no_gui_imports(pkg):
    for py in (ROOT / pkg).rglob("*.py"):
        bad = _imports(py) & {"PySide6", "PyQt5", "PyQt6", "tkinter", "customtkinter", "app"}
        assert not bad, f"{py.relative_to(ROOT)} mengimpor GUI: {bad}"


# --- Kontrak panel GUI ---------------------------------------------------------------

def test_panels_follow_base_contract():
    pytest.importorskip("PySide6")
    from app.panels.base import BasePanel

    panel_modules = {
        "app.panels.dataset_panel": "DatasetPanel",
        "app.panels.overview_panel": "OverviewPanel",
        "app.panels.ex117_panel": "Ex117Panel",
        "app.panels.ex1115_1118_panel": "Ex1115_1118Panel",
        "app.panels.ex1122_panel": "Ex1122Panel",
        "app.panels.case_explorer": "CaseExplorer",
    }
    for modname, clsname in panel_modules.items():
        cls = getattr(importlib.import_module(modname), clsname)
        assert issubclass(cls, BasePanel), clsname
        assert hasattr(cls, "open_case") and hasattr(cls, "results_ready")
        assert "set_log" in cls.__dict__, f"{clsname} harus override set_log"


# --- Kontrak v2: open_case_for & set_loaded -------------------------------------------

def test_base_panel_v2_signals_and_optional_set_loaded(qtbot):
    pytest.importorskip("PySide6")
    from app.panels.base import BasePanel

    class MinimalPanel(BasePanel):
        def set_log(self, df, durations):
            pass

    panel = MinimalPanel()
    qtbot.addWidget(panel)
    loaded = LoadedLog(path=Path("x.xes"), n_cases=1, n_events=2)
    assert panel.set_loaded(loaded) is None  # opsional: default no-op, tidak error
    with qtbot.waitSignal(panel.open_case_for, timeout=1000) as blocker:
        panel.open_case_for.emit("c6", "11.7E")
    assert blocker.args == ["c6", "11.7E"]
    with qtbot.waitSignal(panel.open_case, timeout=1000) as blocker:
        panel.open_case.emit("c6")  # v1 tetap ada
    assert blocker.args == ["c6"]


def test_loaded_log_fields_and_loader_signature():
    assert [f.name for f in dataclasses.fields(LoadedLog)] == [
        "path", "n_cases", "n_events", "attributes", "warnings",
    ]
    import core.loader

    assert core.loader.LoadedLog is LoadedLog  # diekspor ulang dari core.loader
    ret = str(inspect.signature(core.loader.load_xes).return_annotation)
    assert "DataFrame" in ret and "LoadedLog" in ret  # load_xes -> (df, LoadedLog)


# --- Kontrak v2: AnalysisResult.params = argumen efektif -------------------------------

def _as_results(out) -> list[AnalysisResult]:
    return [out] if isinstance(out, AnalysisResult) else list(out)


def _assert_same_result(a: AnalysisResult, b: AnalysisResult) -> None:
    for f in dataclasses.fields(AnalysisResult):
        x, y = getattr(a, f.name), getattr(b, f.name)
        if isinstance(x, pd.DataFrame):
            pd.testing.assert_frame_equal(x.reset_index(drop=True), y.reset_index(drop=True))
        else:
            assert x == y, f"{a.code}.{f.name}: {x!r} != {y!r}"


def check_params_contract(module, df: pd.DataFrame, durations: pd.Series) -> None:
    """Pemeriksa kontrak v2 untuk satu modul analisis (boleh dipakai test anggota)."""
    first = _as_results(module.run(df, durations))
    allowed = set(module.DEFAULT_PARAMS)
    for r in first:
        extra = set(r.params) - allowed
        assert not extra, f"{r.code}: params berisi kunci di luar DEFAULT_PARAMS: {extra}"
        assert r.params == first[0].params, f"{r.code}: params beda antar hasil satu run"
        again = _as_results(module.run(df, durations, **r.params))
        twin = {x.code: x for x in again}
        assert r.code in twin, f"{r.code} hilang saat run(**params)"
        _assert_same_result(r, twin[r.code])


@pytest.mark.parametrize("modname", ANALYSIS_MODULES)
def test_params_rerun_identical(modname, tiny_log, tiny_durs):
    mod = importlib.import_module(modname)
    try:
        check_params_contract(mod, tiny_log, tiny_durs)
    except NotImplementedError:
        pytest.skip(f"{modname}.run belum diimplementasikan")


def _fake_module(record_extra: bool):
    defaults = {"activity": "O_Accepted"}

    def run(df, durations, **params):
        eff = {**defaults, **params}
        ids = sorted(df.loc[df["activity"] == eff["activity"], "case_id"].unique())
        stored = {**eff, "dijalankan_pada": "sekarang"} if record_extra else eff
        return AnalysisResult("F", "f", "f", n_cases=len(ids), denominator=df["case_id"].nunique(),
                              case_ids=list(ids), params=stored)

    return SimpleNamespace(run=run, DEFAULT_PARAMS=defaults)


def test_params_checker_accepts_compliant_and_rejects_extra_keys(tiny_log, tiny_durs):
    check_params_contract(_fake_module(record_extra=False), tiny_log, tiny_durs)
    with pytest.raises(AssertionError, match="di luar DEFAULT_PARAMS"):
        check_params_contract(_fake_module(record_extra=True), tiny_log, tiny_durs)
