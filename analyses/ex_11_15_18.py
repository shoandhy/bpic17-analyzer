"""Exercise 11.15 dan 11.18 (F04, F05).

Pemilik: Anggota C (feat/c-1115-1118).

Hasil yang dikembalikan ``run`` (list berisi 2 AnalysisResult):
    "11.15" case dengan aktivitas target (W_Assess Potential Fraud) berstatus COMPLETE
            minimal ``min_count`` kali. Hanya occurrence complete yang dihitung
            (schedule/start/abort tidak). per_case: case_id, duration_days, n_complete.
            evidence: event complete yang terhitung.
    "11.18" dari event complete tadi, case yang >= ``min_count`` complete-nya dilakukan
            resource yang SAMA. Resource NA dibuang sebelum dikelompokkan (NA tidak
            dianggap satu resource yang sama). per_case: case_id, duration_days, resource,
            n_complete_by_resource. evidence: event complete oleh resource tersebut.

TODO(C): verifikasi dari data (jangan menebak):
    * ejaan aktivitas target — bisa "W_Assess potential fraud" (huruf kecil) di BPIC17,
      berbeda dengan PDF;
    * nilai lifecycle yang berarti "complete" setelah di-lowercase oleh loader, dan
      tuliskan alasannya di rule_text / laporan.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from core.result import AnalysisResult

CANONICAL_COLS = [
    "case_id",
    "activity",
    "timestamp",
    "lifecycle",
    "resource",
    "orig_idx",
    "event_pos",
]

DEFAULT_PARAMS: dict[str, object] = {
    # TODO(C): ejaan disalin dari PDF instruksi; cek ejaan asli di BPIC17.
    "target_activity": "W_Assess potential fraud",
    # TODO(C): isi dengan nilai lifecycle "complete" yang benar-benar ada di data.
    "complete_lifecycle": "complete",
    "min_count": 2,
}


def _resolve_complete_lifecycle(
    df: pd.DataFrame, complete_lifecycle: Optional[str]
) -> Optional[str]:
    if complete_lifecycle is not None and str(complete_lifecycle).strip() != "":
        return str(complete_lifecycle).strip().lower()
    if "lifecycle" not in df.columns or df.empty:
        return "complete"
    non_null = df["lifecycle"].dropna().astype(str).str.strip().str.lower()
    if (non_null == "complete").any():
        return "complete"
    return None


def complete_events(
    df: pd.DataFrame, target_activity: str, complete_lifecycle: Optional[str]
) -> pd.DataFrame:
    """Baris event aktivitas target yang berstatus complete (dipakai 11.15 & 11.18).

    Pemilik: Anggota C.
    """
    if df.empty:
        return pd.DataFrame(columns=list(df.columns))

    work = df.copy()
    target_norm = str(target_activity).strip().lower()
    act_mask = work["activity"].astype(str).str.strip().str.lower() == target_norm

    resolved_lc = _resolve_complete_lifecycle(work, complete_lifecycle)
    if resolved_lc is not None and "lifecycle" in work.columns:
        lc_series = work["lifecycle"].where(work["lifecycle"].notna(), None)
        lc_mask = lc_series.apply(
            lambda v: v is not None and str(v).strip().lower() == resolved_lc
        )
    else:
        lc_mask = pd.Series(True, index=work.index)

    return work.loc[act_mask & lc_mask].copy()


def _mean_duration(durations: pd.Series, case_ids: list[str]) -> Optional[float]:
    if not case_ids or durations.empty:
        return None
    vals = durations.reindex(case_ids).dropna()
    if vals.empty:
        return None
    return float(vals.mean())


def _empty_evidence(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in CANONICAL_COLS if c in df.columns] or CANONICAL_COLS
    return pd.DataFrame(columns=cols)


def run(df: pd.DataFrame, durations: pd.Series, **params) -> list[AnalysisResult]:
    """Hitung 11.15 dan 11.18. Pemilik: Anggota C."""
    effective_params: dict[str, object] = {
        "target_activity": params.get("target_activity", DEFAULT_PARAMS["target_activity"]),
        "complete_lifecycle": params.get(
            "complete_lifecycle", DEFAULT_PARAMS["complete_lifecycle"]
        ),
        "min_count": int(params.get("min_count", DEFAULT_PARAMS["min_count"])),
    }

    target_activity = str(effective_params["target_activity"])
    raw_lc = effective_params["complete_lifecycle"]
    complete_lc_param: Optional[str] = None if raw_lc is None else str(raw_lc)
    min_count = int(effective_params["min_count"])
    if min_count < 1:
        raise ValueError("min_count harus >= 1")

    all_case_ids = (
        list(dict.fromkeys(df["case_id"].astype(str).tolist()))
        if (not df.empty and "case_id" in df.columns)
        else []
    )
    denominator = len(all_case_ids)

    resolved_lc = _resolve_complete_lifecycle(df, complete_lc_param)
    comp_df = complete_events(df, target_activity, resolved_lc)
    if not comp_df.empty and "case_id" in comp_df.columns:
        comp_df = comp_df.copy()
        comp_df["case_id"] = comp_df["case_id"].astype(str)

    lc_desc = (
        f"lifecycle == '{resolved_lc}' (setelah normalisasi lowercase oleh loader)"
        if resolved_lc is not None
        else "seluruh event aktivitas target (kolom lifecycle tidak tersedia / 'complete' tidak ditemukan)"
    )

    # --- 11.15 ---
    if comp_df.empty:
        selected_1115: list[str] = []
        per_case_1115 = pd.DataFrame(columns=["case_id", "duration_days", "n_complete"])
        ev_1115 = _empty_evidence(df)
    else:
        counts_1115 = comp_df.groupby("case_id", sort=False).size()
        qual_1115 = set(counts_1115[counts_1115 >= min_count].index.astype(str))
        selected_1115 = [cid for cid in all_case_ids if cid in qual_1115]
        ev_1115 = comp_df[comp_df["case_id"].isin(selected_1115)].copy()

        rows_1115 = []
        for cid in selected_1115:
            dur = (
                float(durations.loc[cid])
                if (not durations.empty and cid in durations.index)
                else float("nan")
            )
            rows_1115.append(
                {
                    "case_id": cid,
                    "duration_days": dur,
                    "n_complete": int(counts_1115.loc[cid]),
                }
            )
        per_case_1115 = pd.DataFrame(
            rows_1115, columns=["case_id", "duration_days", "n_complete"]
        )

    rule_1115 = (
        f"Case dengan aktivitas '{target_activity}' (pencocokan mengabaikan kapitalisasi huruf) "
        f"berstatus {lc_desc} minimal {min_count} kali dalam satu case; event non-complete "
        f"(schedule/start/abort/withdraw) tidak dihitung dan setiap case dihitung satu kali."
    )

    res_1115 = AnalysisResult(
        code="11.15",
        title="Repeated fraud assessment completions",
        rule_text=rule_1115,
        n_cases=len(selected_1115),
        denominator=denominator,
        percentage=None,
        mean_cycle_days=_mean_duration(durations, selected_1115),
        case_ids=selected_1115,
        per_case=per_case_1115,
        evidence=ev_1115,
        params=effective_params,
    )

    # --- 11.18 ---
    if comp_df.empty or "resource" not in comp_df.columns:
        selected_1118: list[str] = []
        per_case_1118 = pd.DataFrame(
            columns=["case_id", "duration_days", "resource", "n_complete_by_resource"]
        )
        ev_1118 = _empty_evidence(df)
    else:
        res_series = comp_df["resource"].where(comp_df["resource"].notna(), None)
        valid_mask = res_series.apply(
            lambda r: r is not None and not pd.isna(r) and str(r).strip() != ""
        )
        valid_res = comp_df.loc[valid_mask].copy()

        if valid_res.empty:
            selected_1118 = []
            per_case_1118 = pd.DataFrame(
                columns=["case_id", "duration_days", "resource", "n_complete_by_resource"]
            )
            ev_1118 = _empty_evidence(df)
        else:
            valid_res["_res_key"] = valid_res["resource"].astype(str).str.strip()
            grouped = (
                valid_res.groupby(["case_id", "_res_key"], sort=False)
                .size()
                .reset_index(name="n_complete_by_resource")
            )
            qual_pairs = grouped[grouped["n_complete_by_resource"] >= min_count].copy()
            qual_cases = set(qual_pairs["case_id"].astype(str))
            selected_1118 = [cid for cid in all_case_ids if cid in qual_cases]

            allowed_pairs = set(
                zip(qual_pairs["case_id"].astype(str), qual_pairs["_res_key"].astype(str))
            )
            ev_mask = [
                (str(c), str(r)) in allowed_pairs
                for c, r in zip(valid_res["case_id"], valid_res["_res_key"])
            ]
            ev_1118 = valid_res.loc[ev_mask].drop(columns=["_res_key"]).copy()

            rows_1118 = []
            for cid in selected_1118:
                dur = (
                    float(durations.loc[cid])
                    if (not durations.empty and cid in durations.index)
                    else float("nan")
                )
                sub = qual_pairs[qual_pairs["case_id"] == cid]
                for _, prow in sub.iterrows():
                    rows_1118.append(
                        {
                            "case_id": cid,
                            "duration_days": dur,
                            "resource": prow["_res_key"],
                            "n_complete_by_resource": int(prow["n_complete_by_resource"]),
                        }
                    )
            per_case_1118 = pd.DataFrame(
                rows_1118,
                columns=["case_id", "duration_days", "resource", "n_complete_by_resource"],
            )

    rule_1118 = (
        f"Case dengan aktivitas '{target_activity}' berstatus {lc_desc} minimal {min_count} kali "
        f"oleh resource yang sama dalam satu case; nilai resource kosong/NA dibuang sebelum "
        f"dikelompokkan sehingga resource NA tidak dianggap sebagai resource yang sama."
    )

    res_1118 = AnalysisResult(
        code="11.18",
        title="Repeated fraud assessment completions by same resource",
        rule_text=rule_1118,
        n_cases=len(selected_1118),
        denominator=denominator,
        percentage=None,
        mean_cycle_days=_mean_duration(durations, selected_1118),
        case_ids=selected_1118,
        per_case=per_case_1118,
        evidence=ev_1118,
        params=effective_params,
    )

    return [res_1115, res_1118]