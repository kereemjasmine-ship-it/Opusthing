"""Build the Sur-Ron Light Bee X (mid-poly, Roblox-ready) from its part modules.

    python build.py [--render] [--samples N] [--res PX] [--views hero,side,front,rear]
                    [--only chassis,wheels,...] [--no-export]

Parts live in parts/<name>.py and each defines build(m) that adds geometry to
the shared midpoly.Model `m` using the measurements in spec.py. A full build
writes SurRonLightBee.blend, export/SurRonLightBee.fbx/.glb plus the palette
maps, and (with --render) renders/<view>.png. With --only, nothing is
exported and renders are written as renders/<view>_<parts>.png.
"""

import importlib
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "lib"))
sys.path.insert(0, HERE)

import bpy  # noqa: E402,I001
import midpoly  # noqa: E402
import spec  # noqa: E402

NAME = "SurRonLightBee"
PARTS = ["chassis", "wheels", "front_end", "bodywork"]


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

    root, objects = model.finish(HERE)
    midpoly.report(objects, spec.BUDGETS)
    cams = midpoly.build_studio(objects)
    midpoly.setup_render(args["samples"], args["res"], int(args["res"] * 0.72))

    full = not args["only"] and not missing and not failed
    if full and not args["no_export"]:
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

    if failed:
        print("FAILED PARTS:", ", ".join(failed))
        sys.exit(1)


if __name__ == "__main__":
    main()
