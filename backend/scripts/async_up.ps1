[CmdletBinding()]
param(
    [string]$ComposeFile = "docker-compose.async.yml",
    [string]$ProjectName = "langgraph-async",
    [string]$BackendEnvFile = ".env"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendRoot = Resolve-Path (Join-Path $scriptDir "..")
$composePath = Join-Path $backendRoot $ComposeFile
$envPath = Join-Path $backendRoot $BackendEnvFile

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker не найден в PATH"
}

if (-not (Test-Path $composePath)) {
    throw "Файл compose не найден: $composePath"
}

$cmd = @("compose", "-f", $composePath, "--project-name", $ProjectName)
if (Test-Path $envPath) {
    $cmd += @("--env-file", $envPath)
}
$cmd += @("up", "-d", "--build")

Push-Location $backendRoot
try {
    & docker @cmd
}
finally {
    Pop-Location
}

Write-Host "Redis + Celery worker контейнеры подняты."
Write-Host "Проверьте статус: docker compose -f $composePath --project-name $ProjectName ps"
