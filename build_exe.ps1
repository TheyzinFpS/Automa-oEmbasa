$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $projectRoot ".venv\\Scripts\\python.exe"

function Invoke-Native([scriptblock]$command) {
    & $command

    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao executar comando nativo. Exit code: $LASTEXITCODE"
    }
}

function Assert-InProject([string]$path) {
    $resolved = [System.IO.Path]::GetFullPath($path)
    $root = [System.IO.Path]::GetFullPath($projectRoot)

    if (-not $resolved.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Caminho fora do projeto: $resolved"
    }

    return $resolved
}

if (-not (Test-Path $venvPython)) {
    throw "Ambiente .venv não encontrado. Execute setup_env.ps1 primeiro."
}

Push-Location $projectRoot

try {
    foreach ($artifact in @("build", "dist")) {
        $artifactPath = Join-Path $projectRoot $artifact

        if (Test-Path $artifactPath) {
            $target = Assert-InProject $artifactPath
            Remove-Item -LiteralPath $target -Recurse -Force
        }
    }

    Invoke-Native { & $venvPython -m PyInstaller --noconfirm --clean (Join-Path $projectRoot "main.spec") }
}
finally {
    Pop-Location
}

$exePath = Join-Path $projectRoot "dist\\EMBASA\\EMBASA.exe"

if (-not (Test-Path $exePath)) {
    throw "Build concluído sem gerar dist\\EMBASA\\EMBASA.exe"
}

Get-Item $exePath | Select-Object FullName, Length, LastWriteTime
