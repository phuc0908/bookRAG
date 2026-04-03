@echo off
chcp 65001 >nul
echo ================================================
echo   BookRAG ^| Tao Virtual Environment (venv)
echo   Paper: arXiv 2512.03413
echo ================================================
echo.

:: Kiem tra Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [LOI] Khong tim thay Python. Hay cai Python 3.10+
    pause & exit /b 1
)
echo Python: OK

:: Tao venv
echo.
echo [1/4] Tao virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo [LOI] Khong the tao venv
    pause & exit /b 1
)
echo       Tao venv thanh cong tai thu muc: venv\

:: Upgrade pip ben trong venv
echo.
echo [2/4] Nang cap pip...
venv\Scripts\python.exe -m pip install --upgrade pip -q

:: Cai dependencies voi numpy 1.x truoc de tranh xung dot binary
echo.
echo [3/4] Cai dat thu vien (co the mat 5-10 phut, lan dau tai model ~500MB)...
echo.
venv\Scripts\pip.exe install numpy==1.26.4 -q
venv\Scripts\pip.exe install sentence-transformers==2.7.0 networkx==3.2.1 python-dotenv==1.0.1 rich==13.7.1
venv\Scripts\pip.exe install google-generativeai==0.8.4 groq==0.13.1 openai==1.14.3

if %errorlevel% neq 0 (
    echo.
    echo [LOI] Cai dat that bai. Kiem tra ket noi mang.
    pause & exit /b 1
)

:: Tao .env neu chua co
echo.
echo [4/4] Tao file .env...
if not exist ".env" (
    copy .env.example .env >nul
    echo       .env duoc tao. Mo de dien OpenAI key (tuy chon).
) else (
    echo       .env da ton tai, bo qua.
)

echo.
echo ================================================
echo   HOAN THANH! Buoc tiep theo:
echo     run_build.bat   ^<-- Buoc 1: Xay BookIndex
echo     run_query.bat   ^<-- Buoc 2: Hoi dap
echo ================================================
pause
