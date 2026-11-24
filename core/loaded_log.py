"""Metadata log yang dimuat — KONTRAK BERSAMA v2 (ubah hanya lewat kesepakatan kelompok).

Dihasilkan ``core.loader.load_xes`` bersama DataFrame kanonik, lalu diteruskan MainWindow ke
setiap panel lewat ``BasePanel.set_loaded(loaded)``. Sengaja TIDAK memuat DataFrame (data
event dikirim terpisah lewat ``set_log(df, durations)``). Tanpa import GUI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class LoadedLog:
    """Informasi file XES aktif untuk panel Dataset, status bar, dan laporan.

    Field:
        path: path file XES yang dimuat.
        n_cases: jumlah case unik di log.
        n_events: jumlah event di log.
        attributes: nama atribut event yang tersedia di file (mis. ``concept:name``,
            ``lifecycle:transition``, ``org:resource``) — dipakai F01 untuk menampilkan
            atribut dan mendeteksi lifecycle/resource.
        warnings: peringatan non-fatal saat impor (bahasa Indonesia).
    """

    path: Path
    n_cases: int
    n_events: int
    attributes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
