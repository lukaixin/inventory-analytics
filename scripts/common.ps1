$ErrorActionPreference = 'Stop'
$script:ProjectRoot = Split-Path -Parent $PSScriptRoot
$script:RuntimeRoot = Join-Path $ProjectRoot '.runtime'
function Get-V7Settings {
    $settings = @{}
    $path = Join-Path $ProjectRoot '.env'
    if (-not (Test-Path -LiteralPath $path)) { throw 'Missing .env. Run scripts/bootstrap-local.ps1 first.' }
    foreach ($line in Get-Content -LiteralPath $path -Encoding utf8) {
        if ($line -match '^([A-Z_]+)=(.*)$') { $settings[$Matches[1]] = $Matches[2].Trim() }
    }
    return $settings
}
function Assert-NativeExit([string]$Step) {
    if ($LASTEXITCODE -ne 0) { throw "$Step failed with exit code $LASTEXITCODE" }
}
function Get-V7BackendProcess {
    $path = Join-Path $RuntimeRoot 'backend-process.json'
    if (-not (Test-Path -LiteralPath $path)) { return $null }
    $record = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $($record.pid)" -ErrorAction SilentlyContinue
    if (-not $process) { return $null }
    $expected = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
    $recordedTime = ([datetime]$record.created_at).ToUniversalTime().ToString('o')
    if ($process.ExecutablePath -ne $expected -or $process.CommandLine -notlike '*uvicorn app.main:app*' -or $process.CreationDate.ToUniversalTime().ToString('o') -ne $recordedTime) { throw 'API PID identity changed; refusing to operate on another process.' }
    return $process
}
