@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
title Screenshot OCR Tool
"C:\Users\12081\AppData\Local\Programs\Python\Python313\python.exe" ocr_gui.py
pause
