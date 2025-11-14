<#
.SYNOPSIS
    Monitors OneDrive status for RMM integration.

.DESCRIPTION
    Detects and reports:
    - OneDrive process not running
    - Sync stopped
    - Sync paused
    - Sync errors
    - Not signed in
    - Trouble signing in

.OUTPUTS
    "Success — OneDrive is healthy" (exit 0)
    or
    "Failure — [reasons]" (exit 1)
#>

# Initialize issue list
$Issues = @()

# Check if OneDrive process is running
$process = Get-Process -Name "OneDrive" -ErrorAction SilentlyContinue
if (-not $process) {
    $Issues += "Not Running"
}

# Registry path to OneDrive accounts
$baseKey = "HKCU:\Software\Microsoft\OneDrive\Accounts"
$accounts = @()

try {
    $accounts = Get-ChildItem -Path $baseKey -ErrorAction Stop
} catch {
    $Issues += "Not Signed In"
}

# Check each detected OneDrive account (Personal, Business, etc.)
foreach ($account in $accounts) {
    try {
        $props = Get-ItemProperty -Path $account.PSPath -ErrorAction Stop

        # Check if signed in
        if (-not $props.UserEmail) {
            $Issues += "Not Signed In"
        }

        # Sync Paused
        if ($props.PauseReason -ne 0) {
            $Issues += "Sync Paused"
        }

        # Sync Errors Detected
        if ($props.SyncErrorStatus -ne 0) {
            $Issues += "Sync Errors Detected"
        }

        # Sync Stopped (no active folders)
        if ($props.HasActiveFolders -eq 0) {
            $Issues += "Sync Stopped"
        }

    } catch {
        $Issues += "Trouble Signing In"
    }
}

# Final Output and Exit Code
if ($Issues.Count -eq 0) {
    Write-Output "Success — OneDrive is healthy"
    exit 0
} else {
    $msg = "Failure — " + ($Issues | Sort-Object -Unique | ForEach-Object { $_ }) -join ", "
    Write-Output $msg
    exit 1
}
