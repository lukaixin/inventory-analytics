param([switch]$ActivatePostgres)
if (-not $ActivatePostgres) { throw 'Dormant PostgreSQL candidate; current application uses DuckDB.' }
. "$PSScriptRoot/postgres-common.ps1"
$settings = Get-V7Settings
if (-not (Test-Path -LiteralPath (Join-Path $PgData 'PG_VERSION'))) { throw 'Cluster is not initialized. Run bootstrap-postgres.ps1.' }
if (-not (Assert-V7PgProcess)) {
    & (Join-Path $PgBin 'pg_ctl.exe') -D $PgData -l (Join-Path $PgRuntimeRoot 'postgres.log') -w start
    Assert-NativeExit 'PostgreSQL startup'
}
& (Join-Path $PgBin 'pg_isready.exe') -h 127.0.0.1 -p $settings.PG_PORT
Assert-NativeExit 'PostgreSQL readiness'
