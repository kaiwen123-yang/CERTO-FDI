$ErrorActionPreference = 'Stop'
$d2aRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$d2aExpectedRoot = 'C:\Users\ykw\Documents\ChatGPT\CEO-FDI'
if ($d2aRoot -ne $d2aExpectedRoot) { throw 'Unexpected workspace root' }
$d2aWork = Join-Path $d2aRoot 'work'
$d2aPreparation = Get-Content -LiteralPath (Join-Path $d2aWork 'd2a_cert_detached_recovery_preparation.json') -Raw | ConvertFrom-Json
$d2aProtocol = (Get-FileHash -LiteralPath (Join-Path $d2aWork 'd2a_PROTOCOL_v1.json') -Algorithm SHA256).Hash.ToLowerInvariant()
if ($d2aPreparation.protocol_sha256 -ne $d2aProtocol -or $d2aPreparation.status -ne 'PREPARED_STOPPED_RUN_RECOVERY') { throw 'Preparation/protocol mismatch' }
$d2aStamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ')
$d2aReceiptPath = Join-Path $d2aWork ('d2a_cert_detached_launch_' + $d2aStamp + '.json')
$d2aReceipt = [ordered]@{ status = 'STARTING'; utc = (Get-Date).ToUniversalTime().ToString('o'); workspace = $d2aRoot; protocol_sha256 = $d2aProtocol; launcher_pid = $PID; launcher_mode = 'WMI broker outside unified-exec descendant tree; Start-Process Hidden'; removed_stale_locks = @(); science_pid = $null; publisher_pid = $null; unified_exec_session = $null; preparation_receipt = 'work/d2a_cert_detached_recovery_preparation.json' }

function Save-D2aReceipt {
    $d2aJson = $d2aReceipt | ConvertTo-Json -Depth 8
    [System.IO.File]::WriteAllText($d2aReceiptPath + '.next', $d2aJson, [System.Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath ($d2aReceiptPath + '.next') -Destination $d2aReceiptPath -Force
    $d2aCurrent = Join-Path $d2aWork 'd2a_cert_detached_launch_receipt.json'
    [System.IO.File]::WriteAllText($d2aCurrent + '.next', $d2aJson, [System.Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath ($d2aCurrent + '.next') -Destination $d2aCurrent -Force
}

try {
    foreach ($d2aOldPid in @([int]$d2aPreparation.old_science_pid, [int]$d2aPreparation.old_publisher_pid)) {
        if (Get-Process -Id $d2aOldPid -ErrorAction SilentlyContinue) { throw "Old process $d2aOldPid remains alive" }
    }
    $d2aExisting = @(Get-CimInstance Win32_Process -Filter "Name = 'python.exe' OR Name = 'pythonw.exe'" | Where-Object { $_.CommandLine -match 'd2a_cert_batch\.py|d2a_cert_publish_live\.py' })
    if ($d2aExisting.Count -gt 0) { throw 'Another science runner or publisher is already alive' }
    foreach ($d2aName in @('d2a_cert_batch.lock','d2a_cert_live_publisher.lock')) {
        if (-not (Test-Path -LiteralPath (Join-Path $d2aWork $d2aName))) {
            if ($d2aPreparation.allow_missing_locks) { continue }
            throw 'Expected stale lock is missing'
        }
        $d2aLockPath = (Resolve-Path -LiteralPath (Join-Path $d2aWork $d2aName)).Path
        if (-not $d2aLockPath.StartsWith($d2aRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)) { throw 'Lock target outside workspace' }
        $d2aLock = Get-Content -LiteralPath $d2aLockPath -Raw | ConvertFrom-Json
        $d2aPreserved = @($d2aPreparation.preserved | Where-Object { $_.source -eq ('work\' + $d2aName) })
        if ($d2aPreserved.Count -ne 1 -or (Get-FileHash -LiteralPath $d2aLockPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $d2aPreserved[0].sha256) { throw 'Stale lock differs from preserved receipt' }
        if ($d2aName -eq 'd2a_cert_batch.lock') {
            if ($d2aLock.pid -ne $d2aPreparation.old_science_pid -or $d2aLock.protocol_sha256 -ne $d2aProtocol) { throw 'Wrong science lock owner/protocol' }
        } elseif ($d2aLock.pid -ne $d2aPreparation.old_publisher_pid -or $d2aLock.watch_pid -ne $d2aPreparation.old_science_pid) { throw 'Wrong publisher lock owner' }
        if (Get-Process -Id ([int]$d2aLock.pid) -ErrorAction SilentlyContinue) { throw 'Lock owner became alive' }
        Remove-Item -LiteralPath $d2aLockPath
        $d2aReceipt.removed_stale_locks += $d2aLockPath
        Save-D2aReceipt
    }
    $d2aPython = 'C:\Users\ykw\AppData\Local\Programs\Python\Python312\python.exe'
    $d2aScienceOut = Join-Path $d2aWork ('d2a_cert_detached_science_' + $d2aStamp + '.stdout.log')
    $d2aScienceErr = Join-Path $d2aWork ('d2a_cert_detached_science_' + $d2aStamp + '.stderr.log')
    $d2aScience = Start-Process -FilePath $d2aPython -ArgumentList @('-B','-X','utf8',(Join-Path $d2aWork 'd2a_cert_batch.py')) -WorkingDirectory $d2aRoot -WindowStyle Hidden -RedirectStandardOutput $d2aScienceOut -RedirectStandardError $d2aScienceErr -PassThru
    $d2aReceipt.science_pid = $d2aScience.Id
    $d2aReceipt.science_stdout = $d2aScienceOut
    $d2aReceipt.science_stderr = $d2aScienceErr
    Save-D2aReceipt
    $d2aNewLockPath = Join-Path $d2aWork 'd2a_cert_batch.lock'
    for ($d2aTry = 0; $d2aTry -lt 100; $d2aTry++) {
        if (Test-Path -LiteralPath $d2aNewLockPath -PathType Leaf) { break }
        if (-not (Get-Process -Id $d2aScience.Id -ErrorAction SilentlyContinue)) { throw 'Science runner exited before writing its lock' }
        Start-Sleep -Milliseconds 200
    }
    $d2aNewLock = Get-Content -LiteralPath $d2aNewLockPath -Raw | ConvertFrom-Json
    if ($d2aNewLock.pid -ne $d2aScience.Id -or $d2aNewLock.protocol_sha256 -ne $d2aProtocol) { throw 'New science lock mismatch' }
    $d2aPublisherOut = Join-Path $d2aWork ('d2a_cert_detached_publisher_' + $d2aStamp + '.stdout.log')
    $d2aPublisherErr = Join-Path $d2aWork ('d2a_cert_detached_publisher_' + $d2aStamp + '.stderr.log')
    $d2aPublisher = Start-Process -FilePath $d2aPython -ArgumentList @('-B','-X','utf8',(Join-Path $d2aWork 'd2a_cert_publish_live.py'),'--watch-pid',[string]$d2aScience.Id) -WorkingDirectory $d2aRoot -WindowStyle Hidden -RedirectStandardOutput $d2aPublisherOut -RedirectStandardError $d2aPublisherErr -PassThru
    $d2aReceipt.publisher_pid = $d2aPublisher.Id
    $d2aReceipt.publisher_stdout = $d2aPublisherOut
    $d2aReceipt.publisher_stderr = $d2aPublisherErr
    Start-Sleep -Seconds 1
    $d2aReceipt.science_alive_at_handoff = [bool](Get-Process -Id $d2aScience.Id -ErrorAction SilentlyContinue)
    $d2aReceipt.publisher_alive_at_handoff = [bool](Get-Process -Id $d2aPublisher.Id -ErrorAction SilentlyContinue)
    $d2aReceipt.processes_at_handoff = @(Get-CimInstance Win32_Process -Filter "ProcessId = $($d2aScience.Id) OR ProcessId = $($d2aPublisher.Id)" | Select-Object ProcessId,ParentProcessId,CreationDate,CommandLine)
    if (-not $d2aReceipt.science_alive_at_handoff -or -not $d2aReceipt.publisher_alive_at_handoff) { throw 'A detached process exited at handoff' }
    $d2aReceipt.status = 'DETACHED_SERIAL_SCIENCE_AND_METADATA_STARTED'
    Save-D2aReceipt
} catch {
    $d2aReceipt.status = 'DETACHED_LAUNCH_FAILED_OR_PARTIAL'
    $d2aReceipt.error = $_.Exception.Message
    Save-D2aReceipt
    throw
}
