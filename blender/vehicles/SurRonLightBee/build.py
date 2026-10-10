"""Build the Sur-Ron Light Bee X (mid-poly, Roblox-ready) from its part modules.

    python build.py [--render] [--samples N] [--res PX] [--views hero,side,front,rear]
                    [--only chassis,wheels,...] [--no-export]

Parts live in parts/<name>.py and each defines build(m) that adds geometry to
the shared midpoly.Model `m` using the measurements in spec.py. A full build
writes SurRonLightBee.blend, export/SurRonLightBee.fbx/.glb plus the palette
maps, and (with --render) renders/<view>.png. With --only or --no-export,
nothing in the project is rewritten except the renders (with --only they are
written as renders/<view>_<parts>.png).
"""

import importlib
import os
import shutil
import sys
import tempfile
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "lib"))
sys.path.insert(0, HERE)

import bpy  # noqa: E402,I001
import midpoly  # noqa: E402
import spec  # noqa: E402

NAME = "SurRonLightBee"
PARTS = ["chassis", "wheels", "front_end", "bodywork"]


def fix_palette_maps(out_dir):
    """Refill the Metalness, Roughness and Emission palette maps, then save and re-pack them.

    midpoly.Model._palette_images() writes the pixels first and then switches the image to
    Non-Color, which makes Blender regenerate the image blank (all three maps came out black:
    every surface non-metal with roughness 0, no light emission). midpoly.py is shared and is
    not edited here, so the maps are rewritten after Model.finish(); the colour space is
    already Non-Color, so the pixels now stick. The material nodes use these same images.
    """
    entries = midpoly.Palette(spec.PALETTE_ENTRIES).entries
    for kind in ("Metalness", "Roughness", "Emission"):
        img = bpy.data.images[f"{NAME}_{kind}"]
        if img.packed_file:  # drop the blank packed copy (pack() would otherwise keep it)
            img.unpack(method="REMOVE")
        if img.colorspace_settings.name != "Non-Color":
            img.colorspace_settings.name = "Non-Color"
        w, h = img.size
        px = [0.0] * (w * h * 4)
        for slot, (_, hx, metal, rough, light) in enumerate(entries):
            r, g, b = midpoly.hex_rgb(hx)
            val = {"Metalness": (metal,) * 3, "Roughness": (rough,) * 3,
                   "Emission": (r, g, b) if light else (0.0, 0.0, 0.0)}[kind]
            for y in range(h):
                for x in range(slot * midpoly.CELL, (slot + 1) * midpoly.CELL):
                    i = (y * w + x) * 4
                    px[i : i + 4] = (*val, 1.0)
        for i in range(slot + 1, w // midpoly.CELL):  # unused slots stay black, alpha 1
            for y in range(h):
                for x in range(i * midpoly.CELL, (i + 1) * midpoly.CELL):
                    px[(y * w + x) * 4 + 3] = 1.0
        img.pixels = px
        img.update()
        path = os.path.join(out_dir, "export", f"{NAME}_{kind}.png")
        img.filepath_raw = path
        img.file_format = "PNG"
        img.save()
        img.pack()  # packs the file just written (the .blend, FBX and GLB use the packed copy)
        if img.packed_file is None or img.packed_file.size != os.path.getsize(path):
            raise RuntimeError(f"{kind} palette map did not re-pack")
    # guard: the maps must carry the palette's values (a black Metalness map means the bug is back)
    for kind, want in (("Metalness", max(e[2] for e in entries)), ("Roughness", max(e[3] for e in entries))):
        got = max(bpy.data.images[f"{NAME}_{kind}"].pixels[:][0::4])
        if abs(got - want) > 0.01:
            raise RuntimeError(f"{kind} palette map is wrong (max {got:.3f}, expected {want:.3f})")


def main():
    args = midpoly.parse_args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    model = midpoly.Model(NAME, midpoly.Palette(spec.PALETTE_ENTRIES))
    for group, pivot in spec.PIVOTS.items():
        model.group(group, pivot)

    parts = args["only"] or PARTS
    failed, missing = [], []
    for part in parts:
        if not os.path.exists(os.path.join(HERE, "parts", f"{part}.py")):
            missing.append(part)
            continue
        try:
            importlib.import_module(f"parts.{part}").build(model)
        except Exception:
            traceback.print_exc()
            failed.append(part)
    if missing:
        print("not built yet:", ", ".join(missing))

    full = not args["only"] and not missing and not failed
    write = full and not args["no_export"]
    # palette maps go to export/ only on a full export; test builds write them to a temporary folder
    out_dir = HERE if write else tempfile.mkdtemp(prefix=f"{NAME}_")
    root, objects = model.finish(out_dir)
    fix_palette_maps(out_dir)
    midpoly.report(objects, spec.BUDGETS)
    cams = midpoly.build_studio(objects)
    midpoly.setup_render(args["samples"], args["res"], int(args["res"] * 0.72))

    if write:
        midpoly.export(NAME, root, objects, HERE)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, f"{NAME}.blend"), compress=True)

    if args["render"]:
        out = os.path.join(HERE, "renders")
        os.makedirs(out, exist_ok=True)
        suffix = "" if not args["only"] else "_" + "-".join(args["only"])
        scene = bpy.context.scene
        for view in args["views"]:
            scene.camera = cams["Cam" + view.capitalize()]
            scene.render.filepath = os.path.join(out, f"{view}{suffix}.png")
            bpy.ops.render.render(write_still=True)
            print("rendered", scene.render.filepath)

    if not write:
        shutil.rmtree(out_dir, ignore_errors=True)
    if failed:
        print("FAILED PARTS:", ", ".join(failed))
        sys.exit(1)


if __name__ == "__main__":
    main()
