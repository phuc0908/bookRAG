@echo off
chcp 65001 >nul

:: Kiem tra venv da duoc tao chua
if not exist "venv\Scripts\python.exe" (
    echo [LOI] Chua co virtual environment.
    echo Hay chay setup.bat truoc!
    pause & exit /b 1
)

echo ================================================
echo   BookRAG ^| Xay dung BookIndex
echo ================================================
echo.

:: Chay build_index.py bang python trong venv
venv\Scripts\python.exe build_index.py %*

echo.
if %errorlevel% equ 0 (
    echo [OK] BookIndex da duoc luu vao bookindex.pkl
    echo Chay run_query.bat de hoi dap.
) else (
    echo [LOI] Co loi xay ra. Xem thong bao phia tren.
)
echo.
pause
