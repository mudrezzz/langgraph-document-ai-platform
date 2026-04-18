[CmdletBinding()]
param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8000,
    [int]$StartupTimeoutSec = 30,
    [string]$Query = "evidence pack retrieval",
    [string]$CaseDatasetId = "saa_release_readiness"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..\..")
$backendRoot = Join-Path $repoRoot "backend"
$baseUrl = "http://$HostName`:$Port"

$prevPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = "$backendRoot;$backendRoot\packages"

$serverArgs = @(
    "-m", "uvicorn", "apps.api.main:app",
    "--host", $HostName,
    "--port", "$Port"
)

$serverProcess = $null

try {
    # Запускаем API сервер в отдельном процессе для smoke-проверки endpoint-ов.
    $serverProcess = Start-Process -FilePath "python" -ArgumentList $serverArgs -WorkingDirectory $backendRoot -PassThru

    $started = $false
    $deadline = (Get-Date).AddSeconds($StartupTimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $health = Invoke-RestMethod -Method Get -Uri "$baseUrl/health"
            if ($health.status -eq "ok") {
                $started = $true
                break
            }
        }
        catch {
            Start-Sleep -Milliseconds 300
        }
    }

    if (-not $started) {
        throw "API сервер не поднялся за $StartupTimeoutSec секунд"
    }

    $startRequest = @{
        query = $Query
        filters = @{
            project_id = "p1"
            document_types = @("requirements", "methodology", "security", "operations", "governance")
        }
        task_context = @{
            requester = "smoke-script"
            case_dataset_id = $CaseDatasetId
        }
    } | ConvertTo-Json -Depth 10
    $startBody = [System.Text.Encoding]::UTF8.GetBytes($startRequest)

    $startResponse = Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/tasks/retrieval/start" -ContentType "application/json; charset=utf-8" -Body $startBody
    $taskId = $startResponse.task_id

    $statusResponse = Invoke-RestMethod -Method Get -Uri "$baseUrl/api/v1/tasks/$taskId"
    $evidenceResponse = Invoke-RestMethod -Method Get -Uri "$baseUrl/api/v1/tasks/$taskId/evidence"

    $resumeRequest = @{
        decision = "rerun"
        comment = "smoke rerun"
        metadata = @{
            source = "smoke-script"
        }
    } | ConvertTo-Json -Depth 10
    $resumeBody = [System.Text.Encoding]::UTF8.GetBytes($resumeRequest)

    $resumeResponse = Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/tasks/$taskId/resume" -ContentType "application/json; charset=utf-8" -Body $resumeBody
    $historyResponse = Invoke-RestMethod -Method Get -Uri "$baseUrl/api/v1/tasks?limit=5&offset=0"
    $historyTaskIds = @($historyResponse.items | ForEach-Object { $_.task_id })

    $result = [ordered]@{
        base_url = $baseUrl
        dataset_id = $CaseDatasetId
        query = $Query
        task_id = $taskId
        start_status = $startResponse.status
        task_status = $statusResponse.status
        evidence_blocks = $evidenceResponse.evidence_pack.selected_blocks.Count
        top_sources = @($evidenceResponse.evidence_pack.selected_sources | Select-Object -First 3)
        resume_status = $resumeResponse.status
        resume_decision = $resumeResponse.details.resume_decision
        history_returned = @($historyResponse.items).Count
        history_contains_task = ($historyTaskIds -contains $taskId)
    }

    Write-Output ($result | ConvertTo-Json -Depth 10)
}
finally {
    if ($serverProcess -and -not $serverProcess.HasExited) {
        Stop-Process -Id $serverProcess.Id -Force
    }

    if ($null -eq $prevPythonPath) {
        Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    }
    else {
        $env:PYTHONPATH = $prevPythonPath
    }
}
