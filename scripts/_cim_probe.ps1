# Quick test, run from elevated PowerShell:
# Checks CIM/WMI API surface for changing service logon account to LocalSystem
$svc = "OmniRoute"
$mgr = Get-CimInstance -ClassName Win32_Service -Filter "Name='$svc'"
Write-Host "Current StartName: $($mgr.StartName)"
Write-Host "StartMode: $($mgr.StartMode)"
Write-Host "PathName:  $($mgr.PathName)"
