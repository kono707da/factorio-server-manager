param(
    [int]$Port = 8199
)

$ErrorActionPreference = "SilentlyContinue"

$connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
if (-not $connections) {
    Write-Host "Port $Port is free."
    exit 0
}

$ourPids = @()
$otherPids = @()

foreach ($conn in $connections) {
    $pid = $conn.OwningProcess
    if ($pid -and $ourPids -notcontains $pid -and $otherPids -notcontains $pid) {
        $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($proc) {
            $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $pid" -ErrorAction SilentlyContinue).CommandLine
            if ($cmdLine -and ($cmdLine -match "factorio-manager" -or $cmdLine -match "uvicorn.*app\.main")) {
                $ourPids += $pid
            } else {
                $otherPids += $pid
            }
        }
    }
}

if ($otherPids.Count -gt 0) {
    Write-Host "Port $Port is held by another program (PID: $($otherPids -join ', '))."
    exit 2
}

if ($ourPids.Count -gt 0) {
    foreach ($pid in $ourPids) {
        Write-Host "Killing stale process on port $Port (PID: $pid)..."
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Milliseconds 500

    $stillAlive = $ourPids | Where-Object { (Get-Process -Id $_ -ErrorAction SilentlyContinue) -ne $null }
    if ($stillAlive.Count -gt 0) {
        Write-Host "ERROR: Failed to kill stale process on port $Port."
        exit 1
    }

    Write-Host "Stale process on port $Port killed."
    exit 0
}

exit 0
