param([switch]$Migrate, [switch]$Seed)
. "$PSScriptRoot/common.ps1"
& "$PSScriptRoot/bootstrap-local.ps1"
$pythonPath = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Missing project .venv. Follow README dependency setup.' }
$existing = Get-V7BackendProcess
if ($existing -and ($Migrate -or $Seed)) { throw 'Stop API before migrations/seed: DuckDB permits one writer process.' }
if ($Migrate -or $Seed) {
    Push-Location (Join-Path $ProjectRoot 'backend')
    try {
        if ($Migrate) { & $pythonPath -m alembic upgrade head; Assert-NativeExit 'Alembic migration' }
        if ($Seed) { & $pythonPath -m app.seed; Assert-NativeExit 'Seed' }
    } finally { Pop-Location }
}
$pidPath = Join-Path $RuntimeRoot 'backend-process.json'
if ($existing) {
    $response = Invoke-WebRequest -Uri 'http://127.0.0.1:8170/health/ready' -TimeoutSec 5
    if ($response.StatusCode -ne 200) { throw 'Recorded API process is not ready.' }
    Write-Output 'Recorded project API process is already running and ready.'
    exit 0
}
if (Get-NetTCPConnection -LocalPort 8170 -State Listen -ErrorAction SilentlyContinue) { throw 'Port 8170 is occupied by an unverified process; not starting or stopping it.' }
$process = Start-Process -FilePath $pythonPath -ArgumentList @('-m','uvicorn','app.main:app','--app-dir','backend','--host','127.0.0.1','--port','8170') -WorkingDirectory $ProjectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $RuntimeRoot 'backend.out.log') -RedirectStandardError (Join-Path $RuntimeRoot 'backend.err.log')
$created = Get-CimInstance Win32_Process -Filter "ProcessId = $($process.Id)"
@{pid=$process.Id;created_at=$created.CreationDate.ToUniversalTime().ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath $pidPath -Encoding utf8
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    try {
        $response = Invoke-WebRequest -Uri 'http://127.0.0.1:8170/health/ready' -TimeoutSec 2
        if ($response.StatusCode -eq 200) { Write-Output 'Application ready: http://127.0.0.1:8170 ; API docs: /docs'; exit 0 }
    } catch { Start-Sleep -Milliseconds 500 }
}
throw 'API did not become ready. Inspect .runtime/backend.err.log; process retained for diagnosis.'
