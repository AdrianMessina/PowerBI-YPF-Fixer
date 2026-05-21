@echo off
echo ========================================
echo Power BI Fixer - YPF
echo ========================================
echo.

REM Check if venv exists
if not exist "venv\" (
    echo [INFO] Virtual environment not found. Creating...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        echo [INFO] Make sure Python 3.8+ is installed and in PATH.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
    echo.
)

REM Activate venv
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if dependencies are installed
python -c "import streamlit" 2>nul
if errorlevel 1 (
    echo [INFO] Dependencies not found. Installing...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed.
    echo.
)

REM Launch Streamlit
echo [INFO] Launching Power BI Fixer...
echo [INFO] Opening browser...
echo.
streamlit run app.py --server.headless=false

pause
