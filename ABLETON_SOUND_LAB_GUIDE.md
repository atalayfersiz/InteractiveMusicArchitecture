# Ableton Live Sound Lab — Interactive Music Architecture

This guide explains the **single-file workflow** to customize, edit, and import sounds for all 7 architectural elements in the James-Simon-Galerie project.

---

## 1. The Master Ableton File (All Elements in One File)

Open this file in **Ableton Live 12**:
- **File location:** [`D:\CODING\InteractiveMusicArchitecture\InteractiveMusicArchitecture_SoundLab.als`](file:///D:/CODING/InteractiveMusicArchitecture/InteractiveMusicArchitecture_SoundLab.als)
  *(Also mirrored at `D:\CODING\Thesis\InteractiveMusicArchitecture_SoundLab.als` and `ableton/InteractiveMusicArchitecture_SoundLab.als`)*

Inside this single Ableton Live Set, all 7 architectural voices are set up on dedicated, color-coded tracks:

| # | Track Name | Architectural Element | Default Instrument / Character | Arrangement Bar | Time Offset |
|---|---|---|---|---|---|
| **1** | `01_EXT_STAIR` | Exterior Grand Stairs | Deep electronic sub pulse & rhythmic transients | Bars 1–5 | `0.0s – 8.28s` |
| **2** | `02_EXT_COLUMNS` | West Colonnade | Warm analog synth arpeggio in C-Minor | Bars 5–9 | `8.28s – 16.55s` |
| **3** | `03_ENTRANCE_GLASS` | South Upper Entrance Glass | Lush C-Minor9 ambient chord & shimmering harmonics | Bars 9–13 | `16.55s – 24.83s` |
| **4** | `04_FOYER_VOID` | Closed Foyer Mass | Deep spatial void drone & architectural resonance | Bars 13–17 | `24.83s – 33.10s` |
| **5** | `05_FOYER_FRAMES` | Facade Mullions & Transoms | Acoustic / metallic plucked transients, syncopated rhythm | Bars 17–21 | `33.10s – 41.38s` |
| **6** | `06_INT_STAIR_DOWN` | Interior Monumental Stair | Cascading descending melodic analog scale | Bars 21–25 | `41.38s – 49.66s` |
| **7** | `07_SKYLIGHT_ROOF` | Overhead Skylight & Fins | High crystalline shimmer, ambient air and light | Bars 25–29 | `49.66s – 57.93s` |

---

## 2. Two Ways to Work Inside Ableton

### A. Arrangement View (For Exporting)
In **Arrangement View** (press `Tab`), all 7 elements are laid out sequentially across **28 bars** (4 bars per element at 116 BPM).
- There is a named locator/marker at the beginning of each element.
- Because each track plays in its own 4-bar window, there is **zero bleed** between elements on the Master output.

### B. Session View (For Jamming / Auditioning)
In **Session View**, each track has a 4-bar loop in Clip Slot 1.
- You can trigger the Scene play button to listen to all 7 sounds playing together as a cohesive musical piece.

---

## 3. How to Edit the Sounds
1. Click any track (e.g., `01_EXT_STAIR`).
2. Tweak the instruments, synths (Wavetable, Drift, Operator, Analog), presets, VSTs, samplers, EQ, filters, or effects to your exact liking.
3. You can replace the MIDI patterns or drop in your own audio recordings and drum samples!

---

## 4. The Efficient "One-File" Export Workflow

When you are happy with your sounds:

1. In Ableton Live, press **`Ctrl + Shift + R`** (or go to `File > Export Audio/Video`).
2. Set:
   - **Rendered Track:** `Master`
   - **Start:** `1.1.1`
   - **Length:** `28.0.0` (Bars 1 to 29)
   - **File Type:** `WAV` (16-bit, 44.1 kHz)
3. Save the exported file as:
   **`voices.wav`** inside the [`ableton/`](file:///D:/CODING/InteractiveMusicArchitecture/ableton/) folder:
   `D:\CODING\InteractiveMusicArchitecture\ableton\voices.wav`

> **Note:** That's it! You only export **one single file**. You do **not** have to solo tracks or export 7 separate stems.

---

## 5. One-Click Import to the Project

To import your updated sounds into the web project:

- **Option A (Double-Click):**
  Double-click [`import_sounds.bat`](file:///D:/CODING/InteractiveMusicArchitecture/import_sounds.bat) in the project folder.

- **Option B (Command Line):**
  Run:
  ```powershell
  python D:\CODING\InteractiveMusicArchitecture\import_ableton_sounds.py
  ```

### What Happens Automatically:
1. Slices the 7 voice stems from your single `voices.wav` at the exact locator timestamps.
2. Applies smooth micro-crossfades to guarantee click-free seamless audio looping.
3. Saves individual stems to [`web_prototype/audio/`](file:///D:/CODING/InteractiveMusicArchitecture/web_prototype/audio/).
4. Encodes them into [`jsg_audio_data.js`](file:///D:/CODING/InteractiveMusicArchitecture/web_prototype/jsg_audio_data.js) for instant, CORS-free playback locally and on GitHub Pages.
5. Reload your browser (`Ctrl + F5`) at `http://localhost:8080/index.html` to hear your custom sounds live in the 3D space!
