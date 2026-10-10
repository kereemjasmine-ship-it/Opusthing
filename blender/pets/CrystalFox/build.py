"""Build the CrystalFox pet (Rare) in the blocky, studded "void pet" style.

A sleek void fox standing alert with glowing crystals growing out of it. Its
big studded head has a narrow stepped snout with a void nose, a slightly open
jaw with bone fangs and teeth around a lilac mouth glow, sly slanted ice-blue
eyes with void slit pupils under angled plate brows, a lilac crystal gem on
the forehead, a belly-coloured muzzle and plate cheek tufts sweeping out and
back. Very tall stepped ears (with sloped fur backs) end in small crystal
clusters. A belly-coloured chest ruff of stepped blocks hangs under the chin,
slim legs end in paws with separate toes and bone claw tips, a ridge of small
crystal shards runs down the studded back, and a big bushy tail (stepped
rounded segments that widen, then narrow, with fur tufts) sweeps back and up
in a J, swishing a little to the fox's left, with crystal shards erupting
along it and a large crystal cluster bursting from its tip. It stands in the
family's segmented summoning circle (ice outer ring, lilac inner ring) with a
few loose crystals floating around it.

Crystals are built from taper() pieces: each shard is a square shaft turned
45 degrees (a diamond cross-section) with a pointed cap, and clusters fan
several shards out at varied angles from a plate socket, alternating neon ice
and neon lilac.

Run with the bpy module:   python build.py [--render] [--samples N] [--res PX] [--views hero,front,side]
or with Blender:           blender -b -P build.py -- [--render] ...

Coordinates: Z up, the fox faces -Y, design units (blocky.SCALE = 0.4 studs).
Everything is built roughly in place, then recentre() puts the paws on z = 0
and centres the fox on the origin; the Circle and Shards groups are added
after that, centred on the origin that Roblox spins and orbits them around.
The fox's left is +X (EarL, LegFL, LegBL).
"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
import blocky  # noqa: E402  (loads bpy before bmesh)
import bmesh  # noqa: E402
from blocky import Vector, rot, tr  # noqa: E402

NAME = "CrystalFox"
# Saturated hexes so the glow keeps its hue instead of blowing out to white:
# ice renders as a pale icy blue, lilac as a soft lilac.
PALETTE = blocky.Palette(
    blocky.FAMILY + [("neon_ice", "4d8eff"), ("neon_lilac", "7d5eff")],
    neon=["neon_ice", "neon_lilac"],
)
ICE, LILAC = "neon_ice", "neon_lilac"

# Main proportions (design units). Head plus ears make up over half the height.
TORSO_Z = 2.3  # centre height of the torso blocks
HEAD = Vector((0.0, -1.95, 3.95))  # skull centre
HEAD_SIZE = (2.4, 2.0, 1.8)
NECK = Vector((0.0, -1.4, 3.05))  # neck block centre (the head turns around it)
EAR_X = 0.74  # ears stand at the outer edges of the skull cap
FRONT_Y, BACK_Y = -0.85, 1.2  # leg rows
FRONT_X, BACK_X = 0.58, 0.62
TAIL_BASE = Vector((0.0, 1.72, 2.62))


def at(x, y, z, rx=0.0, ry=0.0, rz=0.0):
    """Translation then rotation, the usual way every part is placed."""
    return tr(x, y, z) @ rot(rx, ry, rz)


def aim(direction):
    """A rotation whose local +Z points along `direction` (for tufts, eyes and shards).

    Local Y is kept as close to world up (+Z) as possible, local X lies level.
    """
    return Vector(direction).normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()


# -- crystals --------------------------------------------------------------------


def crystal(b, g, base, length, width, color):
    """One crystal shard growing along the local +Z of `base`, from its root.

    A slightly tapering square shaft turned 45 degrees (so its edges catch the
    light like a gem) topped by a pointed cap.
    """
    m = base @ rot(0, 0, 45)
    shaft = length * 0.64
    tip = length - shaft
    b.taper(g, (width, width, shaft), m @ tr(0, 0, shaft / 2), color=color, top=(0.84, 0.84))
    b.taper(g, (width * 0.84, width * 0.84, tip), m @ tr(0, 0, shaft + tip / 2 - 0.02), color=color,
            top=(0.06, 0.06))


# Shards of a cluster: (tilt about X, tilt about Y, length factor, width factor, colour 0/1).
# The first shard is the tall centre one; the rest lean out at varied angles.
CLUSTER = [
    (0, 0, 1.0, 1.0, 0),
    (22, 24, 0.68, 0.72, 1),
    (-26, 18, 0.58, 0.66, 1),
    (16, -30, 0.62, 0.7, 0),
    (-20, -24, 0.5, 0.6, 1),
    (34, -4, 0.45, 0.55, 0),
]


def cluster(b, g, base, length, width, n=5, flip=False, socket=True):
    """A crystal cluster on the local +Z of `base`: n shards fanning out of a plate socket."""
    colors = (LILAC, ICE) if flip else (ICE, LILAC)
    if socket:
        b.block(g, (width * 1.9, width * 1.9, width * 0.6), base @ rot(0, 0, 45), color="plate")
        b.block(g, (width * 1.3, width * 1.3, width * 0.5), base @ tr(0, 0, width * 0.3), color="void")
    for ax, ay, lf, wf, ci in CLUSTER[:n]:
        off = Vector((math.sin(math.radians(ay)), -math.sin(math.radians(ax)), 0)) * width * 0.55
        crystal(b, g, base @ tr(off) @ rot(ax, ay, 0), length * lf, width * wf, colors[ci])


# -- body ------------------------------------------------------------------------


def build_body(b):
    g = "Body"
    z0 = TORSO_Z
    b.pivot(g, (0, 0.2, z0))

    # three torso blocks (chest, middle, hips) alternate hidelight/hide so the
    # seams read; the outer stud columns stay, the spine row is left clear for
    # the crystal ridge
    spine_clear = lambda x, y: abs(x) > 0.3  # noqa: E731
    b.block(g, (1.85, 1.2, 1.5), at(0, -0.8, z0 + 0.05), color="hidelight", studs=True, keep=spine_clear)
    b.block(g, (1.55, 1.0, 1.3), at(0, 0.22, z0), color="hide", studs=True, keep=spine_clear)
    b.block(g, (1.7, 1.05, 1.42), at(0, 1.2, z0 + 0.07), color="hidelight", studs=True, keep=spine_clear)

    # segmented belly plates underneath
    for k, y in enumerate((-0.75, 0.22, 1.15)):
        b.block(g, (1.2 - k * 0.08, 0.85, 0.22), at(0, y, z0 - 0.73), color="belly")

    # neck, leaning forward into the head
    b.block(g, (1.3, 1.1, 1.25), tr(NECK) @ rot(35, 0, 0), color="hide")

    # chest ruff: stepped belly rows pushed forward under the chin, narrowing
    # downwards to a point, with tufts flaring out at the sides
    rows = ((1.7, 2.95), (1.46, 2.58), (1.18, 2.22), (0.9, 1.88), (0.6, 1.56))
    for k, (w, z) in enumerate(rows):
        b.block(g, (w, 0.46, 0.42), at(0, -1.72 + k * 0.07, z, 10, 0, 0),
                color="belly" if k % 2 == 0 else "plate")
    b.taper(g, (0.4, 0.32, 0.4), at(0, -1.42, 1.28, 180 - 10, 0, 0), color="belly", top=(0.2, 0.4))
    for sd in (-1, 1):
        for k in range(3):
            m = tr(sd * (0.72 - k * 0.12), -1.64 + k * 0.06, 2.92 - k * 0.37) @ aim((sd, -0.35, -0.3))
            b.taper(g, (0.3, 0.3, 0.48 - k * 0.07), m @ tr(0, 0, 0.16), color="belly" if k != 1 else "plate",
                    top=(0.25, 0.4))

    # crystal ridge down the back: small clusters leaning back, set in the
    # cleared stud column
    top = z0 + 0.75
    for y, z, s, flip in ((-0.42, top + 0.05, 1.0, False), (0.25, top - 0.1, 0.9, True), (0.95, top + 0.02, 0.8, False)):
        cluster(b, g, at(0, y, z, -22, 0, 0), 0.75 * s, 0.22 * s, n=3, flip=flip)

    for sd in (-1, 1):
        # shoulder pauldrons and hip plates, studded, tilted outwards
        b.block(g, (0.66, 1.05, 0.22), at(sd * 1.0, -0.82, z0 + 0.6, 0, sd * 30, 0), color="plate", studs=True)
        b.block(g, (0.52, 0.85, 0.18), at(sd * 1.1, -0.82, z0 + 0.27, 0, sd * 55, 0), color="plate")
        b.block(g, (0.66, 0.95, 0.22), at(sd * 0.97, 1.2, z0 + 0.58, 0, sd * 30, 0), color="plate", studs=True)
        # flank: a plate diamond with a void socket and a bone stud in it
        b.block(g, (0.1, 0.56, 0.56), at(sd * 0.8, 0.22, z0 - 0.05, 45, 0, 0), color="plate")
        b.block(g, (0.06, 0.3, 0.3), at(sd * 0.84, 0.22, z0 - 0.05, 45, 0, 0), color="void")
        b.block(g, (0.06, 0.1, 0.1), at(sd * 0.87, 0.22, z0 - 0.05, 45, 0, 0), color="bone")


# -- head ------------------------------------------------------------------------


def build_head(b):
    g = "Head"
    b.pivot(g, NECK + Vector((0, 0, 0.35)))
    hm = tr(HEAD)
    hx, hy, hz = (s / 2 for s in HEAD_SIZE)

    def h(size, pos, r=(0, 0, 0), color="hidelight", **kw):
        b.block(g, size, hm @ tr(*pos) @ rot(*r), color=color, **kw)

    # skull: a core block with a slightly inset studded cap (the ears stand on its outer edges)
    h((2.4, 2.0, 1.36), (0, 0, -0.22), color="hidelight")
    h((2.2, 1.8, 0.46), (0, 0.05, hz - 0.23), color="hide", studs=True,
      keep=lambda x, y: not (abs(x) > 0.5 and y > -0.3))
    h((1.9, 0.3, 1.2), (0, hy + 0.08, -0.05), color="plate")  # back plate
    h((1.1, 0.22, 0.42), (0, hy + 0.22, 0.36), color="plate")  # crest step on the back plate

    # narrow stepped snout, each step smaller and a little lower
    h((1.3, 0.62, 0.9), (0, -hy - 0.26, -0.42), color="hide")
    h((0.98, 0.56, 0.72), (0, -hy - 0.8, -0.5), color="hidelight")
    h((0.7, 0.46, 0.56), (0, -hy - 1.28, -0.56), color="hide")
    h((0.42, 1.6, 0.16), (0, -hy - 0.78, -0.02), (-8, 0, 0), color="plate", studs=True)  # snout ridge
    h((0.3, 0.12, 0.75), (0, -hy - 0.03, 0.32), color="plate")  # forehead blaze between the eyes
    h((0.48, 0.26, 0.32), (0, -hy - 1.56, -0.42), color="void")  # nose
    h((0.26, 0.1, 0.08), (0, -hy - 1.66, -0.3), color="plate")  # nose glint
    # pale fox muzzle: belly sides on the lower snout steps
    for sd in (-1, 1):
        h((0.1, 0.5, 0.4), (sd * 0.66, -hy - 0.28, -0.65), color="belly")
        h((0.1, 0.46, 0.32), (sd * 0.5, -hy - 0.8, -0.7), color="belly")

    # lower jaw and chin, belly coloured, hinged under the skull and dropped
    # open a little so the lilac mouth glow shows between the teeth
    jm = hm @ tr(0, -hy, -0.9) @ rot(6, 0, 0)
    b.block(g, (0.92, 1.4, 0.3), jm @ tr(0, -0.64, -0.14), color="belly")
    b.block(g, (0.56, 0.42, 0.2), jm @ tr(0, -1.04, -0.34), color="belly")
    b.block(g, (0.78, 1.2, 0.24), jm @ tr(0, -0.72, 0.04), color=LILAC)  # mouth glow
    for sd in (-1, 1):
        # long bone fangs hanging over the jaw, small upper side teeth and
        # lower teeth set between them
        h((0.12, 0.12, 0.34), (sd * 0.22, -hy - 1.34, -0.94), color="bone")
        for k in range(2):
            h((0.1, 0.1, 0.16), (sd * 0.38, -hy - 0.56 - k * 0.32, -0.92), color="bone")
            b.block(g, (0.09, 0.09, 0.14), jm @ tr(sd * 0.32, -0.72 - k * 0.32, 0.04), color="bone")

        # sly angular eyes: a wedge of ice glow running from the inner corner
        # and narrowing up to the outer corner, set in a slightly larger void
        # wedge, with a void slit pupil and a bone glint, under an angled brow
        eye_dir = Vector((sd, 0, 0.32)).normalized()
        inner = Vector((sd * 0.28, -hy, 0.15))
        # (aim() keeps local Y as close to world up as it can, so local Y is the eye's height)
        b.taper(g, (0.12, 0.48, 0.92), hm @ tr(inner - eye_dir * 0.08 + Vector((0, -0.02, 0))) @ aim(eye_dir)
                @ tr(0, 0, 0.46), color="void", top=(1.0, 0.36))
        b.taper(g, (0.1, 0.34, 0.74), hm @ tr(inner + Vector((0, -0.07, 0))) @ aim(eye_dir) @ tr(0, 0, 0.37),
                color=ICE, top=(1.0, 0.3))
        pupil = inner + eye_dir * 0.24
        h((0.08, 0.12, 0.3), (pupil.x, -hy - 0.1, pupil.z), (0, -sd * 8, 0), color="void")  # slit pupil
        glint = inner + eye_dir * 0.42
        h((0.07, 0.06, 0.07), (glint.x, -hy - 0.14, glint.z + 0.05), color="bone")  # glint
        h((0.92, 0.44, 0.18), (sd * 0.6, -hy + 0.12, 0.58), (0, -sd * 22, 0), color="plate")  # brow
        # pale cheek patch under each eye
        h((0.5, 0.1, 0.34), (sd * 0.88, -hy - 0.03, -0.3), color="belly")

        # side of the skull: a seam panel with a plate rune stud
        h((0.12, 0.9, 0.6), (sd * (hx + 0.02), 0.3, 0.1), color="hide")
        b.diamond(g, 0.22, hm @ tr(sd * (hx + 0.06), 0.3, 0.1), "plate")

        # cheek tufts: a stepped jowl block with tapered plate tufts flaring
        # out and down, giving the face its fox triangle
        h((0.3, 1.2, 0.75), (sd * 1.25, -0.25, -0.5), color="hide")
        # (they fan from slightly up at the front to slightly down at the back,
        # sweeping backwards like fur rather than hanging down like jowls)
        for k in range(3):
            m = hm @ tr(sd * 1.3, -0.62 + k * 0.38, -0.24 - k * 0.2) @ aim((sd, 0.55 + k * 0.25, 0.22 - k * 0.24))
            b.taper(g, (0.4, 0.36, 0.9 - k * 0.14), m @ tr(0, 0, 0.34), color="plate" if k != 1 else "hidelight",
                    top=(0.18, 0.32))

    # lilac crystal gem on the forehead in a plate setting
    h((0.44, 0.12, 0.44), (0, -hy - 0.05, 0.64), (0, 45, 0), color="plate")
    h((0.27, 0.12, 0.27), (0, -hy - 0.1, 0.64), (0, 45, 0), color=LILAC)


def build_ear(b, side):
    """A very tall stepped plate ear with a belly inner panel and a crystal tip."""
    g = "EarL" if side > 0 else "EarR"
    base = HEAD + Vector((side * EAR_X, 0.15, HEAD_SIZE[2] / 2))
    b.pivot(g, base)
    em = tr(base) @ rot(-6, side * 12, 0)
    b.block(g, (0.9, 0.66, 0.32), em @ tr(0, 0.05, 0), color="hide")  # ear root, sunk into the cap
    # two tapered steps: a wide, deep lower ear and a narrow upper ear; the
    # front faces stay flat while the backs slope in, so the profile is a triangle
    b.taper(g, (0.9, 0.62, 1.15), em @ tr(0, 0.06, 0.62), color="plate", top=(0.62, 0.6), shift=(0, -0.12))
    b.taper(g, (0.56, 0.38, 0.95), em @ tr(0, -0.02, 1.62), color="hidelight", top=(0.28, 0.55), shift=(0, -0.08))
    # sloped fur on the back of the lower ear: a deeper base, so the profile is
    # a swept-back triangle rather than a thin post
    b.taper(g, (0.74, 0.36, 0.95), em @ tr(0, 0.4, 0.47), color="hide", top=(0.6, 0.2), shift=(0, -0.4))
    b.taper(g, (0.4, 0.2, 0.4), em @ tr(0, 0.52, 0.2), color="plate", top=(0.5, 0.3), shift=(0, -0.3))
    # belly inner panels on the front face, and a fur tuft at the base
    b.taper(g, (0.58, 0.08, 1.05), em @ tr(0, -0.23, 0.62), color="belly", top=(0.6, 1.0))
    b.taper(g, (0.34, 0.08, 0.8), em @ tr(0, -0.17, 1.55), color="belly", top=(0.3, 1.0))
    b.taper(g, (0.3, 0.2, 0.42), em @ tr(-side * 0.2, -0.28, 0.25) @ rot(-15, -side * 25, 0), color="belly",
            top=(0.2, 0.4))
    # a plate cuff where the two steps meet, with a small bone stud on its back
    b.block(g, (0.66, 0.46, 0.14), em @ tr(0, 0.05, 1.17), color="plate")
    b.block(g, (0.12, 0.08, 0.12), em @ tr(0, 0.3, 1.17) @ rot(0, 45, 0), color="bone")
    # crystal tip: a small cluster bursting out of the ear point
    cluster(b, g, em @ tr(0, 0.04, 2.06), 0.74, 0.22, n=4, flip=side < 0, socket=False)


# -- legs ------------------------------------------------------------------------


def paw(b, g, x, y):
    """Paw block with three toes and bone claw tips."""
    b.block(g, (0.6, 0.72, 0.28), at(x, y - 0.12, 0.14), color="hidelight")
    for c in (-1, 0, 1):
        tx = x + c * 0.2
        b.block(g, (0.18, 0.28, 0.2), at(tx, y - 0.56, 0.1), color="hide")
        b.block(g, (0.1, 0.14, 0.08), at(tx, y - 0.74, 0.05, 15, 0, 0), color="bone")
    b.block(g, (0.3, 0.2, 0.18), at(x, y + 0.27, 0.12), color="hide")  # heel pad


def build_leg(b, side, front):
    x = side * (FRONT_X if front else BACK_X)
    y = FRONT_Y if front else BACK_Y
    g = ("LegF" if front else "LegB") + ("L" if side > 0 else "R")
    b.pivot(g, (x, y, TORSO_Z - 0.3))
    if front:
        b.block(g, (0.64, 0.82, 0.8), at(x, y, 1.75), color="hide")  # shoulder
        b.block(g, (0.5, 0.56, 0.7), at(x, y - 0.03, 1.14), color="hidelight")  # upper foreleg
        b.block(g, (0.36, 0.12, 0.3), at(x, y - 0.32, 1.2), color="plate")  # elbow plate
        b.block(g, (0.42, 0.46, 0.66), at(x, y - 0.05, 0.58), color="hide")  # lower foreleg
        b.taper(g, (0.3, 0.24, 0.4), at(x, y + 0.3, 1.0, -125, 0, 0), color="hidelight", top=(0.3, 0.3))  # tuft
    else:
        b.block(g, (0.72, 1.15, 1.05), at(x + side * 0.06, y, 1.82), color="hide")  # haunch
        b.block(g, (0.52, 0.66, 0.62), at(x, y + 0.12, 1.2, -15, 0, 0), color="hidelight")  # thigh
        b.block(g, (0.42, 0.46, 0.72), at(x, y + 0.14, 0.6), color="hide")  # shin
        b.block(g, (0.32, 0.12, 0.32), at(x, y + 0.4, 0.76), color="plate")  # hock plate
        b.taper(g, (0.4, 0.3, 0.5), at(x + side * 0.08, y + 0.6, 1.62, -110, 0, 0), color="hidelight",
                top=(0.35, 0.3))  # haunch tuft
    b.block(g, (0.52, 0.56, 0.12), at(x, y - 0.03 if front else y + 0.12, 0.33), color="plate")  # cuff
    # a glowing rune on the outside of the shoulder / haunch, in a plate setting
    rx = x + side * (0.33 if front else 0.43)
    ry = y if front else y - 0.1
    rz = 1.75 if front else 1.85
    b.block(g, (0.08, 0.4, 0.4), at(rx, ry, rz, 45, 0, 0), color="plate")
    b.block(g, (0.06, 0.2, 0.2), at(rx + side * 0.04, ry, rz, 45, 0, 0), color=ICE)
    paw(b, g, x, y)


# -- tail ------------------------------------------------------------------------


def fluff(b, g, m, w, ln, hgt, color, studs=False, keep=None):
    """A bushy tail segment: a core block plus a wider and a taller band, giving
    a stepped, rounded (octagon-like) profile instead of a plain box."""
    b.block(g, (w - 0.3, ln, hgt), m, color=color, studs=studs, keep=keep)
    b.block(g, (w, ln * 0.78, hgt - 0.34), m, color=color)
    b.block(g, (w - 0.14, ln * 0.9, hgt - 0.16), m, color=color)


def build_tail(b):
    g = "Tail"
    b.pivot(g, TAIL_BASE)
    # (width, length, height, angle up from +Y, swish toward the fox's left, colour):
    # a J-shaped plume that widens, then narrows. It swishes a little to the
    # fox's left (+X) as it rises, so in the front view its crystal tip hides
    # behind the left ear instead of sitting between the ears like a crown.
    segs = [
        (0.64, 0.55, 0.62, 10, 0, "hide"),
        (1.0, 0.65, 0.96, 18, 6, "hidelight"),
        (1.34, 0.72, 1.26, 27, 12, "hide"),
        (1.52, 0.76, 1.42, 37, 18, "hidelight"),
        (1.5, 0.74, 1.4, 47, 24, "hide"),
        (1.28, 0.68, 1.2, 57, 30, "hidelight"),
        (0.94, 0.6, 0.88, 66, 36, "hide"),
    ]
    p = TAIL_BASE.copy()
    frames = []
    clear = lambda x, y: abs(x) > 0.3  # noqa: E731  (spine of the tail carries crystals)
    for i, (w, ln, hgt, angle, swish, color) in enumerate(segs):
        r = rot(0, 0, -swish) @ rot(angle, 0, 0)
        d = r.to_3x3() @ Vector((0, 1, 0))
        m = tr(p + d * (ln / 2)) @ r
        frames.append((m, w, ln, hgt))
        if i == 0:
            b.block(g, (w, ln, hgt), m, color=color)
        else:
            fluff(b, g, m, w, ln, hgt, color, studs=1 <= i <= 3, keep=clear)
        b.block(g, (w * 0.6, ln * 0.85, 0.12), m @ tr(0, 0, -hgt / 2), color="belly")  # underside fur
        if i >= 1:
            for sd in (-1, 1):  # two layers of fur tufts on the flanks, sweeping back along the tail
                for lz, dz, col in ((-0.2, -0.35, "plate" if i % 2 else "hidelight"),
                                    (0.2, 0.2, "hidelight" if i % 2 else "plate")):
                    tm = m @ tr(sd * w * 0.36, 0.12, hgt * lz) @ aim((sd * 0.9, 0.9, dz))
                    b.taper(g, (0.3, hgt * 0.4, 0.3 + w * 0.3), tm @ tr(0, 0, 0.2), color=col,
                            top=(0.22, 0.35))
        if i >= 2:
            # an underside tuft hanging back
            tm = m @ tr(0, 0.15, -hgt * 0.42) @ aim((0, 0.9, -0.5))
            b.taper(g, (w * 0.4, 0.3, 0.42), tm @ tr(0, 0, 0.15), color="belly", top=(0.3, 0.3))
        p = p + d * (ln * 0.75)  # segments overlap so the plume reads as one mass

    # white-tipped fox tail: a stepped belly cap at the end
    r = rot(0, 0, -40) @ rot(72, 0, 0)
    d = r.to_3x3() @ Vector((0, 1, 0))
    tip = tr(p + d * 0.12) @ r
    b.block(g, (0.72, 0.44, 0.7), tip, color="belly")
    b.block(g, (0.5, 0.3, 0.5), tip @ tr(0, 0.25, 0), color="plate")

    # crystals erupting along the tail: out of the top of the rising part and
    # leaning out of the flanks of the bushy middle
    m, w, ln, hgt = frames[2]
    cluster(b, g, m @ tr(0, 0.0, hgt / 2) @ rot(-34, 0, 0), 0.8, 0.24, n=4)
    m, w, ln, hgt = frames[4]
    for sd in (-1, 1):
        cluster(b, g, m @ tr(sd * w * 0.45, 0.0, hgt * 0.2) @ aim((sd, 0.15, 0.6)), 0.72, 0.22, n=3, flip=sd > 0)
    m, w, ln, hgt = frames[5]  # (leaning out to the swish side, so it stays behind the left ear from the front)
    cluster(b, g, m @ tr(w * 0.22, 0.05, hgt / 2) @ aim((0.55, 0.5, 0.65)), 0.58, 0.2, n=3, flip=True)

    # the big cluster bursting from the tip
    cluster(b, g, tip @ tr(0, 0.38, 0) @ rot(-90, 0, 0), 1.3, 0.34, n=6)


# -- base ring ---------------------------------------------------------------------


def flat_ring(b, g, radius, n, depth, thickness, color, gap):
    """A segmented ground ring like Builder.ring, but with unbevelled segments:
    on blocks this thin the bevel is invisible, and it would quadruple the tris."""
    chord = 2 * math.pi * radius / n * gap
    for k in range(n):
        b.block(g, (chord, thickness, depth), rot(0, 0, k * 360 / n + 7.5) @ tr(0, radius, depth / 2),
                color=color, bevel=0)


def build_circle(b):
    """The family's glowing summoning circle on the ground (Roblox spins "Circle*").
    Built after recentre(), so it is centred on the origin the game spins it around."""
    g = "Circle"
    b.pivot(g, (0, 0, 0))
    flat_ring(b, g, 2.6, 24, 0.1, 0.28, ICE, gap=0.78)
    flat_ring(b, g, 2.16, 18, 0.08, 0.13, LILAC, gap=0.7)
    for k in range(6):  # rune ticks between the two rings
        b.block(g, (0.12, 0.2, 0.06), rot(0, 0, k * 60 + 30) @ tr(0, 2.34, 0.03), color=LILAC, bevel=0)


def build_shards(b):
    """Small loose crystals floating around the fox (Roblox orbits "Shards*" about the
    origin). They stay low (under the head, jaw and tail) and inside the ring, so
    they never pass through the fox while they orbit."""
    g = "Shards"
    b.pivot(g, (0, 0, 0))
    for k in range(6):
        a = math.radians(k * 60 + 15)
        r = 2.2 + (k % 2) * 0.15
        z = 0.85 + (k % 3) * 0.45
        m = tr(math.sin(a) * r, -math.cos(a) * r, z) @ rot(18 + (k % 3) * 14, -20 + k * 9, k * 37)
        crystal(b, g, m @ tr(0, 0, -0.28), 0.56 - (k % 2) * 0.1, 0.2, ICE if k % 2 == 0 else LILAC)


# -- assembly --------------------------------------------------------------------


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


def build(b):
    build_body(b)
    build_head(b)
    for side in (-1, 1):
        build_ear(b, side)
        build_leg(b, side, front=True)
        build_leg(b, side, front=False)
    build_tail(b)
    recentre(b)
    build_circle(b)
    build_shards(b)


if __name__ == "__main__":
    blocky.main(NAME, PALETTE, build, os.path.dirname(os.path.abspath(__file__)),
                rim=(0.55, 0.75, 1.0), rim2=(0.75, 0.5, 1.0))
