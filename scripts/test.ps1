# Run against a fresh isolated file; never the development database.
$ErrorActionPreference = 'Stop'
$v7Root = Split-Path -Parent $PSScriptRoot
$v7Python = Join-Path $v7Root '.venv\Scripts\python.exe'
$v7TestRoot = Join-Path $v7Root '.runtime\tests'
New-Item -ItemType Directory -Force $v7TestRoot | Out-Null
$v7TestFile = Join-Path $v7TestRoot ('inventory-test-' + [guid]::NewGuid().ToString('N') + '.duckdb')
$v7PriorDb = $env:DATABASE_URL
$v7PriorIntegration = $env:RUN_DUCKDB_INTEGRATION
try {
    $env:DATABASE_URL = 'duckdb:///' + $v7TestFile.Replace('\','/')
    $env:RUN_DUCKDB_INTEGRATION = '1'
    if (-not $env:DATABASE_URL.Contains('/.runtime/tests/inventory-test-')) { throw 'Refusing non-isolated test target.' }
    Push-Location (Join-Path $v7Root 'backend')
    try {
        & $v7Python -m alembic upgrade head
        if ($LASTEXITCODE -ne 0) { throw 'Test migration failed.' }
        & $v7Python -m pytest -q
        if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed.' }
    } finally { Pop-Location }
} finally {
    $env:DATABASE_URL = $v7PriorDb
    $env:RUN_DUCKDB_INTEGRATION = $v7PriorIntegration
}
