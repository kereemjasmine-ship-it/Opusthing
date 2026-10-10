"""Render every void pet side by side, smallest to largest, to check they read as one family.

Run after the pets are built:  python render_lineup.py [--samples N] [--res PX]
Writes blender/pets/lineup.png.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))

import bpy  # noqa: E402,I001
from mathutils import Vector  # noqa: E402

import blocky  # noqa: E402

# Rarity order, common first. The hydra lives one folder up.
PETS = [
    ("VoidPup", os.path.join(HERE, "VoidPup", "VoidPup.blend")),
    ("ShadowBat", os.path.join(HERE, "ShadowBat", "ShadowBat.blend")),
    ("CrystalFox", os.path.join(HERE, "CrystalFox", "CrystalFox.blend")),
    ("NebulaOwl", os.path.join(HERE, "NebulaOwl", "NebulaOwl.blend")),
    ("RuneGolem", os.path.join(HERE, "RuneGolem", "RuneGolem.blend")),
    ("VoidHydra", os.path.join(HERE, "..", "VoidHydra.blend")),
]
GAP = 0.8  # studs between pets


def load_pet(name, path):
    """Append the pet's own collection (not its stage) from its .blend."""
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.collections = [c for c in src.collections if c == name]
    coll = dst.collections[0]
    bpy.context.scene.collection.children.link(coll)
    root = next(ob for ob in coll.objects if ob.parent is None)
    meshes = [ob for ob in coll.objects if ob.type == "MESH"]
    return root, meshes


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    samples = int(argv[argv.index("--samples") + 1]) if "--samples" in argv else 48
    res = int(argv[argv.index("--res") + 1]) if "--res" in argv else 1600

    bpy.ops.wm.read_factory_settings(use_empty=True)
    x = 0.0
    everything = []
    for name, path in PETS:
        if not os.path.exists(path):
            print("missing", path)
            continue
        root, meshes = load_pet(name, path)
        bpy.context.view_layer.update()
        lo, hi = blocky.bounds(meshes)
        width = hi.x - lo.x
        root.location = Vector((x - lo.x, -(lo.y + hi.y) / 2, 0))
        x += width + GAP
        everything += meshes
    bpy.context.view_layer.update()

    # centre the row on the origin
    lo, hi = blocky.bounds(everything)
    shift = -(lo.x + hi.x) / 2
    for ob in bpy.context.scene.objects:
        if ob.parent is None:
            ob.location.x += shift
    bpy.context.view_layer.update()

    cams = blocky.build_stage(everything)
    blocky.setup_render(samples, res)
    scene = bpy.context.scene
    scene.render.resolution_y = int(res * 0.45)
    cam = cams["CamFront"]
    lo, hi = blocky.bounds(everything)
    centre = (lo + hi) / 2
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = (hi.x - lo.x) * 1.08
    cam.location = centre + Vector((0, -40, 6))
    cam.rotation_euler = (centre - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    scene.render.filepath = os.path.join(HERE, "lineup.png")
    bpy.ops.render.render(write_still=True)
    print("rendered", scene.render.filepath)


if __name__ == "__main__":
    main()
