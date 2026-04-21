[CmdletBinding()]
param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8060,
    [ValidateSet("approve", "needs_changes", "reject")]
    [string]$HitlDecision = "approve"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..\..")
$backendRoot = Join-Path $repoRoot "backend"
$outputFile = Join-Path $backendRoot "examples\cases\release_go_no_go_case\output\authoring_async_hitl_result.json"

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $outputFile) | Out-Null

Write-Host "[1/2] Smoke async authoring + HITL flow..."
$smokeOutput = powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $backendRoot "scripts\smoke_authoring_async_api.ps1") `
    -HostName $HostName `
    -Port $Port `
    -Query "Подготовь async release readiness draft с HITL решением" `
    -ArtifactType "release_report" `
    -ArtifactTitle "Release Async HITL Demo" `
    -ArtifactFormat "markdown" `
    -WorkflowMode "multi_step" `
    -DraftStrategy "deterministic" `
    -HitlDecision $HitlDecision `
    -HitlRequired

Write-Host "[2/2] Сохраняем demo-результат..."
$smokeOutput | Out-File -FilePath $outputFile -Encoding utf8

Write-Host "=== DEMO: Release Authoring Async + HITL Case ==="
Write-Host "Output: $outputFile"
Write-Host ""
Write-Host "Краткий результат:"
Write-Output $smokeOutput
