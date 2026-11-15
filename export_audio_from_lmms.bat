@echo off
title LMMS -- Render Audio & Sync Web Project
cd /d "%~dp0"

echo ======================================================================
echo   LMMS -- Headless Audio Export ^& Web Project Sync
echo ======================================================================
echo.
echo  This tool will:
echo   [1] Render InteractiveMusicArchitecture_SoundLab.mmp via LMMS CLI
echo   [2] Export the 28-bar mix to ableton\voices.wav (44.1 kHz)
echo   [3] Verify non-zero audio output
echo   [4] Slice all 7 architectural stems with 15 ms loop crossfades
echo   [5] Update web_prototype\audio\ and jsg_audio_data.js
echo.
echo ======================================================================

python "%~dp0export_and_sync_lmms.py"
if errorlevel 1 (
    echo.
    echo [FAILED] Export encountered an error. Check messages above.
)

echo.
pause
