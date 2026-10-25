$ErrorActionPreference = 'Stop'
$script:ProjectRoot = Split-Path -Parent $PSScriptRoot
$script:RuntimeRoot = Join-Path $ProjectRoot '.runtime'
New-Item -ItemType Directory -Force $RuntimeRoot | Out-Null
# PostgreSQL's Windows initdb cannot reliably embed non-ASCII paths into bootstrap SQL.
# A per-user drive alias keeps every physical file inside this project.
$mappingFile = Join-Path $RuntimeRoot 'drive-alias.json'
$mapping = if (Test-Path -LiteralPath $mappingFile) { Get-Content -LiteralPath $mappingFile -Raw | ConvertFrom-Json } else { $null }
$substMappings = @{}
foreach ($entry in (& subst.exe)) {
    if ($entry -match '^([A-Z]):\\: => (.+)$') { $substMappings[$Matches[1]] = $Matches[2] }
}
$letter = if ($mapping) { $mapping.letter } else { $null }
if ($letter -and $substMappings.ContainsKey($letter) -and $substMappings[$letter] -ne $ProjectRoot) { throw 'Recorded drive alias points elsewhere; refusing to change it.' }
if ($letter -and (Test-Path "${letter}:\") -and -not $substMappings.ContainsKey($letter)) { throw 'Recorded drive alias is occupied by another drive.' }
if (-not $letter) {
    $letter = @('V','W','X','Y','Z','U','T','S') | Where-Object { -not (Test-Path "${_}:\") } | Select-Object -First 1
    if (-not $letter) { throw 'No available temporary drive alias for PostgreSQL.' }
}
if (-not $substMappings.ContainsKey($letter)) {
    & subst.exe "${letter}:" $ProjectRoot
    if ($LASTEXITCODE -ne 0) { throw 'Failed to create project drive alias.' }
}
@{letter=$letter;target=$ProjectRoot} | ConvertTo-Json | Set-Content -LiteralPath $mappingFile -Encoding utf8
$script:PgRuntimeRoot = "${letter}:\.runtime"
$script:PgBin = Join-Path $PgRuntimeRoot 'pgsql\bin'
$script:PgData = Join-Path $PgRuntimeRoot 'pgdata'
function Get-V7Settings {
    $settings = @{}
    $path = Join-Path $RuntimeRoot 'postgres-settings.env'
    if (-not (Test-Path -LiteralPath $path)) { throw 'Missing .env. Run scripts/bootstrap-postgres.ps1 first.' }
    foreach ($line in Get-Content -LiteralPath $path -Encoding utf8) {
        if ($line -match '^([A-Z_]+)=(.*)$') { $settings[$Matches[1]] = $Matches[2].Trim() }
    }
    return $settings
}
function Assert-NativeExit([string]$Step) {
    if ($LASTEXITCODE -ne 0) { throw "$Step failed with exit code $LASTEXITCODE" }
}
function Assert-V7PgProcess {
    $pidFile = Join-Path $PgData 'postmaster.pid'
    if (-not (Test-Path -LiteralPath $pidFile)) { return $false }
    $lines = Get-Content -LiteralPath $pidFile
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $($lines[0])" -ErrorAction SilentlyContinue
    if (-not $process) { return $false }
    $expected = [IO.Path]::GetFullPath((Join-Path $PgBin 'postgres.exe'))
    $physicalExpected = Join-Path $RuntimeRoot 'pgsql\bin\postgres.exe'
    if ($process.ExecutablePath -ne $expected -and $process.ExecutablePath -ne $physicalExpected) { throw 'PostgreSQL PID belongs to another executable; refusing operation.' }
    $recordedData = [IO.Path]::GetFullPath($lines[1])
    if ($recordedData -ne [IO.Path]::GetFullPath($PgData)) { throw 'PostgreSQL data path mismatch; refusing operation.' }
    return $true
}
