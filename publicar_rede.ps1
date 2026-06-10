param(
    [string]$DestinoRede = (
        "N:\DF\FAFT\documentos\Gerir Tesouraria\Outros receb" +
        [char]0x00ED +
        "veis\Servi" +
        [char]0x00E7 +
        "os t" +
        [char]0x00E9 +
        "cnicos\Geracao Boletos Automaticos\EmbasaPedidosSAP"
    )
)

$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

$BuildDir = Join-Path $PSScriptRoot "dist\EmbasaPedidosSAP"
$ExePath = Join-Path $BuildDir "EmbasaPedidosSAP.exe"
$PastaPaiRede = Split-Path -Path $DestinoRede -Parent

Write-Host "==============================================="
Write-Host " PUBLICACAO EMBASA PEDIDOS SAP"
Write-Host "==============================================="
Write-Host ""
Write-Host "Origem : $BuildDir"
Write-Host "Destino: $DestinoRede"
Write-Host ""

if (-not (Test-Path -LiteralPath $ExePath)) {
    throw "Build nao encontrado. Rode primeiro: powershell -ExecutionPolicy Bypass -File .\build_empresarial.ps1"
}

if (-not (Test-Path -LiteralPath $PastaPaiRede)) {
    throw "Pasta pai da rede nao encontrada: $PastaPaiRede"
}

if (-not (Test-Path -LiteralPath $DestinoRede)) {
    New-Item -ItemType Directory -Path $DestinoRede -Force | Out-Null
}

Write-Host "Copiando build onedir para a rede..."

$null = robocopy $BuildDir $DestinoRede /MIR /R:2 /W:2 /XD "__pycache__" "dados_compartilhados" /XF "*.pyc" "*.pyo"
$RoboCode = $LASTEXITCODE

if ($RoboCode -gt 7) {
    throw "Falha ao publicar na rede. Codigo robocopy: $RoboCode"
}

$ExeRede = Join-Path $DestinoRede "EmbasaPedidosSAP.exe"
$LauncherRede = Join-Path $DestinoRede "Abrir_EMBASA_Rapido.cmd"

if (-not (Test-Path -LiteralPath $ExeRede)) {
    throw "Publicacao incompleta: executavel nao encontrado no destino."
}

$LauncherConteudo = @'
@echo off
setlocal
set "SOURCE_DIR=%~dp0"
set "EXE_REDE=%SOURCE_DIR%EmbasaPedidosSAP.exe"
set "VERSION_FILE=%SOURCE_DIR%VERSAO.txt"
set "LOCAL_DIR="

for /f "usebackq delims=" %%D in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$version=(Get-Content -LiteralPath $env:VERSION_FILE -ErrorAction SilentlyContinue | Select-Object -First 1); $root=Join-Path $env:LOCALAPPDATA 'EMBASA\Runtime'; if($version -and (Test-Path -LiteralPath $root)){ Get-ChildItem -LiteralPath $root -Directory -ErrorAction SilentlyContinue | Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'EmbasaPedidosSAP.exe') } | Where-Object { (Get-Content -LiteralPath (Join-Path $_.FullName 'VERSAO.txt') -ErrorAction SilentlyContinue | Select-Object -First 1) -eq $version } | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName }"`) do set "LOCAL_DIR=%%D"

if defined LOCAL_DIR if exist "%LOCAL_DIR%\EmbasaPedidosSAP.exe" (
    set "EMBASA_LOCAL_RUNTIME=1"
    set "EMBASA_NETWORK_SOURCE=%SOURCE_DIR%"
    start "" "%LOCAL_DIR%\EmbasaPedidosSAP.exe" %*
    exit /b
)

start "" "%EXE_REDE%" %*
'@

Set-Content -LiteralPath $LauncherRede -Value $LauncherConteudo -Encoding ASCII

Write-Host ""
Write-Host "==============================================="
Write-Host " PUBLICACAO CONCLUIDA COM SUCESSO"
Write-Host "==============================================="
Write-Host ""
Write-Host "Atalho dos usuarios deve apontar preferencialmente para:"
Write-Host $LauncherRede
Write-Host ""
Write-Host "Executavel publicado em:"
Write-Host $ExeRede
