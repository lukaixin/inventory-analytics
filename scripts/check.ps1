. "$PSScriptRoot/common.ps1"
foreach ($path in @('/health/live','/health/ready','/api/v1/datasets','/openapi.json')) {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8170$path" -TimeoutSec 5
    if ($response.StatusCode -ne 200) { throw "$path failed" }
    Write-Output "$path HTTP 200"
}
Write-Output 'Readiness executes database checks inside the single backend writer process.'
