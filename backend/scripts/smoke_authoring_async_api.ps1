[CmdletBinding()]
param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8050,
    [int]$StartupTimeoutSec = 30,
    [string]$Query = "подготовь release readiness draft async + hitl",
    [string]$ArtifactType = "release_report",
    [string]$ArtifactTitle = "Smoke Async Authoring Draft",
    [string]$ArtifactFormat = "markdown",
    [ValidateSet("auto", "deterministic", "llm")]
    [string]$DraftStrategy = "deterministic",
    [ValidateSet("single_pass", "multi_step")]
    [string]$WorkflowMode = "multi_step",
    [ValidateSet("approve", "needs_changes", "reject")]
    [string]$HitlDecision = "approve",
    [string]$HitlDecisionSequence = "",
    [string]$CaseDatasetId = "saa_release_readiness",
    [string]$CaseDatasetPath = "",
    [string]$CaseDatasetDir = "",
    [switch]$HitlRequired
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..\..")
$backendRoot = Join-Path $repoRoot "backend"

function Resolve-PythonExecutable {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)

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
& $pythonExe -c "import uvicorn" *> $null
if ($LASTEXITCODE -ne 0) {
    throw "В выбранном интерпретаторе ($pythonExe) не найден модуль uvicorn."
}

$prevPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = "$backendRoot;$backendRoot\packages"

try {
    Push-Location $repoRoot
    $pythonArgs = @(
        "$backendRoot\scripts\smoke_authoring_async_api.py",
        "--host", $HostName,
        "--port", $Port,
        "--startup-timeout-sec", $StartupTimeoutSec,
        "--query", $Query,
        "--artifact-type", $ArtifactType,
        "--artifact-title", $ArtifactTitle,
        "--artifact-format", $ArtifactFormat,
        "--draft-strategy", $DraftStrategy,
        "--workflow-mode", $WorkflowMode,
        "--hitl-decision", $HitlDecision,
        "--hitl-decision-sequence", $HitlDecisionSequence,
        "--case-dataset-id", $CaseDatasetId,
        "--case-dataset-path", $CaseDatasetPath,
        "--case-dataset-dir", $CaseDatasetDir
    )
    if ($HitlRequired.IsPresent) {
        $pythonArgs += "--hitl-required"
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
