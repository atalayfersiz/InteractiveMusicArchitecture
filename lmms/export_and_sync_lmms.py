"""
LMMS Headless Audio Exporter, Stem Slicer & Web Project Sync Tool.

Single self-contained pipeline inside lmms/:
1. Locates LMMS binary on D: or C: drive.
2. Syncs lmms/InteractiveMusicArchitecture_SoundLab.mmp if edited in Thesis workspace.
3. Renders lmms/InteractiveMusicArchitecture_SoundLab.mmp headlessly via `lmms.exe render`
   into lmms/voices.wav (44.1 kHz WAV).
4. Verifies voices.wav is > 1 MB and non-silent.
5. Slices the 7 architectural stems strictly by 16-beat duration @ 116 BPM with
   15 ms micro-crossfades, writes web_prototype/audio/*.wav and audio/*.wav, and
   rebuilds web_prototype/jsg_audio_data.js and jsg_audio_data.js.
"""

import base64
import io
import json
import os
import shutil
import subprocess
import sys

import numpy as np
from scipy.io import wavfile

SCRIPT_LMMS_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(SCRIPT_LMMS_DIR)
REPO_DIR = (
    PARENT_DIR
    if os.path.isdir(os.path.join(PARENT_DIR, "web_prototype"))
    else r"D:\CODING\InteractiveMusicArchitecture"
)

PROJECT_FILENAME = "InteractiveMusicArchitecture_SoundLab.mmp"
REPO_LMMS_DIR = os.path.join(REPO_DIR, "lmms")
MMP_PATH = os.path.join(REPO_LMMS_DIR, PROJECT_FILENAME)
LOCAL_MMP_PATH = os.path.join(SCRIPT_LMMS_DIR, PROJECT_FILENAME)
VOICES_WAV = os.path.join(REPO_LMMS_DIR, "voices.wav")

WEB_AUDIO_DIR = os.path.join(REPO_DIR, "web_prototype", "audio")
ROOT_AUDIO_DIR = os.path.join(REPO_DIR, "audio")
WEB_JS_PATH = os.path.join(REPO_DIR, "web_prototype", "jsg_audio_data.js")
ROOT_JS_PATH = os.path.join(REPO_DIR, "jsg_audio_data.js")

BPM = 116.0
BEATS_PER_ELEMENT = 16.0
VOICE_KEYS = [
    "EXT_STAIR",
    "EXT_COLUMNS",
    "ENTRANCE_GLASS",
    "FOYER_VOID",
    "FOYER_FRAMES",
    "INT_STAIR_DOWN",
    "SKYLIGHT_ROOF",
]

LMMS_CANDIDATES = [
    r"D:\Program Files\LMMS\lmms.exe",
    r"D:\LMMS\lmms.exe",
    r"C:\Program Files\LMMS\lmms.exe",
]


def find_lmms():
    """Return path to installed lmms.exe binary, or None if missing."""
    for candidate in LMMS_CANDIDATES:
        if os.path.isfile(candidate):
            return candidate
    return shutil.which("lmms")


def sync_newer_mmp():
    """Keep the repo .mmp up to date if edited inside D:\\CODING\\Thesis\\lmms."""
    if os.path.abspath(LOCAL_MMP_PATH) != os.path.abspath(MMP_PATH) and os.path.isfile(LOCAL_MMP_PATH):
        if not os.path.isfile(MMP_PATH) or os.path.getmtime(LOCAL_MMP_PATH) > os.path.getmtime(MMP_PATH):
            os.makedirs(REPO_LMMS_DIR, exist_ok=True)
            shutil.copy2(LOCAL_MMP_PATH, MMP_PATH)
            print(f"[INFO] Synced edited project: {LOCAL_MMP_PATH} -> {MMP_PATH}")


def normalize_float_audio(data):
    """Convert WAV sample array to float32 normalized in [-1.0, 1.0]."""
    if data.dtype == np.int16:
        return data.astype(np.float32) / 32768.0
    if data.dtype == np.int32:
        return data.astype(np.float32) / 2147483648.0
    if data.dtype in (np.float32, np.float64):
        return data.astype(np.float32)
    peak = np.max(np.abs(data))
    return data.astype(np.float32) / (peak if peak > 0 else 1.0)


def verify_rendered_wav(wav_path):
    """Confirm rendered WAV exists, exceeds 1 MB, and contains non-zero audio."""
    if not os.path.isfile(wav_path):
        raise RuntimeError(f"Rendered WAV not found: {wav_path}")

    size_bytes = os.path.getsize(wav_path)
    if size_bytes <= 1_000_000:
        raise RuntimeError(f"Rendered WAV too small ({size_bytes} bytes <= 1 MB): {wav_path}")

    sr, data = wavfile.read(wav_path)
    norm = normalize_float_audio(data)
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
    return sr, norm


def apply_loop_crossfade(samples, crossfade_len):
    """Apply a smooth linear crossfade at the loop seam to prevent clicks."""
    if len(samples) <= crossfade_len * 2:
        return samples
    out = samples.copy()
    fade_in = np.linspace(0.0, 1.0, crossfade_len, dtype=np.float32)
    fade_out = np.linspace(1.0, 0.0, crossfade_len, dtype=np.float32)
    if out.ndim == 2:
        fade_in = fade_in[:, np.newaxis]
        fade_out = fade_out[:, np.newaxis]
    tail = out[-crossfade_len:].copy()
    head = out[:crossfade_len].copy()
    out[:crossfade_len] = head * fade_in + tail * fade_out
    return out[:-crossfade_len]


def wav_to_base64_data_url(sample_rate, samples_int16):
    """Encode 16-bit PCM WAV samples as a data URL for zero-CORS web playback."""
    buf = io.BytesIO()
    wavfile.write(buf, sample_rate, samples_int16)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:audio/wav;base64,{b64}"


def slice_and_publish_stems(sr, audio_f, source_wav):
    """Slice 7 sequential 16-beat stems and update audio/ + jsg_audio_data.js."""
    os.makedirs(WEB_AUDIO_DIR, exist_ok=True)
    os.makedirs(ROOT_AUDIO_DIR, exist_ok=True)

    samples_per_elem = int(round(BEATS_PER_ELEMENT * (60.0 / BPM) * sr))
    crossfade_samples = int(sr * 0.015)

    audio_manifest = {
        "sourceFile": source_wav,
        "bpm": BPM,
        "voices": {},
        "hasAudioStems": True,
        "audioStemsBase64": {},
    }

    for idx, vk in enumerate(VOICE_KEYS):
        s_start = idx * samples_per_elem
        s_end = min(len(audio_f), (idx + 1) * samples_per_elem)
        cf_data = apply_loop_crossfade(audio_f[s_start:s_end], crossfade_samples)

        peak = float(np.max(np.abs(cf_data)))
        norm_samples = cf_data * (0.95 / peak) if peak > 0.0001 else cf_data
        int16_samples = (norm_samples * 32767).astype(np.int16)

        out_wav_name = f"{vk.lower()}.wav"
        for dest_dir in (WEB_AUDIO_DIR, ROOT_AUDIO_DIR):
            wavfile.write(os.path.join(dest_dir, out_wav_name), sr, int16_samples)

        audio_manifest["audioStemsBase64"][vk] = wav_to_base64_data_url(sr, int16_samples)
        audio_manifest["voices"][vk] = {
            "key": vk,
            "filename": out_wav_name,
            "sampleRate": sr,
            "duration": round(len(int16_samples) / sr, 3),
        }
        print(f"  -> Sliced Voice {idx+1}/7 [{vk:15s}]: {len(int16_samples)/sr:.3f}s")

    js_content = (
        "// Auto-generated LMMS audio data for James-Simon-Galerie\n"
        + "window.JSG_AUDIO_DATA = "
        + json.dumps(audio_manifest, separators=(",", ":"))
        + ";\n"
    )
    for js_path in (WEB_JS_PATH, ROOT_JS_PATH):
        with open(js_path, "w", encoding="utf-8") as f:
            f.write(js_content)


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

    res = subprocess.run(
        [lmms_exe, "render", MMP_PATH, "-o", VOICES_WAV, "-f", "wav", "-s", "44100"],
        check=False,
    )
    if res.returncode != 0:
        print(f"[ERROR] LMMS render failed with exit code {res.returncode}")
        sys.exit(res.returncode)

    print("[2/3] Verifying rendered WAV integrity & non-zero audio...")
    sr, audio_f = verify_rendered_wav(VOICES_WAV)

    print("[3/3] Slicing 7 architectural stems & updating web_prototype/audio + jsg_audio_data.js...")
    slice_and_publish_stems(sr, audio_f, VOICES_WAV)

    print("=" * 70)
    print("[DONE] LMMS export & web audio sync complete!")
    print("       Reload index.html / GitHub Pages to hear your updated sounds.")
    print("=" * 70)


if __name__ == "__main__":
    main()
