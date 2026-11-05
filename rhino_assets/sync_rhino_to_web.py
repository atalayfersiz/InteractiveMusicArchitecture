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
  - Redundant duplicate slabs/panes & sealed internal elevator/shaft dividers
And exports the exact right-handed 3D triangulated surface meshes + clean non-coplanar
crease edges (1D interval-clipped MergeAllCoplanarFaces across all adjacent objects) to:
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

# Internal sealed core shaft dividers that are completely enclosed inside the outer
# South Core / Central Core walls and never entered by the user, plus buried floor ribs.
INTERNAL_SEALED_SHAFT_NAMES = {
    "SM_Macro_Wall_SouthCore_South",
    "SM_Macro_Wall_SouthCore_InternalLong",
    "SM_Macro_Wall_SouthCore_InternalCross",
    "SM_Macro_FloorSlab_UpperCentralCore_Z593",
    "SM_Macro_Wall_CentralCore_CoreStairDiv",
    "SM_Macro_Wall_CentralCore_ElevatorDiv",
    "SM_Macro_Wall_CentralCore_StairMidWall",
    "SM_Macro_Wall_CentralCore_TwinElevatorWall",
}


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
        or "WindbreakStoneBlock" in n
        or "SouthEntrancePortico" in n
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


def point_in_triangle_3d(pt, pA, pB, pC, n, eps=0.015):
    """Returns True if 3D point pt (assumed near the plane of ABC) lies inside or on triangle ABC."""
    c0 = np.dot(np.cross(pB - pA, pt - pA), n)
    c1 = np.dot(np.cross(pC - pB, pt - pB), n)
    c2 = np.dot(np.cross(pA - pC, pt - pC), n)
    return (c0 >= -eps) and (c1 >= -eps) and (c2 >= -eps)


def filter_all_coplanar_seams(objects_list, cell_size=4.0, tol=0.025, step=0.025):
    """
    Applies comprehensive coplanar seam elimination across the entire model for Shaded, Hybrid, and LiDAR views:
      1. Culls redundant coplanar overlapping triangles (contained inside a larger coplanar face of another object)
         and internal abutting seam triangles between solid blocks, preventing Z-fighting and double LiDAR density.
      2. Splits every edge segment into 1D intervals at all nearby vertex/box projections and clips out:
         - any sub-interval buried inside another solid volume, and
         - any sub-interval where coplanar surfaces exist on both sides (+perp and -perp) of the edge.
      3. Deduplicates shared crease edges globally across touching objects.
    """
    # Collect solid axis-aligned bounding boxes for non-glass, non-frame structural masses
    solid_boxes = []
    for idx, o in enumerate(objects_list):
        if o.get("passThrough") or o["voice"] in ("ENTRANCE_GLASS", "FOYER_FRAMES", "SKYLIGHT_ROOF"):
            continue
        V = np.array(o["v"], dtype=np.float32).reshape(-1, 3)
        bmin = np.array(o["min"], dtype=np.float32)
        bmax = np.array(o["max"], dtype=np.float32)
        on_x = (np.abs(V[:, 0] - bmin[0]) < 0.02) | (np.abs(V[:, 0] - bmax[0]) < 0.02)
        on_y = (np.abs(V[:, 1] - bmin[1]) < 0.02) | (np.abs(V[:, 1] - bmax[1]) < 0.02)
        on_z = (np.abs(V[:, 2] - bmin[2]) < 0.02) | (np.abs(V[:, 2] - bmax[2]) < 0.02)
        if np.all(on_x & on_y & on_z) and len(o["f"]) == 36:
            solid_boxes.append((idx, bmin, bmax))

    # Build spatial hash of all triangles first for coplanar face deduplication & edge clipping
    faces_by_cell = {}
    obj_tris = []

    for obj_idx, o in enumerate(objects_list):
        V = np.array(o["v"], dtype=np.float32).reshape(-1, 3)
        F = np.array(o["f"], dtype=np.int32).reshape(-1, 3)
        v0, v1, v2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
        cross = np.cross(v1 - v0, v2 - v0)
        lengths = np.linalg.norm(cross, axis=1, keepdims=True)
        valid = lengths[:, 0] > 1e-4
        normals = np.zeros_like(cross)
        normals[valid] = cross[valid] / lengths[valid]
        areas = 0.5 * lengths[:, 0]

        tris_for_obj = []
        for i in range(len(F)):
            if not valid[i]:
                continue
            n = normals[i]
            d = float(np.dot(n, v0[i]))
            pA, pB, pC = v0[i], v1[i], v2[i]
            area = float(areas[i])
            min_p = np.minimum(np.minimum(pA, pB), pC) - tol
            max_p = np.maximum(np.maximum(pA, pB), pC) + tol
            entry = (obj_idx, i, n, d, pA, pB, pC, min_p, max_p, area)
            tris_for_obj.append(entry)
            gx0, gy0, gz0 = int(min_p[0] // cell_size), int(min_p[1] // cell_size), int(min_p[2] // cell_size)
            gx1, gy1, gz1 = int(max_p[0] // cell_size), int(max_p[1] // cell_size), int(max_p[2] // cell_size)
            for gx in range(gx0, gx1 + 1):
                for gy in range(gy0, gy1 + 1):
                    for gz in range(gz0, gz1 + 1):
                        faces_by_cell.setdefault((gx, gy, gz), []).append(entry)
        obj_tris.append(tris_for_obj)

    # Sealed interior core cavities (inaccessible solid/shaft cores where internal faces should not generate LiDAR points)
    sealed_cavities = [
        # South Core interior cavity (enclosed by Obj 49, 50, 654, 655, 107, 45)
        (np.array([68.90, -6.36, -13.16], dtype=np.float32), np.array([82.35, 13.89, -7.42], dtype=np.float32)),
        # Central Core interior cavity (enclosed by Obj 89, 90, 91, 94, 108)
        (np.array([25.50, -9.32, -13.16], dtype=np.float32), np.array([46.35, 13.89, -7.42], dtype=np.float32)),
    ]

    # 1. Filter out:
    #    (a) smaller coplanar overlapping faces (same normal, contained inside a larger coplanar face),
    #    (b) opposing abutting seam faces (opposite normal, pressed flush against another solid face),
    #    (c) faces buried inside another solid box or facing into a sealed core cavity.
    total_faces_before = 0
    total_faces_after = 0
    for obj_idx, o in enumerate(objects_list):
        F = np.array(o["f"], dtype=np.int32).reshape(-1, 3)
        total_faces_before += len(F)
        is_structural_solid = (not o.get("passThrough")) and (o["voice"] not in ("ENTRANCE_GLASS", "FOYER_FRAMES", "SKYLIGHT_ROOF"))
        kept_faces = []
        for (_oi, tri_idx, n, d, pA, pB, pC, _min_p, _max_p, area) in obj_tris[obj_idx]:
            centroid = (pA + pB + pC) / 3.0

            # Check if outward normal from centroid points into a sealed core cavity or strictly inside another solid box
            if is_structural_solid:
                pt_out = centroid + 0.04 * n
                in_sealed_or_solid = False
                for cmin, cmax in sealed_cavities:
                    if np.all(pt_out > cmin) and np.all(pt_out < cmax):
                        in_sealed_or_solid = True
                        break
                if not in_sealed_or_solid:
                    for (b_idx, bmin, bmax) in solid_boxes:
                        if b_idx == obj_idx:
                            continue
                        if np.all(pt_out > bmin + 0.015) and np.all(pt_out < bmax - 0.015):
                            # Check that all 3 triangle sample points also step into a solid box
                            s1 = (0.6 * pA + 0.2 * pB + 0.2 * pC) + 0.04 * n
                            s2 = (0.2 * pA + 0.6 * pB + 0.2 * pC) + 0.04 * n
                            s3 = (0.2 * pA + 0.2 * pB + 0.6 * pC) + 0.04 * n
                            if (
                                np.all(s1 > bmin + 0.01) and np.all(s1 < bmax - 0.01)
                                and np.all(s2 > bmin + 0.01) and np.all(s2 < bmax - 0.01)
                                and np.all(s3 > bmin + 0.01) and np.all(s3 < bmax - 0.01)
                            ):
                                in_sealed_or_solid = True
                                break
                if in_sealed_or_solid:
                    continue

            sample_pts = [
                centroid,
                0.6 * pA + 0.2 * pB + 0.2 * pC,
                0.2 * pA + 0.6 * pB + 0.2 * pC,
                0.2 * pA + 0.2 * pB + 0.6 * pC,
            ]
            gx, gy, gz = int(centroid[0] // cell_size), int(centroid[1] // cell_size), int(centroid[2] // cell_size)
            cands = faces_by_cell.get((gx, gy, gz), [])

            # Check if all sample points of this triangle are covered by:
            # - a larger coplanar face with the same normal (dot > 0.98), OR
            # - an opposing abutting solid face with opposite normal (dot < -0.98)
            covered_or_abutting = False
            for sp in sample_pts:
                sp_covered = False
                for (other_idx, _oti, on, od, opA, opB, opC, omin, omax, oarea) in cands:
                    if other_idx == obj_idx:
                        continue
                    dot_n = float(np.dot(n, on))
                    if dot_n > 0.98:
                        if oarea < area - 1e-3:
                            continue
                        if abs(oarea - area) <= 1e-3 and other_idx > obj_idx:
                            continue
                    elif dot_n < -0.98 and is_structural_solid:
                        # Opposing abutting face between two solids: if our triangle is smaller (or equal with higher idx), cull it;
                        # and if both triangles are within the abutting overlap, cull the smaller one so no internal seam face remains
                        if oarea < area - 1e-3:
                            continue
                    else:
                        continue
                    if abs(np.dot(on, sp) - od) > tol:
                        continue
                    if np.any(sp < omin) or np.any(sp > omax):
                        continue
                    if point_in_triangle_3d(sp, opA, opB, opC, on, eps=0.015):
                        sp_covered = True
                        break
                if not sp_covered:
                    covered_or_abutting = False
                    break
                covered_or_abutting = True

            if not covered_or_abutting:
                kept_faces.extend(F[tri_idx].tolist())
                total_faces_after += 1

        o["f"] = kept_faces

    print(f"Coplanar Face Deduplication: {total_faces_before} triangles -> {total_faces_after} clean triangles ({total_faces_before - total_faces_after} overlapping coplanar triangles removed).")

    # 2. 1D Interval-Splitting Coplanar & Buried Edge Clipper
    def clip_edge_coplanar_intervals(p0, p1, is_structural_solid):
        v = p1 - p0
        v_len = float(np.linalg.norm(v))
        if v_len < 1e-4:
            return []
        v_dir = v / v_len

        min_e = np.minimum(p0, p1) - tol
        max_e = np.maximum(p0, p1) + tol
        gx0, gy0, gz0 = int(min_e[0] // cell_size), int(min_e[1] // cell_size), int(min_e[2] // cell_size)
        gx1, gy1, gz1 = int(max_e[0] // cell_size), int(max_e[1] // cell_size), int(max_e[2] // cell_size)

        candidates = []
        seen_ids = set()
        for gx in range(gx0, gx1 + 1):
            for gy in range(gy0, gy1 + 1):
                for gz in range(gz0, gz1 + 1):
                    for entry in faces_by_cell.get((gx, gy, gz), ()):
                        eid = id(entry)
                        if eid not in seen_ids:
                            seen_ids.add(eid)
                            candidates.append(entry)

        t_splits = [0.0, 1.0]
        rel_faces = []
        for (_oi, _ti, n, d, pA, pB, pC, min_p, max_p, _area) in candidates:
            if np.any(max_e < min_p) or np.any(min_e > max_p):
                continue
            if abs(np.dot(n, v_dir)) < 0.05 and abs(np.dot(n, p0) - d) < tol:
                rel_faces.append((n, d, pA, pB, pC, min_p, max_p))
                for pt in (pA, pB, pC):
                    t_val = float(np.dot(pt - p0, v_dir) / v_len)
                    for delta in (-0.01 / v_len, 0.0, 0.01 / v_len):
                        td = t_val + delta
                        if 0.0 < td < 1.0:
                            t_splits.append(td)

        rel_boxes = []
        if is_structural_solid:
            for (_bi, bmin, bmax) in solid_boxes:
                if np.any(max_e < bmin - tol) or np.any(min_e > bmax + tol):
                    continue
                rel_boxes.append((bmin, bmax))
                for axis in range(3):
                    if abs(v[axis]) > 1e-4:
                        for bval in (bmin[axis], bmax[axis]):
                            t_val = float((bval - p0[axis]) / v[axis])
                            if 0.0 < t_val < 1.0:
                                t_splits.append(t_val)

        t_splits = sorted(set(round(t, 4) for t in t_splits))
        kept_intervals = []

        for idx in range(len(t_splits) - 1):
            ta, tb = t_splits[idx], t_splits[idx + 1]
            if (tb - ta) * v_len < 0.008:
                continue
            tm = 0.5 * (ta + tb)
            pm = p0 + tm * v

            # Test A: Is pm strictly buried inside any solid box?
            buried = False
            if is_structural_solid:
                for bmin, bmax in rel_boxes:
                    if np.all(pm > bmin + 0.015) and np.all(pm < bmax - 0.015):
                        buried = True
                        break
            if buried:
                continue

            # Test B: In any plane containing the edge, does coplanar surface exist on BOTH sides (+perp and -perp)?
            is_seam = False
            plane_groups = []
            for n, d, pA, pB, pC, min_p, max_p in rel_faces:
                if np.any(pm < min_p) or np.any(pm > max_p):
                    continue
                placed = False
                for pg_n, pg_list in plane_groups:
                    if np.dot(n, pg_n) > 0.96:
                        pg_list.append((n, pA, pB, pC))
                        placed = True
                        break
                if not placed:
                    plane_groups.append((n, [(n, pA, pB, pC)]))

            for pg_n, pg_list in plane_groups:
                perp = np.cross(pg_n, v_dir)
                p_norm = np.linalg.norm(perp)
                if p_norm < 1e-4:
                    continue
                perp = perp / p_norm
                pt_plus = pm + step * perp
                pt_minus = pm - step * perp

                has_plus = False
                has_minus = False
                for n, pA, pB, pC in pg_list:
                    if not has_plus and point_in_triangle_3d(pt_plus, pA, pB, pC, n, eps=0.012):
                        has_plus = True
                    if not has_minus and point_in_triangle_3d(pt_minus, pA, pB, pC, n, eps=0.012):
                        has_minus = True
                    if has_plus and has_minus:
                        break
                if has_plus and has_minus:
                    is_seam = True
                    break

            if not is_seam:
                if kept_intervals and abs(kept_intervals[-1][1] - ta) < 1e-3:
                    kept_intervals[-1][1] = tb
                else:
                    kept_intervals.append([ta, tb])

        result_segs = []
        for ta, tb in kept_intervals:
            if (tb - ta) * v_len >= 0.015:
                result_segs.append((p0 + ta * v, p0 + tb * v))
        return result_segs

    seen_global_edges = set()
    raw_edge_count = 0
    clean_edge_count = 0

    for o in objects_list:
        raw_e = o.get("e", [])
        clean_e = []
        is_structural_solid = (not o.get("passThrough")) and (o["voice"] not in ("ENTRANCE_GLASS", "FOYER_FRAMES", "SKYLIGHT_ROOF"))
        for i in range(0, len(raw_e), 6):
            raw_edge_count += 1
            p0 = np.array([raw_e[i], raw_e[i + 1], raw_e[i + 2]], dtype=np.float32)
            p1 = np.array([raw_e[i + 3], raw_e[i + 4], raw_e[i + 5]], dtype=np.float32)
            segs = clip_edge_coplanar_intervals(p0, p1, is_structural_solid)
            for s0, s1 in segs:
                k0 = (round(float(s0[0]), 2), round(float(s0[1]), 2), round(float(s0[2]), 2))
                k1 = (round(float(s1[0]), 2), round(float(s1[1]), 2), round(float(s1[2]), 2))
                edge_key = (min(k0, k1), max(k0, k1))
                if edge_key in seen_global_edges:
                    continue
                seen_global_edges.add(edge_key)
                clean_e.extend([
                    round(float(s0[0]), 3), round(float(s0[1]), 3), round(float(s0[2]), 3),
                    round(float(s1[0]), 3), round(float(s1[1]), 3), round(float(s1[2]), 3),
                ])
                clean_edge_count += 1
        o["e"] = clean_e

    print(f"1D Interval Coplanar Edge Clipping: {raw_edge_count} raw edges -> {clean_edge_count} clean non-coplanar edges.")


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
    seen_name_bbox = set()

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

        name = attr.Name or f"Arch_{i}"

        # Skip internal sealed elevator/service shaft dividers and buried floor ribs
        if name in INTERNAL_SEALED_SHAFT_NAMES or name.startswith("SM_Meso_Beam_FoyerFloorRib_"):
            continue

        bb = geom.GetBoundingBox()
        min_x = round(bb.Min.X / 100.0, 3)
        min_y = round(bb.Min.Z / 100.0, 3)
        min_z = round(-bb.Max.Y / 100.0, 3)
        max_x = round(bb.Max.X / 100.0, 3)
        max_y = round(bb.Max.Z / 100.0, 3)
        max_z = round(-bb.Min.Y / 100.0, 3)

        # Skip old smaller ground slab Obj 42 that is completely contained inside the enlarged ground slab Obj 659
        if name == "SM_Macro_FloorSlab_GroundLevel_Z000" and max_x < 120.0:
            continue

        # Skip exact duplicate objects (e.g. duplicate glass panes with identical name and bounding box)
        sig = (name, min_x, min_y, min_z, max_x, max_y, max_z)
        if sig in seen_name_bbox:
            continue
        seen_name_bbox.add(sig)

        verts, faces, raw_edges = extract_brep_mesh_and_raw_edges(geom)
        if not verts or not faces:
            continue

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

    # Apply global coplanar face deduplication + 1D interval coplanar edge clipping across all objects
    filter_all_coplanar_seams(exported_objects)

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

    print(f"Exported {len(exported_objects)} mirrored right-handed 3D objects with clean non-coplanar faces & edges -> {OUT_JS_PATH}")


if __name__ == "__main__":
    main()
