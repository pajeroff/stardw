"""Renders a sample isometric scene + gallery page into docs/preview/.

Uses the same 2:1 iso math as scripts/world/iso.gd so the preview mirrors the
engine's layout. Run:  python3 tools/render_preview.py
"""

import json
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
ASSETS = os.path.join(ROOT, "assets")
OUT = os.path.join(ROOT, "docs", "preview")

TILE_W, TILE_H = 64, 32


def cell_to_local(x, y):
    return ((x - y) * TILE_W // 2, (x + y) * TILE_H // 2)


def main():
    os.makedirs(OUT, exist_ok=True)
    m = json.load(open(os.path.join(ASSETS, "manifest.json"), encoding="utf-8"))
    imgs = {at: Image.open(os.path.join(ASSETS, m["atlases"][at]["file"])).convert("RGBA")
            for at in m["atlases"]}

    def crop(at, name):
        x, y, w, h = m["atlases"][at]["regions"][name][:4]
        return imgs[at].crop((x, y, x + w, y + h))

    W, H = 960, 560
    canvas = Image.new("RGBA", (W, H), (24, 32, 46, 255))
    OX, OY = W // 2 - 160, 60

    GW, GH = 11, 9
    # ground
    for s in range(0, GW + GH):
        for x in range(GW):
            y = s - x
            if 0 <= y < GH:
                px, py = cell_to_local(x, y)
                t = "water_mid" if x >= GW - 3 else ("sand" if x == GW - 4 else "grass_a")
                if (x + y) % 5 == 0 and t == "grass_a":
                    t = "grass_b"
                canvas.alpha_composite(crop("tiles", t), (OX + px, OY + py))

    def put(at, name, cell, lift=0):
        im = crop(at, name)
        px, py = cell_to_local(*cell)
        canvas.alpha_composite(im, (OX + px - im.width // 2, OY + py + 24 - im.height - lift))

    # props (back to front)
    put("objects", "tree_oak_big", (1, 1))
    put("objects", "tree_pine", (2, 0))
    put("objects", "house", (0, 3), lift=10)
    put("objects", "rock_big", (4, 2))
    put("objects", "tree_autumn", (3, 4))
    put("objects", "quest_board", (5, 3))
    put("objects", "campfire_1", (6, 4))
    put("objects", "reeds", (GW - 4, 2))
    put("objects", "lily_flower", (GW - 2, 3))
    put("chars", "char_down_hold_0", (5, 5), lift=0)
    put("objects", "tree_oak", (7, 6))

    canvas.convert("RGB").save(os.path.join(OUT, "scene.png"))

    # gallery page
    sections = []
    for at in ["tiles", "objects", "chars", "fish", "items", "ui", "fx"]:
        sections.append("<h2>%s.png</h2><img src='%s.png' style='image-rendering:pixelated;max-width:100%%;background:#20242e;border:1px solid #333'>" % (at, at))
        # copy png
        Image.open(os.path.join(ASSETS, m["atlases"][at]["file"])).save(os.path.join(OUT, at + ".png"))
    html = """<!DOCTYPE html><html><head><meta charset='utf-8'><title>STARDW art preview</title>
<style>body{background:#171b24;color:#dfe7f2;font-family:monospace;margin:24px}h1{color:#7fd0ff}h2{color:#ffd873;margin-top:28px}img{image-rendering:pixelated}</style>
</head><body>
<h1>STARDW — рыбалка в изометрии (Godot 4.7)</h1>
<p>Вся графика и звук сгенерированы процедурно (tools/gen_assets.py, tools/gen_audio.py).</p>
<h2>Пример изометрической сцены</h2><img src='scene.png' style='image-rendering:pixelated;border:1px solid #333'>
%s
<p>Анимации: walk/idle/cast/hold/reel x4 направления, костёр, всплески, рябь, листья, птицы, светлячки.</p>
</body></html>""" % "\n".join(sections)
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(html)
    print("preview written to", OUT)


if __name__ == "__main__":
    main()
