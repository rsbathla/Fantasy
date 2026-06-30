@echo off
REM Double-click this to run the X dossier pull. It runs x_fetch.ps1 (same folder),
REM reads X_BEARER_TOKEN.txt, and writes x_posts.json. Then upload x_posts.json to the chat.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0x_fetch.ps1"
