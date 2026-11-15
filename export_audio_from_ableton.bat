@echo off
title LMMS SoundLab -- Render Audio & Sync Project
cd /d "%~dp0"

echo ======================================================================
echo   LMMS SoundLab -- Headless Export Audio ^& Sync Web Project
echo ======================================================================
echo.
echo  Switched from Ableton Live to open-source LMMS.
echo  This tool will:
echo   [1] Render InteractiveMusicArchitecture_SoundLab.mmp headlessly
echo   [2] Write ableton\voices.wav (44.1 kHz)
echo   [3] Slice all 7 architectural stems with 15 ms micro-crossfades
echo   [4] Update web_prototype/audio/ and jsg_audio_data.js
echo.
echo ======================================================================

python "%~dp0export_and_sync_lmms.py"

echo.
pause
