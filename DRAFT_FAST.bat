@echo off
REM ============================================================
REM  ON-THE-CLOCK best-ball grade (~10 seconds).
REM  1) In the DraftKings/Underdog draft room: Ctrl+A then Ctrl+C.
REM  2) Double-click this file. The dashboard opens automatically.
REM ============================================================
cd /d "%~dp0"
where py >nul 2>nul && ( py -3 bb_grade.py clip --fast --open ) || ( python bb_grade.py clip --fast --open )
echo.
echo If nothing happened: install Python 3.11, then run  pip install -r requirements.txt  once.
echo See SETUP_WINDOWS.md.
pause
