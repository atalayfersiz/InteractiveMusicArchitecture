"""
Headless LMMS Audio Exporter & Web Project Sync Tool.

1. Locates LMMS (D:\\Program Files\\LMMS\\lmms.exe, etc.).
2. Renders InteractiveMusicArchitecture_SoundLab.mmp headlessly via `lmms.exe render`
   into ableton/voices.wav (44.1 kHz WAV).
3. Verifies voices.wav is > 1 MB and non-silent.
4. Runs import_ableton_sounds.py to slice all 7 architectural stems with 15 ms
   micro-crossfades and rebuild web_prototype/audio/*.wav + jsg_audio_data.js.
"""

import os
import shutil
import subprocess
import sys

import numpy as np
from scipy.io import wavfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = (
    SCRIPT_DIR
    if os.path.exists(os.path.join(SCRIPT_DIR, "import_ableton_sounds.py"))
    else r"D:\CODING\InteractiveMusicArchitecture"
)

PROJECT_FILENAME = "InteractiveMusicArchitecture_SoundLab.mmp"
MMP_PATH = os.path.join(REPO_DIR, PROJECT_FILENAME)
LOCAL_MMP_PATH = os.path.join(SCRIPT_DIR, PROJECT_FILENAME)
VOICES_WAV = os.path.join(REPO_DIR, "ableton", "voices.wav")
IMPORT_SCRIPT = os.path.join(REPO_DIR, "import_ableton_sounds.py")

LMMS_CANDIDATES = [
    r"D:\Program Files\LMMS\lmms.exe",
    r"D:\LMMS\lmms.exe",
    r"C:\Program Files\LMMS\lmms.exe",
]


def find_lmms():
    for candidate in LMMS_CANDIDATES:
        if os.path.isfile(candidate):
            return candidate
    found = shutil.which("lmms")
    return found


def sync_newer_mmp():
    """If launched from D:\\CODING\\Thesis and that .mmp is newer, sync it to repo."""
    if os.path.abspath(LOCAL_MMP_PATH) != os.path.abspath(MMP_PATH) and os.path.isfile(LOCAL_MMP_PATH):
        if not os.path.isfile(MMP_PATH) or os.path.getmtime(LOCAL_MMP_PATH) > os.path.getmtime(MMP_PATH):
            shutil.copy2(LOCAL_MMP_PATH, MMP_PATH)
            print(f"[INFO] Synced edited project: {LOCAL_MMP_PATH} -> {MMP_PATH}")


def verify_rendered_wav(wav_path):
    """Confirm rendered WAV exists, exceeds 1 MB, and contains non-zero audio."""
    if not os.path.isfile(wav_path):
        raise RuntimeError(f"Rendered WAV not found: {wav_path}")

    size_bytes = os.path.getsize(wav_path)
    if size_bytes <= 1_000_000:
        raise RuntimeError(f"Rendered WAV too small ({size_bytes} bytes <= 1 MB): {wav_path}")

    sr, data = wavfile.read(wav_path)
    if data.dtype == np.int16:
        norm = data.astype(np.float32) / 32768.0
    elif data.dtype == np.int32:
        norm = data.astype(np.float32) / 2147483648.0
    else:
        norm = data.astype(np.float32)

    peak = float(np.max(np.abs(norm)))
    rms = float(np.sqrt(np.mean(norm ** 2)))
    duration_sec = len(norm) / float(sr)

    print(
        f"[OK] Verified {os.path.basename(wav_path)}: "
        f"{size_bytes / (1024 * 1024):.2f} MB | {duration_sec:.2f}s @ {sr} Hz | "
        f"peak={peak:.4f} rms={rms:.4f}"
    )
    if peak < 1e-4 or rms < 1e-5:
        raise RuntimeError(f"Rendered WAV appears silent (peak={peak}, rms={rms})")


def main():
    print("=" * 70)
    print("  LMMS Headless Audio Exporter & Web Project Sync")
    print("=" * 70)

    lmms_exe = find_lmms()
    if not lmms_exe:
        print("[ERROR] LMMS executable not found in D:\\Program Files\\LMMS\\lmms.exe or D:\\LMMS\\lmms.exe.")
        sys.exit(1)

    sync_newer_mmp()
    if not os.path.isfile(MMP_PATH):
        print(f"[ERROR] LMMS project file missing: {MMP_PATH}")
        sys.exit(1)

    os.makedirs(os.path.dirname(VOICES_WAV), exist_ok=True)
    print(f"[1/3] LMMS binary : {lmms_exe}")
    print(f"[1/3] Project file: {MMP_PATH}")
    print(f"[1/3] Rendering 28-bar master WAV -> {VOICES_WAV}")

    cmd = [lmms_exe, "render", MMP_PATH, "-o", VOICES_WAV, "-f", "wav", "-s", "44100"]
    res = subprocess.run(cmd, check=False)
    if res.returncode != 0:
        print(f"[ERROR] LMMS render failed with exit code {res.returncode}")
        sys.exit(res.returncode)

    print("[2/3] Verifying rendered WAV integrity & non-zero audio...")
    verify_rendered_wav(VOICES_WAV)

    print("[3/3] Slicing 7 architectural stems & updating web_prototype/audio + jsg_audio_data.js...")
    sync_res = subprocess.run([sys.executable, IMPORT_SCRIPT], cwd=REPO_DIR, check=False)
    if sync_res.returncode != 0:
        print(f"[ERROR] Stem import failed with exit code {sync_res.returncode}")
        sys.exit(sync_res.returncode)

    print("=" * 70)
    print("[DONE] LMMS export & web audio sync complete!")
    print("       Reload index.html / GitHub Pages to hear your updated sounds.")
    print("=" * 70)


if __name__ == "__main__":
    main()
