param([switch]$SkipDownload, [switch]$ActivatePostgres)
if (-not $ActivatePostgres) { throw 'Dormant PostgreSQL candidate. Current application uses DuckDB. Review PG migration and configuration before explicitly activating this script.' }
. "$PSScriptRoot/postgres-common.ps1"
New-Item -ItemType Directory -Force $RuntimeRoot | Out-Null
$zipPath = Join-Path $RuntimeRoot 'postgresql-17.11.zip'
$url = 'https://get.enterprisedb.com/postgresql/postgresql-17.11-5-windows-x64-binaries.zip'
$expectedSha256 = '80379B2C04D51C30225532E0AE04509899141E9957ED096FE749D7FD9DF8F82F'
Write-Output '[1/5] Ensure isolated PostgreSQL binaries'
if (-not (Test-Path -LiteralPath (Join-Path $PgBin 'postgres.exe'))) {
    if (-not (Test-Path -LiteralPath $zipPath)) {
        if ($SkipDownload) { throw 'PostgreSQL archive missing.' }
        Invoke-WebRequest -Uri $url -OutFile $zipPath -TimeoutSec 600
    }
    if ((Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash -ne $expectedSha256) { throw 'PostgreSQL archive SHA256 mismatch; refusing extraction.' }
    Expand-Archive -LiteralPath $zipPath -DestinationPath $RuntimeRoot
}
& (Join-Path $PgBin 'postgres.exe') --version
Assert-NativeExit 'PostgreSQL version'
Write-Output '[2/5] Ensure private development settings'
$envPath = Join-Path $RuntimeRoot 'postgres-settings.env'
if (-not (Test-Path -LiteralPath $envPath)) {
    $adminPassword = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(24))
    $appPassword = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(24))
    @(
        'APP_ENV=development'
        'PG_PORT=55437'
        'PG_ADMIN_USER=v7_admin'
        "PG_ADMIN_PASSWORD=$adminPassword"
        'PG_APP_USER=v7_app'
        "PG_APP_PASSWORD=$appPassword"
        "DATABASE_URL=postgresql+psycopg://v7_app:${appPassword}@127.0.0.1:55437/inventory_v7"
        "TEST_DATABASE_URL=postgresql+psycopg://v7_app:${appPassword}@127.0.0.1:55437/inventory_v7_test"
        'ALLOWED_LEGACY_SCOPES='
        'ALLOWED_PDT_SCOPES='
    ) | Set-Content -LiteralPath $envPath -Encoding utf8
}
$settings = Get-V7Settings
Write-Output '[3/5] Initialize cluster only if absent'
if (-not (Test-Path -LiteralPath (Join-Path $PgData 'PG_VERSION'))) {
    $passwordFile = Join-Path $RuntimeRoot 'init-password.tmp'
    try {
        [IO.File]::WriteAllText($passwordFile, $settings.PG_ADMIN_PASSWORD, [Text.UTF8Encoding]::new($false))
        & (Join-Path $PgBin 'initdb.exe') -D $PgData -U $settings.PG_ADMIN_USER --encoding=UTF8 --locale=C --auth=scram-sha-256 "--pwfile=$passwordFile"
        Assert-NativeExit 'initdb'
        @("listen_addresses = '127.0.0.1'", "port = $($settings.PG_PORT)", "password_encryption = 'scram-sha-256'") | Add-Content -LiteralPath (Join-Path $PgData 'postgresql.conf') -Encoding utf8
    } finally {
        if (Test-Path -LiteralPath $passwordFile) { Remove-Item -LiteralPath $passwordFile }
    }
}
Write-Output '[4/5] Start isolated cluster'
& "$PSScriptRoot/start-postgres.ps1" -ActivatePostgres
Write-Output '[5/5] Ensure dedicated non-superuser role and development/test databases'
$oldPassword = $env:PGPASSWORD
try {
    $env:PGPASSWORD = $settings.PG_ADMIN_PASSWORD
    $psql = Join-Path $PgBin 'psql.exe'
    $base = @('-X', '-h', '127.0.0.1', '-p', $settings.PG_PORT, '-U', $settings.PG_ADMIN_USER, '-d', 'postgres', '-v', 'ON_ERROR_STOP=1')
    $roleExists = & $psql @base -tAc "SELECT 1 FROM pg_roles WHERE rolname='v7_app'"
    Assert-NativeExit 'role inspection'
    if (([string]$roleExists).Trim() -ne '1') {
        "CREATE ROLE v7_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD '$($settings.PG_APP_PASSWORD)';" | & $psql @base
        Assert-NativeExit 'application role creation'
    }
    foreach ($databaseName in @('inventory_v7', 'inventory_v7_test')) {
        $databaseExists = & $psql @base -tAc "SELECT 1 FROM pg_database WHERE datname='$databaseName'"
        Assert-NativeExit 'database inspection'
        if (([string]$databaseExists).Trim() -ne '1') {
            "CREATE DATABASE $databaseName OWNER v7_app ENCODING 'UTF8';" | & $psql @base
            Assert-NativeExit 'database creation'
        }
    }
} finally { $env:PGPASSWORD = $oldPassword }
Write-Output 'PostgreSQL ready: 127.0.0.1:55437, databases inventory_v7 and inventory_v7_test. Secrets remain in ignored .env.'
