@echo off

cd /d "%~dp0"

python "%~dp0tools\sync_app_icon.py"
if errorlevel 1 exit /b 1

call gradlew.bat assembleDebug

if errorlevel 1 exit /b 1

echo.

echo APK: app\build\outputs\apk\debug\AprilTagScannerPro.apk

if not exist "..\release" mkdir "..\release"

copy /Y "app\build\outputs\apk\debug\AprilTagScannerPro.apk" "..\release\AprilTagScannerPro.apk"
copy /Y "..\AprilTagScanner\Assets\AppIcon.ico" "..\release\AprilTagScannerPro.ico"

echo Copied to: ..\release\AprilTagScannerPro.apk
echo Icon:     ..\release\AprilTagScannerPro.ico

