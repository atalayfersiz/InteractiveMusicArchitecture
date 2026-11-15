# Interactive Music Architecture — Project Hub

Digital prototype workspace for the **Interactive Music Architecture (James-Simon-Galerie)** audiovisual sequencer.

---

## Workspace Structure

```
d:\CODING\InteractiveMusicArchitecture\
├── open_lmms_soundlab.bat              <-- [1] Launch LMMS with all 7 architectural tracks
├── export_audio_from_lmms.bat          <-- [2] Headless LMMS render -> stem slice -> web sync
├── lmms\
│   ├── InteractiveMusicArchitecture_SoundLab.mmp   <-- Single-file 7-track LMMS project
│   ├── export_and_sync_lmms.py                     <-- CLI render + beat-accurate stem slicer
│   ├── build_lmms_project.py                       <-- Generator / reset script for .mmp
│   └── voices.wav                                  <-- Rendered 28-bar master WAV (44.1 kHz)
├── web_prototype\
│   ├── index.html                      <-- Playable 3D architectural sequencer
│   ├── audio\                          <-- Sliced 7 architectural stem loops (*.wav)
│   ├── jsg_audio_data.js               <-- Base64 WAV stems embedded for zero-CORS playback
│   └── jsg_model_data.js               <-- Exported architectural geometry
├── rhino_assets\
│   ├── InteractiveMusicArchitecture_Master.3dm
│   └── sync_rhino_to_web.py            <-- Syncs Rhino 3D geometry to web_prototype
├── osc_server\
│   └── osc_bridge.py                   <-- Python OSC UDP bridge
└── ue5_specs\
    └── UE5_SEQUENCER_SPEC.md           <-- Native Unreal Engine 5.8 Blueprint & Niagara spec
```

---

## Sound Editing Workflow (LMMS)
1. Double-click **`open_lmms_soundlab.bat`** to open `lmms\InteractiveMusicArchitecture_SoundLab.mmp` in LMMS.
2. Edit any synth patch, effects, or MIDI notes across the 7 tracks (`01_EXT_STAIR` through `07_SKYLIGHT_ROOF`), then save (`Ctrl+S`).
3. Double-click **`export_audio_from_lmms.bat`** to headlessly render `lmms\voices.wav`, slice all 7 loops at exact 16-beat boundaries (`116 BPM`), and update `web_prototype\audio\` and `jsg_audio_data.js`.
4. Reload `web_prototype\index.html` (or push for GitHub Pages) to hear your new sounds immediately.
