[CmdletBinding()]
param([string]$EnvFile, [int]$WaitTimeout = 240)

$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw 'Docker is unavailable. Install and start Docker Desktop first.'
    }
    & docker info --format '{{.ServerVersion}}' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Docker Desktop is not ready.' }
    $composeArgs = @('compose', '-f', 'compose.yaml')
    if ($EnvFile) { $composeArgs += @('--env-file', $EnvFile) }
    & docker @composeArgs up -d --build --wait --wait-timeout $WaitTimeout
    if ($LASTEXITCODE -ne 0) {
        throw 'Compose startup failed. Inspect: docker compose logs backend frontend db'
    }
    $frontendAddress = & docker @composeArgs port frontend 3000
    if ($LASTEXITCODE -ne 0) { throw 'Unable to resolve frontend port.' }
    $backendAddress = & docker @composeArgs port backend 8000
    if ($LASTEXITCODE -ne 0) { throw 'Unable to resolve backend port.' }
    $databaseAddress = & docker @composeArgs port db 5432
    if ($LASTEXITCODE -ne 0) { throw 'Unable to resolve database port.' }
    $frontendUrl = 'http://' + ([string]$frontendAddress).Replace('127.0.0.1', 'localhost')
    $backendUrl = 'http://' + ([string]$backendAddress).Replace('127.0.0.1', 'localhost')
    Write-Host "Frontend: $frontendUrl"
    Write-Host "Backend:  $backendUrl"
    Write-Host "API docs: $backendUrl/docs"
    Write-Host "Database: $databaseAddress"
    Write-Host 'Stop with .\stop.ps1; database volume is preserved.'
} finally { Pop-Location }
