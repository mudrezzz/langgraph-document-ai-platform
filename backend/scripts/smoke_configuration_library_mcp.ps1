[CmdletBinding()]
param(
    [string]$ConfigId = "retrieval-policy-demo",
    [string]$Version = "1",
    [string]$NextVersion = "2",
    [int]$Limit = 10,
    [int]$Offset = 0
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
    & $pythonExe "$backendRoot\scripts\smoke_configuration_library_mcp.py" --config-id $ConfigId --version $Version --next-version $NextVersion --limit $Limit --offset $Offset
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
