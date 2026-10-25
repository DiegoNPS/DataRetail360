@echo off
cd /d "%~dp0"
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo Primero ejecuta PREPARAR_ENTORNO.cmd.
    pause
    exit /b 1
)
set "JUPYTER_PATH=%~dp0.venv\share\jupyter"
set "PATH=%~dp0.venv\Scripts;%PATH%"
echo Se abrira JupyterLab. Selecciona Python - DataRetail360 y ejecuta una celda a la vez.
echo Esta ventana mantiene el editor abierto; no ejecuta la ETL automaticamente.
"%~dp0.venv\Scripts\python.exe" -m jupyterlab --ServerApp.root_dir="%~dp0." --LabApp.default_url=/lab/tree/notebooks/demostracion_etl.ipynb
exit /b %ERRORLEVEL%
