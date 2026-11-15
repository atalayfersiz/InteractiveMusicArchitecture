"""
Build single-file LMMS project (InteractiveMusicArchitecture_SoundLab.mmp)
containing all 7 architectural sound voices for the James-Simon-Galerie.

Reads exact MIDI clip timing and notes from
ableton_project/InteractiveMusicArchitecture_SoundLab.als (Arrangement clips)
so all 7 tracks sit sequentially on bars 1-28 (16 beats = 4 bars each @ 116 BPM)
for headless CLI rendering and beat-accurate stem slicing.
"""

import gzip
import os
import shutil
import xml.etree.ElementTree as ET

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
ALS_PATH = os.path.join(ROOT_DIR, "ableton_project", "InteractiveMusicArchitecture_SoundLab.als")
MMP_PATH = os.path.join(ROOT_DIR, "InteractiveMusicArchitecture_SoundLab.mmp")
THESIS_MMP_PATH = os.path.join(r"D:\CODING\Thesis", "InteractiveMusicArchitecture_SoundLab.mmp")

BPM = 116
TICKS_PER_BEAT = 48
BEATS_PER_ELEMENT = 16
TICKS_PER_ELEMENT = BEATS_PER_ELEMENT * TICKS_PER_BEAT  # 768 ticks (4 bars)

# Distinct tripleoscillator + filter + ADSR voices per architectural element
VOICE_PATCHES = {
    "01_EXT_STAIR": {
        "vol": 85,
        "osc": {
            "wavetype0": 2, "vol0": 45, "coarse0": 0, "finel0": -6, "finer0": 6, "stphdetun0": 15,
            "wavetype1": 0, "vol1": 50, "coarse1": -12, "finel1": 0, "finer1": 0, "stphdetun1": 0,
            "wavetype2": 1, "vol2": 30, "coarse2": 0, "finel2": 8, "finer2": -8, "stphdetun2": 25,
        },
        "fcut": 1500, "fres": 0.35, "ftype": 0, "fwet": 1,
        "env": {"att": 0.012, "hold": 0.0, "dec": 0.35, "sustain": 0.45, "rel": 0.16},
    },
    "02_EXT_COLUMNS": {
        "vol": 82,
        "osc": {
            "wavetype0": 1, "vol0": 55, "coarse0": 0, "finel0": -5, "finer0": 5, "stphdetun0": 20,
            "wavetype1": 3, "vol1": 28, "coarse1": 12, "finel1": 6, "finer1": -6, "stphdetun1": 40,
            "wavetype2": 0, "vol2": 35, "coarse2": 0, "finel2": 0, "finer2": 0, "stphdetun2": 0,
        },
        "fcut": 2800, "fres": 0.30, "ftype": 0, "fwet": 1,
        "env": {"att": 0.005, "hold": 0.0, "dec": 0.22, "sustain": 0.08, "rel": 0.12},
    },
    "03_ENTRANCE_GLASS": {
        "vol": 65,
        "osc": {
            "wavetype0": 0, "vol0": 45, "coarse0": 0, "finel0": -10, "finer0": 10, "stphdetun0": 60,
            "wavetype1": 1, "vol1": 38, "coarse1": 12, "finel1": 9, "finer1": -9, "stphdetun1": 90,
            "wavetype2": 0, "vol2": 25, "coarse2": 19, "finel2": -4, "finer2": 4, "stphdetun2": 45,
        },
        "fcut": 4400, "fres": 0.25, "ftype": 0, "fwet": 1,
        "env": {"att": 0.40, "hold": 0.0, "dec": 0.60, "sustain": 0.80, "rel": 0.30},
    },
    "04_FOYER_VOID": {
        "vol": 62,
        "osc": {
            "wavetype0": 4, "vol0": 40, "coarse0": 0, "finel0": -12, "finer0": 12, "stphdetun0": 80,
            "wavetype1": 0, "vol1": 50, "coarse1": -12, "finel1": 4, "finer1": -4, "stphdetun1": 30,
            "wavetype2": 1, "vol2": 35, "coarse2": 0, "finel2": 7, "finer2": -7, "stphdetun2": 110,
        },
        "fcut": 1150, "fres": 0.25, "ftype": 0, "fwet": 1,
        "env": {"att": 0.50, "hold": 0.0, "dec": 0.70, "sustain": 0.85, "rel": 0.35},
    },
    "05_FOYER_FRAMES": {
        "vol": 84,
        "osc": {
            "wavetype0": 1, "vol0": 55, "coarse0": 0, "finel0": -4, "finer0": 4, "stphdetun0": 15,
            "wavetype1": 3, "vol1": 30, "coarse1": 0, "finel1": 6, "finer1": -6, "stphdetun1": 35,
            "wavetype2": 0, "vol2": 35, "coarse2": -12, "finel2": 0, "finer2": 0, "stphdetun2": 0,
        },
        "fcut": 2300, "fres": 0.35, "ftype": 0, "fwet": 1,
        "env": {"att": 0.004, "hold": 0.0, "dec": 0.18, "sustain": 0.06, "rel": 0.10},
    },
    "06_INT_STAIR_DOWN": {
        "vol": 78,
        "osc": {
            "wavetype0": 1, "vol0": 50, "coarse0": 0, "finel0": -7, "finer0": 7, "stphdetun0": 30,
            "wavetype1": 0, "vol1": 45, "coarse1": 12, "finel1": 5, "finer1": -5, "stphdetun1": 50,
            "wavetype2": 2, "vol2": 20, "coarse2": 0, "finel2": -3, "finer2": 3, "stphdetun2": 20,
        },
        "fcut": 3200, "fres": 0.25, "ftype": 0, "fwet": 1,
        "env": {"att": 0.02, "hold": 0.0, "dec": 0.28, "sustain": 0.55, "rel": 0.16},
    },
    "07_SKYLIGHT_ROOF": {
        "vol": 70,
        "osc": {
            "wavetype0": 0, "vol0": 48, "coarse0": 0, "finel0": -8, "finer0": 8, "stphdetun0": 70,
            "wavetype1": 1, "vol1": 38, "coarse1": 12, "finel1": 8, "finer1": -8, "stphdetun1": 100,
            "wavetype2": 0, "vol2": 28, "coarse2": 7, "finel2": -5, "finer2": 5, "stphdetun2": 40,
        },
        "fcut": 6200, "fres": 0.20, "ftype": 0, "fwet": 1,
        "env": {"att": 0.20, "hold": 0.0, "dec": 0.45, "sustain": 0.72, "rel": 0.25},
    },
}


def load_als_tracks(als_path):
    """Extract ordered (track_name, [(time_beats, midi_key, dur_beats, vel), ...]) from ALS."""
    with gzip.open(als_path, "rb") as f:
        root = ET.parse(f).getroot()

    tracks = []
    for mt in root.findall(".//MidiTrack"):
        name_el = mt.find("./Name/EffectiveName")
        tname = name_el.attrib.get("Value") if name_el is not None else f"Track_{len(tracks)+1}"
        clip = mt.find(".//ArrangerAutomation/Events/MidiClip")
        notes = []
        if clip is not None:
            for kt in clip.findall(".//KeyTrack"):
                key = int(kt.find("./MidiKey").attrib["Value"])
                for mn in kt.findall("./Notes/MidiNoteEvent"):
                    t = float(mn.attrib["Time"])
                    d = float(mn.attrib["Duration"])
                    v = int(float(mn.attrib["Velocity"]))
                    notes.append((t, key, d, v))
        notes.sort()
        tracks.append((tname, notes))
    return tracks


def make_env_sub(tag, amt=0, att=0.0, hold=0.0, dec=0.5, sustain=0.5, rel=0.1):
    """Create <elvol>, <elcut>, or <elres> element matching LMMS 1.2.2."""
    return ET.Element(
        tag,
        {
            "lspd_denominator": "4",
            "sustain": f"{sustain}",
            "pdel": "0",
            "userwavefile": "",
            "dec": f"{dec}",
            "lamt": "0",
            "latt": "0",
            "rel": f"{rel}",
            "amt": f"{amt}",
            "x100": "0",
            "att": f"{att}",
            "lpdel": "0",
            "hold": f"{hold}",
            "lspd_syncmode": "0",
            "lshp": "0",
            "lspd": "0.1",
            "ctlenvamt": "0",
            "lspd_numerator": "4",
        },
    )


def build_track_xml(idx, track_name, notes):
    """Build a single LMMS <track type='0'> element with instrument and 4-bar pattern."""
    patch = VOICE_PATCHES.get(track_name, VOICE_PATCHES["01_EXT_STAIR"])
    osc_cfg = patch["osc"]
    env_cfg = patch["env"]

    track = ET.Element("track", {"muted": "0", "type": "0", "name": track_name, "solo": "0"})
    inst_track = ET.SubElement(
        track,
        "instrumenttrack",
        {
            "pan": "0",
            "fxch": "0",
            "usemasterpitch": "1",
            "pitchrange": "1",
            "pitch": "0",
            "basenote": "57",
            "vol": str(patch["vol"]),
        },
    )

    inst = ET.SubElement(inst_track, "instrument", {"name": "tripleoscillator"})
    osc_attrs = {
        "phoffset0": "0", "phoffset1": "0", "phoffset2": "0",
        "userwavefile0": "", "userwavefile1": "", "userwavefile2": "",
        "modalgo1": "2", "modalgo2": "2", "modalgo3": "2",
        "pan0": "0", "pan1": "0", "pan2": "0",
    }
    for k, v in osc_cfg.items():
        osc_attrs[k] = str(v)
    ET.SubElement(inst, "tripleoscillator", osc_attrs)

    eldata = ET.SubElement(
        inst_track,
        "eldata",
        {
            "fres": str(patch["fres"]),
            "ftype": str(patch["ftype"]),
            "fcut": str(patch["fcut"]),
            "fwet": str(patch["fwet"]),
        },
    )
    eldata.append(
        make_env_sub(
            "elvol",
            amt=1,
            att=env_cfg["att"],
            hold=env_cfg["hold"],
            dec=env_cfg["dec"],
            sustain=env_cfg["sustain"],
            rel=env_cfg["rel"],
        )
    )
    eldata.append(make_env_sub("elcut", amt=0))
    eldata.append(make_env_sub("elres", amt=0))

    ET.SubElement(inst_track, "chordcreator", {"chord": "0", "chordrange": "1", "chord-enabled": "0"})
    ET.SubElement(
        inst_track,
        "arpeggiator",
        {
            "arptime": "100", "arprange": "1", "arpskip": "0",
            "arptime_denominator": "4", "arptime_syncmode": "0",
            "arpmode": "0", "arpcycle": "0", "arp-enabled": "0",
            "arp": "0", "arptime_numerator": "4", "arpdir": "0",
            "arpmiss": "0", "arpgate": "100",
        },
    )
    ET.SubElement(
        inst_track,
        "midiport",
        {
            "inputcontroller": "0", "fixedoutputvelocity": "-1",
            "inputchannel": "0", "outputcontroller": "0",
            "writable": "0", "outputchannel": "1",
            "fixedinputvelocity": "-1", "fixedoutputnote": "-1",
            "outputprogram": "1", "basevelocity": "63", "readable": "0",
        },
    )
    ET.SubElement(inst_track, "fxchain", {"numofeffects": "0", "enabled": "0"})

    pattern = ET.SubElement(
        track,
        "pattern",
        {
            "muted": "0",
            "name": track_name,
            "steps": "16",
            "pos": str(idx * TICKS_PER_ELEMENT),
            "type": "1",
            "len": str(TICKS_PER_ELEMENT),
        },
    )

    for beat_t, midi_key, dur_b, vel in notes:
        pos_ticks = max(0, int(round(beat_t * TICKS_PER_BEAT)))
        len_ticks = max(6, int(round(dur_b * TICKS_PER_BEAT)))
        # Clamp inside the 4-bar slot so sustained notes release smoothly before the next voice
        if pos_ticks + len_ticks > TICKS_PER_ELEMENT - 4:
            len_ticks = max(6, (TICKS_PER_ELEMENT - 4) - pos_ticks)
        # LMMS basenote=57 equals MIDI 69 (A4 = 440 Hz), so lmms_key = midi_key - 12
        lmms_key = max(0, min(107, midi_key - 12))
        lmms_vol = max(1, min(200, int(round((vel / 127.0) * 100))))
        ET.SubElement(
            pattern,
            "note",
            {
                "key": str(lmms_key),
                "vol": str(lmms_vol),
                "pos": str(pos_ticks),
                "pan": "0",
                "len": str(len_ticks),
            },
        )

    return track


def build_lmms_project():
    tracks = load_als_tracks(ALS_PATH)
    total_ticks = len(tracks) * TICKS_PER_ELEMENT

    root = ET.Element(
        "lmms-project",
        {"version": "1.0", "creator": "LMMS", "creatorversion": "1.2.2", "type": "song"},
    )
    ET.SubElement(
        root,
        "head",
        {
            "timesig_numerator": "4",
            "mastervol": "100",
            "timesig_denominator": "4",
            "bpm": str(BPM),
            "masterpitch": "0",
        },
    )
    song = ET.SubElement(root, "song")
    tc = ET.SubElement(
        song,
        "trackcontainer",
        {
            "width": "720",
            "x": "5",
            "y": "5",
            "maximized": "0",
            "height": "420",
            "visible": "1",
            "type": "song",
            "minimized": "0",
        },
    )

    for idx, (tname, notes) in enumerate(tracks):
        tc.append(build_track_xml(idx, tname, notes))
        print(f"  + Added LMMS track {idx+1}/7: {tname:18s} ({len(notes)} notes @ bar {idx*4+1})")

    fxmixer = ET.SubElement(
        song,
        "fxmixer",
        {"width": "543", "x": "5", "y": "435", "maximized": "0", "height": "260", "visible": "1", "minimized": "0"},
    )
    master_ch = ET.SubElement(fxmixer, "fxchannel", {"num": "0", "muted": "0", "volume": "1", "name": "Master", "soloed": "0"})
    ET.SubElement(master_ch, "fxchain", {"numofeffects": "0", "enabled": "0"})

    ET.SubElement(song, "ControllerRackView", {"width": "350", "x": "740", "y": "435", "maximized": "0", "height": "200", "visible": "0", "minimized": "0"})
    ET.SubElement(song, "pianoroll", {"width": "720", "x": "5", "y": "5", "maximized": "0", "height": "480", "visible": "0", "minimized": "0"})
    ET.SubElement(song, "automationeditor", {"width": "640", "x": "5", "y": "5", "maximized": "0", "height": "400", "visible": "0", "minimized": "0"})
    notes_el = ET.SubElement(
        song,
        "projectnotes",
        {"width": "500", "x": "740", "y": "5", "maximized": "0", "height": "360", "visible": "1", "minimized": "0"},
    )
    notes_el.text = (
        "InteractiveMusicArchitecture SoundLab (116 BPM, 28 bars = 4 bars per architectural element).\n"
        "Edit any instrument/effect or notes in the 7 tracks, save (Ctrl+S), then double-click "
        "export_audio_from_lmms.bat to render and update the web app!"
    )
    ET.SubElement(song, "timeline", {"lp1pos": str(total_ticks), "lp0pos": "0", "lpstate": "0"})
    ET.SubElement(song, "controllers")

    ET.indent(root, space="  ")
    xml_body = ET.tostring(root, encoding="unicode")
    full_xml = '<?xml version="1.0"?>\n<!DOCTYPE lmms-project>\n' + xml_body + "\n"

    with open(MMP_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(full_xml)
    print(f"[SUCCESS] Wrote {MMP_PATH}")

    if os.path.isdir(os.path.dirname(THESIS_MMP_PATH)):
        shutil.copy2(MMP_PATH, THESIS_MMP_PATH)
        print(f"[SUCCESS] Copied to {THESIS_MMP_PATH}")


if __name__ == "__main__":
    build_lmms_project()
