"""STARDW asset generator.

Run with the repo's virtualenv python:

    python3 tools/gen_assets.py

It draws every texture used by the game into assets/ and writes assets/manifest.json,
which the engine reads at boot to build AtlasTextures. Nothing here is downloaded:
tiles, props, characters, fish, items, UI and effects are all painted procedurally.
"""

import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image  # noqa: E402

import gen_chars  # noqa: E402
import gen_fish  # noqa: E402
import gen_fx  # noqa: E402
import gen_items  # noqa: E402
import gen_objects  # noqa: E402
import gen_tiles  # noqa: E402
import gen_ui  # noqa: E402
from pixlib import Atlas  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "assets"))

ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">
  <rect width="128" height="128" rx="18" fill="#24384a"/>
  <path d="M0 78 Q32 66 64 78 T128 78 V128 H0 Z" fill="#2f6f9e"/>
  <path d="M0 90 Q32 80 64 90 T128 90 V128 H0 Z" fill="#255a83"/>
  <circle cx="90" cy="30" r="14" fill="#ffd873"/>
  <ellipse cx="56" cy="66" rx="26" ry="15" fill="#7fc2dd"/>
  <path d="M30 66 L14 54 L14 78 Z" fill="#7fc2dd"/>
  <circle cx="70" cy="62" r="3.5" fill="#1b2430"/>
  <path d="M92 84 q10 14 -4 22 q-10 6 -14 -4" fill="none" stroke="#e8e8e0" stroke-width="4"/>
</svg>
"""


def main():
    rng = random.Random(20260930)
    os.makedirs(OUT, exist_ok=True)

    manifest = {"version": 1, "atlases": {}, "anims": {}}

    # --- terrain tiles (strict grid, consumed by a TileSetAtlasSource) ---- #
    tiles_info = gen_tiles.build(os.path.join(OUT, "tiles.png"), seed=1234)
    tiles_info["tile_size"] = [gen_tiles.TILE_W, gen_tiles.TILE_H]
    tiles_info["cols"] = gen_tiles.COLS
    manifest["atlases"]["tiles"] = tiles_info

    # --- free packed atlases --------------------------------------------- #
    plan = [
        ("objects", 1024, gen_objects.build),
        ("chars", 1024, gen_chars.build),
        ("fish", 1024, gen_fish.build),
        ("items", 512, gen_items.build),
        ("ui", 512, gen_ui.build),
        ("fx", 512, gen_fx.build),
    ]
    for name, width, fn in plan:
        atlas = Atlas(name, width=width, pad=2)
        extra = fn(atlas, rng)
        info = atlas.save(os.path.join(OUT, name + ".png"))
        manifest["atlases"][name] = info
        if isinstance(extra, dict):
            for anim_key, anim_val in extra.items():
                anim_val = dict(anim_val)
                anim_val["atlas"] = name
                manifest["anims"][anim_key] = anim_val
        print("%-8s %4dx%-4d  %3d regions" % (name, info["size"][0], info["size"][1], len(info["regions"])))

    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)

    # --- project icon ----------------------------------------------------- #
    with open(os.path.join(OUT, "..", "icon.svg"), "w", encoding="utf-8") as fh:
        fh.write(ICON_SVG)

    # --- sanity: report total pixels and file sizes ---------------------- #
    total = 0
    for f in sorted(os.listdir(OUT)):
        p = os.path.join(OUT, f)
        if f.endswith(".png"):
            with Image.open(p) as im:
                total += im.width * im.height
            print("  %-16s %6.1f KB" % (f, os.path.getsize(p) / 1024.0))
    print("total texture pixels: %d" % total)
    print("manifest: assets/manifest.json")


if __name__ == "__main__":
    main()
