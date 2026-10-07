$ErrorActionPreference = 'Stop'
$d2aRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
if ($d2aRoot -ne 'C:\Users\ykw\Documents\ChatGPT\CEO-FDI') { throw 'Unexpected workspace root' }
$d2aLauncherPath = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot 'd2a_cert_resume_detached.ps1')).Path
$d2aLaunchCommand = '"' + [Environment]::ProcessPath + '" -NoProfile -NonInteractive -WindowStyle Hidden -File "' + $d2aLauncherPath + '"'
$d2aStartup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ ShowWindow = [uint16]0 }
$d2aResult = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $d2aLaunchCommand; CurrentDirectory = $d2aRoot; ProcessStartupInformation = $d2aStartup }
$d2aResult | Select-Object ReturnValue,ProcessId | ConvertTo-Json -Compress
if ($d2aResult.ReturnValue -ne 0) { throw 'WMI detached launcher failed' }
