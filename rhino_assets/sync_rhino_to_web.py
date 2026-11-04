#!/usr/bin/env python3
"""
sync_rhino_to_web.py
====================
Reads the user's edited Rhino 3D model:
    D:/CODING/Thesis/InteractiveMusicArchitecture_Master.3dm
Strictly filters out:
  - Deleted objects
  - Hidden objects (attr.Visible == False)
  - Objects on hidden layers or parent layers (layer.Visible == False)
  - Reference drawing layers (00_REFERENCE_DRAWINGS)
And exports the exact right-handed 3D triangulated surface meshes + Brep wireframe edges
of all visible architectural elements to:
    D:/CODING/InteractiveMusicArchitecture/web_prototype/jsg_model_data.js

Coordinate Mapping (Right-Handed Rhino Z-up -> Right-Handed Three.js Y-up):
  Three.js x = +Rhino X / 100.0  (South Stair = 103.3m -> North Tip = 0.0m)
  Three.js y = +Rhino Z / 100.0  (Elevation Up: 0.0m -> +5.93m Upper Floor)
  Three.js z = -Rhino Y / 100.0  (West Colonnade = Left side when climbing stairs,
                                  East Foyer Wall = Right side when climbing stairs)
"""

import json
import os
import rhino3dm

RHINO_PATH = r"D:\CODING\Thesis\InteractiveMusicArchitecture_Master.3dm"
OUT_JS_PATH = r"D:\CODING\InteractiveMusicArchitecture\web_prototype\jsg_model_data.js"


def classify_musical_voice(name: str, layer_path: str) -> str:
    n = name or ""
    lp = layer_path or ""

    if "Stair_GrandExterior" in n or "GrandStair_CheekWall" in n:
        return "EXT_STAIR"
    if "SM_Meso_Column_" in n or "02_Meso_Columns" in lp or "Colonnade" in lp:
        return "EXT_COLUMNS"
    if (
        "SouthUpperEntrance" in n
        or "VestibuleInner" in n
        or "EntranceWindbreak" in n
        or "TerracePavilion" in n
    ):
        return "ENTRANCE_GLASS"
    if (
        "InteriorStairSkylight" in n
        or "SkylightCofferFin" in n
        or "StairwellRoof_CofferSlab" in n
    ):
        return "SKYLIGHT_ROOF"
    if "Stair_InteriorMain" in n or "StairEastWalkway_Balustrade" in n:
        return "INT_STAIR_DOWN"
    if (
        "SM_Meso_Mullion_" in n
        or "SM_Meso_Transom_" in n
        or "FacadeFrames" in lp
    ):
        return "FOYER_FRAMES"
    if "SM_Micro_Glass_" in n or "FacadeGlazing" in lp:
        return "ENTRANCE_GLASS"
    if (
        "Foyer" in n
        or "Core" in n
        or "Stairwell" in n
        or "UpperLevel_MainFloorSlab" in n
        or "Ceiling_Coffer_MainFoyer" in n
    ):
        return "FOYER_VOID"
    return "CONTEXT_MASS"


def is_pass_through(name: str, layer_path: str) -> bool:
    n = name or ""
    lp = layer_path or ""
    if "SM_Micro_Glass_" in n or "FacadeGlazing" in lp:
        return True
    if "SouthUpperEntrance" in n or "VestibuleInner" in n or "EntranceWindbreak" in n:
        return True
    return False


def extract_brep_mesh_and_edges(geom):
    """
    Extracts exact right-handed Three.js coordinates:
      (x = +rx/100, y = +rz/100, z = -ry/100)
    from Rhino Brep render meshes and Brep edges.
    """
    verts = []
    faces = []
    edges = []
    v_offset = 0

    if hasattr(geom, "Faces"):
        for f_idx in range(len(geom.Faces)):
            msh = geom.Faces[f_idx].GetMesh(rhino3dm.MeshType.Any)
            if msh is None:
                continue
            for v_i in range(len(msh.Vertices)):
                pt = msh.Vertices[v_i]
                verts.extend([
                    round(pt.X / 100.0, 3),
                    round(pt.Z / 100.0, 3),
                    round(-pt.Y / 100.0, 3),
                ])
            for fc_i in range(len(msh.Faces)):
                fc = msh.Faces[fc_i]
                faces.extend([v_offset + fc[0], v_offset + fc[1], v_offset + fc[2]])
                if fc[2] != fc[3]:
                    faces.extend([v_offset + fc[0], v_offset + fc[2], v_offset + fc[3]])
            v_offset += len(msh.Vertices)

    if hasattr(geom, "Edges"):
        for e_idx in range(len(geom.Edges)):
            ed = geom.Edges[e_idx]
            p0 = ed.PointAtStart
            p1 = ed.PointAtEnd
            edges.extend([
                round(p0.X / 100.0, 3),
                round(p0.Z / 100.0, 3),
                round(-p0.Y / 100.0, 3),
                round(p1.X / 100.0, 3),
                round(p1.Z / 100.0, 3),
                round(-p1.Y / 100.0, 3),
            ])

    return verts, faces, edges


def main():
    print(f"Reading edited Rhino model: {RHINO_PATH}")
    model = rhino3dm.File3dm.Read(RHINO_PATH)
    if not model:
        raise RuntimeError(f"Failed to read {RHINO_PATH}")

    layers_by_id = {}
    layers_by_index = {}
    for i in range(len(model.Layers)):
        ly = model.Layers[i]
        layers_by_id[str(ly.Id)] = ly
        layers_by_index[ly.Index] = ly

    def is_layer_effectively_visible(ly) -> bool:
        curr = ly
        while curr is not None:
            if not curr.Visible:
                return False
            pid = str(curr.ParentLayerId)
            curr = layers_by_id.get(pid, None)
        return True

    exported_objects = []
    voice_counts = {}

    for i in range(len(model.Objects)):
        obj = model.Objects[i]
        attr = obj.Attributes
        geom = obj.Geometry
        ly = layers_by_index.get(attr.LayerIndex)
        lp = ly.FullPath if ly else "Default"

        if lp.startswith("00_REFERENCE"):
            continue
        if ly and not is_layer_effectively_visible(ly):
            continue
        if not attr.Visible:
            continue

        bb = geom.GetBoundingBox()
        # Note: because Three.js z = -Rhino Y, min_z comes from -bb.Max.Y and max_z comes from -bb.Min.Y!
        min_x = round(bb.Min.X / 100.0, 3)
        min_y = round(bb.Min.Z / 100.0, 3)
        min_z = round(-bb.Max.Y / 100.0, 3)
        max_x = round(bb.Max.X / 100.0, 3)
        max_y = round(bb.Max.Z / 100.0, 3)
        max_z = round(-bb.Min.Y / 100.0, 3)

        verts, faces, edges = extract_brep_mesh_and_edges(geom)
        if not verts or not faces:
            continue

        name = attr.Name or f"Arch_{i}"
        voice = classify_musical_voice(name, lp)
        voice_counts[voice] = voice_counts.get(voice, 0) + 1

        exported_objects.append(
            {
                "id": i,
                "name": name,
                "layer": lp,
                "voice": voice,
                "passThrough": is_pass_through(name, lp),
                "min": [min_x, min_y, min_z],
                "max": [max_x, max_y, max_z],
                "v": verts,
                "f": faces,
                "e": edges,
            }
        )

    payload = {
        "sourceFile": RHINO_PATH,
        "objectCount": len(exported_objects),
        "voiceCounts": voice_counts,
        "objects": exported_objects,
    }

    os.makedirs(os.path.dirname(OUT_JS_PATH), exist_ok=True)
    with open(OUT_JS_PATH, "w", encoding="utf-8") as f:
        f.write("// Auto-generated exact right-handed 3D geometry from D:\\CODING\\Thesis\\InteractiveMusicArchitecture_Master.3dm\n")
        f.write("window.JSG_MODEL_DATA = ")
        json.dump(payload, f, separators=(",", ":"))
        f.write(";\n")

    print(f"Exported {len(exported_objects)} mirrored right-handed 3D objects -> {OUT_JS_PATH}")


if __name__ == "__main__":
    main()
