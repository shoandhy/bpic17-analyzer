"""Modul analisis soal. DILARANG mengimpor GUI (PySide6/app) di paket ini.

Signature wajib setiap modul::

    def run(df: pd.DataFrame, durations: pd.Series, **params) -> AnalysisResult | list[AnalysisResult]

* ``df``: DataFrame kanonik UTUH (lihat core/loader.py). Jangan dimodifikasi in-place.
* ``durations``: Series index case_id, durasi hari (float), dari SELURUH event case
  (core.durations.compute_case_durations). Mean cycle time diambil dari sini.
* ``params``: nama aktivitas / lifecycle / ambang. Setiap modul punya ``DEFAULT_PARAMS``;
  nilai efektif = ``{**DEFAULT_PARAMS, **params}``.

Kontrak v2 untuk ``AnalysisResult.params``: isinya HANYA argumen efektif tersebut (kunci
``DEFAULT_PARAMS``, tanpa metadata lain), sehingga ``run(df, durations, **result.params)``
menghasilkan AnalysisResult yang identik. Dipakai tombol Re-run dan diuji di
``tests/test_contract.py::test_params_rerun_identical``.
"""
