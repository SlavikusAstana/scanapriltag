@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

set DIST=dist\AprilTagScanner
set ZIP=release\AprilTagScanner-win-x64.zip

echo Сборка AprilTag Scanner Pro...
if exist "%DIST%" rmdir /s /q "%DIST%"

dotnet publish AprilTagScanner\AprilTagScanner.csproj -c Release -r win-x64 -o "%DIST%" ^
  --self-contained true ^
  -p:PublishSingleFile=false ^
  -p:PublishReadyToRun=true ^
  -p:DebugType=none ^
  -p:DebugSymbols=false

if errorlevel 1 (
    echo Ошибка сборки.
    if not defined SKIP_PAUSE pause
    exit /b 1
)

if not exist release mkdir release
if exist "%ZIP%" del /f /q "%ZIP%"
powershell -NoProfile -Command "Compress-Archive -Path '%DIST%' -DestinationPath '%ZIP%' -CompressionLevel Optimal"

echo.
echo Готово:
echo   %CD%\%DIST%\AprilTagScanner.exe
echo   %CD%\%ZIP%
echo.
if not defined SKIP_PAUSE pause
