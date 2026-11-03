# Interactive Music Architecture — Project Hub

Welcome to the **Interactive Music Architecture** digital prototype workspace, inspired by DAO's *Wake · 森* audiovisual sequencer.

---

## Workspace Structure

```
d:\CODING\InteractiveMusicArchitecture\
├── web_prototype\
│   └── index.html               <-- Fully playable, zero-install 3D point cloud sequencer
├── rhino_assets\
│   └── generate_test_track.py   <-- Rhino Python script generating the 3-Zone geometry
├── osc_server\
│   └── osc_bridge.py            <-- Python OSC UDP relay for Ableton / Max / REAPER
└── ue5_specs\
    └── UE5_SEQUENCER_SPEC.md    <-- Native Unreal Engine 5.8 Blueprint & Niagara specification
```

---

## 1. Quick Test (Interactive Web Prototype)
You can test the entire experience immediately in your browser:
* Double click `d:\CODING\InteractiveMusicArchitecture\web_prototype\index.html` to open it in Chrome / Edge.
* Click to capture mouse pointer lock.
* Use **WASD** to walk through the Void, Colonnade, and Niche.
* Aim the reticle at any floor, column, ceiling, or niche wall and **Left Click** to capture its sound into the continuous **16-step sequencer**.
* Watch the beat loop continuously and build your architectural track!

---

## 2. Rhino 3D Modeling Asset
* Located in `rhino_assets\generate_test_track.py`.
* Sets units to Centimeters (1 unit = 1 cm).
* Generates all 3 architectural zones with exact Datasmith naming conventions (`SM_Macro_*`, `SM_Meso_*`, `SM_Micro_*`).

---

## 3. UE5.8 & OSC Production Setup
* When ready to bring it into your native Unreal Engine 5.8 project, refer to `ue5_specs\UE5_SEQUENCER_SPEC.md` for Niagara particle reproduction and Blueprint OSC nodes.
