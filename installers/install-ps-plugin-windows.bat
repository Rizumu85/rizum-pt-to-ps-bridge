@echo off
setlocal

set "SCRIPT=%~dp0install-ps-plugin-windows.ps1"

echo Rizum PT-to-PS Bridge Photoshop plugin installer
echo.

if not exist "%SCRIPT%" (
  echo ERROR: Missing PowerShell installer:
  echo   %SCRIPT%
  echo.
  pause
  exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%"
set "STATUS=%ERRORLEVEL%"

echo.
if "%STATUS%"=="0" (
  echo Installer finished successfully.
) else (
  echo Installer failed with exit code %STATUS%.
)
echo.
echo Press any key to close this window.
pause >nul
exit /b %STATUS%
