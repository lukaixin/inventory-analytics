. "$PSScriptRoot/common.ps1"
New-Item -ItemType Directory -Force $RuntimeRoot | Out-Null
$envPath = Join-Path $ProjectRoot '.env'
if (Test-Path -LiteralPath $envPath) { Write-Output 'Existing private .env retained.'; exit 0 }
$databasePath = (Join-Path $RuntimeRoot 'inventory.duckdb').Replace('\','/')
$testPath = (Join-Path $RuntimeRoot 'inventory-test.duckdb').Replace('\','/')
@(
    'APP_ENV=development'
    "DATABASE_URL=duckdb:///$databasePath"
    "TEST_DATABASE_URL=duckdb:///$testPath"
    'ALLOWED_LEGACY_SCOPES='
    'ALLOWED_PDT_SCOPES='
) | Set-Content -LiteralPath $envPath -Encoding utf8
Write-Output 'DuckDB settings created. Database will be initialized by Alembic, never deleted by this script.'
