@echo off
chcp 65001 >nul

:: Kiem tra venv
if not exist "venv\Scripts\python.exe" (
    echo [LOI] Chua co virtual environment.
    echo Hay chay setup.bat truoc!
    pause & exit /b 1
)

:: Kiem tra BookIndex
if not exist "bookindex.pkl" (
    echo [LOI] Chua co bookindex.pkl.
    echo Hay chay run_build.bat truoc!
    pause & exit /b 1
)

echo ================================================
echo   BookRAG ^| Hoi Dap
echo   Cac lenh:
echo     Khong tham so   : Chat tuong tac
echo     --demo          : Chay 3 cau hoi mau
echo     --compare       : So sanh BookRAG vs Flat RAG
echo     -q "cau hoi"    : Hoi 1 cau roi thoat
echo ================================================
echo.

venv\Scripts\python.exe query.py %*

echo.
pause
