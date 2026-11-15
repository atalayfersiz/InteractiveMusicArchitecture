@echo off
title Open LMMS SoundLab Project
cd /d "%~dp0"

set "LMMS_EXE="
if exist "D:\Program Files\LMMS\lmms.exe" set "LMMS_EXE=D:\Program Files\LMMS\lmms.exe"
if not defined LMMS_EXE if exist "D:\LMMS\lmms.exe" set "LMMS_EXE=D:\LMMS\lmms.exe"
if not defined LMMS_EXE if exist "C:\Program Files\LMMS\lmms.exe" set "LMMS_EXE=C:\Program Files\LMMS\lmms.exe"

if not defined LMMS_EXE (
    echo [ERROR] Could not locate lmms.exe on D: or C: drive.
    pause
    exit /b 1
)

echo Launching LMMS with lmms\InteractiveMusicArchitecture_SoundLab.mmp...
start "" "%LMMS_EXE%" "%~dp0lmms\InteractiveMusicArchitecture_SoundLab.mmp"
