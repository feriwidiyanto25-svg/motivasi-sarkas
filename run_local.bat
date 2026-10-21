@echo off
echo ====================================================
echo       MENJALANKAN KENAPAYA? (GRADIO LOCAL)
echo ====================================================

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" app.py
) else (
    python app.py
)
pause

