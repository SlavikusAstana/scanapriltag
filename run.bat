@echo off
cd /d "%~dp0"

if exist "dist\AprilTagScanner\AprilTagScanner.exe" (
    start "" "%~dp0dist\AprilTagScanner\AprilTagScanner.exe"
    exit /b 0
)

if exist "AprilTagScanner\bin\Release\net9.0-windows\win-x64\publish\AprilTagScanner.exe" (
    start "" "%~dp0AprilTagScanner\bin\Release\net9.0-windows\win-x64\publish\AprilTagScanner.exe"
    exit /b 0
)

echo EXE не найден. Сначала запустите build.bat
pause
