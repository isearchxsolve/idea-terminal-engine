# fix_omniroute_throttle.ps1
# Run as Administrator to prevent OmniRoute crash-storm restarts.
# Sets NSSM AppThrottle from 1500ms → 30000ms (30 seconds).
#
# Usage (from an elevated PowerShell prompt):
#   .\scripts\fix_omniroute_throttle.ps1

$svc = "OmniRoute"

Write-Host "=== OmniRoute NSSM Throttle Fix ===" -ForegroundColor Cyan
Write-Host "Current AppThrottle:"
nssm get $svc AppThrottle

Write-Host "`nSetting AppThrottle to 30000ms (30 seconds)..."
nssm set $svc AppThrottle 30000
if ($LASTEXITCODE -eq 0) {
    Write-Host "Done." -ForegroundColor Green
} else {
    Write-Host "Failed — make sure you are running as Administrator." -ForegroundColor Red
    exit 1
}

Write-Host "`nVerifying..."
nssm get $svc AppThrottle

Write-Host "`nAlso setting AppRestartDelay to 15000ms (15 seconds)..."
nssm set $svc AppRestartDelay 15000

Write-Host "`nAll settings:" -ForegroundColor Cyan
nssm get $svc AppThrottle
nssm get $svc AppRestartDelay
nssm get $svc AppExit

Write-Host "`n[OK] Throttle fix applied. No service restart needed (takes effect on next crash)." -ForegroundColor Green
