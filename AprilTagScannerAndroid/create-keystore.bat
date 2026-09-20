@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================
echo  Sozdanie klyucha podpisi (odin raz)
echo ============================================
echo.

if exist "release.keystore" (
    echo Fayl release.keystore uzhe est.
    echo Udalite ego vruchnuyu, esli nuzhen novyy klyuch.
    goto :done
)

set "KEYTOOL="
where keytool >nul 2>&1 && set "KEYTOOL=keytool"

if not defined KEYTOOL if defined JAVA_HOME (
    if exist "%JAVA_HOME%\bin\keytool.exe" set "KEYTOOL=%JAVA_HOME%\bin\keytool.exe"
)

if not defined KEYTOOL (
    for /d %%D in ("C:\Program Files\Java\jdk*") do (
        if exist "%%~D\bin\keytool.exe" set "KEYTOOL=%%~D\bin\keytool.exe"
    )
)

if not defined KEYTOOL (
    echo OSHIBKA: keytool ne nayden. Ustanovite JDK 17+.
    goto :done
)

echo Nayden keytool: %KEYTOOL%
echo.
echo Keytool seychas sprosit:
echo   1. Parol hranilishcha - pridumayte i zapomnite
echo   2. Povtor parolya
echo   3. Imya (CN) - vashe imya, naprimer Ivan Ivanov
echo   4. Ostalnoe - Enter ili po zhelaniyu
echo   5. V kontse vvedite: yes
echo.
echo VAZHNO: parol pri vvode NE vidен - eto normalno!
echo.
pause

"%KEYTOOL%" -genkeypair -v ^
  -keystore release.keystore ^
  -alias apriltag ^
  -keyalg RSA ^
  -keysize 2048 ^
  -validity 10000 ^
  -storetype PKCS12

if errorlevel 1 (
    echo.
    echo OSHIBKA pri sozdanii klyucha.
    goto :done
)

echo.
echo Gotovo: %CD%\release.keystore
echo.
echo Dalyshe:
echo   copy keystore.properties.example keystore.properties
echo   notepad keystore.properties   ^(vpiшite paroli^)
echo   build-release.bat
echo.

:done
pause
