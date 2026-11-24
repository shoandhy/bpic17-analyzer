"""Exercise 11.22 (F06).

Pemilik: Anggota D (feat/d-1122-fixtures).

Hasil ``run`` (satu AnalysisResult, code "11.22"):
    Case dipilih jika ada pasangan posisi i < j (``event_pos``) dengan event i = O_Cancelled
    dan event j = O_Accepted. Kedua event TIDAK harus bersebelahan, dan ini BUKAN sama dengan
    "case berakhir O_Cancelled" (itu 11.7E).
    percentage = n_cases / denominator * 100, denominator = jumlah seluruh case di log aktif.
    evidence: pasangan event bukti (kolom tambahan ``role`` = "cancelled" / "accepted").

Analisis level offer ID (jika dibuat) harus diberi code terpisah, mis. "11.22-offer", dan
TIDAK dicampur dengan jawaban soal.

TODO(D): verifikasi ejaan nama aktivitas langsung dari data.
"""

from __future__ import annotations

import pandas as pd

from core.result import AnalysisResult

# TODO(D): ejaan disalin dari PDF instruksi; cek ejaan asli di BPIC17.
DEFAULT_PARAMS: dict[str, str] = {
    "first_activity": "O_Cancelled",
    "then_activity": "O_Accepted",
}


def run(df: pd.DataFrame, durations: pd.Series, **params) -> AnalysisResult:
    """Hitung 11.22. Pemilik: Anggota D."""
    raise NotImplementedError("Anggota D: analyses.ex_11_22.run")
