[CmdletBinding()]
param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8040
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..\..")
$backendRoot = Join-Path $repoRoot "backend"
$outputFile = Join-Path $backendRoot "examples\cases\release_go_no_go_case\output\authoring_traceability_result.json"

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $outputFile) | Out-Null

Write-Host "[1/2] Smoke authoring API flow..."
$smokeOutput = powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $backendRoot "scripts\smoke_authoring_api.ps1") `
    -HostName $HostName `
    -Port $Port `
    -Query "Подготовь черновик release readiness и traceability для Payments v2" `
    -ArtifactType "release_report" `
    -ArtifactTitle "Release Authoring Traceability Demo" `
    -ArtifactFormat "markdown" `
    -WorkflowMode "multi_step" `
    -CaseDatasetId "saa_release_readiness"

Write-Host "[2/2] Сохраняем demo-результат..."
$smokeOutput | Out-File -FilePath $outputFile -Encoding utf8

Write-Host "=== DEMO: Release Authoring Traceability Case ==="
Write-Host "Output: $outputFile"
Write-Host ""
Write-Host "Краткий результат:"
Write-Output $smokeOutput
