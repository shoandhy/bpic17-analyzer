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

DEFAULT_PARAMS: dict[str, object] = {
    # TODO(C): ejaan disalin dari PDF instruksi; cek ejaan asli di BPIC17.
    "target_activity": "W_Assess Potential Fraud",
    # TODO(C): isi dengan nilai lifecycle "complete" yang benar-benar ada di data.
    "complete_lifecycle": None,
    "min_count": 2,
}


def run(df: pd.DataFrame, durations: pd.Series, **params) -> list[AnalysisResult]:
    """Hitung 11.15 dan 11.18. Pemilik: Anggota C."""
    raise NotImplementedError("Anggota C: analyses.ex_11_15_18.run")


def complete_events(
    df: pd.DataFrame, target_activity: str, complete_lifecycle: Optional[str]
) -> pd.DataFrame:
    """Baris event aktivitas target yang berstatus complete (dipakai 11.15 & 11.18).

    Pemilik: Anggota C.
    """
    raise NotImplementedError("Anggota C: analyses.ex_11_15_18.complete_events")
