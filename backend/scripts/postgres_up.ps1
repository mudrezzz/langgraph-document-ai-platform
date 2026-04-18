[CmdletBinding()]
param(
    [string]$ComposeFile = "docker-compose.postgres.yml",
    [string]$ProjectName = "langgraph",
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

if (-not (Test-Path -LiteralPath $composePath)) {
    throw "Файл compose не найден: $composePath"
}

$cmd = @("compose", "-f", $composePath, "--project-name", $ProjectName)

if (Test-Path -LiteralPath $envPath) {
    $cmd += @("--env-file", $envPath)
}

$cmd += @("up", "-d")

Push-Location $backendRoot
try {
    docker @cmd
}
finally {
    Pop-Location
}

Write-Host "PostgreSQL контейнер поднят."
Write-Host "Проверьте статус: docker compose -f $composePath --project-name $ProjectName ps"