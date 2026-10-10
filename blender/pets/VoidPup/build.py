"""Build the VoidPup pet (Common) in the blocky, studded "void pet" style.

A small void wolf pup standing alert: a big boxy studded head with a stepped
snout, a void nose, bone fangs and incisors peeking over the lower jaw, glowing
violet eyes in void sockets under plate brows, a mane of tapered fur tufts
sweeping back off the skull, glowing runes on the sides of the head, and tall
tapered ears with belly inner panels. A neon violet collar of small blocks
rings the neck with a plate diamond tag (a small pink gem set in it) dangling
at the front. Stubby legs end in paws with separate toes and bone claw tips
(and a glowing rune on each paw), a row of plate spikes runs down the studded
back, and a four-step tail curls up behind the rump to a tapered neon violet tip.

Run with the bpy module:   python build.py [--render] [--samples N] [--res PX] [--views hero,front,side]
or with Blender:           blender -b -P build.py -- [--render] ...

Coordinates: Z up, the pup faces -Y, design units (blocky.SCALE = 0.4 studs).
Everything is built roughly in place, then recentre() puts the paws on z = 0
and centres the pup on the origin.

Pet's left is +X (it faces -Y), so EarL / LegFL / LegBL sit on the +X side.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
import blocky  # noqa: E402  (loads bpy before bmesh)
import bmesh  # noqa: E402
from blocky import Vector, rot, tr  # noqa: E402

NAME = "VoidPup"
PALETTE = blocky.Palette(
    blocky.FAMILY + [("neon_violet", "a64dff"), ("neon_pink", "ff8bf0")],
    neon=["neon_violet", "neon_pink"],
)

# Main proportions (design units). The head is about 40% of the pup's height.
HEAD = Vector((0.0, -1.75, 4.15))  # skull centre
HEAD_SIZE = (2.5, 2.2, 2.2)
NECK = Vector((0.0, -1.05, 2.95))  # centre of the neck / collar
NECK_TILT = 45  # degrees the neck leans forward (collar dips at the front)
FRONT_Y, BACK_Y = -0.8, 1.35  # leg rows
FRONT_X, BACK_X = 0.68, 0.72
TAIL_BASE = Vector((0.0, 2.0, 2.3))


def at(x, y, z, rx=0.0, ry=0.0, rz=0.0):
    """Translation then rotation, the usual way every part is placed."""
    return tr(x, y, z) @ rot(rx, ry, rz)


def spike(b, g, matrix, size=(0.26, 0.5, 0.42), color="plate"):
    """A small plate spike leaning back (+Y), made from a tapered block."""
    b.taper(g, size, matrix, color=color, top=(0.3, 0.25), shift=(0.0, 0.22))


# -- body ------------------------------------------------------------------------


def build_body(b):
    g = "Body"
    b.pivot(g, (0, 0.3, 2.0))

    # three torso blocks (chest, middle, hips) alternate hide/hidelight so the
    # seams read; the outer stud columns stay, the spine row is left clear
    spine_clear = lambda x, y: abs(x) > 0.3  # noqa: E731
    b.block(g, (2.2, 1.3, 1.65), at(0, -0.65, 2.05), color="hidelight", studs=True, keep=spine_clear)
    b.block(g, (2.0, 1.0, 1.5), at(0, 0.45, 2.0), color="hide", studs=True, keep=spine_clear)
    b.block(g, (2.1, 1.1, 1.6), at(0, 1.45, 2.0), color="hidelight", studs=True, keep=spine_clear)

    # segmented belly plates underneath
    for k, y in enumerate((-0.65, 0.4, 1.4)):
        b.block(g, (1.5 - k * 0.1, 0.85, 0.25), at(0, y, 1.18), color="belly")

    # chest ruff: belly rows narrowing downwards under the chin
    for k, (w, z) in enumerate(((1.5, 2.3), (1.15, 1.9), (0.75, 1.52))):
        b.block(g, (w, 0.32, 0.42), at(0, -1.38 + k * 0.03, z, 8, 0, 0), color="belly")

    # neck, leaning forward into the head
    nm = tr(NECK) @ rot(NECK_TILT, 0, 0)
    b.block(g, (1.6, 1.5, 1.5), nm, color="hide")

    # collar, low on the neck: a plate band with a neon violet ring of small blocks on it
    cm = nm @ tr(0, 0, -0.15)
    b.ring(g, cm, 0.86, 12, 0.4, 0.12, "plate", gap=1.1)
    b.ring(g, cm, 0.96, 12, 0.26, 0.12, "neon_violet", gap=0.9)
    for k in (-1, 1):  # bone studs either side of the tag
        b.block(g, (0.12, 0.12, 0.12), cm @ rot(0, 0, 180 + k * 30) @ tr(0, 1.02, 0), color="bone")
    # dangling tag: a plate link and loop, then a plate diamond frame with a small
    # pink gem set in its face (a small gem keeps the pink from blooming to white)
    front = cm @ Vector((0, -0.98, 0))
    b.block(g, (0.1, 0.1, 0.24), tr(front + Vector((0, -0.02, -0.12))), color="plate")
    b.block(g, (0.22, 0.08, 0.22), tr(front + Vector((0, -0.03, -0.28))) @ rot(0, 45, 0), color="plate")
    tag = tr(front + Vector((0, -0.05, -0.6))) @ rot(0, 45, 0)
    b.block(g, (0.42, 0.14, 0.42), tag, color="plate")
    b.block(g, (0.2, 0.06, 0.2), tag @ tr(0, -0.08, 0), color="neon_pink")
    for k in (-1, 1):  # bone rivets on the frame's side corners
        b.block(g, (0.07, 0.05, 0.07), tag @ tr(k * 0.12, -0.08, k * 0.12), color="bone")

    # spine spikes down the back
    for y, z, s in ((-0.55, 2.88, 1.0), (0.2, 2.75, 0.95), (0.75, 2.75, 0.9), (1.45, 2.8, 0.85)):
        spike(b, g, at(0, y, z + 0.2 * s), size=(0.26 * s, 0.5 * s, 0.42 * s))

    for side in (-1, 1):
        # shoulder pauldrons and hip plates, studded, tilted outwards
        b.block(g, (0.75, 1.1, 0.24), at(side * 1.08, -0.7, 2.62, 0, side * 28, 0), color="plate", studs=True)
        b.block(g, (0.6, 0.9, 0.2), at(side * 1.2, -0.7, 2.3, 0, side * 50, 0), color="plate")
        b.block(g, (0.75, 1.0, 0.24), at(side * 1.07, 1.45, 2.62, 0, side * 28, 0), color="plate", studs=True)
        # flank: a plate diamond with a small glowing rune set into it
        b.block(g, (0.1, 0.62, 0.62), at(side * 1.0, 0.45, 2.0, 45, 0, 0), color="plate")
        b.block(g, (0.06, 0.24, 0.24), at(side * 1.05, 0.45, 2.0, 45, 0, 0), color="neon_violet")


# -- head ------------------------------------------------------------------------


def build_head(b):
    g = "Head"
    b.pivot(g, NECK + Vector((0, 0, 0.3)))
    hm = tr(HEAD)
    hx, hy, hz = (s / 2 for s in HEAD_SIZE)

    def h(size, pos, r=(0, 0, 0), color="hidelight", **kw):
        b.block(g, size, hm @ tr(*pos) @ rot(*r), color=color, **kw)

    # skull: a core block with a slightly inset studded cap (the ears stand on it)
    h((2.5, 2.2, 1.75), (0, 0, -0.225), color="hidelight")
    h((2.3, 2.0, 0.5), (0, 0.05, hz - 0.25), color="hide", studs=True,
      keep=lambda x, y: not (abs(x) > 0.5 and abs(y) < 0.3))
    h((2.1, 0.3, 1.25), (0, hy + 0.08, 0.15), color="plate")  # back plate

    # mane: tapered fur tufts sweeping back off the top and back of the skull, so
    # the head is not a plain box from the side and the back
    for k, (x, z, length, color) in enumerate((
        (-0.62, 0.72, 0.75, "hidelight"), (0.0, 0.82, 0.85, "plate"), (0.62, 0.72, 0.75, "hidelight"),
        (-0.36, 0.12, 0.65, "plate"), (0.36, 0.12, 0.65, "plate"),
    )):
        m = hm @ tr(x, hy + 0.18, z) @ rot(-62 if z > 0.5 else -78, 0, -x * 22)
        b.taper(g, (0.55, 0.42, length), m @ tr(0, 0, length / 2 - 0.1), color=color, top=(0.25, 0.3))

    # stepped snout
    h((1.6, 0.8, 1.0), (0, -hy - 0.35, -0.55), color="hide")  # muzzle, step 1
    h((1.2, 0.65, 0.8), (0, -hy - 0.98, -0.52), color="hidelight")  # muzzle, step 2
    h((0.5, 1.4, 0.18), (0, -hy - 0.62, -0.02), color="plate", studs=True)  # snout ridge
    h((0.34, 0.1, 0.62), (0, -hy - 0.03, 0.3), color="plate")  # forehead blaze between the eyes
    h((0.62, 0.3, 0.38), (0, -hy - 1.36, -0.24), color="void")  # nose
    h((0.36, 0.12, 0.1), (0, -hy - 1.5, -0.08), color="plate")  # nose highlight

    # lower jaw and chin, belly coloured, set back under the muzzle
    h((1.3, 1.2, 0.36), (0, -hy - 0.45, -1.2), color="belly")
    h((0.8, 0.4, 0.22), (0, -hy - 0.85, -1.42), color="belly")
    h((1.05, 0.5, 0.1), (0, -hy - 0.9, -0.97), color="neon_violet")  # mouth glow in the jaw slit
    for sd in (-1, 1):
        # fangs peeking over the jaw, tiny front incisors and two little side teeth
        h((0.14, 0.14, 0.3), (sd * 0.36, -hy - 1.2, -1.0), color="bone")
        h((0.09, 0.09, 0.14), (sd * 0.13, -hy - 1.22, -0.98), color="bone")
        h((0.11, 0.11, 0.18), (sd * 0.52, -hy - 0.85, -0.95), color="bone")

        # eyes: void socket, violet glow, a bone glint, plate brow
        h((0.8, 0.14, 0.64), (sd * 0.62, -hy - 0.03, 0.28), color="void")
        h((0.58, 0.1, 0.46), (sd * 0.62, -hy - 0.1, 0.26), color="neon_violet")
        h((0.13, 0.06, 0.13), (sd * 0.76, -hy - 0.16, 0.4), color="bone")
        h((0.85, 0.48, 0.2), (sd * 0.62, -hy + 0.1, 0.72), (0, -sd * 7, 0), color="plate")

        # side of the skull: a stepped seam panel with a plate rune stud, and two
        # fur tufts behind it sweeping back past the back plate
        h((0.12, 1.0, 0.7), (sd * (hx + 0.02), 0.35, 0.05), color="hide")
        h((0.1, 0.6, 0.12), (sd * (hx + 0.04), 0.35, 0.44), color="plate")  # brow of the panel
        # a plate diamond with a small glowing rune, echoing the flank runes on the body
        h((0.1, 0.44, 0.44), (sd * (hx + 0.07), 0.35, 0.05), (45, 0, 0), color="plate")
        h((0.06, 0.18, 0.18), (sd * (hx + 0.11), 0.35, 0.05), (45, 0, 0), color="neon_violet")
        for k, (z, length) in enumerate(((0.55, 0.6), (-0.15, 0.7))):
            m = hm @ tr(sd * (hx - 0.12), hy - 0.15, z) @ rot(-80, 0, -sd * 32)
            b.taper(g, (0.4, 0.36, length), m @ tr(0, 0, length / 2), color="hidelight" if k else "plate",
                    top=(0.25, 0.3))

        # cheek ruff: stepped blocks and tapered tufts sweeping out and back
        h((0.34, 1.2, 0.7), (sd * 1.3, -0.15, -0.7), color="hide")
        h((0.3, 0.8, 0.45), (sd * 1.45, 0.15, -0.95), (0, 0, -sd * 12), color="hidelight")
        for k in range(3):
            m = hm @ tr(sd * 1.5, -0.35 + k * 0.38, -0.55 - k * 0.12) @ rot(0, sd * (100 + k * 10), sd * 25)
            b.taper(g, (0.36, 0.34, 0.5), m, color="plate" if k % 2 == 0 else "hidelight", top=(0.3, 0.4))


def build_ear(b, side):
    """A tall tapered plate ear with a belly inner panel, standing on the skull cap."""
    g = "EarL" if side > 0 else "EarR"
    base = HEAD + Vector((side * 0.72, 0.08, HEAD_SIZE[2] / 2))
    b.pivot(g, base)
    em = tr(base) @ rot(-4, side * 14, 0)
    b.block(g, (0.95, 0.5, 0.3), em @ tr(0, 0.02, 0.0), color="hide")  # ear root, sunk into the cap
    # flat front face, back sloping forward to the tip
    b.taper(g, (0.95, 0.44, 1.25), em @ tr(0, 0, 0.72), color="plate", top=(0.12, 0.5), shift=(0, -0.25))
    b.taper(g, (0.6, 0.08, 0.9), em @ tr(0, -0.24, 0.6), color="belly", top=(0.15, 1.0))


# -- legs ------------------------------------------------------------------------


def paw(b, g, x, y, side):
    """Paw block with three toes, bone claw tips and a glowing rune on the outside."""
    b.block(g, (0.82, 0.95, 0.36), at(x, y - 0.18, 0.18), color="hide")
    for c in (-1, 0, 1):
        tx = x + c * 0.27
        b.block(g, (0.24, 0.32, 0.26), at(tx, y - 0.72, 0.13), color="hidelight")
        b.block(g, (0.12, 0.14, 0.1), at(tx, y - 0.92, 0.05), color="bone")
    b.block(g, (0.06, 0.26, 0.26), at(x + side * 0.42, y - 0.15, 0.2, 45, 0, 0), color="neon_violet")


def build_leg(b, side, front):
    x = side * (FRONT_X if front else BACK_X)
    y = FRONT_Y if front else BACK_Y
    g = ("LegF" if front else "LegB") + ("L" if side > 0 else "R")
    b.pivot(g, (x, y, 1.55))
    if front:
        b.block(g, (0.85, 1.0, 0.9), at(x, y, 1.45), color="hide")  # shoulder
        b.block(g, (0.68, 0.72, 0.85), at(x, y - 0.05, 0.72), color="hidelight")  # foreleg
        b.block(g, (0.48, 0.14, 0.4), at(x, y - 0.44, 0.9), color="plate")  # elbow plate
        b.taper(g, (0.46, 0.34, 0.6), at(x + side * 0.08, y + 0.48, 1.08, -125, 0, 0), color="plate",
                top=(0.35, 0.3))  # elbow tuft
    else:
        b.block(g, (0.82, 1.25, 1.15), at(x + side * 0.1, y, 1.5), color="hide")  # haunch
        b.block(g, (0.64, 0.7, 0.8), at(x, y + 0.05, 0.68), color="hidelight")  # shin
        b.block(g, (0.45, 0.14, 0.38), at(x, y + 0.43, 0.75), color="plate")  # hock plate
        b.taper(g, (0.56, 0.38, 0.62), at(x + side * 0.12, y + 0.64, 1.3, -115, 0, 0), color="plate",
                top=(0.35, 0.3))  # haunch tuft
    b.block(g, (0.76, 0.8, 0.12), at(x, y - 0.05 if front else y + 0.05, 0.42), color="plate")  # cuff
    paw(b, g, x, y, side)


# -- tail ------------------------------------------------------------------------


def build_tail(b):
    g = "Tail"
    b.pivot(g, TAIL_BASE)
    # (width, length, height, angle up from +Y in degrees, colour): sweeps back, then
    # curls up and a little forward, so the tip stays clear of the head
    segs = [
        (0.82, 0.85, 0.8, 8, "hide"),
        (0.74, 0.75, 0.72, 35, "hidelight"),
        (0.64, 0.62, 0.62, 65, "hide"),
        (0.56, 0.5, 0.54, 95, "hidelight"),
    ]
    p = TAIL_BASE.copy()
    for i, (w, length, hgt, angle, color) in enumerate(segs):
        r = rot(angle, 0, 0)
        d = r.to_3x3() @ Vector((0, 1, 0))
        m = tr(p + d * (length / 2)) @ r
        b.block(g, (w, length, hgt), m, color=color)
        b.block(g, (w * 0.7, length * 0.8, 0.1), m @ tr(0, 0, hgt / 2), color="belly")  # inner fur
        b.diamond(g, 0.34 - i * 0.04, m @ tr(0, 0, -hgt / 2 - 0.02), "plate")  # ridge on the outside
        if i < 3:
            for sd in (-1, 1):  # fur tufts on the flanks of the tail
                b.block(g, (0.12, length * 0.55, hgt * 0.5), m @ tr(sd * w / 2, 0.05, -0.08), color="plate")
        p = p + d * (length * 0.85)
    # neon tip: a plate cuff, then a tapered glowing tuft like a flame
    angle = 120
    r = rot(angle, 0, 0)
    d = r.to_3x3() @ Vector((0, 1, 0))
    b.block(g, (0.54, 0.2, 0.54), tr(p + d * 0.05) @ r, color="plate")
    b.taper(g, (0.46, 0.46, 0.66), tr(p + d * 0.46) @ rot(angle - 90, 0, 0), color="neon_violet",
            top=(0.3, 0.3))


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


if __name__ == "__main__":
    blocky.main(NAME, PALETTE, build, os.path.dirname(os.path.abspath(__file__)))
