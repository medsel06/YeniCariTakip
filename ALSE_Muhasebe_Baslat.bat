@echo off
chcp 65001 >nul
title ALSE Muhasebe Takip Sistemi

REM Scriptin bulundugu klasore gec (import'lar icin sart)
cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo Python bulunamadi! https://www.python.org/downloads/
    echo Kurulumda "Add Python to PATH" kutusunu isaretleyin!
    pause
    exit /b 1
)

python -c "import nicegui" >nul 2>&1
if errorlevel 1 (
    echo Gerekli kutuphaneler kuruluyor...
    pip install nicegui reportlab --quiet
)

echo.
echo  ========================================
echo   ALSE Plastik Hammadde
echo   Muhasebe Takip Sistemi
echo  ========================================
echo.
echo  Uygulama modu aciliyor...
echo  Kapatmak icin bu pencereyi kapatin.
echo.

set "ALSE_CHROME_APP_MODE=1"

python main.py
if errorlevel 1 (
    echo.
    echo  [HATA] Uygulama beklenmedik sekilde kapandi.
    pause
)
