[CmdletBinding()]
param([string]$EnvFile)

$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw 'Docker is unavailable.'
    }
    $composeArgs = @('compose', '-f', 'compose.yaml')
    if ($EnvFile) { $composeArgs += @('--env-file', $EnvFile) }
    & docker @composeArgs down
    if ($LASTEXITCODE -ne 0) { throw 'Compose shutdown failed.' }
    Write-Host 'Stopped Docker development services. Database volume preserved.'
} finally { Pop-Location }
