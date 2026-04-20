[CmdletBinding()]
param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8030,
    [int]$StartupTimeoutSec = 30,
    [string]$Query = "подготовь release readiness draft и traceability",
    [string]$ArtifactType = "release_report",
    [string]$ArtifactTitle = "Smoke Authoring Draft",
    [string]$ArtifactFormat = "markdown",
    [ValidateSet("auto", "deterministic", "llm")]
    [string]$DraftStrategy = "auto",
    [switch]$RequireLlm,
    [string]$CaseDatasetId = "saa_release_readiness",
    [string]$CaseDatasetPath = "",
    [string]$CaseDatasetDir = ""
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
& $pythonExe -c "import uvicorn" *> $null
if ($LASTEXITCODE -ne 0) {
    throw "В выбранном интерпретаторе ($pythonExe) не найден модуль uvicorn. Активируйте .venv или установите зависимости."
}

$prevPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = "$backendRoot;$backendRoot\packages"

try {
    Push-Location $repoRoot
    $pythonArgs = @(
        "$backendRoot\scripts\smoke_authoring_api.py",
        "--host", $HostName,
        "--port", $Port,
        "--startup-timeout-sec", $StartupTimeoutSec,
        "--query", $Query,
        "--artifact-type", $ArtifactType,
        "--artifact-title", $ArtifactTitle,
        "--artifact-format", $ArtifactFormat,
        "--draft-strategy", $DraftStrategy,
        "--case-dataset-id", $CaseDatasetId,
        "--case-dataset-path", $CaseDatasetPath,
        "--case-dataset-dir", $CaseDatasetDir
    )
    if ($RequireLlm.IsPresent) {
        $pythonArgs += "--require-llm"
    }
    & $pythonExe @pythonArgs
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
