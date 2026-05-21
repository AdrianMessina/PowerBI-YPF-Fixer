@echo off
echo ================================================
echo Power BI Analyzer v2 - Ejecutando aplicacion...
echo ================================================
echo.

REM Verificar que existe el entorno virtual
if not exist venv (
    echo ERROR: Entorno virtual no encontrado
    echo Por favor ejecuta install.bat primero
    pause
    exit /b 1
)

REM Activar entorno virtual y ejecutar aplicacion
call venv\Scripts\activate.bat
streamlit run test_analyzer.py

if errorlevel 1 (
    echo.
    echo ERROR: La aplicacion termino con errores
    pause
)
