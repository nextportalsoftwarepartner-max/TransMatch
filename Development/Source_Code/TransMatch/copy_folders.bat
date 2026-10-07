@echo off
echo Copying external folders to dist\TransMatch\
echo.

set "SRC=%~dp0"
set "DST=%SRC%dist\TransMatch"

if not exist "%DST%" (
    echo Error: %DST% does not exist!
    echo Please build the project first.
    pause
    exit /b 1
)

echo Copying folders...
echo.

if exist "%SRC%ml_libraries" (
    echo Copying ml_libraries...
    xcopy /E /I /Y "%SRC%ml_libraries" "%DST%\ml_libraries\" >nul
    echo   [OK] ml_libraries
) else (
    echo   [SKIP] ml_libraries - not found
)

if exist "%SRC%tesseract" (
    echo Copying tesseract...
    xcopy /E /I /Y "%SRC%tesseract" "%DST%\tesseract\" >nul
    echo   [OK] tesseract
) else (
    echo   [SKIP] tesseract - not found
)

if exist "%SRC%poppler" (
    echo Copying poppler...
    xcopy /E /I /Y "%SRC%poppler" "%DST%\poppler\" >nul
    echo   [OK] poppler
) else (
    echo   [SKIP] poppler - not found
)

if exist "%SRC%templates" (
    echo Copying templates...
    xcopy /E /I /Y "%SRC%templates" "%DST%\templates\" >nul
    echo   [OK] templates
) else (
    echo   [SKIP] templates - not found
)

echo.
echo Done!
echo.
pause
