"""Chassis of the Sur-Ron Light Bee X (mid-poly, Roblox-ready).

Group "Body" (frame and mechanics only; the plastics and the seat come from bodywork.py):
  * forged aluminium frame: head tube, a loop of wide flat beams on each side of the
    battery (a top beam falling ~17 degrees to the rear, a forward-placed rear upright, the
    lower beam and the down beam) whose two ends meet in a forged headstock behind the head
    tube, a corner web, a short forged tower from the rear-top corner up to the shock mount,
    cross-members, big swingarm pivot plates with footpeg mounts, tubular rear subframe
    (spec.SUBFRAME_RAIL)
  * battery case with vertical slats on its sides, motor controller under the seat
  * motor (finned body, end cap, bolts), primary gearbox case on the LEFT, front sprocket,
    black skid plate, phase cable
  * folding serrated footpegs (both sides), kickstand (left, folded back)
  * the shock's top mount; the frame half of the rear brake hose
Groups "Shock" (origin spec.SHOCK_TOP) and "ShockRod" (origin spec.SHOCK_BOTTOM):
  * the rear shock in two halves that can be aimed at each other (body, top eye, preload collar and
    coil spring; lower eye, rod end, spring seat and chrome shaft)
Group "Swingarm" (origin at spec.SWINGARM_PIVOT):
  * box-section aluminium swingarm with a cross brace and shock clevis, pivot bosses,
    axle blocks, chain adjusters, axle and nuts, chain slider
  * the drive chain on the LEFT, a loop of link plates from the front to the rear sprocket
  * rear brake caliper on the RIGHT clasping the rear disc, its bracket and hose

All positions are world metres taken from spec.py (Z up, the bike faces -Y, the rider's
left is +X). Model.finish() moves every group to its pivot, so world coordinates are
used throughout. Shapes that exist on both sides are built on the LEFT (+X) and use
mirror=True.

Shading note: Model.finish() marks edges sharper than 35 degrees, so round things use
12+ sides (or are meant to look faceted, like hex bolts), and flat plates are built with
slab(), which keeps their big faces flat-shaded and pre-triangulates their caps.
"""

import math

import bmesh
from mathutils import Matrix, Vector

import spec as S
from midpoly import look, rounded_rect

BODY, ARM, SHOCK, ROD = "Body", "Swingarm", "Shock", "ShockRod"
BACK = -S.STEER_FWD  # square to the steering axis, pointing to the back of the head tube
XAXIS = (1, 0, 0)


# =============================================================================== helpers


def fillet_path(ctrl, radii=0.0, closed=False, step=12.0):
    """Polyline through `ctrl` with each corner rounded (radius per point, or one number).

    Returns (points, index) where index[i] is the control point each output point
    belongs to, so per-control values (scales, radii) can be looked up. Straight runs get
    only their two end points, so long flat beams stay cheap.
    """
    pts = [Vector(p) for p in ctrl]
    n = len(pts)
    rr = [radii] * n if isinstance(radii, (int, float)) else list(radii)
    out, idx = [], []

    def add(p, i):
        if out and (out[-1] - p).length < 1e-4:
            return
        out.append(p)
        idx.append(i)

    for i in range(n):
        p = pts[i]
        if (not closed and i in (0, n - 1)) or rr[i] <= 0:
            add(p.copy(), i)
            continue
        a, b = pts[i - 1], pts[(i + 1) % n]
        d1, d2 = p - a, b - p
        l1, l2 = d1.length, d2.length
        d1.normalize()
        d2.normalize()
        turn = math.acos(max(-1.0, min(1.0, d1.dot(d2))))
        if turn < math.radians(1.0):
            add(p.copy(), i)
            continue
        t = min(rr[i] * math.tan(turn / 2), 0.48 * l1, 0.48 * l2)
        s, e = p - d1 * t, p + d2 * t
        k = max(2, math.ceil(math.degrees(turn) / step))
        for j in range(k + 1):
            u = j / k
            add((1 - u) ** 2 * s + 2 * (1 - u) * u * p + u * u * e, i)
    if closed and len(out) > 2 and (out[0] - out[-1]).length < 1e-4:
        out.pop()
        idx.pop()
    return out, idx


def beam(m, group, ctrl, radii, color, w, h, r=None, cs=3, scales=None, closed=False, mirror=True, step=12.0,
         lateral=XAXIS):
    """A forged beam: rounded-rectangle section (w along `lateral`, h square to it) swept along a filleted path.

    scales: one (su, sv) per control point (held over each corner, blended along straights).
    """
    path, idx = fillet_path(ctrl, radii, closed, step)
    prof = rounded_rect(w, h, min(w, h) * 0.42 if r is None else r, cs)
    sc = None if scales is None else [scales[i] for i in idx]
    m.sweep(group, path, prof, color, scales=sc, lateral=lateral, closed=closed, caps=not closed, mirror=mirror)


def pipe(m, group, ctrl, radius, color, radii=0.0, segments=12, rads=None, mirror=False, step=15.0):
    """Round tube along a filleted polyline; rads gives a radius per control point."""
    path, idx = fillet_path(ctrl, radii, False, step)
    r = None if rads is None else [rads[i] for i in idx]
    m.tube(group, path, radius, color, segments=segments, radii=r, mirror=mirror)


def frame_mat(origin, u, v):
    """Rotation + translation mapping local X->u, Y->v (made square to u), Z->u x v."""
    u = Vector(u).normalized()
    v = Vector(v)
    v = (v - u * v.dot(u)).normalized()
    w = u.cross(v)
    mat = Matrix((u, v, w)).transposed().to_4x4()
    mat.translation = Vector(origin)
    return mat


def side_mat(x):
    """Local (u, v) = world (y, z) at width position x; local thickness runs along world +X."""
    return frame_mat((x, 0, 0), (0, 1, 0), (0, 0, 1))


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


def slab(m, group, outline, thick, color, matrix, bevel=0.0, segs=3, mirror=False, caps=True):
    """A flat 2D outline extruded `thick` along local Z with rounded rims (forged / machined plates).

    The two large faces are committed flat-shaded and the rim smooth-shaded, so big faces
    stay perfectly flat while the bevel reads round.
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
        top = [(b - b * math.sin(a), h - b + b * math.cos(a)) for a in angles]  # (inset, height) round the rim
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
    if caps:
        cap = bmesh.new()
        cap.faces.new([cap.verts.new(p) for p in loops[0]])
        cap.faces.new(list(reversed([cap.verts.new(p) for p in loops[-1]])))
        # Triangulate here, with real face normals: Model.finish() triangulates ngons whose
        # normals were never computed, which folds concave outlines (teeth, notches).
        cap.normal_update()
        bmesh.ops.triangulate(cap, faces=list(cap.faces), quad_method="BEAUTY", ngon_method="BEAUTY")
        m.commit(group, cap, color, mirror=mirror, smooth=False, recalc=False)


def rbox(m, group, size, color, matrix, r=0.006, bevel=0.003, cs=2, segs=2, mirror=False):
    """Box (size x, y, z) with rounded vertical edges and bevelled top/bottom rims."""
    slab(m, group, rounded_rect(size[0], size[1], r, cs), size[2], color, matrix, bevel, segs, mirror)


def blk(m, group, size, color, matrix, bevel=0.0, mirror=False):
    """Cheap box for small hidden-ish parts (12 tris, or 44 with a one-segment bevel)."""
    m.box(group, size, color, matrix=matrix, bevel=bevel, bevel_segments=1, mirror=mirror)


def fillet_outline(pts, radii, step=24.0):
    """Round the corners of a closed 2D polygon (radius per corner or one number)."""
    p3 = [(p[0], p[1], 0.0) for p in pts]
    out, _ = fillet_path(p3, radii, closed=True, step=step)
    return [(p.x, p.y) for p in out]


def circle_pts(c, r, a0, a1, n):
    """n+1 points on a 2D arc from angle a0 to a1 (radians)."""
    return [Vector((c[0] + r * math.cos(a0 + (a1 - a0) * i / n), c[1] + r * math.sin(a0 + (a1 - a0) * i / n)))
            for i in range(n + 1)]


def belt(c1, r1, c2, r2):
    """Open-belt loop round two circles in 2D, run clockwise (top run from circle 1 to 2).

    Returns the loop as segments [("line", p, q) | ("arc", centre, r, start_angle, sweep)],
    sweeps negative (clockwise), plus the total length.
    """
    c1, c2 = Vector(c1), Vector(c2)
    d = c2 - c1
    e = d.normalized()
    n = Vector((-e.y, e.x))
    k = (r2 - r1) / d.length
    s = math.sqrt(max(0.0, 1 - k * k))
    mu, ml = -k * e + s * n, -k * e - s * n
    au, al = math.atan2(mu.y, mu.x), math.atan2(ml.y, ml.x)
    sw2 = (au - al) % (2 * math.pi)
    sw1 = (al - au) % (2 * math.pi)
    segs = [("line", c1 + mu * r1, c2 + mu * r2), ("arc", c2, r2, au, -sw2),
            ("line", c2 + ml * r2, c1 + ml * r1), ("arc", c1, r1, al, -sw1)]
    total = 2 * (c2 + mu * r2 - c1 - mu * r1).length + r2 * sw2 + r1 * sw1
    return segs, total


def belt_point(segs, s):
    """Point at arc length s along a belt() loop."""
    for seg in segs:
        if seg[0] == "line":
            ln = (seg[2] - seg[1]).length
            if s <= ln:
                return seg[1].lerp(seg[2], s / ln)
        else:
            ln = seg[2] * abs(seg[4])
            if s <= ln:
                a = seg[3] + seg[4] * s / ln
                return seg[1] + Vector((math.cos(a), math.sin(a))) * seg[2]
        s -= ln
    return belt_point(segs, 0.0)


def belt_outline(c1, r1, c2, r2, step_deg=15.0):
    """Outline points of the convex hull of two circles (arcs sampled, straights as end points)."""
    segs, _ = belt(c1, r1, c2, r2)
    out = []
    for seg in segs:
        if seg[0] == "arc":
            n = max(2, math.ceil(abs(math.degrees(seg[4])) / step_deg))
            out += circle_pts(seg[1], seg[2], seg[3], seg[3] + seg[4], n)[:-1]
        else:
            out.append(seg[1])
    return [(p.x, p.y) for p in out]


def hexbolt(m, group, pos, axis, r, h, color="steel", mirror=False, segments=6):
    """A small hex bolt head / nut, centred on pos, axis along `axis`."""
    m.cylinder(group, r, h, color, matrix=look(pos, axis), segments=segments, mirror=mirror)


def yz(v):
    return Vector((v.y, v.z))


# =============================================================================== frame

def _ht(t, back, x):
    """Point t metres up the steering axis, `back` behind it, at width x."""
    p = S.steer_point(t) + BACK * back
    p.x = x
    return p


RT_CORNER = Vector((0.118, 0.140, 0.700))  # rear-top corner of the loop (the shock tower rises from it)

# Frame side loop (left side): control point (x, y, z), corner radius, section scale (su, sv).
# It runs from the headstock back along the top beam, down the rear section to the pivot
# plate, forward along the lower beam under the battery, and up the down beam to the
# headstock again. Both ends are buried in the headstock, so the sweep is left open.

LOOP = [
    (_ht(0.640, 0.010, 0.026), 0.0, (1.0, 1.0)),  # top-beam root, inside the headstock
    # the top beam falls ~17 degrees towards the rear below the small side panel, as on the real bike...
    (Vector((0.084, -0.190, 0.805)), 0.08, (1.0, 1.10)),
    (Vector((0.110, -0.060, 0.765)), 0.15, (1.0, 1.05)),
    (Vector((0.117, 0.060, 0.725)), 0.20, (1.0, 1.0)),
    # ...and turns down at a forward-placed rear-top corner into the rear upright
    (RT_CORNER, 0.09, (1.0, 1.0)),
    (Vector((0.132, 0.168, 0.450)), 0.06, (1.05, 1.05)),  # rear-bottom corner into the pivot plate
    (Vector((0.112, -0.170, 0.468)), 0.05, (1.0, 0.95)),  # front-bottom corner of the battery bay
    # down-beam root, inside the headstock. The beam runs straight up from the corner so that
    # below the head tube its front edge stays ~40 mm behind the steering axis (room for the
    # lower triple clamp at spec.LOWER_CLAMP to turn).
    (_ht(0.650, 0.025, 0.022), 0.0, (1.0, 1.1)),
]
BEAM_W, BEAM_H = 0.024, 0.060
PIVOT_PLATE_X, PIVOT_PLATE_T = 0.145, 0.024
TOP_MOUNT = Vector((0.0, 0.178, 0.776))  # shock top cross-member (in front of the shock eye)
# forged tower from the loop's rear-top corner up to the shock cross-member and the subframe roots
TOWER = [RT_CORNER + Vector((0.0, -0.012, -0.022)), Vector((0.118, TOP_MOUNT.y + 0.004, TOP_MOUNT.z + 0.016))]


def frame_loops(m):
    """Both side loops of the frame plus the forged webs in two of their corners."""
    ctrl = [c[0] for c in LOOP]
    radii = [c[1] for c in LOOP]
    scales = [c[2] for c in LOOP]
    beam(m, BODY, ctrl, radii, "alu", BEAM_W, BEAM_H, r=0.0075, cs=3, scales=scales, mirror=True, step=22.0)
    # forged web filling the inside of the front-bottom corner
    front = [(-0.170, 0.476), (-0.060, 0.476), (-0.128, 0.520), (-0.192, 0.640)]
    slab(m, BODY, fillet_outline(front, [0.0, 0.006, 0.06, 0.006], step=45), 0.014, "alu", side_mat(0.111),
         bevel=0.003, segs=1, mirror=True)
    # forged tower from the rear-top corner up to the shock cross-member, with a small gusset
    # tying it into the top beam
    beam(m, BODY, TOWER, 0.0, "alu", 0.024, 0.045, r=0.0075, cs=3)
    gus = [(0.085, 0.745), (0.128, 0.705), (0.150, 0.772)]
    slab(m, BODY, fillet_outline(gus, [0.004, 0.0, 0.004], step=45), 0.012, "alu", side_mat(0.118),
         bevel=0.003, segs=1, mirror=True)


def head_tube(m):
    """Head tube between the spec.HEAD_TUBE points (bearing cups at both ends) and the headstock."""
    a, b = S.HEAD_TUBE
    ln = (b - a).length
    prof = [(0.024, -0.006), (0.036, -0.006), (0.036, 0.010), (0.032, 0.017), (0.032, ln - 0.017),
            (0.036, ln - 0.010), (0.036, ln + 0.006), (0.024, ln + 0.006)]
    m.lathe(BODY, prof, "alu", matrix=look(a, S.STEER_DIR, up=(0, 1, 0)), segments=18)
    # forged headstock: a solid neck behind the head tube that swallows both beam roots
    outline = [yz(_ht(0.705, 0.008, 0)), (-0.227, 0.840), (-0.262, 0.790), (-0.266, 0.752), (-0.306, 0.752),
               yz(_ht(0.604, 0.030, 0)), yz(_ht(0.610, 0.008, 0))]
    outline = fillet_outline(outline, [0.0, 0.02, 0.04, 0.012, 0.012, 0.0, 0.0], step=30)
    slab(m, BODY, outline, 0.070, "alu", side_mat(0.0), bevel=0.010, segs=3)


def cross_members(m):
    """Tubes tying the two side loops together, and the shock's top mount."""
    def xtube(y, z, half, r, color="alu", seg=12):
        m.cylinder(BODY, r, 2 * half, color, matrix=look((0, y, z), XAXIS), segments=seg)

    xtube(-0.172, 0.468, 0.115, 0.017)  # under the battery front
    xtube(0.170, 0.590, 0.122, 0.016)  # behind the battery, low
    xtube(TOP_MOUNT.y, TOP_MOUNT.z, 0.118, 0.017)  # shock top cross-member
    # shock top clevis: two tabs from the cross-member back to the shock eye
    tab = fillet_outline([(TOP_MOUNT.y - 0.012, TOP_MOUNT.z - 0.018), (S.SHOCK_TOP.y + 0.022, S.SHOCK_TOP.z - 0.02),
                          (S.SHOCK_TOP.y + 0.024, S.SHOCK_TOP.z + 0.016), (TOP_MOUNT.y - 0.008, TOP_MOUNT.z + 0.017)],
                         0.008, step=45)
    slab(m, BODY, tab, 0.006, "alu", side_mat(0.022), mirror=True)
    m.cylinder(BODY, 0.0065, 0.062, "steel", matrix=look(S.SHOCK_TOP, XAXIS), segments=8)
    hexbolt(m, BODY, S.SHOCK_TOP + Vector((0.029, 0, 0)), XAXIS, 0.010, 0.006)


def pivot_plates(m):
    """Big forged plates round the swingarm pivot (outside the swingarm), with the footpeg mounts."""
    p = S.SWINGARM_PIVOT
    pts = [(0.198, 0.590), (0.218, 0.445), (0.188, 0.352), (0.160, 0.286), (0.103, 0.282), (0.090, 0.352),
           (0.028, 0.432), (0.034, 0.494), (0.124, 0.506), (0.146, 0.590)]
    rad = [0.02, 0.05, 0.04, 0.012, 0.012, 0.03, 0.02, 0.015, 0.04, 0.02]
    slab(m, BODY, fillet_outline(pts, rad, step=40), PIVOT_PLATE_T, "alu", side_mat(PIVOT_PLATE_X), bevel=0.006,
         segs=2, mirror=True)
    # pivot bolt cap
    xo = PIVOT_PLATE_X + PIVOT_PLATE_T / 2
    m.lathe(BODY, [(0.0, 0.0), (0.024, 0.0), (0.024, 0.006), (0.019, 0.010), (0.0, 0.010)], "dark_alu",
            matrix=look((xo, p.y, p.z), XAXIS), segments=12, mirror=True)
    hexbolt(m, BODY, (xo + 0.0125, p.y, p.z), XAXIS, 0.009, 0.006, mirror=True)  # seated on the cap
    # lower bolts holding the plate to the cradle
    for y, z in ((0.072, 0.468), (0.180, 0.540)):
        hexbolt(m, BODY, (xo + 0.002, y, z), XAXIS, 0.0075, 0.006, mirror=True)


def subframe(m):
    """Tubular aluminium rear subframe: upper rails (spec.SUBFRAME_RAIL) under the seat, rising at their
    ends to carry the rear fender, two cross tubes and the lower struts."""
    pipe(m, BODY, S.SUBFRAME_RAIL, S.SUBFRAME_RAIL_R, "alu", radii=[0, 0.15, 0.15, 0], segments=12, mirror=True)
    strut = [(0.124, 0.176, 0.560), (0.110, 0.290, 0.664), (0.090, 0.430, 0.784)]
    pipe(m, BODY, strut, 0.0115, "alu", radii=[0, 0.12, 0], segments=12, mirror=True)
    for y in S.SUBFRAME_CROSS_Y:
        x, z = S.subframe_rail_at(y)
        m.cylinder(BODY, 0.009, 2 * x, "alu", matrix=look((0, y, z), XAXIS), segments=12)


# =============================================================================== power train

def battery(m):
    """Battery case in the frame loop (spec.BATTERY_CENTRE / BATTERY_SIZE) with vertical slats on its sides."""
    c, sz = S.BATTERY_CENTRE, S.BATTERY_SIZE
    outline = [(c.y + u, c.z + v) for (u, v) in rounded_rect(sz.y, sz.z, 0.022, 3)]
    slab(m, BODY, outline, sz.x, "battery", side_mat(c.x), bevel=0.008, segs=2)
    # vertical cooling slats on each side face, seen through the frame window (as on the real pack)
    for k in range(5):
        y = -0.118 + 0.046 * k
        rbox(m, BODY, (0.013, 0.205, 0.007), "dark_alu",
             frame_mat((sz.x / 2 + 0.0015, y, 0.605), (0, 1, 0), (0, 0, 1)), r=0.004, bevel=0.0015, cs=2, segs=1,
             mirror=True)
    # charge port cap on the front face
    m.cylinder(BODY, 0.016, 0.012, "black", matrix=look((0.045, c.y - sz.y / 2 - 0.004, c.z + 0.06), (0, -1, 0)),
               segments=12)


def controller(m):
    """Finned motor controller under the seat, between the subframe rails."""
    c = Vector((0.0, 0.365, 0.735))
    blk(m, BODY, (0.10, 0.17, 0.040), "dark_alu", frame_mat(c, (1, 0, 0), (0, 1, 0)), bevel=0.004)
    for i in range(4):
        blk(m, BODY, (0.004, 0.15, 0.016), "dark_alu", frame_mat((-0.033 + 0.022 * i, c.y, c.z + 0.026), (1, 0, 0),
                                                                (0, 1, 0)))
    blk(m, BODY, (0.06, 0.03, 0.024), "black", frame_mat((0.0, c.y - 0.095, c.z - 0.004), (1, 0, 0), (0, 1, 0)))
    # mounting straps to the rails
    for y in (c.y - 0.06, c.y + 0.06):
        m.cylinder(BODY, 0.005, 0.19, "steel", matrix=look((0, y, 0.776), XAXIS), segments=8)


def motor(m):
    """Motor (axis along X): finned body, right end cap with bolts, left end ring under the gearbox."""
    c = S.MOTOR_CENTRE
    r = S.MOTOR_RADIUS
    x0, x1 = -0.066, 0.046  # finned body span
    fins = 18
    outline = []
    for i in range(fins):
        a = 2 * math.pi * i / fins
        da = 2 * math.pi / fins
        for f, rad in ((-0.36, r - 0.007), (-0.16, r), (0.16, r), (0.36, r - 0.007)):
            outline.append((c.y + rad * math.cos(a + f * da), c.z + rad * math.sin(a + f * da)))
    slab(m, BODY, outline, x1 - x0, "battery", side_mat((x0 + x1) / 2), bevel=0.0, caps=False)
    # right end cap (dark alu) with a centre boss
    # (it starts with a flat ring over the fin ends, so the open ends of the fin valleys are covered)
    prof = [(r + 0.0005, 0.0), (r - 0.003, 0.0), (r - 0.003, -0.010), (r - 0.010, -0.017), (0.060, -0.019),
            (0.034, -0.020), (0.030, -0.026), (0.0, -0.027)]
    m.lathe(BODY, prof, "dark_alu", matrix=look((x0, c.y, c.z), XAXIS), segments=24)
    for k in range(6):
        a = 2 * math.pi * k / 6 + 0.3
        hexbolt(m, BODY, (x0 - 0.019, c.y + 0.072 * math.cos(a), c.z + 0.072 * math.sin(a)), XAXIS, 0.0055, 0.006)
    # left end ring tapering into the gearbox case
    prof = [(r + 0.0005, 0.0), (r - 0.003, 0.002), (0.080, 0.008)]
    m.lathe(BODY, prof, "dark_alu", matrix=look((x1, c.y, c.z), XAXIS), segments=20)
    # mounting lugs from the lower beams down to the motor (both sides)
    for y in (c.y - 0.055, c.y + 0.055):
        blk(m, BODY, (0.014, 0.03, 0.07), "alu", frame_mat((0.098, y, c.z + 0.065), (1, 0, 0), (0, 1, 0)),
            mirror=True)
    # phase cable from the motor up the back of the battery to the controller
    # (it passes outside the shock's preload collar, then into the controller's front end)
    pipe(m, BODY, [(-0.045, c.y + 0.07, c.z + 0.06), (-0.06, 0.15, 0.52), (-0.066, 0.170, 0.69),
                   (-0.062, 0.245, 0.735), (-0.035, 0.300, 0.735)], 0.009, "black", radii=[0, 0.05, 0.05, 0.04, 0],
         segments=8, step=25)
    m.cylinder(BODY, 0.013, 0.02, "dark_alu", matrix=look((-0.045, c.y + 0.066, c.z + 0.056), (0, 0.6, 0.8)),
               segments=10)


def gearbox(m):
    """Primary reduction case on the LEFT from the motor axis back to the front sprocket shaft."""
    c = S.MOTOR_CENTRE
    sp = S.FRONT_SPROCKET
    x0, x1 = 0.046, 0.075
    outline = belt_outline((c.y, c.z), 0.082, (sp.y, sp.z), 0.040, step_deg=14)
    slab(m, BODY, outline, x1 - x0, "dark_alu", side_mat((x0 + x1) / 2), bevel=0.006, segs=2)
    # raised silver cover over the motor shaft
    m.lathe(BODY, [(0.0, 0.007), (0.030, 0.007), (0.036, 0.004), (0.040, 0.0)], "alu",
            matrix=look((x1 - 0.001, c.y, c.z), XAXIS), segments=20)
    # cover bolts round the rim
    segs, total = belt((c.y, c.z), 0.070, (sp.y, sp.z), 0.030)
    for k in range(6):
        q = belt_point(segs, total * (k + 0.5) / 6)
        hexbolt(m, BODY, (x1 + 0.002, q.x, q.y), XAXIS, 0.0045, 0.005)
    # front sprocket on the output shaft, and its nut
    front_sprocket(m)
    hexbolt(m, BODY, (S.CHAIN_X + 0.008, sp.y, sp.z), XAXIS, 0.012, 0.008)


def front_sprocket(m, teeth=20):
    """Front (countershaft) sprocket; spec.FRONT_SPROCKET_RADIUS is the chain pitch circle."""
    sp = S.FRONT_SPROCKET
    rp = S.FRONT_SPROCKET_RADIUS
    tip, root = rp + 0.0055, rp - 0.0050
    outline = []
    for i in range(teeth):
        a = 2 * math.pi * i / teeth
        da = 2 * math.pi / teeth
        for f, rad in ((-0.5, root), (-0.14, tip), (0.14, tip)):
            outline.append((sp.y + rad * math.cos(a + f * da), sp.z + rad * math.sin(a + f * da)))
    slab(m, BODY, outline, 0.006, "steel", side_mat(S.CHAIN_X), bevel=0.0)


def skid_plate(m):
    """Black bash plate under the motor: a bent plate with low side lips, bolted to the frame."""
    path = [(0, -0.182, 0.400), (0, -0.168, 0.300), (0, -0.090, 0.262), (0, 0.075, 0.262), (0, 0.112, 0.292)]
    pts, _ = fillet_path(path, [0, 0.05, 0.06, 0.03, 0], step=14)
    m.sweep(BODY, pts, rounded_rect(0.184, 0.005, 0.0024, 1), "black", lateral=XAXIS)
    # side lips follow the plate's outline, 11 mm tall (a swept strip: no long sliver triangles)
    lip = []
    for i, p in enumerate(pts):
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        t = (b - a).normalized()
        nrm = Vector((0.0, -t.z, t.y))  # inward/up, square to the plate
        if nrm.z < 0 and abs(t.z) < 0.5:
            nrm = -nrm
        lip.append(Vector((0.090, p.y, p.z)) + nrm * 0.0075)
    m.sweep(BODY, lip, rounded_rect(0.004, 0.011, 0.0015, 1), "black", lateral=XAXIS, mirror=True)
    # two brackets from the front lip up to the frame's front cross tube
    blk(m, BODY, (0.014, 0.005, 0.068), "black", frame_mat((0.060, -0.177, 0.428), (1, 0, 0), (0, 1, 0)),
        mirror=True)


# =============================================================================== rider controls

def footpegs(m):
    """Folding serrated footpegs on clevis brackets under the pivot plates (both sides)."""
    f = S.FOOTPEG
    peg_len = 0.080
    hinge_x = f.x - peg_len / 2 - 0.004  # the peg body is centred on spec.FOOTPEG
    # clevis bracket hanging under the pivot plate
    blk(m, BODY, (0.020, 0.060, 0.034), "dark_alu", frame_mat((hinge_x - 0.004, f.y, f.z - 0.005), (1, 0, 0),
                                                             (0, 1, 0)), bevel=0.004, mirror=True)
    # hinge pin along Y and the peg knuckle
    m.cylinder(BODY, 0.0045, 0.066, "steel", matrix=look((hinge_x, f.y, f.z + 0.004), (0, 1, 0)), segments=8,
               mirror=True)
    m.cylinder(BODY, 0.009, 0.036, "dark_alu", matrix=look((hinge_x, f.y, f.z + 0.004), (0, 1, 0)), segments=10,
               mirror=True)
    # two serrated side rails and cross bars
    x0, length = hinge_x + 0.004, peg_len
    teeth = 5
    rail = [(0.0, -0.011), (length, -0.011), (length, 0.004)]
    for i in range(teeth):
        u = length - (i + 0.5) * length / teeth
        rail += [(u + 0.004, 0.006), (u + 0.0015, 0.012), (u - 0.0015, 0.012), (u - 0.004, 0.006)]
    rail += [(0.0, 0.006)]
    for dy in (-0.022, 0.022):
        mat = frame_mat((x0, f.y + dy, f.z), (1, 0, 0), (0, 0, 1))
        slab(m, BODY, rail, 0.006, "dark_alu", mat, bevel=0.0, mirror=True)
    for u in (0.012, 0.045, 0.075):  # all within the side rails' length
        blk(m, BODY, (0.008, 0.040, 0.014), "dark_alu", frame_mat((x0 + u, f.y, f.z - 0.001), (1, 0, 0),
                                                                 (0, 1, 0)), mirror=True)


def kickstand(m):
    """Kickstand on the left, folded back along under the swingarm."""
    piv = Vector((PIVOT_PLATE_X + 0.016, 0.186, 0.300))
    blk(m, BODY, (0.016, 0.040, 0.030), "dark_alu", frame_mat(piv + Vector((-0.006, -0.012, 0.004)), (1, 0, 0),
                                                             (0, 1, 0)), bevel=0.003)
    m.cylinder(BODY, 0.012, 0.016, "dark_alu", matrix=look(piv + Vector((0.012, 0, 0)), XAXIS), segments=12)
    hexbolt(m, BODY, piv + Vector((0.022, 0, 0)), XAXIS, 0.007, 0.005)
    leg = [piv + Vector((0.014, 0.0, 0.0)), Vector((piv.x + 0.020, 0.330, 0.318)), Vector((piv.x + 0.022, 0.468,
                                                                                            0.338))]
    pipe(m, BODY, leg, 0.011, "dark_alu", radii=[0, 0.25, 0], rads=[0.0115, 0.010, 0.0085], segments=12,
         step=20)
    foot = leg[-1] + Vector((0.0, 0.010, -0.004))
    blk(m, BODY, (0.020, 0.036, 0.014), "dark_alu", frame_mat(foot, (1, 0, 0), (0, 1, 0.15)), bevel=0.004)
    # foot tang and return spring
    pipe(m, BODY, [leg[0] + Vector((0.004, 0.035, 0.002)), leg[0] + Vector((0.030, 0.050, 0.010))], 0.0045,
         "dark_alu", segments=8)
    pipe(m, BODY, [piv + Vector((0.004, -0.018, 0.014)), Vector((piv.x + 0.012, 0.250, 0.316))], 0.0035, "steel",
         segments=8)


# =============================================================================== rear shock

def rear_shock(m):
    """Coil-over shock from the frame (top) to the swingarm clevis (bottom); body up, shaft down.

    It is split so the suspension can move: "Shock" (body, top eye, preload collar and spring; pivot
    spec.SHOCK_TOP) and "ShockRod" (lower eye, rod end, spring seat and chrome shaft; pivot
    spec.SHOCK_BOTTOM, it rides on the swingarm). Aimed at each other, the shaft slides into the body.
    """
    bot, top = S.SHOCK_BOTTOM, S.SHOCK_TOP
    ax = (top - bot).normalized()
    ln = (top - bot).length
    base = look(bot, ax, up=(0, 1, 0))
    # eyes (bushings along X)
    m.cylinder(ROD, 0.0155, 0.022, "dark_alu", matrix=look(bot, XAXIS), segments=12)
    m.cylinder(SHOCK, 0.0165, 0.026, "dark_alu", matrix=look(top, XAXIS), segments=12)
    # rod end + lower spring seat
    m.lathe(ROD, [(0.012, 0.012), (0.013, 0.040), (0.035, 0.043), (0.036, 0.050), (0.030, 0.054),
                  (0.008, 0.055)], "dark_alu", matrix=base, segments=14)
    # chrome shaft (its top end runs on inside the body, so it stays hidden as the shock compresses)
    m.lathe(ROD, [(0.0079, 0.052), (0.0079, 0.230), (0.0, 0.230)], "chrome", matrix=base, segments=12)
    # body with seal head and top cap
    m.lathe(SHOCK, [(0.0079, 0.168), (0.020, 0.168), (0.023, 0.176), (0.023, 0.340), (0.019, 0.350),
                    (0.016, 0.352), (0.016, ln - 0.012)], "battery", matrix=base, segments=14)
    # preload collar
    m.lathe(SHOCK, [(0.023, 0.296), (0.033, 0.297), (0.034, 0.306), (0.033, 0.315), (0.023, 0.316)], "dark_alu",
            matrix=base, segments=14)
    # the coil spring: a wire swept along a helix with closed end coils
    m.tube(SHOCK, spring_helix(bot, ax, 0.0285, 0.054, 0.296, 6.0, 9, 0.0055), 0.0055, "black", segments=6)


def spring_helix(base, axis, r, s0, s1, turns, per_turn, wire):
    """Helix of radius r along `axis` from s0 to s1 (distances from base), with closed end coils."""
    axis = Vector(axis).normalized()
    e1 = axis.cross(Vector((1, 0, 0))).normalized()
    e2 = axis.cross(e1)
    total = 2 * math.pi * turns
    n = int(turns * per_turn) + 1
    closed = 0.8 * 2 * math.pi  # closed (ground) end coils, pitch = wire diameter
    end_rise = 2 * wire * closed / (2 * math.pi)
    a0, a1 = s0 + wire, s1 - wire
    mid = (a1 - a0) - 2 * end_rise
    pts = []
    for i in range(n + 1):
        phi = total * i / n
        if phi < closed:
            s = a0 + end_rise * phi / closed
        elif phi > total - closed:
            s = a1 - end_rise * (total - phi) / closed
        else:
            s = a0 + end_rise + mid * (phi - closed) / (total - 2 * closed)
        pts.append(Vector(base) + axis * s + (e1 * math.cos(phi) + e2 * math.sin(phi)) * r)
    return pts


def frame_brake_hose(m):
    """Rear brake hose on the frame: from the pivot area up the right rear section to a clip."""
    pts = [(-0.104, 0.188, 0.452), (-0.106, 0.198, 0.560), (-0.106, 0.190, 0.680), (-0.112, 0.166, 0.735)]
    pipe(m, BODY, pts, 0.0042, "black", radii=[0, 0.05, 0.04, 0], segments=6, step=30)
    rbox(m, BODY, (0.006, 0.014, 0.012), "black", frame_mat((-0.103, 0.197, 0.620), (1, 0, 0), (0, 1, 0)),
         r=0.002, bevel=0.0, cs=1)


# =============================================================================== swingarm

ARM_CTRL = [(S.SWINGARM_ARM_X, S.SWINGARM_PIVOT.y, S.SWINGARM_PIVOT.z), (S.SWINGARM_ARM_X, 0.400, 0.372),
            (S.SWINGARM_ARM_X, 0.668, 0.300)]
ARM_W, ARM_H = 0.030, 0.060


def arm_z(y):
    """Centre height of the swingarm arm at y (piecewise linear through ARM_CTRL)."""
    pts = [(c[1], c[2]) for c in ARM_CTRL]
    for (y0, z0), (y1, z1) in zip(pts, pts[1:]):
        if y <= y1:
            return z0 + (z1 - z0) * (y - y0) / (y1 - y0)
    return pts[-1][1]


def swingarm(m):
    """Tapered box-section arms, pivot bosses, cross brace with the shock clevis, axle hardware, chain slider."""
    p, ax = S.SWINGARM_PIVOT, S.REAR_AXLE
    xa = S.SWINGARM_ARM_X
    # tapered box-section arms
    beam(m, ARM, ARM_CTRL, [0, 0.35, 0], "alu", ARM_W, ARM_H, r=0.009, cs=3,
         scales=[(1.0, 1.15), (1.0, 0.98), (0.95, 0.70)], mirror=True)
    # pivot bosses with bushings
    m.lathe(ARM, [(0.0, -0.016), (0.022, -0.016), (0.028, -0.012), (0.028, 0.012), (0.022, 0.016),
                  (0.0, 0.016)], "alu", matrix=look((xa, p.y, p.z), XAXIS), segments=16, mirror=True)
    m.cylinder(ARM, 0.012, 0.004, "black", matrix=look((xa - 0.017, p.y, p.z), XAXIS), segments=12, mirror=True)
    # cross brace in front of the tyre (between the chain runs) and the shock clevis
    yb = 0.285
    zb = arm_z(yb) - 0.008
    m.sweep(ARM, [(-xa + 0.01, yb, zb), (xa - 0.01, yb, zb)], rounded_rect(0.046, 0.032, 0.012, 3), "alu",
            lateral=(0, 0, 1))
    sb = S.SHOCK_BOTTOM
    tab = fillet_outline([(yb - 0.012, zb - 0.020), (yb + 0.02, zb - 0.022), (sb.y + 0.014, sb.z - 0.010),
                          (sb.y + 0.012, sb.z + 0.014), (sb.y - 0.012, sb.z + 0.016), (yb - 0.010, zb + 0.020)],
                         [0.006, 0.01, 0.01, 0.008, 0.01, 0.006], step=40)
    slab(m, ARM, tab, 0.007, "alu", side_mat(0.0155), mirror=True)
    m.cylinder(ARM, 0.006, 0.048, "steel", matrix=look(sb, XAXIS), segments=8)
    hexbolt(m, ARM, sb + Vector((0.022, 0, 0)), XAXIS, 0.0095, 0.006)
    # rear ends: axle blocks, adjuster bolts, end caps, axle and nuts
    for side in (1, -1):
        xo = side * (xa + ARM_W / 2 + 0.004)
        blk(m, ARM, (0.008, 0.044, 0.030), "dark_alu", frame_mat((xo, ax.y + 0.004, ax.z), (1, 0, 0), (0, 1, 0)),
            bevel=0.002)
        blk(m, ARM, (ARM_W + 0.004, 0.006, 0.036), "dark_alu",
            frame_mat((side * xa, 0.670, arm_z(0.670)), (1, 0, 0), (0, 1, 0)), bevel=0.002)
        m.cylinder(ARM, 0.0042, 0.050, "steel", matrix=look((side * xa, 0.668, ax.z), (0, 1, 0)), segments=8)
        hexbolt(m, ARM, (side * xa, 0.688, ax.z), (0, 1, 0), 0.0075, 0.007)
    m.cylinder(ARM, 0.0085, 2 * (xa + ARM_W / 2 + 0.012), "steel", matrix=look(ax, XAXIS), segments=12)
    hexbolt(m, ARM, (xa + ARM_W / 2 + 0.014, ax.y, ax.z), XAXIS, 0.0135, 0.010)  # axle nut (left)
    hexbolt(m, ARM, (-(xa + ARM_W / 2 + 0.013), ax.y, ax.z), XAXIS, 0.0135, 0.008)  # axle head (right)
    # chain slider on the inside of the left arm by the pivot
    ang = math.atan2(arm_z(0.33) - arm_z(0.17), 0.16)
    rbox(m, ARM, (0.17, 0.074, 0.007), "black",
         frame_mat((xa - ARM_W / 2 - 0.0025, 0.252, arm_z(0.252)), (0, math.cos(ang), math.sin(ang)),
                   (0, -math.sin(ang), math.cos(ang))), r=0.008, bevel=0.0015, cs=2, segs=1)


def chain(m, pitch=0.0127):
    """Drive chain on the left: alternating outer and inner link plates round both sprockets."""
    fs, ax = S.FRONT_SPROCKET, S.REAR_AXLE
    segs, total = belt((fs.y, fs.z), S.FRONT_SPROCKET_RADIUS, (ax.y, ax.z), S.REAR_SPROCKET_RADIUS)
    n = int(round(total / pitch / 2)) * 2
    p = total / n
    pins = [belt_point(segs, i * p) for i in range(n)]
    verts, faces = [], []
    for i in range(n):
        a, b = pins[i], pins[(i + 1) % n]
        u = (b - a).normalized()
        nv = Vector((-u.y, u.x))
        mid = (a + b) / 2
        outer = i % 2 == 0
        hl = (b - a).length / 2 + (0.0048 if outer else 0.0036)
        hh = 0.0056 if outer else 0.0047
        wx = 0.0086 if outer else 0.0062
        c = hh * 0.85
        hexa = [(-hl, 0), (-hl + c, -hh), (hl - c, -hh), (hl, 0), (hl - c, hh), (-hl + c, hh)]
        base = len(verts)
        for sx in (-wx, wx):
            for (al, ac) in hexa:
                q = mid + u * al + nv * ac
                verts.append((S.CHAIN_X + sx, q.x, q.y))
        faces.append(tuple(base + j for j in range(6)))
        faces.append(tuple(base + 6 + j for j in reversed(range(6))))
        for j in range(6):
            j1 = (j + 1) % 6
            faces.append((base + j, base + j1, base + 6 + j1, base + 6 + j))
    m.mesh(ARM, verts, faces, "steel", smooth=False)


def rear_caliper(m):
    """Rear brake caliper on the RIGHT, ahead of and below the axle, on a bracket from the axle."""
    ax = S.REAR_AXLE
    xd = S.REAR_DISC_X
    th = math.radians(222.0)  # low enough to clear the arm, so the body can sit out past it
    d = Vector((0.0, math.cos(th), math.sin(th)))  # radial (y, z)
    t = Vector((0.0, -math.sin(th), math.cos(th)))  # tangential
    rc = S.REAR_DISC_RADIUS - 0.012
    cen = ax + d * rc
    cen.x = xd - 0.009  # floating caliper: piston half outboard of the disc
    # caliper body (two halves bridged over the disc)
    body = frame_mat(cen, t, d)
    rbox(m, ARM, (0.066, 0.040, 0.044), "black", body, r=0.012, bevel=0.005, cs=3, segs=2)
    rbox(m, ARM, (0.046, 0.026, 0.010), "black", body @ Matrix.Translation((0, 0.004, 0.026)), r=0.009,
         bevel=0.002, cs=2, segs=1)  # piston housing bulge on the outer face (local +Z = world -X)
    for s in (-0.027, 0.027):  # caliper bolts on the outer face
        hexbolt(m, ARM, cen + t * s + d * 0.004 + Vector((-0.023, 0, 0)), XAXIS, 0.0045, 0.004)
    # bracket from the axle to the caliper (inside the right arm)
    br_x = -(S.SWINGARM_ARM_X - ARM_W / 2) + 0.004
    a2, c2 = Vector((ax.y, ax.z)), Vector((cen.y, cen.z))
    slab(m, ARM, belt_outline(a2, 0.016, c2 - (c2 - a2).normalized() * 0.010, 0.017, step_deg=24), 0.006,
         "dark_alu", side_mat(br_x))
    # torque stop pin up into a lug under the arm
    lug_y = cen.y - 0.020
    blk(m, ARM, (0.012, 0.020, 0.026), "alu", frame_mat((-S.SWINGARM_ARM_X, lug_y, arm_z(lug_y) - 0.030),
                                                        (1, 0, 0), (0, 1, 0)), bevel=0.002)
    # banjo, bleed nipple and the hose forward along the right arm
    banjo = cen - t * 0.030 + d * 0.012 + Vector((-0.010, 0, 0))
    hexbolt(m, ARM, banjo, XAXIS, 0.0065, 0.012)
    m.cylinder(ARM, 0.0028, 0.012, "steel", matrix=look(cen - t * 0.028 - d * 0.010, (0, -0.3, -1)), segments=6)
    yb = banjo.y - 0.03
    hose = [banjo, (banjo.x + 0.002, yb, arm_z(yb) - 0.030), (-0.104, 0.40, arm_z(0.40) - 0.032),
            (-0.104, 0.24, arm_z(0.24) - 0.036), (-0.104, 0.188, 0.452)]
    pipe(m, ARM, hose, 0.0042, "black", radii=[0, 0.02, 0.1, 0.06, 0], segments=8, step=22)
    for y in (0.30, 0.46):  # hose clips
        blk(m, ARM, (0.010, 0.010, 0.012), "black", frame_mat((-0.104, y, arm_z(y) - 0.030), (1, 0, 0), (0, 1, 0)))


# =============================================================================== entry point

def build(m):
    # Body: frame
    frame_loops(m)
    head_tube(m)
    cross_members(m)
    pivot_plates(m)
    subframe(m)
    # Body: power train and mechanics
    battery(m)
    controller(m)
    motor(m)
    gearbox(m)
    skid_plate(m)
    footpegs(m)
    kickstand(m)
    rear_shock(m)
    frame_brake_hose(m)
    # Swingarm group
    swingarm(m)
    chain(m)
    rear_caliper(m)
