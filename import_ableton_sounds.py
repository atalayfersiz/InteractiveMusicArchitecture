#!/usr/bin/env python3
"""
import_ableton_sounds.py
========================
Imports sound elements edited in Ableton Live into the Interactive Music Architecture project.

EFFICIENT ONE-FILE WORKFLOW:
1. Open 'InteractiveMusicArchitecture_SoundLab.als' in Ableton Live.
2. Edit / design sounds on the 7 tracks (or adjust synths/presets/samples):
     Track 1 (Bars 1-5):   01_EXT_STAIR       (Exterior Stairs · Deep Electronic Pulse)
     Track 2 (Bars 5-9):   02_EXT_COLUMNS     (Terrace Columns · Warm Synth Arpeggio)
     Track 3 (Bars 9-13):  03_ENTRANCE_GLASS  (Entrance Glass · Lush C-Minor9 Pad)
     Track 4 (Bars 13-17): 04_FOYER_VOID      (Closed Foyer Mass · Deep Architectural Void)
     Track 5 (Bars 17-21): 05_FOYER_FRAMES    (Facade Frames · Plucked Synth Rhythm)
     Track 6 (Bars 21-25): 06_INT_STAIR_DOWN  (Interior Stair · Cascading Analog Scale)
     Track 7 (Bars 25-29): 07_SKYLIGHT_ROOF   (Skylight Roof · High Shimmer Chord)
3. In Ableton Live, choose: File > Export Audio/Video (Ctrl+Shift+R)
     - Rendered Track: Master
     - File Format: WAV (16-bit, 44.1kHz or 48kHz)
     - Save as: 'voices.wav' (inside 'ableton/' or project root).
4. Run this script:
     python import_ableton_sounds.py

The script automatically:
  - Slices the 7 voice stems from the single exported file.
  - Applies micro-crossfade at loop points to guarantee click-free seamless audio.
  - Generates web-ready audio files in 'web_prototype/audio/' and root 'audio/'.
  - Embeds the audio directly into 'jsg_audio_data.js' as Base64 WAV buffers for instant,
    CORS-free playback locally and on GitHub Pages!
"""

import os
import sys
import io
import base64
import json
import numpy as np
import scipy.io.wavfile as wav

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = SCRIPT_DIR
ABLETON_DIR = os.path.join(PROJECT_DIR, "ableton")
WEB_AUDIO_DIR = os.path.join(PROJECT_DIR, "web_prototype", "audio")
ROOT_AUDIO_DIR = os.path.join(PROJECT_DIR, "audio")
WEB_JS_PATH = os.path.join(PROJECT_DIR, "web_prototype", "jsg_audio_data.js")
ROOT_JS_PATH = os.path.join(PROJECT_DIR, "jsg_audio_data.js")

VOICE_KEYS = [
    "EXT_STAIR",
    "EXT_COLUMNS",
    "ENTRANCE_GLASS",
    "FOYER_VOID",
    "FOYER_FRAMES",
    "INT_STAIR_DOWN",
    "SKYLIGHT_ROOF",
]

def find_exported_master_wav():
    candidates = [
        os.path.join(ABLETON_DIR, "voices.wav"),
        os.path.join(PROJECT_DIR, "voices.wav"),
        os.path.join(ABLETON_DIR, "Master.wav"),
        os.path.join(PROJECT_DIR, "Master.wav"),
        os.path.join(ABLETON_DIR, "export.wav"),
        os.path.join(PROJECT_DIR, "export.wav"),
    ]
    for c in candidates:
        if os.path.exists(c) and os.path.getsize(c) > 1000:
            return c
    return None

def find_individual_stems():
    stems = {}
    search_dirs = [ABLETON_DIR, PROJECT_DIR, os.path.join(ABLETON_DIR, "stems")]
    for d in search_dirs:
        if not os.path.exists(d):
            continue
        for f in os.listdir(d):
            f_lower = f.lower()
            if not f_lower.endswith(".wav"):
                continue
            for vk in VOICE_KEYS:
                if vk.lower() in f_lower:
                    stems[vk] = os.path.join(d, f)
    return stems if len(stems) == len(VOICE_KEYS) else None

def apply_loop_crossfade(samples, crossfade_len=512):
    """Applies a smooth micro-crossfade between the start and end of the audio loop to prevent clicking."""
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
    buf = io.BytesIO()
    wav.write(buf, sample_rate, samples_int16)
    b64 = base64.b64encode(buf.getvalue()).decode('ascii')
    return f"data:audio/wav;base64,{b64}"

def main():
    print("=" * 70)
    print(" Interactive Music Architecture — Ableton Sound Importer")
    print("=" * 70)

    os.makedirs(WEB_AUDIO_DIR, exist_ok=True)
    os.makedirs(ROOT_AUDIO_DIR, exist_ok=True)

    # 1. Check for single master file first (recommended one-file workflow)
    master_path = find_exported_master_wav()
    stems_dict = {}

    if master_path:
        print(f"[*] Found single master Ableton export: {master_path}")
        sr, master_data = wav.read(master_path)
        print(f"    Sample Rate: {sr} Hz, Channels: {1 if master_data.ndim == 1 else master_data.shape[1]}, Total Samples: {len(master_data)}")

        # Convert to float32 normalized [-1.0, 1.0]
        if master_data.dtype == np.int16:
            audio_f = master_data.astype(np.float32) / 32768.0
        elif master_data.dtype == np.int32:
            audio_f = master_data.astype(np.float32) / 2147483648.0
        elif master_data.dtype == np.float32 or master_data.dtype == np.float64:
            audio_f = master_data.astype(np.float32)
        else:
            audio_f = master_data.astype(np.float32) / np.max(np.abs(master_data))

        # 7 equal sections (16 beats / 4 bars each in the 28-bar timeline)
        n_elements = len(VOICE_KEYS)
        samples_per_elem = len(audio_f) // n_elements

        for idx, vk in enumerate(VOICE_KEYS):
            s_start = idx * samples_per_elem
            s_end = (idx + 1) * samples_per_elem if idx < n_elements - 1 else len(audio_f)
            slice_data = audio_f[s_start:s_end]
            cf_data = apply_loop_crossfade(slice_data, crossfade_len=int(sr * 0.015))
            stems_dict[vk] = (sr, cf_data)
            print(f"  -> Extracted Voice {idx+1}/7 [{vk:15s}]: {len(cf_data)/sr:.2f}s")

    else:
        # Fallback to individual stem files
        indiv_stems = find_individual_stems()
        if indiv_stems:
            print("[*] Found individual exported stem files:")
            for vk in VOICE_KEYS:
                path = indiv_stems[vk]
                sr, stem_data = wav.read(path)
                if stem_data.dtype == np.int16:
                    audio_f = stem_data.astype(np.float32) / 32768.0
                else:
                    audio_f = stem_data.astype(np.float32)
                cf_data = apply_loop_crossfade(audio_f, crossfade_len=int(sr * 0.015))
                stems_dict[vk] = (sr, cf_data)
                print(f"  -> Loaded [{vk:15s}] from {os.path.basename(path)}")
        else:
            print("[!] Error: No exported Ableton audio file found.")
            print("    Please export 'voices.wav' from Ableton Live into the 'ableton/' directory.")
            return

    # 2. Save individual clean WAV files and compile Base64 stems
    b64_stems = {}
    audio_manifest = {
        "sourceFile": master_path or "Individual Stems",
        "bpm": 116.0,
        "voices": {},
        "hasAudioStems": True,
        "audioStemsBase64": {}
    }

    for vk, (sr, f_samples) in stems_dict.items():
        # Normalize and convert to int16 for web efficiency
        peak = np.max(np.abs(f_samples))
        if peak > 0.0001:
            norm_samples = f_samples * (0.95 / peak)
        else:
            norm_samples = f_samples
        int16_samples = (norm_samples * 32767).astype(np.int16)

        # Write to web_prototype/audio and root audio
        out_wav_name = f"{vk.lower()}.wav"
        for dest_dir in [WEB_AUDIO_DIR, ROOT_AUDIO_DIR]:
            wav.write(os.path.join(dest_dir, out_wav_name), sr, int16_samples)

        # Encode to Base64
        data_url = wav_to_base64_data_url(sr, int16_samples)
        b64_stems[vk] = data_url
        audio_manifest["voices"][vk] = {
            "key": vk,
            "filename": out_wav_name,
            "sampleRate": sr,
            "duration": round(len(int16_samples) / sr, 3)
        }

    audio_manifest["audioStemsBase64"] = b64_stems

    # 3. Write jsg_audio_data.js
    js_content = "// Auto-generated Ableton audio data for James-Simon-Galerie\n"
    js_content += "window.JSG_AUDIO_DATA = " + json.dumps(audio_manifest, separators=(",", ":")) + ";\n"

    with open(WEB_JS_PATH, "w", encoding="utf-8") as f:
        f.write(js_content)
    with open(ROOT_JS_PATH, "w", encoding="utf-8") as f:
        f.write(js_content)

    print(f"\n[OK] Successfully imported all 7 Ableton voices!")
    print(f"     -> Stems written to: {WEB_AUDIO_DIR}")
    print(f"     -> Audio JS bundle updated: {WEB_JS_PATH}")
    print(f"     -> Instant web playback ready!")

if __name__ == "__main__":
    main()
