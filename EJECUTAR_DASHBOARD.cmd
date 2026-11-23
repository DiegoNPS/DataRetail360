@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Falta el entorno virtual. Ejecute PREPARAR_ENTORNO.cmd primero.
  pause
  exit /b 1
)
if not exist "resultados\dataretail360.sqlite" (
  echo Falta la base Gold. Ejecute EJECUTAR_COMPLETO.cmd primero.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m streamlit run dashboard\app.py
endlocal
