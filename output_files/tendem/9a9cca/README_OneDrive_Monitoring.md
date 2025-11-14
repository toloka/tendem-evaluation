# OneDrive Monitoring Script – Deployment & Usage Documentation

Overview
- Purpose: Monitor Microsoft OneDrive health on Windows 10/11 endpoints and emit plain-text output suitable for RMM parsing with exit codes.
- Script file: `onedrive_monitor.ps1`
- Outputs:
  - Success → exit code 0
  - Failure: <list of issues> → exit code 1
- Target environment: Windows 10/11, OneDrive desktop app installed.

What the Script Detects
- Not Running: OneDrive process (`OneDrive.exe`) not present.
- Not Signed In: No configured OneDrive account detected under user hives.
- Sync Paused: Pause/suspend flags found in user registry (UserSettingSuspendSync or PauseSyncEndTime in the future).
- Sync Stopped: Recent Application event log entries from OneDrive providers containing “sync stopped” keywords.
- Sync Errors Detected: Recent Application event log entries from OneDrive providers with Level Error.
- Trouble Signing In: Recent Application event log entries containing sign-in keywords.

How Detection Works (Technical)
1) Process check:
   - `Get-Process -Name OneDrive` and `Win32_Process` via CIM when `-OneDriveExePath` is provided to match executable path.
2) Signed-in status:
   - Enumerates loaded user hives under `HKEY_USERS`.
   - Looks for `Software\Microsoft\OneDrive\Accounts` subkeys; presence of `UserEmail`, `TenantName`, or `Configured=1` indicates a signed-in account.
3) Sync paused:
   - Checks `Software\Microsoft\OneDrive` for `UserSettingSuspendSync=1` and/or `PauseSyncEndTime` future timestamp.
4) Event log scan:
   - `Get-WinEvent -LogName Application` within a lookback window.
   - Providers: `OneDrive`, `FileSync`, `OneDrive (Microsoft OneDrive)`.
   - Flags:
     - Error level → Sync Errors Detected.
     - Message contains keywords → Trouble Signing In (auth/credential/login/signin) and Sync Stopped (stopped syncing/not syncing).

Script Output Format
- Success
- Failure: Not Running; Sync Paused; Sync Stopped; Sync Errors Detected; Not Signed In; Trouble Signing In
  - Issues are joined by `; `.
- Exit codes: 0 on Success; 1 on Failure.

Configurable Parameters
- `-LookbackMinutes` (int, default 30): Window for scanning Application event log entries.
- `-OneDriveExePath` (string, optional): Explicit path to OneDrive executable (e.g., `C:\Program Files\Microsoft OneDrive\OneDrive.exe`). When provided, the script will validate the running process path via CIM.

Usage Examples
- Default:
  - `powershell.exe -ExecutionPolicy Bypass -File .\onedrive_monitor.ps1`
- Adjust lookback window:
  - `powershell.exe -ExecutionPolicy Bypass -File .\onedrive_monitor.ps1 -LookbackMinutes 60`
- Explicit OneDrive path:
  - `powershell.exe -ExecutionPolicy Bypass -File .\onedrive_monitor.ps1 -OneDriveExePath "C:\\Program Files\\Microsoft OneDrive\\OneDrive.exe"`

RMM Deployment Guidance
1) Context
   - The script inspects all loaded user hives under `HKEY_USERS`. Running under SYSTEM is acceptable and generally preferred for broad coverage.
   - If your RMM can run in user context, it will still work; ensure the user’s hive is loaded.
2) PowerShell bitness
   - Works under either 32-bit or 64-bit PowerShell. Prefer 64-bit when available.
3) Polling interval
   - Recommended: every 15–30 minutes.
   - If you expect fast-changing states, reduce `-LookbackMinutes` to 5–10 to minimize stale event detection.
4) Scripting policy
   - Use `-ExecutionPolicy Bypass` if your environment restricts unsigned scripts.
5) Parsing output
   - Parse stdout for `Success` or `Failure:` prefix.
   - Trigger automated remediation when exit code is 1 and key phrases are present.

Examples for Common RMMs
- Generic RMM “Script Check”:
  - Command: `powershell.exe -ExecutionPolicy Bypass -File "{path_to_script}\onedrive_monitor.ps1" -LookbackMinutes 30`
  - Success condition: exit code = 0 and stdout contains `Success`.
  - Failure condition: exit code != 0 and stdout starts with `Failure:`.

Troubleshooting & Notes
- No events found:
  - Increase `-LookbackMinutes` or verify OneDrive providers are present in Application logs.
- False “Not Signed In” when signed in:
  - Confirm the user hive is loaded and the `Accounts` keys exist.
  - Run in the interactive user context as a test.
- OneDrive process path mismatch:
  - Provide `-OneDriveExePath` if OneDrive is installed in a non-standard directory.
- Keyword heuristics:
  - The script uses keyword matching for “Sync Stopped” and “Trouble Signing In.” Adjust `LookbackMinutes` to tune sensitivity.
- Performance:
  - Designed to be lightweight: limited registry and targeted Application log scan.

Limitations
- Relies on event log messages and registry keys that may vary by OneDrive version/tenant policies.
- “Sync Stopped” and “Trouble Signing In” are heuristic detections based on keywords.
- Deep per-file sync status is not inspected; this script focuses on endpoint health indicators.

Security Considerations
- No elevation changes; reads registry and event logs.
- Outputs plain text only; no sensitive data is logged intentionally.

Versioning & Maintenance
- Keep the script in source control; update providers/keywords if Microsoft changes event log naming.

Files
- `onedrive_monitor.ps1`
