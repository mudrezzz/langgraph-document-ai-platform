[CmdletBinding()]
param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8020
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..\..")
$backendRoot = Join-Path $repoRoot "backend"
$caseRoot = Join-Path $backendRoot "examples\cases\release_go_no_go_case"
$inputMarkdown = Join-Path $caseRoot "input\release_packet.md"
$datasetJson = Join-Path $caseRoot "output\release_packet_dataset.generated.json"
$reportMarkdown = Join-Path $caseRoot "output\release_readiness_report.md"
$pidFile = Join-Path $backendRoot ".demo_release_go_no_go_uvicorn_$Port.pid"

$buildDatasetPath = Join-Path $scriptDir "build_release_packet_dataset.py"
$buildReportPath = Join-Path $scriptDir "build_release_readiness_report.py"
$smokePath = Join-Path $scriptDir "smoke_retrieval_api.ps1"
$baseUrl = "http://$HostName`:$Port"
$query = "Что блокирует релиз Payments v2 и какие approvals еще не закрыты?"

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
$statusFile = $null
$evidenceFile = $null
$summaryFile = $null

try {
    Write-Host "[1/4] Сборка retrieval dataset из markdown release packet..."
    & $pythonExe $buildDatasetPath `
        --input-file $inputMarkdown `
        --output-file $datasetJson `
        --dataset-id "release_go_no_go"

    Write-Host "[2/4] Smoke прогон API с file-based dataset (сервер остается поднятым)..."
    $smokeResult = & "$PSScriptRoot\smoke_retrieval_api.ps1" `
        -HostName $HostName `
        -Port $Port `
        -Query $query `
        -CaseDatasetId "release_go_no_go" `
        -CaseDatasetPath $datasetJson `
        -KeepServer `
        -ServerPidFile $pidFile

    $smokePayload = $smokeResult | ConvertFrom-Json
    $taskId = $smokePayload.task_id

    Write-Host "[3/4] Сбор evidence и audit summary по задаче $taskId..."
    $statusPayload = Invoke-RestMethod -Method Get -Uri "$baseUrl/api/v1/tasks/$taskId"
    $evidencePayload = Invoke-RestMethod -Method Get -Uri "$baseUrl/api/v1/tasks/$taskId/evidence"
    $eventsSummaryPayload = Invoke-RestMethod -Method Get -Uri "$baseUrl/api/v1/tasks/events/summary?task_id=$taskId&task_type=retrieval_pack"

    $statusFile = New-TemporaryFile
    $evidenceFile = New-TemporaryFile
    $summaryFile = New-TemporaryFile
    $statusPayload | ConvertTo-Json -Depth 20 | Out-File -FilePath $statusFile -Encoding utf8
    $evidencePayload | ConvertTo-Json -Depth 20 | Out-File -FilePath $evidenceFile -Encoding utf8
    $eventsSummaryPayload | ConvertTo-Json -Depth 20 | Out-File -FilePath $summaryFile -Encoding utf8

    Write-Host "[4/4] Генерация осмысленного release readiness отчета..."
    & $pythonExe $buildReportPath `
        --task-id $taskId `
        --query $query `
        --status-file $statusFile `
        --evidence-file $evidenceFile `
        --events-summary-file $summaryFile `
        --output-file $reportMarkdown

    Write-Host "=== DEMO: Release Go/No-Go Case ==="
    Write-Host "Input markdown: $inputMarkdown"
    Write-Host "Dataset JSON: $datasetJson"
    Write-Host "Task ID: $taskId"
    Write-Host "Report: $reportMarkdown"
}
finally {
    if (Test-Path $pidFile) {
        $pidValue = Get-Content $pidFile -ErrorAction SilentlyContinue
        if ($pidValue) {
            try {
                Stop-Process -Id [int]$pidValue -Force -ErrorAction SilentlyContinue
            }
            catch {
            }
        }
        Remove-Item $pidFile -ErrorAction SilentlyContinue
    }

    if ($statusFile) { Remove-Item $statusFile -ErrorAction SilentlyContinue }
    if ($evidenceFile) { Remove-Item $evidenceFile -ErrorAction SilentlyContinue }
    if ($summaryFile) { Remove-Item $summaryFile -ErrorAction SilentlyContinue }

    if ($null -eq $prevPythonPath) {
        Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    }
    else {
        $env:PYTHONPATH = $prevPythonPath
    }
}
