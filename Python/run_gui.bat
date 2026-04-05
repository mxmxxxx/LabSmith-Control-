@echo off
REM Double-click to start LabSmith Control GUI (labsmith_gui.py).
REM Python search order:
REM   1) Python\.venv
REM   2) repo root .venv (parent of this folder)
REM   3) py -3 or python on PATH
REM To hide the black console window, create a shortcut whose target is:
REM   pythonw.exe "...\labsmith_gui.py"
REM (use the same venv pythonw if you use a venv)

setlocal EnableExtensions
cd /d "%~dp0"

set "PY="
if exist "%~dp0.venv\Scripts\python.exe" set "PY=%~dp0.venv\Scripts\python.exe"
if not defined PY if exist "%~dp0..\.venv\Scripts\python.exe" set "PY=%~dp0..\.venv\Scripts\python.exe"

if defined PY (
  "%PY%" "%~dp0labsmith_gui.py"
) else (
  py -3 "%~dp0labsmith_gui.py" 2>nul || python "%~dp0labsmith_gui.py"
)

if errorlevel 1 (
  echo.
  echo Failed to start. Press a key to close.
  pause >nul
)

endlocal
