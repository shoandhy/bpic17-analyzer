"""Fixture pytest bersama."""

from __future__ import annotations

import os

import pandas as pd
import pytest

# GUI test berjalan tanpa layar (CI / SSH).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from tests.fixtures.dummy_results import make_dummy_results  # noqa: E402
from tests.fixtures.tiny_log import make_tiny_log, tiny_durations  # noqa: E402


@pytest.fixture
def tiny_log() -> pd.DataFrame:
    return make_tiny_log()


@pytest.fixture
def tiny_durs(tiny_log: pd.DataFrame) -> pd.Series:
    return tiny_durations(tiny_log)


@pytest.fixture
def dummy_results(tiny_log, tiny_durs):
    return make_dummy_results(tiny_log, tiny_durs)
