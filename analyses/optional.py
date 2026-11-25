"""Fitur opsional: fast cases (< ambang hari) vs slow cases (>= ambang hari) + histogram durasi.

Pemilik: Anggota D (feat/d-1122-fixtures). Mengacu Example 11.10 (ambang default 45 hari).

Hasil ``run`` (list berisi 2 AnalysisResult): ``"OPT.fast"`` dan ``"OPT.slow"``.
Fitur ini tidak menggantikan soal wajib dan disajikan terpisah dari jawaban wajib.
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd

from core.result import AnalysisResult
from core.schema import CANONICAL_COLUMNS, DURATION_NAME

DEFAULT_PARAMS: dict[str, float] = {"threshold_days": 45.0}


def _normalize_durations(durations: pd.Series) -> pd.Series:
    dur = durations.copy()
    dur.index = dur.index.astype(str)
    dur.name = DURATION_NAME
    return dur


def _canonical_columns_of(df: pd.DataFrame) -> list[str]:
    canonical = [c for c in CANONICAL_COLUMNS if c in df.columns]
    extras = [c for c in df.columns if c not in canonical]
    return [*canonical, *extras]


def _boundary_evidence(df: pd.DataFrame, case_ids: list[str]) -> pd.DataFrame:
    """Ambil event awal dan akhir tiap case (penentu durasi) sebagai evidence tanpa duplikasi."""
    cols = _canonical_columns_of(df)
    if not case_ids or df.empty:
        ev = df.iloc[0:0][cols].copy().reset_index(drop=True)
        ev["role"] = pd.Series(dtype="object")
        return ev

    sub = df.loc[df["case_id"].astype(str).isin(case_ids), cols].copy()
    sub["_cid_str"] = sub["case_id"].astype(str)
    sub = sub.sort_values(["_cid_str", "event_pos", "orig_idx"], kind="stable")

    grp = sub.groupby("_cid_str", sort=False)
    first_ev = grp.head(1).copy()
    last_ev = grp.tail(1).copy()

    # Jika satu case hanya punya 1 event, orig_idx awal == akhir -> gabung jadi "start/end".
    single_idx = set(first_ev["orig_idx"]).intersection(set(last_ev["orig_idx"]))
    first_ev["role"] = np.where(first_ev["orig_idx"].isin(single_idx), "start/end", "start")
    last_ev = last_ev.loc[~last_ev["orig_idx"].isin(single_idx)].copy()
    last_ev["role"] = "end"

    return (
        pd.concat([first_ev, last_ev], ignore_index=True)
        .sort_values(["_cid_str", "event_pos", "orig_idx"], kind="stable")
        .drop(columns=["_cid_str"])
        .reset_index(drop=True)
    )


def _build_per_case(
    case_ids: list[str], dur: pd.Series, event_counts: pd.Series
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "case_id": list(case_ids),
            DURATION_NAME: dur.reindex(case_ids).to_numpy(dtype="float64"),
            "n_events": event_counts.reindex(case_ids, fill_value=0).to_numpy(dtype="int64"),
        }
    )


def _mean_duration(case_ids: list[str], dur: pd.Series) -> Optional[float]:
    if not case_ids:
        return None
    sub = dur.reindex(case_ids).dropna()
    return float(sub.mean()) if not sub.empty else None


def run(df: pd.DataFrame, durations: pd.Series, **params) -> list[AnalysisResult]:
    """Bagi case menjadi fast (< threshold_days) dan slow (>= threshold_days).

    Pemilik: Anggota D. Mengembalikan ``[res_fast, res_slow]`` dengan kode
    ``"OPT.fast"`` dan ``"OPT.slow"``.
    """
    unknown = set(params) - set(DEFAULT_PARAMS)
    if unknown:
        raise TypeError(f"Parameter tidak dikenal untuk optional.run: {sorted(unknown)}")

    eff: dict[str, float] = {
        "threshold_days": float({**DEFAULT_PARAMS, **params}["threshold_days"]),
    }
    threshold = eff["threshold_days"]
    if threshold < 0:
        raise ValueError(f"threshold_days tidak boleh negatif, didapat {threshold}")

    dur = _normalize_durations(durations)
    if df.empty:
        all_case_ids: list[str] = []
        event_counts = pd.Series(dtype="int64")
    else:
        cid_series = df["case_id"].astype(str)
        all_case_ids = sorted(cid_series.unique().tolist())
        event_counts = cid_series.value_counts()

    denominator = len(all_case_ids)
    aligned = dur.reindex(all_case_ids).dropna()

    fast_ids = sorted(aligned.index[aligned < threshold].tolist())
    slow_ids = sorted(aligned.index[aligned >= threshold].tolist())

    fast_pct = (len(fast_ids) / denominator * 100.0) if denominator > 0 else None
    slow_pct = (len(slow_ids) / denominator * 100.0) if denominator > 0 else None

    res_fast = AnalysisResult(
        code="OPT.fast",
        title=f"Fast cases (< {threshold:g} hari)",
        rule_text=(
            f"[Opsional — Example 11.10] Case dengan durasi penuh (max(timestamp) − min(timestamp)) "
            f"< {threshold:g} hari. Persentase = {len(fast_ids)} / {denominator} × 100%."
        ),
        n_cases=len(fast_ids),
        denominator=denominator,
        percentage=fast_pct,
        mean_cycle_days=_mean_duration(fast_ids, dur),
        case_ids=fast_ids,
        per_case=_build_per_case(fast_ids, dur, event_counts),
        evidence=_boundary_evidence(df, fast_ids),
        params=dict(eff),
    )

    res_slow = AnalysisResult(
        code="OPT.slow",
        title=f"Slow cases (>= {threshold:g} hari)",
        rule_text=(
            f"[Opsional — Example 11.10] Case dengan durasi penuh (max(timestamp) − min(timestamp)) "
            f">= {threshold:g} hari. Persentase = {len(slow_ids)} / {denominator} × 100%."
        ),
        n_cases=len(slow_ids),
        denominator=denominator,
        percentage=slow_pct,
        mean_cycle_days=_mean_duration(slow_ids, dur),
        case_ids=slow_ids,
        per_case=_build_per_case(slow_ids, dur, event_counts),
        evidence=_boundary_evidence(df, slow_ids),
        params=dict(eff),
    )

    return [res_fast, res_slow]


def duration_histogram(
    durations: pd.Series,
    bins: int = 20,
    threshold_days: float = 45.0,
) -> dict[str, Any]:
    """Hitung data histogram durasi case (hari) tanpa ketergantungan GUI.

    Mengembalikan dict berisi:
        ``counts`` (np.ndarray int), ``bin_edges`` (np.ndarray float),
        ``table`` (DataFrame: ``bin_start``, ``bin_end``, ``count``, ``group``),
        ``threshold_days`` (float), ``n_fast`` (int), ``n_slow`` (int),
        serta statistik ringkas (``min``, ``median``, ``mean``, ``p90``, ``max``).
    """
    if bins < 1:
        raise ValueError(f"bins harus >= 1, didapat {bins}")
    if threshold_days < 0:
        raise ValueError(f"threshold_days tidak boleh negatif, didapat {threshold_days}")

    vals = pd.to_numeric(durations, errors="coerce").dropna().to_numpy(dtype="float64")
    if vals.size == 0:
        empty_tbl = pd.DataFrame(columns=["bin_start", "bin_end", "count", "group"])
        return {
            "counts": np.array([], dtype="int64"),
            "bin_edges": np.array([], dtype="float64"),
            "table": empty_tbl,
            "threshold_days": float(threshold_days),
            "n_fast": 0,
            "n_slow": 0,
            "min": None,
            "median": None,
            "mean": None,
            "p90": None,
            "max": None,
        }

    lo = float(vals.min())
    hi = float(vals.max())
    if lo == hi:
        edges = np.array([lo, lo + 1.0], dtype="float64")
        counts = np.array([int(vals.size)], dtype="int64")
    else:
        counts, edges = np.histogram(vals, bins=bins)
        counts = counts.astype("int64")

    starts = edges[:-1]
    ends = edges[1:]
    midpoints = (starts + ends) / 2.0
    groups = np.where(midpoints < threshold_days, "fast", "slow")

    table = pd.DataFrame(
        {
            "bin_start": starts,
            "bin_end": ends,
            "count": counts,
            "group": groups,
        }
    )

    return {
        "counts": counts,
        "bin_edges": edges,
        "table": table,
        "threshold_days": float(threshold_days),
        "n_fast": int((vals < threshold_days).sum()),
        "n_slow": int((vals >= threshold_days).sum()),
        "min": lo,
        "median": float(np.median(vals)),
        "mean": float(np.mean(vals)),
        "p90": float(np.percentile(vals, 90)),
        "max": hi,
    }


def compare_fast_slow(
    df: pd.DataFrame,
    durations: pd.Series,
    threshold_days: float = 45.0,
) -> pd.DataFrame:
    """Bandingkan karakteristik ringkas antara kelompok fast (< ambang) dan slow (>= ambang)."""
    dur = _normalize_durations(durations)
    cols = [
        "group",
        "n_cases",
        "percentage",
        "mean_duration_days",
        "median_duration_days",
        "mean_events",
        "accepted_rate_pct",
        "refused_rate_pct",
    ]
    if df.empty:
        return pd.DataFrame(columns=cols)

    cid_series = df["case_id"].astype(str)
    all_ids = sorted(cid_series.unique().tolist())
    total = len(all_ids)
    aligned = dur.reindex(all_ids).dropna()
    event_counts = cid_series.value_counts()

    acc_cases = set(df.loc[df["activity"] == "O_Accepted", "case_id"].astype(str).unique())
    ref_cases = set(df.loc[df["activity"] == "O_Refused", "case_id"].astype(str).unique())

    rows: list[dict[str, Any]] = []
    for label, ids in (
        (f"Fast (< {threshold_days:g} hari)", sorted(aligned.index[aligned < threshold_days].tolist())),
        (f"Slow (>= {threshold_days:g} hari)", sorted(aligned.index[aligned >= threshold_days].tolist())),
    ):
        n = len(ids)
        sub_dur = aligned.reindex(ids)
        sub_ev = event_counts.reindex(ids, fill_value=0)
        n_acc = sum(1 for c in ids if c in acc_cases)
        n_ref = sum(1 for c in ids if c in ref_cases)
        rows.append(
            {
                "group": label,
                "n_cases": n,
                "percentage": (n / total * 100.0) if total else 0.0,
                "mean_duration_days": float(sub_dur.mean()) if n else None,
                "median_duration_days": float(sub_dur.median()) if n else None,
                "mean_events": float(sub_ev.mean()) if n else None,
                "accepted_rate_pct": (n_acc / n * 100.0) if n else None,
                "refused_rate_pct": (n_ref / n * 100.0) if n else None,
            }
        )
    return pd.DataFrame(rows, columns=cols)
