"""Build the Void Hydra pet in Blender.

A blocky, studded five-headed hydra with neon collars, floating over a
segmented summoning circle. Every piece is a bevelled box (with real
cylinder studs on top faces), so it reads as classic Roblox "stud" style
while keeping the detail of the reference art.

Run with Blender:   blender -b -P build_void_hydra.py -- [--render] [--samples N]
or with the bpy module (pip install bpy):   python build_void_hydra.py [--render]

Outputs (next to this file):
  VoidHydra.blend                 the model, materials, lights and cameras
  export/VoidHydra.fbx            for the Roblox 3D Importer (recommended)
  export/VoidHydra.glb            glTF alternative
  export/VoidHydra_Palette.png    the colour palette texture every mesh uses
  renders/*.png                   preview renders (with --render)

Coordinates: Z up, the pet faces -Y. Sizes are in "design units"; SCALE
turns them into studs (the finished pet is about 5.5 studs tall).
"""

import math
import os
import sys

import bpy  # noqa: I001  (bpy must load before bmesh when used as a module)
import bmesh
from mathutils import Euler, Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
SCALE = 0.4  # studs per design unit
HOVER = 0.8  # body floats this far above the circle
STUD_PITCH = 0.5
STUD_RADIUS = 0.15
STUD_HEIGHT = 0.12
BEVEL = 0.05
NECKS = 5
NECK_SEGMENTS = 5

# (slot name, sRGB hex). Order = position in the palette texture.
PALETTE = [
    ("void", "0b0710"),
    ("hide", "1c1326"),
    ("hidelight", "2a1b3d"),
    ("plate", "3d2659"),
    ("belly", "5a3a85"),
    ("bone", "e8dcf5"),
    ("neon_magenta", "e35cff"),
    ("neon_pink", "ff8bf0"),
    ("neon_violet", "a64dff"),
]
SLOT = {name: i for i, (name, _) in enumerate(PALETTE)}
NEON_SUFFIX = {"neon_magenta": "NeonMagenta", "neon_pink": "NeonPink", "neon_violet": "NeonViolet"}
CELL = 16  # each palette colour is a CELL x CELL square, so mipmaps stay clean
PAL_W, PAL_H = CELL * 16, CELL


def rot(rx=0.0, ry=0.0, rz=0.0):
    return Euler((math.radians(rx), math.radians(ry), math.radians(rz)), "XYZ").to_matrix().to_4x4()


def tr(x, y=None, z=None):
    v = Vector(x) if y is None else Vector((x, y, z))
    return Matrix.Translation(v)


def hex_rgb(h):
    return tuple(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


class Hydra:
    def __init__(self):
        self.meshes = {}  # object name -> bmesh
        self.pivots = {}  # group -> Vector (design units)

    # -- geometry helpers ---------------------------------------------------

    def _bm(self, name):
        if name not in self.meshes:
            bm = bmesh.new()
            bm.faces.layers.int.new("pal")
            self.meshes[name] = bm
        return self.meshes[name]

    def block(self, group, size, matrix, color="hide", studs=False, keep=None):
        """A bevelled box of `size` placed by `matrix`, optionally studded on its local +Z face."""
        sx, sy, sz = size
        tmp = bmesh.new()
        bmesh.ops.create_cube(tmp, size=1.0, matrix=matrix @ Matrix.Diagonal((sx, sy, sz, 1.0)))
        offset = min(BEVEL, min(size) * 0.18)
        bmesh.ops.bevel(
            tmp, geom=list(tmp.verts) + list(tmp.edges), offset=offset, offset_type="OFFSET",
            segments=1, profile=0.5, affect="EDGES", clamp_overlap=True,
        )
        if studs and sx >= 0.4 and sy >= 0.4:
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
        name = f"{group}_{NEON_SUFFIX[color]}" if color in NEON_SUFFIX else group
        dst = self._bm(name)
        layer = dst.faces.layers.int["pal"]
        vmap = {v: dst.verts.new(v.co) for v in tmp.verts}
        for f in tmp.faces:
            nf = dst.faces.new([vmap[v] for v in f.verts])
            nf[layer] = SLOT[color]
        tmp.free()

    def body_block(self, group, size, pos, r=(0, 0, 0), **kw):
        x, y, z = pos
        self.block(group, size, tr(x, y, z + HOVER) @ rot(*r), **kw)

    def diamond(self, group, s, matrix, color):
        self.block(group, (s, s, s), matrix @ rot(45, 0, 0), color=color)

    # -- body -----------------------------------------------------------------

    def build_body(self):
        g = "Body"
        self.pivots[g] = Vector((0, 0, 0))
        bb = self.body_block
        bb(g, (4.0, 5.0, 3.0), (0, 0.6, 3.6), color="hide", studs=True, keep=lambda x, y: abs(x) > 0.6)
        for k in range(4):  # segmented belly plates
            bb(g, (3.0 - k * 0.15, 0.95, 0.35), (0, -1.0 + k * 1.05, 2.0), color="belly", studs=False)
        bb(g, (3.6, 1.8, 2.8), (0, -2.4, 4.0), color="hidelight", studs=True, keep=lambda x, y: abs(x) > 0.6)
        for row in range(3):  # chest scales
            bb(g, (2.6 - row * 0.4, 0.3, 0.5), (0, -3.35, 2.95 + row * 0.6), color="belly")
        self.block(g, (0.55, 0.2, 0.55), tr(0, -3.55, 4.75 + HOVER) @ rot(0, 45, 0), color="neon_magenta")

        for side in (-1, 1):
            # shoulder pauldrons (two layers) and hip plates
            bb(g, (1.6, 2.4, 0.5), (side * 2.15, -1.8, 5.0), (0, side * 20, 0), color="plate", studs=True)
            bb(g, (1.4, 2.0, 0.4), (side * 2.5, -1.8, 4.55), (0, side * 38, 0), color="plate")
            bb(g, (1.3, 2.0, 0.5), (side * 2.1, 2.0, 4.6), (0, side * 20, 0), color="plate", studs=True)

            for y in (-1.6, 2.2):  # front and rear legs
                x = side * 2.2
                bb(g, (1.4, 1.6, 1.8), (x, y, 2.6), color="hidelight", studs=False)
                bb(g, (0.9, 0.3, 0.8), (x, y - 0.85, 2.15), color="plate")  # knee plate
                bb(g, (1.0, 1.0, 1.4), (x, y - 0.2, 1.1), color="hide")
                bb(g, (1.4, 1.8, 0.5), (x, y - 0.5, 0.25), color="plate", studs=True)
                for c in (-1, 0, 1):
                    bb(g, (0.28, 0.6, 0.28), (x + c * 0.45, y - 1.6, 0.2), (15, 0, 0), color="void")
                    bb(g, (0.16, 0.2, 0.16), (x + c * 0.45, y - 1.95, 0.12), (15, 0, 0), color="bone")
                self.block(g, (0.06, 0.35, 0.35), tr(x + side * 0.72, y, 2.7 + HOVER) @ rot(45, 0, 0),
                           color="neon_magenta")

        for i in range(5):  # spine spikes with glowing tips
            y = 3.0 - i * 1.1
            s = 0.75 - i * 0.04
            self.diamond(g, s, tr(0, y, 5.15 + HOVER), "plate")
            self.diamond(g, 0.22, tr(0, y, 5.62 + HOVER), "neon_magenta")

    def build_tail(self):
        g = "Tail"
        self.pivots[g] = Vector((0, 3.0, 3.4 + HOVER))
        segs = [
            ((2.2, 1.8, 1.8), (0, 3.8, 3.4), -10, "hide"),
            ((1.6, 1.8, 1.3), (0, 5.4, 2.9), -20, "hidelight"),
            ((1.1, 1.6, 0.9), (0, 6.8, 2.2), -25, "hide"),
            ((0.7, 1.4, 0.6), (0, 8.0, 1.5), -30, "hidelight"),
        ]
        for i, (size, pos, pitch, color) in enumerate(segs):
            m = tr(pos[0], pos[1], pos[2] + HOVER) @ rot(pitch, 0, 0)
            self.block(g, size, m, color=color, studs=(i < 2), keep=lambda x, y: abs(x) > 0.3)
            self.diamond(g, 0.42 - i * 0.07, m @ tr(0, 0, size[2] / 2 + 0.12), "plate")
        self.block(g, (0.5, 1.0, 0.5), tr(0, 9.0, 1.0 + HOVER) @ rot(-35, 0, 0), color="neon_magenta")

    # -- necks and heads ------------------------------------------------------

    def collar(self, group, frame, radius, depth, thickness, color="neon_pink", n=8):
        chord = 2 * math.pi * radius / n * 1.08
        for k in range(n):
            m = frame @ rot(0, k * 360 / n, 0) @ tr(0, 0, radius)
            self.block(group, (chord, depth, thickness), m, color=color)

    def build_necks(self):
        for i in range(NECKS):
            u = (i / (NECKS - 1)) * 2 - 1 if NECKS > 1 else 0.0
            g = f"Neck{i + 1}"
            phi = math.radians(u * 55)
            fwd = Vector((math.sin(phi), -math.cos(phi), 0))
            lateral = Vector((math.cos(phi), math.sin(phi), 0))
            base = Vector((u * 1.3, -2.6, 4.8 + HOVER))
            self.pivots[g] = base.copy()
            height = 6.0 - abs(u) * 1.6  # middle head stands tallest
            reach = 2.0 + abs(u) * 2.0  # outer heads reach further out
            p0, p1, p2 = (0.0, 0.0), (-0.5, height * 0.9), (reach, height)

            def point(t):
                qx = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
                qz = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
                return base + fwd * qx + Vector((0, 0, qz))

            for s in range(NECK_SEGMENTS):
                a, b = point(s / NECK_SEGMENTS), point((s + 1) / NECK_SEGMENTS)
                along = (b - a).normalized()
                x = -lateral
                z = x.cross(along).normalized()  # dorsal side of the neck
                frame = Matrix((x, along, z)).transposed().to_4x4()
                frame.translation = (a + b) / 2
                w = 1.22 - s * 0.06
                length = (b - a).length
                color = "hide" if s % 2 == 0 else "hidelight"
                self.block(g, (w, length + 0.3, w), frame, color=color, studs=(s % 2 == 1))
                self.block(g, (w * 0.72, length * 0.85, 0.2), frame @ tr(0, 0, -w / 2), color="belly")
                if s % 2 == 0:
                    self.diamond(g, 0.38, frame @ tr(0, 0, w / 2 + 0.1), "plate")
                if s == NECK_SEGMENTS - 2:  # the double glowing collar under each head
                    self.collar(g, frame @ tr(0, 0.22, 0), w / 2 + 0.2, 0.2, 0.14)
                    self.collar(g, frame @ tr(0, -0.22, 0), w / 2 + 0.3, 0.16, 0.12)

            head_rot = rot(0, 0, math.degrees(phi)) @ rot(12, 0, 0)
            end = point(1.0)
            hm = tr(end + head_rot.to_3x3() @ Vector((0, -0.55, 0.1))) @ head_rot
            self.build_head(g, hm)

    def build_head(self, g, hm):
        def h(size, pos, r=(0, 0, 0), color="hidelight", studs=False, keep=None, base=hm):
            self.block(g, size, base @ tr(*pos) @ rot(*r), color=color, studs=studs, keep=keep)

        h((1.8, 1.7, 1.3), (0, 0, 0), studs=True, keep=lambda x, y: y > -0.3)  # skull
        h((1.5, 0.5, 1.0), (0, 0.95, 0.05), color="plate")  # back plate
        h((1.3, 1.6, 0.72), (0, -1.5, -0.12), color="hide")  # snout
        h((0.5, 1.3, 0.22), (0, -1.45, 0.33), color="plate", studs=True)  # snout ridge
        for sd in (-1, 1):
            h((0.2, 0.14, 0.12), (sd * 0.32, -2.3, 0.05), color="void")  # nostril
            h((0.6, 0.32, 0.34), (sd * 0.66, -0.76, 0.36), color="void")  # eye socket
            h((0.5, 0.3, 0.24), (sd * 0.68, -0.78, 0.36), color="neon_magenta")  # eye
            h((0.62, 0.55, 0.22), (sd * 0.62, -0.62, 0.6), (0, -sd * 14, 0), color="plate")  # brow
            for k in range(4):  # upper teeth
                h((0.13, 0.13, 0.22), (sd * 0.5, -1.0 - k * 0.33, -0.55), color="bone")
            h((0.16, 0.16, 0.38), (sd * 0.42, -2.12, -0.62), color="bone")  # fang
            for k in range(3):  # cheek frills
                h((0.14, 0.55, 0.3), (sd * 0.95, 0.2 + k * 0.32, -0.15 + k * 0.12), (20, 0, -sd * 25), color="plate")
            # stepped horn sweeping back, up and out
            pos = Vector((sd * 0.5, 0.35, 0.6))
            for length, width, pitch, color in ((0.8, 0.42, 30, "plate"), (0.7, 0.34, 48, "plate"), (0.6, 0.26, 65, "bone")):
                r = rot(pitch, 0, -sd * 15)
                d = r.to_3x3() @ Vector((0, 1, 0))
                center = pos + d * (length / 2)
                self.block(g, (width, length, width), hm @ tr(center) @ r, color=color)
                pos = pos + d * (length * 0.9)

        # open lower jaw, hinged under the skull
        jaw = hm @ tr(0, -0.35, -0.5) @ rot(18, 0, 0)
        h((1.15, 1.7, 0.34), (0, -0.9, -0.12), color="belly", base=jaw)
        h((0.85, 1.4, 0.08), (0, -0.85, 0.08), color="neon_magenta", base=jaw)  # mouth glow
        for sd in (-1, 1):
            for k in range(4):
                h((0.13, 0.13, 0.2), (sd * 0.45, -0.4 - k * 0.35, 0.12), color="bone", base=jaw)
            h((0.13, 0.13, 0.26), (sd * 0.15, -1.65, 0.14), color="bone", base=jaw)

    # -- summoning circle and shards -----------------------------------------

    def ground_ring(self, g, radius, n, width, height, z, color):
        chord = 2 * math.pi * radius / n * 0.82  # small gaps read as segments
        for k in range(n):
            self.block(g, (chord, width, height), rot(0, 0, k * 360 / n) @ tr(0, -radius, z), color=color)

    def build_circle(self):
        g = "Circle"
        self.pivots[g] = Vector((0, 0, 0))
        self.ground_ring(g, 6.2, 32, 0.4, 0.12, 0.06, "neon_pink")
        self.ground_ring(g, 7.1, 40, 0.18, 0.08, 0.04, "neon_magenta")
        self.ground_ring(g, 5.2, 24, 0.24, 0.1, 0.05, "neon_violet")
        for k in range(12):  # rune ticks between the rings
            self.block(g, (0.14, 0.5, 0.08), rot(0, 0, k * 30 + 15) @ tr(0, -5.7, 0.04), color="neon_violet")

    def build_shards(self):
        g = "Shards"
        self.pivots[g] = Vector((0, 0, 0))
        for k in range(10):
            a = math.radians(k * 36 + 10)
            r = 4.6 + (k % 3) * 0.9
            z = 1.4 + (k % 4) * 1.1
            m = tr(math.sin(a) * r, -math.cos(a) * r, z) @ rot(45, 35, k * 20)
            self.block(g, (0.32, 0.32, 0.32), m, color="neon_violet" if k % 2 else "neon_pink")

    # -- objects, materials ---------------------------------------------------

    def palette_image(self):
        img = bpy.data.images.new("VoidHydra_Palette", PAL_W, PAL_H, alpha=False)
        px = [0.0] * (PAL_W * PAL_H * 4)
        for slot, (_, hx) in enumerate(PALETTE):
            r, g, b = hex_rgb(hx)
            for y in range(PAL_H):
                for x in range(slot * CELL, (slot + 1) * CELL):
                    i = (y * PAL_W + x) * 4
                    px[i : i + 4] = (r, g, b, 1.0)
        img.pixels = px
        os.makedirs(os.path.join(HERE, "export"), exist_ok=True)
        img.filepath_raw = os.path.join(HERE, "export", "VoidHydra_Palette.png")
        img.file_format = "PNG"
        img.save()
        img.pack()
        return img

    def material(self, name, img, emission):
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

    def finish(self):
        coll = bpy.data.collections.new("VoidHydra")
        bpy.context.scene.collection.children.link(coll)
        root = bpy.data.objects.new("VoidHydra", None)
        root.empty_display_type = "PLAIN_AXES"
        coll.objects.link(root)

        img = self.palette_image()
        body_mat = self.material("VoidHydra_Body", img, 0.0)
        neon_mat = self.material("VoidHydra_Neon", img, 3.0)

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
        return root, objects


def build_stage():
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
    bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, 0))
    ground = bpy.context.active_object
    ground.name = "Ground"
    ground.data.materials.append(ground_mat)
    for c in ground.users_collection:
        c.objects.unlink(ground)
    stage.objects.link(ground)

    def light(name, kind, energy, color, loc, size=4.0):
        data = bpy.data.lights.new(name, kind)
        data.energy = energy
        data.color = color
        if kind == "AREA":
            data.size = size
        ob = bpy.data.objects.new(name, data)
        ob.location = loc
        target = Vector((0, 0, 2.0))
        ob.rotation_euler = (target - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        ob.visible_glossy = False  # keep the lamps out of the floor reflection
        stage.objects.link(ob)

    light("Key", "AREA", 600, (0.85, 0.8, 1.0), (-5, -7, 7), 5)
    light("RimMagenta", "AREA", 500, (1.0, 0.35, 1.0), (5, 7, 6), 4)
    light("RimViolet", "AREA", 300, (0.6, 0.35, 1.0), (-6, 6, 3), 4)

    cams = {}
    for name, loc, target, lens in (
        ("CamHero", (7.0, -11.6, 4.2), (0, 0.2, 2.45), 46),
        ("CamFront", (0, -14.0, 3.0), (0, 0, 2.5), 50),
        ("CamSide", (14.0, 0.6, 3.0), (0, 0.6, 2.4), 50),
    ):
        data = bpy.data.cameras.new(name)
        data.lens = lens
        ob = bpy.data.objects.new(name, data)
        ob.location = loc
        ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        stage.objects.link(ob)
        cams[name] = ob
    scene.camera = cams["CamHero"]
    return cams


def setup_render(samples):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 1024
    scene.view_settings.view_transform = "Standard"  # keeps the neon saturated pink

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


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    do_render = "--render" in argv
    samples = int(argv[argv.index("--samples") + 1]) if "--samples" in argv else 64

    bpy.ops.wm.read_factory_settings(use_empty=True)
    hydra = Hydra()
    hydra.build_body()
    hydra.build_tail()
    hydra.build_necks()
    hydra.build_circle()
    hydra.build_shards()
    root, objects = hydra.finish()

    total = 0
    for ob in objects:
        tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
        total += tris
        print(f"  {ob.name:<22} {tris:>6} tris")
    print(f"  {'TOTAL':<22} {total:>6} tris in {len(objects)} meshes")

    cams = build_stage()
    setup_render(samples)

    export_dir = os.path.join(HERE, "export")
    for ob in bpy.context.scene.objects:
        ob.select_set(ob == root or ob in objects)
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.fbx(
        filepath=os.path.join(export_dir, "VoidHydra.fbx"), use_selection=True,
        object_types={"EMPTY", "MESH"}, mesh_smooth_type="FACE", path_mode="COPY",
        embed_textures=True, apply_scale_options="FBX_SCALE_UNITS", bake_anim=False,
    )
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(export_dir, "VoidHydra.glb"), export_format="GLB", use_selection=True,
    )
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "VoidHydra.blend"), compress=True)

    if do_render:
        render_dir = os.path.join(HERE, "renders")
        os.makedirs(render_dir, exist_ok=True)
        scene = bpy.context.scene
        for name, file in (("CamHero", "hero.png"), ("CamFront", "front.png"), ("CamSide", "side.png")):
            scene.camera = cams[name]
            scene.render.filepath = os.path.join(render_dir, file)
            bpy.ops.render.render(write_still=True)
            print("rendered", file)
        scene.camera = cams["CamHero"]


if __name__ == "__main__":
    main()
