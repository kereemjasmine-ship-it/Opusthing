"""Build the ShadowBat pet (Uncommon) in Blender, in the Void Hydra's blocky style.

A chubby void bat hovering with its wings spread over a small segmented cyan
summoning ring. Everything is a bevelled block, tapered block or diamond from
the shared blocky builder: a stacked round-ish body with a shingled fluffy
chest of fur tufts, a big studded head with huge stepped ears (glowing inner
panels), a squashed snout with flared void nostrils, two bone fangs and small
incisors, and real bat wings made of plate
finger bones fanning from a wrist with hide / hidelight membrane panels and
thin plate veins, and thin neon cyan strips along their scalloped trailing edges.

Run (bpy module):  python build.py [--render] [--samples N] [--res PX] [--views hero,front,side]
  or with Blender:  blender -b -P build.py -- [--render] ...

Coordinates: Z up, the bat faces -Y, design units (blocky.SCALE = 0.4 studs per
unit). The bat is modelled with the bottom of its torso at z = 0 and then lifted
by HOVER above the ground ring. Its own left side is +X (WingL, EarL, FootL).
"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
import blocky  # noqa: E402  (imports bpy before bmesh)
import bmesh  # noqa: E402
from blocky import rot, tr  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

NAME = "ShadowBat"
PALETTE = blocky.Palette(
    blocky.FAMILY + [("neon_cyan", "4de1ff"), ("neon_pink", "ff8bf0")],
    neon=["neon_cyan", "neon_pink"],
)

HOVER = 2.5  # the torso floats this far above the ring (design units; 1 unit = 0.4 studs)
SIDES = (1, -1)  # +1 = the bat's left (+X), -1 = its right (-X)

# Wing layout in its own plane: u runs out from the shoulder, v runs up.
SHOULDER = (0.95, 0.3, 1.25)  # where each wing joins the body (x is mirrored)
SWEEP = 22  # degrees the wings sweep back at the shoulder...
CUP = 0.025  # ...and how much they cup forward towards the tips (offset = CUP * u^2)
ARM = [(0.0, 0.0), (0.85, 0.8), (1.95, 1.4)]  # shoulder, elbow, wrist
TIPS = [(4.95, 2.05), (4.85, 0.25), (3.55, -1.1), (1.85, -1.65)]  # finger tips, leading edge first
BODY_ATTACH = (-0.15, -1.3)  # the membrane's last corner, on the body's flank
MEMBRANE = 0.12  # membrane thickness


def side_name(side):
    return "L" if side > 0 else "R"


# -- helpers ------------------------------------------------------------------


def frame(origin, x, y, z):
    """A matrix whose local axes are the unit vectors x, y, z, placed at origin."""
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = origin
    return m


def bar(b, g, p0, p1, thick, width, color, normal, studs=False, keep=None, ext=0.0):
    """A block running from p0 to p1.

    `thick` is measured along `normal`, `width` across it; the block's local +Z
    face is turned upwards, so studs=True studs the bar's top edge.
    """
    p0, p1 = Vector(p0), Vector(p1)
    along = (p1 - p0).normalized()
    z = normal.cross(along).normalized()
    if z.z < 0:
        z = -z
    x = along.cross(z)
    m = frame((p0 + p1) / 2, x, along, z)
    b.block(g, (thick, (p1 - p0).length + ext, width), m, color=color, studs=studs, keep=keep)


def point(b, g, base, direction, normal, size, color, top=(0.2, 0.2)):
    """A tapered spike growing from `base` along `direction` (claws, tufts, finger tips)."""
    z = Vector(direction).normalized()
    x = Vector(normal).cross(z).normalized()
    y = z.cross(x)
    b.taper(g, size, frame(Vector(base) + z * (size[2] / 2), x, y, z), color=color, top=top)


def tri(b, g, apex, p1, p2, thick, color):
    """A thin triangular panel (a wedge-tapered block) with corners apex, p1, p2."""
    apex, p1, p2 = Vector(apex), Vector(p1), Vector(p2)
    base = p2 - p1
    length = base.length
    x = base / length
    rel = apex - p1
    along = rel.dot(x)
    perp = rel - x * along
    h = perp.length
    z = perp / h
    y = z.cross(x)
    m = frame((p1 + p2) / 2 + z * (h / 2), x, y, z)
    b.taper(g, (length, thick, h), m, color=color, top=(0.04, 1.0), shift=((along - length / 2) / length, 0.0))


def strip(b, g, p0, p1, normal, color="neon_cyan", maxlen=1.1, gap=0.08, thick=0.2, width=0.14):
    """A glowing hem along p0 -> p1, cut into segments no longer than maxlen."""
    p0, p1 = Vector(p0), Vector(p1)
    n = max(1, math.ceil((p1 - p0).length / maxlen))
    for i in range(n):
        a, c = p0.lerp(p1, i / n), p0.lerp(p1, (i + 1) / n)
        d = (c - a).normalized()
        bar(b, g, a + d * (gap / 2), c - d * (gap / 2), thick, width, color, normal)


def lift(b, dz, skip=("Circle",)):
    """Raise every group except the ground ring by dz (sets the hover height)."""
    for name, bm in b.meshes.items():
        if name.split("_")[0] not in skip:
            bmesh.ops.translate(bm, vec=(0, 0, dz), verts=bm.verts)
    for g in b.pivots:
        if g not in skip:
            b.pivots[g] = b.pivots[g] + Vector((0, 0, dz))


# -- body -----------------------------------------------------------------------


def build_body(b):
    g = "Body"
    b.pivot(g, (0, 0.1, 0.85))

    # chunky round-ish torso: three stacked blocks, widest in the middle
    b.block(g, (1.7, 1.5, 0.45), tr(0, 0.15, 0.22), color="hide")
    b.block(g, (2.15, 1.85, 1.05), tr(0, 0.1, 0.85), color="hidelight")
    b.block(g, (1.85, 1.65, 0.42), tr(0, 0.15, 1.5), color="hide")
    for sd in SIDES:  # flank bulges round off the sides
        b.block(g, (0.25, 1.4, 0.75), tr(sd * 1.12, 0.15, 0.85), color="hide")

    # fluffy chest: staggered rows of downward-pointing fur tufts, overlapping like
    # shingles, widest in the middle so the bib reads round (count, z, y)
    rows = [(3, 1.3, -0.98), (4, 0.98, -1.02), (3, 0.66, -0.99), (2, 0.36, -0.92), (1, 0.08, -0.8)]
    for n, z, y in rows:
        for k in range(n):
            x = (k - (n - 1) / 2) * 0.44
            b.taper(g, (0.46, 0.5, 0.52), tr(x, y, z) @ rot(180, 0, 0), color="belly", top=(0.3, 0.6))

    b.diamond(g, 0.3, tr(0, -1.3, 0.86), "neon_cyan")  # small rune gem in the fur

    # studded back plates, tilted so their studs face back and up
    b.block(g, (1.4, 1.0, 0.26), tr(0, 0.98, 1.05) @ rot(-68, 0, 0), color="plate", studs=True)
    b.block(g, (1.1, 0.7, 0.24), tr(0, 0.92, 0.35) @ rot(-80, 0, 0), color="plate")

    # studded shoulder pauldrons over the wing joints
    for sd in SIDES:
        b.block(g, (0.95, 1.1, 0.34), tr(sd * 1.0, 0.4, 1.62) @ rot(0, sd * 24, 0), color="plate", studs=True)
        b.block(g, (0.7, 0.9, 0.26), tr(sd * 1.3, 0.4, 1.32) @ rot(0, sd * 42, 0), color="plate")


def build_feet(b):
    """Tiny tucked feet under the body, each with three curled bone claws."""
    for sd in SIDES:
        g = "Foot" + side_name(sd)
        x = sd * 0.52
        b.pivot(g, (x, 0.3, 0.05))
        b.block(g, (0.45, 0.5, 0.4), tr(x, 0.3, -0.1), color="hidelight")  # leg
        b.block(g, (0.66, 0.66, 0.26), tr(x, 0.18, -0.32), color="hide")  # foot
        for c in (-1, 0, 1):
            cx = x + c * 0.21
            b.block(g, (0.15, 0.3, 0.15), tr(cx, -0.17, -0.37) @ rot(25, 0, 0), color="void")
            b.taper(g, (0.13, 0.13, 0.24), tr(cx, -0.28, -0.52) @ rot(160, 0, 0), color="bone", top=(0.2, 0.2))


def build_tail(b):
    """A short stubby tail hanging back from the rump, with a plate tip."""
    g = "Tail"
    b.pivot(g, (0, 0.85, 0.2))
    b.block(g, (0.42, 0.7, 0.34), tr(0, 1.05, 0.05) @ rot(28, 0, 0), color="hide")
    b.block(g, (0.32, 0.6, 0.26), tr(0, 1.5, -0.3) @ rot(45, 0, 0), color="hidelight")
    point(b, g, (0, 1.7, -0.5), (0, 0.55, -0.85), (1, 0, 0), (0.24, 0.24, 0.4), "plate")


# -- head -----------------------------------------------------------------------


def build_head(b):
    g = "Head"
    b.pivot(g, (0, -0.05, 1.55))

    def h(size, pos, r=(0, 0, 0), color="hidelight", **kw):
        b.block(g, size, tr(*pos) @ rot(*r), color=color, **kw)

    h((2.6, 2.2, 1.8), (0, -0.1, 2.4))  # skull
    for sd in SIDES:
        h((0.3, 1.7, 1.15), (sd * 1.38, -0.2, 2.1), color="hide")  # chubby cheeks
    # studded skull cap; studs cleared where the ears and the crown tuft sit
    h((2.2, 1.8, 0.3), (0, 0.0, 3.43), color="plate", studs=True,
      keep=lambda x, y: (abs(x) < 0.5 and y > -0.3) or y > 0.3)
    # back of the head: a studded plate tilted to face back and up, and a fur ruff at the nape
    h((1.9, 0.3, 1.1), (0, 1.02, 2.3), color="hide")
    h((1.8, 1.0, 0.24), (0, 1.0, 3.0), (-65, 0, 0), color="plate", studs=True)
    for k, x in enumerate((-0.72, -0.36, 0.0, 0.36, 0.72)):
        point(b, g, (x, 1.05, 1.95), (x * 0.3, 0.55, -0.85), (1, 0, 0), (0.36, 0.3, 0.5 - abs(x) * 0.15),
              "hidelight" if k % 2 == 0 else "hide", top=(0.15, 0.3))

    h((1.7, 0.1, 0.72), (0, -1.21, 2.0), color="hide")  # darker mask around the snout
    # squashed snout: studded plate ridge, plate nose pad with void nostrils, plate nose-leaf
    h((1.3, 0.5, 0.6), (0, -1.43, 1.98), color="belly")
    h((1.0, 0.45, 0.18), (0, -1.36, 2.35), color="plate", studs=True)
    b.taper(g, (0.66, 0.14, 0.34), tr(0, -1.72, 2.08) @ rot(180, 0, 0), color="plate",
            top=(0.7, 1.0))  # nose pad, wider at the top
    for sd in SIDES:
        h((0.18, 0.08, 0.2), (sd * 0.15, -1.8, 2.07), (0, sd * 25, 0), color="void")  # flared nostrils
    b.taper(g, (0.38, 0.1, 0.36), tr(0, -1.7, 2.38), color="plate", top=(0.2, 1.0))  # nose-leaf

    # mouth: belly chin, a thin pink glow line and two bone fangs
    h((1.1, 0.5, 0.3), (0, -1.32, 1.56), color="belly")
    h((0.85, 0.08, 0.07), (0, -1.65, 1.69), color="neon_pink")
    for sd in SIDES:
        b.taper(g, (0.2, 0.16, 0.44), tr(sd * 0.3, -1.6, 1.62) @ rot(180, 0, 0), color="bone",
                top=(0.2, 0.3))  # fang
        b.taper(g, (0.1, 0.1, 0.17), tr(sd * 0.11, -1.63, 1.66) @ rot(180, 0, 0), color="bone",
                top=(0.35, 0.5))  # little incisor

    # big glowing eyes in void sockets with slit pupils, angled plate brows, widow's peak
    for sd in SIDES:
        h((0.82, 0.14, 0.66), (sd * 0.62, -1.22, 2.6), color="void")
        h((0.62, 0.12, 0.48), (sd * 0.62, -1.26, 2.6), color="neon_cyan")
        h((0.15, 0.05, 0.3), (sd * 0.55, -1.33, 2.57), color="void")
        h((0.8, 0.4, 0.22), (sd * 0.62, -1.12, 3.02), (0, -sd * 12, 0), color="plate")
    b.taper(g, (0.5, 0.16, 0.42), tr(0, -1.25, 3.08) @ rot(180, 0, 0), color="plate", top=(0.15, 1.0))

    # fur tufts sticking out of each cheek, and a little tuft on the crown
    for sd in SIDES:
        for k, (y, z, s) in enumerate(((-0.55, 1.85, 0.5), (-0.1, 1.95, 0.6), (0.35, 2.1, 0.5))):
            point(b, g, (sd * 1.42, y, z), (sd * 0.85, 0.15, -0.5), (0, -1, 0), (0.34, 0.34, s),
                  "belly" if k == 0 else "hidelight", top=(0.15, 0.3))
    for x, ry, s in ((0.0, 0, 0.55), (-0.2, 18, 0.42), (0.2, -18, 0.42)):
        b.taper(g, (0.32, 0.3, s), tr(x, -0.55, 3.58 + s / 2) @ rot(-15, ry, 0), color="hidelight",
                top=(0.2, 0.3))


def build_ear(b, side):
    """A huge stepped ear tilted outwards, with a glowing inner panel."""
    g = "Ear" + side_name(side)
    base = Vector((side * 0.98, 0.0, 3.25))
    b.pivot(g, base)
    em = tr(base) @ rot(0, side * 25, 0) @ rot(0, 0, side * 16) @ rot(-6, 0, 0)

    def e(size, pos, color, r=(0, 0, 0)):
        b.block(g, size, em @ tr(*pos) @ rot(*r), color=color)

    o = side  # +local x points outward on the left ear, inward on the right
    # three stepped sections, each nudged outward so the ear curls out
    e((1.45, 0.6, 0.85), (0, 0, 0.32), "hide")
    e((1.15, 0.55, 0.75), (o * 0.08, 0.02, 1.05), "hidelight")
    b.taper(g, (0.9, 0.5, 1.15), em @ tr(o * 0.16, 0.04, 1.95), color="hide", top=(0.12, 0.5),
            shift=(o * 0.18, 0))
    # inner panel: belly lining with a narrow stepped neon core running up its middle
    e((1.02, 0.08, 0.7), (0, -0.33, 0.36), "belly")
    e((0.8, 0.08, 0.62), (o * 0.08, -0.3, 1.05), "belly")
    b.taper(g, (0.58, 0.08, 0.75), em @ tr(o * 0.16, -0.27, 1.7), color="belly", top=(0.2, 1.0),
            shift=(o * 0.14, 0))
    e((0.34, 0.06, 0.52), (0, -0.38, 0.4), "neon_cyan")
    e((0.26, 0.06, 0.5), (o * 0.08, -0.35, 1.05), "neon_cyan")
    b.taper(g, (0.18, 0.06, 0.5), em @ tr(o * 0.16, -0.32, 1.6), color="neon_cyan", top=(0.3, 1.0),
            shift=(o * 0.1, 0))
    # plate ribs down the back of the ear
    e((0.36, 0.12, 0.8), (o * 0.02, 0.33, 0.36), "plate")
    e((0.28, 0.12, 0.62), (o * 0.08, 0.31, 1.05), "plate")
    # tragus, the notched outer rim and a fur tuft at the base
    b.taper(g, (0.26, 0.12, 0.45), em @ tr(-o * 0.46, -0.38, 0.3), color="belly", top=(0.3, 0.5))
    e((0.18, 0.46, 0.34), (o * 0.78, 0.0, 0.45), "plate", (0, o * 25, 0))
    e((0.16, 0.4, 0.3), (o * 0.66, 0.02, 1.12), "plate", (0, o * 25, 0))
    b.taper(g, (0.4, 0.3, 0.4), em @ tr(-o * 0.35, -0.3, -0.05) @ rot(-35, 0, 0), color="hidelight",
            top=(0.2, 0.3))


# -- wings ------------------------------------------------------------------------


def build_wing(b, side):
    """A bat wing: arm to a wrist, four plate finger bones, membrane panels between."""
    g = "Wing" + side_name(side)
    sw = math.radians(SWEEP)
    U = Vector((side * math.cos(sw), math.sin(sw), 0))  # outward
    V = Vector((0, 0, 1))  # up
    N = U.cross(V) * side  # wing normal, facing front on both wings
    S = Vector((side * SHOULDER[0], SHOULDER[1], SHOULDER[2]))
    b.pivot(g, S)

    def P(uv, w=0.0):
        return S + U * uv[0] + V * uv[1] + N * (w + CUP * uv[0] ** 2)

    def dirn(a, c):
        return (P(c) - P(a)).normalized()

    shoulder, elbow, wrist = ARM

    # membrane: a fan of triangles from the wrist, with scalloped trailing edges
    def notch(a, c, k=0.3):
        m = ((a[0] + c[0]) / 2, (a[1] + c[1]) / 2)
        return (m[0] + (wrist[0] - m[0]) * k, m[1] + (wrist[1] - m[1]) * k)

    chain = TIPS + [BODY_ATTACH]
    edges = []
    for a, c in zip(chain, chain[1:]):
        n = notch(a, c)
        edges += [(a, n), (n, c)]
    panels = edges + [(BODY_ATTACH, shoulder)]
    for k, (p1, p2) in enumerate(panels):
        tri(b, g, P(wrist), P(p1), P(p2), MEMBRANE, "hidelight" if k % 2 == 0 else "hide")
    for p1, p2 in edges:  # glowing hem along the trailing edge
        strip(b, g, P(p1), P(p2), N)

    def along(tip, f):
        return (wrist[0] + (tip[0] - wrist[0]) * f, wrist[1] + (tip[1] - wrist[1]) * f)

    # thin plate veins stretched across each membrane panel, like a real bat's wing fibres
    for t1, t2 in zip(TIPS, TIPS[1:]):
        bar(b, g, P(along(t1, 0.6), 0.05), P(along(t2, 0.6), 0.05), 0.12, 0.1, "plate", N)

    # arm: chunky upper arm, elbow knuckle, studded forearm
    bar(b, g, P(shoulder), P(elbow), 0.55, 0.6, "hidelight", N, ext=0.2)
    bar(b, g, P(elbow) - dirn(shoulder, elbow) * 0.22, P(elbow) + dirn(shoulder, elbow) * 0.22,
        0.5, 0.5, "hide", N)
    bar(b, g, P(elbow), P(wrist), 0.42, 0.42, "plate", N, studs=True, ext=0.1)

    # finger bones: two plate segments with a belly knuckle, ending in a point
    for i, tip in enumerate(TIPS):
        d = dirn(wrist, tip)
        knuckle = (wrist[0] + (tip[0] - wrist[0]) * 0.48, wrist[1] + (tip[1] - wrist[1]) * 0.48)
        bar(b, g, P(wrist), P(knuckle), 0.3, 0.3, "plate", N, ext=0.1)
        bar(b, g, P(knuckle), P(tip), 0.24, 0.24, "plate", N, ext=0.05)
        bar(b, g, P(knuckle) - d * 0.17, P(knuckle) + d * 0.17, 0.36, 0.36, "belly", N)
        point(b, g, P(tip) - d * 0.05, d, N, (0.24, 0.24, 0.42), "bone" if i == 0 else "plate")

    # wrist knuckle and the little thumb claw
    bar(b, g, P(wrist) - dirn(elbow, wrist) * 0.25, P(wrist) + dirn(elbow, wrist) * 0.25, 0.5, 0.5, "belly", N)
    thumb = (wrist[0] - 0.22, wrist[1] + 0.55)
    bar(b, g, P(wrist), P(thumb), 0.22, 0.22, "plate", N, ext=0.08)
    point(b, g, P(thumb), dirn(thumb, (thumb[0] - 0.4, thumb[1] + 0.15)), N, (0.16, 0.16, 0.34), "bone")


# -- summoning ring ------------------------------------------------------------------


def build_circle(b):
    g = "Circle"
    b.pivot(g, (0, 0, 0))
    b.ring(g, tr(0, 0, 0.05), 2.7, 24, 0.1, 0.28, "neon_cyan", gap=0.78)
    b.ring(g, tr(0, 0, 0.05), 2.22, 18, 0.08, 0.14, "neon_cyan", gap=0.7)
    for k in range(8):  # pink rune ticks between the two rings
        b.block(g, (0.1, 0.3, 0.06), rot(0, 0, k * 45 + 22.5) @ tr(0, 2.46, 0.04), color="neon_pink")


def build(b):
    build_body(b)
    build_feet(b)
    build_tail(b)
    build_head(b)
    for sd in SIDES:
        build_ear(b, sd)
        build_wing(b, sd)
    lift(b, HOVER)  # everything above was modelled with the torso bottom at z = 0
    build_circle(b)


if __name__ == "__main__":
    blocky.main(NAME, PALETTE, build, os.path.dirname(os.path.abspath(__file__)),
                rim=(0.3, 0.85, 1.0), rim2=(0.6, 0.35, 1.0))
