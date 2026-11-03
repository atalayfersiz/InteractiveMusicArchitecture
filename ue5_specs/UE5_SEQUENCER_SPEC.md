# UE5.8 Architectural Sequencer Implementation Specification
# Project: Interactive Music Architecture (Wake · Arch)

This document contains the exact Blueprint logic, OSC parameters, and Niagara particle settings to replicate the prototype natively in Unreal Engine 5.8.

---

## 1. Unreal Engine 5 Setup & Plugins
1. Open UE5.8 (`D:\Program Files\Epic Games\UE_5.8`).
2. Go to `Edit > Plugins` and enable:
   * **OSC** (Open Sound Control built-in plugin)
   * **Niagara** (Default enabled)
   * **Datasmith CAD / Rhino Importer**

---

## 2. Niagara Point-Cloud Architecture Look (Dark Luminous Look)
To mimic the point-cloud look from the video without heavy LiDAR processing:
1. In the Content Browser, right-click -> `FX > Niagara System` -> New system from selected emitter template (`Mesh Surface Reproduction`).
2. Set the Emitter:
   * **Mesh Sampling Module:** Select your imported `SM_Macro_*` or `SM_Meso_*` static meshes.
   * **Particle Spawn Rate:** 20,000 particles per volume.
   * **Sprite Material:** Default `M_Particle` or an unlit circle with an Emissive Multiplier of `5.0`.
   * **Color:**
     * Macro Floor/Walls: Steel Blue `(R=0.0, G=0.7, B=1.0)`
     * Meso Colonnade: Emerald Green `(R=0.02, G=0.85, B=0.62)`
     * Micro Niche: Vibrant Carmine / Magenta `(R=0.93, G=0.27, B=0.43)`

---

## 3. First-Person Raycast & Touch Mechanics (`BP_PlayerCharacter`)
In the First Person Character Event Graph:

### On Input Action "PrimaryAction" (Left Mouse Click):
1. **Get Player Camera Manager** -> `Get Camera Location` -> Start.
2. `Get Camera Rotation` -> `Get Forward Vector` -> `Multiply by 2500.0` -> `Add to Camera Location` -> End.
3. Call **Line Trace By Channel** (Trace Channel: `Visibility`).
4. On Hit:
   * **Spawn Emitter at Location** (or Spawn Niagara System at `Hit Impact Point`) -> Spawns an expanding particle ring.
   * Get `Hit Actor` -> `Get Actor Label` (or `Get Component Tags`).
   * Branch based on string prefix:
     * Contains `"Floor"` -> Voice = `KICK` (OSC `/voice/kick`)
     * Contains `"Column"` -> Voice = `SNARE` (OSC `/voice/snare`)
     * Contains `"Ceiling"` -> Voice = `HIHAT` (OSC `/voice/hihat`)
     * Contains `"Niche"` -> Voice = `LEAD` (OSC `/voice/lead`)
   * Call `BP_SequencerSubsystem -> RegisterHit(Voice)`.

---

## 4. 16-Step Looping Sequencer (`BP_SequencerManager`)
Create an Actor Blueprint `BP_SequencerManager` placed in the level:

### Variables:
* `BPM` (Float, Default: `124.0`)
* `CurrentStep` (Integer, 0 to 15)
* `LoopBuffer` (Map or Array of 16 Structs, each holding boolean flags for `Kick`, `Snare`, `Hat`, `Lead`)
* `OSCClient` (OSCClient Object)

### Logic:
1. **Event BeginPlay:**
   * Create OSC Client: Target IP `127.0.0.1`, Target Port `8000`.
   * Compute Step Time: `StepTime = (60.0 / BPM) / 4.0` (approx `0.12s`).
   * Call `Set Timer by Function Name` (Looping = `True`, Time = `StepTime`, Function = `TickStep`).

2. **Function `TickStep`:**
   * `CurrentStep = (CurrentStep + 1) % 16`.
   * Read `LoopBuffer[CurrentStep]`:
     * If `Kick == True` -> Play MetaSound Kick & Send OSC `/seq/trigger` with args `["KICK", CurrentStep]`.
     * If `Snare == True` -> Play MetaSound Snare & Send OSC `/seq/trigger` with args `["SNARE", CurrentStep]`.
     * If `Hat == True` -> Play MetaSound Hat & Send OSC `/seq/trigger` with args `["HIHAT", CurrentStep]`.
     * If `Lead == True` -> Play MetaSound Tone & Send OSC `/seq/trigger` with args `["LEAD", CurrentStep]`.

3. **Function `RegisterHit(Voice)`:**
   * `TargetStep = CurrentStep` (quantized).
   * Set `LoopBuffer[TargetStep][Voice] = True`.

---

## 5. Summary of OSC Namespace
* `/seq/step` `[int step_index]` — Broadcasts clock pulse.
* `/seq/trigger` `[string voice_name, int step_index]` — Broadcasts active drum/melody trigger.
* `/seq/clear` `[]` — Clears the loop buffer.
