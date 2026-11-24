"""Struktur hasil analisis — KONTRAK BERSAMA (ubah hanya lewat kesepakatan kelompok).

Setiap fungsi ``run`` di ``analyses/`` mengembalikan ``AnalysisResult`` atau
``list[AnalysisResult]``. Panel GUI, Case Explorer, dan ekspor CSV hanya membaca struktur ini.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import pandas as pd


@dataclass
class AnalysisResult:
    """Satu jawaban soal beserta jejak buktinya.

    Field:
        code: kode soal, mis. "11.7A", "11.7C", "11.15", "11.18", "11.22", "OPT.fast".
        title: judul singkat untuk GUI, mis. "Successful cases".
        rule_text: aturan filter dalam bahasa Indonesia, persis seperti yang diterapkan
            kode (ditampilkan di GUI dan diekspor), mis. "Case memuat minimal satu event
            dengan activity = 'O_Accepted'".
        n_cases: jumlah case yang lolos (= ``len(case_ids)``; satu case dihitung sekali).
        denominator: jumlah seluruh case pada log aktif (pembagi persentase).
        percentage: ``n_cases / denominator * 100`` jika soal meminta persentase, selain itu
            None.
        mean_cycle_days: rata-rata ``durations`` (hari) atas ``case_ids``; None jika tidak
            diminta atau tidak ada case.
        case_ids: daftar case_id terpilih (unik, urutan deterministik).
        per_case: ringkasan satu baris per case terpilih; wajib punya kolom ``case_id``
            dan ``duration_days``, boleh kolom tambahan (mis. ``n_complete``, ``resource``).
        evidence: baris event dari DataFrame kanonik yang menjadi bukti; wajib memuat
            ketujuh kolom kanonik (terutama ``case_id`` dan ``orig_idx`` untuk highlight di
            Case Explorer), boleh kolom tambahan (mis. ``role`` = "cancelled"/"accepted").
        params: parameter yang dipakai (nama aktivitas, nilai lifecycle, ambang, dll.)
            agar hasil dapat direproduksi.
    """

    code: str
    title: str
    rule_text: str
    n_cases: int
    denominator: int
    percentage: Optional[float] = None
    mean_cycle_days: Optional[float] = None
    case_ids: list[str] = field(default_factory=list)
    per_case: pd.DataFrame = field(default_factory=pd.DataFrame)
    evidence: pd.DataFrame = field(default_factory=pd.DataFrame)
    params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Penjaga invarian "satu case dihitung sekali".
        if len(set(self.case_ids)) != len(self.case_ids):
            raise ValueError(f"{self.code}: case_ids mengandung duplikat")
        if self.n_cases != len(self.case_ids):
            raise ValueError(
                f"{self.code}: n_cases ({self.n_cases}) != len(case_ids) ({len(self.case_ids)})"
            )
        if self.n_cases > self.denominator:
            raise ValueError(f"{self.code}: n_cases melebihi denominator")
