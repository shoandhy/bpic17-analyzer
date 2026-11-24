"""Test app/worker.py (Anggota E): hasil, progress, dan penerusan exception."""

from __future__ import annotations

import threading

from PySide6.QtCore import QThreadPool

from app.worker import Worker, run_in_background


def test_worker_forwards_exception_to_error_signal(qtbot):
    def boom():
        raise ValueError("file rusak")

    worker = Worker(boom)
    with qtbot.waitSignal(worker.signals.error, timeout=5000) as blocker:
        QThreadPool.globalInstance().start(worker)
    message, details = blocker.args
    assert message == "ValueError: file rusak"
    assert "Traceback" in details and "boom" in details


def test_worker_emits_finished_with_result(qtbot):
    worker = Worker(lambda a, b: a + b, 2, 3)
    with qtbot.waitSignal(worker.signals.finished, timeout=5000) as blocker:
        QThreadPool.globalInstance().start(worker)
    assert blocker.args == [5]


def test_run_in_background_calls_on_error_in_ui_thread(qtbot):
    seen = {}

    def boom():
        raise RuntimeError("gagal")

    def on_error(message, details):
        seen["message"] = message
        seen["thread"] = threading.current_thread()

    run_in_background(boom, on_error=on_error, on_finished=lambda _r: seen.setdefault("finished", True))
    qtbot.waitUntil(lambda: "message" in seen, timeout=5000)
    assert seen["message"] == "RuntimeError: gagal"
    assert "finished" not in seen
    assert seen["thread"] is threading.main_thread()


def test_progress_injected_only_for_explicit_parameter(qtbot):
    updates, out = [], {}

    def with_progress(n, progress):
        progress(50, "setengah")
        return n

    def analysis_like(df, durations, **params):
        return sorted(params)  # 'progress' tidak boleh ikut masuk ke **params

    run_in_background(with_progress, 7, on_progress=lambda p, m: updates.append((p, m)),
                      on_finished=lambda r: out.setdefault("a", r))
    run_in_background(analysis_like, None, None, on_finished=lambda r: out.setdefault("b", r))
    qtbot.waitUntil(lambda: {"a", "b"} <= out.keys() and bool(updates), timeout=5000)
    assert out["a"] == 7
    assert updates == [(50, "setengah")]
    assert out["b"] == []
