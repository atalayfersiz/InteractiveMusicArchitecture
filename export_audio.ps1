# export_audio.ps1
# Automates exporting audio from Ableton Live 12 and syncs with the web prototype.

param(
    [string]$TargetFile = "D:\CODING\InteractiveMusicArchitecture\ableton\voices.wav"
)

$targetDir = [System.IO.Path]::GetDirectoryName($TargetFile)
if (-not (Test-Path $targetDir)) {
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
}

$alsPath = "D:\CODING\InteractiveMusicArchitecture\InteractiveMusicArchitecture_SoundLab.als"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  Interactive Music Architecture - Ableton Live Audio Exporter" -ForegroundColor White
Write-Host "======================================================================" -ForegroundColor Cyan

# 1. Check if Ableton Live is running
$liveProc = Get-Process -Name "*Live*" -ErrorAction SilentlyContinue | Select-Object -First 1

if (-not $liveProc) {
    Write-Host "[!] Ableton Live is not currently running." -ForegroundColor Yellow
    Write-Host "[*] Launching SoundLab project in Ableton Live..." -ForegroundColor Cyan
    Start-Process $alsPath
    Write-Host "    Please wait for Ableton Live to finish loading, then run this script again." -ForegroundColor Green
    Exit 0
}

Write-Host "[*] Found running Ableton Live process (PID: $($liveProc.Id))." -ForegroundColor Green

# Record previous file timestamp to detect when export finishes
$prevModTime = [DateTime]::MinValue
if (Test-Path $TargetFile) {
    $prevModTime = (Get-Item $TargetFile).LastWriteTime
}

$wshell = New-Object -ComObject WScript.Shell

Write-Host "[*] Bringing Ableton Live to foreground..." -ForegroundColor Cyan
$activated = $wshell.AppActivate("SoundLab") -or $wshell.AppActivate("Ableton Live") -or $wshell.AppActivate("Live") -or $wshell.AppActivate($liveProc.Id)

Start-Sleep -Milliseconds 600

# 2. Trigger Export Audio/Video (Ctrl + Shift + R)
Write-Host "[*] Triggering Export Audio/Video (Ctrl + Shift + R)..." -ForegroundColor Cyan
$wshell.SendKeys("^+r")

Start-Sleep -Milliseconds 1200

# 3. Press Enter on the Export Audio/Video modal to confirm export settings
Write-Host "[*] Confirming Export Settings..." -ForegroundColor Cyan
$wshell.SendKeys("{ENTER}")

Start-Sleep -Milliseconds 1200

# 4. Set clipboard to destination path and paste into the Save As dialog
Write-Host "[*] Setting destination path: $TargetFile" -ForegroundColor Cyan
Set-Clipboard -Value $TargetFile
Start-Sleep -Milliseconds 300
$wshell.SendKeys("^v")
Start-Sleep -Milliseconds 400
$wshell.SendKeys("{ENTER}")

Start-Sleep -Milliseconds 800

# In case Windows asks to overwrite existing file, confirm with 'y' and Enter
$wshell.SendKeys("y")
Start-Sleep -Milliseconds 300
$wshell.SendKeys("{ENTER}")

Write-Host "[*] Waiting for Ableton to render audio..." -ForegroundColor Yellow

# 5. Monitor for file creation / update
$rendered = $false
$maxWaitSeconds = 60
$elapsed = 0

while ($elapsed -lt $maxWaitSeconds) {
    Start-Sleep -Seconds 1
    $elapsed++
    
    if (Test-Path $TargetFile) {
        $curItem = Get-Item $TargetFile
        if ($curItem.LastWriteTime -gt $prevModTime) {
            try {
                $fileStream = [System.IO.File]::Open($TargetFile, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::None)
                if ($fileStream.Length -gt 10000) {
                    $fileStream.Close()
                    $rendered = $true
                    break
                }
                $fileStream.Close()
            } catch {
                # File is still being written by Ableton
            }
        }
    }
    Write-Host "    Rendering... ($($elapsed)s)" -ForegroundColor DarkGray
}

if ($rendered) {
    $sizeMb = [Math]::Round((Get-Item $TargetFile).Length / 1MB, 2)
    Write-Host "[SUCCESS] Ableton exported voices.wav ($sizeMb MB)!" -ForegroundColor Green
    Write-Host ""
    Write-Host "[*] Slicing stems and syncing with web project..." -ForegroundColor Cyan
    
    $importerPath = Join-Path $scriptDir "import_ableton_sounds.py"
    if (Test-Path $importerPath) {
        python $importerPath
    } else {
        python "D:\CODING\InteractiveMusicArchitecture\import_ableton_sounds.py"
    }
    
    Write-Host ""
    Write-Host "======================================================================" -ForegroundColor Green
    Write-Host " [OK] ALL SOUNDS EXPORTED AND IMPORTED TO WEB PROJECT SUCCESSFULLY!" -ForegroundColor Green
    Write-Host " Refresh your browser (Ctrl + F5) at http://localhost:8080" -ForegroundColor Green
    Write-Host "======================================================================" -ForegroundColor Green
} else {
    Write-Host "[!] Timed out waiting for automatic render." -ForegroundColor Yellow
    Write-Host "    If Ableton export dialog is open, simply save as:" -ForegroundColor White
    Write-Host "    $TargetFile" -ForegroundColor Cyan
    Write-Host "    Then run import_sounds.bat to sync." -ForegroundColor White
}
