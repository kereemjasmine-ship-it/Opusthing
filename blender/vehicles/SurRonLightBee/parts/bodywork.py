"""Bodywork of the Sur-Ron Light Bee X (mid-poly, Roblox-ready): the plastics and the seat.

Group "Body" (shared with chassis.py, which adds the frame and the mechanics):
  * seat: long, thin, flat dirt-bike seat from spec.SEAT_FRONT to spec.SEAT_REAR with a
    narrow nose, rounded shoulders, a slight dish and a pointed tail
  * front shroud: white moulded cover over the headstock, the front of the top beams and the
    top of the battery; the seat nose sits in a channel between its two raised flanks
  * side panels (both sides): large white covers over the frame top beams and the upper
    battery, from behind the head tube back under the seat, with an angled lower edge, a
    raised upper flare (a sculpted shape line) and a grey stripe decal
  * rear side panels (both sides): white covers under the back of the seat that taper into
    the tail, with a grey decal
  * rear fender / tail: short white fender from under the seat to spec.TAIL_END (just behind the
    rear axle, as on the real bike), sweeping up
    slightly at the tip, with a black tail-light unit under it carrying a red LED lens
    (light_red -> Body_NeonRed in Roblox) and a red reflector
  * black inner rear mudguard under the fender: an arc concentric with the rear wheel whose
    skin stays >= 20 cm from the tyre, its side flanges standing on the subframe rails

All positions are world metres from spec.py (Z up, the bike faces -Y, the rider's left is
+X). Pieces that exist on both sides are built on the LEFT (+X) and use mirror=True.

Construction: the plastics are thin moulded shells (SHELL = 4 mm walls). shell() turns a
grid of outer-surface points into a closed shell (outer skin, inner skin offset along the
surface normal, and a rim round the edge with a 2.5 mm chamfer on the outer edge); faces are
wound outwards explicitly, since Roblox does not draw back faces. Side panels are laid out as 2D outlines in the
side view (y, z) and wrapped onto a gently curved surface x = f(y, z) (outline_grid()), so
their outlines can be drawn freely while the surface stays smooth. The shroud, fender and
mudguard are lofts through hand-placed cross-sections; the seat is a closed loft.
"""

import math

import bmesh
from mathutils import Vector

import spec as S
from midpoly import look, tr

BODY = "Body"
SHELL = 0.004  # plastic wall thickness

# =============================================================================== helpers


def curve(table, t):
    """Smooth (cubic Hermite) interpolation through [(t, value), ...]; value may be a tuple."""
    ts = [k[0] for k in table]
    if t <= ts[0]:
        return table[0][1]
    if t >= ts[-1]:
        return table[-1][1]
    i = max(k for k in range(len(ts) - 1) if ts[k] <= t)
    vals = [k[1] if isinstance(k[1], tuple) else (k[1],) for k in table]

    def slope(k, c):
        if k == 0:
            return (vals[1][c] - vals[0][c]) / (ts[1] - ts[0])
        if k == len(ts) - 1:
            return (vals[k][c] - vals[k - 1][c]) / (ts[k] - ts[k - 1])
        a = (vals[k][c] - vals[k - 1][c]) / (ts[k] - ts[k - 1])
        b = (vals[k + 1][c] - vals[k][c]) / (ts[k + 1] - ts[k])
        return 0.0 if a * b <= 0 else (a + b) / 2  # flat at turning points: no overshoot

    h = ts[i + 1] - ts[i]
    u = (t - ts[i]) / h
    h00, h10, h01, h11 = 2 * u ** 3 - 3 * u ** 2 + 1, u ** 3 - 2 * u ** 2 + u, -2 * u ** 3 + 3 * u ** 2, u ** 3 - u ** 2
    out = tuple(h00 * vals[i][c] + h10 * h * slope(i, c) + h01 * vals[i + 1][c] + h11 * h * slope(i + 1, c)
                for c in range(len(vals[0])))
    return out if isinstance(table[0][1], tuple) else out[0]


def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def fillet2d(pts, radii, step=30.0):
    """Closed 2D polygon with each corner rounded (radius per corner, or one number)."""
    pts = [Vector(p) for p in pts]
    n = len(pts)
    rr = [radii] * n if isinstance(radii, (int, float)) else list(radii)
    out = []
    for i in range(n):
        p, a, b = pts[i], pts[i - 1], pts[(i + 1) % n]
        d1, d2 = (p - a), (b - p)
        l1, l2 = d1.length, d2.length
        d1.normalize()
        d2.normalize()
        turn = math.acos(max(-1.0, min(1.0, d1.dot(d2))))
        if rr[i] <= 0 or turn < math.radians(2):
            out.append(p)
            continue
        t = min(rr[i] * math.tan(turn / 2), 0.45 * l1, 0.45 * l2)
        s, e = p - d1 * t, p + d2 * t
        k = max(2, math.ceil(math.degrees(turn) / step))
        for j in range(k + 1):
            u = j / k
            out.append((1 - u) ** 2 * s + 2 * (1 - u) * u * p + u * u * e)
    return out


def _chain_eval(chain, cum, t):
    """Point at normalised arc length t on a polyline with cumulative lengths cum (0..1)."""
    for k in range(len(chain) - 1):
        if t <= cum[k + 1] or k == len(chain) - 2:
            span = max(cum[k + 1] - cum[k], 1e-9)
            return chain[k].lerp(chain[k + 1], max(0.0, min(1.0, (t - cum[k]) / span)))
    return chain[-1]


def outline_grid(outline, rows, xfun, max_gap=0.09, min_gap=0.025):
    """Wrap a side-view outline [(y, z), ...] onto the surface x = xfun(y, z).

    The outline is split at its front-most and rear-most points into a lower and an upper
    chain; both are sampled at the same normalised arc lengths (every vertex of either chain,
    thinned to min_gap and filled to max_gap) and joined by straight columns. rows is a row
    count or a list of fractions 0..1 (bottom to top), e.g. bunched near a curled edge.
    Returns grid[i][j] (i front to back, j bottom to top) of world points.
    """
    pts = [Vector(p) for p in outline]  # 2D: .x is world y, .y is world z
    n = len(pts)
    imin = min(range(n), key=lambda i: (pts[i].x, pts[i].y))
    imax = max(range(n), key=lambda i: (pts[i].x, pts[i].y))
    chains = [[pts[(imin + k) % n] for k in range((imax - imin) % n + 1)],
              [pts[(imin - k) % n] for k in range((imin - imax) % n + 1)]]
    cums = []
    for ch in chains:
        ln = [0.0]
        for a, b in zip(ch, ch[1:]):
            ln.append(ln[-1] + (b - a).length)
        cums.append([v / ln[-1] for v in ln])
    ts = sorted(set(cums[0]) | set(cums[1]))
    thin = [ts[0]]
    for t in ts[1:]:
        if t - thin[-1] >= min_gap or t == 1.0:
            if t == 1.0 and 1.0 - thin[-1] < min_gap and len(thin) > 1:
                thin[-1] = 1.0
            else:
                thin.append(t)
    full = [thin[0]]
    for t in thin[1:]:
        k = math.ceil((t - full[-1]) / max_gap)
        full += [full[-1] + (t - full[-1]) * q / k for q in range(1, k)] + [t]
    sides = [[_chain_eval(ch, cum, t) for t in full] for ch, cum in zip(chains, cums)]
    if sum(p.y for p in sides[0]) > sum(p.y for p in sides[1]):
        sides.reverse()
    lower, upper = sides
    fr = [j / rows for j in range(rows + 1)] if isinstance(rows, int) else rows
    grid = []
    for a, b in zip(lower, upper):
        col = []
        for f in fr:
            p = a.lerp(b, f)
            col.append(Vector((xfun(p.x, p.y), p.x, p.y)))
        grid.append(col)
    return grid


def grid_normals(grid, hint):
    """Unit normals of a point grid, all turned to the side `hint(p)` points to."""
    ni, nj = len(grid), len(grid[0])
    raw = []
    for i in range(ni):
        row = []
        for j in range(nj):
            du = grid[min(i + 1, ni - 1)][j] - grid[max(i - 1, 0)][j]
            dv = grid[i][min(j + 1, nj - 1)] - grid[i][max(j - 1, 0)]
            if du.length < 1e-7:  # collapsed column (pointed end): look one column in
                k = 1 if i == 0 else -1
                du = grid[i + k][j] - grid[i][j]
            if dv.length < 1e-7:
                k = 1 if j == 0 else -1
                dv = grid[i][j + k] - grid[i][j]
            row.append(du.cross(dv))
        raw.append(row)
    sign = 1.0 if sum(raw[i][j].dot(hint(grid[i][j])) for i in range(ni) for j in range(nj)) >= 0 else -1.0
    out = []
    for row in raw:
        out.append([(v * sign).normalized() if v.length > 1e-12 else Vector((0, 0, 1)) for v in row])
    return out, sign


def shell(m, outer, color, thick=SHELL, inner=None, hint=None, back=True, rim=True, bevel=0.0, mirror=False,
          smooth=True):
    """A moulded shell from a grid of outer-surface points outer[i][j].

    inner: explicit inner grid (otherwise the outer grid offset `thick` against the normal).
    hint(p): a vector pointing out of the part at p (picks the outer side).
    bevel: chamfers the outer edge all round by this much (a moulded edge that catches light).
    back=False leaves out the inner skin (for raised details whose back is buried in a panel);
    rim=False also leaves out the edge (a decal sheet). Faces are wound here (outer faces
    towards hint) and committed without a normal recalculation, so open pieces stay right.
    """
    hint = hint or (lambda p: Vector((1, 0, 0)))
    normals, sign = grid_normals(outer, hint)
    ni, nj = len(outer), len(outer[0])
    for i in range(ni):  # a pointed end (collapsed column) gets one normal, so it stays one point
        if all((p - outer[i][0]).length < 1e-6 for p in outer[i]):
            avg = sum(normals[i], Vector()).normalized()
            normals[i] = [avg] * nj
    if inner is None:
        inner = [[outer[i][j] - normals[i][j] * thick for j in range(nj)] for i in range(ni)]
    loop = ([(i, 0) for i in range(ni)] + [(ni - 1, j) for j in range(1, nj)] +
            [(i, nj - 1) for i in range(ni - 2, -1, -1)] + [(0, j) for j in range(nj - 2, 0, -1)])
    face_pts = [list(col) for col in outer]  # the outer skin (boundary pulled in when bevelled)
    cham = {}
    if rim and bevel > 0:
        nl = len(loop)
        for k, (i, j) in enumerate(loop):
            p, n = outer[i][j], normals[i][j]
            cham[(i, j)] = p - n * min(bevel, 0.6 * thick)
            if all((q - outer[i][0]).length < 1e-6 for q in outer[i]):  # pointed end: no chamfer
                continue
            # step into the skin square to the boundary (a 2D offset of the edge in the tangent plane)
            into, reach = Vector(), 1.0
            for di, dj, edge in ((0, 1, j == 0), (0, -1, j == nj - 1), (1, 0, i == 0), (-1, 0, i == ni - 1)):
                if edge:
                    v = outer[i + di][j + dj] - p
                    if v.length > 1e-6:
                        reach = min(reach, v.length)
                        into += v.normalized()
            prv, nxt = outer[loop[k - 1][0]][loop[k - 1][1]], outer[loop[(k + 1) % nl][0]][loop[(k + 1) % nl][1]]
            t = nxt - prv
            d = n.cross(t) if t.length > 1e-7 else into
            d -= n * d.dot(n)
            if d.dot(into) < 0:
                d = -d
            if d.length > 1e-7:
                face_pts[i][j] = p + d.normalized() * min(bevel, 0.4 * reach)
    bm = bmesh.new()
    cache = {}

    def vert(p):
        key = (round(p.x, 6), round(p.y, 6), round(p.z, 6))
        if key not in cache:
            cache[key] = bm.verts.new(p)
        return cache[key]

    ov = [[vert(p) for p in col] for col in face_pts]  # outer skin verts
    iv = [[vert(p) for p in col] for col in inner]  # inner skin verts

    def face(vs):
        uniq = []
        for v in vs:
            if v not in uniq:
                uniq.append(v)
        if len(uniq) >= 3:
            try:
                bm.faces.new(uniq)
            except ValueError:
                pass

    for i in range(ni - 1):
        for j in range(nj - 1):
            q = [ov[i][j], ov[i + 1][j], ov[i + 1][j + 1], ov[i][j + 1]]
            face(q if sign > 0 else q[::-1])
            if back:
                q = [iv[i][j], iv[i + 1][j], iv[i + 1][j + 1], iv[i][j + 1]]
                face(q[::-1] if sign > 0 else q)
    if rim:
        # rim strips round the boundary loop (outer skin -> [chamfer ring] -> inner skin),
        # each face turned to face away from the grid interior
        cen = sum((p for col in outer for p in col), Vector()) / (ni * nj)
        rings = [(ov, face_pts)]
        if cham:
            rings.append(({k: vert(p) for k, p in cham.items()}, cham))
        rings.append((iv, inner))

        def at(ring, ij):
            return ring[ij] if isinstance(ring, dict) else ring[ij[0]][ij[1]]

        for k in range(len(loop)):
            a, b = loop[k], loop[(k + 1) % len(loop)]
            if a[1] == b[1]:  # a j-side of the grid: step inwards along j
                inward = (0, 1) if a[1] == 0 else (0, -1)
            else:  # an i-side: step inwards along i
                inward = (1, 0) if a[0] == 0 else (-1, 0)
            mid = (outer[a[0]][a[1]] + outer[b[0]][b[1]]) / 2
            nb = (outer[a[0] + inward[0]][a[1] + inward[1]] + outer[b[0] + inward[0]][b[1] + inward[1]]) / 2
            out_dir = mid - nb if (mid - nb).length > 1e-7 else mid - cen
            for (v0, p0), (v1, p1) in zip(rings, rings[1:]):
                q = [at(v0, a), at(v0, b), at(v1, b), at(v1, a)]
                pa, pb = at(p0, a), at(p0, b)
                fn = (pb - pa).cross(at(p1, a) - pa)
                if fn.length < 1e-12:
                    fn = (pb - pa).cross(at(p1, b) - pa)
                face(q if fn.dot(out_dir) >= 0 else q[::-1])
    # without a back skin the inner grid's interior points are unused: drop them (no loose verts in the export)
    unused = [v for v in bm.verts if not v.link_faces]
    if unused:
        bmesh.ops.delete(bm, geom=unused, context="VERTS")
    m.commit(BODY, bm, color, mirror=mirror, smooth=smooth, recalc=False)


def lift_grid(grid, xfun, dx):
    """Copy of a side-panel grid moved to x = xfun(y, z) + dx (for raised details and decals)."""
    return [[Vector((xfun(p.y, p.z) + dx, p.y, p.z)) for p in col] for col in grid]


# =============================================================================== seat
# Plan width, top line and bottom line of the seat along y. SEAT_FRONT / SEAT_REAR are the
# top surface at the nose and at the tail; the seat sits in the shroud channel at the front,
# on the battery and frame top beams in the middle, on the subframe rails and the fender behind.

SEAT_Y = [-0.138, -0.134, -0.128, -0.120, -0.100, -0.070, -0.030, 0.020, 0.080, 0.160, 0.250, 0.340, 0.420,
          0.480, 0.520, 0.540, 0.553, 0.562]
SEAT_W = [(-0.138, 0.010), (-0.134, 0.024), (-0.128, 0.033), (-0.120, 0.041), (-0.100, 0.053), (-0.070, 0.067),
          (-0.030, 0.084), (0.020, 0.100), (0.080, 0.112), (0.160, 0.119), (0.250, S.SEAT_MAX_HALF_WIDTH),
          (0.340, 0.118), (0.420, 0.111), (0.480, 0.098), (0.520, 0.080), (0.540, 0.064), (0.553, 0.044),
          (0.562, 0.020)]
SEAT_BOT = [(-0.138, 0.817), (-0.030, 0.814), (0.060, 0.812), (0.200, 0.807), (0.330, 0.808), (0.400, 0.818),
            (0.450, 0.829), (0.500, 0.843), (0.530, 0.851), (0.562, 0.861)]
SEAT_EDGE_LIFT = [(-0.138, 0.002), (-0.120, 0.008), (-0.060, 0.013), (0.000, 0.016), (0.060, 0.012),
                  (0.120, 0.006), (0.200, 0.004), (0.562, 0.002)]


def seat_top(y):
    """Centre-line height of the seat top: SEAT_FRONT -> SEAT_REAR with a slight dish, rounded ends."""
    f, r = S.SEAT_FRONT, S.SEAT_REAR
    u = max(0.0, min(1.0, (y - f.y) / (r.y - f.y)))
    z = f.z + (r.z - f.z) * u ** 1.25 - 0.004 * math.sin(math.pi * u)
    z -= 0.016 * smoothstep(-0.120, -0.139, y)  # nose rolls down
    z -= 0.016 * smoothstep(0.525, 0.563, y)  # tail tip rolls down onto the fender
    return z


def seat_section(y):
    """Closed cross-section loop of the seat at y (20 points): flat crown, tight rounded shoulders."""
    w = curve(SEAT_W, y)
    zt = seat_top(y)
    zb = curve(SEAT_BOT, y)
    zbe = zb + curve(SEAT_EDGE_LIFT, y)
    zs = zt - 0.004  # shoulder line sits a little below the crown
    r = max(0.004, min(0.017, 0.6 * (zs - zbe), 0.6 * w))
    half = [(0.0, zt)]
    for f in (0.40, 0.78):  # crown
        x = f * (w - r)
        half.append((x, zt - (zt - zs) * f * f))
    for a in (75, 45, 15, -12):  # rounded shoulder down into the side
        ang = math.radians(a)
        half.append((w - r + r * math.cos(ang), zs - r + r * math.sin(ang)))
    half += [(w - 0.003, zbe + 0.003), (w - 0.010, zbe), (0.55 * w, zb + (zbe - zb) * 0.3)]
    loop = half + [(0.0, zb)] + [(-x, z) for (x, z) in reversed(half[1:])]
    return [Vector((x, y, z)) for (x, z) in loop]


def seat(m):
    """The long flat seat with rounded edges."""
    m.loft(BODY, [seat_section(y) for y in SEAT_Y], "seat", closed=True, caps=True)


# =============================================================================== front shroud
# Cross-sections (y, half-profile from the skirt edge up over the flank to the centre line).
# The front three sections dome over the headstock; behind them the centre drops into a
# channel for the seat nose, leaving a raised flank over each top beam that runs back under
# the seat edge.

SHROUD = [
    (-0.250, [(0.092, 0.795), (0.098, 0.842), (0.093, 0.876), (0.078, 0.898), (0.055, 0.906), (0.033, 0.908),
              (0.014, 0.909), (0.0, 0.909)]),
    (-0.225, [(0.099, 0.792), (0.105, 0.838), (0.100, 0.873), (0.084, 0.894), (0.060, 0.900), (0.036, 0.901),
              (0.015, 0.901), (0.0, 0.901)]),
    (-0.195, [(0.106, 0.789), (0.112, 0.834), (0.107, 0.869), (0.089, 0.888), (0.064, 0.891), (0.040, 0.888),
              (0.017, 0.886), (0.0, 0.886)]),
    (-0.165, [(0.112, 0.786), (0.118, 0.830), (0.112, 0.864), (0.094, 0.882), (0.070, 0.879), (0.046, 0.865),
              (0.020, 0.857), (0.0, 0.856)]),
    (-0.140, [(0.117, 0.786), (0.122, 0.827), (0.116, 0.859), (0.097, 0.874), (0.074, 0.864), (0.052, 0.839),
              (0.026, 0.828), (0.0, 0.826)]),
    (-0.120, [(0.121, 0.788), (0.126, 0.824), (0.119, 0.853), (0.100, 0.867), (0.078, 0.857), (0.062, 0.827),
              (0.035, 0.815), (0.0, 0.813)]),
    (-0.090, [(0.125, 0.792), (0.129, 0.821), (0.122, 0.846), (0.104, 0.859), (0.085, 0.848), (0.074, 0.823),
              (0.048, 0.813), (0.0, 0.812)]),
    (-0.055, [(0.130, 0.800), (0.133, 0.819), (0.126, 0.840), (0.110, 0.852), (0.097, 0.845), (0.090, 0.826),
              (0.055, 0.813), (0.0, 0.812)]),
    (-0.030, [(0.132, 0.806), (0.135, 0.823), (0.128, 0.837), (0.114, 0.846), (0.102, 0.840), (0.095, 0.825),
              (0.060, 0.812), (0.0, 0.811)]),
    (0.000, [(0.133, 0.812), (0.136, 0.828), (0.129, 0.839), (0.116, 0.841), (0.105, 0.835), (0.099, 0.824),
             (0.060, 0.811), (0.0, 0.810)]),
    (0.040, [(0.134, 0.809), (0.137, 0.824), (0.130, 0.834), (0.119, 0.836), (0.110, 0.830), (0.106, 0.820),
             (0.070, 0.810), (0.0, 0.809)]),
]
SHROUD_RAKE = {0: 0.35, 1: 0.22, 2: 0.08}  # front sections lean back with the head tube (about z = 0.85)
SHROUD_DECAL_ROWS = range(1, 10)  # sections carrying the flank graphic
SHROUD_DECAL_COLS = (2, 3, 4)  # profile points it spans (left flank: shoulder to the channel wall)


def front_shroud(m):
    """White moulded cover over the headstock, front top beams and battery top."""
    grid = []
    for k, (y, half) in enumerate(SHROUD):
        prof = half + [(-x, z) for (x, z) in reversed(half[:-1])]
        rake = SHROUD_RAKE.get(k, 0.0)
        grid.append([Vector((x, y - rake * (z - 0.85), z)) for (x, z) in prof])
    hint = lambda p: Vector((p.x, 0.0, 1.0))  # noqa: E731
    shell(m, grid, "white", hint=hint, bevel=0.0025)
    # grey graphic along the top of each flank (a decal sheet 1 mm proud of the surface). Both
    # sides are cut from the shroud's own grid (not mirrored) so their quads split the same way.
    normals, _ = grid_normals(grid, hint)
    last = len(grid[0]) - 1
    for cols in (SHROUD_DECAL_COLS, [last - j for j in reversed(SHROUD_DECAL_COLS)]):
        deco = [[grid[i][j] + normals[i][j] * 0.001 for j in cols] for i in SHROUD_DECAL_ROWS]
        shell(m, deco, "grey", thick=0.0, hint=hint, back=False, rim=False)


# =============================================================================== side panels
# Side-view outline of the left side panel (y, z): tall behind the head tube, tapering back
# under the seat with an angled lower edge, and the surface it is wrapped onto.

PANEL_TOP = [(-0.262, 0.806), (-0.230, 0.803), (-0.195, 0.801), (-0.150, 0.799), (-0.100, 0.802), (-0.050, 0.811),
             (0.000, 0.822), (0.040, 0.822), (0.100, 0.819), (0.200, 0.817)]
PANEL_BOT = [(-0.262, 0.655), (-0.228, 0.640), (0.185, 0.778), (0.205, 0.790)]
PANEL_OUTLINE = fillet2d([(-0.228, 0.640), (0.185, 0.778), (0.202, 0.806)] + PANEL_TOP[::-1],
                         [0.022, 0.030, 0.0, 0.008] + [0.0] * 8 + [0.014], step=28)
PANEL_XC = [(-0.265, 0.096), (-0.230, 0.103), (-0.200, 0.111), (-0.150, 0.123), (-0.100, 0.131), (-0.050, 0.137),
            (0.000, 0.140), (0.080, 0.142), (0.210, 0.142)]
# the top edge tucks in under the shroud / seat by this (less where the frame's top beams run just inside it)
PANEL_CURL = [(-0.265, 0.008), (-0.165, 0.009), (-0.050, 0.010), (0.020, 0.012), (0.100, 0.018), (0.210, 0.026)]
PANEL_ROWS = [0.0, 0.4, 0.75, 0.92, 1.0]  # bunched towards the tucked-in top edge


def panel_x(y, z):
    """Outer surface of the left side panel: flared out going back, crowned, top edge tucked in."""
    zt, zb = curve(PANEL_TOP, y), curve(PANEL_BOT, y)
    v = max(0.0, min(1.0, (z - zb) / max(zt - zb, 1e-3)))
    x = curve(PANEL_XC, y) + 0.007 * math.sin(math.pi * v) ** 0.8
    x -= curve(PANEL_CURL, y) * smoothstep(0.022, 0.0, zt - z) ** 1.3
    x -= 0.004 * smoothstep(0.016, 0.0, z - zb)
    return x


# raised flare on the upper part of the panel: its lower edge is a shape line running
# roughly parallel to the angled lower edge of the panel
FLARE_OUTLINE = fillet2d([(-0.244, 0.792), (-0.222, 0.682), (0.070, 0.771), (0.128, 0.787), (0.050, 0.796),
                          (-0.050, 0.797), (-0.150, 0.790)], [0.010, 0.016, 0.0, 0.006, 0.0, 0.0, 0.0], step=30)
STRIPE_OUTLINE = [(-0.206, 0.668), (0.080, 0.752), (0.128, 0.767), (0.080, 0.762), (-0.192, 0.682)]


def side_panels(m):
    """Large side panels (both sides) with a raised upper flare and a grey stripe decal."""
    grid = outline_grid(PANEL_OUTLINE, PANEL_ROWS, panel_x, max_gap=0.09, min_gap=0.06)
    shell(m, grid, "white", bevel=0.0025, mirror=True)
    flare = outline_grid(FLARE_OUTLINE, 2, lambda y, z: panel_x(y, z) + 0.0035, max_gap=0.1, min_gap=0.06)
    shell(m, flare, "white", inner=lift_grid(flare, panel_x, -0.002), back=False, mirror=True)
    stripe = outline_grid(STRIPE_OUTLINE, 1, lambda y, z: panel_x(y, z) + 0.0012, max_gap=0.12, min_gap=0.01)
    shell(m, stripe, "grey", thick=0.0, back=False, rim=False, mirror=True)


# =============================================================================== rear side panels
# Under the back of the seat, starting just behind the frame's rear-top corner and tapering
# into the side of the tail.

REAR_TOP = [(0.250, 0.813), (0.330, 0.815), (0.400, 0.823), (0.450, 0.832), (0.500, 0.842), (0.540, 0.848),
            (0.580, 0.853), (0.615, 0.857), (0.645, 0.858), (0.668, 0.852)]
REAR_BOT = [(0.255, 0.718), (0.440, 0.768), (0.590, 0.815), (0.668, 0.852)]
REAR_OUTLINE = fillet2d(REAR_BOT + REAR_TOP[::-1][1:], [0.014, 0.0, 0.0, 0.012] + [0.0] * 8 + [0.010], step=30)
REAR_XC = [(0.250, 0.122), (0.300, 0.121), (0.400, 0.116), (0.480, 0.110), (0.560, 0.103), (0.620, 0.097),
           (0.668, 0.092)]
REAR_ROWS = [0.0, 0.5, 0.85, 1.0]
REAR_DECAL = [(0.320, 0.775), (0.500, 0.809), (0.585, 0.832), (0.545, 0.834), (0.320, 0.792)]


def rear_x(y, z):
    """Outer surface of the left rear side panel."""
    zt, zb = curve(REAR_TOP, y), curve(REAR_BOT, y)
    v = max(0.0, min(1.0, (z - zb) / max(zt - zb, 1e-3)))
    x = curve(REAR_XC, y) + 0.005 * math.sin(math.pi * v) ** 0.8
    x -= 0.012 * smoothstep(0.022, 0.0, zt - z) ** 1.3
    x -= 0.003 * smoothstep(0.014, 0.0, z - zb)
    return x


def rear_side_panels(m):
    """Rear side panels under the back of the seat (both sides) with a grey decal."""
    grid = outline_grid(REAR_OUTLINE, REAR_ROWS, rear_x, max_gap=0.09, min_gap=0.06)
    shell(m, grid, "white", bevel=0.0025, mirror=True)
    decal = outline_grid(REAR_DECAL, 1, lambda y, z: rear_x(y, z) + 0.0012, max_gap=0.12, min_gap=0.01)
    shell(m, decal, "grey", thick=0.0, back=False, rim=False, mirror=True)


# =============================================================================== rear fender

# y, crown height (centre line), half width, skirt bottom height. It must stay wider than the
# subframe rails, which end under it at y = 0.64.
FENDER = [(0.420, 0.819, 0.086, 0.799), (0.465, 0.830, 0.087, 0.806), (0.520, 0.845, 0.088, 0.812),
          (0.565, 0.857, 0.087, 0.816), (0.605, 0.867, 0.085, 0.814), (0.635, 0.874, 0.080, 0.808),
          (0.655, 0.879, 0.072, 0.810), (0.670, 0.883, 0.060, 0.826), (0.681, 0.886, 0.045, 0.850),
          (S.TAIL_END.y, S.TAIL_END.z, 0.026, 0.872)]
FENDER_CROWN = 0.011  # the centre line stands this much above the shoulders


def fender_profile(zc, w, zsk):
    """Half cross-section of the fender (skirt edge -> centre): crowned top, rounded shoulder."""
    crown = min(FENDER_CROWN, 0.5 * (zc - zsk))
    ze = zc - crown  # shoulder height
    r = max(0.002, min(0.016, 0.45 * (ze - zsk), 0.4 * w))
    return [(w - 0.002, zsk), (w, zsk + 0.5 * (ze - r - zsk)), (w, ze - r), (w - 0.3 * r, ze - 0.3 * r),
            (w - r, ze), (0.5 * (w - r), zc - crown * 0.28), (0.0, zc)]


def rear_fender(m):
    """Long white rear fender from under the seat to the tail tip."""
    grid = []
    for y, zc, w, zsk in FENDER:
        half = fender_profile(zc, w, zsk)
        prof = half + [(-x, z) for (x, z) in reversed(half[:-1])]
        grid.append([Vector((x, y, z)) for (x, z) in prof])
    shell(m, grid, "white", hint=lambda p: Vector((p.x, 0.0, 1.0)), bevel=0.0025)


def tail_light(m):
    """Black tail-light unit filling the space under the fender tip, from the fender's underside
    down onto the subframe's end tabs (it is bolted to them), with the LED lens and a reflector."""
    c = Vector((0.0, 0.655, 0.834))
    m.box(BODY, (0.112, 0.036, 0.058), "black", matrix=tr(c), bevel=0.009, bevel_segments=1)
    # LED lens across the upper rear face (under the fender tip), slightly proud
    m.box(BODY, (0.070, 0.006, 0.016), "light_red", matrix=tr((0.0, c.y + 0.0185, c.z + 0.008)), bevel=0.0025,
          bevel_segments=1)
    # round red reflector below it
    m.cylinder(BODY, 0.0080, 0.004, "red", matrix=look((0.0, c.y + 0.019, c.z - 0.017), (0, 1, 0)), segments=12)


# =============================================================================== inner mudguard

GUARD_R = 0.518  # radius of its top skin about the rear axle: >= 0.20 m from the tyre


def rail(y):
    """Centre (x, z) of the left subframe rail at y (approximates chassis.subframe(); radius 0.0125)."""
    return curve([(0.33, (0.096, 0.780)), (0.52, (0.080, 0.790)), (0.64, (0.066, 0.796))], y)


def inner_mudguard(m):
    """Black splash guard under the fender: an arc concentric with the rear wheel, its side flanges
    standing on the subframe rails (it is screwed to them)."""
    ax = S.REAR_AXLE
    grid = []
    for y in (0.486, 0.515, 0.545, 0.575, 0.600, 0.620):  # between the subframe cross tubes
        z = ax.z + math.sqrt(GUARD_R ** 2 - (y - ax.y) ** 2)
        rx, rz = rail(y)
        w = rx - 0.005
        foot = rz + 0.0115  # on top of the rail
        half = [(w, min(foot, z - 0.008)), (w, z - 0.004), (w - 0.006, z), (0.0, z + 0.002)]
        grid.append([Vector((x, y, h)) for (x, h) in half + [(-x, h) for (x, h) in reversed(half[:-1])]])
    shell(m, grid, "black", thick=0.003, hint=lambda p: Vector((p.x, 0.0, 1.0)))


# =============================================================================== entry point


def build(m):
    seat(m)
    front_shroud(m)
    side_panels(m)
    rear_side_panels(m)
    rear_fender(m)
    tail_light(m)
    inner_mudguard(m)
