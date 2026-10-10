"""Shared measurements for the Sur-Ron Light Bee X build, in metres.

Every part module reads these so the parts fit together. Coordinates:
Z up, the bike faces -Y, ground at z = 0. The rider's LEFT side (chain and
front brake disc side) is +X, the RIGHT side (rear brake disc side) is -X.
Real-bike figures: wheelbase ~1260 mm, 19" wheels with 70/100-19 tyres,
seat ~880 mm, overall length ~1.9 m, ground clearance ~270 mm.
"""

import math

from mathutils import Vector

# -- wheels -------------------------------------------------------------------
WHEEL_RADIUS = 0.31  # tyre outer radius (knob tips)
RIM_RADIUS = 0.2413  # 19" bead seat
RIM_WIDTH = 0.036  # 1.40" rim
TYRE_WIDTH = 0.078
FRONT_AXLE = Vector((0.0, -0.63, 0.31))
REAR_AXLE = Vector((0.0, 0.63, 0.31))
FRONT_HUB_HALF_WIDTH = 0.05
REAR_HUB_HALF_WIDTH = 0.07
FRONT_DISC_X = 0.055  # left side
FRONT_DISC_RADIUS = 0.11
REAR_DISC_X = -0.075  # right side
REAR_DISC_RADIUS = 0.10
CHAIN_X = 0.085  # chain line, left side (rear sprocket and front sprocket centre planes)
REAR_SPROCKET_RADIUS = 0.115  # about 58T
FRONT_SPROCKET_RADIUS = 0.04

# -- steering and fork ----------------------------------------------------------
RAKE_DEG = 25.0
STEER_DIR = Vector((0.0, math.sin(math.radians(RAKE_DEG)), math.cos(math.radians(RAKE_DEG))))  # up and back
STEER_FWD = Vector((0.0, -math.cos(math.radians(RAKE_DEG)), math.sin(math.radians(RAKE_DEG))))  # square to it, forward
FORK_OFFSET = 0.03  # axle sits this far in front of the steering axis


def fork_point(t):
    """A point on the fork-leg axis plane (through the front axle), t metres up the leg from the axle."""
    return FRONT_AXLE + STEER_DIR * t


def steer_point(t):
    """A point on the steering axis, t metres up from level with the front axle."""
    return FRONT_AXLE - STEER_FWD * FORK_OFFSET + STEER_DIR * t


# Clamp heights fitted to the reference photo: top clamp ~0.97 m, bar ends ~1.06 m above the ground
# (the real bike is 1.04 m tall overall).
LOWER_CLAMP = steer_point(0.58)  # centre of the lower triple clamp on the steering axis
TOP_CLAMP = steer_point(0.74)
HEAD_TUBE = (steer_point(0.60), steer_point(0.72))  # frame head tube ends (frame part)
FORK_LEG_X = 0.085  # each fork leg centre at x = +-FORK_LEG_X, on the fork_point() line
FORK_OUTER_RADIUS = 0.027  # gold upper (outer) tube of the upside-down fork
FORK_INNER_RADIUS = 0.019  # chrome stanchion below it
FORK_SPLIT_T = 0.32  # gold outer tube covers t = FORK_SPLIT_T .. FORK_TOP_T, stanchion below
FORK_TOP_T = 0.77
FRONT_AXLE_IN_FORK = True  # front axle, head and nut are built in ForkLowers (they do not spin with the wheel)
FORK_TRAVEL = 0.06  # usable fork compression (ForkLowers sliding up STEER_DIR) before the guards reach the wipers
HANDLEBAR_CENTRE = TOP_CLAMP + Vector((0.0, 0.039, 0.045))  # low bar, just behind the fork caps
HANDLEBAR_HALF_WIDTH = 0.39
NUMBER_PLATE_CENTRE = LOWER_CLAMP + STEER_FWD * 0.10 + STEER_DIR * 0.03

# -- chassis -----------------------------------------------------------------------
SWINGARM_PIVOT = Vector((0.0, 0.15, 0.42))
SWINGARM_ARM_X = 0.115  # each swingarm arm centre at +-x (arm about 0.03 thick)
SHOCK_TOP = Vector((0.0, 0.21, 0.77))
SHOCK_BOTTOM = Vector((0.0, 0.31, 0.415))  # on the swingarm (eye clears the rear tyre)
MOTOR_CENTRE = Vector((0.0, -0.01, 0.37))  # motor axis runs along X
MOTOR_RADIUS = 0.09
MOTOR_HALF_WIDTH = 0.08
FRONT_SPROCKET = Vector((CHAIN_X, 0.12, 0.385))
BATTERY_CENTRE = Vector((0.0, -0.02, 0.63))
BATTERY_SIZE = Vector((0.19, 0.30, 0.34))  # x, y, z: sits inside the frame loop
FOOTPEG = Vector((0.20, 0.13, 0.30))  # left peg; right is mirrored
SEAT_FRONT = Vector((0.0, -0.12, 0.87))  # top surface of the seat nose (it stands clear of the shroud flanks)
SEAT_REAR = Vector((0.0, 0.52, 0.89))
SEAT_MAX_HALF_WIDTH = 0.12
TAIL_END = Vector((0.0, 0.69, 0.89))  # tip of the rear fender (just behind the rear axle, as in the photo)
# Left rear-subframe rail centre line (mirrored for the right rail), read by chassis.py (which builds the
# rails) and bodywork.py (whose inner mudguard stands on them). Its end rises to meet the fender's underside.
SUBFRAME_RAIL = [Vector((0.104, 0.180, 0.772)), Vector((0.096, 0.330, 0.780)), Vector((0.084, 0.470, 0.790)),
                 Vector((0.068, 0.565, 0.826))]
SUBFRAME_RAIL_R = 0.0125
SUBFRAME_CROSS_Y = (0.470, 0.548)  # cross tubes between the rails


def subframe_rail_at(y):
    """(x, z) of the left subframe rail centre line at y (straight between its control points)."""
    pts = SUBFRAME_RAIL
    for a, b in zip(pts, pts[1:]):
        if y <= b.y:
            f = max(0.0, (y - a.y) / (b.y - a.y))
            return a.x + (b.x - a.x) * f, a.z + (b.z - a.z) * f
    return pts[-1].x, pts[-1].z


# -- groups ------------------------------------------------------------------------
# Each group is one Roblox MeshPart; its origin is the pivot listed here.
PIVOTS = {
    "Body": Vector((0.0, 0.0, 0.0)),  # frame, battery, motor, bodywork, seat
    "Swingarm": SWINGARM_PIVOT,  # swingarm, chain, rear caliper (pivots about X)
    # rear shock in two halves, so the swingarm can move: aim each at the other's pivot every frame
    # (Shock turns about X at SHOCK_TOP; ShockRod rides on the swingarm and turns about X at SHOCK_BOTTOM)
    "Shock": SHOCK_TOP,  # shock body, top eye, preload collar, spring
    "ShockRod": SHOCK_BOTTOM,  # lower eye, rod end and spring seat, chrome shaft
    "Steering": LOWER_CLAMP,  # clamps, gold fork tubes, bars, number plate, front fender (turns about STEER_DIR)
    "ForkLowers": FRONT_AXLE,  # stanchions, axle lugs, fork guards, front caliper (slide along STEER_DIR)
    "FrontWheel": FRONT_AXLE,  # tyre, rim, spokes, hub, disc (spins about X)
    "RearWheel": REAR_AXLE,  # tyre, rim, spokes, hub, disc, sprocket (spins about X)
}
BUDGETS = {  # triangles per group mesh (the Roblox hard limit is 20,000 per mesh)
    "Body": 13500,
    "Swingarm": 4700,
    "Shock": 1100,
    "ShockRod": 400,
    "Steering": 8800,
    "ForkLowers": 3000,
    "FrontWheel": 6200,
    "RearWheel": 7000,
}  # these add up to 44,700, inside TOTAL_BUDGET
TOTAL_BUDGET = 45000

# -- materials (name, hex, metallic, roughness[, light]) ------------------------------
PALETTE_ENTRIES = [
    ("white", "eef0f2", 0.0, 0.32),  # bodywork plastics
    ("black", "1c1d20", 0.0, 0.45),  # black plastic: guards, covers, controls
    ("seat", "17171a", 0.0, 0.85),  # matte seat vinyl
    ("rubber", "141414", 0.0, 0.92),  # tyres, grips
    ("alu", "c3c7cc", 0.9, 0.32),  # frame, swingarm (raw aluminium)
    ("dark_alu", "4b5058", 0.85, 0.38),  # clamps, hubs, rims, motor caps
    ("gold", "9c7c4c", 1.0, 0.30),  # fork outer tubes (bronze gold, as in the photo)
    ("chrome", "e1e4e8", 1.0, 0.12),  # fork stanchions, shock shaft
    ("steel", "9ea3aa", 1.0, 0.35),  # discs, spokes, chain, bolts
    ("battery", "2a2c31", 0.3, 0.50),  # battery case, motor body
    ("red", "b3121a", 0.0, 0.35),  # reflectors, small accents
    ("grey", "7a7f87", 0.0, 0.50),  # trims, decal stripes
    ("light_white", "f4f8ff", 0.0, 0.10, True),  # headlight LEDs (Neon in Roblox)
    ("light_red", "ff2a2a", 0.0, 0.20, True),  # tail light (Neon in Roblox)
]
