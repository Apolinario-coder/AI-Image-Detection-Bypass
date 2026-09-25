@echo off
title AI Image De-Fingerprint Tool
chcp 65001 >nul
cd /d "%~dp0scripts"
python deai.py
if errorlevel 1 (
    echo.
    echo Ocorreu um erro ao executar a aplicacao.
    pause
)
