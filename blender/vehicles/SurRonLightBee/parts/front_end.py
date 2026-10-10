"""Front end of the Sur-Ron Light Bee X (mid-poly, Roblox-ready).

Group "Steering" (origin spec.LOWER_CLAMP, turns about spec.STEER_DIR):
  * machined lower and top triple clamps with pinch-bolt ears, steering stem, stem nut and
    bearing seals
  * gold outer tubes of the upside-down fork with seal housings, dust wipers, fork caps and
    preload adjusters
  * risers, two-piece bar clamps and a tapered motocross bar with rise and sweep, ribbed
    grips and bar-end plugs
  * both hand-brake master cylinders (reservoir, lid, pivot, lever blade), the twist
    throttle housing on the right, the switch pod with the ignition key on the left, a
    small display between the bar clamps
  * front brake hose from the right lever, across behind the number plate and down the front
    of the left fork leg; rear brake hose, throttle cable and switch loom from the bar into
    the front opening of the shroud (smooth runs, no sharp kinks)
  * the white front number plate (wrapped round the fork, tilted with it, cut lower corners,
    dipped top edge) with a rectangular LED headlight and running-light strip set into it,
    and its mounting straps
  * the high white front fender under the lower clamp, ending in a beak at the front
Group "ForkLowers" (origin spec.FRONT_AXLE, slides up spec.STEER_DIR by up to spec.FORK_TRAVEL):
  * chrome stanchions, machined axle feet with axle pinch bolts
  * black plastic fork guards, the front brake caliper and its bracket on the LEFT leg (+X)
    clasping the front disc behind the axle, the lower brake hose, axle shaft/head/nut
    (while spec.FRONT_AXLE_IN_FORK, see axle())

Coordinates: world metres from spec.py (Z up, the bike faces -Y, rider's left is +X).
Most of the front end is designed in a "steer frame" (see sp()): local x = world X,
local y = back along the bike square to the steering axis, local z = up the steering
axis, origin on the steering axis level with the front axle. In that frame the fork legs
are vertical lines at (+-FORK_LEG_X, -FORK_OFFSET) and a leg's local z is exactly the
spec's fork-leg parameter t. The handlebar is laid out in world axes (rise = world up,
sweep = world back) because that is how a rider sees it. Model.finish() moves every group
to its pivot, so all geometry is given in world coordinates.

Shading: Model.finish() splits normals at edges sharper than 35 degrees, so parts meant
to read round use 12+ sides, machined plates get a single crisp chamfer (slab(segs=1)),
moulded plastics a rounded rim (segs=2..3), and small hardware is left faceted.
"""

import math

import bmesh
from mathutils import Matrix, Vector

import midpoly as mp
import spec as S

ST, FL = "Steering", "ForkLowers"
XAX = Vector((1.0, 0.0, 0.0))
ZW = Vector((0.0, 0.0, 1.0))

# -- steer frame -------------------------------------------------------------------------------
BACK = -S.STEER_FWD  # square to the steering axis, towards the rear
UP = S.STEER_DIR  # up the steering axis
ORIGIN = S.steer_point(0.0)
STEER_M = Matrix((XAX, BACK, UP)).transposed().to_4x4()
STEER_M.translation = ORIGIN
STEER_INV = STEER_M.inverted()

LEG_X = S.FORK_LEG_X
LEG_Y = -S.FORK_OFFSET  # fork-leg axis (and the axle) in the steer frame
T_LOWER = (S.LOWER_CLAMP - ORIGIN).dot(UP)  # 0.58
T_TOP = (S.TOP_CLAMP - ORIGIN).dot(UP)  # 0.74
R_OUT = S.FORK_OUTER_RADIUS
R_IN = S.FORK_INNER_RADIUS


# Lower clamp spans local z LC0..LC1: its top sits just under the head tube's bottom bearing
# cup (spec.HEAD_TUBE starts at T_LOWER + 0.02, the frame's cup reaches 6 mm below that).
LC0, LC1 = T_LOWER - 0.030, T_LOWER + 0.013
# Top clamp spans TC0..TC1, just above the head tube's top cup.
TC0, TC1 = T_TOP - 0.012, T_TOP + 0.018


def sp(x, y, z):
    """World point from steer-frame coordinates."""
    return STEER_M @ Vector((x, y, z))


def sv(x, y, z):
    """World direction from steer-frame components."""
    return STEER_M.to_3x3() @ Vector((x, y, z))


def sm(x=0.0, y=0.0, z=0.0):
    """Steer-frame matrix moved to local (x, y, z)."""
    return STEER_M @ mp.tr(x, y, z)


def local(p):
    """Steer-frame coordinates of a world point."""
    return STEER_INV @ Vector(p)


def leg_m(side=1, t=0.0):
    """Matrix on a fork-leg axis at height t, local Z up the leg (lathe profiles are (r, t))."""
    return sm(side * LEG_X, LEG_Y, t)


def basis(origin, xdir, ydir):
    """Matrix mapping local X->xdir, Y->ydir (made square to X), Z->X x Y, at origin."""
    u = Vector(xdir).normalized()
    v = Vector(ydir)
    v = (v - u * v.dot(u)).normalized()
    w = u.cross(v)
    mat = Matrix((u, v, w)).transposed().to_4x4()
    mat.translation = Vector(origin)
    return mat


# -- generic helpers ------------------------------------------------------------------------------


def arc2(cx, cy, r, a0, a1, n):
    """n+1 points on a 2D arc (degrees, a0 -> a1)."""
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def fillet_poly(pts, r, n=4):
    """Round every corner of a convex 2D polygon with radius r (n segments per corner)."""
    out = []
    k = len(pts)
    for i in range(k):
        p = Vector(pts[i])
        a = (Vector(pts[i - 1]) - p).normalized()
        b = (Vector(pts[(i + 1) % k]) - p).normalized()
        half = math.acos(max(-1.0, min(1.0, a.dot(b)))) / 2
        dist = r / math.tan(half)
        c = p + (a + b).normalized() * (r / math.sin(half))
        t0, t1 = p + a * dist, p + b * dist
        a0 = math.atan2(t0.y - c.y, t0.x - c.x)
        a1 = math.atan2(t1.y - c.y, t1.x - c.x)
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        out += [(c.x + r * math.cos(a0 + da * j / n), c.y + r * math.sin(a0 + da * j / n)) for j in range(n + 1)]
    return out


def _offset(pts, d):
    """Offset a counter-clockwise 2D outline inward by d (mitred)."""
    n = len(pts)
    out = []
    for i in range(n):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
        e1 = (p1 - p0).normalized()
        e2 = (p2 - p1).normalized()
        n1 = Vector((-e1.y, e1.x))
        n2 = Vector((-e2.y, e2.x))
        b = n1 + n2
        b = n1.copy() if b.length < 1e-6 else b.normalized()
        out.append(p1 + b * (d / max(b.dot(n1), 0.3)))
    return out


def _caps(m, group, loops, color, mirror):
    """Flat-shaded caps for closed loops [(points, reverse)], triangulated with real normals.

    (Model.finish() triangulates ngons before their normals exist, which can fold concave
    outlines, so caps are triangulated here.)
    """
    cap = bmesh.new()
    for loop, rev in loops:
        vs = [cap.verts.new(p) for p in loop]
        cap.faces.new(list(reversed(vs)) if rev else vs)
    cap.normal_update()
    bmesh.ops.triangulate(cap, faces=list(cap.faces), quad_method="BEAUTY", ngon_method="BEAUTY")
    m.commit(group, cap, color, mirror=mirror, smooth=False, recalc=False)


def slab(m, group, outline, thick, color, matrix, bevel=0.0, segs=1, mirror=False):
    """A 2D outline (local XY) extruded `thick` along local Z with a bevelled rim.

    segs=1 gives a crisp machined chamfer, segs=3 a fully rounded moulded rim (each step
    under the 35 degree normal split). The two big faces stay flat-shaded.
    """
    pts = [Vector((p[0], p[1])) for p in outline]
    n = len(pts)
    area = sum(pts[i].x * pts[(i + 1) % n].y - pts[(i + 1) % n].x * pts[i].y for i in range(n))
    if area < 0:
        pts.reverse()
    h = thick / 2
    if bevel > 0:
        b = min(bevel, 0.9 * h)
        angles = [math.pi / 2 * k / segs for k in range(segs + 1)]
        top = [(b - b * math.sin(a), h - b + b * math.cos(a)) for a in angles]
        rings = top + [(i, -z) for (i, z) in reversed(top)]
    else:
        rings = [(0.0, h), (0.0, -h)]
    loops = []
    for ins, z in rings:
        ring = _offset(pts, ins) if ins > 1e-9 else pts
        loops.append([matrix @ Vector((q.x, q.y, z)) for q in ring])
    side = bmesh.new()
    vs = [[side.verts.new(p) for p in loop] for loop in loops]
    for k in range(len(vs) - 1):
        a, c = vs[k], vs[k + 1]
        for j in range(n):
            j1 = (j + 1) % n
            side.faces.new((a[j], c[j], c[j1], a[j1]))
    m.commit(group, side, color, mirror=mirror, smooth=True, recalc=False)
    _caps(m, group, [(loops[0], False), (loops[-1], True)], color, mirror)


def rbox(m, group, size, color, matrix, r=0.004, bevel=0.002, cs=2, segs=1, mirror=False):
    """Rounded box (size x, y, z): rounded corners round local Z, chamfered top and bottom rims."""
    slab(m, group, mp.rounded_rect(size[0], size[1], r, cs), size[2], color, matrix, bevel, segs, mirror)


def _newell(loop):
    """Area normal of a closed 3D loop (its direction follows the loop's winding)."""
    nrm = Vector()
    for i in range(len(loop)):
        a, b = Vector(loop[i]), Vector(loop[(i + 1) % len(loop)])
        nrm += Vector(((a.y - b.y) * (a.z + b.z), (a.z - b.z) * (a.x + b.x), (a.x - b.x) * (a.y + b.y)))
    return nrm


def skin(m, group, rings, color, mirror=False):
    """Smooth closed surface through cross-section loops (world points), flat triangulated end caps.

    Each cap is wound to face away from its neighbouring section, whichever way the loops run.
    """
    tmp = bmesh.new()
    vs = [[tmp.verts.new(Vector(p)) for p in r] for r in rings]
    n = len(vs[0])
    for i in range(len(vs) - 1):
        a, c = vs[i], vs[i + 1]
        for j in range(n):
            j1 = (j + 1) % n
            tmp.faces.new((a[j], a[j1], c[j1], c[j]))
    m.commit(group, tmp, color, mirror=mirror, smooth=True, recalc=True)

    def centre(r):
        return sum((Vector(p) for p in r), Vector()) / len(r)

    out0 = centre(rings[0]) - centre(rings[1])
    out1 = centre(rings[-1]) - centre(rings[-2])
    _caps(m, group, [(rings[0], _newell(rings[0]).dot(out0) < 0), (rings[-1], _newell(rings[-1]).dot(out1) < 0)],
          color, mirror)


def bolt(m, group, pos, axis, r=0.005, h=0.005, color="steel", segments=6, mirror=False):
    """Hex bolt head / nut with its base on pos, standing out along axis."""
    a = Vector(axis).normalized()
    m.cylinder(group, r, h, color, matrix=mp.look(Vector(pos) + a * (h / 2), a), segments=segments, mirror=mirror)


def catmull(points, per=3):
    """Smooth path through control points (Catmull-Rom, `per` steps per span); works for any vector size."""
    pts = [Vector(p) for p in points]
    out = []
    for i in range(len(pts) - 1):
        p0 = pts[max(i - 1, 0)]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[min(i + 2, len(pts) - 1)]
        for k in range(per):
            t = k / per
            t2, t3 = t * t, t * t * t
            out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(pts[-1].copy())
    return out


def hose(m, group, local_pts, radius=0.0042, per=2, color="black", segments=6):
    """A flexible hose / cable through steer-frame control points (thin, so 6 faceted sides is plenty)."""
    path = [sp(*p) for p in catmull(local_pts, per)]
    m.tube(group, path, radius, color, segments=segments)


# =============================================================================== Steering: clamps


def clamp_outline(leg_r, stem_r, a_leg, a_stem, k=0.45):
    """Plan outline of a triple clamp in the steer frame (x, y = back), counter-clockwise.

    Two fork-leg bosses joined by a straight front edge, and a stem boss at the back joined
    to them by concave fillets: the usual machined triple-clamp shape.
    """
    half = arc2(LEG_X, LEG_Y, leg_r, -90, a_leg, 8)
    p0 = Vector(half[-1])
    t0 = Vector((-math.sin(math.radians(a_leg)), math.cos(math.radians(a_leg))))
    p3 = Vector((stem_r * math.cos(math.radians(a_stem)), stem_r * math.sin(math.radians(a_stem))))
    t3 = Vector((-math.sin(math.radians(a_stem)), math.cos(math.radians(a_stem))))
    dist = (p3 - p0).length
    join = mp.bezier(p0, p0 + t0 * dist * k, p3 - t3 * dist * k, p3, n=4)
    half += [(p.x, p.y) for p in join[1:-1]]
    half += arc2(0.0, 0.0, stem_r, a_stem, 90, 4)
    other = [(-x, y) for (x, y) in reversed(half)][1:]
    return half + other


def pinch_ear(m, z0, z1, leg_r, ang, bolts_z):
    """Pinch ear on the rear-outer side of a clamp's leg boss (both sides): slit and pinch bolts."""
    a = math.radians(ang)
    radial = Vector((math.cos(a), math.sin(a)))
    tang = Vector((-math.sin(a), math.cos(a)))
    c = Vector((LEG_X, LEG_Y)) + radial * (leg_r + 0.002)
    zc, th = (z0 + z1) / 2, z1 - z0
    ear = basis(sp(c.x, c.y, zc), sv(radial.x, radial.y, 0), sv(tang.x, tang.y, 0))
    m.box(ST, (0.020, 0.028, th), "dark_alu", matrix=ear, bevel=0.0025, bevel_segments=1, mirror=True)
    m.box(ST, (0.014, 0.0016, th + 0.0008), "black", matrix=ear @ mp.tr(0.005, 0, 0), bevel=0.0,
          mirror=True)  # the slit
    t = sv(tang.x, tang.y, 0)
    for z in bolts_z:
        base = c + tang * 0.014
        bolt(m, ST, sp(base.x, base.y, z), t, r=0.0052, h=0.0045, mirror=True)


def lower_clamp(m):
    """Lower triple clamp: a machined plate round both gold tubes and the stem, two pinch bolts a side."""
    slab(m, ST, clamp_outline(0.039, 0.036, 112, 32), LC1 - LC0, "dark_alu", sm(0, 0, (LC0 + LC1) / 2),
         bevel=0.0035, segs=1)
    pinch_ear(m, LC0 + 0.002, LC1 - 0.002, 0.039, 38, (LC0 + 0.012, LC1 - 0.012))
    bolt(m, ST, sp(0, 0, LC0), -UP, r=0.016, h=0.008, segments=6)  # steering stem nut underneath


def top_clamp(m):
    """Top triple clamp with pinch ears, the domed stem nut, the steering stem and bearing seals."""
    slab(m, ST, clamp_outline(0.037, 0.044, 116, 30), TC1 - TC0, "dark_alu", sm(0, 0, (TC0 + TC1) / 2),
         bevel=0.0035, segs=1)
    pinch_ear(m, TC0 + 0.002, TC1 - 0.002, 0.037, 40, ((TC0 + TC1) / 2,))
    prof = [(0.0, TC1 + 0.013), (0.0120, TC1 + 0.013), (0.0180, TC1 + 0.008), (0.0185, TC1 - 0.001)]
    m.lathe(ST, prof, "steel", matrix=sm(), segments=14)
    bolt(m, ST, sp(0, 0, TC1 + 0.0125), UP, r=0.0072, h=0.0015, color="black")  # hex socket
    # steering stem (hidden inside the head tube) and the dust seals at both bearings
    m.cylinder(ST, 0.0145, TC0 - LC1 + 0.004, "steel", matrix=sm(0, 0, (TC0 + LC1) / 2), segments=8)
    for z in (LC1 + 0.0015, TC0 - 0.0015):
        m.cylinder(ST, 0.031, 0.003, "black", matrix=sm(0, 0, z), segments=14)


# =============================================================================== Steering: fork tubes


def fork_uppers(m):
    """Gold outer tubes (FORK_SPLIT_T..FORK_TOP_T) with seal housings, dust wipers, caps and adjusters."""
    t0, t1 = S.FORK_SPLIT_T, S.FORK_TOP_T
    # gold tube: a slightly fatter seal housing at the bottom, then the clamped tube, and an inner
    # wall back down (a closed section, so every face's normal points out of the solid wall)
    gold = [(0.0215, t0 + 0.001), (R_OUT + 0.0013, t0 + 0.001), (R_OUT + 0.0026, t0 + 0.004),
            (R_OUT + 0.0026, t0 + 0.063), (R_OUT, t0 + 0.076), (R_OUT, t1), (R_OUT - 0.002, t1),
            (0.0215, t0 + 0.006)]
    m.lathe(ST, gold, "gold", matrix=leg_m(), segments=20, closed=True, mirror=True)
    # black dust wiper hugging the stanchion below the seal housing
    wiper = [(R_IN + 0.0003, t0 - 0.011), (0.0222, t0 - 0.012), (0.0255, t0 - 0.006), (0.0255, t0 + 0.0015)]
    m.lathe(ST, wiper, "black", matrix=leg_m(), segments=16, mirror=True)
    # fork cap: round collar, hex flats, gold preload adjuster with a screwdriver slot
    cap = [(R_OUT - 0.0008, t1 - 0.0005), (R_OUT, t1 + 0.001), (R_OUT, t1 + 0.008), (R_OUT - 0.0015, t1 + 0.0095),
           (0.0, t1 + 0.0095)]
    m.lathe(ST, cap, "dark_alu", matrix=leg_m(), segments=16, mirror=True)
    m.cylinder(ST, 0.0185, 0.007, "dark_alu", matrix=leg_m(1, t1 + 0.0125), segments=6, mirror=True)
    knob = [(0.0, t1 + 0.0225), (0.0098, t1 + 0.0225), (0.0098, t1 + 0.0150)]
    m.lathe(ST, knob, "gold", matrix=leg_m(), segments=12, mirror=True)
    m.box(ST, (0.013, 0.0022, 0.002), "black", matrix=leg_m(1, t1 + 0.0225), bevel=0.0, mirror=True)


# =============================================================================== Steering: handlebar

HB_C = S.HANDLEBAR_CENTRE
HB_HALF = S.HANDLEBAR_HALF_WIDTH
BAR_R_CLAMP = 0.0143  # 28.6 mm fat-bar centre section
BAR_R_GRIP = 0.0111  # 22.2 mm at the grips
G0_OFF = Vector((0.200, 0.018, 0.040))  # start of the straight grip section (offset from the centre)
G1_OFF = Vector((HB_HALF, 0.036, 0.046))  # bar end: ~46 mm rise, ~36 mm pull-back (low stock bar)
BEND_START = 0.075
BC_X = 0.040  # risers / bar clamps at x = +-BC_X
BAR_LOCAL = local(HB_C)  # bar centre in the steer frame
GRIP_S0, GRIP_S1 = 0.060, 0.1955  # grip rubber along the grip section


def grip_frame(side):
    """(start, outward axis, forward, up) unit frame of one straight grip section."""
    g0 = HB_C + Vector((side * G0_OFF.x, G0_OFF.y, G0_OFF.z))
    g1 = HB_C + Vector((side * G1_OFF.x, G1_OFF.y, G1_OFF.z))
    d = (g1 - g0).normalized()
    fwd = Vector((0.0, -1.0, 0.0))
    fwd = (fwd - d * fwd.dot(d)).normalized()
    up = ZW - d * ZW.dot(d) - fwd * ZW.dot(fwd)
    return g0, d, fwd, up.normalized()


def gp(side, s, f=0.0, u=0.0):
    """Point s along a grip section from its start, offset f forward and u up."""
    g0, d, fwd, up = grip_frame(side)
    return g0 + d * s + fwd * f + up * u


def handlebar(m):
    """Risers, two-piece bar clamps, the tapered MX bar, ribbed grips and bar-end plugs."""
    bl = BAR_LOCAL
    # risers and clamps (built on the left, mirrored)
    if bl.z - 0.020 - TC1 > 0.004:
        m.cylinder(ST, 0.0150, bl.z - 0.020 - TC1, "dark_alu", matrix=sm(BC_X, bl.y, (TC1 + bl.z - 0.020) / 2),
                   segments=14, mirror=True)
    clamp = basis(sp(BC_X, bl.y, bl.z), BACK, UP)  # local x = back, y = up, z = +X (bar axis)
    rbox(m, ST, (0.042, 0.046, 0.032), "dark_alu", clamp, r=0.012, bevel=0.003, mirror=True)
    m.box(ST, (0.0436, 0.0016, 0.0326), "black", matrix=clamp @ mp.tr(0, 0.002, 0), bevel=0.0,
          mirror=True)  # split line between the clamp and its cap
    for dy in (-0.013, 0.013):
        bolt(m, ST, sp(BC_X, bl.y + dy, bl.z + 0.023), UP, r=0.0048, h=0.004, mirror=True)
    # the bar: straight centre section, a rising bend each side, straight grip sections
    p0 = Vector((BEND_START, 0.0, 0.0))
    dgrip = (G1_OFF - G0_OFF).normalized()
    bend = mp.bezier(p0, (0.135, 0.0, 0.0), G0_OFF - dgrip * 0.058, G0_OFF, n=7)
    half = bend + [G1_OFF]
    radii_half = []
    for i in range(len(bend)):
        f = i / (len(bend) - 1)
        radii_half.append(BAR_R_CLAMP + (BAR_R_GRIP - BAR_R_CLAMP) * (3 * f * f - 2 * f ** 3))
    radii_half.append(BAR_R_GRIP)
    path = [HB_C + Vector((-p.x, p.y, p.z)) for p in reversed(half)] + [HB_C + p for p in half]
    radii = list(reversed(radii_half)) + radii_half
    m.tube(ST, path, 1.0, "black", segments=14, radii=radii)
    # grips: a flange, then rings with crisp grooves, then the closed outer end
    s0, s1 = GRIP_S0, GRIP_S1
    prof = [(BAR_R_GRIP, s0), (0.0188, s0 + 0.001), (0.0188, s0 + 0.007), (0.0164, s0 + 0.010)]
    s = s0 + 0.030
    while s < s1 - 0.012:
        prof += [(0.0172, s - 0.0008), (0.0160, s)]
        s += 0.022
    prof += [(0.0170, s1 - 0.006), (0.0150, s1), (BAR_R_GRIP + 0.0005, s1)]
    plug = [(BAR_R_GRIP + 0.0005, s1 - 0.001), (0.0152, s1), (0.0152, s1 + 0.006), (0.0, s1 + 0.0085)]
    for side in (1, -1):
        g0, d, fwd, up = grip_frame(side)
        m.lathe(ST, prof, "rubber", matrix=mp.look(g0, d), segments=12)
        m.lathe(ST, plug, "dark_alu", matrix=mp.look(g0, d), segments=12)


def master_cylinder(m, side, s_clamp, s_body, s_pivot, s_end):
    """Hydraulic brake master cylinder: bar clamp, bore body, reservoir with lid, pivot and lever blade.

    Returns the inboard end of the bore (where the hose banjo sits) and the grip frame.
    """
    g0, d, fwd, up = grip_frame(side)
    m.lathe(ST, [(BAR_R_GRIP, -0.008), (0.0172, -0.008), (0.0172, 0.008), (BAR_R_GRIP, 0.008)], "black",
            matrix=mp.look(gp(side, s_clamp), d), segments=12, closed=True)
    m.box(ST, (0.014, 0.022, 0.016), "black", matrix=basis(gp(side, s_clamp, 0.016, 0.004), d, fwd), bevel=0.0)
    m.cylinder(ST, 0.0102, 0.042, "black", matrix=mp.look(gp(side, s_body, 0.032, 0.005), d), segments=12)
    rbox(m, ST, (0.036, 0.026, 0.016), "black", basis(gp(side, s_body, 0.027, 0.019), d, fwd), r=0.005)
    m.box(ST, (0.032, 0.022, 0.0018), "grey", matrix=basis(gp(side, s_body, 0.027, 0.0285), d, fwd), bevel=0.0)
    # lever pivot boss and bolt
    lever_dir = (fwd * math.cos(math.radians(22)) - up * math.sin(math.radians(22))).normalized()
    pivot_axis = d.cross(lever_dir).normalized()
    piv = gp(side, s_pivot, 0.034)
    m.cylinder(ST, 0.0085, 0.020, "black", matrix=mp.look(piv, pivot_axis), segments=12)
    bolt(m, ST, piv + pivot_axis * 0.010, pivot_axis, r=0.0045, h=0.003)

    # lever blade: a dog-leg out of the pivot, then parallel to the grip, tapering to the tip
    def lp(s, off):
        return gp(side, s) + lever_dir * off

    ctrl = [lp(s_pivot, 0.036), lp(s_pivot + 0.012, 0.046), lp(s_pivot + 0.030, 0.052), lp(s_end - 0.020, 0.051),
            lp(s_end, 0.048)]
    path = catmull(ctrl, per=2)
    scales = [1.0 - 0.2 * i / (len(path) - 1) for i in range(len(path))]
    m.sweep(ST, path, mp.rounded_rect(0.015, 0.0085, 0.0038, 1), "alu", scales=scales, lateral=lever_dir)
    return gp(side, s_body - 0.021, 0.032, 0.005), d, fwd, up


def throttle(m):
    """Twist-throttle housing on the right grip (-X) with its cable boss."""
    g0, d, fwd, up = grip_frame(-1)
    s0, s1 = 0.022, 0.0585
    prof = [(BAR_R_GRIP + 0.0005, s0), (0.0188, s0), (0.0210, s0 + 0.006), (0.0207, s1 - 0.005), (0.0185, s1),
            (BAR_R_GRIP + 0.0005, s1)]
    m.lathe(ST, prof, "black", matrix=mp.look(g0, d), segments=12, closed=True)
    boss = gp(-1, s0 + 0.012, 0.010, -0.017)
    m.cylinder(ST, 0.0055, 0.016, "black", matrix=mp.look(boss, (fwd - up * 1.2).normalized()), segments=8)


def switch_pod(m):
    """Left switch pod (lights / horn / mode buttons) with the ignition key on top."""
    g0, d, fwd, up = grip_frame(1)
    rbox(m, ST, (0.044, 0.042, 0.030), "black", basis(gp(1, 0.010, 0.006), fwd, up), r=0.013, bevel=0.003)
    for du, color in ((0.008, "grey"), (-0.008, "red")):
        m.cylinder(ST, 0.0042, 0.006, color, matrix=mp.look(gp(1, 0.010, -0.015, du), -fwd), segments=8)
    kb = gp(1, 0.010, 0.010, 0.021)
    m.cylinder(ST, 0.0072, 0.006, "steel", matrix=mp.look(kb, up), segments=8)
    m.box(ST, (0.016, 0.014, 0.003), "black", matrix=basis(kb + up * 0.0095, fwd, up), bevel=0.0)  # key head


def display(m):
    """Small LCD display on a stalk from the top clamp, between the bar clamps, facing the rider."""
    base_y = BAR_LOCAL.y - 0.024
    m.cylinder(ST, 0.0050, 0.038, "black", matrix=sm(0, base_y, TC1 + 0.019), segments=6)
    tilt = math.radians(55.0)  # the screen leans back towards the rider
    face = sv(0, math.cos(tilt), math.sin(tilt))
    housing = basis(sp(0, base_y - 0.011, TC1 + 0.050), XAX, face.cross(XAX))  # local Z = screen normal
    rbox(m, ST, (0.044, 0.034, 0.016), "black", housing, r=0.007, bevel=0.003)
    # the screen stands 2 mm proud of the housing face (no z-fighting)
    m.box(ST, (0.034, 0.022, 0.002), "grey", matrix=housing @ mp.tr(0, 0.001, 0.0090), bevel=0.0)


def controls(m):
    """Both master cylinders and levers, throttle, switch pod, display, brake hoses and cables."""
    # right lever = front brake (its clamp inboard of the throttle housing)
    rb, rd, rf, ru = master_cylinder(m, -1, s_clamp=0.010, s_body=0.016, s_pivot=0.040, s_end=0.172)
    # left lever = rear brake (next to the grip, the switch pod inboard of it)
    lb, ld, lf, lu = master_cylinder(m, 1, s_clamp=0.045, s_body=0.050, s_pivot=0.074, s_end=0.184)
    throttle(m)
    switch_pod(m)
    display(m)
    for b, d in ((rb, rd), (lb, ld)):  # banjo bolts at the hose ends
        m.cylinder(ST, 0.0058, 0.012, "steel", matrix=mp.look(b - d * 0.005, d), segments=8)
    # front brake hose: right master cylinder, down in front of the right fork tube, across behind the
    # number plate (between the clamps) and down the front of the left gold tube to a clip on its
    # seal housing
    rs = local(rb - rd * 0.004 - ru * 0.004)
    hose(m, ST, [(rs.x, rs.y, rs.z), (rs.x + 0.022, rs.y - 0.018, rs.z - 0.040), (-0.120, -0.062, TC0 - 0.004),
                 (-0.060, -0.068, 0.690), (0.000, -0.066, 0.660), (0.062, -0.070, 0.620), (0.088, -0.077, 0.570),
                 (0.090, -0.070, 0.480), (0.090, -0.066, S.FORK_SPLIT_T)], per=4)
    m.lathe(ST, [(R_OUT + 0.0024, -0.005), (R_OUT + 0.0052, -0.005), (R_OUT + 0.0052, 0.005),
                 (R_OUT + 0.0024, 0.005)], "black", matrix=leg_m(1, S.FORK_SPLIT_T + 0.045), segments=16,
            closed=True)
    m.box(ST, (0.012, 0.012, 0.010), "black", matrix=sm(0.090, -0.065, S.FORK_SPLIT_T + 0.045), bevel=0.0)
    # The other three run down behind the fork tubes beside the head tube, then back over the frame's
    # headstock (between its top beams) into the front opening of the shroud; their hidden ends are
    # under the shroud's roof, near the steering axis, so they stay inside it at full lock.
    # rear brake hose: left master cylinder, outside the left fork tube
    ls = local(lb - ld * 0.004 - lu * 0.004)
    hose(m, ST, [(ls.x, ls.y, ls.z), (ls.x - 0.015, ls.y - 0.012, ls.z - 0.040), (0.160, -0.020, 0.745),
                 (0.088, 0.036, 0.677), (0.052, 0.068, 0.684), (0.026, 0.100, 0.676)], per=4)
    # throttle cable (right) and the switch loom (left)
    tb = local(gp(-1, 0.034, 0.012, -0.024))
    hose(m, ST, [(tb.x, tb.y, tb.z), (tb.x + 0.015, tb.y + 0.010, tb.z - 0.040), (-0.150, 0.010, 0.740),
                 (-0.078, 0.039, 0.677), (-0.046, 0.068, 0.684), (-0.014, 0.100, 0.676)], per=4, radius=0.0032,
         segments=5)
    sb = local(gp(1, 0.010, 0.010, -0.020))
    hose(m, ST, [(sb.x, sb.y, sb.z), (sb.x - 0.010, sb.y + 0.015, sb.z - 0.040), (0.135, 0.022, 0.740),
                 (0.070, 0.046, 0.677), (0.040, 0.072, 0.684), (0.010, 0.100, 0.676)], per=4, radius=0.0032,
         segments=5)


# =============================================================================== Steering: plate, light, fender

PLATE = local(S.NUMBER_PLATE_CENTRE)
PLATE_Y = PLATE.y  # front face on the centre line (steer frame)
PLATE_K = 1.6  # wrap round the fork: the face curves back by PLATE_K * x^2
PLATE_T = 0.0042
# plate, headlight and fender hang from the lower clamp, so their heights are given relative to it
PLATE_Z0, PLATE_Z1 = T_LOWER - 0.063, T_LOWER + 0.137  # bottom edge (resting on the fender) and top corners
PLATE_W0, PLATE_W1 = 0.160, 0.222  # width at the bottom and at the top
PLATE_CUT = 0.028  # the lower corners are cut off at 45 degrees
PLATE_DIP = 0.010  # the top edge dips this much in the middle (the top corners stand up as ears)


def plate_front(x):
    return PLATE_Y + PLATE_K * x * x


def number_plate(m):
    """White front number plate: a shield wrapped round the fork with cut lower corners, a dipped top
    edge between rounded ears, crisp edges."""
    rt = 0.034  # top corner radius
    # (distance from the bottom, or None) / (distance from the top, or None)
    rows = [(d, None) for d in (0.0, 0.010, PLATE_CUT, PLATE_CUT + 0.008)]
    rows += [(f * (PLATE_Z1 - PLATE_Z0), None) for f in (0.38, 0.64)]
    rows += [(None, d) for d in (0.040, 0.026, 0.014, 0.005, 0.0)]
    n = 10
    rings = []
    for db, dt in rows:
        z = PLATE_Z0 + db if db is not None else PLATE_Z1 - dt
        f = (z - PLATE_Z0) / (PLATE_Z1 - PLATE_Z0)
        w = (PLATE_W0 + (PLATE_W1 - PLATE_W0) * f) / 2
        if db is not None and db < PLATE_CUT:
            w -= PLATE_CUT - db  # 45 degree cut corner
        if dt is not None and dt < rt:
            w = w - rt + math.sqrt(max(rt * rt - (rt - dt) ** 2, 0.0))
        dip = PLATE_DIP * max(0.0, 1.0 - dt / 0.05) if dt is not None else 0.0
        xs = [w * (2 * i / n - 1) for i in range(n + 1)]

        def zz(x):
            return z - dip * (1.0 - (x / w) ** 2)

        front = [(x, plate_front(x), zz(x)) for x in xs]
        back = [(x, plate_front(x) + PLATE_T, zz(x)) for x in reversed(xs)]
        ye = plate_front(w) + PLATE_T / 2 + 0.0008
        ring = front + [(w + 0.0016, ye, z)] + back + [(-w - 0.0016, ye, z)]
        rings.append([sp(*p) for p in ring])
    skin(m, ST, rings, "white")
    # mounting: rubber straps round the gold tubes with tabs to the plate's back, and a lower tab
    zt = T_LOWER + 0.110
    m.lathe(ST, [(R_OUT - 0.0002, -0.0045), (R_OUT + 0.0025, -0.004), (R_OUT + 0.0025, 0.004),
                 (R_OUT - 0.0002, 0.0045)], "rubber", matrix=leg_m(1, zt), segments=16, closed=True, mirror=True)
    xt = LEG_X + 0.006
    y0 = plate_front(xt) + PLATE_T - 0.002
    y1 = LEG_Y - 0.012
    m.box(ST, (0.008, y1 - y0, 0.008), "rubber", matrix=sm(xt, (y0 + y1) / 2, zt), bevel=0.0, mirror=True)
    y0 = PLATE_Y + PLATE_T - 0.002
    y1 = LEG_Y - 0.039 + 0.004  # into the lower clamp's front edge
    m.box(ST, (0.030, y1 - y0, 0.010), "black", matrix=sm(0, (y0 + y1) / 2, LC0 + 0.007), bevel=0.0)


def headlight(m):
    """LED headlight set into the plate: a wide black housing, a horizontal rectangular LED lens in a
    chrome surround, and a daytime-running LED strip across its top. The lens, surround and strip
    stand 2+ mm proud of what is behind them, so nothing z-fights."""
    zc = T_LOWER + 0.062
    yf = PLATE_Y - 0.012  # housing front face (steer frame)
    depth = 0.022
    housing = basis(sp(0, yf + depth / 2, zc), XAX, UP)  # local Z points forward
    outline = fillet_poly([(0.066, 0.031), (-0.066, 0.031), (-0.056, -0.031), (0.056, -0.031)], 0.012, 4)
    slab(m, ST, outline, depth, "black", housing, bevel=0.005, segs=2)
    slab(m, ST, mp.rounded_rect(0.100, 0.036, 0.008, 2), 0.004, "chrome", basis(sp(0, yf - 0.0005, zc - 0.006),
                                                                              XAX, UP), bevel=0.0015)
    slab(m, ST, mp.rounded_rect(0.090, 0.027, 0.006, 2), 0.003, "light_white",
         basis(sp(0, yf - 0.003, zc - 0.006), XAX, UP))
    drl = basis(sp(0, yf - 0.0005, zc + 0.020), XAX, UP)
    slab(m, ST, mp.rounded_rect(0.100, 0.0065, 0.0032, 2), 0.003, "light_white", drl)


# Fender top-surface centre line in the steer frame, rear end -> beak tip:
# (y, z, half-width, side drop).
FENDER = [(y, T_LOWER + dz, hw, drop) for (y, dz, hw, drop) in [
    (0.070, -0.080, 0.036, 0.018),
    (0.035, -0.054, 0.048, 0.024),
    (0.000, -0.043, 0.051, 0.028),
    (-0.050, -0.049, 0.056, 0.033),
    (-0.105, -0.068, 0.074, 0.042),
    (-0.180, -0.105, 0.080, 0.046),
    (-0.255, -0.157, 0.068, 0.040),
    (-0.318, -0.208, 0.048, 0.027),
    (-0.366, -0.255, 0.013, 0.008),
]]


def front_fender(m):
    """High white front fender under the lower clamp: an arched shell with a beak at the front."""
    pts = catmull([Vector(p) for p in FENDER], per=2)
    n = 8  # points across each surface
    thick = 0.0035
    rings = []
    for i, q in enumerate(pts):
        y, z, hw, drop = q
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        tang = Vector((0.0, b[0] - a[0], b[1] - a[1])).normalized()
        nrm = Vector((0.0, -tang.z, tang.y))
        if nrm.z < 0:
            nrm = -nrm
        c = Vector((0.0, y, z))
        outer, inner = [], []
        for k in range(n + 1):
            u = 2 * k / n - 1
            off = Vector((u * hw, 0, 0)) - nrm * (drop * u * u * (0.3 + 0.7 * u * u))  # flat crown, steep sides
            outer.append(c + off)
            inner.append(c + off - nrm * thick - Vector((u * thick * 0.6, 0, 0)))
        lip = drop + thick * 0.6
        ring = (outer + [c + Vector((hw + 0.0012, 0, 0)) - nrm * lip] + list(reversed(inner))
                + [c + Vector((-hw - 0.0012, 0, 0)) - nrm * lip])
        rings.append([sp(*p) for p in ring])
    skin(m, ST, rings, "white")
    # four spacers between the fender and the lower clamp (mirrored pairs)
    for y, zf in ((-0.048, T_LOWER - 0.050), (0.016, T_LOWER - 0.047)):
        m.cylinder(ST, 0.0070, LC0 - zf + 0.002, "black", matrix=sm(0.026, y, (LC0 + zf) / 2), segments=8,
                   mirror=True)


# =============================================================================== ForkLowers


def stanchions_and_feet(m):
    """Chrome stanchions screwed into machined axle feet with axle pinch bolts."""
    top = S.FORK_SPLIT_T + 0.03 + S.FORK_TRAVEL  # stays inside the gold tube over the whole travel
    m.lathe(FL, [(R_IN, 0.060), (R_IN, top), (0.0, top)], "chrome", matrix=leg_m(), segments=20, mirror=True)
    # foot body: a rounded block, longer fore-aft than across, narrower than the axle boss
    foot_t = [-0.027, -0.021, 0.056, 0.069, 0.0755]
    foot_s = [(0.55, 0.60), (0.94, 0.95), (1.0, 1.0), (0.95, 0.94), (0.86, 0.80)]
    m.sweep(FL, [sp(LEG_X, LEG_Y, t) for t in foot_t], mp.rounded_rect(0.040, 0.050, 0.016, 3), "dark_alu",
            scales=foot_s, lateral=XAX, mirror=True)
    # axle boss across the foot (the wheel's spacers seat on its inner face at FORK_LEG_X - 0.021)
    h = 0.021
    boss = [(0.0, -h), (0.0205, -h), (0.0250, -h + 0.0035), (0.0250, h - 0.0035), (0.0205, h), (0.0, h)]
    m.lathe(FL, boss, "dark_alu", matrix=mp.tr(S.FRONT_AXLE + Vector((LEG_X, 0, 0))) @ mp.rot(0, 90, 0),
            segments=18, mirror=True)
    # axle pinch: slit block on the front-outer side with two bolts facing forward
    blk = sm(LEG_X + 0.010, LEG_Y - 0.020, -0.004)
    m.box(FL, (0.014, 0.016, 0.040), "dark_alu", matrix=blk, bevel=0.002, bevel_segments=1, mirror=True)
    m.box(FL, (0.0016, 0.017, 0.041), "black", matrix=blk @ mp.tr(-0.002, -0.001, 0), bevel=0.0, mirror=True)
    for z in (-0.016, 0.008):
        bolt(m, FL, sp(LEG_X + 0.010, LEG_Y - 0.028, z), sv(0, -1, 0), r=0.0045, h=0.004, mirror=True)


def fork_guards(m):
    """Black plastic guards wrapping the front and outer side of each stanchion."""
    # angle round the leg from straight ahead (0) towards the outside (+); the inner edge stops at -48 deg
    # so the left guard stays clear of the front brake disc (x = FRONT_DISC_X) below the disc radius
    a0, a1 = -48.0, 105.0
    top = S.FORK_SPLIT_T - 0.016 - S.FORK_TRAVEL  # the dust wiper stops 4 mm above it at full travel
    sections = [(0.064, 0.0315, 0.0), (0.090, 0.0300, 0.004), (0.090 + 0.47 * (top - 0.090), 0.0290, 0.005),
                (top - 0.030, 0.0283, 0.004), (top, 0.0262, 0.0)]
    n = 10
    thick = 0.0028
    rings = []
    for t, r, bulge in sections:
        outer, inner = [], []
        for k in range(n + 1):
            a = math.radians(a0 + (a1 - a0) * k / n)
            rr = r + bulge * max(math.cos(a), 0.0) ** 2  # a raised spine down the front
            dx, dy = math.sin(a), -math.cos(a)
            outer.append(sp(LEG_X + dx * rr, LEG_Y + dy * rr, t))
            inner.append(sp(LEG_X + dx * (rr - thick), LEG_Y + dy * (rr - thick), t))
        rings.append(outer + list(reversed(inner)))
    skin(m, FL, rings, "black", mirror=True)
    for a in (-35.0, 70.0):  # mounting bolts into the foot
        ar = math.radians(a)
        bolt(m, FL, sp(LEG_X + math.sin(ar) * 0.031, LEG_Y - math.cos(ar) * 0.031, 0.080),
             sv(math.sin(ar), -math.cos(ar), 0), r=0.0040, h=0.0030, mirror=True)


CAL_T = 14.0  # caliper centre angle: degrees from straight back towards up the leg
CAL_SPAN = 19.0  # half the angle the caliper covers on the disc
CAL_R = 0.097  # pad centre radius


def disc_pt(r, ang_deg, x):
    """Point in the front wheel plane at radius r from the axle, angle measured from 'back' towards
    'up the leg', at world x."""
    a = math.radians(ang_deg)
    return sp(x, LEG_Y + r * math.cos(a), r * math.sin(a))


def front_caliper(m):
    """Front brake caliper on the LEFT leg clasping the disc behind the axle, with its bracket.

    Returns the hose banjo position on the caliper.
    """
    x = S.FRONT_DISC_X
    path = [disc_pt(CAL_R, CAL_T - CAL_SPAN + 2 * CAL_SPAN * i / 6, x) for i in range(7)]

    def prof(uc, vc, w, h, r, cs=2):  # u = along +X from the disc plane, v = radially outward
        return [(u + uc, v + vc) for (u, v) in mp.rounded_rect(w, h, r, cs)]

    m.sweep(FL, path, prof(0.0145, 0.002, 0.019, 0.044, 0.007), "black", lateral=XAX)  # piston half
    m.sweep(FL, path, prof(-0.0120, 0.004, 0.013, 0.038, 0.005), "black", lateral=XAX)  # inboard half
    m.sweep(FL, path[1:-1], prof(0.0010, 0.0205, 0.044, 0.009, 0.003, 1), "black", lateral=XAX)  # bridge
    for da in (-8.5, 8.5):  # gold piston covers
        c = disc_pt(CAL_R + 0.001, CAL_T + da, x + 0.024)
        m.lathe(FL, [(0.0, 0.0022), (0.0085, 0.0012), (0.0090, -0.0015)], "gold", matrix=mp.look(c, XAX),
                segments=12)
    bleed_dir = sv(0, 0.4, 0.9).normalized()
    bolt(m, FL, disc_pt(CAL_R + 0.020, CAL_T + CAL_SPAN - 4, x + 0.015), bleed_dir, r=0.0028, h=0.008)
    # bracket from the back of the foot to two ears at the caliper's ends (outboard of it)
    e1 = (LEG_Y + 0.104 * math.cos(math.radians(CAL_T - CAL_SPAN)), 0.104 * math.sin(math.radians(CAL_T - CAL_SPAN)))
    e2 = (LEG_Y + 0.104 * math.cos(math.radians(CAL_T + CAL_SPAN)), 0.104 * math.sin(math.radians(CAL_T + CAL_SPAN)))
    outline = [(-0.014, -0.020), (0.040, -0.028)]
    outline += arc2(e1[0], e1[1], 0.010, -110, 90, 5)
    outline += [(p.x, p.y) for p in mp.bezier(Vector((e1[0], e1[1] + 0.010)), Vector((0.045, 0.012)),
                                              Vector((0.040, 0.030)), Vector((e2[0] + 0.006, e2[1] - 0.008)),
                                              n=4)[1:-1]]
    outline += arc2(e2[0], e2[1], 0.010, -40, 150, 5)
    outline += [(0.020, 0.068), (-0.014, 0.060)]
    plane = basis(sp(x + 0.0295, 0, 0), BACK, UP)  # local x = back, y = up the leg, z = +X
    slab(m, FL, outline, 0.010, "dark_alu", plane, bevel=0.0025, segs=1)
    for e in (e1, e2):
        bolt(m, FL, sp(x + 0.0345, e[0], e[1]), XAX, r=0.0055, h=0.005)
    return disc_pt(CAL_R + 0.004, CAL_T + CAL_SPAN + 3, x + 0.012)


def lower_hose(m, banjo):
    """Front brake hose from the seal-housing clip, down the outside of the left guard to the caliper."""
    b = local(banjo)
    hose(m, FL, [(0.090, -0.066, S.FORK_SPLIT_T), (0.098, -0.062, S.FORK_SPLIT_T - 0.060), (0.110, -0.054, 0.205),
                 (0.122, -0.030, 0.150), (0.116, 0.010, 0.110), (0.096, 0.040, 0.090),
                 (b.x + 0.004, b.y + 0.006, b.z + 0.018), (b.x, b.y, b.z)])
    m.cylinder(FL, 0.0058, 0.012, "steel", matrix=mp.look(banjo, XAX), segments=8)  # banjo bolt
    m.box(FL, (0.010, 0.012, 0.014), "black", matrix=sm(0.109, -0.050, 0.205) @ mp.rot(0, 0, 35), bevel=0.0)


def axle(m):
    """Axle shaft, its head on the left foot and the nut on the right foot (while spec.FRONT_AXLE_IN_FORK;
    otherwise parts/wheels.py builds them)."""
    if not S.FRONT_AXLE_IN_FORK:
        return
    a = S.FRONT_AXLE
    lug_out = LEG_X + 0.021
    m.tube(FL, [a + Vector((-(lug_out + 0.0055), 0, 0)), a + Vector((lug_out + 0.004, 0, 0))], 0.0085, "steel",
           segments=12, caps=False)
    m.cylinder(FL, 0.0132, 0.011, "steel", segments=6,
               matrix=mp.tr(a + Vector((-(lug_out + 0.0055), 0, 0))) @ mp.rot(0, 90, 0) @ mp.rot(0, 0, 30))
    m.lathe(FL, [(0.0, 0.006), (0.0106, 0.006), (0.0123, 0.004), (0.0123, -0.002)], "steel",
            matrix=mp.tr(a + Vector((lug_out, 0, 0))) @ mp.rot(0, 90, 0), segments=14)


# =============================================================================== build


def build(m):
    # Steering
    lower_clamp(m)
    top_clamp(m)
    fork_uppers(m)
    handlebar(m)
    controls(m)
    number_plate(m)
    headlight(m)
    front_fender(m)
    # ForkLowers
    stanchions_and_feet(m)
    fork_guards(m)
    lower_hose(m, front_caliper(m))
    axle(m)
