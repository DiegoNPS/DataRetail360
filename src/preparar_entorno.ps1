param([string]$PythonBase = '')
$ErrorActionPreference = 'Stop'
$raizProyecto = Split-Path -Parent $PSScriptRoot
$pythonEntorno = Join-Path $raizProyecto '.venv/Scripts/python.exe'
Set-Location -LiteralPath $raizProyecto

try {
    if (-not (Test-Path -LiteralPath $pythonEntorno)) {
        $argumentos = @()
        if (-not $PythonBase) {
            $lanzador = Get-Command py -ErrorAction SilentlyContinue
            if ($lanzador) {
                $PythonBase = $lanzador.Source
                $argumentos = @('-3')
            }
        }
        if (-not $PythonBase) {
            $uvLocal = Get-Command uv -ErrorAction SilentlyContinue
            if ($uvLocal) {
                $encontrado = & $uvLocal.Source python find 2>$null
                if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $encontrado)) { $PythonBase = $encontrado }
            }
        }
        if (-not $PythonBase) {
            $comandoPython = Get-Command python -ErrorAction SilentlyContinue
            if ($comandoPython -and $comandoPython.Source -notlike '*WindowsApps*') { $PythonBase = $comandoPython.Source }
        }
        if (-not $PythonBase) { throw 'Instala Python 3.12 o posterior (probado en 3.12 y 3.14) y vuelve a preparar el entorno.' }
        & $PythonBase @argumentos -c 'import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)'
        if ($LASTEXITCODE -ne 0) { throw 'La version de Python no es compatible.' }
        & $PythonBase @argumentos -m venv (Join-Path $raizProyecto '.venv')
        if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno Python del proyecto.' }
    }
    & $pythonEntorno -m pip install -r (Join-Path $raizProyecto 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'No se instalaron las dependencias. Revisa el mensaje anterior y la conexion. Si indica Long Path o ruta demasiado larga, descomprime el ZIP en una carpeta corta, como C:\ETL, y prepara alli el entorno.' }
    & $pythonEntorno -m ipykernel install --prefix (Join-Path $raizProyecto '.venv') --name dataretail360_proyecto --display-name 'Python - DataRetail360'
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo registrar el kernel local.' }
    & $pythonEntorno -c 'import pandas, sqlalchemy, jupyterlab, nbformat, nbclient, ipykernel, pyarrow'
    if ($LASTEXITCODE -ne 0) { throw 'Las dependencias no se pueden importar.' }
    Write-Host 'ENTORNO PREPARADO. Ya puedes ejecutar EJECUTAR_COMPLETO.cmd o ABRIR_DEMOSTRACION.cmd.' -ForegroundColor Green
    exit 0
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
