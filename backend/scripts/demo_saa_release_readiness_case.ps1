[CmdletBinding()]
param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8010
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$smokePath = Join-Path $scriptDir "smoke_retrieval_api.ps1"

$query = "Какие ключевые ограничения и approval точки нужно учесть перед релизом SAA?"

$resultJson = & $smokePath `
    -HostName $HostName `
    -Port $Port `
    -CaseDatasetId "saa_release_readiness" `
    -Query $query

$result = $resultJson | ConvertFrom-Json

Write-Host "=== DEMO: SAA Release Readiness Case ==="
Write-Host "Task ID: $($result.task_id)"
Write-Host "Status: $($result.task_status)"
Write-Host "Evidence blocks: $($result.evidence_blocks)"
Write-Host "Top sources:"

foreach ($src in $result.top_sources) {
    Write-Host "- doc_id=$($src.doc_id), version=$($src.version), block_id=$($src.block_id)"
}

Write-Host "Resume status: $($result.resume_status)"
Write-Host "History returned: $($result.history_returned)"
Write-Host "History contains task: $($result.history_contains_task)"
Write-Host "Events returned: $($result.events_returned)"
Write-Host "Has running->completed event: $($result.events_has_running_to_completed)"
Write-Host "Events summary total: $($result.events_summary_total)"
Write-Host "Events summary unique tasks: $($result.events_summary_unique_tasks)"
Write-Host "Summary has running->completed: $($result.events_summary_has_running_to_completed)"
