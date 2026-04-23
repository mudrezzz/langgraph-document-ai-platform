[CmdletBinding()]
param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8022,
    [switch]$NoBuildBinaryDemoDocs
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
        # Для demo-скрипта используем python из локального окружения репозитория.
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
    $scriptArgs = @(
        "$backendRoot\scripts\demo_release_go_no_go_multifile_case.py",
        "--host",
        $HostName,
        "--port",
        $Port
    )
    if (-not $NoBuildBinaryDemoDocs) {
        $scriptArgs += "--build-binary-demo-docs"
    }
    else {
        $scriptArgs += "--no-build-binary-demo-docs"
    }
    & $pythonExe @scriptArgs
}
finally {
    if ($null -eq $prevPythonPath) {
        Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    }
    else {
        $env:PYTHONPATH = $prevPythonPath
    }
}
