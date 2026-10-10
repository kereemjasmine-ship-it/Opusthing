"""Build the NebulaOwl pet (Epic) in Blender, in the Void Hydra's blocky style.

A chubby cosmic void owl hovering upright over a small segmented teal summoning
ring, with a segmented gold halo floating above its head. Everything is a
bevelled block, tapered block, diamond, prism or ring from the shared blocky
builder:

  * a big studded head with a stepped facial disc (belly discs framed by plate
    ruff segments), huge concentric eyes (neon teal ring, teal iris, void pupil,
    bone catch-light), a V brow, a forehead rune, a hooked plate/bone beak whose
    front edges glow gold, shingled ear-covert scales with temple runes, a swept
    neck ruff and pointed feather rows on the back of the head,
  * angled horn-tuft ear feathers (EarL / EarR),
  * an egg-shaped body with a layered chest of small belly scale-feathers with
    dark barred tips, a gold star rune and pointed back feathers,
  * folded wings (WingL / WingR, pivots at the shoulders) made of overlapping
    rows of stepped feather blocks with teal rune diamonds,
  * fluffy feathered legs with plate toes and curled bone talons gripping
    nothing (FootL / FootR),
  * a short fanned tail with pale barred tips (Tail),
  * a teal base ring (Circle), a gold halo (CircleHalo) and gold four-point
    sparkles and teal crystals (Shards).

Run (bpy module):  python build.py [--render] [--samples N] [--res PX] [--views hero,front,side]
  or with Blender:  blender -b -P build.py -- [--render] ...

Coordinates: Z up, the owl faces -Y, design units (blocky.SCALE = 0.4 studs per
unit). The owl is modelled with the bottom of its body at z = 0 and then lifted
by HOVER above the ground ring. Its own left side is +X (WingL, EarL, FootL).
"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
import blocky  # noqa: E402  (imports bpy before bmesh)
import bmesh  # noqa: E402
from blocky import rot, tr  # noqa: E402
from mathutils import Vector  # noqa: E402

NAME = "NebulaOwl"
PALETTE = blocky.Palette(
    blocky.FAMILY + [("neon_teal", "3ff2c8"), ("neon_gold", "ffcf4d")],
    neon=["neon_teal", "neon_gold"],
)

HOVER = 1.5  # the body floats this far above the ring (design units; 1 unit = 0.4 studs)
HALO_Z = 8.75  # height of the floating halo (world, after the lift)
SIDES = (1, -1)  # +1 = the owl's left (+X), -1 = its right (-X)

EYE_X, EYE_Y, EYE_Z = 0.85, -1.49, 4.4  # eye centres (x mirrored), on the facial disc
DISC_R = 1.02  # facial disc radius around each eye


def side_name(side):
    return "L" if side > 0 else "R"


# -- helpers ------------------------------------------------------------------


def lift(b, dz, skip=("Circle", "CircleHalo", "Shards")):
    """Raise every group except the rings and shards by dz (sets the hover height)."""
    for name, bm in b.meshes.items():
        if name.split("_")[0] not in skip:
            bmesh.ops.translate(bm, vec=(0, 0, dz), verts=bm.verts)
    for g in b.pivots:
        if g not in skip:
            b.pivots[g] = b.pivots[g] + Vector((0, 0, dz))


def arc(b, g, frame, radius, n, depth, thick, color, keep=None, gap=1.0):
    """Like Builder.ring, but keep(angle_deg) can drop segments (open rings, ruffs).

    The segment at angle a sits at local (-r sin a, r cos a) in the frame's XY plane.
    """
    chord = 2 * math.pi * radius / n * gap
    for k in range(n):
        a = k * 360 / n
        if keep and not keep(a):
            continue
        b.block(g, (chord, thick, depth), frame @ rot(0, 0, a) @ tr(0, radius, 0), color=color)


def feather(b, g, m, size, color, tip=None):
    """A stepped feather hanging down along local -Z: a block and a narrower tip step."""
    sx, sy, sz = size
    b.block(g, size, m, color=color)
    b.block(g, (sx * 0.8, sy * 0.55, sz * 0.32), m @ tr(0, 0, -sz * 0.6), color=tip or color)


def spike(b, g, m, size, color, top=(0.3, 0.3), shift=(0.0, 0.0)):
    """A tapered spike growing along local +Z from the origin of m."""
    b.taper(g, size, m @ tr(0, 0, size[2] / 2), color=color, top=top, shift=shift)


# -- body -----------------------------------------------------------------------


def build_body(b):
    g = "Body"
    b.pivot(g, (0, 0, 0))
    blk = lambda size, pos, r=(0, 0, 0), **kw: b.block(g, size, tr(*pos) @ rot(*r), **kw)  # noqa: E731

    # egg-shaped torso: stacked blocks, widest at the belly, narrow under the big head
    blk((1.8, 1.7, 0.4), (0, 0.05, 0.2), color="hide")
    blk((2.5, 2.2, 1.0), (0, 0, 0.85), color="hidelight")
    blk((2.75, 2.4, 1.0), (0, 0, 1.8), color="hide")
    blk((2.4, 2.1, 0.8), (0, 0.05, 2.65), color="hidelight", studs=True,
        keep=lambda x, y: abs(x) > 0.9 and y > 0.3)

    # layered feather chest: rows of overlapping belly feathers with stepped tips
    blk((2.0, 0.2, 2.4), (0, -1.22, 1.6), color="hide")
    blk((1.5, 0.2, 0.5), (0, -1.22, 0.35), color="hide")
    for r in range(6):
        z = 2.7 - r * 0.42  # top row first, so lower rows sit in front of the ones above
        n = 4 if r % 2 == 0 else 5
        width = (1.6, 2.0, 2.2, 2.2, 2.0, 1.5)[r]
        pitch = width / 5
        for j in range(n):
            x = (j - (n - 1) / 2) * pitch
            m = tr(x, -1.36 - r * 0.02, z) @ rot(-14, 0, 0)
            # dark plate tips give each row the scalloped barring of an owl's breast
            feather(b, g, m, (pitch * 0.9, 0.12, 0.4), "belly", tip="plate")
    # gold star rune on the chest
    b.diamond(g, 0.34, tr(0, -1.6, 1.75) @ rot(0, 45, 0) @ rot(-45, 0, 0), "neon_gold")
    for sx, sz in ((-1, 0), (1, 0), (0, -1), (0, 1)):  # four teal sparks around it
        blk((0.1, 0.2, 0.1), (sx * 0.36, -1.52, 1.75 + sz * 0.36), r=(0, 45, 0), color="neon_teal")

    # back: shingled rows of pointed feathers (tapered blocks pointing down)
    for r in range(3):
        z = 0.75 + r * 0.7
        for j in range(3):
            x = (j - 1) * 0.72
            m = tr(x * 0.92, 1.22 + 0.02 * r, z) @ rot(15, 0, 0)
            b.taper(g, (0.62, 0.16, 0.8), m @ rot(180, 0, 0), top=(0.5, 1.0),
                    color="plate" if (r + j) % 2 == 0 else "hidelight")


# -- head -----------------------------------------------------------------------


def build_eye(b, g, side):
    """A huge concentric eye: void socket, segmented teal ring, teal iris, void pupil."""
    f = tr(side * EYE_X, EYE_Y, EYE_Z) @ rot(90, 0, 0)  # local Z -> -Y (out of the face), local Y -> up
    oct_flat = rot(0, 0, 22.5)
    b.prism(g, DISC_R, 0.18, f @ oct_flat, color="belly", segments=8)  # facial disc
    # plate ruff around the outer part of each disc (open towards the beak)
    arc(b, g, f @ tr(0, 0, 0.04), DISC_R + 0.08, 12, 0.24, 0.18, "plate",
        keep=lambda a: -math.sin(math.radians(a)) * side > -0.35)
    b.prism(g, 0.74, 0.12, f @ tr(0, 0, 0.12) @ oct_flat, color="void", segments=8)  # socket
    b.ring(g, f @ tr(0, 0, 0.2), 0.6, 12, 0.08, 0.1, "neon_teal", gap=0.8)  # outer glow ring
    b.prism(g, 0.42, 0.08, f @ tr(0, 0, 0.2) @ oct_flat, color="neon_teal", segments=8)  # iris
    b.prism(g, 0.23, 0.08, f @ tr(0, 0, 0.26) @ oct_flat, color="void", segments=8)  # pupil
    b.block(g, (0.11, 0.11, 0.05), f @ tr(-0.09, 0.09, 0.31), color="bone")  # catch-light


def build_head(b):
    g = "Head"
    b.pivot(g, (0, 0, 3.0))  # neck joint
    blk = lambda size, pos, r=(0, 0, 0), **kw: b.block(g, size, tr(*pos) @ rot(*r), **kw)  # noqa: E731

    blk((2.8, 2.3, 0.4), (0, 0.05, 3.1), color="hidelight")  # chin / underside
    blk((3.4, 2.8, 2.2), (0, 0, 4.3), color="hide")  # skull
    blk((2.9, 0.3, 1.9), (0, 1.45, 4.3), color="plate")  # back plate
    for sd in SIDES:
        blk((0.32, 2.3, 1.8), (sd * 1.86, 0.05, 4.25), color="hidelight")  # cheek ruff
        # ear coverts: three brick-offset rows of shingled feather scales, lower and back
        # edges flared out, so the side of the head reads as layered feathers, not a wall
        for r in range(3):
            for j in range(3):
                y = (-0.55 if r % 2 == 0 else -0.9) + j * 0.7
                m = tr(sd * (2.07 + r * 0.02), y, 4.86 - r * 0.47) @ rot(0, -sd * 12, -sd * 6)
                b.taper(g, (0.14, 0.66, 0.56), m @ rot(180, 0, 0), top=(1.0, 0.5),  # points down
                        color="plate" if (r + j) % 2 == 0 else "hide")
        b.diamond(g, 0.2, tr(sd * 2.2, -0.9, 4.42), "neon_teal")  # temple rune on a scale
        for k in range(3):  # neck ruff sweeping back over the shoulder, like the hydra's frills
            m = tr(sd * 2.02, -0.6 + k * 0.7, 3.42) @ rot(0, -sd * 22, -sd * 10)
            b.taper(g, (0.2, 0.7, 0.44), m @ rot(180, 0, 0), top=(1.0, 0.5),
                    color="hidelight" if k % 2 == 0 else "plate")
    for r in range(2):  # shingled rows of pointed feathers on the back of the head
        for j in range(3):
            m = tr((j - 1) * 0.9, 1.62 + r * 0.03, 4.73 - r * 0.6) @ rot(12, 0, 0)
            b.taper(g, (0.86, 0.16, 0.62), m @ rot(180, 0, 0), top=(0.5, 1.0),
                    color="hidelight" if (r + j) % 2 == 0 else "hide")

    # stepped, studded crown (studs cleared where the ear tufts and the top step sit)
    def crown_keep(x, y):
        under_top = abs(x) < 1.05 and -0.7 < y < 0.9
        under_tuft = abs(x) > 0.8 and -0.2 < y < 0.75
        return not (under_top or under_tuft)

    b.diamond(g, 0.26, tr(0, 1.66, 5.05) @ rot(0, 45, 0) @ rot(-45, 0, 0), "neon_teal")  # back runes
    for sd in SIDES:
        b.diamond(g, 0.16, tr(sd * 0.5, 1.64, 5.2) @ rot(0, 45, 0) @ rot(-45, 0, 0), "neon_teal")
    blk((3.0, 2.4, 0.4), (0, 0.05, 5.55), color="hidelight", studs=True, keep=crown_keep)
    blk((2.0, 1.6, 0.3), (0, 0.15, 5.9), color="hide", studs=True)

    # facial disc and eyes
    for sd in SIDES:
        build_eye(b, g, sd)
        # V brow sweeping up and out towards the ear tufts
        blk((1.2, 0.36, 0.3), (sd * 0.76, -1.66, 5.36), (0, -sd * 13, 0), color="plate")
        blk((0.5, 0.3, 0.22), (sd * 1.42, -1.58, 5.58), (0, -sd * 34, 0), color="plate")
    blk((0.5, 0.26, 1.0), (0, -1.56, 4.9), color="hidelight")  # bridge between the eyes
    b.diamond(g, 0.28, tr(0, -1.72, 5.5) @ rot(0, 45, 0) @ rot(-45, 0, 0), "neon_teal")  # forehead rune

    # hooked beak: plate cere with void nostrils, plate upper beak whose front corners glow
    # gold (the glow runs down the beak, not across it, so it never bridges the two eyes)
    # and a bone hook
    blk((0.6, 0.3, 0.24), (0, -1.74, 4.46), color="plate")  # cere
    base = tr(0, -1.66, 4.34) @ rot(165, 0, 0)  # local +Z runs down the beak, +Y faces forward
    spike(b, g, base, (0.66, 0.6, 0.86), "plate", top=(0.45, 0.6))  # narrows to a V
    spike(b, g, base @ tr(0, 0, 0.78) @ rot(24, 0, 0), (0.34, 0.36, 0.46), "bone", top=(0.3, 0.3))
    for sd in SIDES:
        blk((0.12, 0.08, 0.08), (sd * 0.15, -1.9, 4.46), color="void")  # nostrils
        # gold glow along the beak's front corner edge, converging on the hook
        b.block(g, (0.08, 0.08, 0.74), base @ tr(sd * 0.23, 0.23, 0.43) @ rot(8, -sd * 11.8, 0),
                color="neon_gold")
        # chin "beard" feathers either side of the beak
        blk((0.36, 0.2, 0.4), (sd * 0.38, -1.5, 3.36), (-12, 0, sd * 10), color="belly")


def build_ear(b, side):
    """A big horn-tuft of three angled feathers with a bone tip."""
    g = "Ear" + side_name(side)
    base = Vector((side * 1.22, 0.25, 5.65))
    b.pivot(g, base)
    b.block(g, (0.8, 0.8, 0.45), tr(base), color="hidelight")
    m = tr(base) @ rot(-10, side * 32, 0)
    spike(b, g, m, (0.7, 0.55, 1.5), "plate", top=(0.35, 0.5))
    spike(b, g, m @ tr(0, 0, 1.36) @ rot(-8, side * 10, 0), (0.28, 0.26, 0.42), "bone", top=(0.3, 0.3))
    spike(b, g, tr(base + Vector((side * 0.25, 0.2, -0.05))) @ rot(-20, side * 58, 0),
          (0.5, 0.42, 1.0), "hide", top=(0.35, 0.5))
    spike(b, g, tr(base + Vector((-side * 0.22, 0.25, 0.0))) @ rot(-16, side * 12, 0),
          (0.44, 0.38, 0.95), "hidelight", top=(0.35, 0.5))


# -- wings ------------------------------------------------------------------------


def build_wing(b, side):
    """A folded wing hugging the body: overlapping rows of stepped, barred feather blocks."""
    g = "Wing" + side_name(side)
    S = Vector((side * 1.46, 0.05, 2.95))
    b.pivot(g, S)
    W = tr(S) @ rot(0, -side * 6, 0) @ rot(10, 0, 0)  # the lower wing sweeps back and flares out

    def at(x, y, z, r=(0, 0, 0)):  # mirror a local position / rotation onto this side
        return W @ tr(side * x, y, z) @ rot(r[0], side * r[1], side * r[2])

    b.block(g, (0.6, 2.0, 2.5), at(-0.28, 0.35, -1.45), color="hide")  # filler against the body
    b.block(g, (0.62, 1.95, 0.7), at(0.0, 0.1, -0.25), color="plate")  # shoulder cap (under the head)
    b.block(g, (0.5, 0.28, 1.7), at(0.06, -0.95, -1.0), color="plate")  # leading edge
    for i in range(4):  # lesser coverts
        feather(b, g, at(0.12, -0.62 + i * 0.48, -0.85 - i * 0.05), (0.42, 0.52, 0.72),
                "hidelight" if i % 2 == 0 else "hide", tip="plate")
    for i in range(4):  # greater coverts
        feather(b, g, at(0.07, -0.42 + i * 0.5, -1.55 - i * 0.08), (0.4, 0.55, 0.82),
                "hide" if i % 2 == 0 else "hidelight", tip="plate")
    for i in range(5):  # flight feathers with pale barred tips, lowest at the back
        feather(b, g, at(0.0, -0.32 + i * 0.44, -2.25 - i * 0.1), (0.34, 0.48, 1.2),
                "plate" if i % 2 == 0 else "hidelight", tip="belly")
    for i in range(2):  # long primaries crossing behind the tail
        spike(b, g, at(-0.02, 1.45 + i * 0.26, -1.95 - i * 0.2, (205, 0, 0)), (0.3, 0.42, 0.8),
              "plate" if i == 0 else "hide", top=(0.6, 0.4))
    # teal rune diamonds on the coverts
    for y, z in ((-0.3, -1.4), (0.35, -1.75), (1.0, -1.5)):
        b.diamond(g, 0.2, at(0.32, y, z), "neon_teal")


# -- feet and tail ------------------------------------------------------------------


def build_foot(b, side):
    """A fluffy feathered leg peeking out under the chest, plate toes and curled bone talons."""
    g = "Foot" + side_name(side)
    x, y0 = side * 0.62, -0.55
    b.pivot(g, (x, y0, 0.1))
    b.block(g, (0.8, 0.8, 0.55), tr(x, y0, -0.02), color="hidelight")  # feathered "trousers"
    for c in (-1, 0, 1):  # stepped feather fringe over the front of the foot
        b.block(g, (0.3, 0.2, 0.34), tr(x + c * 0.25, y0 - 0.42, -0.2) @ rot(-12, 0, 0),
                color="plate" if c == 0 else "hide")
    b.block(g, (0.66, 0.62, 0.22), tr(x, y0 - 0.12, -0.4), color="hide")  # foot pad
    for c in (-1, 0, 1):  # three splayed front toes, each ending in a curled bone talon
        toe = tr(x + c * 0.21, y0 - 0.36, -0.44) @ rot(0, 0, c * 16)  # local -Y points forward
        b.block(g, (0.19, 0.5, 0.19), toe @ tr(0, -0.2, 0) @ rot(8, 0, 0), color="plate")
        b.block(g, (0.15, 0.16, 0.16), toe @ tr(0, -0.5, 0.0) @ rot(-20, 0, 0), color="bone")
        spike(b, g, toe @ tr(0, -0.56, -0.04) @ rot(205, 0, 0), (0.13, 0.13, 0.3), "bone",
              top=(0.25, 0.25))
    b.block(g, (0.17, 0.34, 0.17), tr(x, y0 + 0.36, -0.44), color="hidelight")  # back toe
    spike(b, g, tr(x, y0 + 0.5, -0.48) @ rot(150, 0, 0), (0.13, 0.13, 0.28), "bone", top=(0.25, 0.25))


def build_tail(b):
    g = "Tail"
    base = Vector((0, 1.05, 0.72))
    b.pivot(g, base)
    for i in range(5):  # a fan of five studded feathers, the middle one longest and on top
        k = i - 2
        length = 1.95 - abs(k) * 0.22
        # pitched down enough to clear the folded wing tips, so it reads from the side and back
        m = tr(base + Vector((0, 0, 0.05 * (2 - abs(k))))) @ rot(0, 0, k * 22) @ rot(-26, 0, 0)
        color = "plate" if k % 2 == 0 else "hidelight"
        b.block(g, (0.46, length, 0.2), m @ tr(0, length / 2, 0), color=color, studs=True,
                keep=lambda x, y: y > -0.2)
        b.block(g, (0.32, 0.3, 0.16), m @ tr(0, length + 0.1, 0), color="belly")  # pale barred tip
        if k % 2 == 0:  # teal rune studs on the middle and outer feather tips
            b.diamond(g, 0.15, m @ tr(0, length - 0.12, 0.14) @ rot(0, 0, 90), "neon_teal")


# -- rings, halo and shards -----------------------------------------------------------


def build_circle(b):
    g = "Circle"
    b.pivot(g, (0, 0, 0))
    b.ring(g, tr(0, 0, 0.05), 2.5, 24, 0.1, 0.26, "neon_teal", gap=0.78)
    b.ring(g, tr(0, 0, 0.05), 2.05, 18, 0.08, 0.12, "neon_teal", gap=0.7)
    for k in range(6):  # gold rune ticks between the two rings
        b.block(g, (0.1, 0.28, 0.06), rot(0, 0, k * 60 + 15) @ tr(0, 2.28, 0.04), color="neon_gold")


def build_halo(b):
    g = "CircleHalo"  # a "Circle" group, so Roblox spins it about the vertical axis
    b.pivot(g, (0, 0, HALO_Z))
    b.ring(g, tr(0, 0, HALO_Z), 1.3, 16, 0.14, 0.24, "neon_gold", gap=0.8)
    b.ring(g, tr(0, 0, HALO_Z), 1.02, 8, 0.08, 0.1, "neon_teal", gap=0.45)


def build_shards(b):
    g = "Shards"
    b.pivot(g, (0, 0, 0))
    # (angle around the owl, radius, height, kind) in point-symmetric pairs (a, a + 180) of the
    # same kind and radius, so the bounding box stays centred on the origin. No shard sits in
    # front of the face in the front view; the ones in front stay low or out at the sides.
    shards = ((110, 3.1, 7.0, "star"), (290, 3.1, 2.3, "star"),
              (310, 2.95, 6.0, "star"), (130, 2.95, 3.2, "star"),
              (85, 3.2, 4.8, "crystal"), (265, 3.2, 3.8, "crystal"),
              (340, 3.35, 1.0, "crystal"), (160, 3.35, 7.6, "crystal"))  # reach past the tail
    for a, r, z, kind in shards:
        m = tr(math.sin(math.radians(a)) * r, -math.cos(math.radians(a)) * r, z) @ rot(0, 0, a)
        if kind == "star":  # gold four-point sparkle: a gem with four tapered rays
            b.diamond(g, 0.17, m @ rot(0, 0, 90), "neon_gold")
            for ray, length in ((rot(0, 0, 0), 0.36), (rot(180, 0, 0), 0.36),
                                (rot(0, 90, 0), 0.25), (rot(0, -90, 0), 0.25)):
                spike(b, g, m @ ray, (0.13, 0.07, length), "neon_gold", top=(0.12, 0.12))
        else:  # teal crystal shard: a tilted bipyramid
            c = m @ rot(18, 25, 0)
            b.taper(g, (0.24, 0.24, 0.3), c @ tr(0, 0, 0.15), color="neon_teal", top=(0.15, 0.15))
            b.taper(g, (0.24, 0.24, 0.24), c @ rot(180, 0, 0) @ tr(0, 0, 0.12), color="neon_teal",
                    top=(0.15, 0.15))


def build(b):
    build_body(b)
    build_head(b)
    build_tail(b)
    for sd in SIDES:
        build_ear(b, sd)
        build_wing(b, sd)
        build_foot(b, sd)
    lift(b, HOVER)  # everything above was modelled with the body bottom at z = 0
    build_circle(b)
    build_halo(b)
    build_shards(b)


if __name__ == "__main__":
    blocky.main(NAME, PALETTE, build, os.path.dirname(os.path.abspath(__file__)),
                rim=(0.3, 1.0, 0.85), rim2=(0.6, 0.35, 1.0))
