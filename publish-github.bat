@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

where gh >nul 2>&1
if errorlevel 1 (
    echo Установите GitHub CLI: winget install GitHub.cli
    pause
    exit /b 1
)

gh auth status >nul 2>&1
if errorlevel 1 (
    echo Войдите в GitHub:
    gh auth login
)

set SKIP_PAUSE=1
call build.bat
if errorlevel 1 exit /b 1

echo.
echo Публикация на GitHub...
git add -A
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "Update build and sources"
)

gh repo view >nul 2>&1
if errorlevel 1 (
    gh repo create scanapriltag --public --source=. --remote=origin --push
) else (
    git push -u origin HEAD
)

gh release view v1.0.0 >nul 2>&1
if errorlevel 1 (
    gh release create v1.0.0 release\AprilTagScanner-win-x64.zip --title "v1.0.0" --notes "Windows x64 self-contained build."
) else (
    gh release upload v1.0.0 release\AprilTagScanner-win-x64.zip --clobber
)

echo.
echo Готово. Откройте репозиторий:
gh repo view --web
pause
