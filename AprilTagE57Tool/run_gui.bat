@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

title AprilTag E57 Tool

where python >nul 2>&1
if %errorlevel% equ 0 (
    python run_gui.py
    goto :done
)

where py >nul 2>&1
if %errorlevel% equ 0 (
    py -3 run_gui.py
    goto :done
)

echo Python не найден. Установите Python 3 и добавьте в PATH.
pause
exit /b 1

:done
if errorlevel 1 (
    echo.
    echo Ошибка запуска GUI. Проверьте зависимости: pip install opencv-python numpy pyquaternion pye57
    pause
    exit /b 1
)

endlocal
