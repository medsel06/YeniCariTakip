@echo off
setlocal
chcp 65001 >nul
echo ============================================
echo  ALSE Muhasebe - EXE Olusturucu
echo ============================================
echo.

REM Scriptin bulundugu klasore gec
cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo [HATA] Python bulunamadi!
    echo Python sadece SENIN bilgisayarinda olmali.
    echo Musteri EXE'yi kullanacak, Python gerekmez.
    pause
    exit /b 1
)

echo [1/3] Gerekli kutuphaneler yukleniyor...
set "BUILD_VENV=.buildenv"
if not exist "%BUILD_VENV%\Scripts\python.exe" (
    echo [INFO] Izole build ortami olusturuluyor...
    python -m venv "%BUILD_VENV%"
    if errorlevel 1 (
        echo [HATA] venv olusturulamadi!
        pause
        exit /b 1
    )
)

"%BUILD_VENV%\Scripts\python.exe" -m pip install --upgrade pip --quiet
"%BUILD_VENV%\Scripts\python.exe" -m pip install nicegui reportlab pyinstaller --quiet

echo [INFO] Eski build kalintilari temizleniyor...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "ALSE_Muhasebe.spec" del /q "ALSE_Muhasebe.spec"
if exist "pyinstaller_build.log" del /q "pyinstaller_build.log"

echo [2/3] EXE olusturuluyor (3-7 dakika surebilir)...
"%BUILD_VENV%\Scripts\python.exe" -m PyInstaller --clean --onefile ^
    --name "ALSE_Muhasebe" ^
    --noconsole ^
    --collect-all nicegui ^
    --exclude-module torch ^
    --exclude-module tensorboard ^
    --exclude-module tensorflow ^
    --exclude-module jax ^
    --exclude-module jaxlib ^
    --exclude-module scipy ^
    --exclude-module pandas ^
    --exclude-module matplotlib ^
    --hidden-import=sqlite3 ^
    --hidden-import=reportlab ^
    --hidden-import=reportlab.graphics ^
    --add-data "assets;assets" ^
    --log-level=WARN ^
    --noconfirm ^
    main.py > "pyinstaller_build.log" 2>&1

if errorlevel 1 (
    echo.
    echo [HATA] EXE olusturulamadi!
    echo.
    findstr /C:"PermissionError" /C:"WinError 5" "pyinstaller_build.log" >nul 2>&1
    if not errorlevel 1 (
        echo [NEDEN] dist\ALSE_Muhasebe.exe kullanimda veya kilitli.
        echo [COZUM] Uygulamayi/EXE'yi kapatip tekrar deneyin.
    )
    echo [LOG] Ayrinti: pyinstaller_build.log
    pause
    exit /b 1
)

if not exist "dist\ALSE_Muhasebe.exe" (
    echo.
    echo [HATA] EXE olusturulamadi!
    echo [LOG] Ayrinti: pyinstaller_build.log
    pause
    exit /b 1
)

echo [3/3] Dosyalar hazirlaniyor...

REM dist klasorune DB ve data.json kopyala
if exist "data.json" copy "data.json" "dist\data.json" >nul
if exist "alse_muhasebe.db" copy "alse_muhasebe.db" "dist\alse_muhasebe.db" >nul
mkdir "dist\yedekler" 2>nul

REM App mode baslatma kisayolu (sekmesiz Chrome gorunumu)
(
echo @echo off
echo chcp 65001 ^>nul
echo set "ALSE_CHROME_APP_MODE=1"
echo start "" "%%~dp0ALSE_Muhasebe.exe"
) > "dist\ALSE_Muhasebe_AppMode.bat"

echo.
echo ============================================
echo  TAMAM! Asagidaki klasoru musteriye ver:
echo.
echo  dist\
echo    ALSE_Muhasebe.exe              (normal)
echo    ALSE_Muhasebe_AppMode.bat      (onerilen - uygulama gorunumu)
echo    alse_muhasebe.db    (veriler)
echo    yedekler\           (otomatik yedekler)
echo.
echo  Musteride Python GEREKMEZ.
echo  EXE her seyi icinde tasiyor.
echo ============================================
pause
