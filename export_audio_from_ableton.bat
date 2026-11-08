@echo off
title Ableton Live -- Export Audio & Sync Project
cd /d "%~dp0"

echo ======================================================================
echo   Ableton Live -- Auto Export Audio ^& Sync Web Project
echo ======================================================================
echo.
echo  This tool will:
echo   [1] Bring your running Ableton Live window to the front
echo   [2] Trigger File ^> Export Audio/Video (Ctrl + Shift + R)
echo   [3] Render the 28-bar master mix to ableton\voices.wav
echo   [4] Slice all 7 architectural stems with micro-crossfades
echo   [5] Update web_prototype/audio/ and jsg_audio_data.js
echo.
echo ======================================================================
echo  Starting in 2 seconds (or press any key to start immediately)...
echo ======================================================================
timeout /t 2 >nul

python "%~dp0export_and_sync_ableton.py"

echo.
pause
