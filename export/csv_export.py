"""Ekspor CSV (F07).

Pemilik: Anggota E (feat/e-shell-explorer).

Format (UTF-8, pemisah koma, timestamp ISO-8601 UTC, nilai kosong/None -> sel kosong):
    ringkasan  : code, title, rule_text, n_cases, denominator, percentage, mean_cycle_days
    daftar case: code, case_id                (satu baris per case per analisis)
    evidence   : code, <7 kolom kanonik>, <kolom tambahan evidence jika ada>

Fungsi ``*_frame`` murni (tanpa I/O) agar mudah diuji; fungsi ``export_*`` menulis file.
Semua angka berasal dari ``AnalysisResult`` — modul ini tidak menghitung jawaban apa pun.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from core.result import AnalysisResult
from core.schema import CANONICAL_COLUMNS

SUMMARY_COLUMNS: list[str] = [
    "code", "title", "rule_text", "n_cases", "denominator", "percentage", "mean_cycle_days",
]
CASE_LIST_COLUMNS: list[str] = ["code", "case_id"]


# --- Penyusun DataFrame (murni) ---------------------------------------------------------

def summary_frame(results: list[AnalysisResult]) -> pd.DataFrame:
    """Satu baris per AnalysisResult dengan kolom ``SUMMARY_COLUMNS``."""
    rows = [{col: getattr(r, col) for col in SUMMARY_COLUMNS} for r in results]
    df = pd.DataFrame(rows, columns=SUMMARY_COLUMNS)
    return df.astype({"n_cases": "int64", "denominator": "int64"}) if len(df) else df


def case_list_frame(results: list[AnalysisResult]) -> pd.DataFrame:
    """Satu baris per (code, case_id), urutan sesuai ``AnalysisResult.case_ids``."""
    rows = [(r.code, str(cid)) for r in results for cid in r.case_ids]
    return pd.DataFrame(rows, columns=CASE_LIST_COLUMNS)


def evidence_frame(results: list[AnalysisResult]) -> pd.DataFrame:
    """Gabungan ``evidence`` semua hasil, diawali kolom ``code``."""
    frames = []
    for r in results:
        ev = r.evidence
        if ev is None or ev.empty:
            continue
        f = ev.reset_index(drop=True).copy()
        f.insert(0, "code", r.code)
        frames.append(f)
    if not frames:
        return pd.DataFrame(columns=["code", *CANONICAL_COLUMNS])
    df = pd.concat(frames, ignore_index=True)
    canonical = [c for c in CANONICAL_COLUMNS if c in df.columns]
    extras = [c for c in df.columns if c not in ("code", *canonical)]
    return _format_datetimes(df[["code", *canonical, *extras]])


def _format_datetimes(df: pd.DataFrame) -> pd.DataFrame:
    """Ubah kolom datetime menjadi teks ISO-8601 (UTC diberi akhiran ``Z``)."""
    out = df.copy()
    for col in out.columns:
        s = out[col]
        if isinstance(s.dtype, pd.DatetimeTZDtype):
            out[col] = s.dt.tz_convert("UTC").dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        elif pd.api.types.is_datetime64_dtype(s.dtype):
            out[col] = s.dt.strftime("%Y-%m-%dT%H:%M:%S.%f")
    return out


# --- Penulis file ---------------------------------------------------------------------

def _write(df: pd.DataFrame, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")
    return path


def export_summary(results: list[AnalysisResult], path: str | Path) -> Path:
    """Tulis ringkasan semua AnalysisResult ke CSV. Pemilik: Anggota E."""
    return _write(summary_frame(results), path)


def export_case_lists(results: list[AnalysisResult], path: str | Path) -> Path:
    """Tulis daftar case_id per analisis ke CSV. Pemilik: Anggota E."""
    return _write(case_list_frame(results), path)


def export_evidence(results: list[AnalysisResult], path: str | Path) -> Path:
    """Tulis baris evidence semua analisis ke CSV. Pemilik: Anggota E."""
    return _write(evidence_frame(results), path)


def export_all(
    results: list[AnalysisResult], directory: str | Path, stamp: str | None = None
) -> dict[str, Path]:
    """Tulis ketiga CSV ke ``directory`` dengan nama berstempel waktu. Pemilik: Anggota E."""
    stamp = stamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    directory = Path(directory)
    return {
        "ringkasan": export_summary(results, directory / f"ringkasan_{stamp}.csv"),
        "daftar_case": export_case_lists(results, directory / f"daftar_case_{stamp}.csv"),
        "evidence": export_evidence(results, directory / f"evidence_{stamp}.csv"),
    }
