"""Ekspor CSV (F07).

Pemilik: Anggota E (feat/e-shell-explorer).

Format (UTF-8, pemisah koma, timestamp ISO-8601 UTC):
    ringkasan  : code, title, rule_text, n_cases, denominator, percentage, mean_cycle_days
    daftar case: code, case_id                (satu baris per case per analisis)
    evidence   : code, <7 kolom kanonik>, <kolom tambahan evidence jika ada>
"""

from __future__ import annotations

from pathlib import Path

from core.result import AnalysisResult

SUMMARY_COLUMNS: list[str] = [
    "code", "title", "rule_text", "n_cases", "denominator", "percentage", "mean_cycle_days",
]
CASE_LIST_COLUMNS: list[str] = ["code", "case_id"]


def export_summary(results: list[AnalysisResult], path: str | Path) -> Path:
    """Tulis ringkasan semua AnalysisResult ke CSV. Pemilik: Anggota E."""
    raise NotImplementedError("Anggota E: export.csv_export.export_summary")


def export_case_lists(results: list[AnalysisResult], path: str | Path) -> Path:
    """Tulis daftar case_id per analisis ke CSV. Pemilik: Anggota E."""
    raise NotImplementedError("Anggota E: export.csv_export.export_case_lists")


def export_evidence(results: list[AnalysisResult], path: str | Path) -> Path:
    """Tulis baris evidence semua analisis ke CSV. Pemilik: Anggota E."""
    raise NotImplementedError("Anggota E: export.csv_export.export_evidence")
