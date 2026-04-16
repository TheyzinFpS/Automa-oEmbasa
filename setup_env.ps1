$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvDir = Join-Path $projectRoot ".venv"
$venvPython = Join-Path $venvDir "Scripts\\python.exe"

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

if (Test-Path $venvDir) {
    $target = Assert-InProject $venvDir
    Remove-Item -LiteralPath $target -Recurse -Force
}

$pyLauncher = Get-Command py -ErrorAction SilentlyContinue

if ($pyLauncher) {
    Invoke-Native { py -3.11 -m venv $venvDir }
}
else {
    $python311 = "C:\\Users\\Taylor\\AppData\\Local\\Programs\\Python\\Python311\\python.exe"

    if (-not (Test-Path $python311)) {
        throw "Python 3.11 não encontrado. Instale o Python 3.11 antes de continuar."
    }

    Invoke-Native { & $python311 -m venv $venvDir }
}

Invoke-Native { & $venvPython -m pip install --upgrade pip }
Invoke-Native { & $venvPython -m pip install -r (Join-Path $projectRoot "requirements.txt") }
Invoke-Native { & $venvPython -m pip check }
Invoke-Native { & $venvPython -c "import sys, webview, pythonnet; print(sys.executable); print(sys.version)" }
