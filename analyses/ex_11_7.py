"""Exercise 11.7 A–E (F03).

Pemilik: Anggota B (feat/b-117).

Hasil yang dikembalikan ``run`` (list berisi 5 AnalysisResult, urutan tetap):
    "11.7A" jumlah seluruh case (case unik, bukan event).
    "11.7B" rata-rata cycle time seluruh case (hari).
    "11.7C" successful: case memuat >= 1 event O_Accepted (contains).
    "11.7D" unsuccessful: case memuat >= 1 event O_Refused (contains; boleh tumpang tindih
            dengan C).
    "11.7E" canceled: event TERAKHIR trace (event_pos maksimum) adalah O_Cancelled
            (endpoint; bukan sekadar pernah muncul).

Aturan: hitung di level case (satu case sekali); mean cycle time diambil dari ``durations``
(seluruh event case), bukan dari event hasil filter. Tidak boleh ada angka jawaban
hard-coded.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from core.result import AnalysisResult
from core.schema import CANONICAL_COLUMNS, DURATION_NAME

DEFAULT_PARAMS: dict[str, str] = {
    "accepted_activity": "O_Accepted",
    "refused_activity": "O_Refused",
    "cancelled_activity": "O_Cancelled",
}


def filter_contains(df: pd.DataFrame, activity: str) -> set[str]:
    """Kembalikan himpunan case_id yang memuat minimal satu event dengan ``activity``.

    Hitung di level case: satu case hanya masuk satu kali walau event muncul berkali-kali.
    """
    if df.empty:
        return set()
    mask = df["activity"] == activity
    return {str(c) for c in df.loc[mask, "case_id"].unique()}


def filter_endpoint(
    df: pd.DataFrame, activity: str, position: str = "last"
) -> set[str]:
    """Kembalikan himpunan case_id yang event pertama/terakhirnya adalah ``activity``.

    Event terakhir ditentukan oleh ``event_pos`` maksimum per case (atau ``event_pos == 0``
    untuk ``position='first'``) sesuai urutan kanonik DataFrame.
    """
    if position not in ("last", "first"):
        raise ValueError(f"position harus 'last' atau 'first', didapat {position!r}")
    if df.empty:
        return set()
    ordered = df.sort_values(["case_id", "event_pos"], kind="stable")
    endpoints = (
        ordered.groupby("case_id", sort=False).tail(1)
        if position == "last"
        else ordered.groupby("case_id", sort=False).head(1)
    )
    matched = endpoints.loc[endpoints["activity"] == activity, "case_id"].unique()
    return {str(c) for c in matched}


def _normalize_durations(durations: pd.Series) -> pd.Series:
    """Salin ``durations`` dengan index bertipe ``str`` tanpa memodifikasi input asli."""
    dur = durations.copy()
    dur.index = dur.index.astype(str)
    dur.name = DURATION_NAME
    return dur


def _build_per_case(
    case_ids: list[str],
    dur: pd.Series,
    extra_col: Optional[tuple[str, pd.Series]] = None,
) -> pd.DataFrame:
    """Susun DataFrame ringkasan satu baris per case terpilih (``case_id``, ``duration_days``)."""
    sub = dur.reindex(case_ids)
    per_case = pd.DataFrame(
        {
            "case_id": list(case_ids),
            DURATION_NAME: sub.to_numpy(dtype="float64"),
        }
    )
    if extra_col is not None:
        col_name, series = extra_col
        s = series.copy()
        s.index = s.index.astype(str)
        per_case[col_name] = s.reindex(case_ids, fill_value=0).to_numpy()
    return per_case


def _mean_duration(case_ids: list[str], dur: pd.Series) -> Optional[float]:
    """Hitung rata-rata cycle time (hari) dari ``durations`` utuh untuk ``case_ids``."""
    if not case_ids:
        return None
    sub = dur.reindex(case_ids).dropna()
    if sub.empty:
        return None
    return float(sub.mean())


def _canonical_slice(df: pd.DataFrame, mask: pd.Series) -> pd.DataFrame:
    """Ambil baris bukti dari ``df`` dengan kolom kanonik tanpa memodifikasi ``df``."""
    cols = [c for c in CANONICAL_COLUMNS if c in df.columns]
    extras = [c for c in df.columns if c not in cols]
    return df.loc[mask, [*cols, *extras]].copy().reset_index(drop=True)


def run(df: pd.DataFrame, durations: pd.Series, **params) -> list[AnalysisResult]:
    """Hitung Exercise 11.7 A–E pada level case. Pemilik: Anggota B.

    Mengembalikan 5 ``AnalysisResult`` dengan kode ``11.7A`` s.d. ``11.7E``.
    """
    unknown = set(params) - set(DEFAULT_PARAMS)
    if unknown:
        raise TypeError(f"Parameter tidak dikenal untuk ex_11_7.run: {sorted(unknown)}")

    eff: dict[str, str] = {
        k: str(v) for k, v in {**DEFAULT_PARAMS, **params}.items()
    }
    acc_act = eff["accepted_activity"]
    ref_act = eff["refused_activity"]
    can_act = eff["cancelled_activity"]

    dur = _normalize_durations(durations)
    all_case_ids = sorted({str(c) for c in df["case_id"].unique()}) if not df.empty else []
    denominator = len(all_case_ids)
    all_per_case = _build_per_case(all_case_ids, dur)
    all_mean = _mean_duration(all_case_ids, dur)
    empty_evidence = df.iloc[0:0].copy().reset_index(drop=True)

    # 11.7A — Jumlah seluruh case di log
    res_a = AnalysisResult(
        code="11.7A",
        title="Jumlah seluruh case (pengajuan pinjaman)",
        rule_text="Seluruh case unik (case_id unik) di dalam event log aktif.",
        n_cases=denominator,
        denominator=denominator,
        percentage=None,
        mean_cycle_days=all_mean,
        case_ids=list(all_case_ids),
        per_case=all_per_case.copy(),
        evidence=empty_evidence.copy(),
        params=dict(eff),
    )

    # 11.7B — Rata-rata cycle time seluruh case (hari)
    res_b = AnalysisResult(
        code="11.7B",
        title="Rata-rata cycle time seluruh case",
        rule_text=(
            "Rata-rata durasi seluruh case dalam hari, dengan durasi tiap case = "
            "max(timestamp) - min(timestamp) dari seluruh event pada case tersebut."
        ),
        n_cases=denominator,
        denominator=denominator,
        percentage=None,
        mean_cycle_days=all_mean,
        case_ids=list(all_case_ids),
        per_case=all_per_case.copy(),
        evidence=empty_evidence.copy(),
        params=dict(eff),
    )

    # 11.7C — Successful cases (contains >= 1 accepted_activity)
    c_ids = sorted(filter_contains(df, acc_act))
    c_mask = (df["case_id"].astype(str).isin(c_ids)) & (df["activity"] == acc_act)
    c_ev = _canonical_slice(df, c_mask)
    c_counts = c_ev.groupby(c_ev["case_id"].astype(str)).size() if not c_ev.empty else pd.Series(dtype="int64")
    res_c = AnalysisResult(
        code="11.7C",
        title=f"Successful cases (memuat {acc_act})",
        rule_text=(
            f"Case memuat minimal 1 event dengan activity = '{acc_act}' (contains; "
            "dihitung di level case, satu case sekali; cycle time dari seluruh event case)."
        ),
        n_cases=len(c_ids),
        denominator=denominator,
        percentage=None,
        mean_cycle_days=_mean_duration(c_ids, dur),
        case_ids=c_ids,
        per_case=_build_per_case(c_ids, dur, ("n_matching_events", c_counts)),
        evidence=c_ev,
        params=dict(eff),
    )

    # 11.7D — Unsuccessful cases (contains >= 1 refused_activity)
    d_ids = sorted(filter_contains(df, ref_act))
    d_mask = (df["case_id"].astype(str).isin(d_ids)) & (df["activity"] == ref_act)
    d_ev = _canonical_slice(df, d_mask)
    d_counts = d_ev.groupby(d_ev["case_id"].astype(str)).size() if not d_ev.empty else pd.Series(dtype="int64")
    res_d = AnalysisResult(
        code="11.7D",
        title=f"Unsuccessful cases (memuat {ref_act})",
        rule_text=(
            f"Case memuat minimal 1 event dengan activity = '{ref_act}' (contains; "
            "boleh tumpang tindih dengan 11.7C; dihitung satu case sekali; cycle time dari seluruh event case)."
        ),
        n_cases=len(d_ids),
        denominator=denominator,
        percentage=None,
        mean_cycle_days=_mean_duration(d_ids, dur),
        case_ids=d_ids,
        per_case=_build_per_case(d_ids, dur, ("n_matching_events", d_counts)),
        evidence=d_ev,
        params=dict(eff),
    )

    # 11.7E — Canceled cases (event terakhir trace adalah cancelled_activity)
    e_ids = sorted(filter_endpoint(df, can_act, position="last"))
    if not df.empty and e_ids:
        ordered = df.sort_values(["case_id", "event_pos"], kind="stable")
        last_events = ordered.groupby("case_id", sort=False).tail(1)
        e_ev = (
            last_events.loc[last_events["case_id"].astype(str).isin(e_ids)]
            .copy()
            .reset_index(drop=True)
        )
    else:
        e_ev = empty_evidence.copy()
    res_e = AnalysisResult(
        code="11.7E",
        title=f"Canceled cases (berakhir dengan {can_act})",
        rule_text=(
            f"Event terakhir trace (event_pos maksimum) memiliki activity = '{can_act}' "
            "(endpoint; bukan sekadar pernah muncul di tengah trace; cycle time dari seluruh event case)."
        ),
        n_cases=len(e_ids),
        denominator=denominator,
        percentage=None,
        mean_cycle_days=_mean_duration(e_ids, dur),
        case_ids=e_ids,
        per_case=_build_per_case(e_ids, dur),
        evidence=e_ev,
        params=dict(eff),
    )

    return [res_a, res_b, res_c, res_d, res_e]
