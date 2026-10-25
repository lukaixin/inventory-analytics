. "$PSScriptRoot/common.ps1"
if (Get-V7BackendProcess) { throw 'Stop the API before backing up the DuckDB file.' }
$databasePath = Join-Path $RuntimeRoot 'inventory.duckdb'
if (-not (Test-Path -LiteralPath $databasePath)) { throw 'DuckDB file does not exist.' }
$backupRoot = Join-Path $RuntimeRoot 'backups'
New-Item -ItemType Directory -Force $backupRoot | Out-Null
$backupPath = Join-Path $backupRoot ("inventory-" + (Get-Date -Format 'yyyyMMdd-HHmmssfff') + '.duckdb')
$pythonPath = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
& $pythonPath -c 'import duckdb,shutil,sys; con=duckdb.connect(sys.argv[1]); con.execute("CHECKPOINT"); con.close(); shutil.copy2(sys.argv[1],sys.argv[2]); con=duckdb.connect(sys.argv[2],read_only=True); con.execute("SELECT 1").fetchone(); con.close()' $databasePath $backupPath
Assert-NativeExit 'DuckDB checkpoint, backup and read check'
Write-Output "Offline backup created and readable: $backupPath"
Write-Output 'Restore by selecting a separate backup file only after stopping the API. Never overwrite the live database automatically.'
