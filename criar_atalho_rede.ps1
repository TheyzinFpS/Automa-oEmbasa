param(
    [Parameter(Mandatory = $true)]
    [string]$CaminhoExeRede,

    [string]$NomeAtalho = "Embasa Pedidos SAP"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $CaminhoExeRede)) {
    throw "Executavel nao encontrado: $CaminhoExeRede"
}

$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "$NomeAtalho.lnk"
$pastaRede = Split-Path -Parent $CaminhoExeRede
$launcherRapido = Join-Path $pastaRede "Abrir_EMBASA_Rapido.cmd"
$targetPath = if (Test-Path -LiteralPath $launcherRapido) { $launcherRapido } else { $CaminhoExeRede }

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $targetPath
$shortcut.WorkingDirectory = $pastaRede
$shortcut.IconLocation = "$CaminhoExeRede,0"
$shortcut.Description = "EMBASA - Automacao de Pedidos SAP"
$shortcut.Save()

Write-Host "Atalho criado em:"
Write-Host $shortcutPath
