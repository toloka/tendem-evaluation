#
# Onedrive Monitoring Script
#
# This PowerShell script monitors the state of the Microsoft OneDrive sync client
# for the currently logged‑on user. It is designed to be executed by a Remote
# Monitoring and Management (RMM) tool on Windows 10 or Windows 11 devices. The
# script attempts to detect the most common failure modes of OneDrive (such as
# the process not running, the user not signed in, paused or stopped sync,
# and sync errors) by inspecting the running processes, the user’s registry
# hive and the built‑in OneDrive log file (SyncDiagnostics.log). When no
# problems are detected the script prints “Success” and exits with code 0.
# Otherwise it prints “Failure: …” followed by a list of detected issues and
# exits with code 1. The output format is plain text to facilitate easy
# parsing by RMM platforms.
#
# The script contains no third‑party dependencies and uses only built‑in
# PowerShell cmdlets. It should be run in the user context when possible,
# but it also contains logic to determine the interactive user and load
# their registry hive when executed as the system account. See the
# accompanying documentation for further details.

param(
    # How many hours back to look when examining the SyncDiagnostics.log.
    [int]$LogLookbackHours = 24,
    # The OneDrive process name (default: OneDrive). Override this if your
    # deployment uses a different binary name.
    [string]$OneDriveProcessName = 'OneDrive'
)

function Get-LoggedInUser {
    <#
    .SYNOPSIS
        Returns the SID and username of the primary interactive user.
    .DESCRIPTION
        When the script runs under the SYSTEM account there is no user‑
        specific environment (HKCU), so we need to discover which user is
        currently logged on. The technique below enumerates the owner of
        explorer.exe, then resolves the SID from the ProfileList registry
        entries. This approach comes from Andrew Taylor’s blog on
        enumerating the logged on user when running as SYSTEM【75572633694309†L61-L74】.
    .OUTPUTS
        Hashtable with keys UserName and SID, or $null if no user could be
        identified.
    #>
    try {
        # Find the username associated with explorer.exe. This should be the
        # primary interactive session on a Windows client.
        $user = Get-WmiObject Win32_Process -Filter "Name='explorer.exe'" |
            ForEach-Object { $_.GetOwner() } |
            Select-Object -Unique -ExpandProperty User

        if ([string]::IsNullOrWhiteSpace($user)) {
            return $null
        }

        # Resolve the SID by matching the profile path in the ProfileList key
        $profileListPath = 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\*'
        $sid = (Get-ItemProperty -Path $profileListPath |
            Where-Object { $_.ProfileImagePath -like "*$user" }).PSChildName

        if ([string]::IsNullOrWhiteSpace($sid)) {
            return $null
        }

        return @{ UserName = $user; SID = $sid }
    } catch {
        return $null
    }
}

function Get-OneDriveStatusFromLog {
    <#
    .SYNOPSIS
        Parses the latest SyncDiagnostics.log file for a user and returns the
        last observed SyncProgressState.
    .DESCRIPTION
        OneDrive writes a file named SyncDiagnostics.log in
        %LOCALAPPDATA%\Microsoft\OneDrive\logs\<Account> (e.g. Business1).
        The file contains lines with a property called SyncProgressState.
        According to testing described by Rudy Ooms【880171871167664†L53-L61】, values
        0 or 16777216 correspond to “Up‑to‑Date”, 65536 to “Paused”, 8194
        to “Not syncing” and 1854 to “Having syncing problems”. This
        function searches for the most recent SyncDiagnostics.log under the
        user’s OneDrive logs folder, looks back up to the specified number
        of hours, and returns the numeric state. If no log is found or the
        state cannot be parsed the function returns $null.
    .PARAMETER UserProfile
        The path to the user’s profile folder (e.g. C:\Users\alice).
    .PARAMETER LookbackHours
        How far back in hours to consider log files. Files older than this
        threshold are ignored.
    .OUTPUTS
        Integer representing the last SyncProgressState value, or $null.
    #>
    param(
        [Parameter(Mandatory)] [string]$UserProfile,
        [Parameter(Mandatory)] [int]$LookbackHours
    )

    $logsRoot = Join-Path -Path $UserProfile -ChildPath 'AppData\Local\Microsoft\OneDrive\logs'
    if (-not (Test-Path $logsRoot)) {
        return $null
    }

    # Find all SyncDiagnostics.log files within the logs directory. We do not
    # know whether the account folder is Business1, Business, Personal, etc.,
    # so we search recursively.
    $cutoff = (Get-Date).AddHours(-$LookbackHours)
    $logFile = Get-ChildItem -Path $logsRoot -Filter 'SyncDiagnostics.log' -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -gt $cutoff } |
        Sort-Object -Property LastWriteTime -Descending |
        Select-Object -First 1
    if ($null -eq $logFile) {
        return $null
    }
    try {
        # Read the log and locate the last occurrence of SyncProgressState
        $lines = Get-Content -Path $logFile.FullName -ErrorAction Stop
        $stateLine = $lines | Where-Object { $_ -match 'SyncProgressState' } | Select-Object -Last 1
        if ($null -eq $stateLine) {
            return $null
        }
        # Split on ':' and trim whitespace. The state appears after the colon.
        $parts = $stateLine -split ':'
        if ($parts.Length -gt 1) {
            $value = $parts[1].Trim()
            if ($value -match '^[0-9]+$') {
                return [int]$value
            }
        }
        return $null
    } catch {
        return $null
    }
}

# Main script execution
$issues = @()

# Determine the interactive user
$userInfo = Get-LoggedInUser
if ($null -eq $userInfo) {
    Write-Output 'Failure: No logged in user detected'
    exit 1
}

$userName = $userInfo.UserName
$userSID = $userInfo.SID

# Check whether the OneDrive process is running
$process = Get-Process -Name $OneDriveProcessName -ErrorAction SilentlyContinue
if ($null -eq $process) {
    $issues += 'Not Running'
}

# Check if the user has signed in to OneDrive by looking for the Accounts key
$accountKeyPath = "Registry::HKEY_USERS\$userSID\Software\Microsoft\OneDrive\Accounts"
if (-not (Test-Path $accountKeyPath)) {
    $issues += 'Not Signed In'
}

# If the user is signed in, attempt to read the last SyncProgressState from the log
if (-not $issues.Contains('Not Signed In')) {
    # Derive the user profile path from the ProfileList registry entry
    $profilePath = (Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\$userSID").ProfileImagePath
    $stateValue = Get-OneDriveStatusFromLog -UserProfile $profilePath -LookbackHours $LogLookbackHours
    if ($null -ne $stateValue) {
        switch ($stateValue) {
            {$_ -in 0, 16777216, 42} {
                # Up‑to‑Date means success; nothing to add to issues
                break
            }
            65536 {
                $issues += 'Sync Paused'
                break
            }
            8194 {
                $issues += 'Sync Stopped'
                break
            }
            1854 {
                $issues += 'Sync Errors Detected'
                break
            }
            default {
                # Unknown sync state; treat as error
                $issues += "Unknown Sync State ($stateValue)"
                break
            }
        }
    } else {
        # No recent log found – this might indicate that sync isn’t running
        $issues += 'Sync Stopped'
    }
}

# If the process is running but the user isn’t signed in, this could be a
# sign‑in issue. Mark it explicitly to distinguish from the user never
# configuring OneDrive.
if ($issues.Contains('Not Signed In') -and $null -ne $process) {
    $issues += 'Trouble Signing In'
}

# Compose output
if ($issues.Count -eq 0) {
    Write-Output 'Success'
    exit 0
} else {
    # Remove duplicates and format as a comma‑separated list
    $uniqueIssues = $issues | Select-Object -Unique
    $message = 'Failure: ' + ($uniqueIssues -join ', ')
    Write-Output $message
    exit 1
}