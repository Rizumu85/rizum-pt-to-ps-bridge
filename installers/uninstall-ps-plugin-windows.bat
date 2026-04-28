@echo off
setlocal

set "SCRIPT=%~dp0uninstall-ps-plugin-windows.ps1"

echo Rizum PT-to-PS Bridge Photoshop plugin uninstaller
echo.

if not exist "%SCRIPT%" (
  echo ERROR: Missing PowerShell uninstaller:
  echo   %SCRIPT%
  echo.
  pause
  exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%"
set "STATUS=%ERRORLEVEL%"

echo.
if "%STATUS%"=="0" (
  echo Uninstaller finished successfully.
) else (
  echo Uninstaller failed with exit code %STATUS%.
)
echo.
echo Press any key to close this window.
pause >nul
exit /b %STATUS%
