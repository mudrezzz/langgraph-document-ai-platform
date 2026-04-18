[CmdletBinding()]
param(
    [string]$BackendEnvFile = ".env"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendRoot = Resolve-Path (Join-Path $scriptDir "..")
$envPath = Join-Path $backendRoot $BackendEnvFile

if (-not (Test-Path -LiteralPath $envPath)) {
    throw "Файл окружения не найден: $envPath"
}

# Простейшая загрузка key=value из .env в текущий процесс.
Get-Content -Path $envPath | ForEach-Object {
    if (-not $_ -or $_.Trim().StartsWith("#")) {
        return
    }
    $pair = $_ -split "=", 2
    if ($pair.Count -eq 2) {
        $name = $pair[0].Trim()
        $value = $pair[1].Trim()
        if ($name) {
            [System.Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

& (Join-Path $scriptDir "apply_migrations.ps1")