"""Durasi (cycle time) per case dan ringkasan overview log.

Pemilik: Anggota A (feat/a-loader). Dipakai F02 dan semua analisis.

Kontrak:
    * Input: DataFrame kanonik UTUH (seluruh event, belum difilter).
    * Output ``compute_case_durations``: ``pd.Series`` float, index = case_id
      (unik, semua case di log), name = ``core.schema.DURATION_NAME`` ("duration_days").
    * Nilai = (timestamp maksimum - timestamp minimum) case, dalam HARI
      (``total_seconds() / 86400``). Case dengan satu event -> 0.0.
    * Analisis WAJIB memakai Series ini untuk mean cycle time, bukan menghitung ulang
      dari event hasil filter (filter level-event dapat memperpendek durasi secara keliru).
"""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from core.schema import DURATION_NAME


def compute_case_durations(df: pd.DataFrame) -> pd.Series:
    """Hitung durasi tiap case dalam hari dari seluruh event case. Pemilik: Anggota A."""
    if df.empty:
        s = pd.Series(dtype="float64", name=DURATION_NAME)
        s.index.name = "case_id"
        return s

    grouped = df.groupby("case_id", sort=False)["timestamp"]
    durations = (grouped.max() - grouped.min()).dt.total_seconds() / 86400.0
    durations = durations.astype("float64")
    durations.name = DURATION_NAME
    return durations


# Alias sesuai penamaan di prompt tugas Anggota A.
case_durations = compute_case_durations


def compute_overview(
    df: pd.DataFrame, durations: Optional[pd.Series] = None
) -> dict[str, Any]:
    """Hitung metrik overview (F02) dari DataFrame kanonik utuh.

    Mengembalikan dict berisi:
        - ``total_cases`` (int)
        - ``total_events`` (int)
        - ``min_timestamp`` (pd.Timestamp | None)
        - ``max_timestamp`` (pd.Timestamp | None)
        - ``mean_cycle_days`` (float | None)
        - ``median_cycle_days`` (float | None)
        - ``max_cycle_days`` (float | None)
        - ``activity_freq`` (pd.DataFrame: activity, count, percentage)
        - ``activity_lifecycle_freq`` (pd.DataFrame: activity, lifecycle, count, percentage)
        - ``case_table`` (pd.DataFrame: case_id, n_events, duration_days)
    """
    if durations is None:
        durations = compute_case_durations(df)

    total_events = int(len(df))
    total_cases = int(df["case_id"].nunique()) if total_events else 0

    if total_events == 0:
        return {
            "total_cases": 0,
            "total_events": 0,
            "min_timestamp": None,
            "max_timestamp": None,
            "mean_cycle_days": None,
            "median_cycle_days": None,
            "max_cycle_days": None,
            "activity_freq": pd.DataFrame(columns=["activity", "count", "percentage"]),
            "activity_lifecycle_freq": pd.DataFrame(
                columns=["activity", "lifecycle", "count", "percentage"]
            ),
            "case_table": pd.DataFrame(columns=["case_id", "n_events", "duration_days"]),
        }

    min_ts = df["timestamp"].min()
    max_ts = df["timestamp"].max()

    mean_days = float(durations.mean()) if len(durations) else None
    median_days = float(durations.median()) if len(durations) else None
    max_days = float(durations.max()) if len(durations) else None

    act_counts = (
        df.groupby("activity", sort=False)
        .size()
        .reset_index(name="count")
        .sort_values(["count", "activity"], ascending=[False, True], kind="stable")
        .reset_index(drop=True)
    )
    act_counts["percentage"] = act_counts["count"] / total_events * 100.0

    lc_series = df["lifecycle"].fillna("(tanpa lifecycle)")
    act_lc_counts = (
        df.assign(_lc=lc_series)
        .groupby(["activity", "_lc"], sort=False)
        .size()
        .reset_index(name="count")
        .rename(columns={"_lc": "lifecycle"})
        .sort_values(["count", "activity", "lifecycle"], ascending=[False, True, True], kind="stable")
        .reset_index(drop=True)
    )
    act_lc_counts["percentage"] = act_lc_counts["count"] / total_events * 100.0

    event_counts = df.groupby("case_id", sort=False).size().rename("n_events")
    case_table = pd.DataFrame(
        {
            "case_id": durations.index.astype(str),
            "n_events": event_counts.reindex(durations.index).astype("int64").to_numpy(),
            "duration_days": durations.to_numpy(),
        }
    )

    return {
        "total_cases": total_cases,
        "total_events": total_events,
        "min_timestamp": min_ts,
        "max_timestamp": max_ts,
        "mean_cycle_days": mean_days,
        "median_cycle_days": median_days,
        "max_cycle_days": max_days,
        "activity_freq": act_counts,
        "activity_lifecycle_freq": act_lc_counts,
        "case_table": case_table,
    }


overview = compute_overview
