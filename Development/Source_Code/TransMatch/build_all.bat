@echo off
echo ======================================================================
echo TransMatch Build Script
echo ======================================================================
echo.

cd /d "%~dp0"

echo [Step 1/3] Packaging ML libraries...
echo ----------------------------------------------------------------------
python build_ml_libraries.py
if errorlevel 1 (
    echo ERROR: Failed to package ML libraries
    pause
    exit /b 1
)
echo.

echo [Step 2/3] Building with PyInstaller...
echo ----------------------------------------------------------------------
python -m PyInstaller TransMatch.spec --clean --noconfirm
if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    pause
    exit /b 1
)
echo.

echo [Step 3/3] Copying dependencies...
echo ----------------------------------------------------------------------
call copy_deps.bat
if errorlevel 1 (
    echo ERROR: Failed to copy dependencies
    pause
    exit /b 1
)
echo.

echo ======================================================================
echo Build Complete!
echo ======================================================================
echo.
echo Executable: dist\TransMatch\TransMatch.exe
echo Dependencies: dist\TransMatch\_internal\
echo.
pause
