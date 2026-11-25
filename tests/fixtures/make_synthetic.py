"""Log XES sintetis berisi SEMUA 8 skenario uji Instruksi Bagian 8 + hasil yang seharusnya.

Pemilik: Anggota D (feat/d-1122-fixtures). Dipakai semua anggota untuk menguji modulnya
secara independen maupun terpadu.

Skenario uji (12 case dengan ``case_id`` deskriptif):
    1. ``accepted_twice``                   (10 hari) — Bag. 8 #1: O_Accepted 2x -> 11.7C hitung sekali.
    2. ``cancel_middle``                    ( 5 hari) — Bag. 8 #2: O_Cancelled di tengah lalu event lain -> bukan 11.7E.
    3. ``refused_and_accepted``             ( 8 hari) — Bag. 8 #3: O_Refused & O_Accepted -> lolos 11.7C & 11.7D.
    4. ``fraud_scheduled_twice_one_complete`` (4 hari) — Bag. 8 #4: W_Assess Potential Fraud schedule 2x, complete 1x -> bukan 11.15.
    5. ``fraud_two_complete_diff_resource`` ( 6 hari) — Bag. 8 #5: 2x complete resource berbeda (R1, R2) -> lolos 11.15, bukan 11.18.
    6. ``fraud_two_complete_same_resource`` (12 hari) — Bag. 8 #6: 2x complete resource sama (R3) -> lolos 11.15 & 11.18.
    7. ``cancel_then_other_then_accepted``  (20 hari) — Bag. 8 #7: O_Cancelled -> aktivitas lain -> O_Accepted -> lolos 11.22.
    8. ``accepted_before_cancel_only``      (15 hari) — Bag. 8 #8: O_Accepted lalu O_Cancelled tanpa accepted sesudahnya -> bukan 11.22, lolos 11.7E.
    9. ``ends_with_cancel_only``            (60 hari) — Edge case: berakhir O_Cancelled tanpa O_Accepted -> lolos 11.7E, bukan 11.22, OPT.slow.
   10. ``fraud_missing_resource``           (45 hari) — Edge case: 2x complete resource NA -> lolos 11.15, bukan 11.18; tepat 45.0 hari -> OPT.slow.
   11. ``cancel_multi_then_accepted``       (50 hari) — Edge case: multiple O_Cancelled & O_Accepted -> 11.22 hitung sekali (bukti pertama & terakhir), OPT.slow.
   12. ``same_timestamp_tiebreak``          (10 hari) — Edge case: O_Accepted & O_Cancelled ber-timestamp sama (O_Accepted lebih dulu di file) -> lolos 11.7E, bukan 11.22.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from core.schema import CANONICAL_COLUMNS, DURATION_NAME, SORT_KEYS

FRAUD = "W_Assess Potential Fraud"
NA = pd.NA

#: Timestamp dasar deterministik (UTC).
BASE_TIMESTAMP = pd.Timestamp("2026-01-01 00:00:00", tz="UTC")

#: Deskripsi singkat tiap case sintetis (dipakai di expected.json dan dokumentasi demo).
SCENARIO_DESCRIPTIONS: dict[str, str] = {
    "accepted_twice": "Bag. 8 #1: Satu case memiliki O_Accepted dua kali -> 11.7C menghitung case satu kali.",
    "cancel_middle": "Bag. 8 #2: O_Cancelled di tengah dan ada event sesudahnya -> 11.7E tidak menganggapnya canceled.",
    "refused_and_accepted": "Bag. 8 #3: Memiliki O_Refused dan O_Accepted -> lolos kedua filter contains (11.7C & 11.7D).",
    "fraud_scheduled_twice_one_complete": "Bag. 8 #4: W_Assess Potential Fraud dijadwalkan 2x tetapi complete hanya 1x -> tidak lolos 11.15.",
    "fraud_two_complete_diff_resource": "Bag. 8 #5: Dua complete W_Assess Potential Fraud dengan resource berbeda -> lolos 11.15, tidak lolos 11.18.",
    "fraud_two_complete_same_resource": "Bag. 8 #6: Dua complete W_Assess Potential Fraud oleh resource sama -> lolos 11.15 dan 11.18.",
    "cancel_then_other_then_accepted": "Bag. 8 #7: O_Cancelled diikuti aktivitas lain lalu O_Accepted -> lolos 11.22 meski tidak bertetangga.",
    "accepted_before_cancel_only": "Bag. 8 #8: O_Accepted mendahului O_Cancelled tanpa accepted sesudahnya -> tidak lolos 11.22 (lolos 11.7E).",
    "ends_with_cancel_only": "Edge case: Berakhir O_Cancelled tanpa O_Accepted (60 hari) -> lolos 11.7E & OPT.slow, tidak lolos 11.22.",
    "fraud_missing_resource": "Edge case: Dua complete dengan resource kosong/NA (tepat 45 hari) -> lolos 11.15 & OPT.slow, tidak lolos 11.18.",
    "cancel_multi_then_accepted": "Edge case: Beberapa O_Cancelled lalu beberapa O_Accepted (50 hari) -> 11.22 hitung 1x, bukti a pertama & b terakhir, OPT.slow.",
    "same_timestamp_tiebreak": "Edge case: O_Accepted dan O_Cancelled ber-timestamp sama (O_Accepted lebih dulu di file) -> lolos 11.7E, tidak lolos 11.22.",
}

# Format: (case_id, activity, offset_hari, lifecycle, resource)
# Urutan di dalam setiap trace dipertahankan saat menulis XES sehingga tie-break orig_idx konsisten.
_RAW_EVENTS: list[tuple[str, str, float, str, Any]] = [
    # 1. accepted_twice (durasi = 10 hari)
    ("accepted_twice", "A_Create Application", 0.0, "complete", "R1"),
    ("accepted_twice", "O_Accepted", 3.0, "complete", "R1"),
    ("accepted_twice", "O_Accepted", 6.0, "complete", "R2"),
    ("accepted_twice", "W_Validate application", 10.0, "complete", "R1"),
    # 2. cancel_middle (durasi = 5 hari)
    ("cancel_middle", "A_Create Application", 0.0, "complete", "R1"),
    ("cancel_middle", "O_Cancelled", 2.0, "complete", "R2"),
    ("cancel_middle", "W_Validate application", 5.0, "complete", "R3"),
    # 3. refused_and_accepted (durasi = 8 hari)
    ("refused_and_accepted", "A_Create Application", 0.0, "complete", "R1"),
    ("refused_and_accepted", "O_Refused", 3.0, "complete", "R2"),
    ("refused_and_accepted", "O_Accepted", 8.0, "complete", "R1"),
    # 4. fraud_scheduled_twice_one_complete (durasi = 4 hari)
    ("fraud_scheduled_twice_one_complete", "A_Create Application", 0.0, "complete", "R1"),
    ("fraud_scheduled_twice_one_complete", FRAUD, 1.0, "schedule", NA),
    ("fraud_scheduled_twice_one_complete", FRAUD, 2.0, "schedule", NA),
    ("fraud_scheduled_twice_one_complete", FRAUD, 3.0, "start", "R1"),
    ("fraud_scheduled_twice_one_complete", FRAUD, 4.0, "complete", "R1"),
    # 5. fraud_two_complete_diff_resource (durasi = 6 hari)
    ("fraud_two_complete_diff_resource", "A_Create Application", 0.0, "complete", "R1"),
    ("fraud_two_complete_diff_resource", FRAUD, 2.0, "complete", "R1"),
    ("fraud_two_complete_diff_resource", FRAUD, 4.0, "complete", "R2"),
    ("fraud_two_complete_diff_resource", "W_Validate application", 6.0, "complete", "R2"),
    # 6. fraud_two_complete_same_resource (durasi = 12 hari)
    ("fraud_two_complete_same_resource", "A_Create Application", 0.0, "complete", "R3"),
    ("fraud_two_complete_same_resource", FRAUD, 2.0, "complete", "R3"),
    ("fraud_two_complete_same_resource", FRAUD, 6.0, "complete", "R3"),
    ("fraud_two_complete_same_resource", "W_Validate application", 12.0, "complete", "R3"),
    # 7. cancel_then_other_then_accepted (durasi = 20 hari)
    ("cancel_then_other_then_accepted", "A_Create Application", 0.0, "complete", "R1"),
    ("cancel_then_other_then_accepted", "O_Cancelled", 5.0, "complete", "R2"),
    ("cancel_then_other_then_accepted", "W_Call after offers", 10.0, "complete", "R3"),
    ("cancel_then_other_then_accepted", "O_Accepted", 20.0, "complete", "R3"),
    # 8. accepted_before_cancel_only (durasi = 15 hari)
    ("accepted_before_cancel_only", "A_Create Application", 0.0, "complete", "R1"),
    ("accepted_before_cancel_only", "O_Accepted", 5.0, "complete", "R1"),
    ("accepted_before_cancel_only", "W_Call after offers", 10.0, "complete", "R2"),
    ("accepted_before_cancel_only", "O_Cancelled", 15.0, "complete", "R2"),
    # 9. ends_with_cancel_only (durasi = 60 hari -> OPT.slow)
    ("ends_with_cancel_only", "A_Create Application", 0.0, "complete", "R1"),
    ("ends_with_cancel_only", "W_Call after offers", 30.0, "complete", "R2"),
    ("ends_with_cancel_only", "O_Cancelled", 60.0, "complete", "R2"),
    # 10. fraud_missing_resource (durasi = 45 hari tepat -> OPT.slow)
    ("fraud_missing_resource", "A_Create Application", 0.0, "complete", "R1"),
    ("fraud_missing_resource", FRAUD, 10.0, "complete", NA),
    ("fraud_missing_resource", FRAUD, 20.0, "complete", NA),
    ("fraud_missing_resource", "W_Validate application", 45.0, "complete", "R1"),
    # 11. cancel_multi_then_accepted (durasi = 50 hari -> OPT.slow)
    ("cancel_multi_then_accepted", "A_Create Application", 0.0, "complete", "R1"),
    ("cancel_multi_then_accepted", "O_Cancelled", 5.0, "complete", "R2"),
    ("cancel_multi_then_accepted", "O_Cancelled", 10.0, "complete", "R2"),
    ("cancel_multi_then_accepted", "W_Validate application", 20.0, "complete", "R3"),
    ("cancel_multi_then_accepted", "O_Accepted", 40.0, "complete", "R3"),
    ("cancel_multi_then_accepted", "O_Accepted", 50.0, "complete", "R3"),
    # 12. same_timestamp_tiebreak (durasi = 10 hari)
    ("same_timestamp_tiebreak", "A_Create Application", 0.0, "complete", "R1"),
    ("same_timestamp_tiebreak", "O_Accepted", 10.0, "complete", "R1"),
    ("same_timestamp_tiebreak", "O_Cancelled", 10.0, "complete", "R1"),
]

#: Ekspektasi per kode soal -> himpunan case_id yang seharusnya lolos.
EXPECTED: dict[str, set[str]] = {
    "11.7A": set(SCENARIO_DESCRIPTIONS.keys()),
    "11.7B": set(SCENARIO_DESCRIPTIONS.keys()),
    "11.7C": {
        "accepted_twice",
        "refused_and_accepted",
        "cancel_then_other_then_accepted",
        "accepted_before_cancel_only",
        "cancel_multi_then_accepted",
        "same_timestamp_tiebreak",
    },
    "11.7D": {
        "refused_and_accepted",
    },
    "11.7E": {
        "accepted_before_cancel_only",
        "ends_with_cancel_only",
        "same_timestamp_tiebreak",
    },
    "11.15": {
        "fraud_two_complete_diff_resource",
        "fraud_two_complete_same_resource",
        "fraud_missing_resource",
    },
    "11.18": {
        "fraud_two_complete_same_resource",
    },
    "11.22": {
        "cancel_then_other_then_accepted",
        "cancel_multi_then_accepted",
    },
    "OPT.fast": {
        "accepted_twice",
        "cancel_middle",
        "refused_and_accepted",
        "fraud_scheduled_twice_one_complete",
        "fraud_two_complete_diff_resource",
        "fraud_two_complete_same_resource",
        "cancel_then_other_then_accepted",
        "accepted_before_cancel_only",
        "same_timestamp_tiebreak",
    },
    "OPT.slow": {
        "ends_with_cancel_only",
        "fraud_missing_resource",
        "cancel_multi_then_accepted",
    },
}

#: Durasi yang seharusnya (hari) untuk setiap case sintetis.
EXPECTED_CASE_DURATIONS: dict[str, float] = {
    "accepted_twice": 10.0,
    "cancel_middle": 5.0,
    "refused_and_accepted": 8.0,
    "fraud_scheduled_twice_one_complete": 4.0,
    "fraud_two_complete_diff_resource": 6.0,
    "fraud_two_complete_same_resource": 12.0,
    "cancel_then_other_then_accepted": 20.0,
    "accepted_before_cancel_only": 15.0,
    "ends_with_cancel_only": 60.0,
    "fraud_missing_resource": 45.0,
    "cancel_multi_then_accepted": 50.0,
    "same_timestamp_tiebreak": 10.0,
}


def make_synthetic_log() -> pd.DataFrame:
    """Bangun DataFrame kanonik berisi semua 8 skenario Bagian 8 + edge case tambahan.

    Lolos ``core.schema.check_canonical``. Pemilik: Anggota D.
    """
    df = pd.DataFrame(
        _RAW_EVENTS,
        columns=["case_id", "activity", "days", "lifecycle", "resource"],
    )
    df["timestamp"] = BASE_TIMESTAMP + pd.to_timedelta(df.pop("days"), unit="D")
    df["lifecycle"] = df["lifecycle"].astype("object")
    df["resource"] = df["resource"].astype("object").where(df["resource"].notna(), pd.NA)
    df["orig_idx"] = pd.RangeIndex(len(df)).astype("int64")
    df = df.sort_values(SORT_KEYS, kind="stable").reset_index(drop=True)
    df["event_pos"] = df.groupby("case_id", sort=False).cumcount().astype("int64")
    df["orig_idx"] = df["orig_idx"].astype("int64")
    return df[CANONICAL_COLUMNS]


def synthetic_durations(df: pd.DataFrame | None = None) -> pd.Series:
    """Hitung durasi (hari) per case untuk log sintetis."""
    if df is None:
        df = make_synthetic_log()
    g = df.groupby("case_id")["timestamp"]
    return ((g.max() - g.min()).dt.total_seconds() / 86400.0).rename(DURATION_NAME)


def _to_pm4py_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Konversi DataFrame kanonik ke format kolom standar XES PM4Py."""
    xes_df = pd.DataFrame(
        {
            "case:concept:name": df["case_id"].astype(str),
            "concept:name": df["activity"].astype(str),
            "time:timestamp": df["timestamp"],
            "lifecycle:transition": df["lifecycle"].astype("object"),
            # PM4Py/lxml mengharapkan None/NaN (bukan pd.NA) untuk atribut kosong.
            "org:resource": df["resource"].astype("object").where(df["resource"].notna(), None),
        }
    )
    return xes_df


def write_synthetic_xes(path: str | Path) -> Path:
    """Tulis log sintetis ke file ``.xes`` lewat ``pm4py.write_xes``.

    Pemilik: Anggota D. Berguna untuk menguji ``core.loader.load_xes`` dan demo aplikasi.
    """
    import pm4py

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    xes_df = _to_pm4py_dataframe(make_synthetic_log())
    pm4py.write_xes(xes_df, str(target))
    return target


def build_expected_dict() -> dict[str, Any]:
    """Susun struktur dictionary lengkap untuk ``expected.json`` per soal."""
    df = make_synthetic_log()
    total_cases = len(EXPECTED_CASE_DURATIONS)
    exercises: dict[str, dict[str, Any]] = {}

    for code, case_set in EXPECTED.items():
        ids = sorted(case_set)
        durs = [EXPECTED_CASE_DURATIONS[c] for c in ids]
        mean_dur = (sum(durs) / len(durs)) if durs else None
        entry: dict[str, Any] = {
            "n_cases": len(ids),
            "denominator": total_cases,
            "case_ids": ids,
            "mean_cycle_days": mean_dur,
        }
        if code in ("11.22", "OPT.fast", "OPT.slow"):
            entry["percentage"] = len(ids) / total_cases * 100.0
        if code in ("OPT.fast", "OPT.slow"):
            entry["threshold_days"] = 45.0
        exercises[code] = entry

    return {
        "description": (
            "Nilai yang semestinya untuk log sintetis BPIC17 (mencakup semua 8 skenario "
            "Instruksi Bagian 8 + edge case tambahan untuk 11.18, 11.22, tie-break, dan OPT)."
        ),
        "n_cases": total_cases,
        "n_events": int(len(df)),
        "case_durations_days": dict(EXPECTED_CASE_DURATIONS),
        "scenarios": dict(SCENARIO_DESCRIPTIONS),
        "exercises": exercises,
    }


def write_expected_json(path: str | Path) -> Path:
    """Tulis ``expected.json`` berisi hasil yang semestinya per soal."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    data = build_expected_dict()
    target.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return target


def generate_synthetic_bundle(output_dir: str | Path) -> tuple[Path, Path]:
    """Bangun sekaligus ``synthetic_bpic17.xes`` dan ``expected.json`` di ``output_dir``."""
    out = Path(output_dir)
    xes_path = write_synthetic_xes(out / "synthetic_bpic17.xes")
    json_path = write_expected_json(out / "expected.json")
    return xes_path, json_path


if __name__ == "__main__":
    import sys

    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent
    xes, exp = generate_synthetic_bundle(out_dir)
    print(f"XES sintetis  : {xes}")
    print(f"Expected JSON : {exp}")
