@echo off
REM Double-click to start LabSmith Control GUI (labsmith_gui.py).
REM Python search order:
REM   1) Python\.venv
REM   2) repo root .venv (parent of this folder)
REM   3) py -3 or python on PATH
REM Install deps for THE SAME interpreter you use here:
REM   "%PY%" -m pip install -r "%~dp0..\requirements.txt"
REM To hide the black console window, create a shortcut whose target is:
REM   pythonw.exe "...\labsmith_gui.py"
REM (use the same venv pythonw if you use a venv)

setlocal EnableExtensions
cd /d "%~dp0"

set "PY="
if exist "%~dp0.venv\Scripts\python.exe" set "PY=%~dp0.venv\Scripts\python.exe"
if not defined PY if exist "%~dp0..\.venv\Scripts\python.exe" set "PY=%~dp0..\.venv\Scripts\python.exe"

if not defined PY (
  where py >nul 2>nul && ( set "PY=py -3" ) || ( set "PY=python" )
)

REM Quick check: PyQt6 must exist on the chosen interpreter
if defined PY (
  if "%PY%"=="py -3" (
    py -3 -c "import PyQt6" 2>nul
  ) else (
    "%PY%" -c "import PyQt6" 2>nul
  )
  if errorlevel 1 (
    echo.
    echo [Missing PyQt6] The Python below does not have PyQt6 installed:
    if "%PY%"=="py -3" ( py -3 -c "import sys; print(sys.executable)" ) else ( "%PY%" -c "import sys; print(sys.executable)" )
    echo.
    echo Fix ^(run in Command Prompt^):
    if "%PY%"=="py -3" (
      echo   py -3 -m pip install -r "%~dp0..\requirements.txt"
    ) else (
      echo   "%PY%" -m pip install -r "%~dp0..\requirements.txt"
    )
    echo.
    pause
    exit /b 1
  )
)

if "%PY%"=="py -3" (
  py -3 "%~dp0labsmith_gui.py"
) else (
  "%PY%" "%~dp0labsmith_gui.py"
)

if errorlevel 1 (
  echo.
  echo If you see "No module named PyQt6", install dependencies:
  echo   cd /d "%~dp0.."
  echo   python -m pip install -r requirements.txt
  echo Or:  python -m pip install PyQt6 pyserial numpy
  echo.
  echo Failed to start. Press a key to close.
  pause >nul
)

endlocal
