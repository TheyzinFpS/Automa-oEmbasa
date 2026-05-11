$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

Write-Host "== EMBASA | Build empresarial =="
Write-Host "Diretorio: $PSScriptRoot"

$pythonLauncher = Get-Command py -ErrorAction SilentlyContinue

if ($pythonLauncher) {
    & py -3.11 -m venv .venv
} else {
    & python -m venv .venv
}

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$pip = Join-Path $PSScriptRoot ".venv\Scripts\pip.exe"
$pyinstaller = Join-Path $PSScriptRoot ".venv\Scripts\pyinstaller.exe"

& $python -m pip install --upgrade pip
& $pip install -r requirements.txt

if (Test-Path (Join-Path $PSScriptRoot "build")) {
    Remove-Item -LiteralPath (Join-Path $PSScriptRoot "build") -Recurse -Force
}

if (Test-Path (Join-Path $PSScriptRoot "dist")) {
    Remove-Item -LiteralPath (Join-Path $PSScriptRoot "dist") -Recurse -Force
}

& $pyinstaller --clean --noconfirm EMBASA.spec

$distDir = Join-Path $PSScriptRoot "dist\EmbasaPedidosSAP"
$exeFinal = Join-Path $distDir "EmbasaPedidosSAP.exe"
$pythonRuntimeDeps = Join-Path $distDir "_internal\pythonnet\runtime\Python.Runtime.deps.json"

if (-not (Test-Path -LiteralPath $exeFinal)) {
    throw "Build incompleto: executavel nao foi gerado em $exeFinal"
}

if (-not (Test-Path -LiteralPath $pythonRuntimeDeps)) {
    throw "Build incompleto: Python.Runtime.deps.json nao foi incluido. Recrie a venv e rode o build novamente."
}

$arquivosRaiz = @(
    "embasa_settings.json",
    "LEIA-ME_EMPRESA.txt",
    "VERSAO.txt"
)

foreach ($arquivo in $arquivosRaiz) {
    $origem = Join-Path $PSScriptRoot $arquivo

    if (Test-Path -LiteralPath $origem) {
        Copy-Item -LiteralPath $origem -Destination $distDir -Force
    }
}

Write-Host ""
Write-Host "Build concluido."
Write-Host "Executavel: $exeFinal"
Write-Host ""
Write-Host "Para publicar na rede:"
Write-Host "powershell -ExecutionPolicy Bypass -File .\publicar_rede.ps1"
