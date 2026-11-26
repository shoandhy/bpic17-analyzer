#!/usr/bin/env bash
# Jalankan aplikasi dengan satu perintah: ./run.sh
#   ./run.sh                 -> buka BPIC17 dari data/ jika ada, selain itu buka app kosong
#   ./run.sh --demo          -> log sintetis kecil (tanpa dataset)
#   ./run.sh path/file.xes   -> buka file XES tertentu
# Pertama kali dijalankan, venv .venv dibuat dan dependency diinstal otomatis.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
    echo "Menyiapkan .venv (sekali saja)..."
    python3.12 -m venv .venv
    .venv/bin/pip install -r requirements.txt
fi

DATA="data/BPI Challenge 2017.xes.gz"
if [ "$#" -gt 0 ]; then
    exec .venv/bin/python main.py "$@"
elif [ -f "$DATA" ]; then
    exec .venv/bin/python main.py "$DATA"
else
    exec .venv/bin/python main.py
fi
