@echo off
cd /d "%~dp0"
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo Primero ejecuta PREPARAR_ENTORNO.cmd.
    if not defined ETL_SIN_PAUSA pause
    exit /b 1
)
"%~dp0.venv\Scripts\python.exe" -m src.ejecutar_etl --limpiar
set "RESULTADO=%ERRORLEVEL%"
if not defined ETL_SIN_PAUSA pause
exit /b %RESULTADO%
