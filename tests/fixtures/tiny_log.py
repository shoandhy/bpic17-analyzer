"""Log kanonik kecil (6 case) — fixture SEMENTARA sampai Anggota D menyelesaikan
``tests/fixtures/make_synthetic.py``.

Nilai lifecycle memakai model lifecycle standar XES (schedule/start/complete, lowercase
sesuai kontrak). Ejaan aktivitas mengikuti PDF instruksi, BUKAN hasil verifikasi BPIC17.

Skenario (Instruksi Bagian 8):
    c1  O_Accepted dua kali                                -> 11.7C dihitung sekali
    c2  O_Cancelled di tengah, ada event sesudahnya        -> tidak masuk 11.7E
    c3  O_Refused dan O_Accepted                           -> masuk 11.7C dan 11.7D
    c4  W_Assess dijadwalkan 2x, complete hanya 1x;
        berakhir O_Cancelled                               -> tidak 11.15; masuk 11.7E
    c5  W_Assess complete 3x (R1, R2, NA);
        O_Cancelled -> aktivitas lain -> O_Accepted        -> 11.15 ya, 11.18 tidak, 11.22 ya
    c6  W_Assess complete 2x oleh R3; O_Accepted dan
        O_Cancelled ber-timestamp SAMA (accepted lebih dulu
        di file) lalu berakhir O_Cancelled                 -> 11.15 & 11.18 ya, 11.22 tidak,
                                                              masuk 11.7E (uji tie-break)
"""

from __future__ import annotations

import pandas as pd

from core.schema import CANONICAL_COLUMNS, DURATION_NAME, SORT_KEYS

FRAUD = "W_Assess Potential Fraud"
NA = pd.NA

# (case_id, activity, offset_jam, lifecycle, resource) dalam URUTAN FILE (-> orig_idx).
# Sengaja diselang-seling antar case agar sort kanonik benar-benar diuji.
_RAW_EVENTS: list[tuple] = [
    ("c1", "A_Create Application", 0, "complete", "R1"),
    ("c2", "A_Create Application", 0, "complete", "R1"),
    ("c1", "O_Accepted", 24, "complete", "R1"),
    ("c3", "A_Create Application", 0, "complete", "R2"),
    ("c1", "O_Accepted", 48, "complete", "R2"),
    ("c2", "O_Cancelled", 24, "complete", "R2"),
    ("c3", "O_Refused", 24, "complete", "R2"),
    ("c2", "W_Validate application", 72, "complete", "R3"),
    ("c1", "W_Validate application", 120, "complete", "R1"),
    ("c3", "O_Accepted", 48, "complete", "R1"),
    ("c4", "A_Create Application", 0, "complete", "R1"),
    ("c4", FRAUD, 1, "schedule", NA),
    ("c4", FRAUD, 2, "schedule", NA),
    ("c4", FRAUD, 3, "start", "R1"),
    ("c4", FRAUD, 4, "complete", "R1"),
    ("c4", "O_Cancelled", 240, "complete", "R2"),
    ("c5", "A_Create Application", 0, "complete", "R1"),
    ("c5", FRAUD, 5, "complete", "R1"),
    ("c5", FRAUD, 10, "complete", "R2"),
    ("c5", FRAUD, 15, "complete", NA),
    ("c5", "O_Cancelled", 30, "complete", "R2"),
    ("c5", "W_Call after offers", 40, "complete", "R3"),
    ("c5", "O_Accepted", 50, "complete", "R3"),
    ("c6", "A_Create Application", 0, "complete", "R3"),
    ("c6", FRAUD, 6, "complete", "R3"),
    ("c6", "O_Accepted", 100, "complete", "R1"),
    ("c6", "O_Cancelled", 100, "complete", "R1"),  # timestamp sama dengan O_Accepted di atas
    ("c6", FRAUD, 12, "complete", "R3"),           # muncul belakangan di file, waktu lebih awal
]

#: Ekspektasi test (himpunan case_id per kode soal). Hanya untuk test.
EXPECTED: dict[str, set[str]] = {
    "11.7A": {"c1", "c2", "c3", "c4", "c5", "c6"},
    "11.7C": {"c1", "c3", "c5", "c6"},
    "11.7D": {"c3"},
    "11.7E": {"c4", "c6"},
    "11.15": {"c5", "c6"},
    "11.18": {"c6"},
    "11.22": {"c5"},
}

_BASE = pd.Timestamp("2016-01-01 09:00:00", tz="UTC")


def make_tiny_log() -> pd.DataFrame:
    """Bangun DataFrame kanonik 6 case (lolos ``core.schema.check_canonical``)."""
    df = pd.DataFrame(_RAW_EVENTS, columns=["case_id", "activity", "hours", "lifecycle", "resource"])
    df["timestamp"] = _BASE + pd.to_timedelta(df.pop("hours"), unit="h")
    df["resource"] = df["resource"].astype("object").where(df["resource"].notna(), pd.NA)
    df["orig_idx"] = range(len(df))
    df = df.sort_values(SORT_KEYS, kind="stable").reset_index(drop=True)
    df["event_pos"] = df.groupby("case_id", sort=False).cumcount().astype("int64")
    df["orig_idx"] = df["orig_idx"].astype("int64")
    return df[CANONICAL_COLUMNS]


def tiny_durations(df: pd.DataFrame) -> pd.Series:
    """Durasi referensi per case (hari) untuk test; implementasi resmi ada di core.durations."""
    g = df.groupby("case_id")["timestamp"]
    return ((g.max() - g.min()).dt.total_seconds() / 86400.0).rename(DURATION_NAME)
