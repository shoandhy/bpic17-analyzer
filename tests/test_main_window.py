"""Test MainWindow (Anggota E): placeholder panel, hasil, reset, re-run, dan jalur error."""

from __future__ import annotations

import pytest

import analyses.ex_11_22
from app.main_window import MainWindow, PlaceholderPanel, module_for_code


@pytest.fixture
def window(qtbot, monkeypatch):
    w = MainWindow()
    qtbot.addWidget(w)
    w.errors = []
    monkeypatch.setattr(w, "_show_error", lambda t, m, d="": w.errors.append(m))
    monkeypatch.setattr(w, "_show_info", lambda t, m: None)
    return w


def test_opens_even_when_panels_are_stubs(window):
    titles = [window.sidebar.item(i).text() for i in range(window.sidebar.count())]
    assert titles[0] == "Dataset" and titles[-2:] == ["Case Explorer", "Hasil & Ekspor"]
    assert any(isinstance(p, PlaceholderPanel) for p in window.panels)


def test_results_flow_and_reset(window, tiny_log, tiny_durs, dummy_results):
    window.set_log(tiny_log, tiny_durs, source="tiny")
    assert window.explorer.case_model.rowCount() == 6
    window.add_results(dummy_results)
    assert window.results_model.rowCount() == len(dummy_results)
    assert window.act_export_all.isEnabled()
    window.reset_results()
    assert window.results_model.rowCount() == 0
    assert window.explorer.results() == []
    assert window._df is tiny_log  # reset tidak membuang log


def test_rerun_replaces_result_by_code(window, qtbot, monkeypatch, tiny_log, tiny_durs, dummy_results):
    window.set_log(tiny_log, tiny_durs, source="tiny")
    window.add_results(dummy_results)
    old = next(r for r in dummy_results if r.code == "11.22")
    new = type(old)(**{**old.__dict__, "title": "Hasil re-run"})
    monkeypatch.setattr(analyses.ex_11_22, "run", lambda df, durations, **p: new)
    window.rerun_codes(["11.22"])
    qtbot.waitUntil(lambda: window._results["11.22"].title == "Hasil re-run", timeout=5000)
    assert window.results_model.rowCount() == len(dummy_results)


def test_loader_error_reaches_error_dialog(window, qtbot):
    window.load_xes_file("tidak_ada.xes")
    qtbot.waitUntil(lambda: bool(window.errors), timeout=5000)
    assert "NotImplementedError" in window.errors[0] or "Error" in window.errors[0]
    assert not window._loading and window.progress.isHidden()


def test_run_all_with_stub_modules_is_quiet(window, qtbot, tiny_log, tiny_durs):
    window.set_log(tiny_log, tiny_durs, source="tiny")
    window.run_all()
    qtbot.waitUntil(lambda: window._tasks == 0, timeout=5000)
    assert window.errors == []  # NotImplementedError hanya dilaporkan di status bar


def test_open_case_from_panel_focuses_panel_result(window, tiny_log, tiny_durs, dummy_results):
    window.set_log(tiny_log, tiny_durs, source="tiny")
    panel = window.panels[2]
    window._on_panel_results(panel, [r for r in dummy_results if r.code.startswith("11.7")])
    panel.open_case.emit("c6")
    assert window.stack.currentWidget() is window.explorer
    # Hasil paling spesifik (case paling sedikit) yang memuat c6: 11.7E (2 case),
    # bukan 11.7A yang memuat semua case.
    assert window.explorer._focus_code == "11.7E"


def test_export_all_to_folder(window, qtbot, tmp_path, tiny_log, tiny_durs, dummy_results):
    window.set_log(tiny_log, tiny_durs, source="tiny")
    window.add_results(dummy_results)
    window.export_all_to(tmp_path)
    qtbot.waitUntil(lambda: len(list(tmp_path.glob("*.csv"))) == 3, timeout=5000)


@pytest.mark.parametrize("code,module", [
    ("11.7A", "analyses.ex_11_7"), ("11.7E", "analyses.ex_11_7"),
    ("11.15", "analyses.ex_11_15_18"), ("11.18", "analyses.ex_11_15_18"),
    ("11.22", "analyses.ex_11_22"), ("11.22-offer", "analyses.ex_11_22"),
    ("OPT.fast", "analyses.optional"), ("lain", None),
])
def test_module_for_code(code, module):
    assert module_for_code(code) == module
