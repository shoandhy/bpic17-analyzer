@echo off
REM Jalankan aplikasi di Windows dengan satu perintah: run.bat (atau double-click)
REM   run.bat                 -> buka BPIC17 dari data\ jika ada, selain itu buka app kosong
REM   run.bat --demo          -> log sintetis kecil (tanpa dataset)
REM   run.bat path\file.xes   -> buka file XES tertentu
REM Pertama kali dijalankan, venv .venv dibuat dan dependency diinstal otomatis.
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Menyiapkan .venv ^(sekali saja^)...
    py -3.12 -m venv .venv || python -m venv .venv || goto :fail
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :fail
)

set "DATA=data\BPI Challenge 2017.xes.gz"
if not "%~1"=="" (
    ".venv\Scripts\python.exe" main.py %*
) else if exist "%DATA%" (
    ".venv\Scripts\python.exe" main.py "%DATA%"
) else (
    ".venv\Scripts\python.exe" main.py
)
if errorlevel 1 pause
exit /b %errorlevel%

:fail
echo Gagal menyiapkan .venv. Pastikan Python 3.12 terpasang (python.org, centang "Add to PATH").
pause
exit /b 1
