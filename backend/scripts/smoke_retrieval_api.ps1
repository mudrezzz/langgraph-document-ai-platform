[CmdletBinding()]
param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8000,
    [int]$StartupTimeoutSec = 30
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
        query = "evidence pack retrieval"
        filters = @{
            project_id = "p1"
            document_types = @("requirements", "methodology")
        }
        task_context = @{
            requester = "smoke-script"
        }
    } | ConvertTo-Json -Depth 10

    $startResponse = Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/tasks/retrieval/start" -ContentType "application/json" -Body $startRequest
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

    $resumeResponse = Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/tasks/$taskId/resume" -ContentType "application/json" -Body $resumeRequest

    $result = [ordered]@{
        base_url = $baseUrl
        task_id = $taskId
        start_status = $startResponse.status
        task_status = $statusResponse.status
        evidence_blocks = $evidenceResponse.evidence_pack.selected_blocks.Count
        resume_status = $resumeResponse.status
        resume_decision = $resumeResponse.details.resume_decision
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