[CmdletBinding()]
param(
    [string]$OutputDir = "backend/examples/cases/release_go_no_go_multifile_case/input",
    [switch]$Overwrite
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
    $scriptArgs = @("$backendRoot\scripts\build_binary_demo_documents.py", "--output-dir", $OutputDir)
    if ($Overwrite) {
        $scriptArgs += "--overwrite"
    }
    & $pythonExe @scriptArgs
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
