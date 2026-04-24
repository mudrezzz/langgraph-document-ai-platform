[CmdletBinding()]
param(
    [string]$InputPath = "backend/examples/cases/release_go_no_go_multifile_case/input",
    [string]$Query = "security approval pending",
    [string]$ProjectId = "p1",
    [string]$DocumentTypes = "requirements,methodology,security,operations,governance",
    [string]$Tags = "",
    [int]$SummaryLimit = 5,
    [int]$BlockLimit = 5,
    [switch]$BuildBinaryDemoDocs
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
        # Предпочитаем python из локального окружения проекта.
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

    $argsList = @(
        "$backendRoot\scripts\smoke_retrieval_mcp.py",
        "--input-path", $InputPath,
        "--query", $Query,
        "--project-id", $ProjectId,
        "--document-types", $DocumentTypes,
        "--tags", $Tags,
        "--summary-limit", $SummaryLimit,
        "--block-limit", $BlockLimit
    )
    if ($BuildBinaryDemoDocs) {
        $argsList += "--build-binary-demo-docs"
    }

    & $pythonExe @argsList
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
