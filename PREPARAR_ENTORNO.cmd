@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0src\preparar_entorno.ps1"
set "RESULTADO=%ERRORLEVEL%"
if not defined ETL_SIN_PAUSA pause
exit /b %RESULTADO%
