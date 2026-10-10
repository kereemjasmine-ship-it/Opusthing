"""Build the RuneGolem pet (Legendary) in the blocky, studded "void pet" style.

A heavy void-stone golem standing on short thick legs with its long gorilla
arms angled down to two enormous fists. The barrel torso is stacked from
courses of chunky masonry blocks (hide / hidelight alternating, every other
block pushed out a little so the seams read), widening from a narrow belted
waist to massive studded shoulders, with a studded hump behind the head. The
head sits sunk between the pauldrons and juts forward of them: a heavy V brow
over a single glowing amber visor slit, outward-sweeping stepped horns, and an
open underbite jaw with rows of bone teeth and tusks around a furnace glow. The
fists rest on their knuckles (bone knuckle studs), and stepped plate spikes with
amber tips run down the back. Thin amber rune
cracks run through stones of the chest, arms and legs, radiating from a
faceted amber core crystal set in a plate frame in the middle of the chest
(with two small pink sparks). Chunky rock shards with amber rune studs float
around the shoulders and back, amber crystals grow from the hump, and an
amber segmented circle lies under its feet.

Run with the bpy module:   python build.py [--render] [--samples N] [--res PX] [--views hero,front,side]
or with Blender:           blender -b -P build.py -- [--render] ...

Coordinates: Z up, the golem faces -Y, design units (blocky.SCALE = 0.4 studs).
Everything is built roughly in place, then recentre() puts the feet on z = 0
and centres the golem on the origin before the shards and the circle are added.

Pet's left is +X (it faces -Y), so ArmL / LegL sit on the +X side.
"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
import blocky  # noqa: E402  (loads bpy before bmesh)
import bmesh  # noqa: E402
from blocky import Matrix, Vector, rot, tr  # noqa: E402

NAME = "RuneGolem"
PALETTE = blocky.Palette(
    blocky.FAMILY + [("neon_amber", "ff9a3c"), ("neon_pink", "ff8bf0")],
    neon=["neon_amber", "neon_pink"],
)

# blocky lights the neon material at emission 3.0, which clips amber (ff9a3c) to
# yellow in the renders (Standard view transform). This pet's own Builder instance
# uses a lower strength so the glow reads amber-orange (1.3 keeps the red channel
# just over the bloom threshold); it only changes this pet's render material
# (see soften_neon), never the palette colour Roblox uses.
NEON_EMISSION = 1.3

# Main proportions (design units).
LEG_X = 1.45  # leg centre lines
HIP_Z = 3.3  # hip joint height
SHOULDER = Vector((3.6, 0.15, 8.15))  # +X shoulder joint (mirrored for the right arm)
NECK = Vector((0.0, -0.85, 8.7))  # head joint
SKULL = Vector((0.0, -1.5, 9.62))  # skull centre
HEAD_SCALE = 1.12  # the head is laid out in head units around SKULL
CORE = Vector((0.0, -2.0, 6.85))  # chest core crystal centre

RUNE_W = 0.13  # width of the glowing rune strips
RUNE_D = 0.1  # their depth; mostly sunk into the stone, ~0.04 stands proud


def at(x, y, z, rx=0.0, ry=0.0, rz=0.0):
    """Translation then rotation, the usual way every part is placed."""
    return tr(x, y, z) @ rot(rx, ry, rz)


def seg_frame(lo, hi):
    """Frame at the middle of lo -> hi with local +Z running up the segment and -Y facing front.

    Returns (matrix, length). Used for the arm stones, which lean.
    """
    lo, hi = Vector(lo), Vector(hi)
    z = (hi - lo).normalized()
    y = Vector((0, 1, 0))
    y = (y - z * y.dot(z)).normalized()
    x = y.cross(z)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = (lo + hi) / 2
    return m, (hi - lo).length


# -- rune strips -----------------------------------------------------------------

# Glyphs in face-normalised coordinates (u, v in -0.5..0.5; u points outward on
# front faces and backward on side faces, v up). Each is a list of polylines.
GLYPHS = {
    "crack": [[(-0.5, 0.08), (-0.2, 0.26), (0.04, -0.04), (0.3, 0.12), (0.5, -0.12)],
              [(0.04, -0.04), (0.16, -0.36)]],
    "crack_v": [[(0.05, 0.5), (-0.12, 0.2), (0.12, -0.02), (-0.06, -0.26), (0.1, -0.5)],
                [(0.12, -0.02), (0.38, 0.1)]],
    "fork": [[(-0.3, -0.38), (0.0, -0.02), (0.0, 0.4)], [(0.0, -0.02), (0.3, -0.34)]],
    "tri": [[(0.0, 0.36), (0.3, -0.24), (-0.3, -0.24), (0.0, 0.36)], [(0.0, -0.24), (0.0, -0.44)]],
}

# Hand-placed chest cracks (block-local units, u outward) radiating from the core.
# Keyed by the course and the block's mirror index (0 = outer corner stone).
CHEST_CRACKS = {
    ("C", 1): [[(-0.3, 0.02), (-0.06, 0.24), (0.14, -0.02), (0.5, 0.2)], [(0.14, -0.02), (0.3, -0.4)]],
    ("C", 0): [[(-0.45, 0.2), (-0.16, 0.38), (0.06, 0.12), (0.3, 0.24)]],
    ("D", 0): [[(-0.4, -0.6), (-0.18, -0.26), (0.1, -0.36), (0.24, 0.04), (0.08, 0.3)]],
    ("B", 0): [[(-0.32, 0.57), (-0.1, 0.24), (-0.26, -0.02), (0.04, -0.3)], [(-0.1, 0.24), (0.26, 0.14)]],
}


def rune_path(b, g, face, pts, color="neon_amber", w=RUNE_W):
    """Thin glowing strips joining (u, v) points on a face frame (local -Y points out of the stone)."""
    for (u0, v0), (u1, v1) in zip(pts, pts[1:]):
        du, dv = u1 - u0, v1 - v0
        length = math.hypot(du, dv)
        ang = math.degrees(math.atan2(dv, du))
        m = face @ tr((u0 + u1) / 2, 0, (v0 + v1) / 2) @ rot(0, -ang, 0)
        b.block(g, (length + w, RUNE_D, w), m, color=color, bevel=0)


def glyph(b, g, face, name, fw, fh, flip=1.0, fill=0.78):
    """Scale glyph `name` onto a face fw wide and fh tall; flip=-1 mirrors it left/right."""
    for line in GLYPHS[name]:
        rune_path(b, g, face, [(u * fw * fill * flip, v * fh * fill) for u, v in line])


def front_face(m, size):
    """Face frame on a block's front (-Y) face: u = local x, v = local z."""
    return m @ tr(0, -size[1] / 2 + 0.02, 0)


def back_face(m, size):
    """Face frame on a block's back (+Y) face (u = local -x, v = local z)."""
    return m @ tr(0, size[1] / 2 - 0.02, 0) @ rot(0, 0, 180)


def side_face(m, size, sd):
    """Face frame on a block's +X (sd=1) or -X (sd=-1) face; u runs backward on +X, forward on -X."""
    return m @ tr(sd * (size[0] / 2 - 0.02), 0, 0) @ rot(0, 0, 90 * sd)


def stone(b, g, size, m, color, front=None, side=None, sd=1, **kw):
    """A block with optional rune glyphs on its front face and on its outer side face."""
    b.block(g, size, m, color=color, **kw)
    if front:
        glyph(b, g, front_face(m, size), front, size[0], size[2], flip=sd)
    if side:
        glyph(b, g, side_face(m, size, sd), side, size[1], size[2], flip=sd)


def rune_stud(b, g, matrix, s=0.22, color="neon_amber"):
    """A small glowing diamond (rune stud) on a stone face; the matrix's -Y points out."""
    b.block(g, (s, s * 0.5, s), matrix @ rot(0, 45, 0), color=color, bevel=0.02)


def soften_neon(b):
    """Make this Builder light its neon material at NEON_EMISSION (see the note at the top)."""
    make = b._material

    def material(name, img, emission):
        return make(name, img, NEON_EMISSION if emission else emission)

    b._material = material


# -- torso --------------------------------------------------------------------------


def _world_keep(fn, cx, cy):
    """Turn a keep(x, y) test in world X/Y into the block-local test Builder.block wants."""
    return lambda lx, ly: fn(cx + lx, cy + ly)


def course(b, g, name, z0, h, cuts, depth, y, start=0, studs=None, trim=0.84, color0=0):
    """One masonry layer of the barrel torso.

    The layer is cut into blocks at the x positions in `cuts`. Neighbouring blocks
    alternate hide/hidelight and every other one pushes its front out a little;
    the two end blocks are shallower so the barrel's corners read chunky and round.
    Chest cracks for (name, mirror index) come from CHEST_CRACKS, mirrored on -X.
    studs: keep(x, y) in world X/Y for the top-face studs, or None for no studs.
    """
    n = len(cuts) - 1
    for i in range(n):
        x0, x1 = cuts[i], cuts[i + 1]
        cx = (x0 + x1) / 2
        mi = min(i, n - 1 - i)  # mirror index: 0 = outer corner stone
        push = 0.14 if (mi + start) % 2 else 0.0
        d = depth * (trim if mi == 0 else 1.0) + push
        cy = y - push / 2
        color = ("hide", "hidelight")[(mi + color0) % 2]
        m = tr(cx, cy, z0 + h / 2)
        keep = _world_keep(studs, cx, cy) if studs else None
        b.block(g, (x1 - x0, d, h), m, color=color, studs=bool(studs), keep=keep)
        flip = 1 if cx >= 0 else -1
        for line in CHEST_CRACKS.get((name, mi), ()):
            rune_path(b, g, front_face(m, (x1 - x0, d, h)), [(u * flip, v) for u, v in line])


def d_course_keep(x, y):
    """Studs on the top course: only where the head, hump and pauldrons leave it bare."""
    return 1.85 < abs(x) < 2.5


def hump_keep(x, y):
    """Studs on the lower hump: the outer columns the upper hump leaves bare."""
    return abs(x) > 1.3 and y > 0.3


def hump_top_keep(x, y):
    """Studs on the upper hump: the front row, clear of the back crystals."""
    return y < 1.5


def build_body(b):
    g = "Body"
    b.pivot(g, (0, 0.2, HIP_Z))

    # pelvis, belt course and the four barrel courses, bottom to top: narrow waist, huge shoulders
    course(b, g, "P", 2.75, 0.85, [-1.8, -0.6, 0.6, 1.8], 2.6, 0.3, color0=1)
    course(b, g, "W", 3.55, 0.4, [-2.0, -0.7, 0.7, 2.0], 2.9, 0.3)
    course(b, g, "A", 3.9, 1.1, [-1.9, -0.65, 0.65, 1.9], 3.0, 0.45, start=1)
    course(b, g, "B", 5.0, 1.15, [-2.4, -1.35, -0.3, 0.3, 1.35, 2.4], 3.7, 0.45, color0=1)
    course(b, g, "C", 6.15, 1.4, [-2.9, -2.0, -1.0, 1.0, 2.0, 2.9], 4.3, 0.4)
    course(b, g, "D", 7.55, 1.2, [-3.1, -1.7, -0.6, 0.6, 1.7, 3.1], 4.2, 0.5, start=1, studs=d_course_keep,
           color0=1)
    # two-tier hunched hump rising behind the head
    course(b, g, "H", 8.75, 0.8, [-1.7, -0.55, 0.55, 1.7], 2.8, 1.35, studs=hump_keep)
    course(b, g, "I", 9.55, 0.55, [-1.15, -0.4, 0.4, 1.15], 1.8, 1.75, studs=hump_top_keep, color0=1)

    # plate belt around the waist with an amber rune buckle
    b.block(g, (4.3, 3.2, 0.38), tr(0, 0.3, 3.75), color="plate")
    b.block(g, (0.9, 0.3, 0.6), tr(0, -1.38, 3.75), color="plate")
    rune_stud(b, g, tr(0, -1.53, 3.75), 0.3)

    # hanging tasset plates over the thighs
    for sd in (-1, 1):
        b.block(g, (1.35, 0.35, 1.0), at(sd * 1.4, -1.25, 3.25, -8, 0, 0), color="plate")
        b.block(g, (0.9, 0.3, 0.3), at(sd * 1.4, -1.38, 2.75, -8, 0, 0), color="hidelight")

    # belly slabs down the front (like the hydra's chest scales)
    for w, z, y in ((2.2, 5.83, -1.5), (1.8, 5.28, -1.5), (1.5, 4.6, -1.2), (1.1, 4.1, -1.2)):
        b.block(g, (w, 0.36, 0.45), tr(0, y, z), color="belly")

    build_core(b, g)

    # back: spine ridge of plate diamonds with amber tips, like the hydra's spine
    # (stepped plate spikes jutting back and up, so the side silhouette gets a jagged back line)
    for z, y, length in ((4.5, 2.0, 0.55), (5.6, 2.35, 0.7), (6.85, 2.6, 0.8), (8.15, 2.65, 0.7)):
        b.block(g, (1.0, 0.5, 0.7), tr(0, y + 0.15, z), color="plate")
        spike = tr(0, y + 0.3, z) @ rot(-72, 0, 0)
        b.taper(g, (0.62, 0.62, length), spike @ tr(0, 0, length / 2), color="plate", top=(0.45, 0.45))
        b.taper(g, (0.3, 0.3, 0.3), spike @ tr(0, 0, length + 0.1), color="neon_amber", top=(0.2, 0.2))
        for sd in (-1, 1):  # bone rivets either side of each spike root
            b.block(g, (0.16, 0.12, 0.16), at(sd * 0.36, y + 0.42, z - 0.12, 0, 45, 0), color="bone")
    # rune glyphs on the back stones either side of the spine
    for sd in (-1, 1):
        glyph(b, g, back_face(tr(sd * 1.5, 0.4, 6.85), (1.0, 4.3, 1.4)), "crack_v", 1.0, 1.4)
        glyph(b, g, back_face(tr(sd * 1.15, 0.5, 8.15), (1.1, 4.2, 1.2)), "fork", 1.1, 1.2)

    # amber crystals growing out of the hump
    # (they lean well back so they never read as a crest on the head from the front)
    for x, h, lean, out in ((0.0, 1.05, 58, 0), (-0.8, 0.9, 54, -22), (0.8, 0.9, 54, 22)):
        base = at(x, 2.2, 10.1, -lean, out, 0)
        b.taper(g, (0.7, 0.7, 0.4), base, color="plate", top=(0.75, 0.75))
        b.taper(g, (0.44, 0.44, h), base @ tr(0, 0, 0.2 + h / 2), color="neon_amber", top=(0.2, 0.2))


def build_core(b, g):
    """The faceted amber core crystal in a plate frame in the middle of the chest."""
    c = CORE
    b.block(g, (1.7, 0.3, 1.3), tr(c.x, c.y + 0.2, c.z), color="void")  # socket
    b.block(g, (2.5, 0.55, 0.38), tr(c.x, c.y + 0.02, c.z + 0.8), color="plate")  # lintel
    b.block(g, (2.5, 0.55, 0.38), tr(c.x, c.y + 0.02, c.z - 0.8), color="plate")  # sill
    b.block(g, (1.4, 0.4, 0.25), tr(c.x, c.y - 0.15, c.z + 1.06), color="hidelight")  # lintel cap
    for sd in (-1, 1):
        b.block(g, (0.42, 0.55, 1.25), tr(c.x + sd * 1.05, c.y + 0.02, c.z), color="plate")  # jambs
        for v in (-1, 1):  # bone rivets on the frame corners
            b.block(g, (0.2, 0.16, 0.2), at(c.x + sd * 1.05, c.y - 0.3, c.z + v * 0.8, 0, 45, 0), color="bone")
        rune_stud(b, g, tr(c.x + sd * 0.62, c.y - 0.02, c.z + 0.12), 0.18, color="neon_pink")  # sparks
    # bipyramid crystal turned 45 degrees so an edge faces front
    for v in (-1, 1):
        m = tr(c.x, c.y - 0.12, c.z + v * 0.32) @ rot(0, 0, 45) @ rot(0 if v > 0 else 180, 0, 0)
        b.taper(g, (0.78, 0.78, 0.64), m, color="neon_amber", top=(0.1, 0.1))


# -- head ---------------------------------------------------------------------------


def build_head(b):
    """Small sunken head, pushed forward of the pauldrons so the face reads from the side too.

    Laid out in head units around SKULL and scaled by HEAD_SCALE (positions and
    sizes only, so studs keep the shared size). Neon pieces stay under ~1.2 units wide.
    """
    g = "Head"
    b.pivot(g, NECK)
    S = SKULL
    k = HEAD_SCALE

    def h(size, pos, r=(0, 0, 0), color="hidelight", **kw):
        b.block(g, tuple(s * k for s in size), tr(S + Vector(pos) * k) @ rot(*r), color=color, **kw)

    b.block(g, (2.1, 2.2, 0.9), tr(0, -0.85, 8.8), color="hide")  # neck stone, sunk between the shoulders
    # skull, studded behind the brow and around the horn roots
    h((2.5, 2.2, 1.8), (0, 0, 0), studs=True,
      keep=lambda x, y: (y > -0.5 and abs(x) < 0.6) or (y > 0.7 and abs(x) > 0.8))
    h((2.1, 0.4, 1.3), (0, 1.15, -0.05), color="plate")  # back plate
    h((1.5, 0.3, 0.9), (0, 1.35, -0.1), color="hide")  # back plate boss
    h((2.2, 0.3, 0.36), (0, -1.1, -0.48), color="hide")  # upper lip under the visor
    h((2.15, 0.3, 0.58), (0, -1.12, 0.08), color="void")  # visor socket
    h((1.0, 0.2, 0.16), (0, -1.24, 0.08), color="neon_amber")  # visor slit
    h((0.44, 0.22, 0.32), (0, -1.26, 0.08), color="neon_amber")  # eye lens
    # open mouth: dark throat with a furnace glow set back behind two rows of teeth
    h((2.0, 1.0, 0.5), (0, -0.6, -0.88), color="void")
    h((1.05, 0.1, 0.2), (0, -1.15, -0.86), color="neon_amber")
    for x in (-0.48, -0.16, 0.16, 0.48):  # upper teeth hanging from the lip
        h((0.15, 0.15, 0.2), (x, -1.18, -0.74), color="bone")
    for sd in (-1, 1):
        # heavy V brow: each half tips down at the front and down toward the middle
        h((1.45, 0.95, 0.62), (sd * 0.68, -1.05, 0.64), (10, -sd * 8, 0), color="plate")
        h((0.55, 0.4, 0.26), (sd * 1.05, -1.5, 0.92), (10, -sd * 8, 0), color="hide")  # brow cap stone
        h((0.45, 1.5, 1.05), (sd * 1.35, -0.35, -0.12), color="plate")  # cheek stone
        h((0.3, 0.7, 0.5), (sd * 1.38, 0.55, -0.35), color="hide")  # jaw hinge block
        h((0.16, 0.16, 0.16), (sd * 1.55, 0.55, -0.35), (45, 0, 0), color="bone")  # hinge rivet
        for z in (0.12, -0.32):  # two small rune notches down each cheek
            b.block(g, (0.17, 0.17, 0.17), tr(S + Vector((sd * 1.58, -0.6, z)) * k) @ rot(45, 0, 0),
                    color="neon_amber", bevel=0.02)
    # short stepped stone horns sweeping out and up, with bone tips (not scaled: keeps the height)
    for sd in (-1, 1):
        pos = S + Vector((sd * 1.0, 0.15, 0.82)) * k
        for length, width, roll, color in ((0.66, 0.64, 32, "plate"), (0.58, 0.5, 46, "plate"),
                                           (0.44, 0.36, 60, "bone")):
            r = rot(-12, sd * roll, 0)
            d = r.to_3x3() @ Vector((0, 0, 1))
            b.block(g, (width, width, length), tr(pos + d * (length / 2)) @ r, color=color)
            pos = pos + d * (length * 0.85)
    # underbite jaw, dropped open, with a row of lower teeth and big tusks
    h((2.4, 1.45, 0.5), (0, -0.9, -1.3), color="belly")
    h((1.6, 0.42, 0.34), (0, -1.62, -1.5), color="plate")  # chin stone
    for x in (-0.36, 0.0, 0.36):
        h((0.15, 0.15, 0.2), (x, -1.48, -0.98), color="bone")  # lower teeth
    for sd in (-1, 1):
        h((0.28, 0.28, 0.6), (sd * 0.8, -1.5, -0.86), color="bone")  # tusk rising past the lip
        h((0.2, 0.2, 0.2), (sd * 0.8, -1.5, -0.46), (45, 0, 45), color="bone")  # tusk tip


# -- arms ---------------------------------------------------------------------------


def build_arm(b, sd):
    g = "ArmL" if sd > 0 else "ArmR"
    sh = Vector((sd * SHOULDER.x, SHOULDER.y, SHOULDER.z))
    b.pivot(g, sh)
    S = Vector((sd * 3.8, 0.15, 7.9))  # top of the upper arm
    E = Vector((sd * 4.95, 0.05, 5.35))  # elbow, bowed out like a gorilla's
    W = Vector((sd * 4.5, -1.15, 2.5))  # wrist
    F = Vector((sd * 4.42, -1.45, 1.1))  # fist centre: knuckles planted on the ground, forward of the feet

    # shoulder ball and two layers of studded pauldron
    b.block(g, (2.0, 2.1, 1.6), tr(sd * 3.75, 0.15, 8.05), color="hidelight")
    b.block(g, (2.2, 2.5, 0.45), at(sd * 4.25, 0.1, 8.5, 0, sd * 32, 0), color="plate")
    pauldron = at(sd * 3.85, 0.1, 9.0, 0, sd * 15, 0)
    b.block(g, (2.5, 2.8, 0.7), pauldron, color="plate", studs=True,
            keep=lambda x, y: not (sd * x > 0.2 and y > 0.4))
    # small amber crystal cluster on the back-outer corner of the pauldron
    cluster = pauldron @ tr(sd * 0.72, 0.85, 0.35)
    b.block(g, (0.8, 0.8, 0.25), cluster, color="hidelight")
    for dx, dy, w, hgt, lean in ((0.0, 0.0, 0.36, 0.7, 8), (sd * 0.24, -0.2, 0.26, 0.5, 26),
                                 (-sd * 0.2, 0.22, 0.24, 0.45, -22)):
        cm = cluster @ tr(dx, dy, 0.1) @ rot(lean * 0.5, sd * lean, 0)
        b.taper(g, (w, w, hgt), cm @ tr(0, 0, hgt / 2), color="neon_amber", top=(0.2, 0.2))
    for y in (-0.75, 0.0, 0.75):  # rune studs along the lower pauldron's outer edge
        rune_stud(b, g, at(sd * 5.27, 0.1 + y, 8.0, 0, 0, sd * 90) @ rot(0, -32, 0), 0.2)

    # upper arm with a plate band
    m, length = seg_frame(E, S)
    b.block(g, (1.5, 1.5, length), m, color="hide")
    b.block(g, (1.68, 1.68, 0.32), m @ tr(0, 0, -0.3), color="plate")
    b.block(g, (0.3, 1.1, length * 0.42), m @ tr(sd * 0.8, 0, length * 0.12), color="hidelight")  # outer slab
    b.block(g, (0.3, 0.8, 0.5), m @ tr(sd * 0.8, -0.1, -length * 0.3), color="hide")  # lower slab

    # elbow plate with a bone-tipped spike pointing back
    b.block(g, (1.85, 1.8, 0.62), tr(E), color="plate")
    spike = at(E.x, E.y + 0.8, E.z + 0.05, -100, 0, 0)
    b.taper(g, (0.72, 0.72, 0.75), spike, color="plate", top=(0.45, 0.45))
    b.taper(g, (0.34, 0.34, 0.35), spike @ tr(0, 0, 0.52), color="bone", top=(0.25, 0.25))

    # forearm: two stacked stones, the lower one heavier
    m, length = seg_frame(W, E)
    lo = m @ tr(0, 0, -length * 0.22)
    hi = m @ tr(0, 0, length * 0.27)
    stone(b, g, (2.1, 2.1, length * 0.56), lo, "hidelight", front="crack_v", side="crack", sd=sd)
    stone(b, g, (1.85, 1.85, length * 0.48), hi, "hide")
    for v, depth in ((0.26, 1.45), (-0.26, 1.25)):  # two-slab plate bracer on the outer side
        b.block(g, (0.3, depth, 0.48), hi @ tr(sd * 0.98, 0, v - 0.05), color="plate")

    # wrist cuff
    b.block(g, (2.4, 2.4, 0.5), tr(W), color="plate")
    rune_stud(b, g, tr(W + Vector((0, -1.21, 0))), 0.24)
    rune_stud(b, g, tr(W + Vector((sd * 1.21, 0, 0))) @ rot(0, 0, sd * 90), 0.24)

    build_fist(b, g, F, sd)


def build_fist(b, g, F, sd):
    """An enormous blocky fist: hand block, knuckle row, folded fingers and a thumb."""
    size = (2.7, 2.5, 2.2)
    stone(b, g, size, tr(F), "hidelight", side="crack", sd=sd)
    for k, x in enumerate((-0.96, -0.32, 0.32, 0.96)):
        kx = F.x + x
        b.block(g, (0.6, 0.55, 0.68), tr(kx, F.y - 1.4, F.z + 0.55), color="plate")  # knuckle
        b.block(g, (0.26, 0.16, 0.26), at(kx, F.y - 1.72, F.z + 0.6, 0, 45, 0), color="bone")  # knuckle stud
        b.block(g, (0.56, 0.45, 0.62), tr(kx, F.y - 1.33, F.z - 0.18), color="hide")  # finger
        b.block(g, (0.5, 0.5, 0.34), tr(kx, F.y - 1.08, F.z - 0.8), color="void")  # tucked fingertip
    # thumb across the inner side
    b.block(g, (0.62, 1.3, 0.9), tr(F.x - sd * 1.42, F.y - 0.6, F.z + 0.05), color="plate")
    b.block(g, (0.58, 0.6, 0.64), tr(F.x - sd * 1.26, F.y - 1.4, F.z - 0.1), color="hide")
    # studded back-of-hand plate on top of the fist, in front of the cuff
    b.block(g, (2.2, 0.6, 0.3), tr(F.x, F.y - 1.0, F.z + 1.15), color="plate", studs=True)


# -- legs ---------------------------------------------------------------------------


def build_leg(b, sd):
    g = "LegL" if sd > 0 else "LegR"
    x = sd * LEG_X
    b.pivot(g, (x, 0.15, HIP_Z))
    stone(b, g, (1.8, 1.8, 1.3), tr(x, 0.15, 2.85), "hide", side="fork", sd=sd)  # thigh
    b.block(g, (1.3, 0.4, 0.9), at(x, -0.82, 2.15, -8, 0, 0), color="plate")  # knee plate
    rune_stud(b, g, at(x, -1.04, 2.15, -8, 0, 0), 0.22)
    stone(b, g, (1.6, 1.6, 1.3), tr(x, 0.05, 1.45), "hidelight", front="crack_v", sd=sd)  # shin
    b.block(g, (1.8, 1.8, 0.4), tr(x, 0.05, 0.75), color="hide")  # ankle
    # big flat stone foot with studs on the toe end
    b.block(g, (2.4, 2.9, 0.6), tr(x, -0.4, 0.3), color="plate", studs=True, keep=lambda lx, ly: ly < -0.6)
    for c in (-1, 0, 1):
        b.block(g, (0.6, 0.6, 0.5), tr(x + c * 0.74, -2.0, 0.25), color="void")  # toe stone
        b.block(g, (0.42, 0.24, 0.34), tr(x + c * 0.74, -2.36, 0.2), color="bone")  # toe tip
    b.block(g, (1.6, 0.5, 0.45), tr(x, 1.15, 0.27), color="hidelight")  # heel stone


# -- placement, shards, circle -----------------------------------------------------


def recentre(b):
    """Shift every mesh and pivot so the lowest point is z = 0 and X/Y are centred."""
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for bm in b.meshes.values():
        for v in bm.verts:
            for i in range(3):
                lo[i] = min(lo[i], v.co[i])
                hi[i] = max(hi[i], v.co[i])
    shift = Vector((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z))
    for bm in b.meshes.values():
        bmesh.ops.translate(bm, vec=shift, verts=bm.verts)
    for g in b.pivots:
        b.pivots[g] = b.pivots[g] + shift


def rock(b, g, pos, s, spin, rune=False):
    """A chunky floating rock: a main stone, a smaller stone knocked off-centre and a plate chip."""
    m = tr(pos) @ rot(*spin)
    b.block(g, (s, s * 0.85, s * 0.8), m, color="hidelight")
    b.block(g, (s * 0.6, s * 0.6, s * 0.55), m @ tr(s * 0.35, -s * 0.15, s * 0.3), color="hide")
    b.block(g, (s * 0.45, s * 0.4, s * 0.3), m @ tr(-s * 0.3, s * 0.2, -s * 0.42), color="plate")
    if rune:
        b.block(g, (s * 0.26, s * 0.26, s * 0.26), m @ tr(0, -s * 0.43, 0) @ rot(0, 45, 0),
                color="neon_amber", bevel=0.02)


def build_shards(b):
    """Rock chunks hovering around the shoulders and back (Roblox orbits this group).

    Every rock clears the head, the hump and pauldron crystals and the back spikes
    over a full orbit about the vertical axis, even when Roblox's shard bob (0.15
    studs) and body bob (0.05 studs) are at opposite extremes (0.5 design units).
    """
    g = "Shards"
    b.pivot(g, (0, 0, 0))
    for sd in (-1, 1):
        rock(b, g, (sd * 5.15, 1.55, 11.1), 0.92, (12, sd * 20, sd * 25), rune=True)
        rock(b, g, (sd * 3.45, 4.2, 11.1), 0.8, (-18, sd * 30, sd * 40), rune=True)
        rock(b, g, (sd * 5.5, -1.95, 10.4), 0.7, (30, sd * 10, sd * 60), rune=sd < 0)
    rock(b, g, (0, 5.75, 10.9), 0.9, (20, 15, 190), rune=True)  # rune faces back


def build_circle(b):
    """Flat segmented amber summoning circle at the feet (Roblox spins this group)."""
    g = "Circle"
    b.pivot(g, (0, 0, 0))
    b.ring(g, tr(0, 0, 0.05), 6.5, 40, 0.1, 0.32, "neon_amber", gap=0.8)
    b.ring(g, tr(0, 0, 0.04), 5.4, 36, 0.08, 0.14, "neon_amber", gap=0.7)  # thin inner ring
    for k in range(12):  # rune ticks between the rings
        b.block(g, (0.14, 0.5, 0.08), rot(0, 0, k * 30 + 5) @ tr(0, -5.95, 0.04), color="neon_amber")


def build(b):
    soften_neon(b)
    build_body(b)
    build_head(b)
    for sd in (-1, 1):
        build_arm(b, sd)
        build_leg(b, sd)
    recentre(b)
    build_shards(b)
    build_circle(b)


if __name__ == "__main__":
    blocky.main(NAME, PALETTE, build, os.path.dirname(os.path.abspath(__file__)))
