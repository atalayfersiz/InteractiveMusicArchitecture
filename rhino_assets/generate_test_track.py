"""
================================================================================
  Interactive Music Architecture — "Test Track" Generator
  Master's Thesis Prototype | Rhino Python Script
================================================================================

  HOW TO RUN:
  1. Open Rhino 3D.
  2. Type the command: _EditPythonScript  (in the Rhino command line)
  3. In the Python Script Editor, go to File > Open and load this .py file,
     OR paste the entire script contents into the editor window.
  4. Press the green "Run" button (or F5) to execute.
  5. All geometry, layers, names, and colors will be generated automatically.

  IMPORTANT: Save your Rhino file BEFORE running to avoid losing existing work.
             The script will NOT delete existing geometry, but it will change
             the document unit system to Centimeters.

  UE5 / DATASMITH NOTES:
  - Each object is a separate polysurface (no booleans) for raycasting isolation.
  - Object names follow the SM_ prefix convention for UE5 Static Mesh detection.
  - Layers map to Datasmith layer groups for material/OSC tag separation.
  - All coordinates are in Centimeters (1 unit = 1 cm).
================================================================================
"""

import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino
import System.Drawing.Color as SysColor


# ==============================================================================
#  UNIT CONVERSION CONSTANTS  (design values are in METERS; multiply by 100 → cm)
# ==============================================================================

M = 100  # 1 meter = 100 centimeters


# ==============================================================================
#  UTILITY HELPERS
# ==============================================================================

def ensure_centimeters():
    """Force the active Rhino document unit system to Centimeters."""
    doc = sc.doc
    if doc.ModelUnitSystem != Rhino.UnitSystem.Centimeters:
        doc.ModelUnitSystem = Rhino.UnitSystem.Centimeters
        print("  [Units] Document units set to Centimeters.")
    else:
        print("  [Units] Document units are already Centimeters. OK.")


def get_or_create_layer(name, parent_name=None, color=None):
    """
    Return the index of a layer, creating it if it does not exist.
    Optionally parent it under an existing layer and assign a display color.
    """
    full_name = "{0}::{1}".format(parent_name, name) if parent_name else name

    if not rs.IsLayer(full_name):
        rs.AddLayer(name, color=color, parent=parent_name)

    if color:
        rs.LayerColor(full_name, color)

    return full_name


def make_box_surface(x0, y0, z0, x1, y1, z1, obj_name, layer):
    """
    Create a closed polysurface box between two corner points and assign
    the UE5-compatible object name and layer.

    x0,y0,z0 = min corner
    x1,y1,z1 = max corner
    """
    pt_min = (x0, y0, z0)
    pt_max = (x1, y1, z1)
    box_id = rs.AddBox(
        [
            (x0, y0, z0),
            (x1, y0, z0),
            (x1, y1, z0),
            (x0, y1, z0),
            (x0, y0, z1),
            (x1, y0, z1),
            (x1, y1, z1),
            (x0, y1, z1),
        ]
    )
    if box_id:
        rs.ObjectName(box_id, obj_name)
        rs.ObjectLayer(box_id, layer)
    return box_id


def make_planar_surface(corners, obj_name, layer):
    """
    Create a single planar surface from a list of 4 corner points,
    convert it to a polysurface (Brep), then name and layer it.
    """
    srf_id = rs.AddSrfPt(corners)
    if srf_id:
        rs.ObjectName(srf_id, obj_name)
        rs.ObjectLayer(srf_id, layer)
    return srf_id


# ==============================================================================
#  LAYER SETUP
# ==============================================================================

# Color palette (R, G, B)
COLOR_MACRO = (70,  130, 180)   # Steel Blue  – Macro / The Void
COLOR_MESO  = (60,  179, 113)   # Medium Sea Green – Meso / The Colonnade
COLOR_MICRO = (210, 105,  30)   # Chocolate – Micro / The Niche

LAYER_MACRO = "Macro_Zone"
LAYER_MESO  = "Meso_Zone"
LAYER_MICRO = "Micro_Zone"


def setup_layers():
    """Create (or confirm) the three parent zone layers with distinct colors."""
    print("\n  [Layers] Setting up zone layers...")
    for name, rgb in [
        (LAYER_MACRO, COLOR_MACRO),
        (LAYER_MESO,  COLOR_MESO),
        (LAYER_MICRO, COLOR_MICRO),
    ]:
        color = SysColor.FromArgb(*rgb)
        if not rs.IsLayer(name):
            rs.AddLayer(name, color=color)
        else:
            rs.LayerColor(name, color)
        print("    Layer '{0}' ready. Color: {1}".format(name, rgb))


# ==============================================================================
#  ZONE 1 — THE MACRO (The Void)
#
#  Position : origin (0, 0, 0)
#  Size      : 20 m wide (X) × 30 m long (Y) × 15 m high (Z)
#              in centimeters: 2000 × 3000 × 1500
#
#  Geometry  : 6 thin polysurface slabs (floor, ceiling, 4 walls)
#              Thickness = 20 cm (architectural wall convention)
# ==============================================================================

WALL_T = 20  # wall / slab thickness in cm

def build_macro_zone():
    """
    Construct Zone 1: The Macro (The Void).
    A cavernous hall with individually named surfaces.
    Returns a dict mapping name → object GUID.
    """
    print("\n  [Zone 1] Building Macro Zone (The Void)...")
    objs = {}

    W  = 20 * M    # 2000 cm  width  (X)
    L  = 30 * M    # 3000 cm  length (Y)
    H  = 15 * M    # 1500 cm  height (Z)
    T  = WALL_T    #   20 cm  thickness

    # Coordinate reference: hall occupies X[0..W], Y[0..L], Z[0..H]
    # Walls are placed OUTSIDE the interior envelope so the interior is clean.

    # --- Floor ---
    oid = make_box_surface(
        0, 0, -T,
        W, L,  0,
        "SM_Macro_Floor", LAYER_MACRO
    )
    objs["SM_Macro_Floor"] = oid

    # --- Ceiling ---
    oid = make_box_surface(
        0, 0, H,
        W, L, H + T,
        "SM_Macro_Ceiling", LAYER_MACRO
    )
    objs["SM_Macro_Ceiling"] = oid

    # --- Left Wall  (X = 0 face, runs full Y, full Z) ---
    oid = make_box_surface(
        -T, 0, 0,
         0, L, H,
        "SM_Macro_Wall_Left", LAYER_MACRO
    )
    objs["SM_Macro_Wall_Left"] = oid

    # --- Right Wall (X = W face) ---
    oid = make_box_surface(
        W,    0, 0,
        W+T,  L, H,
        "SM_Macro_Wall_Right", LAYER_MACRO
    )
    objs["SM_Macro_Wall_Right"] = oid

    # --- Back Wall  (Y = 0 face — the "entrance" end from origin) ---
    oid = make_box_surface(
         0, -T, 0,
         W,  0, H,
        "SM_Macro_Wall_Back", LAYER_MACRO
    )
    objs["SM_Macro_Wall_Back"] = oid

    # --- Front Wall (Y = L face — the opening toward the Colonnade) ---
    # The colonnade corridor is 5 m wide and centered on X.
    # Leave a doorway opening: corridor X range = [750, 1250] cm (5 m wide, centered at X=1000)
    CORR_W  = 5 * M    # corridor width  = 500 cm
    CORR_X0 = (W - CORR_W) // 2   # 750 cm
    CORR_X1 = CORR_X0 + CORR_W    # 1250 cm
    CORR_H  = 4 * M    # corridor height = 400 cm (meso ceiling)

    # Front wall is split into 3 panels: left pier, door header, right pier
    # Left pier
    oid = make_box_surface(
        0, L, 0,
        CORR_X0, L+T, H,
        "SM_Macro_Wall_Front_Left", LAYER_MACRO
    )
    objs["SM_Macro_Wall_Front_Left"] = oid

    # Right pier
    oid = make_box_surface(
        CORR_X1, L, 0,
        W, L+T, H,
        "SM_Macro_Wall_Front_Right", LAYER_MACRO
    )
    objs["SM_Macro_Wall_Front_Right"] = oid

    # Header above doorway
    oid = make_box_surface(
        CORR_X0, L, CORR_H,
        CORR_X1, L+T, H,
        "SM_Macro_Wall_Front_Header", LAYER_MACRO
    )
    objs["SM_Macro_Wall_Front_Header"] = oid

    # Store corridor parameters for downstream zones
    build_macro_zone.corridor_x0 = CORR_X0
    build_macro_zone.corridor_x1 = CORR_X1
    build_macro_zone.corridor_h   = CORR_H
    build_macro_zone.macro_y_end  = L

    print("    Created {0} Macro objects.".format(len(objs)))
    return objs


# ==============================================================================
#  ZONE 2 — THE MESO (The Colonnade)
#
#  Connects directly to Zone 1 front wall.
#  Size : 5 m wide × 30 m long × 4 m high
#         in cm: 500 × 3000 × 400
#
#  Columns: 0.5 m × 0.5 m square, placed every 3 m along both walls
#           Column height matches corridor height (400 cm)
# ==============================================================================

def build_meso_zone(corridor_x0, corridor_x1, corridor_h, macro_y_end):
    """
    Construct Zone 2: The Meso (The Colonnade).
    Returns a dict mapping name → object GUID.
    """
    print("\n  [Zone 2] Building Meso Zone (The Colonnade)...")
    objs = {}

    W  = corridor_x1 - corridor_x0   # 500 cm
    L  = 30 * M                       # 3000 cm
    H  = corridor_h                   # 400 cm
    T  = WALL_T                       #  20 cm

    X0 = corridor_x0   # 750 cm  (left inner edge of corridor)
    X1 = corridor_x1   # 1250 cm (right inner edge)
    Y0 = macro_y_end   # 3000 cm (where macro zone ends)
    Y1 = Y0 + L        # 6000 cm

    # --- Floor ---
    oid = make_box_surface(
        X0, Y0, -T,
        X1, Y1,  0,
        "SM_Meso_Floor", LAYER_MESO
    )
    objs["SM_Meso_Floor"] = oid

    # --- Ceiling ---
    oid = make_box_surface(
        X0, Y0, H,
        X1, Y1, H + T,
        "SM_Meso_Ceiling", LAYER_MESO
    )
    objs["SM_Meso_Ceiling"] = oid

    # --- Left Wall (X = X0) ---
    oid = make_box_surface(
        X0-T, Y0, 0,
        X0,   Y1, H,
        "SM_Meso_Wall_Left", LAYER_MESO
    )
    objs["SM_Meso_Wall_Left"] = oid

    # --- Right Wall (X = X1) ---
    oid = make_box_surface(
        X1,   Y0, 0,
        X1+T, Y1, H,
        "SM_Meso_Wall_Right", LAYER_MESO
    )
    objs["SM_Meso_Wall_Right"] = oid

    # --- End Wall (Y = Y1 — far terminus of colonnade) ---
    oid = make_box_surface(
        X0, Y1,   0,
        X1, Y1+T, H,
        "SM_Meso_Wall_End", LAYER_MESO
    )
    objs["SM_Meso_Wall_End"] = oid

    # --- Columns ---
    # 0.5 m × 0.5 m square, height = H
    # Spaced every 3 m (300 cm) along the corridor Y axis.
    # First column at Y0 + 300 cm (one spacing from the start).
    # Columns are flush against the inner wall face.

    COL_W   = 50    # 0.5 m = 50 cm
    COL_SPC = 300   # 3.0 m = 300 cm spacing

    col_count = 0
    col_y     = Y0 + COL_SPC   # start position of first column

    while col_y + COL_W <= Y1:
        col_count += 1
        tag = "{:02d}".format(col_count)

        # Left column — sits against the left inner wall (X0 face)
        name_l = "SM_Meso_Column_L{0}".format(tag)
        oid = make_box_surface(
            X0,        col_y, 0,
            X0+COL_W,  col_y + COL_W, H,
            name_l, LAYER_MESO
        )
        objs[name_l] = oid

        # Right column — sits against the right inner wall (X1 face)
        name_r = "SM_Meso_Column_R{0}".format(tag)
        oid = make_box_surface(
            X1-COL_W, col_y, 0,
            X1,       col_y + COL_W, H,
            name_r, LAYER_MESO
        )
        objs[name_r] = oid

        col_y += COL_SPC

    # Store info for Zone 3 (Micro) placement
    build_meso_zone.col_count    = col_count
    build_meso_zone.meso_x0      = X0
    build_meso_zone.meso_x1      = X1
    build_meso_zone.meso_y0      = Y0
    build_meso_zone.meso_y1      = Y1
    build_meso_zone.meso_h       = H
    build_meso_zone.corridor_w   = W
    build_meso_zone.col_w        = COL_W
    build_meso_zone.col_spc      = COL_SPC

    print("    Created {0} Meso objects ({1} column pairs).".format(
        len(objs), col_count))
    return objs


# ==============================================================================
#  ZONE 3 — THE MICRO (The Niche)
#
#  Recessed alcove carved into the LEFT wall of the colonnade,
#  placed at the midpoint of the corridor (Y = meso_y0 + L/2).
#
#  Niche size: 3 m wide × 2 m deep × 2.5 m high
#              in cm: 300 × 200 × 250
# ==============================================================================

def build_micro_zone(meso_x0, meso_y0, meso_y1, meso_h):
    """
    Construct Zone 3: The Micro (The Niche).
    An alcove recessed into the left wall of the colonnade.
    Returns a dict mapping name → object GUID.
    """
    print("\n  [Zone 3] Building Micro Zone (The Niche)...")
    objs = {}

    NW  = 3   * M    # niche width   = 300 cm  (runs along Y axis)
    ND  = 2   * M    # niche depth   = 200 cm  (extends in -X direction)
    NH  = 2.5 * M    # niche height  = 250 cm
    T   = WALL_T     # wall thickness  20 cm

    # Midpoint of the meso corridor along Y
    mid_y  = (meso_y0 + meso_y1) // 2
    NY0    = mid_y - NW // 2    # niche Y start
    NY1    = NY0  + NW          # niche Y end

    # Niche is cut into the LEFT wall: X goes from (meso_x0 - T) outward to (meso_x0 - T - ND)
    NX_INNER = meso_x0            # flush with corridor interior
    NX_OUTER = meso_x0 - T - ND   # back of niche (furthest from corridor)

    # --- Niche Back Wall (the deepest face, parallel to corridor) ---
    oid = make_box_surface(
        NX_OUTER-T, NY0, 0,
        NX_OUTER,   NY1, NH,
        "SM_Micro_NicheWall_Back", LAYER_MICRO
    )
    objs["SM_Micro_NicheWall_Back"] = oid

    # --- Niche Side Wall — Near (Y = NY0) ---
    oid = make_box_surface(
        NX_OUTER, NY0-T, 0,
        NX_INNER, NY0,   NH,
        "SM_Micro_NicheWall_Near", LAYER_MICRO
    )
    objs["SM_Micro_NicheWall_Near"] = oid

    # --- Niche Side Wall — Far (Y = NY1) ---
    oid = make_box_surface(
        NX_OUTER, NY1,   0,
        NX_INNER, NY1+T, NH,
        "SM_Micro_NicheWall_Far", LAYER_MICRO
    )
    objs["SM_Micro_NicheWall_Far"] = oid

    # --- Niche Dropped Ceiling (at NH = 250 cm, below corridor ceiling at meso_h = 400 cm) ---
    oid = make_box_surface(
        NX_OUTER, NY0, NH,
        NX_INNER, NY1, NH + T,
        "SM_Micro_NicheCeiling", LAYER_MICRO
    )
    objs["SM_Micro_NicheCeiling"] = oid

    # --- Niche Floor (same Z=0 as corridor, but explicitly defined) ---
    oid = make_box_surface(
        NX_OUTER, NY0, -T,
        NX_INNER, NY1,  0,
        "SM_Micro_NicheFloor", LAYER_MICRO
    )
    objs["SM_Micro_NicheFloor"] = oid

    # --- Soffit Panel — fills the gap between niche ceiling and corridor ceiling
    #     This is the exposed underside of the corridor left wall ABOVE the niche opening.
    oid = make_box_surface(
        NX_OUTER, NY0, NH + T,
        NX_INNER, NY1, meso_h,
        "SM_Micro_NicheSoffit", LAYER_MICRO
    )
    objs["SM_Micro_NicheSoffit"] = oid

    print("    Created {0} Micro objects.".format(len(objs)))
    return objs


# ==============================================================================
#  SUMMARY REPORT
# ==============================================================================

def print_summary(all_objs):
    """Print a structured report of all created objects to the console."""
    print("\n" + "="*72)
    print("  GENERATION COMPLETE — Test Track Summary")
    print("="*72)
    total = sum(len(v) for v in all_objs.values())
    for zone, objs in all_objs.items():
        print("\n  [{0}]  ({1} objects)".format(zone, len(objs)))
        for name, oid in objs.items():
            status = "OK" if oid else "FAILED"
            print("    {0:<40} [{1}]".format(name, status))
    print("\n  Total objects created: {0}".format(total))
    print("="*72)
    print("\n  NEXT STEPS FOR UE5 / DATASMITH:")
    print("    1. File > Export Selected (or Export All) as .3dm or use")
    print("       the Datasmith Rhino Exporter plugin (recommended).")
    print("    2. In UE5, import via Datasmith. Each Rhino layer becomes")
    print("       a UE5 layer group. SM_ object names map directly to")
    print("       Static Mesh actor names in the World Outliner.")
    print("    3. Use Line Trace By Object Type (Blueprint) or a C++ ray-")
    print("       cast, then read GetActorLabel() to trigger OSC events")
    print("       based on the SM_Macro_ / SM_Meso_ / SM_Micro_ prefixes.")
    print("="*72 + "\n")


# ==============================================================================
#  MAIN ENTRY POINT
# ==============================================================================

def main():
    print("\n" + "="*72)
    print("  Interactive Music Architecture — Test Track Generator")
    print("  Master's Thesis Prototype")
    print("="*72)

    # 1. Units
    ensure_centimeters()

    # 2. Layers
    setup_layers()

    # 3. Zone 1 — Macro
    macro_objs = build_macro_zone()

    # 4. Zone 2 — Meso (uses geometry parameters returned by Zone 1)
    meso_objs = build_meso_zone(
        corridor_x0 = build_macro_zone.corridor_x0,
        corridor_x1 = build_macro_zone.corridor_x1,
        corridor_h  = build_macro_zone.corridor_h,
        macro_y_end = build_macro_zone.macro_y_end,
    )

    # 5. Zone 3 — Micro (uses geometry parameters returned by Zone 2)
    micro_objs = build_micro_zone(
        meso_x0 = build_meso_zone.meso_x0,
        meso_y0 = build_meso_zone.meso_y0,
        meso_y1 = build_meso_zone.meso_y1,
        meso_h  = build_meso_zone.meso_h,
    )

    # 6. Refresh viewport and zoom to fit
    rs.ZoomExtents(all=True)

    # 7. Summary
    print_summary({
        "Macro_Zone": macro_objs,
        "Meso_Zone":  meso_objs,
        "Micro_Zone": micro_objs,
    })


# Guard so the script runs only when executed directly
if __name__ == "__main__":
    main()
