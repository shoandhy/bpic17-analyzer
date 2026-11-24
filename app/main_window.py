"""Jendela utama aplikasi.

Pemilik: Anggota E (feat/e-shell-explorer).

Alur wajib (Instruksi Bagian 6): Impor XES -> Overview -> pilih latihan (sidebar/tab) ->
jalankan -> lihat jawaban -> periksa case -> ekspor. Status bar + progress bar + dialog error.

Tanggung jawab MainWindow:
    * memuat XES lewat ``app.worker.run_in_background(core.loader.load_xes, ...)``, lalu
      menghitung durasi (``core.durations.compute_case_durations``) juga di worker;
    * memanggil ``panel.set_log(df, durations)`` pada setiap panel setelah log dimuat;
    * menyambungkan ``panel.open_case`` -> ``CaseExplorer.show_case`` dan
      ``panel.results_ready`` -> penyimpanan hasil untuk Case Explorer & ekspor;
    * tombol Reset (tanpa membuka ulang file) dan menu ekspor CSV.
"""

from __future__ import annotations

from PySide6.QtWidgets import QMainWindow


class MainWindow(QMainWindow):
    """Shell aplikasi. Pemilik: Anggota E."""

    def __init__(self) -> None:
        super().__init__()
        raise NotImplementedError("Anggota E: app.main_window.MainWindow")
