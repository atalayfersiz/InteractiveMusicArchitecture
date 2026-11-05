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
And exports the exact right-handed 3D triangulated surface meshes + clean non-coplanar
crease edges (equivalent to Rhino's MergeAllCoplanarFaces / display edge cleanup) to:
    D:/CODING/InteractiveMusicArchitecture/web_prototype/jsg_model_data.js

Coordinate Mapping (Right-Handed Rhino Z-up -> Right-Handed Three.js Y-up):
  Three.js x = +Rhino X / 100.0  (South Stair = 103.3m -> North Tip = 0.0m)
  Three.js y = +Rhino Z / 100.0  (Elevation Up: 0.0m -> +5.93m Upper Floor)
  Three.js z = -Rhino Y / 100.0  (West Colonnade = Left side when climbing stairs,
                                  East Foyer Wall = Right side when climbing stairs)
"""

import json
import os
import numpy as np
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


def extract_brep_mesh_and_raw_edges(geom):
    """
    Extracts exact right-handed Three.js coordinates:
      (x = +rx/100, y = +rz/100, z = -ry/100)
    from Rhino Brep render meshes and raw Brep edges.
    """
    verts = []
    faces = []
    raw_edges = []
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
            raw_edges.extend([
                round(p0.X / 100.0, 3),
                round(p0.Z / 100.0, 3),
                round(-p0.Y / 100.0, 3),
                round(p1.X / 100.0, 3),
                round(p1.Z / 100.0, 3),
                round(-p1.Y / 100.0, 3),
            ])

    return verts, faces, raw_edges


def filter_all_coplanar_edges(objects_list, cell_size=2.0, tol=0.005, angle_threshold_deg=15.0):
    """
    Implements the equivalent of Rhino's 'MergeAllCoplanarFaces' & display edge cleanup:
    Eliminates all internal seam edges lying between coplanar faces (both within the same
    Brep and across touching adjacent Breps like walls, plinths, and slabs).
    """
    faces_by_cell = {}
    cos_thresh = np.cos(np.radians(angle_threshold_deg))

    # 1. Spatial hashing of all triangle faces across all visible objects
    for o in objects_list:
        v, f = o.get("v", []), o.get("f", [])
        if not v or not f:
            continue
        V = np.array(v, dtype=np.float32).reshape(-1, 3)
        F = np.array(f, dtype=np.int32).reshape(-1, 3)
        v0, v1, v2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
        cross = np.cross(v1 - v0, v2 - v0)
        lengths = np.linalg.norm(cross, axis=1, keepdims=True)
        valid = lengths[:, 0] > 1e-4
        normals = np.zeros_like(cross)
        normals[valid] = cross[valid] / lengths[valid]

        for i in range(len(F)):
            if not valid[i]:
                continue
            n = normals[i]
            d = float(np.dot(n, v0[i]))
            pA, pB, pC = v0[i], v1[i], v2[i]
            min_p = np.minimum(np.minimum(pA, pB), pC)
            max_p = np.maximum(np.maximum(pA, pB), pC)
            gx0, gy0, gz0 = int(min_p[0] // cell_size), int(min_p[1] // cell_size), int(min_p[2] // cell_size)
            gx1, gy1, gz1 = int(max_p[0] // cell_size), int(max_p[1] // cell_size), int(max_p[2] // cell_size)
            entry = (n, d, pA, pB, pC)
            for gx in range(gx0, gx1 + 1):
                for gy in range(gy0, gy1 + 1):
                    for gz in range(gz0, gz1 + 1):
                        faces_by_cell.setdefault((gx, gy, gz), []).append(entry)

    def is_coplanar_seam(p0, p1):
        pm = (p0 + p1) * 0.5
        v = p1 - p0
        v_len = np.linalg.norm(v)
        if v_len < 1e-4:
            return True  # degenerate zero-length edge
        v_dir = v / v_len

        gx, gy, gz = int(pm[0] // cell_size), int(pm[1] // cell_size), int(pm[2] // cell_size)
        candidates = faces_by_cell.get((gx, gy, gz), [])
        if not candidates:
            return False

        coplanar_normals = []
        for n, d, pA, pB, pC in candidates:
            if abs(np.dot(n, pm) - d) > tol:
                continue
            if abs(np.dot(n, v_dir)) > 0.05:
                continue
            min_f = np.minimum(np.minimum(pA, pB), pC) - tol
            max_f = np.maximum(np.maximum(pA, pB), pC) + tol
            if np.any(pm < min_f) or np.any(pm > max_f):
                continue
            perp = np.cross(n, v_dir)
            d_A = np.dot(pA - pm, perp)
            d_B = np.dot(pB - pm, perp)
            d_C = np.dot(pC - pm, perp)
            side = 0
            if d_A > 0.001 or d_B > 0.001 or d_C > 0.001:
                side += 1
            if d_A < -0.001 or d_B < -0.001 or d_C < -0.001:
                side -= 2
            coplanar_normals.append((n, side))

        for i in range(len(coplanar_normals)):
            n1, s1 = coplanar_normals[i]
            for j in range(i + 1, len(coplanar_normals)):
                n2, s2 = coplanar_normals[j]
                if np.dot(n1, n2) > cos_thresh:
                    # Coplanar triangles on opposite sides of this line segment
                    if (s1 > 0 and s2 < 0) or (s1 < 0 and s2 > 0):
                        return True
        return False

    # 2. Filter every object's edge list to remove coplanar face seams
    total_raw = 0
    total_clean = 0
    for o in objects_list:
        raw_e = o.get("e", [])
        clean_e = []
        for i in range(0, len(raw_e), 6):
            total_raw += 1
            p0 = np.array([raw_e[i], raw_e[i + 1], raw_e[i + 2]], dtype=np.float32)
            p1 = np.array([raw_e[i + 3], raw_e[i + 4], raw_e[i + 5]], dtype=np.float32)
            if not is_coplanar_seam(p0, p1):
                clean_e.extend([
                    round(float(p0[0]), 3), round(float(p0[1]), 3), round(float(p0[2]), 3),
                    round(float(p1[0]), 3), round(float(p1[1]), 3), round(float(p1[2]), 3)
                ])
                total_clean += 1
        o["e"] = clean_e

    print(f"MergeAllCoplanarFaces Edge Filtering: {total_raw} raw edges -> {total_clean} clean edges ({total_raw - total_clean} coplanar seams eliminated).")


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
        min_x = round(bb.Min.X / 100.0, 3)
        min_y = round(bb.Min.Z / 100.0, 3)
        min_z = round(-bb.Max.Y / 100.0, 3)
        max_x = round(bb.Max.X / 100.0, 3)
        max_y = round(bb.Max.Z / 100.0, 3)
        max_z = round(-bb.Min.Y / 100.0, 3)

        verts, faces, raw_edges = extract_brep_mesh_and_raw_edges(geom)
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
                "e": raw_edges,
            }
        )

    # Apply global MergeAllCoplanarFaces edge elimination across all objects
    filter_all_coplanar_edges(exported_objects)

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

    print(f"Exported {len(exported_objects)} mirrored right-handed 3D objects with clean non-coplanar edges -> {OUT_JS_PATH}")


if __name__ == "__main__":
    main()
