[CmdletBinding()]
param(
    [string]$ComposeFile = "docker-compose.async.yml",
    [string]$ProjectName = "langgraph-async",
    [switch]$RemoveVolumes
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendRoot = Resolve-Path (Join-Path $scriptDir "..")
$composePath = Join-Path $backendRoot $ComposeFile

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker не найден в PATH"
}

if (-not (Test-Path $composePath)) {
    throw "Файл compose не найден: $composePath"
}

$cmd = @("compose", "-f", $composePath, "--project-name", $ProjectName, "down")
if ($RemoveVolumes.IsPresent) {
    $cmd += "--volumes"
}

Push-Location $backendRoot
try {
    & docker @cmd
}
finally {
    Pop-Location
}

Write-Host "Redis + Celery worker контейнеры остановлены."
