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
    * Jika ``fn`` punya parameter bernama ``progress``, Worker menyuntikkan callback
      ``progress(persen, pesan)`` yang meneruskan ke sinyal progress. Fungsi yang hanya
      menerima ``**params`` (mis. ``analyses.*.run``) TIDAK disuntik.
    * Exception dari ``fn`` TIDAK boleh ditelan: diteruskan ke sinyal ``error``.
    * Callback dari ``run_in_background`` selalu dijalankan di thread UI (queued connection),
      sehingga aman memperbarui widget di dalamnya.
"""

from __future__ import annotations

import inspect
import traceback
from typing import Any, Callable, Optional

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal

_QUEUED = Qt.ConnectionType.QueuedConnection

#: Worker yang sedang berjalan. Referensi Python disimpan agar objek sinyal tidak
#: dibersihkan garbage collector sebelum sinyalnya terkirim.
_ACTIVE: set["Worker"] = set()


class WorkerSignals(QObject):
    """Sinyal Worker (QRunnable bukan QObject sehingga tidak bisa punya sinyal sendiri)."""

    started = Signal()
    progress = Signal(int, str)
    finished = Signal(object)
    error = Signal(str, str)


def _accepts_progress(fn: Callable[..., Any]) -> bool:
    """True jika ``fn`` punya parameter eksplisit bernama ``progress``."""
    try:
        return "progress" in inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return False


class Worker(QRunnable):
    """Membungkus ``fn(*args, **kwargs)`` agar berjalan di QThreadPool. Pemilik: Anggota E."""

    def __init__(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def _emit_progress(self, percent: int, message: str = "") -> None:
        self.signals.progress.emit(max(0, min(100, int(percent))), str(message))

    def run(self) -> None:  # dipanggil QThreadPool di thread lain
        self.signals.started.emit()
        kwargs = dict(self.kwargs)
        if "progress" not in kwargs and _accepts_progress(self.fn):
            kwargs["progress"] = self._emit_progress
        try:
            result = self.fn(*self.args, **kwargs)
        except Exception as exc:  # diteruskan, tidak ditelan
            self.signals.error.emit(f"{type(exc).__name__}: {exc}", traceback.format_exc())
        else:
            self.signals.finished.emit(result)


def run_in_background(
    fn: Callable[..., Any],
    *args: Any,
    on_finished: Optional[Callable[[Any], None]] = None,
    on_error: Optional[Callable[[str, str], None]] = None,
    on_progress: Optional[Callable[[int, str], None]] = None,
    **kwargs: Any,
) -> Worker:
    """Buat Worker, sambungkan callback, lalu jalankan di ``QThreadPool.globalInstance()``.

    Pemilik: Anggota E. Mengembalikan Worker (berguna untuk test atau sinyal tambahan).
    """
    worker = Worker(fn, *args, **kwargs)
    sig = worker.signals
    if on_progress is not None:
        sig.progress.connect(on_progress, _QUEUED)
    if on_finished is not None:
        sig.finished.connect(on_finished, _QUEUED)
    if on_error is not None:
        sig.error.connect(on_error, _QUEUED)
    # Lepas referensi setelah callback pengguna dijalankan (urutan koneksi = urutan panggil).
    sig.finished.connect(lambda _res, w=worker: _ACTIVE.discard(w), _QUEUED)
    sig.error.connect(lambda _m, _t, w=worker: _ACTIVE.discard(w), _QUEUED)
    _ACTIVE.add(worker)
    QThreadPool.globalInstance().start(worker)
    return worker
