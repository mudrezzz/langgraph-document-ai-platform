[CmdletBinding()]
param(
    [string]$InputPath = "backend/examples/cases/release_go_no_go_multifile_case/input",
    [string]$Query = "что блокирует релиз и какие approvals pending"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..\..")
$backendRoot = Join-Path $repoRoot "backend"

function Resolve-PythonExecutable {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    $venvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        return $venvPython
    }

    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        return $pythonCmd.Source
    }

    $python3Cmd = Get-Command python3 -ErrorAction SilentlyContinue
    if ($python3Cmd) {
        return $python3Cmd.Source
    }

    throw "Не найден интерпретатор python/python3"
}

$pythonExe = Resolve-PythonExecutable -RepoRoot $repoRoot
$prevPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = "$backendRoot;$backendRoot\packages"

try {
    Push-Location $repoRoot
    & $pythonExe "$backendRoot\scripts\smoke_canonical_retrieval.py" --input-path $InputPath --query $Query
}
finally {
    Pop-Location
    if ($null -eq $prevPythonPath) {
        Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    }
    else {
        $env:PYTHONPATH = $prevPythonPath
    }
}
