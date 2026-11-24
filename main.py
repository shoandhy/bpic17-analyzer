"""Titik masuk aplikasi.

    python main.py                      # buka aplikasi, impor XES lewat menu File
    python main.py data/BPIC17.xes.gz   # langsung memuat file tersebut
    python main.py --demo               # log sintetis 6 case + hasil dummy (pengembangan)

Mode ``--demo`` memakai data dari ``tests/fixtures`` dan diberi label [DEMO]; tidak dipakai
untuk menjawab soal (jawaban selalu dihitung dari XES yang dimuat).
"""

from __future__ import annotations

import argparse
import sys


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aplikasi analisis event log BPIC17")
    parser.add_argument("xes", nargs="?", help="file .xes / .xes.gz yang langsung dimuat")
    parser.add_argument("--demo", action="store_true",
                        help="muat log sintetis kecil + hasil dummy (untuk pengembangan)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    from PySide6.QtWidgets import QApplication

    from app.main_window import MainWindow

    app = QApplication(sys.argv[:1])
    app.setApplicationName("BPIC17 Event Log Analyzer")
    window = MainWindow()
    window.show()

    if args.demo:
        from tests.fixtures.dummy_results import make_dummy_results
        from tests.fixtures.tiny_log import make_tiny_log, tiny_durations

        from pathlib import Path

        from core.loaded_log import LoadedLog

        df = make_tiny_log()
        durations = tiny_durations(df)
        loaded = LoadedLog(path=Path("[DEMO] tiny_log"), n_cases=int(df["case_id"].nunique()),
                           n_events=len(df), attributes=["concept:name", "time:timestamp",
                                                         "lifecycle:transition", "org:resource"])
        window.set_log(df, durations, source="[DEMO] log sintetis 6 case", loaded=loaded)
        window.add_results(make_dummy_results(df, durations))
    elif args.xes:
        window.load_xes_file(args.xes)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
