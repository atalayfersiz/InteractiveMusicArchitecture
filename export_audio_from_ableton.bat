@echo off
title Export Audio from Ableton Live & Sync Web Project
cd /d "%~dp0"

echo ======================================================================
echo   Ableton Live -- Auto Export Audio ^& Sync Web Project
echo ======================================================================
echo.
echo  This script will automatically:
echo   [1] Bring your running Ableton Live window to the front
echo   [2] Trigger File ^> Export Audio/Video (Ctrl + Shift + R)
echo   [3] Render the 28-bar master mix to ableton\voices.wav
echo   [4] Slice all 7 architectural stems with micro-crossfades
echo   [5] Update web_prototype/audio/ and jsg_audio_data.js
echo.
echo ======================================================================
echo  Starting in 3 seconds (or press any key to start immediately)...
echo ======================================================================
timeout /t 3 >nul

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0export_audio.ps1"

echo.
echo Press any key to exit...
pause >nul
