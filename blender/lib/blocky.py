"""Shared builder for the blocky, studded "void pet" style of the Void Hydra.

Every pet script builds its model from bevelled blocks (optionally studded on
their local +Z face), tapered blocks, diamonds and rings, in the same design
units and stud size as build_void_hydra.py, so the whole pet family matches.

A pet script looks like:

    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
    import blocky
    from blocky import rot, tr, Vector

    PALETTE = blocky.Palette(blocky.FAMILY + [("neon_cyan", "4de1ff")], neon=["neon_cyan"])

    def build(b):            # b is a blocky.Builder
        b.pivot("Body", (0, 0, 0))
        b.block("Body", (2, 3, 1.6), tr(0, 0, 2), color="hide", studs=True)
        ...

    if __name__ == "__main__":
        blocky.main("VoidPup", PALETTE, build, os.path.dirname(os.path.abspath(__file__)))

Run:  python build.py [--render] [--samples N] [--res PX]   (bpy module)
  or: blender -b -P build.py -- [--render] ...

Conventions (they keep ImportedPet.lua working for every pet):
  * Z up, the pet faces -Y, it stands on z = 0 and is centred on the origin.
  * Design units: SCALE (0.4) studs per unit, stud pitch 0.5 units. Never change
    these per pet, or the studs stop matching the hydra.
  * A glowing colour gets its own mesh named "<Group>_Neon<Colour>" so it can
    use Roblox's Neon material; everything else lives in "<Group>".
  * Each group's object origin is its pivot (set with Builder.pivot).
"""

import math
import os
import sys

import bpy  # noqa: I001  (bpy must load before bmesh when used as a module)
import bmesh
from mathutils import Euler, Matrix, Vector

SCALE = 0.4  # studs per design unit (same as the Void Hydra)
STUD_PITCH = 0.5
STUD_RADIUS = 0.15
STUD_HEIGHT = 0.12
BEVEL = 0.05
CELL = 16  # each palette colour is a CELL x CELL square, so mipmaps stay clean
SLOTS = 16
PAL_W, PAL_H = CELL * SLOTS, CELL
MAX_TRIS_PER_MESH = 20000  # Roblox MeshPart limit

# Base colours shared by the whole void pet family (the Void Hydra's body colours).
FAMILY = [
    ("void", "0b0710"),  # claws, deepest shadow
    ("hide", "1c1326"),  # main body blocks
    ("hidelight", "2a1b3d"),  # alternating body blocks
    ("plate", "3d2659"),  # armour, horns, spikes
    ("belly", "5a3a85"),  # bellies, jaws, undersides
    ("bone", "e8dcf5"),  # teeth, horn tips, claws tips
]


def rot(rx=0.0, ry=0.0, rz=0.0):
    """Rotation matrix from XYZ Euler angles in degrees."""
    return Euler((math.radians(rx), math.radians(ry), math.radians(rz)), "XYZ").to_matrix().to_4x4()


def tr(x, y=None, z=None):
    """Translation matrix from a vector or three numbers."""
    v = Vector(x) if y is None else Vector((x, y, z))
    return Matrix.Translation(v)


def hex_rgb(h):
    return tuple(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


class Palette:
    """Up to 16 named colours; the names listed in `neon` glow and get their own meshes."""

    def __init__(self, colors, neon=()):
        self.colors = list(colors)
        if len(self.colors) > SLOTS:
            raise ValueError(f"a palette holds at most {SLOTS} colours")
        self.slot = {name: i for i, (name, _) in enumerate(self.colors)}
        self.neon = set(neon)
        missing = self.neon - set(self.slot)
        if missing:
            raise ValueError(f"neon colours not in the palette: {sorted(missing)}")

    def suffix(self, name):
        base = name[5:] if name.startswith("neon_") else name
        return "Neon" + "".join(part.capitalize() for part in base.split("_"))

    def hex(self, name):
        return self.colors[self.slot[name]][1]


class Builder:
    def __init__(self, name, palette):
        self.name = name
        self.palette = palette
        self.meshes = {}  # object name -> bmesh
        self.pivots = {}  # group -> Vector (design units)

    # -- bookkeeping -------------------------------------------------------

    def pivot(self, group, position):
        """Where the group's object origin goes (a joint to rotate it around)."""
        self.pivots[group] = Vector(position)

    def _bm(self, name):
        if name not in self.meshes:
            bm = bmesh.new()
            bm.faces.layers.int.new("pal")
            self.meshes[name] = bm
        return self.meshes[name]

    def _commit(self, group, tmp, color):
        if color not in self.palette.slot:
            raise KeyError(f"colour {color!r} is not in the palette")
        name = f"{group}_{self.palette.suffix(color)}" if color in self.palette.neon else group
        dst = self._bm(name)
        layer = dst.faces.layers.int["pal"]
        vmap = {v: dst.verts.new(v.co) for v in tmp.verts}
        for f in tmp.faces:
            nf = dst.faces.new([vmap[v] for v in f.verts])
            nf[layer] = self.palette.slot[color]
        tmp.free()

    @staticmethod
    def _bevel(tmp, size, bevel):
        offset = min(BEVEL if bevel is None else bevel, min(size) * 0.18)
        if offset > 0:
            bmesh.ops.bevel(
                tmp, geom=list(tmp.verts) + list(tmp.edges), offset=offset, offset_type="OFFSET",
                segments=1, profile=0.5, affect="EDGES", clamp_overlap=True,
            )

    @staticmethod
    def _studs(tmp, matrix, sx, sy, sz, keep):
        if sx < 0.4 or sy < 0.4:
            return
        nx, ny = max(1, int(sx // STUD_PITCH)), max(1, int(sy // STUD_PITCH))
        for i in range(nx):
            for j in range(ny):
                lx = (i - (nx - 1) / 2) * STUD_PITCH
                ly = (j - (ny - 1) / 2) * STUD_PITCH
                if keep and not keep(lx, ly):
                    continue
                bmesh.ops.create_cone(
                    tmp, cap_ends=True, cap_tris=False, segments=10, radius1=STUD_RADIUS,
                    radius2=STUD_RADIUS, depth=STUD_HEIGHT,
                    matrix=matrix @ tr(lx, ly, sz / 2 + STUD_HEIGHT / 2),
                )

    # -- shapes --------------------------------------------------------------

    def block(self, group, size, matrix, color="hide", studs=False, keep=None, bevel=None):
        """A bevelled box of `size` (x, y, z) placed by `matrix`.

        studs=True puts studs on its local +Z face on the shared 0.5 pitch;
        keep(lx, ly) -> bool can skip individual stud positions.
        """
        sx, sy, sz = size
        tmp = bmesh.new()
        bmesh.ops.create_cube(tmp, size=1.0, matrix=matrix @ Matrix.Diagonal((sx, sy, sz, 1.0)))
        self._bevel(tmp, size, bevel)
        if studs:
            self._studs(tmp, matrix, sx, sy, sz, keep)
        self._commit(group, tmp, color)

    def taper(self, group, size, matrix, color="hide", top=(0.5, 0.5), shift=(0.0, 0.0), bevel=None):
        """A box whose +Z face is scaled by `top` and moved by `shift` (fractions of size).

        Good for ears, beaks, claws, horns, crystals and wing tips.
        """
        sx, sy, sz = size
        tmp = bmesh.new()
        bmesh.ops.create_cube(tmp, size=1.0)
        for v in tmp.verts:
            if v.co.z > 0:
                v.co.x = v.co.x * top[0] + shift[0]
                v.co.y = v.co.y * top[1] + shift[1]
        bmesh.ops.transform(tmp, matrix=matrix @ Matrix.Diagonal((sx, sy, sz, 1.0)), verts=tmp.verts)
        self._bevel(tmp, (sx * min(1.0, max(top[0], 0.3)), sy * min(1.0, max(top[1], 0.3)), sz), bevel)
        self._commit(group, tmp, color)

    def diamond(self, group, s, matrix, color):
        """A cube turned 45 degrees about X: spikes, gems, rune studs."""
        self.block(group, (s, s, s), matrix @ rot(45, 0, 0), color=color)

    def prism(self, group, radius, depth, matrix, color="hide", segments=8, bevel=None):
        """A chunky n-sided prism along local Z (pupils, rollers, orbs, gem faces)."""
        tmp = bmesh.new()
        bmesh.ops.create_cone(
            tmp, cap_ends=True, cap_tris=False, segments=segments, radius1=radius, radius2=radius,
            depth=depth, matrix=matrix,
        )
        self._bevel(tmp, (radius, radius, depth), bevel if bevel is not None else 0.02)
        self._commit(group, tmp, color)

    def ring(self, group, matrix, radius, n, depth, thickness, color, gap=1.08):
        """A ring of n blocks around the local Z axis of `matrix` (collars, halos, base circles).

        gap > 1 makes the blocks touch; gap < 1 leaves segment gaps like the hydra's circle.
        """
        chord = 2 * math.pi * radius / n * gap
        for k in range(n):
            m = matrix @ rot(0, 0, k * 360 / n) @ tr(0, radius, 0)
            self.block(group, (chord, thickness, depth), m, color=color)

    # -- output ----------------------------------------------------------------

    def _palette_image(self, out_dir):
        img = bpy.data.images.new(f"{self.name}_Palette", PAL_W, PAL_H, alpha=False)
        px = [0.0] * (PAL_W * PAL_H * 4)
        for slot, (_, hx) in enumerate(self.palette.colors):
            r, g, b = hex_rgb(hx)
            for y in range(PAL_H):
                for x in range(slot * CELL, (slot + 1) * CELL):
                    i = (y * PAL_W + x) * 4
                    px[i : i + 4] = (r, g, b, 1.0)
        img.pixels = px
        os.makedirs(os.path.join(out_dir, "export"), exist_ok=True)
        img.filepath_raw = os.path.join(out_dir, "export", f"{self.name}_Palette.png")
        img.file_format = "PNG"
        img.save()
        img.pack()
        return img

    def _material(self, name, img, emission):
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        nt = mat.node_tree
        bsdf = nt.nodes["Principled BSDF"]
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = img
        tex.interpolation = "Closest"
        tex.location = (-400, 200)
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = 0.4
        if emission:
            nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
            bsdf.inputs["Emission Strength"].default_value = emission
        return mat

    def finish(self, out_dir):
        coll = bpy.data.collections.new(self.name)
        bpy.context.scene.collection.children.link(coll)
        root = bpy.data.objects.new(self.name, None)
        root.empty_display_type = "PLAIN_AXES"
        coll.objects.link(root)

        img = self._palette_image(out_dir)
        body_mat = self._material(f"{self.name}_Body", img, 0.0)
        neon_mat = self._material(f"{self.name}_Neon", img, 3.0)

        objects = []
        for name in sorted(self.meshes):
            bm = self.meshes[name]
            group = name.split("_")[0]
            pivot = self.pivots.get(group, Vector((0, 0, 0)))
            bmesh.ops.translate(bm, vec=-pivot, verts=bm.verts)
            bmesh.ops.scale(bm, vec=(SCALE, SCALE, SCALE), verts=bm.verts)
            layer = bm.faces.layers.int["pal"]
            slots = [f[layer] for f in bm.faces]
            me = bpy.data.meshes.new(name)
            bm.to_mesh(me)
            bm.free()
            uv = me.uv_layers.new(name="UVMap")
            for poly, slot in zip(me.polygons, slots):
                coord = ((slot + 0.5) * CELL / PAL_W, 0.5)
                for li in poly.loop_indices:
                    uv.data[li].uv = coord
            me.materials.append(neon_mat if "_Neon" in name else body_mat)
            ob = bpy.data.objects.new(name, me)
            ob.location = pivot * SCALE
            ob.parent = root
            coll.objects.link(ob)
            objects.append(ob)
        self.meshes = {}
        return root, objects


# -- reporting, export, stage, render ---------------------------------------------


def bounds(objects):
    pts = [ob.matrix_world @ Vector(c) for ob in objects for c in ob.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    return lo, hi


def report(name, objects):
    """Print triangle counts and size in studs; returns a dict for the build log."""
    bpy.context.view_layer.update()
    total = 0
    meshes = {}
    for ob in objects:
        tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
        meshes[ob.name] = tris
        total += tris
        flag = "  <-- over the Roblox MeshPart limit" if tris > MAX_TRIS_PER_MESH else ""
        print(f"  {ob.name:<26} {tris:>6} tris{flag}")
    lo, hi = bounds(objects)
    size = hi - lo
    print(f"  {'TOTAL':<26} {total:>6} tris in {len(objects)} meshes")
    print(f"  size (studs): {size.x:.2f} wide x {size.y:.2f} deep x {size.z:.2f} tall; "
          f"bottom z = {lo.z:.3f}, centre x,y = ({(lo.x + hi.x) / 2:.2f}, {(lo.y + hi.y) / 2:.2f})")
    return {"name": name, "total_tris": total, "meshes": meshes,
            "size_studs": [round(size.x, 2), round(size.y, 2), round(size.z, 2)], "bottom_z": round(lo.z, 3)}


def export(name, root, objects, out_dir):
    export_dir = os.path.join(out_dir, "export")
    os.makedirs(export_dir, exist_ok=True)
    for ob in bpy.context.scene.objects:
        ob.select_set(ob == root or ob in objects)
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.fbx(
        filepath=os.path.join(export_dir, f"{name}.fbx"), use_selection=True,
        object_types={"EMPTY", "MESH"}, mesh_smooth_type="FACE", path_mode="COPY",
        embed_textures=True, apply_scale_options="FBX_SCALE_UNITS", bake_anim=False,
    )
    bpy.ops.export_scene.gltf(filepath=os.path.join(export_dir, f"{name}.glb"), export_format="GLB",
                              use_selection=True)


def build_stage(objects, rim=(1.0, 0.35, 1.0), rim2=(0.6, 0.35, 1.0)):
    """Dark void stage like the hydra renders, with cameras framed on `objects`."""
    scene = bpy.context.scene
    stage = bpy.data.collections.new("Stage")
    scene.collection.children.link(stage)

    world = bpy.data.worlds.new("Void")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.004, 0.002, 0.008, 1)
    scene.world = world

    ground_mat = bpy.data.materials.new("Ground")
    ground_mat.use_nodes = True
    gb = ground_mat.node_tree.nodes["Principled BSDF"]
    gb.inputs["Base Color"].default_value = (0.006, 0.004, 0.01, 1)
    gb.inputs["Roughness"].default_value = 0.22
    me = bpy.data.meshes.new("Ground")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=200)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(ground_mat)
    ground = bpy.data.objects.new("Ground", me)
    stage.objects.link(ground)

    lo, hi = bounds(objects)
    centre = (lo + hi) / 2
    radius = max((hi - lo).length / 2, 0.5)

    def light(name, energy, color, direction, size):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy * (radius / 3.0) ** 2
        data.color = color
        data.size = size * radius / 3.0
        ob = bpy.data.objects.new(name, data)
        ob.location = centre + Vector(direction).normalized() * radius * 3.2
        ob.rotation_euler = (centre - ob.location).to_track_quat("-Z", "Y").to_euler()
        ob.visible_glossy = False
        stage.objects.link(ob)

    light("Key", 850, (0.85, 0.8, 1.0), (-5, -7, 7), 5)
    light("Rim", 650, rim, (5, 7, 6), 4)
    light("Rim2", 300, rim2, (-6, 6, 3), 4)

    cams = {}
    fov = 2 * math.atan(18 / 50)  # 50 mm lens on a 36 mm sensor
    distance = radius / math.sin(fov / 2) * 1.08
    for cam_name, direction in (("CamHero", (0.52, -0.82, 0.3)), ("CamFront", (0, -1, 0.12)),
                                ("CamSide", (1, 0.04, 0.12))):
        data = bpy.data.cameras.new(cam_name)
        data.lens = 50
        ob = bpy.data.objects.new(cam_name, data)
        ob.location = centre + Vector(direction).normalized() * distance
        ob.rotation_euler = (centre - ob.location).to_track_quat("-Z", "Y").to_euler()
        stage.objects.link(ob)
        cams[cam_name] = ob
    scene.camera = cams["CamHero"]
    return cams


def setup_render(samples, res):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x = res
    scene.render.resolution_y = res
    scene.view_settings.view_transform = "Standard"  # keeps the neon saturated

    ng = bpy.data.node_groups.new("Bloom", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    rl = ng.nodes.new("CompositorNodeRLayers")
    glare = ng.nodes.new("CompositorNodeGlare")
    glare.inputs["Type"].default_value = "Bloom"
    glare.inputs["Quality"].default_value = "High"
    glare.inputs["Threshold"].default_value = 1.0
    glare.inputs["Strength"].default_value = 0.7
    glare.inputs["Size"].default_value = 0.6
    out = ng.nodes.new("NodeGroupOutput")
    ng.links.new(rl.outputs["Image"], glare.inputs["Image"])
    ng.links.new(glare.outputs["Image"], out.inputs[0])
    scene.compositing_node_group = ng


def main(name, palette, build, out_dir, rim=(1.0, 0.35, 1.0), rim2=(0.6, 0.35, 1.0)):
    """Build, report, export (.blend, .fbx, .glb, palette) and optionally render a pet."""
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    do_render = "--render" in argv
    samples = int(argv[argv.index("--samples") + 1]) if "--samples" in argv else 48
    res = int(argv[argv.index("--res") + 1]) if "--res" in argv else 900
    views = argv[argv.index("--views") + 1].split(",") if "--views" in argv else ["hero", "front", "side"]

    bpy.ops.wm.read_factory_settings(use_empty=True)
    builder = Builder(name, palette)
    build(builder)
    root, objects = builder.finish(out_dir)
    info = report(name, objects)

    cams = build_stage(objects, rim, rim2)
    setup_render(samples, res)
    export(name, root, objects, out_dir)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, f"{name}.blend"), compress=True)

    if do_render:
        render_dir = os.path.join(out_dir, "renders")
        os.makedirs(render_dir, exist_ok=True)
        scene = bpy.context.scene
        for view in views:
            scene.camera = cams["Cam" + view.capitalize()]
            scene.render.filepath = os.path.join(render_dir, f"{view}.png")
            bpy.ops.render.render(write_still=True)
            print("rendered", os.path.join(render_dir, f"{view}.png"))
        scene.camera = cams["CamHero"]
    return info
