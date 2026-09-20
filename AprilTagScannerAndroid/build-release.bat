@echo off
cd /d "%~dp0"

if not exist "keystore.properties" (
    echo Ошибка: нет файла keystore.properties
    echo.
    echo 1. Запустите create-keystore.bat ^(если ключа ещё нет^)
    echo 2. Скопируйте keystore.properties.example в keystore.properties
    echo 3. Укажите пароли в keystore.properties
    exit /b 1
)

if not exist "release.keystore" (
    echo Ошибка: нет release.keystore — сначала create-keystore.bat
    exit /b 1
)

python "%~dp0tools\sync_app_icon.py"
if errorlevel 1 exit /b 1

call gradlew.bat assembleRelease
if errorlevel 1 exit /b 1

echo.
echo APK: app\build\outputs\apk\release\AprilTagScannerPro.apk
if not exist "..\release" mkdir "..\release"
copy /Y "app\build\outputs\apk\release\AprilTagScannerPro.apk" "..\release\AprilTagScannerPro.apk"
copy /Y "..\AprilTagScanner\Assets\AppIcon.ico" "..\release\AprilTagScannerPro.ico"
echo Copied to: ..\release\AprilTagScannerPro.apk
echo Icon:     ..\release\AprilTagScannerPro.ico
echo.
echo Этот APK подписан ВАШИМ ключом.
