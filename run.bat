@echo off
chcp 65001 >nul
cd /d "%~dp0"
python ocr_to_note.py %*
pause
