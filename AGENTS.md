# Aturan Agent Proyek — Aplikasi Desktop Analisis Event Log BPIC17

Berlaku untuk semua agent AI (Claude Code, opencode, dll.) dan semua anggota.
`CLAUDE.md` mengimpor file ini; **edit hanya di sini**. Perubahan kontrak di bawah harus
disepakati kelompok dulu, lalu masuk lewat Pull Request yang di-review Anggota E.

## Stack
Python 3.12 · PM4Py (wajib berperan nyata membaca XES) · pandas · PySide6 · pytest (+ pytest-qt).
Jalankan: `python main.py`. Test: `pytest`.

## Lapisan & larangan import
- `core/`, `analyses/`, `export/` → **DILARANG** mengimpor GUI (PySide6/`app`). Dijaga oleh
  `tests/test_contract.py::test_no_gui_imports`.
- `app/` → satu-satunya lapisan GUI.

## Kepemilikan file (kerjakan HANYA file milikmu)
| Anggota | Branch | File |
|---|---|---|
| A | `feat/a-loader` | `core/loader.py`, `core/durations.py`, `app/panels/overview_panel.py`, `app/panels/dataset_panel.py`, `app/panels/about_dialog.py` |
| B | `feat/b-117` | `analyses/ex_11_7.py`, `app/panels/ex117_panel.py` |
| C | `feat/c-1115-1118` | `analyses/ex_11_15_18.py`, `app/panels/ex1115_1118_panel.py` |
| D | `feat/d-1122-fixtures` | `analyses/ex_11_22.py`, `analyses/optional.py`, `tests/fixtures/make_synthetic.py`, `app/panels/ex1122_panel.py` |
| E | `feat/e-shell-explorer` | `app/main_window.py`, `app/worker.py`, `app/panels/case_explorer.py`, `export/csv_export.py` |

Kontrak bersama (ubah hanya lewat kesepakatan): `core/schema.py`, `core/result.py`,
`app/panels/base.py`, docstring kontrak di `core/loader.py`, `tests/test_contract.py`,
`tests/fixtures/tiny_log.py`, `AGENTS.md`. Uji silang di branch `test/<penguji>-uji-<pemilik>`
(mis. `test/e-uji-a`) dalam `tests/crosscheck/`.

## Git
- **Dilarang push/commit langsung ke `main`.** Semua perubahan lewat Pull Request.
- Jika branch sudah ada: checkout lalu pull. Jika belum: buat dari `main` terbaru.
- Pastikan `git status` bersih sebelum mulai; jangan commit file XES/CSV ekspor.
- Pesan commit tidak boleh memuat trailer Co-Authored-By atau atribusi AI.

## Kontrak 1 — DataFrame kanonik (detail: docstring `core/loader.py`)
| kolom | tipe | aturan |
|---|---|---|
| `case_id` | str | dari `case:concept:name` |
| `activity` | str | dari `concept:name`, ejaan asli |
| `timestamp` | datetime tz-aware **UTC** | dari `time:timestamp` |
| `lifecycle` | str lowercase / None | `lifecycle:transition`; None jika atribut tidak ada |
| `resource` | str / `pd.NA` | `org:resource`; string kosong → NA |
| `orig_idx` | int | urutan asli event di file (0-based, unik) |
| `event_pos` | int | posisi 0-based di dalam trace setelah sort |

Urutan: `sort_values(["case_id","timestamp","orig_idx"], kind="stable")`. Timestamp sama →
event yang lebih dulu di file dianggap lebih dulu. "Event terakhir" = `event_pos` maksimum.
Validator: `core.schema.check_canonical(df)`.

## Kontrak 2 — Durasi
`durations`: `pd.Series` index `case_id`, float **hari**, name `duration_days`, =
max(timestamp) − min(timestamp) dari **SELURUH** event case (`core.durations.compute_case_durations`).

## Kontrak 3 — Analisis
```python
def run(df: pd.DataFrame, durations: pd.Series, **params) -> AnalysisResult | list[AnalysisResult]
```
Setiap modul punya `DEFAULT_PARAMS` (dict). Jangan modifikasi `df` in-place.

## Kontrak 4 — `AnalysisResult` (`core/result.py`)
`code, title, rule_text, n_cases, denominator, percentage, mean_cycle_days, case_ids, per_case, evidence, params`.
- `code`: `11.7A`–`11.7E`, `11.15`, `11.18`, `11.22`, opsional `OPT.fast`/`OPT.slow`;
  analisis tambahan level offer diberi kode terpisah (mis. `11.22-offer`).
- `n_cases == len(case_ids)`, `case_ids` unik (dijaga `__post_init__`).
- `per_case` wajib kolom `case_id`, `duration_days`. `evidence` = baris df kanonik (7 kolom,
  `orig_idx` dipakai highlight Case Explorer) + kolom tambahan opsional.
- `rule_text` = aturan filter dalam bahasa Indonesia, persis seperti yang dijalankan kode.

## Kontrak 5 — GUI
- Setiap panel = subclass `app.panels.base.BasePanel` (QWidget) dengan sinyal
  `open_case(str)` dan `results_ready(object)` (list[AnalysisResult]), method
  `set_log(df, durations)` dan `reset()`.
- Semua komputasi berat lewat `app.worker.run_in_background` (QThreadPool; sinyal
  `started`, `progress(int,str)`, `finished(object)`, `error(str,str)`), **bukan** di thread UI.

## Aturan analisis (WAJIB)
1. **Tidak boleh ada angka jawaban hard-coded.** Semua angka dihitung dari log yang dimuat.
2. **Hitung di level case: satu case dihitung sekali**, walaupun event pemicunya muncul berkali-kali.
3. **Dilarang memfilter level-event sebelum menghitung durasi.** Mean cycle time selalu dari `durations`.
4. Contains (11.7C/D) ≠ endpoint (11.7E) ≠ eventually-follows (11.22, `event_pos` i < j, tidak harus bersebelahan).
5. 11.15/11.18: hanya occurrence lifecycle complete; resource NA tidak dianggap resource yang sama.
6. 11.22: persentase = n_cases / seluruh case log aktif × 100; tampilkan denominator.
7. Jangan menebak ejaan aktivitas/lifecycle BPIC17 — verifikasi dari data (mis. `W_Assess potential fraud`
   vs `W_Assess Potential Fraud`). Nama di `DEFAULT_PARAMS` saat ini disalin dari PDF dan bertanda TODO.

## Test
- Runner: **pytest** (`pytest` dari root repo). GUI test pakai pytest-qt, `QT_QPA_PLATFORM=offscreen`.
- Fixture bersama: `tiny_log`, `tiny_durs`, `dummy_results` (`tests/conftest.py`). Log sintetis lengkap
  akan disediakan Anggota D di `tests/fixtures/make_synthetic.py`.
- `tests/test_contract.py` harus selalu hijau sebelum PR di-merge.

## Gaya kerja agent
- Jelaskan singkat dalam bahasa Indonesia setiap langkah besar (anggota harus bisa menjelaskan saat demo).
- Jika kontrak terasa perlu diubah: **berhenti**, tulis usulan untuk dibawa ke kelompok.
