"""Eksekusi komputasi berat di background (QThreadPool).

Pemilik: Anggota E (feat/e-shell-explorer).

KONTRAK (dipakai semua panel):
    * SEMUA komputasi berat (load_xes, compute_case_durations, analyses.*.run) dijalankan
      lewat ``run_in_background``; tidak boleh dipanggil langsung di thread UI.
    * Sinyal ``WorkerSignals``:
        started()              — pekerjaan dimulai
        progress(int, str)     — persen 0-100 dan pesan status
        finished(object)       — nilai kembalian fungsi
        error(str, str)        — (pesan singkat, traceback lengkap)
    * Jika ``fn`` menerima argumen kata kunci ``progress``, Worker menyuntikkan callback
      ``progress(persen, pesan)`` yang meneruskan ke sinyal progress.
    * Exception dari ``fn`` TIDAK boleh ditelan: harus diteruskan ke sinyal ``error``.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from PySide6.QtCore import QObject, QRunnable, Signal


class WorkerSignals(QObject):
    """Sinyal Worker (QRunnable tidak bisa memiliki sinyal sendiri)."""

    started = Signal()
    progress = Signal(int, str)
    finished = Signal(object)
    error = Signal(str, str)


class Worker(QRunnable):
    """Membungkus ``fn(*args, **kwargs)`` agar berjalan di QThreadPool. Pemilik: Anggota E."""

    def __init__(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self) -> None:  # noqa: D401 — dipanggil QThreadPool
        raise NotImplementedError("Anggota E: app.worker.Worker.run")


def run_in_background(
    fn: Callable[..., Any],
    *args: Any,
    on_finished: Optional[Callable[[Any], None]] = None,
    on_error: Optional[Callable[[str, str], None]] = None,
    on_progress: Optional[Callable[[int, str], None]] = None,
    **kwargs: Any,
) -> Worker:
    """Buat Worker, sambungkan callback, lalu jalankan di ``QThreadPool.globalInstance()``.

    Pemilik: Anggota E.
    """
    raise NotImplementedError("Anggota E: app.worker.run_in_background")
