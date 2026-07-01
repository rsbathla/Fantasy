@echo off
REM ============================================================
REM  FULL best-ball grade (~40 seconds) — for slow drafts.
REM  Adds the 2-ply look-ahead ("then take X next pick") the fast
REM  mode skips. Same clipboard flow: Ctrl+A, Ctrl+C, then run this.
REM ============================================================
cd /d "%~dp0"
where py >nul 2>nul && ( py -3 bb_grade.py clip --open ) || ( python bb_grade.py clip --open )
pause
