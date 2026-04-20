[CmdletBinding()]
param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8000,
    [int]$StartupTimeoutSec = 30,
    [string]$Query = "evidence pack retrieval",
    [string]$CaseDatasetId = "saa_release_readiness",
    [string]$CaseDatasetPath = "",
    [switch]$KeepServer,
    [string]$ServerPidFile = ""
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..\..")
$backendRoot = Join-Path $repoRoot "backend"
$baseUrl = "http://$HostName`:$Port"
$startedOk = $false

function Resolve-PythonExecutable {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    $venvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        # Предпочитаем python из локального venv, чтобы исключить расхождения окружений.
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

if ($KeepServer -and [string]::IsNullOrWhiteSpace($ServerPidFile)) {
    $ServerPidFile = Join-Path $backendRoot ".smoke_uvicorn_$Port.pid"
}

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
    $serverProcess = Start-Process -FilePath $pythonExe -ArgumentList $serverArgs -WorkingDirectory $backendRoot -PassThru

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
    $startedOk = $true

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

    if (-not [string]::IsNullOrWhiteSpace($CaseDatasetPath)) {
        $startRequestObject = $startRequest | ConvertFrom-Json
        $startRequestObject.task_context.case_dataset_path = $CaseDatasetPath
        $startRequest = $startRequestObject | ConvertTo-Json -Depth 10
    }
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
    $historyResponse = Invoke-RestMethod -Method Get -Uri "$baseUrl/api/v1/tasks?limit=5&status=completed&task_type=retrieval_pack"
    $eventsResponse = Invoke-RestMethod -Method Get -Uri "$baseUrl/api/v1/tasks/events?limit=10&task_id=$taskId&task_type=retrieval_pack"
    $eventsSummaryResponse = Invoke-RestMethod -Method Get -Uri "$baseUrl/api/v1/tasks/events/summary?task_id=$taskId&task_type=retrieval_pack"
    $historyTaskIds = @($historyResponse.items | ForEach-Object { $_.task_id })
    $hasCompletedTransition = @($eventsResponse.items | Where-Object { $_.from_status -eq "running" -and $_.to_status -eq "completed" }).Count -gt 0
    $summaryHasCompletedTransition = @($eventsSummaryResponse.transitions | Where-Object { $_.from_status -eq "running" -and $_.to_status -eq "completed" }).Count -gt 0

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
        events_returned = @($eventsResponse.items).Count
        events_has_running_to_completed = $hasCompletedTransition
        events_summary_total = $eventsSummaryResponse.total_events
        events_summary_unique_tasks = $eventsSummaryResponse.unique_tasks
        events_summary_has_running_to_completed = $summaryHasCompletedTransition
    }

    Write-Output ($result | ConvertTo-Json -Depth 10)
}
finally {
    if ($serverProcess -and -not $serverProcess.HasExited) {
        if ($KeepServer -and $startedOk) {
            Set-Content -Path $ServerPidFile -Value "$($serverProcess.Id)" -Encoding utf8
            Write-Warning "Smoke: API сервер оставлен запущенным (pid=$($serverProcess.Id))."
            Write-Warning "Smoke: stop command -> Stop-Process -Id $($serverProcess.Id) -Force; Remove-Item '$ServerPidFile'"
        }
        else {
            Stop-Process -Id $serverProcess.Id -Force
        }
    }

    if ($null -eq $prevPythonPath) {
        Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    }
    else {
        $env:PYTHONPATH = $prevPythonPath
    }
}
