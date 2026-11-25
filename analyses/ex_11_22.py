"""Exercise 11.22 (F06): analisis urutan event ``eventually follows``.

Pemilik: Anggota D (feat/d-1122-fixtures).

Hasil ``run`` (satu AnalysisResult, code "11.22"):
    Case dipilih jika ada pasangan posisi ``i < j`` (``event_pos``) dengan
    ``event[i] = first_activity`` (default ``O_Cancelled``) dan
    ``event[j] = then_activity`` (default ``O_Accepted``). Kedua event TIDAK harus
    bersebelahan, dan ini BUKAN sama dengan "case berakhir O_Cancelled" (itu 11.7E).
    ``percentage = n_cases / denominator * 100``, dengan ``denominator`` = jumlah seluruh
    case di log aktif.
    ``evidence``: pasangan event bukti per case yang memenuhi — event ``first_activity``
    pertama (``event_pos`` minimum) dan event ``then_activity`` terakhir (``event_pos``
    maksimum), disertai kolom tambahan ``role`` ("cancelled" / "accepted" untuk default,
    atau "first" / "then" untuk aktivitas kustom).

Analisis tambahan level OfferID tersedia secara terpisah melalui ``run_offer_level``
dengan kode ``"11.22-offer"`` dan TIDAK dicampur dengan jawaban soal wajib level case.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from core.result import AnalysisResult
from core.schema import CANONICAL_COLUMNS, DURATION_NAME

DEFAULT_PARAMS: dict[str, str] = {
    "first_activity": "O_Cancelled",
    "then_activity": "O_Accepted",
}

#: Nama kolom kandidat untuk atribut OfferID di BPIC17 / event log XES.
OFFER_ID_CANDIDATES: tuple[str, ...] = (
    "OfferID",
    "offer_id",
    "case:OfferID",
    "offer:id",
)


def _normalize_durations(durations: pd.Series) -> pd.Series:
    """Salin ``durations`` dengan index bertipe ``str`` tanpa memodifikasi input asli."""
    dur = durations.copy()
    dur.index = dur.index.astype(str)
    dur.name = DURATION_NAME
    return dur


def _mean_duration(case_ids: list[str], dur: pd.Series) -> Optional[float]:
    """Hitung rata-rata cycle time (hari) dari ``durations`` utuh atas ``case_ids``."""
    if not case_ids:
        return None
    sub = dur.reindex(case_ids).dropna()
    if sub.empty:
        return None
    return float(sub.mean())


def _canonical_columns_of(df: pd.DataFrame) -> list[str]:
    """Kembalikan daftar kolom kanonik diikuti kolom tambahan yang ada pada ``df``."""
    canonical = [c for c in CANONICAL_COLUMNS if c in df.columns]
    extras = [c for c in df.columns if c not in canonical]
    return [*canonical, *extras]


def _empty_evidence(df: pd.DataFrame) -> pd.DataFrame:
    """DataFrame evidence kosong yang tetap menjaga kolom kanonik + ``role``."""
    cols = _canonical_columns_of(df)
    ev = df.iloc[0:0][cols].copy().reset_index(drop=True)
    ev["role"] = pd.Series(dtype="object")
    return ev


def _empty_per_case() -> pd.DataFrame:
    """DataFrame ``per_case`` kosong dengan skema standar 11.22."""
    return pd.DataFrame(
        {
            "case_id": pd.Series(dtype="object"),
            DURATION_NAME: pd.Series(dtype="float64"),
            "first_pos": pd.Series(dtype="int64"),
            "first_timestamp": pd.Series(dtype="datetime64[ns, UTC]"),
            "then_pos": pd.Series(dtype="int64"),
            "then_timestamp": pd.Series(dtype="datetime64[ns, UTC]"),
            "gap_events": pd.Series(dtype="int64"),
        }
    )


def _role_labels(a: str, b: str) -> tuple[str, str]:
    """Label kolom ``role`` pada evidence (sesuai kontrak: cancelled/accepted untuk default)."""
    role_a = "cancelled" if a == DEFAULT_PARAMS["first_activity"] else "first"
    role_b = "accepted" if b == DEFAULT_PARAMS["then_activity"] else "then"
    return role_a, role_b


def eventually_follows(
    df: pd.DataFrame,
    a: str = "O_Cancelled",
    b: str = "O_Accepted",
) -> set[str]:
    """Kembalikan himpunan ``case_id`` yang memiliki posisi ``i < j`` (``event_pos``)
    dengan ``event[i] = a`` dan ``event[j] = b``.

    Implementasi vektor penuh (tanpa loop Python per event):
    Syarat "ada i < j dengan activity[i] == a dan activity[j] == b" ekuivalen secara
    matematis dengan ``min(event_pos | activity == a) < max(event_pos | activity == b)``
    pada masing-masing case. Kedua event tidak harus bertetangga.
    """
    if df.empty:
        return set()

    mask_a = df["activity"] == a
    mask_b = df["activity"] == b
    if not mask_a.any() or not mask_b.any():
        return set()

    sub_a = df.loc[mask_a, ["case_id", "event_pos"]]
    sub_b = df.loc[mask_b, ["case_id", "event_pos"]]

    min_a = sub_a.groupby(sub_a["case_id"].astype(str), sort=False)["event_pos"].min()
    max_b = sub_b.groupby(sub_b["case_id"].astype(str), sort=False)["event_pos"].max()

    common = min_a.index.intersection(max_b.index)
    if common.empty:
        return set()

    matched = common[min_a.loc[common].to_numpy() < max_b.loc[common].to_numpy()]
    return {str(c) for c in matched.tolist()}


def _build_evidence_and_per_case(
    df: pd.DataFrame,
    case_ids: list[str],
    dur: pd.Series,
    a: str,
    b: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Susun pasangan event bukti (``a`` pertama, ``b`` terakhir) dan tabel ``per_case``
    secara vektor untuk ``case_ids`` yang lolos."""
    if not case_ids or df.empty:
        return _empty_evidence(df), _empty_per_case()

    cols = _canonical_columns_of(df)
    role_a, role_b = _role_labels(a, b)

    sub = df.loc[df["case_id"].astype(str).isin(case_ids), cols].copy()
    sub["_cid_str"] = sub["case_id"].astype(str)
    sub = sub.sort_values(["_cid_str", "event_pos", "orig_idx"], kind="stable")

    # Event a pertama (event_pos minimum) dan event b terakhir (event_pos maksimum) per case.
    first_a = (
        sub.loc[sub["activity"] == a]
        .groupby("_cid_str", sort=False)
        .head(1)
        .copy()
    )
    last_b = (
        sub.loc[sub["activity"] == b]
        .groupby("_cid_str", sort=False)
        .tail(1)
        .copy()
    )

    first_a["role"] = role_a
    last_b["role"] = role_b

    evidence = (
        pd.concat([first_a, last_b], ignore_index=True)
        .sort_values(["_cid_str", "event_pos", "orig_idx"], kind="stable")
        .drop(columns=["_cid_str"])
        .reset_index(drop=True)
    )

    # Ringkasan per_case dengan timestamp pasangan bukti untuk ditampilkan di GUI.
    a_info = first_a.set_index("_cid_str")[["event_pos", "timestamp"]]
    b_info = last_b.set_index("_cid_str")[["event_pos", "timestamp"]]

    a_pos = a_info["event_pos"].reindex(case_ids).to_numpy(dtype="int64")
    b_pos = b_info["event_pos"].reindex(case_ids).to_numpy(dtype="int64")
    a_ts = a_info["timestamp"].reindex(case_ids).reset_index(drop=True)
    b_ts = b_info["timestamp"].reindex(case_ids).reset_index(drop=True)

    per_case = pd.DataFrame(
        {
            "case_id": list(case_ids),
            DURATION_NAME: dur.reindex(case_ids).to_numpy(dtype="float64"),
            "first_pos": a_pos,
            "first_timestamp": a_ts,
            "then_pos": b_pos,
            "then_timestamp": b_ts,
            "gap_events": (b_pos - a_pos - 1).astype("int64"),
        }
    )
    return evidence, per_case


def run(df: pd.DataFrame, durations: pd.Series, **params) -> AnalysisResult:
    """Hitung Exercise 11.22 pada level case. Pemilik: Anggota D.

    Mengembalikan satu ``AnalysisResult`` dengan ``code="11.22"``.
    """
    unknown = set(params) - set(DEFAULT_PARAMS)
    if unknown:
        raise TypeError(f"Parameter tidak dikenal untuk ex_11_22.run: {sorted(unknown)}")

    eff: dict[str, str] = {
        k: str(v) for k, v in {**DEFAULT_PARAMS, **params}.items()
    }
    first_act = eff["first_activity"]
    then_act = eff["then_activity"]

    dur = _normalize_durations(durations)
    denominator = int(df["case_id"].nunique()) if not df.empty else 0
    matched_ids = sorted(eventually_follows(df, a=first_act, b=then_act))
    n_cases = len(matched_ids)
    percentage = (n_cases / denominator * 100.0) if denominator > 0 else None

    evidence, per_case = _build_evidence_and_per_case(
        df, matched_ids, dur, first_act, then_act
    )

    rule_text = (
        f"[Analisis level case] Case memiliki pasangan posisi i < j (event_pos) dengan "
        f"event i = '{first_act}' dan event j = '{then_act}' (tidak harus bertetangga; "
        f"bukan syarat event terakhir = '{first_act}'). "
        f"Persentase = n_cases / denominator × 100% ({n_cases} / {denominator} × 100%). "
        f"Bukti menampilkan event '{first_act}' pertama dan '{then_act}' terakhir per case."
    )

    return AnalysisResult(
        code="11.22",
        title=f"Eventually follows: {first_act} → {then_act} (level case)",
        rule_text=rule_text,
        n_cases=n_cases,
        denominator=denominator,
        percentage=percentage,
        mean_cycle_days=_mean_duration(matched_ids, dur),
        case_ids=matched_ids,
        per_case=per_case,
        evidence=evidence,
        params=dict(eff),
    )


def find_offer_column(df: pd.DataFrame) -> Optional[str]:
    """Cari nama kolom OfferID pada ``df`` jika tersedia, atau ``None``."""
    for col in OFFER_ID_CANDIDATES:
        if col in df.columns:
            return col
    return None


def run_offer_level(
    df: pd.DataFrame,
    durations: pd.Series,
    offer_col: Optional[str] = None,
    **params,
) -> AnalysisResult:
    """Analisis TAMBAHAN level OfferID (``code="11.22-offer"``), terpisah dari soal wajib.

    Memeriksa apakah di dalam satu ``(case_id, offer_id)`` yang SAMA terdapat
    ``first_activity`` mendahului ``then_activity`` (``event_pos`` i < j).
    Mengembalikan hasil teragregasi per case unik yang memiliki minimal satu offer
    yang memenuhi syarat tersebut.
    """
    unknown = set(params) - set(DEFAULT_PARAMS)
    if unknown:
        raise TypeError(
            f"Parameter tidak dikenal untuk ex_11_22.run_offer_level: {sorted(unknown)}"
        )

    col = offer_col or find_offer_column(df)
    if col is None or col not in df.columns:
        raise KeyError(
            "Kolom OfferID tidak tersedia pada DataFrame aktif "
            f"(kandidat: {', '.join(OFFER_ID_CANDIDATES)})."
        )

    eff: dict[str, str] = {
        k: str(v) for k, v in {**DEFAULT_PARAMS, **params}.items()
    }
    first_act = eff["first_activity"]
    then_act = eff["then_activity"]

    dur = _normalize_durations(durations)
    denominator = int(df["case_id"].nunique()) if not df.empty else 0

    if df.empty:
        matched_ids: list[str] = []
        evidence = _empty_evidence(df)
        per_case = _empty_per_case()
        per_case["offer_id"] = pd.Series(dtype="object")
    else:
        valid_offer = df[col].notna() & (df[col].astype(str).str.strip() != "")
        sub_valid = df.loc[valid_offer].copy()
        sub_valid["_cid_str"] = sub_valid["case_id"].astype(str)
        sub_valid["_oid_str"] = sub_valid[col].astype(str)

        mask_a = sub_valid["activity"] == first_act
        mask_b = sub_valid["activity"] == then_act

        if not mask_a.any() or not mask_b.any():
            matched_pairs: list[tuple[str, str]] = []
        else:
            min_a = (
                sub_valid.loc[mask_a]
                .groupby(["_cid_str", "_oid_str"], sort=False)["event_pos"]
                .min()
            )
            max_b = (
                sub_valid.loc[mask_b]
                .groupby(["_cid_str", "_oid_str"], sort=False)["event_pos"]
                .max()
            )
            common = min_a.index.intersection(max_b.index)
            if common.empty:
                matched_pairs = []
            else:
                hits = common[min_a.loc[common].to_numpy() < max_b.loc[common].to_numpy()]
                matched_pairs = sorted((str(c), str(o)) for c, o in hits.tolist())

        matched_ids = sorted({c for c, _ in matched_pairs})
        if not matched_pairs:
            evidence = _empty_evidence(df)
            per_case = _empty_per_case()
            per_case["offer_id"] = pd.Series(dtype="object")
        else:
            cols = _canonical_columns_of(df)
            role_a, role_b = _role_labels(first_act, then_act)
            pair_index = pd.MultiIndex.from_tuples(matched_pairs, names=["_cid_str", "_oid_str"])
            pair_mask = pd.MultiIndex.from_frame(
                sub_valid[["_cid_str", "_oid_str"]]
            ).isin(pair_index)
            hit_rows = sub_valid.loc[pair_mask].sort_values(
                ["_cid_str", "_oid_str", "event_pos", "orig_idx"], kind="stable"
            )
            first_a = (
                hit_rows.loc[hit_rows["activity"] == first_act]
                .groupby(["_cid_str", "_oid_str"], sort=False)
                .head(1)
                .copy()
            )
            last_b = (
                hit_rows.loc[hit_rows["activity"] == then_act]
                .groupby(["_cid_str", "_oid_str"], sort=False)
                .tail(1)
                .copy()
            )
            first_a["role"] = role_a
            last_b["role"] = role_b
            evidence = (
                pd.concat([first_a, last_b], ignore_index=True)
                .sort_values(["_cid_str", "event_pos", "orig_idx"], kind="stable")
                [[*cols, "role"]]
                .reset_index(drop=True)
            )

            # Ringkasan satu baris per case unik (menjaga invarian level case).
            offers_by_case = (
                pd.DataFrame(matched_pairs, columns=["case_id", "offer_id"])
                .groupby("case_id", sort=False)["offer_id"]
                .agg(lambda s: ", ".join(sorted(set(s))))
            )
            a_case = first_a.groupby("_cid_str", sort=False).head(1).set_index("_cid_str")
            b_case = last_b.groupby("_cid_str", sort=False).tail(1).set_index("_cid_str")
            a_pos = a_case["event_pos"].reindex(matched_ids).to_numpy(dtype="int64")
            b_pos = b_case["event_pos"].reindex(matched_ids).to_numpy(dtype="int64")
            per_case = pd.DataFrame(
                {
                    "case_id": list(matched_ids),
                    DURATION_NAME: dur.reindex(matched_ids).to_numpy(dtype="float64"),
                    "offer_id": offers_by_case.reindex(matched_ids).to_numpy(),
                    "first_pos": a_pos,
                    "first_timestamp": a_case["timestamp"].reindex(matched_ids).reset_index(drop=True),
                    "then_pos": b_pos,
                    "then_timestamp": b_case["timestamp"].reindex(matched_ids).reset_index(drop=True),
                    "gap_events": (b_pos - a_pos - 1).astype("int64"),
                }
            )

    n_cases = len(matched_ids)
    percentage = (n_cases / denominator * 100.0) if denominator > 0 else None
    rule_text = (
        f"[TAMBAHAN — Analisis level OfferID ({col}), bukan jawaban wajib] "
        f"Case memiliki minimal satu OfferID identik dengan posisi i < j (event_pos) "
        f"di mana event i = '{first_act}' dan event j = '{then_act}'. "
        f"Persentase = n_cases / denominator × 100% ({n_cases} / {denominator} × 100%)."
    )

    return AnalysisResult(
        code="11.22-offer",
        title=f"[Tambahan] {first_act} → {then_act} pada OfferID sama",
        rule_text=rule_text,
        n_cases=n_cases,
        denominator=denominator,
        percentage=percentage,
        mean_cycle_days=_mean_duration(matched_ids, dur),
        case_ids=matched_ids,
        per_case=per_case,
        evidence=evidence,
        params=dict(eff),
    )
