"""AnalysisResult palsu untuk mengembangkan GUI/ekspor sebelum modul analisis selesai.

Dibangun dari ``tiny_log.EXPECTED`` (ekspektasi test), BUKAN dari logika analisis.
"""

from __future__ import annotations

import pandas as pd

from core.result import AnalysisResult
from core.schema import DURATION_NAME
from tests.fixtures.tiny_log import EXPECTED


def make_dummy_results(df: pd.DataFrame, durations: pd.Series) -> list[AnalysisResult]:
    """Satu AnalysisResult dummy per kode di EXPECTED."""
    total = int(df["case_id"].nunique())
    results: list[AnalysisResult] = []
    for code, cases in EXPECTED.items():
        case_ids = sorted(cases)
        sub = durations.loc[case_ids]
        per_case = sub.rename(DURATION_NAME).rename_axis("case_id").reset_index()
        evidence = df[df["case_id"].isin(case_ids)].groupby("case_id").tail(1)
        results.append(
            AnalysisResult(
                code=code,
                title=f"Dummy {code}",
                rule_text=f"[DUMMY] aturan untuk {code}",
                n_cases=len(case_ids),
                denominator=total,
                percentage=len(case_ids) / total * 100 if code == "11.22" else None,
                mean_cycle_days=float(sub.mean()) if case_ids else None,
                case_ids=case_ids,
                per_case=per_case,
                evidence=evidence.reset_index(drop=True),
                params={},  # dummy tidak berasal dari run(); kontrak v2: hanya argumen efektif
            )
        )
    return results
