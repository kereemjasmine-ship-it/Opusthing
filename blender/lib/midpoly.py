"""Mid-poly modelling toolkit for Roblox-ready vehicles and props.

Smooth-shaded geometry built from swept profiles, lathed (revolved) profiles,
extruded outlines, lofts and bevelled boxes. Colours and PBR values come from
one small palette texture set (colour, metalness, roughness), so every mesh
has a single material that Roblox can show with a SurfaceAppearance.

Units: build in METRES (real-world sizes). export() converts to studs at
STUDS_PER_METRE (Roblox: 1 stud = 0.28 m).

Conventions:
  * Z up, the model faces -Y, it stands on z = 0. For a vehicle the left side
    (rider's left) is +X and the right side is -X.
  * Geometry goes into named groups; each group becomes one mesh object whose
    origin is the group's pivot (set with Model.group). Palette colours marked
    light=True go into their own "<Group>_Neon<Colour>" mesh.
  * Every shape takes `mirror=True` to add an X-mirrored copy as well.
"""

import math
import os
import sys

import bpy  # noqa: I001  (bpy must load before bmesh when used as a module)
import bmesh
from mathutils import Euler, Matrix, Vector

STUDS_PER_METRE = 1 / 0.28
MAX_TRIS_PER_MESH = 20000  # Roblox MeshPart limit
CELL = 16
SLOTS = 16
PAL_W, PAL_H = CELL * SLOTS, CELL
IDENTITY = Matrix.Identity(4)


def rot(rx=0.0, ry=0.0, rz=0.0):
    """Rotation matrix from XYZ Euler angles in degrees."""
    return Euler((math.radians(rx), math.radians(ry), math.radians(rz)), "XYZ").to_matrix().to_4x4()


def tr(x, y=None, z=None):
    """Translation matrix from a vector or three numbers."""
    v = Vector(x) if y is None else Vector((x, y, z))
    return Matrix.Translation(v)


def scl(x, y=None, z=None):
    """Scale matrix (one number = uniform)."""
    if y is None:
        y = z = x
    return Matrix.Diagonal((x, y, z, 1.0))


def look(origin, direction, up=(0, 0, 1)):
    """Matrix at `origin` whose local +Z points along `direction` (local +Y as close to `up` as possible)."""
    z = Vector(direction).normalized()
    upv = Vector(up)
    if abs(z.dot(upv.normalized())) > 0.999:
        upv = Vector((1, 0, 0)) if abs(z.x) < 0.9 else Vector((0, 1, 0))
    x = upv.cross(z).normalized()
    y = z.cross(x)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = Vector(origin)
    return m


def hex_rgb(h):
    return tuple(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))


def circle(radius, n=12, rx=None, start=0.0):
    """2D circle/ellipse points (counter-clockwise) for sweeps and lofts."""
    ry = radius
    rx = radius if rx is None else rx
    return [(rx * math.cos(start + 2 * math.pi * i / n), ry * math.sin(start + 2 * math.pi * i / n)) for i in range(n)]


def rounded_rect(w, h, r, corner_segments=3):
    """2D rounded rectangle (counter-clockwise), centred on the origin."""
    r = min(r, w / 2 - 1e-4, h / 2 - 1e-4)
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180),
                       (w / 2 - r, -h / 2 + r, 270)):
        for k in range(corner_segments + 1):
            a = math.radians(a0 + 90 * k / corner_segments)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def bezier(p0, p1, p2, p3=None, n=12):
    """Points along a quadratic (3 points) or cubic (4 points) Bezier curve."""
    p0, p1, p2 = Vector(p0), Vector(p1), Vector(p2)
    out = []
    for i in range(n + 1):
        t = i / n
        if p3 is None:
            out.append((1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t * t * p2)
        else:
            q3 = Vector(p3)
            out.append((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t * t * p2 + t ** 3 * q3)
    return out


class Palette:
    """Up to 16 materials: (name, hex, metallic, roughness) plus optional light=True entries."""

    def __init__(self, entries):
        self.entries = []
        for e in entries:
            name, hx, metal, rough = e[:4]
            light = bool(e[4]) if len(e) > 4 else False
            self.entries.append((name, hx, float(metal), float(rough), light))
        if len(self.entries) > SLOTS:
            raise ValueError(f"a palette holds at most {SLOTS} entries")
        self.slot = {e[0]: i for i, e in enumerate(self.entries)}

    def is_light(self, name):
        return self.entries[self.slot[name]][4]

    def suffix(self, name):
        return "Neon" + "".join(p.capitalize() for p in name.replace("light_", "").split("_"))


class Model:
    def __init__(self, name, palette):
        self.name = name
        self.palette = palette
        self.meshes = {}
        self.pivots = {}

    # -- bookkeeping ---------------------------------------------------------

    def group(self, name, pivot=(0, 0, 0)):
        """Declare a group (one mesh object) and its pivot / object origin."""
        self.pivots[name] = Vector(pivot)

    def _bm(self, name):
        if name not in self.meshes:
            bm = bmesh.new()
            bm.faces.layers.int.new("pal")
            self.meshes[name] = bm
        return self.meshes[name]

    def _merge(self, dst, src, slot):
        layer = dst.faces.layers.int["pal"]
        vmap = {v: dst.verts.new(v.co) for v in src.verts}
        for f in src.faces:
            try:
                nf = dst.faces.new([vmap[v] for v in f.verts])
            except ValueError:
                continue  # duplicate face
            nf[layer] = slot
            nf.smooth = f.smooth

    def commit(self, group, tmp, color, mirror=False, smooth=True, recalc=True):
        """Add a finished temporary bmesh (world coordinates) to a group in `color`."""
        if color not in self.palette.slot:
            raise KeyError(f"colour {color!r} is not in the palette")
        bmesh.ops.remove_doubles(tmp, verts=tmp.verts, dist=1e-6)
        if recalc and tmp.faces:
            bmesh.ops.recalc_face_normals(tmp, faces=tmp.faces)
        for f in tmp.faces:
            f.smooth = smooth
        name = f"{group}_{self.palette.suffix(color)}" if self.palette.is_light(color) else group
        dst = self._bm(name)
        slot = self.palette.slot[color]
        self._merge(dst, tmp, slot)
        if mirror:
            bmesh.ops.scale(tmp, vec=(-1, 1, 1), verts=tmp.verts)
            bmesh.ops.reverse_faces(tmp, faces=tmp.faces)
            self._merge(dst, tmp, slot)
        tmp.free()

    # -- shapes ----------------------------------------------------------------

    def sweep(self, group, path, profile, color, scales=None, lateral=(1, 0, 0), closed=False, caps=True,
              mirror=False, smooth=True, twist=0.0):
        """Sweep a 2D profile [(u, v), ...] along a 3D path.

        u maps to the `lateral` hint direction (projected square to the path), v to path x u.
        scales: per-point float or (su, sv). closed: the path is a loop (rings, tyres).
        """
        pts = [Vector(p) for p in path]
        n = len(pts)
        if n < 2:
            raise ValueError("sweep needs at least two path points")
        tangents = []
        for i in range(n):
            if closed:
                t = pts[(i + 1) % n] - pts[(i - 1) % n]
            else:
                t = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
            tangents.append(t.normalized())
        lat = Vector(lateral)
        a = lat - tangents[0] * lat.dot(tangents[0])
        if a.length < 1e-6:
            a = Vector((0, 0, 1)) - tangents[0] * tangents[0].z
            if a.length < 1e-6:
                a = Vector((0, 1, 0)) - tangents[0] * tangents[0].y
        a.normalize()
        axes = [a]
        for i in range(1, n):
            q = tangents[i - 1].rotation_difference(tangents[i])
            ai = q @ axes[-1]
            ai = (ai - tangents[i] * ai.dot(tangents[i])).normalized()
            axes.append(ai)
        tmp = bmesh.new()
        rings = []
        m = len(profile)
        for i, p in enumerate(pts):
            s = 1.0 if scales is None else scales[i]
            su, sv = (s, s) if isinstance(s, (int, float)) else s
            u_ax = axes[i]
            v_ax = tangents[i].cross(u_ax)
            if twist:
                ang = math.radians(twist) * i / max(n - 1, 1)
                u_ax, v_ax = (u_ax * math.cos(ang) + v_ax * math.sin(ang), v_ax * math.cos(ang) - u_ax * math.sin(ang))
            rings.append([tmp.verts.new(p + u_ax * (u * su) + v_ax * (v * sv)) for (u, v) in profile])
        segs = n if closed else n - 1
        for i in range(segs):
            r0, r1 = rings[i], rings[(i + 1) % n]
            for j in range(m):
                tmp.faces.new((r0[j], r0[(j + 1) % m], r1[(j + 1) % m], r1[j]))
        if caps and not closed:
            tmp.faces.new(list(reversed(rings[0])))
            tmp.faces.new(rings[-1])
        self.commit(group, tmp, color, mirror, smooth)

    def tube(self, group, path, radius, color, segments=12, radii=None, closed=False, caps=True, mirror=False):
        """Round tube along a path; radii gives a per-point radius."""
        prof = circle(1.0, segments)
        scales = [radius] * len(path) if radii is None else list(radii)
        self.sweep(group, path, prof, color, scales=scales, closed=closed, caps=caps, mirror=mirror)

    def lathe(self, group, profile, color, matrix=IDENTITY, segments=32, closed=False, mirror=False, smooth=True):
        """Revolve a 2D profile [(radius, height), ...] around local Z (wheels, hubs, discs, lenses).

        closed=True joins the last profile point back to the first (a tyre cross-section).
        """
        tmp = bmesh.new()
        rings = []
        for k in range(segments):
            ang = 2 * math.pi * k / segments
            c, s = math.cos(ang), math.sin(ang)
            rings.append([tmp.verts.new(matrix @ Vector((r * c, r * s, h))) for (r, h) in profile])
        m = len(profile)
        last = m if closed else m - 1
        for k in range(segments):
            r0, r1 = rings[k], rings[(k + 1) % segments]
            for j in range(last):
                j1 = (j + 1) % m
                quad = [r0[j], r1[j], r1[j1], r0[j1]]
                uniq = []
                for v in quad:
                    if all((v.co - u.co).length > 1e-7 for u in uniq):
                        uniq.append(v)
                if len(uniq) >= 3:
                    try:
                        tmp.faces.new(uniq)
                    except ValueError:
                        pass
        self.commit(group, tmp, color, mirror, smooth)

    def extrude(self, group, outline, thickness, color, matrix=IDENTITY, bevel=0.0, bevel_segments=2, mirror=False,
                smooth=True):
        """A flat 2D outline [(x, y), ...] in local XY, extruded `thickness` along local Z (centred).

        bevel rounds every edge by that radius (metres) for a moulded look.
        """
        tmp = bmesh.new()
        lo = [tmp.verts.new((x, y, -thickness / 2)) for (x, y) in outline]
        hi = [tmp.verts.new((x, y, thickness / 2)) for (x, y) in outline]
        n = len(outline)
        tmp.faces.new(list(reversed(lo)))
        tmp.faces.new(hi)
        for i in range(n):
            j = (i + 1) % n
            tmp.faces.new((lo[i], lo[j], hi[j], hi[i]))
        bmesh.ops.recalc_face_normals(tmp, faces=tmp.faces)
        if bevel > 0:
            bmesh.ops.bevel(tmp, geom=list(tmp.edges), offset=min(bevel, thickness * 0.45), offset_type="OFFSET",
                            segments=bevel_segments, profile=0.5, affect="EDGES", clamp_overlap=True)
        bmesh.ops.transform(tmp, matrix=matrix, verts=tmp.verts)
        self.commit(group, tmp, color, mirror, smooth)

    def box(self, group, size, color, matrix=IDENTITY, bevel=0.004, bevel_segments=2, mirror=False, smooth=True):
        """A box of `size` (x, y, z) centred on matrix's origin, with rounded edges."""
        tmp = bmesh.new()
        bmesh.ops.create_cube(tmp, size=1.0, matrix=Matrix.Diagonal((size[0], size[1], size[2], 1.0)))
        if bevel > 0:
            bmesh.ops.bevel(tmp, geom=list(tmp.verts) + list(tmp.edges), offset=min(bevel, min(size) * 0.45),
                            offset_type="OFFSET", segments=bevel_segments, profile=0.5, affect="EDGES",
                            clamp_overlap=True)
        bmesh.ops.transform(tmp, matrix=matrix, verts=tmp.verts)
        self.commit(group, tmp, color, mirror, smooth)

    def cylinder(self, group, radius, depth, color, matrix=IDENTITY, segments=16, bevel=0.0, radius2=None,
                 mirror=False, smooth=True):
        """A cylinder (or cone with radius2) along local Z, centred on matrix's origin."""
        tmp = bmesh.new()
        bmesh.ops.create_cone(tmp, cap_ends=True, cap_tris=False, segments=segments, radius1=radius,
                              radius2=radius if radius2 is None else radius2, depth=depth)
        if bevel > 0:
            caps = [e for e in tmp.edges if all(abs(abs(v.co.z) - depth / 2) < 1e-6 for v in e.verts)
                    and abs(e.verts[0].co.z - e.verts[1].co.z) < 1e-6]
            bmesh.ops.bevel(tmp, geom=caps, offset=bevel, offset_type="OFFSET", segments=2, profile=0.5,
                            affect="EDGES", clamp_overlap=True)
        bmesh.ops.transform(tmp, matrix=matrix, verts=tmp.verts)
        self.commit(group, tmp, color, mirror, smooth)

    def loft(self, group, sections, color, closed=True, caps=True, mirror=False, smooth=True):
        """Skin a surface through cross-section loops [[Vector, ...], ...] (same point count each).

        closed: each section is a closed loop. caps: close the first and last sections.
        """
        tmp = bmesh.new()
        rings = [[tmp.verts.new(Vector(p)) for p in sec] for sec in sections]
        m = len(rings[0])
        for r in rings:
            if len(r) != m:
                raise ValueError("loft sections need the same number of points")
        cols = m if closed else m - 1
        for i in range(len(rings) - 1):
            r0, r1 = rings[i], rings[i + 1]
            for j in range(cols):
                j1 = (j + 1) % m
                tmp.faces.new((r0[j], r0[j1], r1[j1], r1[j]))
        if caps and closed:
            tmp.faces.new(list(reversed(rings[0])))
            tmp.faces.new(rings[-1])
        self.commit(group, tmp, color, mirror, smooth)

    def mesh(self, group, verts, faces, color, matrix=IDENTITY, mirror=False, smooth=True):
        """Raw geometry: verts [(x, y, z)], faces [(i, j, k, ...)]."""
        tmp = bmesh.new()
        vs = [tmp.verts.new(matrix @ Vector(v)) for v in verts]
        for f in faces:
            try:
                tmp.faces.new([vs[i] for i in f])
            except ValueError:
                pass
        self.commit(group, tmp, color, mirror, smooth)

    # -- output ----------------------------------------------------------------

    def _palette_images(self, out_dir):
        os.makedirs(os.path.join(out_dir, "export"), exist_ok=True)
        maps = {}
        for kind in ("Color", "Metalness", "Roughness", "Emission"):
            img = bpy.data.images.new(f"{self.name}_{kind}", PAL_W, PAL_H, alpha=False)
            px = [0.0] * (PAL_W * PAL_H * 4)
            for slot, (_, hx, metal, rough, light) in enumerate(self.palette.entries):
                r, g, b = hex_rgb(hx)
                val = {"Color": (r, g, b), "Metalness": (metal,) * 3, "Roughness": (rough,) * 3,
                       "Emission": (r, g, b) if light else (0.0, 0.0, 0.0)}[kind]
                for y in range(PAL_H):
                    for x in range(slot * CELL, (slot + 1) * CELL):
                        i = (y * PAL_W + x) * 4
                        px[i : i + 4] = (*val, 1.0)
            img.pixels = px
            if kind != "Color":
                img.colorspace_settings.name = "Non-Color"
            img.filepath_raw = os.path.join(out_dir, "export", f"{self.name}_{kind}.png")
            img.file_format = "PNG"
            img.save()
            img.pack()
            maps[kind] = img
        return maps

    def _material(self, maps):
        mat = bpy.data.materials.new(f"{self.name}_Mat")
        mat.use_nodes = True
        nt = mat.node_tree
        bsdf = nt.nodes["Principled BSDF"]
        y = 300
        for kind, socket in (("Color", "Base Color"), ("Metalness", "Metallic"), ("Roughness", "Roughness"),
                             ("Emission", "Emission Color")):
            tex = nt.nodes.new("ShaderNodeTexImage")
            tex.image = maps[kind]
            tex.interpolation = "Closest"
            tex.location = (-500, y)
            y -= 280
            out = tex.outputs["Color"]
            if kind in ("Metalness", "Roughness"):
                sep = nt.nodes.new("ShaderNodeSeparateColor")
                sep.location = (-220, y + 280)
                nt.links.new(out, sep.inputs[0])
                out = sep.outputs[0]
            nt.links.new(out, bsdf.inputs[socket])
        bsdf.inputs["Emission Strength"].default_value = 4.0
        return mat

    def finish(self, out_dir, smooth_angle=35.0):
        coll = bpy.data.collections.new(self.name)
        bpy.context.scene.collection.children.link(coll)
        root = bpy.data.objects.new(self.name, None)
        root.empty_display_type = "PLAIN_AXES"
        coll.objects.link(root)
        maps = self._palette_images(out_dir)
        mat = self._material(maps)
        objects = []
        for name in sorted(self.meshes):
            bm = self.meshes[name]
            group = name.split("_")[0]
            pivot = self.pivots.get(group, Vector((0, 0, 0)))
            big = [f for f in bm.faces if len(f.verts) > 4]
            if big:
                bmesh.ops.triangulate(bm, faces=big, quad_method="BEAUTY", ngon_method="BEAUTY")
            bmesh.ops.translate(bm, vec=-pivot, verts=bm.verts)
            layer = bm.faces.layers.int["pal"]
            slots = [f[layer] for f in bm.faces]
            smooth = [f.smooth for f in bm.faces]
            me = bpy.data.meshes.new(name)
            bm.to_mesh(me)
            bm.free()
            uv = me.uv_layers.new(name="UVMap")
            for poly, slot, sm in zip(me.polygons, slots, smooth):
                coord = ((slot + 0.5) * CELL / PAL_W, 0.5)
                for li in poly.loop_indices:
                    uv.data[li].uv = coord
                poly.use_smooth = sm
            me.set_sharp_from_angle(angle=math.radians(smooth_angle))
            me.materials.append(mat)
            ob = bpy.data.objects.new(name, me)
            ob.location = pivot
            ob.parent = root
            coll.objects.link(ob)
            objects.append(ob)
        self.meshes = {}
        return root, objects


# -- reporting, export, studio, render ---------------------------------------------


def bounds(objects):
    bpy.context.view_layer.update()
    pts = [ob.matrix_world @ Vector(c) for ob in objects for c in ob.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    return lo, hi


def report(objects, budgets=None):
    """Print triangles per mesh (flagging limits) and the overall size."""
    total = 0
    info = {}
    for ob in objects:
        tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
        info[ob.name] = tris
        total += tris
        group = ob.name.split("_")[0]
        flag = ""
        if tris > MAX_TRIS_PER_MESH:
            flag = "  <-- over the Roblox 20k MeshPart limit"
        elif budgets and group in budgets and tris > budgets[group]:
            flag = f"  <-- over this group's budget of {budgets[group]}"
        print(f"  {ob.name:<24} {tris:>6} tris{flag}")
    lo, hi = bounds(objects)
    size = hi - lo
    print(f"  {'TOTAL':<24} {total:>6} tris in {len(objects)} meshes")
    print(f"  size (m): {size.x:.3f} wide x {size.y:.3f} long x {size.z:.3f} tall; bottom z = {lo.z:.4f}; "
          f"= {size.y * STUDS_PER_METRE:.2f} studs long")
    return {"total_tris": total, "meshes": info, "size_m": [round(size.x, 3), round(size.y, 3), round(size.z, 3)],
            "bottom_z": round(lo.z, 4)}


def export(name, root, objects, out_dir):
    """Write export/<name>.fbx and .glb in studs (geometry scaled by STUDS_PER_METRE)."""
    export_dir = os.path.join(out_dir, "export")
    os.makedirs(export_dir, exist_ok=True)
    k = STUDS_PER_METRE
    for ob in objects:
        ob.data.transform(scl(k))
        ob.location = ob.location * k
    bpy.context.view_layer.update()
    for ob in bpy.context.scene.objects:
        ob.select_set(ob == root or ob in objects)
    bpy.context.view_layer.objects.active = root
    try:
        bpy.ops.export_scene.fbx(
            filepath=os.path.join(export_dir, f"{name}.fbx"), use_selection=True,
            object_types={"EMPTY", "MESH"}, mesh_smooth_type="OFF", path_mode="COPY", embed_textures=True,
            apply_scale_options="FBX_SCALE_UNITS", bake_anim=False,
        )
        bpy.ops.export_scene.gltf(filepath=os.path.join(export_dir, f"{name}.glb"), export_format="GLB",
                                  use_selection=True)
    finally:
        for ob in objects:
            ob.data.transform(scl(1 / k))
            ob.location = ob.location / k
        bpy.context.view_layer.update()


def build_studio(objects, backdrop=(0.62, 0.64, 0.68)):
    """A soft grey studio with a reflective floor and cameras framed on `objects`.

    Cameras: CamHero (front-left 3/4), CamSide (from the left side, front of the
    vehicle on the left of the frame), CamFront, CamRear (rear-right 3/4).
    """
    scene = bpy.context.scene
    stage = bpy.data.collections.new("Stage")
    scene.collection.children.link(stage)

    world = bpy.data.worlds.new("Studio")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*backdrop, 1)
    bg.inputs["Strength"].default_value = 0.6
    scene.world = world

    floor_mat = bpy.data.materials.new("Floor")
    floor_mat.use_nodes = True
    fb = floor_mat.node_tree.nodes["Principled BSDF"]
    fb.inputs["Base Color"].default_value = (*backdrop, 1)
    fb.inputs["Roughness"].default_value = 0.35
    me = bpy.data.meshes.new("Floor")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=60)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(floor_mat)
    stage.objects.link(bpy.data.objects.new("Floor", me))

    lo, hi = bounds(objects)
    centre = (lo + hi) / 2
    radius = max((hi - lo).length / 2, 0.2)

    def light(name, energy, direction, size, color=(1, 1, 1)):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy * radius ** 2
        data.size = size * radius
        data.color = color
        ob = bpy.data.objects.new(name, data)
        ob.location = centre + Vector(direction).normalized() * radius * 3.0
        ob.rotation_euler = (centre - ob.location).to_track_quat("-Z", "Y").to_euler()
        ob.visible_glossy = False
        stage.objects.link(ob)

    light("Key", 260, (0.7, -0.8, 0.9), 1.6, (1.0, 0.97, 0.93))
    light("Fill", 110, (-0.9, -0.3, 0.4), 2.0, (0.9, 0.94, 1.0))
    light("Rim", 220, (-0.2, 0.9, 0.7), 1.2)
    light("Top", 120, (0.0, 0.0, 1.0), 2.5)

    cams = {}
    fov = 2 * math.atan(18 / 70)
    distance = radius / math.sin(fov / 2) * 1.04
    for cam_name, direction in (("CamHero", (0.62, -0.72, 0.30)), ("CamSide", (1, 0, 0.04)),
                                ("CamFront", (0.0, -1, 0.10)), ("CamRear", (-0.6, 0.75, 0.28))):
        data = bpy.data.cameras.new(cam_name)
        data.lens = 70
        ob = bpy.data.objects.new(cam_name, data)
        ob.location = centre + Vector(direction).normalized() * distance
        ob.rotation_euler = (centre - ob.location).to_track_quat("-Z", "Y").to_euler()
        stage.objects.link(ob)
        cams[cam_name] = ob
    scene.camera = cams["CamHero"]
    return cams


def setup_render(samples, res_x, res_y):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]

    def opt(flag, default, cast=str):
        return cast(argv[argv.index(flag) + 1]) if flag in argv else default

    return {
        "render": "--render" in argv,
        "samples": opt("--samples", 64, int),
        "res": opt("--res", 1200, int),
        "views": opt("--views", "hero,side,front,rear").split(","),
        "only": [s for s in opt("--only", "").split(",") if s],
        "no_export": "--no-export" in argv,
    }
