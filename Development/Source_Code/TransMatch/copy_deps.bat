@echo off
echo ======================================================================
echo Copying dependencies to _internal directory
echo ======================================================================
echo.

set "INTERNAL_DIR=%~dp0dist\TransMatch\_internal"
set "PROJECT_ROOT=%~dp0"
set "POPPLER_SRC=D:\CHIANWEILON\Software_Dev\TransMatch\Development\libs\poppler-24.08.0"
set "TESSERACT_SRC=C:\Program Files\Tesseract-OCR"

echo Target: %INTERNAL_DIR%
echo.

if not exist "%INTERNAL_DIR%" (
    echo ERROR: _internal directory not found!
    echo Please build the project first.
    pause
    exit /b 1
)

echo ======================================================================
echo Copying ML Libraries...
echo ======================================================================
set "ML_LIB_SRC=%PROJECT_ROOT%ml_libraries"
if exist "%ML_LIB_SRC%" (
    if exist "%INTERNAL_DIR%\ml_libraries" (
        echo Removing existing ml_libraries folder...
        rmdir /s /q "%INTERNAL_DIR%\ml_libraries"
    )
    echo Copying ml_libraries folder (this may take a while)...
    xcopy /E /I /Y "%ML_LIB_SRC%" "%INTERNAL_DIR%\ml_libraries\" >nul
    if errorlevel 1 (
        echo [WARNING] Failed to copy ml_libraries
    ) else (
        echo [OK] ml_libraries copied
    )
) else (
    echo [WARNING] ml_libraries source not found at %ML_LIB_SRC%
)
echo.

echo ======================================================================
echo Copying Poppler...
echo ======================================================================
echo Source: %POPPLER_SRC%
if not exist "%POPPLER_SRC%" (
    echo ERROR: Poppler source not found!
    pause
    exit /b 1
)

if exist "%INTERNAL_DIR%\poppler" (
    echo Removing existing poppler folder...
    rmdir /s /q "%INTERNAL_DIR%\poppler"
)

echo Copying poppler folder (this may take a while)...
xcopy /E /I /Y "%POPPLER_SRC%" "%INTERNAL_DIR%\poppler\" >nul
if errorlevel 1 (
    echo ERROR: Failed to copy poppler!
    pause
    exit /b 1
)
echo [OK] Poppler copied

if exist "%INTERNAL_DIR%\poppler\Library\bin\pdftoppm.exe" (
    echo [OK] Verified: pdftoppm.exe exists
) else (
    echo [WARNING] pdftoppm.exe not found!
)

if exist "%INTERNAL_DIR%\poppler\Library\bin\pdfinfo.exe" (
    echo [OK] Verified: pdfinfo.exe exists
) else (
    echo [WARNING] pdfinfo.exe not found!
)

echo.

echo ======================================================================
echo Copying Tesseract...
echo ======================================================================
echo Source: %TESSERACT_SRC%
if not exist "%TESSERACT_SRC%\tesseract.exe" (
    echo ERROR: Tesseract source not found!
    pause
    exit /b 1
)

if exist "%INTERNAL_DIR%\tesseract" (
    echo Removing existing tesseract folder...
    rmdir /s /q "%INTERNAL_DIR%\tesseract"
)

mkdir "%INTERNAL_DIR%\tesseract" 2>nul

echo Copying tesseract.exe and DLLs...
copy /Y "%TESSERACT_SRC%\tesseract.exe" "%INTERNAL_DIR%\tesseract\" >nul
if errorlevel 1 (
    echo ERROR: Failed to copy tesseract.exe!
    pause
    exit /b 1
)
echo [OK] tesseract.exe copied

REM Copy all DLL files from Tesseract directory (required for tesseract.exe to run)
echo Copying Tesseract DLLs...
xcopy /Y "%TESSERACT_SRC%\*.dll" "%INTERNAL_DIR%\tesseract\" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Some DLLs may not have been copied
) else (
    echo [OK] Tesseract DLLs copied
)

if exist "%TESSERACT_SRC%\tessdata" (
    echo Copying tessdata folder (this may take a while)...
    xcopy /E /I /Y "%TESSERACT_SRC%\tessdata" "%INTERNAL_DIR%\tesseract\tessdata\" >nul
    if errorlevel 1 (
        echo [WARNING] Failed to copy tessdata folder
    ) else (
        echo [OK] tessdata folder copied
    )
) else (
    echo [WARNING] tessdata folder not found in source
)

if exist "%INTERNAL_DIR%\tesseract\tesseract.exe" (
    echo [OK] Verified: tesseract.exe exists
) else (
    echo [WARNING] tesseract.exe not found after copy!
)

echo.

echo ======================================================================
echo Final Verification
echo ======================================================================
if exist "%INTERNAL_DIR%\poppler\Library\bin\pdftoppm.exe" (
    echo [OK] pdftoppm.exe
) else (
    echo [FAIL] pdftoppm.exe MISSING
)

if exist "%INTERNAL_DIR%\poppler\Library\bin\pdfinfo.exe" (
    echo [OK] pdfinfo.exe
) else (
    echo [FAIL] pdfinfo.exe MISSING
)

if exist "%INTERNAL_DIR%\tesseract\tesseract.exe" (
    echo [OK] tesseract.exe
) else (
    echo [FAIL] tesseract.exe MISSING
)

echo.
echo ======================================================================
echo Copy Complete!
echo ======================================================================
echo.
echo Folders are now in: %INTERNAL_DIR%
if exist "%INTERNAL_DIR%\ml_libraries" (
    echo   [OK] ml_libraries\
) else (
    echo   [MISSING] ml_libraries\
)
echo   - poppler\Library\bin\pdftoppm.exe
echo   - poppler\Library\bin\pdfinfo.exe
echo   - tesseract\tesseract.exe
echo   - tesseract\tessdata\
echo.
pause
