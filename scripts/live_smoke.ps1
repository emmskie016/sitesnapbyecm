# Live smoke test against the deployed Render service.
# POSTs a real submission, then polls the job until it reaches done/failed.

$BASE = "https://sitesnap-backend-uc7s.onrender.com"

Write-Host "=== /healthz ===" -ForegroundColor Cyan
try {
    $h = Invoke-RestMethod -Uri "$BASE/healthz" -TimeoutSec 60
    Write-Host ($h | ConvertTo-Json -Depth 5 -Compress)
} catch {
    Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== POST /api/sites ===" -ForegroundColor Cyan
$body = @{
    full_name     = "Live Smoke Test"
    email         = "myemail@emmersonmorales.com"
    brand_name    = "Loaf and Larder"
    industry      = "neighborhood bakery and small-batch coffee roaster"
    questionnaire = @{
        tone           = "warm grounded unpretentious"
        differentiator = "sourdough cold-fermented 48 hours; beans roasted in-house"
        city           = "Brooklyn"
        audience       = "morning regulars from the surrounding three blocks"
    }
} | ConvertTo-Json -Depth 5 -Compress

$resp = Invoke-RestMethod -Uri "$BASE/api/sites" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 60
Write-Host "job_id    = $($resp.job_id)"
Write-Host "status URL = $BASE$($resp.status_url)"
$jobId = $resp.job_id

Write-Host ""
Write-Host "=== polling /api/jobs/$jobId every 3s ===" -ForegroundColor Cyan
$lastStatus = ""
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 3
    try {
        $j = Invoke-RestMethod -Uri "$BASE/api/jobs/$jobId" -TimeoutSec 30
    } catch {
        Write-Host ("{0,4}s  poll error: {1}" -f ($i * 3 + 3), $_.Exception.Message) -ForegroundColor Yellow
        continue
    }
    $line = "{0,4}s  status={1,-18} progress={2,3}%" -f ($i * 3 + 3), $j.status, $j.progress_pct
    if ($j.site_url) { $line += "  url=$($j.site_url)" }
    if ($j.error)    { $line += "  error_code=$($j.error.code)" }
    if ($j.status -ne $lastStatus) {
        Write-Host $line -ForegroundColor Green
        $lastStatus = $j.status
    } else {
        Write-Host $line
    }
    if ($j.status -eq "done" -or $j.status -eq "failed") {
        Write-Host ""
        Write-Host "=== final job row ===" -ForegroundColor Cyan
        Write-Host ($j | ConvertTo-Json -Depth 5)
        break
    }
}
