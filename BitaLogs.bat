@echo off
title BitaLogs - Practica Profesional
cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] No se encontro Python. Instala Python desde python.org
    pause
    exit /b 1
)

python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo   Instalando dependencias por primera vez, espera un momento...
    python -m pip install streamlit pandas plotly openpyxl
)

echo   Iniciando BitaLogs... se abrira en tu navegador.
python -m streamlit run bitalogs.py

echo.
echo   BitaLogs se detuvo.
pause