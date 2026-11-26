"""Test unit dan GUI milik Anggota A (core/loader.py, core/durations.py,
app/panels/dataset_panel.py, app/panels/overview_panel.py, app/panels/about_dialog.py).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from core.durations import compute_case_durations, compute_overview
from core.loaded_log import LoadedLog
from core.loader import LogValidationError, load_xes, to_canonical, validate
from core.schema import DURATION_NAME, check_canonical


def _raw_sample() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "case:concept:name": ["C1", "C1", "C1", "C2"],
            "concept:name": ["A_Create", "W_Call", "O_Accepted", "A_Create"],
            "time:timestamp": [
                "2017-01-01T10:00:00+00:00",
                "2017-01-01T10:00:00+00:00",  # timestamp sama dengan baris 0
                "2017-01-03T10:00:00+00:00",
                "2017-01-02T12:00:00+00:00",
            ],
            "lifecycle:transition": ["COMPLETE", "Start", "complete", None],
            "org:resource": ["User_1", "   ", "", "User_2"],
        }
    )


# --- core/loader.py ------------------------------------------------------------------


def test_validate_missing_required_attribute_returns_error():
    raw = _raw_sample().drop(columns=["concept:name"])
    errors, _warnings = validate(raw)
    assert errors
    assert "concept:name" in errors[0]
    with pytest.raises(LogValidationError, match="concept:name"):
        to_canonical(raw)


def test_validate_detects_missing_optional_attributes_as_warnings():
    raw = _raw_sample().drop(columns=["lifecycle:transition", "org:resource"])
    errors, warnings = validate(raw)
    assert errors == []
    assert any("lifecycle:transition" in w for w in warnings)
    assert any("org:resource" in w for w in warnings)

    canon = to_canonical(raw)
    check_canonical(canon)
    assert canon["lifecycle"].isna().all()
    assert canon["resource"].isna().all()


def test_empty_and_whitespace_resource_becomes_na():
    canon = to_canonical(_raw_sample())
    check_canonical(canon)
    c1 = canon[canon["case_id"] == "C1"].reset_index(drop=True)
    assert c1.loc[0, "resource"] == "User_1"
    assert pd.isna(c1.loc[1, "resource"])
    assert pd.isna(c1.loc[2, "resource"])


def test_same_timestamp_preserves_orig_idx_order():
    raw = pd.DataFrame(
        {
            "case:concept:name": ["C1", "C1", "C1"],
            "concept:name": ["Pertama", "Kedua", "Ketiga"],
            "time:timestamp": [
                "2017-01-01T08:00:00+00:00",
                "2017-01-01T08:00:00+00:00",
                "2017-01-01T08:00:00+00:00",
            ],
        }
    )
    canon = to_canonical(raw)
    check_canonical(canon)
    assert canon["activity"].tolist() == ["Pertama", "Kedua", "Ketiga"]
    assert canon["orig_idx"].tolist() == [0, 1, 2]
    assert canon["event_pos"].tolist() == [0, 1, 2]


def test_lifecycle_normalized_to_lowercase():
    canon = to_canonical(_raw_sample())
    c1 = canon[canon["case_id"] == "C1"].reset_index(drop=True)
    assert c1["lifecycle"].tolist() == ["complete", "start", "complete"]


def test_load_xes_missing_or_corrupt_file_raises_validation_error(tmp_path: Path):
    with pytest.raises(LogValidationError, match="tidak ditemukan"):
        load_xes(tmp_path / "tidak_ada.xes")

    bad_file = tmp_path / "rusak.xes"
    bad_file.write_text("bukan xml xes valid", encoding="utf-8")
    with pytest.raises(LogValidationError, match="rusak"):
        load_xes(bad_file)


def test_load_xes_roundtrip_with_pm4py(tmp_path: Path):
    pm4py = pytest.importorskip("pm4py")
    raw = _raw_sample()
    raw["time:timestamp"] = pd.to_datetime(raw["time:timestamp"], utc=True)
    xes_path = tmp_path / "sample.xes"
    pm4py.write_xes(raw, str(xes_path))

    seen_progress: list[tuple[int, str]] = []
    df, loaded = load_xes(xes_path, progress=lambda p, m: seen_progress.append((p, m)))

    check_canonical(df)
    assert isinstance(loaded, LoadedLog)
    assert loaded.path == xes_path
    assert loaded.n_cases == 2
    assert loaded.n_events == 4
    assert "concept:name" in loaded.attributes
    assert seen_progress


# --- core/durations.py ---------------------------------------------------------------


def test_compute_case_durations_max_minus_min():
    canon = to_canonical(_raw_sample())
    durs = compute_case_durations(canon)
    assert durs.name == DURATION_NAME
    assert durs.loc["C1"] == pytest.approx(2.0)
    assert durs.loc["C2"] == pytest.approx(0.0)


def test_compute_overview_metrics_and_frequencies(tiny_log, tiny_durs):
    ov = compute_overview(tiny_log, tiny_durs)
    assert ov["total_cases"] == 6
    assert ov["total_events"] == len(tiny_log)
    assert ov["mean_cycle_days"] == pytest.approx(float(tiny_durs.mean()))
    assert ov["activity_freq"]["count"].sum() == len(tiny_log)
    assert ov["activity_lifecycle_freq"]["count"].sum() == len(tiny_log)
    assert len(ov["case_table"]) == 6


# --- GUI: DatasetPanel, OverviewPanel, AboutDialog -----------------------------------


def test_dataset_panel_displays_loaded_metadata(qtbot, tiny_log, tiny_durs):
    from app.panels.dataset_panel import DatasetPanel

    panel = DatasetPanel()
    qtbot.addWidget(panel)
    panel.set_log(tiny_log, tiny_durs)
    loaded = LoadedLog(
        path=Path("data/bpic17.xes.gz"),
        n_cases=6,
        n_events=len(tiny_log),
        attributes=["case:concept:name", "concept:name", "time:timestamp"],
        warnings=["contoh peringatan"],
    )
    panel.set_loaded(loaded)

    assert "bpic17.xes.gz" in panel.lbl_file.text()
    assert panel.lbl_cases.text() == "6"
    assert panel.attr_list.count() == 3
    assert "contoh peringatan" in panel.lbl_warnings.text()


def test_overview_panel_search_toggle_and_open_case(qtbot, tiny_log, tiny_durs):
    from app.panels.overview_panel import OverviewPanel

    panel = OverviewPanel()
    qtbot.addWidget(panel)
    panel.set_log(tiny_log, tiny_durs)

    assert panel.case_model.rowCount() == 6
    cols_no_lc = [
        panel.act_model.headerData(i, panel.act_view.horizontalHeader().orientation())
        for i in range(panel.act_model.columnCount())
    ]
    assert "Lifecycle" not in cols_no_lc

    panel.chk_lifecycle.setChecked(True)
    cols_with_lc = [
        panel.act_model.headerData(i, panel.act_view.horizontalHeader().orientation())
        for i in range(panel.act_model.columnCount())
    ]
    assert "Lifecycle" in cols_with_lc

    panel.search_case.setText("c6")
    assert panel.case_model.rowCount() == 1

    with qtbot.waitSignal(panel.open_case, timeout=1000) as blocker:
        panel._on_case_double_clicked(panel.case_model.index(0, 0))
    assert blocker.args == ["c6"]


def test_about_dialog_shows_library_versions(qtbot):
    from PySide6.QtWidgets import QLabel

    from app.panels.about_dialog import AboutDialog

    dlg = AboutDialog()
    qtbot.addWidget(dlg)
    labels = [lbl.text() for lbl in dlg.findChildren(QLabel)]
    joined = " ".join(labels)
    assert "BPIC17 Event Log Analyzer" in joined
    assert "Python:" in joined
    assert "PM4Py:" in joined
    assert "pandas:" in joined
    assert "PySide6:" in joined
