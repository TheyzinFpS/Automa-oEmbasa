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

if (-not (Test-Path -LiteralPath $ExeRede)) {
    throw "Publicacao incompleta: executavel nao encontrado no destino."
}

Write-Host ""
Write-Host "==============================================="
Write-Host " PUBLICACAO CONCLUIDA COM SUCESSO"
Write-Host "==============================================="
Write-Host ""
Write-Host "Atalho dos usuarios deve apontar para:"
Write-Host $ExeRede
