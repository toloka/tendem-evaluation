<#
OneDrive Monitoring Script for RMM
Detects OneDrive states and outputs plain text for parsing, with exit codes.

States detected:
- Not Running
- Not Signed In
- Sync Paused
- Sync Stopped (via recent event log keywords)
- Sync Errors Detected (via recent event log errors)
- Trouble Signing In (via recent event log keywords)

Exit codes:
- 0 => Success (no issues)
- 1 => Failure (one or more issues detected)

Usage examples:
  powershell.exe -ExecutionPolicy Bypass -File .\onedrive_monitor.ps1
  powershell.exe -ExecutionPolicy Bypass -File .\onedrive_monitor.ps1 -LookbackMinutes 60
  powershell.exe -ExecutionPolicy Bypass -File .\onedrive_monitor.ps1 -OneDriveExePath "C:\\Program Files\\Microsoft OneDrive\\OneDrive.exe"

Note: Designed to run under SYSTEM or user context. It inspects all loaded user hives under HKEY_USERS.
#>
param(
    [int]$LookbackMinutes = 30,
    [string]$OneDriveExePath = $null
)

$ErrorActionPreference = 'SilentlyContinue'

function Get-LoadedUserSIDs {
    try {
        Get-ChildItem -Path Registry::HKEY_USERS |
            Where-Object { $_.Name -match 'HKEY_USERS\\S-1-5-21-.*' -and $_.Name -notmatch '\\.Default$' }
    } catch {
        @()
    }
}

function Test-OneDriveProcessRunning {
    param([string]$ExePath)
    $proc = Get-Process -Name OneDrive -ErrorAction SilentlyContinue
    if ($proc) { return $true }
    if ($ExePath -and (Test-Path $ExePath)) {
        # Check if the specific exe is running by path
        $procByWMI = Get-CimInstance Win32_Process -Filter "Name='OneDrive.exe'" -ErrorAction SilentlyContinue
        if ($procByWMI) {
            foreach ($p in $procByWMI) {
                if ($p.ExecutablePath -eq $ExePath) { return $true }
            }
        }
    }
    return $false
}

function Test-OneDriveSignedIn {
    # Check all user hives for OneDrive Accounts keys indicating a signed-in account
    $sids = Get-LoadedUserSIDs
    foreach ($sid in $sids) {
        $base = "Registry::${sid.Name.Split(':')[-1]}\\Software\\Microsoft\\OneDrive\\Accounts"
        if (Test-Path $base) {
            $subkeys = Get-ChildItem -Path $base -ErrorAction SilentlyContinue
            foreach ($key in $subkeys) {
                # Heuristics: presence of UserEmail or TenantName indicates configured account
                $userEmail = (Get-ItemProperty -Path $key.PSPath -Name 'UserEmail' -ErrorAction SilentlyContinue).UserEmail
                $tenantName = (Get-ItemProperty -Path $key.PSPath -Name 'TenantName' -ErrorAction SilentlyContinue).TenantName
                $configured = (Get-ItemProperty -Path $key.PSPath -Name 'Configured' -ErrorAction SilentlyContinue).Configured
                if ($userEmail -or $tenantName -or $configured -eq 1) {
                    return $true
                }
            }
        }
    }
    return $false
}

function Test-OneDriveSyncPaused {
    # Check if any user hive has a pause/suspend flag
    $sids = Get-LoadedUserSIDs
    foreach ($sid in $sids) {
        $root = "Registry::${sid.Name.Split(':')[-1]}\\Software\\Microsoft\\OneDrive"
        if (Test-Path $root) {
            $suspend = (Get-ItemProperty -Path $root -Name 'UserSettingSuspendSync' -ErrorAction SilentlyContinue).UserSettingSuspendSync
            $pausedUntil = (Get-ItemProperty -Path $root -Name 'PauseSyncEndTime' -ErrorAction SilentlyContinue).PauseSyncEndTime
            if ($suspend -eq 1) { return $true }
            if ($pausedUntil) {
                try {
                    $end = [DateTime]::FromFileTimeUtc([int64]$pausedUntil)
                    if ($end -gt (Get-Date)) { return $true }
                } catch {}
            }
        }
    }
    return $false
}

function Test-EventLogIssues {
    param(
        [int]$MinutesLookback,
        [string[]]$SignInKeywords = @('sign in','signin','login','credential','auth'),
        [string[]]$SyncStoppedKeywords = @('sync stopped','stopped syncing','syncing stopped','not syncing')
    )
    $since = (Get-Date).AddMinutes(-1 * $MinutesLookback)
    $logNames = @('Application')
    $providers = @('OneDrive','FileSync','OneDrive (Microsoft OneDrive)')

    $filterHash = @{ LogName = $logNames }
    $events = @()
    foreach ($log in $logNames) {
        try {
            # Narrow by time
            $ev = Get-WinEvent -LogName $log -ErrorAction SilentlyContinue |
                Where-Object { $_.TimeCreated -ge $since } |
                Where-Object { $_.ProviderName -in $providers }
            if ($ev) { $events += $ev }
        } catch {}
    }

    $hasError = $false
    $hasSignInTrouble = $false
    $hasSyncStopped = $false

    foreach ($e in $events) {
        $msg = ''
        try { $msg = $e.Message } catch { $msg = '' }
        $lvl = $e.LevelDisplayName
        if ($lvl -eq 'Error' -or $e.Level -eq 2) { $hasError = $true }
        if ($msg) {
            $mLower = $msg.ToLower()
            foreach ($kw in $SignInKeywords) { if ($mLower -like "*${kw}*") { $hasSignInTrouble = $true; break } }
            foreach ($kw in $SyncStoppedKeywords) { if ($mLower -like "*${kw}*") { $hasSyncStopped = $true; break } }
        }
        if ($hasError -and $hasSignInTrouble -and $hasSyncStopped) { break }
    }

    return [PSCustomObject]@{
        HasError = [bool]$hasError
        HasSignInTrouble = [bool]$hasSignInTrouble
        HasSyncStopped = [bool]$hasSyncStopped
    }
}

# Main
$issues = @()

if (-not (Test-OneDriveProcessRunning -ExePath $OneDriveExePath)) {
    $issues += 'Not Running'
}

if (-not (Test-OneDriveSignedIn)) {
    $issues += 'Not Signed In'
}

if (Test-OneDriveSyncPaused) {
    $issues += 'Sync Paused'
}

$eventResults = Test-EventLogIssues -MinutesLookback $LookbackMinutes
if ($eventResults.HasSyncStopped) { $issues += 'Sync Stopped' }
if ($eventResults.HasError) { $issues += 'Sync Errors Detected' }
if ($eventResults.HasSignInTrouble) { $issues += 'Trouble Signing In' }

if ($issues.Count -eq 0) {
    Write-Output 'Success'
    exit 0
} else {
    Write-Output ('Failure: ' + ($issues -join '; '))
    exit 1
}
