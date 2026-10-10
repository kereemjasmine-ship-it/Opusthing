"""Wheels for the Sur-Ron Light Bee X: groups FrontWheel and RearWheel.

Each wheel is built around its axle (the group pivot) and spins about X:

  * knobby off-road tyre: a lathed, rounded carcass plus raised knob blocks
    in staggered rows (centre, intermediate and shoulder knobs),
  * 19" rim with bead flanges and a channel on its inner face, valve stem,
  * 36 spokes laced 3-cross from the hub flanges to the rim,
  * hub with flanges, axle, spacers and axle nut,
  * front: floating wave brake disc on a dark carrier (rider's left, +X),
  * rear: wave brake disc on the right (-X) and a ~58-tooth sprocket with
    lightening cut-outs on the left (+X, chain side).

Not modelled here (other parts): calipers, fork, swingarm, chain.

Wheel-local coordinates used throughout: a point is described by
(x, r, ang) = (offset along the axle, radius, angle around the axle), with
ang = 0 straight down and increasing towards +Y (see wpos). Flat parts
(discs, sprocket, carrier) are drawn as 2D outlines in the plane of the
wheel and placed with wheel_matrix(), which maps local XY onto the wheel
plane and local Z onto the axle (+X).
"""

import math

from mathutils import Vector, geometry

import midpoly as mp
import spec

# -- tuning ------------------------------------------------------------------------
TYRE_SEGMENTS = 40  # around the carcass (the knobs carry the silhouette)
RIM_SEGMENTS = 40
HUB_SEGMENTS = 20
SPOKE_SIDES = 6  # spokes are ~4 mm thick: six sides read round at any distance
SPOKES = 36
SPOKE_CROSS = 3  # 3-cross lacing, like a real MX wheel
# The front axle shaft, nut and head are clamped in the fork, so parts/front_end.py builds them in
# ForkLowers (they must not spin with the wheel) while spec.FRONT_AXLE_IN_FORK is True; otherwise here.
# (The rear axle and nut belong to the swingarm in parts/chassis.py, so the rear wheel only has spacers.)
FRONT_AXLE_NUT = not spec.FRONT_AXLE_IN_FORK

KNOB_HEIGHT = 0.0125  # knob tips sit on spec.WHEEL_RADIUS
CROWN_R = spec.WHEEL_RADIUS - KNOB_HEIGHT  # carcass radius at the tread centre
BEAD_R = spec.RIM_RADIUS + 0.0017  # where the tyre bead disappears into the rim
CARCASS_HALF_W = spec.TYRE_WIDTH / 2 - 0.004  # shoulder knobs stick out past the carcass

# Rim cross-section measurements (relative to the bead seat radius).
RIM_FLANGE_R = spec.RIM_RADIUS + 0.0062  # top of the bead flanges
RIM_INNER_R = spec.RIM_RADIUS - 0.0223  # inner (hub-facing) surface
RIM_HALF_W = spec.RIM_WIDTH / 2


# -- small geometry helpers -------------------------------------------------------------


def wpos(axle, x, r, ang):
    """World point at axle offset x, radius r, angle ang (radians, 0 = down)."""
    return axle + Vector((x, r * math.sin(ang), -r * math.cos(ang)))


def wheel_matrix(axle, x=0.0):
    """Local frame in the wheel plane at axle offset x: local Z = +X (axle), local XY = wheel plane.

    It matches lathe() and wpos(): local (r cos a, r sin a) lands on wpos(axle, x, r, a).
    """
    return mp.tr(axle + Vector((x, 0.0, 0.0))) @ mp.rot(0, 90, 0)


def polar(r, ang):
    """2D point in the wheel plane (for outlines used with wheel_matrix)."""
    return (r * math.cos(ang), r * math.sin(ang))


def arc(r, a0, a1, n):
    """n+1 points on an arc of radius r from angle a0 to a1."""
    return [polar(r, a0 + (a1 - a0) * i / n) for i in range(n + 1)]


def window(r_out, r_in, a0, a1, inset, n_out=4, n_in=2):
    """Lightening window between two arms: outer arc a0 -> a1, inner arc back, narrowed by `inset` (radians)."""
    return arc(r_out, a0, a1, n_out) + arc(r_in, a1 - inset, a0 + inset, n_in)


def stadium(cx, cy, length, width, angle, n_end=3):
    """2D slot outline (rounded ends), centred at (cx, cy), long axis at `angle`."""
    ca, sa = math.cos(angle), math.sin(angle)
    hl, hw = length / 2 - width / 2, width / 2
    pts = []
    for end, a0 in ((hl, -math.pi / 2), (-hl, math.pi / 2)):
        for k in range(n_end + 1):
            a = a0 + math.pi * k / n_end
            u, v = end + hw * math.cos(a), hw * math.sin(a)
            pts.append((cx + u * ca - v * sa, cy + u * sa + v * ca))
    return pts


def plate(m, group, loops, thickness, color, matrix):
    """Flat plate of `thickness` (centred on local z = 0) from 2D loops: [outline, hole, hole, ...].

    Faces are triangulated with holes (mathutils tessellation), so slotted discs
    and sprockets with cut-outs stay light; side walls close every loop.
    """
    flat = [[Vector((x, y, 0.0)) for x, y in loop] for loop in loops]
    tris = geometry.tessellate_polygon(flat)
    pts = [p for loop in loops for p in loop]
    n = len(pts)
    t = thickness / 2
    verts = [(x, y, t) for x, y in pts] + [(x, y, -t) for x, y in pts]
    faces = [(a, b, c) for a, b, c in tris] + [(c + n, b + n, a + n) for a, b, c in tris]
    start = 0
    for loop in loops:
        k = len(loop)
        for i in range(k):
            a, b = start + i, start + (i + 1) % k
            faces.append((a, b, b + n, a + n))
        start += k
    m.mesh(group, verts, faces, color, matrix=matrix)


def ring_of(m, group, axle, x, r, count, radius, depth, color, segments=6, phase=0.0):
    """`count` small bolt heads / buttons along the axle direction on a circle of radius r."""
    for i in range(count):
        ang = phase + 2 * math.pi * i / count
        p = wpos(axle, x, r, ang)
        m.cylinder(group, radius, depth, color, matrix=mp.tr(p) @ mp.rot(0, 90, 0), segments=segments)


# -- tyre -------------------------------------------------------------------------------

# Half of the carcass cross-section as (radius, axial offset), from the tread centre
# out over the shoulder and down the sidewall to the bead. Built from the spec sizes
# so the tyre follows any change to WHEEL_RADIUS / TYRE_WIDTH / RIM_RADIUS.
_HALF = [(1.000, 0.000), (0.872, 0.657), (0.716, 0.890), (0.495, 1.000), (0.275, 0.959), (0.000, 0.452)]
CARCASS_HALF = [(BEAD_R + u * (CROWN_R - BEAD_R), v * CARCASS_HALF_W) for u, v in _HALF]


def _seg_normal(i):
    """Outward unit normal (nr, nh) of carcass half-profile segment i."""
    (r0, h0), (r1, h1) = CARCASS_HALF[i], CARCASS_HALF[i + 1]
    seg = math.hypot(r1 - r0, h1 - h0)
    return (h1 - h0) / seg, -(r1 - r0) / seg


def _vertex_normals():
    """Profile normals averaged at each point so knobs follow the carcass smoothly."""
    n = len(CARCASS_HALF)
    out = []
    for i in range(n):
        if i == 0:
            out.append((1.0, 0.0))  # tread centre: straight out
            continue
        a = _seg_normal(i - 1)
        b = _seg_normal(min(i, n - 2))
        v = Vector((a[0] + b[0], a[1] + b[1])).normalized()
        out.append((v.x, v.y))
    return out


_NORMALS = _vertex_normals()


def _carcass_frame(s):
    """Point (r, h) and outward unit normal (nr, nh) at arc length s across the tread (s < 0 = -X side)."""
    side = -1.0 if s < 0 else 1.0
    s = abs(s)
    pts = CARCASS_HALF
    for i in range(len(pts) - 1):
        (r0, h0), (r1, h1) = pts[i], pts[i + 1]
        seg = math.hypot(r1 - r0, h1 - h0)
        if s <= seg or i == len(pts) - 2:
            f = min(s / seg, 1.0)
            r, h = r0 + (r1 - r0) * f, h0 + (h1 - h0) * f
            n0, n1 = _NORMALS[i], _NORMALS[i + 1]
            nv = Vector((n0[0] + (n1[0] - n0[0]) * f, n0[1] + (n1[1] - n0[1]) * f)).normalized()
            return r, h * side, nv.x, nv.y * side
        s -= seg
    raise AssertionError


def tyre_carcass(m, group, axle):
    """Rounded tyre body: the full closed cross-section revolved around the axle."""
    half = CARCASS_HALF
    prof = [(r, -h) for r, h in reversed(half)] + [(r, h) for r, h in half[1:]]
    m.lathe(group, prof, "rubber", matrix=wheel_matrix(axle), segments=TYRE_SEGMENTS, closed=True)


def knob(m, group, axle, ang, s, width, length, height, taper=0.0028, embed=0.003):
    """One tread block on the carcass at angle `ang`, centred at arc length s across the tread.

    The base corners sit on the carcass at s +- width/2 (pushed slightly in so
    the block never floats over the curved shoulder); the top is a flat face
    square to the carcass normal at the block centre, `height` above it, a
    little smaller than the base so the sides taper like a moulded knob.
    Five quads (10 tris); the buried base needs no face.
    """
    rc, hc, nr, nh = _carcass_frame(s)
    tr_, th = -nh, nr  # profile tangent at the centre, pointing towards +s
    verts = []
    hw, hl = width / 2, length / 2
    for sb, sa in ((-hw, -hl), (hw, -hl), (hw, hl), (-hw, hl)):  # base ring, buried
        r, h, nr0, nh0 = _carcass_frame(s + sb)
        verts.append(wpos(axle, h - nh0 * embed, r - nr0 * embed, ang + sa / CROWN_R))
    hw, hl = hw - taper, hl - taper
    for sb, sa in ((-hw, -hl), (hw, -hl), (hw, hl), (-hw, hl)):  # flat top
        r = rc + nr * height + tr_ * sb
        h = hc + nh * height + th * sb
        verts.append(wpos(axle, h, r, ang + sa / r))
    faces = [(i, (i + 1) % 4, 4 + (i + 1) % 4, 4 + i) for i in range(4)]
    faces.append((4, 5, 6, 7))
    m.mesh(group, verts, faces, "rubber")


def tyre_knobs(m, group, axle, pattern, cycles, phase=0.0):
    """Repeat a knob pattern around the tyre.

    pattern: [(row_offset 0..1 of one pitch, s across tread, width, length, height), ...]
    """
    pitch = 2 * math.pi / cycles
    for c in range(cycles):
        base = phase + c * pitch
        for row, s, w, ln, ht in pattern:
            knob(m, group, axle, base + row * pitch, s, w, ln, ht)


# Front: rows alternate a wide centre knob + two shoulder knobs, then a pair of
# intermediate knobs (the classic MX front pattern).
FRONT_KNOBS = [
    (0.0, 0.0, 0.024, 0.019, KNOB_HEIGHT),
    (0.0, 0.0298, 0.017, 0.019, KNOB_HEIGHT - 0.0015),
    (0.0, -0.0298, 0.017, 0.019, KNOB_HEIGHT - 0.0015),
    (0.5, 0.0155, 0.017, 0.018, KNOB_HEIGHT),
    (0.5, -0.0155, 0.017, 0.018, KNOB_HEIGHT),
]
FRONT_KNOB_CYCLES = 26

# Rear: squarer, wider blocks (drive paddles), same alternating layout.
REAR_KNOBS = [
    (0.0, 0.0, 0.028, 0.021, KNOB_HEIGHT),
    (0.0, 0.0300, 0.018, 0.021, KNOB_HEIGHT - 0.0015),
    (0.0, -0.0300, 0.018, 0.021, KNOB_HEIGHT - 0.0015),
    (0.5, 0.0160, 0.018, 0.020, KNOB_HEIGHT),
    (0.5, -0.0160, 0.018, 0.020, KNOB_HEIGHT),
]
REAR_KNOB_CYCLES = 24


def tyre(m, group, axle, pattern, cycles):
    tyre_carcass(m, group, axle)
    tyre_knobs(m, group, axle, pattern, cycles)


# -- rim ----------------------------------------------------------------------------------


def rim(m, group, axle, color="black"):
    """Rim cross-section revolved: bead flanges, flat side walls and a channel on the inner face."""
    R, fl, inn, hw = spec.RIM_RADIUS, RIM_FLANGE_R, RIM_INNER_R, RIM_HALF_W
    prof = [
        (fl, hw - 0.0015),  # flange lip (tyre bead tucks inside it)
        (R - 0.0035, hw),  # flange outer edge
        (inn + 0.0055, hw - 0.0005),  # side wall
        (inn, hw - 0.004),  # rounded inner edge
        (inn, 0.0060),  # inner face
        (inn + 0.0018, 0.0042),  # channel down the middle (spoke nipples sit in it)
        (inn + 0.0018, -0.0042),
        (inn, -0.0060),
        (inn, -hw + 0.004),
        (inn + 0.0055, -hw + 0.0005),
        (R - 0.0035, -hw),
        (fl, -hw + 0.0015),
    ]
    m.lathe(group, prof, color, matrix=wheel_matrix(axle), segments=RIM_SEGMENTS, closed=True)


def valve_stem(m, group, axle, ang):
    """Valve stem poking inwards from the rim channel, with a black cap."""
    p0 = wpos(axle, 0.0, RIM_INNER_R + 0.0025, ang)  # seated in the channel floor
    inward = (axle - p0).normalized()  # p0 lies in the wheel plane, so this points at the axle
    stem_len, cap_len = 0.013, 0.010
    m.cylinder(group, 0.0034, stem_len, "steel", matrix=mp.look(p0 + inward * stem_len / 2, inward), segments=8)
    m.cylinder(group, 0.0045, cap_len, "black", matrix=mp.look(p0 + inward * (stem_len + cap_len / 2), inward),
               segments=8)


# -- spokes ---------------------------------------------------------------------------------


def spokes(m, group, axle, flange_x, hole_r):
    """36 spokes, 18 per side, laced SPOKE_CROSS-cross.

    Hub holes on each flange are 20 degrees apart (the right flange is turned
    half a hole). Neighbouring spokes leave the hub in opposite directions,
    and the spokes going one way start on the outer face of the flange, the
    others on the inner face, so crossing spokes pass beside each other.
    Each spoke ends in a slightly thicker nipple sitting in the rim channel.
    """
    per_side = SPOKES // 2
    step = 2 * math.pi / per_side
    sweep = SPOKE_CROSS * 2 * step / 2  # angle between hub hole and rim hole (3-cross: 60 deg)
    rim_r = RIM_INNER_R + 0.0025  # nipples end inside the rim channel
    nipple_r = RIM_INNER_R - 0.011
    for side in (1, -1):
        for i in range(per_side):
            hub_ang = i * step + (0.0 if side > 0 else step / 2)
            lead = 1 if i % 2 == 0 else -1
            rim_ang = hub_ang + lead * sweep
            fx = side * (flange_x + lead * 0.0022)
            rim_x = side * 0.0035
            a = wpos(axle, fx, hole_r, hub_ang)
            c = wpos(axle, rim_x, rim_r, rim_ang)
            d = (c - a).normalized()
            b = c - d * (rim_r - nipple_r)
            m.tube(group, [a, b, c], 0.0019, "steel", segments=SPOKE_SIDES, radii=[0.0019, 0.0019, 0.0033],
                   caps=False)


# -- hubs, axle hardware ------------------------------------------------------------------


def front_hub(m, group, axle):
    """Front hub: bearing bosses, two spoke flanges and the disc-carrier boss on the left."""
    fx = 0.033  # flange centre planes at +-fx
    hw = spec.FRONT_HUB_HALF_WIDTH
    boss = spec.FRONT_DISC_X - 0.0025  # disc carrier seats on this face
    prof = [
        (0.0085, -hw), (0.0200, -hw), (0.0215, -hw + 0.002), (0.0215, -0.040),
        (0.0270, -fx - 0.004), (0.0375, -fx - 0.003), (0.0375, -fx + 0.003), (0.0270, -fx + 0.004),
        (0.0235, -0.015), (0.0235, 0.015),
        (0.0270, fx - 0.004), (0.0375, fx - 0.003), (0.0375, fx + 0.003), (0.0300, fx + 0.005),
        (0.0310, boss - 0.004), (0.0325, boss), (0.0085, boss),
    ]
    m.lathe(group, prof, "dark_alu", matrix=wheel_matrix(axle), segments=HUB_SEGMENTS)
    return fx, 0.030


def rear_hub(m, group, axle):
    """Rear hub: wider, bigger flanges, sprocket carrier on the left and disc boss on the right."""
    fx = 0.046
    hw = spec.REAR_HUB_HALF_WIDTH
    disc_face = spec.REAR_DISC_X + 0.002  # disc seats on this face (right side)
    spr_face = spec.CHAIN_X - 0.0025  # sprocket seats on this face (left side)
    prof = [
        (0.0100, disc_face), (0.0470, disc_face), (0.0470, -hw + 0.001), (0.0270, -hw + 0.003),
        (0.0250, -fx - 0.007),
        (0.0310, -fx - 0.004), (0.0450, -fx - 0.003), (0.0450, -fx + 0.003), (0.0310, -fx + 0.004),
        (0.0275, -0.020), (0.0275, 0.020),
        (0.0310, fx - 0.004), (0.0450, fx - 0.003), (0.0450, fx + 0.003), (0.0310, fx + 0.006),
        (0.0300, hw - 0.004),
        (0.0520, hw - 0.002), (0.0530, spr_face - 0.003), (0.0470, spr_face), (0.0100, spr_face),
    ]
    m.lathe(group, prof, "dark_alu", matrix=wheel_matrix(axle), segments=HUB_SEGMENTS)
    return fx, 0.038


def spacers(m, group, axle, pieces):
    """Axle spacers (x0, x1, radius) filling the gaps between hub and fork lugs / swingarm."""
    for x0, x1, r in pieces:
        m.cylinder(group, r, abs(x1 - x0), "dark_alu", matrix=wheel_matrix(axle, (x0 + x1) / 2), segments=12)


def axle_and_nut(m, group, axle, axle_r, nut_x, head_x):
    """Axle shaft with a hex nut on the right (-X) and a round head on the left (+X)."""
    # shaft: only its ends ever show, so a plain open 8-sided tube is enough
    m.tube(group, [axle + Vector((nut_x, 0, 0)), axle + Vector((head_x, 0, 0))], axle_r, "steel", segments=8,
           caps=False)
    m.cylinder(group, axle_r * 1.55, 0.011, "steel", matrix=wheel_matrix(axle, nut_x) @ mp.rot(0, 0, 30),
               segments=6)  # hex nut
    m.lathe(group, [(0.0, head_x + 0.004), (axle_r * 1.25, head_x + 0.004), (axle_r * 1.45, head_x + 0.002),
                    (axle_r * 1.45, head_x - 0.004)], "steel", matrix=wheel_matrix(axle), segments=12)  # axle head


# -- brake discs, carrier, sprocket -------------------------------------------------------------


def wave_outline(radius, depth, waves, pts_per_wave=6):
    """Petal/wave disc edge: rounded lobes with sharp dips between them."""
    out = []
    n = waves * pts_per_wave
    for i in range(n):
        a = 2 * math.pi * i / n
        f = abs(math.cos(waves * a / 2))  # 1 at lobe centres... 0 at the dips
        r = radius - depth * (1 - f) ** 1.6
        out.append(polar(r, a + math.pi / waves))
    return out


def disc_slots(r_mid, count, length, width, tilt, phase=0.0):
    """Angled slot cut-outs around the braking band."""
    return [stadium(*polar(r_mid, phase + 2 * math.pi * i / count), length, width,
                    phase + 2 * math.pi * i / count + math.pi / 2 + tilt, n_end=2)
            for i in range(count)]


def front_disc(m, group, axle):
    """Floating wave disc (steel band) on a dark six-arm carrier, rider's left."""
    x = spec.FRONT_DISC_X
    R = spec.FRONT_DISC_RADIUS
    band_in = R - 0.029
    mat = wheel_matrix(axle, x)
    loops = [wave_outline(R, 0.006, 13, pts_per_wave=4)]
    # inner edge is hidden inside the carrier ring, so it can be coarse
    loops.append([polar(band_in, 2 * math.pi * i / 12) for i in range(12)][::-1])
    loops += disc_slots((R + band_in) / 2 - 0.001, 10, 0.020, 0.0052, math.radians(25))
    plate(m, group, loops, 0.0035, "steel", mat)

    # carrier: a ring overlapping the disc's inner edge plus six arms to the hub boss
    c_out = band_in + 0.0045
    windows = []
    for i in range(6):
        a0 = 2 * math.pi * i / 6 + math.radians(9)
        a1 = 2 * math.pi * (i + 1) / 6 - math.radians(9)
        windows.append(window(band_in - 0.0045, 0.044, a0, a1, math.radians(6)))
    carrier_out = [polar(c_out, 2 * math.pi * i / 30) for i in range(30)]
    # (the carrier stands 2 mm proud of the band on each face where they overlap: no z-fighting)
    plate(m, group, [carrier_out] + windows, 0.0075, "dark_alu", mat)
    # floating buttons joining disc and carrier, and the carrier-to-hub bolts (2 mm proud of the carrier)
    ring_of(m, group, axle, x, band_in + 0.0005, 6, 0.0048, 0.0115, "steel", segments=8,
            phase=math.pi / 6)
    ring_of(m, group, axle, x + 0.0045, 0.038, 6, 0.0042, 0.004, "steel", segments=6)


def rear_disc(m, group, axle):
    """One-piece wave disc on the right (-X): braking band, slots and inner arms to the hub."""
    x = spec.REAR_DISC_X
    R = spec.REAR_DISC_RADIUS
    band_in = R - 0.026
    loops = [wave_outline(R, 0.0055, 12, pts_per_wave=4)]
    loops.append([polar(0.034, 2 * math.pi * i / 16) for i in range(16)][::-1])  # centre hole round the hub
    for i in range(5):  # windows between five arms
        a0 = 2 * math.pi * i / 5 + math.radians(12)
        a1 = 2 * math.pi * (i + 1) / 5 - math.radians(12)
        loops.append(window(band_in, 0.050, a0, a1, math.radians(7)))
    loops += disc_slots((R + band_in) / 2, 10, 0.018, 0.005, math.radians(-25))
    plate(m, group, loops, 0.004, "steel", wheel_matrix(axle, x))
    ring_of(m, group, axle, x - 0.003, 0.042, 5, 0.0042, 0.004, "steel", segments=6, phase=math.pi / 5)


def sprocket(m, group, axle, teeth=58):
    """Large rear sprocket on the left (+X, chain line) with six lightening cut-outs."""
    x = spec.CHAIN_X
    # chain pins run on the pitch circle (spec.REAR_SPROCKET_RADIUS): rollers sit in the valleys
    tip = spec.REAR_SPROCKET_RADIUS + 0.0035
    root = spec.REAR_SPROCKET_RADIUS - 0.004
    pitch = 2 * math.pi / teeth
    outline = []
    for k in range(teeth):
        c = k * pitch
        outline.append(polar(root, c))  # valley (roller seat)
        outline.append(polar(tip, c + pitch * 0.38))
        outline.append(polar(tip, c + pitch * 0.62))
    loops = [outline]
    loops.append([polar(0.036, 2 * math.pi * i / 18) for i in range(18)][::-1])  # centre hole
    arms = 6
    for i in range(arms):
        a0 = 2 * math.pi * i / arms + math.radians(8.5)
        a1 = 2 * math.pi * (i + 1) / arms - math.radians(8.5)
        loops.append(window(root - 0.012, 0.064, a0, a1, math.radians(9), n_out=5))
    plate(m, group, loops, 0.005, "steel", wheel_matrix(axle, x))
    ring_of(m, group, axle, x + 0.004, 0.053, 6, 0.0058, 0.006, "steel", segments=6)


# -- assembly -----------------------------------------------------------------------------------


def front_wheel(m):
    g, axle = "FrontWheel", spec.FRONT_AXLE
    tyre(m, g, axle, FRONT_KNOBS, FRONT_KNOB_CYCLES)
    rim(m, g, axle)
    valve_stem(m, g, axle, math.radians(5))
    fx, hole_r = front_hub(m, g, axle)
    spokes(m, g, axle, fx, hole_r)
    front_disc(m, g, axle)
    hw = spec.FRONT_HUB_HALF_WIDTH
    lug_in = spec.FORK_LEG_X - 0.021  # inner face of the fork axle lugs
    lug_out = spec.FORK_LEG_X + 0.021
    spacers(m, g, axle, [(-hw, -lug_in, 0.0125), (spec.FRONT_DISC_X + 0.0025, lug_in, 0.0125)])
    if FRONT_AXLE_NUT:
        axle_and_nut(m, g, axle, 0.0085, nut_x=-(lug_out + 0.0055), head_x=lug_out + 0.004)


def rear_wheel(m):
    g, axle = "RearWheel", spec.REAR_AXLE
    tyre(m, g, axle, REAR_KNOBS, REAR_KNOB_CYCLES)
    rim(m, g, axle)
    valve_stem(m, g, axle, math.radians(5))
    fx, hole_r = rear_hub(m, g, axle)
    spokes(m, g, axle, fx, hole_r)
    rear_disc(m, g, axle)
    sprocket(m, g, axle)
    # The rear axle, its nut and the chain adjusters belong to the swingarm (Swingarm group, so they do
    # not spin); here only the spacers. The right one stops short of the arm to leave room for the
    # rear caliper bracket that sits on the axle inside the right arm.
    arm_in = spec.SWINGARM_ARM_X - 0.015  # inner face of the swingarm arms
    spacers(m, g, axle, [(spec.REAR_DISC_X - 0.002, -arm_in + 0.007, 0.014),
                         (spec.CHAIN_X + 0.0025, arm_in, 0.014)])


def build(m):
    front_wheel(m)
    rear_wheel(m)
