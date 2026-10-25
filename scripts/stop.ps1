. "$PSScriptRoot/common.ps1"
$process = Get-V7BackendProcess
if ($process) {
    # Windows venv python may be a redirector with a real interpreter child.
    $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId = $($process.ProcessId)" | Where-Object { $_.ExecutablePath -ne (Join-Path $env:SystemRoot 'System32\conhost.exe') })
    foreach ($child in $children) {
        if ($child.CommandLine -ne $process.CommandLine -or $child.CreationDate -lt $process.CreationDate -or [IO.Path]::GetFileName($child.ExecutablePath) -ne 'python.exe') { throw 'Unexpected child process; refusing to stop the process tree.' }
    }
    foreach ($child in $children) { Stop-Process -Id $child.ProcessId -ErrorAction SilentlyContinue }
    Stop-Process -Id $process.ProcessId -ErrorAction SilentlyContinue
    if (Get-NetTCPConnection -LocalPort 8170 -State Listen -ErrorAction SilentlyContinue) { throw 'API port is still listening; inspect process state before continuing.' }
    Write-Output 'Project API stopped. DuckDB file retained.'
}
$pidPath = Join-Path $RuntimeRoot 'backend-process.json'
if (Test-Path -LiteralPath $pidPath) { Remove-Item -LiteralPath $pidPath }
