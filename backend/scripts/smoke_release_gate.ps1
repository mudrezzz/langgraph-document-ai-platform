[CmdletBinding()]
param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8088,
    [string]$DraftStrategy = "deterministic",
    [string]$WorkflowMode = "multi_step",
    [string]$HitlDecisionSequence = "needs_changes,approve",
    [switch]$RequireLlmTokens,
    [switch]$SkipKnowledgeIndexing,
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

$argsList = @(
    "$backendRoot\scripts\smoke_release_gate.py",
    "--host", $HostName,
    "--port", $Port,
    "--draft-strategy", $DraftStrategy,
    "--workflow-mode", $WorkflowMode,
    "--hitl-decision-sequence", $HitlDecisionSequence
)
if ($RequireLlmTokens) { $argsList += "--require-llm-tokens" }
if ($SkipKnowledgeIndexing) { $argsList += "--skip-knowledge-indexing" }
if ($BuildBinaryDemoDocs) { $argsList += "--build-binary-demo-docs" }

try {
    Push-Location $repoRoot
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
