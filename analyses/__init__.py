"""Modul analisis soal. DILARANG mengimpor GUI (PySide6/app) di paket ini.

Signature wajib setiap modul::

    def run(df: pd.DataFrame, durations: pd.Series, **params) -> AnalysisResult | list[AnalysisResult]

* ``df``: DataFrame kanonik UTUH (lihat core/loader.py). Jangan dimodifikasi in-place.
* ``durations``: Series index case_id, durasi hari (float), dari SELURUH event case
  (core.durations.compute_case_durations). Mean cycle time diambil dari sini.
* ``params``: nama aktivitas / lifecycle / ambang, punya nilai default, dan dicatat ke
  ``AnalysisResult.params``.
"""
