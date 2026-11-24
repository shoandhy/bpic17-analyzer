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

TODO(B): verifikasi ejaan nama aktivitas langsung dari data (daftar dari Anggota A).
Nama di bawah hanya disalin dari PDF instruksi dan belum dicek terhadap BPIC17.
"""

from __future__ import annotations

import pandas as pd

from core.result import AnalysisResult

# TODO(B): cek ejaan asli di BPIC17 sebelum dipakai.
DEFAULT_PARAMS: dict[str, str] = {
    "accepted_activity": "O_Accepted",
    "refused_activity": "O_Refused",
    "cancelled_activity": "O_Cancelled",
}


def run(df: pd.DataFrame, durations: pd.Series, **params) -> list[AnalysisResult]:
    """Hitung 11.7 A–E. Pemilik: Anggota B."""
    raise NotImplementedError("Anggota B: analyses.ex_11_7.run")
