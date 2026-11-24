"""Log XES sintetis berisi SEMUA skenario uji Instruksi Bagian 8 + hasil yang seharusnya.

Pemilik: Anggota D (feat/d-1122-fixtures). Akan menggantikan ``tiny_log.py`` sebagai
fixture utama; dipakai semua anggota untuk test.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

#: Ekspektasi per kode soal -> himpunan case_id. Diisi Anggota D.
EXPECTED: dict[str, set[str]] = {}


def make_synthetic_log() -> pd.DataFrame:
    """DataFrame kanonik berisi semua skenario Bagian 8. Pemilik: Anggota D."""
    raise NotImplementedError("Anggota D: tests.fixtures.make_synthetic.make_synthetic_log")


def write_synthetic_xes(path: str | Path) -> Path:
    """Tulis log sintetis ke file .xes (lewat PM4Py) untuk menguji loader. Pemilik: Anggota D."""
    raise NotImplementedError("Anggota D: tests.fixtures.make_synthetic.write_synthetic_xes")
