@echo off
echo ================================================
echo Power BI Analyzer v2 - Instalador Automatico
echo ================================================
echo.

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no esta instalado o no esta en PATH
    echo Por favor instala Python 3.8+ desde https://www.python.org
    pause
    exit /b 1
)

echo [1/4] Python detectado correctamente
echo.

REM Crear entorno virtual
echo [2/4] Creando entorno virtual...
if exist venv (
    echo Entorno virtual ya existe, saltando...
) else (
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: No se pudo crear el entorno virtual
        pause
        exit /b 1
    )
)
echo.

REM Activar entorno virtual e instalar dependencias
echo [3/4] Instalando dependencias (esto puede tardar unos minutos)...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Fallo la instalacion de dependencias
    pause
    exit /b 1
)
echo.

echo [4/4] Instalacion completada exitosamente!
echo.
echo ================================================
echo Para ejecutar la aplicacion:
echo   1. Ejecuta: run.bat
echo   O manualmente:
echo   2. venv\Scripts\activate
echo   3. streamlit run test_analyzer.py
echo ================================================
echo.
pause
