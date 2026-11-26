# Aplikasi Desktop Analisis Event Log BPIC17

Proyek Tahap 1 Process Mining — aplikasi desktop (Python + PM4Py + PySide6) yang mengimpor
file XES BPIC17 dan menjawab Exercise 11.7 (A–E), 11.15, 11.18, dan 11.22 langsung dari data,
lengkap dengan aturan filter, daftar case, bukti event, dan ekspor CSV.

> Status: **kerangka + kontrak kode**. Modul masih berupa stub (`NotImplementedError`) yang
> akan diisi tiap anggota di branch masing-masing.

Repo: https://github.com/shoandhy/bpic17-analyzer

## Prasyarat

- **Python 3.12** (versi yang dipakai menguji `requirements.txt`).
- Git.

## Instalasi

```bash
git clone https://github.com/shoandhy/bpic17-analyzer.git
cd bpic17-analyzer
python3.12 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest                           # pastikan semua test hijau
```

## Menjalankan

Cara paling mudah (Linux/macOS): `./run.sh`. Skrip ini membuat `.venv` dan menginstal dependency
saat pertama kali, lalu membuka aplikasi dengan `data/BPI Challenge 2017.xes.gz` jika file itu ada.
`./run.sh --demo` membuka log sintetis kecil tanpa dataset.
Windows: double-click `run.bat` atau jalankan `run.bat` / `run.bat --demo` dari Command Prompt
(butuh Python 3.12 dari python.org).

Manual:

```bash
python main.py                                   # aplikasi; impor XES lewat File → Buka XES (Ctrl+O)
python main.py "data/BPI Challenge 2017.xes.gz"  # langsung memuat file tersebut
python main.py --demo                            # log sintetis 6 case + hasil dummy (pengembangan)
pytest                                           # test
```

Alur di aplikasi: **Dataset → Overview → Exercise 11.7 / 11.15 & 11.18 / 11.22 → Case Explorer →
Hasil & Ekspor**. Memuat dan menganalisis berjalan di background (progress bar di status bar),
jadi jendela tidak membeku. Di halaman *Hasil & Ekspor* tersedia Re-run per analisis,
Jalankan semua (F5), Reset hasil, dan ekspor CSV (ringkasan, daftar case, evidence).
*File → Muat ulang file* (Ctrl+R) mengimpor ulang file yang sama untuk uji reproduktibilitas.

## Dataset

Dataset BPIC17 **tidak disertakan di repo** (ukurannya besar dan `*.xes`, `*.xes.gz`, serta
`data/` diabaikan git). Unduh sendiri dari 4TU.ResearchData:

| | |
|---|---|
| Judul | BPI Challenge 2017 (versi 1, terbit 6 Februari 2017) |
| Sumber | https://data.4tu.nl/articles/dataset/BPI_Challenge_2017/12696884 |
| DOI | `10.4121/uuid:5f3067df-f10b-45da-b98b-86ae4c7a310b` |
| File | `BPI Challenge 2017.xes.gz` (29.658.747 byte) |
| MD5 | `10b37a2f78e870d78406198403ff13d2` |

Simpan di `data/BPI Challenge 2017.xes.gz`. File `.xes.gz` dapat dibaca langsung oleh
`pm4py.read_xes` tanpa diekstrak. Hasil smoke test (pm4py 2.7.23.14, pandas 3.1.1):
31.509 case, 1.202.267 event, waktu muat ± 41 detik.

## Struktur folder

```
main.py                     titik masuk
app/                        GUI PySide6
  main_window.py            shell, navigasi, status/progress bar            (E)
  worker.py                 QThreadPool worker                               (E)
  panels/base.py            kontrak panel (open_case, results_ready, set_log)
  panels/dataset_panel.py   F01 dataset & status                             (A)
  panels/overview_panel.py  F02 overview                                     (A)
  panels/about_dialog.py    versi library                                    (A)
  panels/ex117_panel.py     F03                                              (B)
  panels/ex1115_1118_panel.py F04, F05                                       (C)
  panels/ex1122_panel.py    F06                                              (D)
  panels/case_explorer.py   F07 Case Explorer                                (E)
core/                       tanpa GUI
  loader.py                 impor XES -> DataFrame kanonik (+ docstring kontrak) (A)
  durations.py              durasi per case                                  (A)
  schema.py                 konstanta & validator kontrak
  result.py                 dataclass AnalysisResult
analyses/                   tanpa GUI
  ex_11_7.py (B) · ex_11_15_18.py (C) · ex_11_22.py (D) · optional.py (D)
export/csv_export.py        ekspor CSV                                       (E)
tests/                      pytest; fixtures/ berisi log sintetis
```

## Tim

| Anggota | Peran | Branch |
|---|---|---|
| A | Data & Overview (F01, F02) | `feat/a-loader` |
| B | Exercise 11.7 A–E (F03) | `feat/b-117` |
| C | Exercise 11.15 & 11.18 (F04, F05) | `feat/c-1115-1118` |
| D | Exercise 11.22 + data uji + opsional (F06) | `feat/d-1122-fixtures` |
| E | Setup repo, Shell, Case Explorer, Export (F07) | `feat/e-shell-explorer` |

Aturan kerja dan kontrak kode: lihat [AGENTS.md](AGENTS.md).
