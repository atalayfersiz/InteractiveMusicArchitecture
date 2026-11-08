#!/usr/bin/env python3
"""
export_and_sync_ableton.py
==========================
Automates exporting audio from Ableton Live 12 and syncs with the web prototype.

Workflow:
  1. Checks if Ableton Live is running (opens the project if not).
  2. Brings Ableton Live to the front.
  3. Sends Ctrl+Shift+R to trigger 'Export Audio/Video'.
  4. Confirms default 28-bar master export settings and sets path to ableton/voices.wav.
  5. Waits for rendering to finish.
  6. Automatically slices all 7 stems and updates jsg_audio_data.js & audio/.
"""

import os
import sys
import time
import ctypes
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = SCRIPT_DIR
ALS_PATH = os.path.join(PROJECT_DIR, "InteractiveMusicArchitecture_SoundLab.als")
TARGET_WAV = os.path.join(PROJECT_DIR, "ableton", "voices.wav")
ABLETON_DIR = os.path.join(PROJECT_DIR, "ableton")

user32 = ctypes.windll.user32

# Virtual key codes
VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_RETURN = 0x0D
VK_V = 0x56
VK_Y = 0x59
KEYEVENTF_KEYUP = 0x0002

def press_key(vk):
    user32.keybd_event(vk, 0, 0, 0)

def release_key(vk):
    user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)

def tap_key(vk, delay=0.06):
    press_key(vk)
    time.sleep(delay)
    release_key(vk)

def hotkey_ctrl_shift_r():
    press_key(VK_CONTROL)
    press_key(VK_SHIFT)
    press_key(0x52)  # 'R'
    time.sleep(0.08)
    release_key(0x52)
    release_key(VK_SHIFT)
    release_key(VK_CONTROL)

def hotkey_ctrl_v():
    press_key(VK_CONTROL)
    press_key(VK_V)
    time.sleep(0.08)
    release_key(VK_V)
    release_key(VK_CONTROL)

def is_ableton_running():
    try:
        out = subprocess.check_output('tasklist /FI "IMAGENAME eq Ableton Live 12 Suite.exe"', shell=True, text=True)
        if "Ableton Live" in out:
            return True
        out = subprocess.check_output('tasklist /FI "IMAGENAME eq Live.exe"', shell=True, text=True)
        return "Live.exe" in out
    except Exception:
        return False

def activate_ableton_window():
    # Use PowerShell WScript.Shell for reliable window activation across desktop sessions
    ps_cmd = "$w = New-Object -ComObject WScript.Shell; $w.AppActivate('SoundLab') -or $w.AppActivate('Ableton Live') -or $w.AppActivate('Live')"
    try:
        res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True)
        return "True" in res.stdout
    except Exception:
        return False

def set_clipboard_text(text):
    escaped = text.replace("'", "''")
    ps_cmd = f"Set-Clipboard -Value '{escaped}'"
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)

def wait_for_file_ready(file_path, prev_mtime, timeout=60):
    start_time = time.time()
    while time.time() - start_time < timeout:
        elapsed = int(time.time() - start_time)
        if os.path.exists(file_path):
            cur_mtime = os.path.getmtime(file_path)
            if cur_mtime > prev_mtime:
                # Test if file is unlocked and written
                try:
                    with open(file_path, "rb") as f:
                        f.seek(0, os.SEEK_END)
                        size = f.tell()
                        if size > 10000:
                            return True
                except (IOError, PermissionError):
                    pass
        print(f"    Rendering audio in Ableton... ({elapsed}s)", end="\r", flush=True)
        time.sleep(1.0)
    print()
    return False

def main():
    print("======================================================================")
    print("  Ableton Live — Auto Export Audio & Sync Web Project")
    print("======================================================================")
    os.makedirs(ABLETON_DIR, exist_ok=True)

    prev_mtime = os.path.getmtime(TARGET_WAV) if os.path.exists(TARGET_WAV) else 0

    if not is_ableton_running():
        print("[!] Ableton Live 12 is not currently running.")
        print(f"[*] Launching SoundLab project: {ALS_PATH}")
        try:
            os.startfile(ALS_PATH)
        except Exception as e:
            print("    Error launching:", e)
        print("    Please wait for Ableton Live to load, edit your sounds, and run this script again.")
        return

    print("[*] Ableton Live 12 is running.")
    print("[*] Bringing Ableton Live to the foreground...")
    activate_ableton_window()
    time.sleep(0.8)

    print("[*] Triggering Export Audio/Video (Ctrl + Shift + R)...")
    hotkey_ctrl_shift_r()
    time.sleep(1.2)

    print("[*] Confirming Export Settings (Master 28 bars)...")
    tap_key(VK_RETURN)
    time.sleep(1.2)

    print(f"[*] Setting destination path: {TARGET_WAV}")
    set_clipboard_text(TARGET_WAV)
    time.sleep(0.3)
    hotkey_ctrl_v()
    time.sleep(0.4)
    tap_key(VK_RETURN)
    time.sleep(0.8)

    # In case Windows Save As shows "Overwrite existing file?", press 'y' and Enter
    tap_key(VK_Y)
    time.sleep(0.3)
    tap_key(VK_RETURN)

    print("[*] Waiting for Ableton to complete rendering...")
    success = wait_for_file_ready(TARGET_WAV, prev_mtime, timeout=45)

    if success:
        file_mb = round(os.path.getsize(TARGET_WAV) / (1024 * 1024), 2)
        print(f"\n[SUCCESS] Ableton exported voices.wav ({file_mb} MB) successfully!")
        print("\n[*] Slicing 7 architectural stems & syncing with web prototype...")
        
        # Import sounds
        importer_script = os.path.join(PROJECT_DIR, "import_ableton_sounds.py")
        subprocess.run([sys.executable, importer_script], check=True)
        
        print("\n======================================================================")
        print(" [OK] ALL SOUNDS EXPORTED AND IMPORTED TO WEB PROJECT SUCCESSFULLY!")
        print(" Refresh your browser (Ctrl + F5) at http://localhost:8080")
        print("======================================================================")
    else:
        print("\n[!] Auto-export timed out or was interrupted.")
        print("    If Ableton's export dialog is open, simply save as:")
        print(f"    {TARGET_WAV}")
        print("    Then run 'import_sounds.bat' to sync.")

if __name__ == "__main__":
    main()
