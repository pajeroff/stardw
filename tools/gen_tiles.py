"""Terrain tiles: a strict 8x4 grid of 64x32 isometric diamonds."""

import random

from PIL import Image

from pixlib import (
    Art,
    darken,
    iso_diamond,
    lighten,
    mix,
    rgb,
    shade,
    with_alpha,
)

TILE_W, TILE_H = 64, 32
COLS, ROWS = 8, 4

# name -> painter key (order defines the atlas grid, left->right, top->bottom)
TILE_ORDER = [
    "grass_a", "grass_b", "grass_c", "grass_dark", "grass_flower_a", "grass_flower_b", "moss", "leaf_floor",
    "dirt_a", "dirt_b", "mud", "path", "sand", "sand_wet", "gravel", "stone_paved",
    "water_shallow", "water_mid", "water_deep", "water_river", "deck", "deck_wet", "bridge", "snow_a",
    "snow_b", "snow_grass", "ice", "cliff",
]

PAL = {
    "grass": [(96, 158, 74), (86, 145, 66), (108, 172, 84), (76, 132, 58), (120, 182, 92)],
    "grass_dark": [(58, 108, 50), (50, 96, 44), (68, 122, 58), (44, 88, 40)],
    "dirt": [(150, 108, 68), (132, 94, 58), (166, 124, 82), (118, 82, 50)],
    "mud": [(104, 78, 54), (92, 68, 46), (118, 90, 62)],
    "path": [(190, 168, 126), (174, 152, 112), (204, 184, 142), (160, 138, 100)],
    "sand": [(228, 206, 150), (212, 188, 132), (240, 222, 172), (196, 172, 118)],
    "water": [(70, 142, 190), (56, 122, 172), (92, 168, 208), (44, 104, 156), (110, 186, 220)],
    "deep": [(32, 84, 138), (24, 70, 120), (44, 100, 156)],
    "wood": [(154, 110, 68), (134, 92, 56), (174, 130, 86), (118, 80, 48)],
    "stone": [(146, 148, 156), (124, 126, 134), (168, 170, 178), (108, 110, 118)],
    "snow": [(240, 246, 252), (222, 234, 246), (250, 253, 255)],
    "ice": [(176, 214, 232), (196, 228, 242), (150, 196, 220), (214, 238, 248)],
}


def _pal(name):
    return [rgb(*c) for c in PAL[name]]


class TileArt(Art):
    """64x32 canvas that knows about the inscribed diamond."""

    def __init__(self):
        super().__init__(TILE_W, TILE_H, ss=2)
        self.cx, self.cy = TILE_W / 2.0, TILE_H / 2.0

    def inside(self, x, y, inset=0.0):
        hw = TILE_W / 2.0 - inset
        hh = TILE_H / 2.0 - inset
        return abs(x - self.cx) / hw + abs(y - self.cy) / hh <= 1.0

    def dpx(self, x, y, col, inset=0.0):
        if self.inside(x + 0.5, y + 0.5, inset):
            self.px(x, y, col)

    def diamond(self, fill, outline=None):
        iso_diamond(self, self.cx, self.cy, TILE_W, TILE_H, fill, outline=outline)


def _noise(art, cols, count, rng, inset=1.0, chance=None):
    for _ in range(count):
        x = rng.randint(0, TILE_W - 1)
        y = rng.randint(0, TILE_H - 1)
        if chance is not None and rng.random() > chance:
            continue
        art.dpx(x, y, rng.choice(cols), inset=inset)


def _grass_blades(art, cols, rng, count=26):
    for _ in range(count):
        x = rng.randint(2, TILE_W - 3)
        y = rng.randint(4, TILE_H - 5)
        c = rng.choice(cols)
        art.dpx(x, y, c)
        if rng.random() < 0.55:
            art.dpx(x, y - 1, lighten(c, 0.18))


def _wave_lines(art, rng, col_hi, col_lo, rows=3, amp=1.0):
    for i in range(rows):
        y = 7 + i * 8 + rng.randint(-1, 1)
        phase = rng.uniform(0, 6.28)
        for x in range(0, TILE_W, 2):
            yy = y + int(round(amp * math.sin(x / 6.0 + phase)))
            art.dpx(x, yy, col_hi, inset=2.0)
            art.dpx(x + 1, yy, col_hi, inset=2.0)
            if rng.random() < 0.4:
                art.dpx(x, yy + 1, col_lo, inset=2.0)


import math  # noqa: E402  (used by _wave_lines)


def _paint(name, rng):
    art = TileArt()
    p = PAL

    if name in ("grass_a", "grass_b", "grass_c"):
        cols = _pal("grass")
        art.diamond(cols[1])
        _noise(art, cols, 190, rng, inset=1.0)
        _grass_blades(art, [cols[2], cols[4], cols[0]], rng, 30)
        if name == "grass_b":
            _noise(art, [cols[0], cols[3]], 130, rng, inset=2.0)
        if name == "grass_c":
            _noise(art, [cols[2], cols[4]], 150, rng, inset=2.0)
            _grass_blades(art, [cols[4]], rng, 22)
        # soft rim light on the two upper edges
        for i in range(TILE_W // 2):
            art.px(TILE_W // 2 - i, TILE_H // 2 - i // 2, lighten(cols[1], 0.20))
            art.px(TILE_W // 2 + i, TILE_H // 2 - i // 2, lighten(cols[1], 0.12))

    elif name == "grass_dark":
        cols = _pal("grass_dark")
        art.diamond(cols[0])
        _noise(art, cols, 200, rng, inset=1.0)
        _grass_blades(art, [cols[2], cols[1]], rng, 18)

    elif name in ("grass_flower_a", "grass_flower_b"):
        cols = _pal("grass")
        art.diamond(cols[1])
        _noise(art, cols, 180, rng)
        _grass_blades(art, [cols[2], cols[4]], rng, 24)
        flowers = [(240, 214, 90), (236, 128, 158), (236, 236, 240), (168, 132, 226)]
        if name == "grass_flower_b":
            flowers = [(236, 128, 158), (236, 236, 240), (126, 190, 236)]
        for _ in range(5):
            x = rng.randint(8, TILE_W - 9)
            y = rng.randint(6, TILE_H - 8)
            c = rgb(*rng.choice(flowers))
            if art.inside(x, y, 4):
                art.px(x, y, c)
                art.px(x + 1, y, rgb(250, 226, 120))
                art.px(x, y + 1, darken(c, 0.25))

    elif name == "moss":
        cols = _pal("grass_dark")
        stone = _pal("stone")
        art.diamond(stone[1])
        _noise(art, stone, 140, rng)
        for _ in range(6):
            x = rng.randint(6, TILE_W - 12)
            y = rng.randint(5, TILE_H - 9)
            if art.inside(x, y, 5):
                for dx in range(6):
                    for dy in range(4):
                        if rng.random() < 0.6:
                            art.dpx(x + dx, y + dy, rng.choice(cols), inset=2.0)

    elif name == "leaf_floor":
        cols = _pal("grass_dark")
        art.diamond(cols[1])
        _noise(art, cols, 170, rng)
        leaves = [(176, 108, 52), (196, 132, 58), (146, 86, 44), (206, 164, 72)]
        for _ in range(10):
            x = rng.randint(6, TILE_W - 9)
            y = rng.randint(5, TILE_H - 8)
            c = rgb(*rng.choice(leaves))
            if art.inside(x, y, 3):
                art.px(x, y, c)
                art.px(x + 1, y, lighten(c, 0.2))
                art.px(x - 1, y + 1, darken(c, 0.2))

    elif name in ("dirt_a", "dirt_b"):
        cols = _pal("dirt")
        art.diamond(cols[0])
        _noise(art, cols, 200, rng)
        if name == "dirt_b":
            _noise(art, [cols[3], cols[1]], 120, rng)
            for _ in range(4):
                x = rng.randint(8, TILE_W - 10)
                y = rng.randint(6, TILE_H - 8)
                art.dpx(x, y, cols[3])
                art.dpx(x + 1, y, cols[3])

    elif name == "mud":
        cols = _pal("mud")
        art.diamond(cols[0])
        _noise(art, cols, 210, rng)
        for _ in range(3):
            x = rng.randint(10, TILE_W - 14)
            y = rng.randint(8, TILE_H - 10)
            art.ellipse(x, y, x + 8, y + 3, with_alpha(rgb(70, 52, 36), 120))

    elif name == "path":
        cols = _pal("path")
        art.diamond(cols[0])
        _noise(art, cols, 200, rng)
        for _ in range(6):
            x = rng.randint(6, TILE_W - 10)
            y = rng.randint(5, TILE_H - 8)
            if art.inside(x, y, 4):
                art.ellipse(x, y, x + 3, y + 2, rng.choice(cols[2:]))

    elif name in ("sand", "sand_wet"):
        cols = _pal("sand")
        base = cols[0] if name == "sand" else mix(cols[0], rgb(120, 110, 90), 0.35)
        art.diamond(base)
        _noise(art, [mix(c, base, 0.35) for c in cols], 210, rng)
        if name == "sand_wet":
            _wave_lines(art, rng, lighten(base, 0.22), darken(base, 0.12), rows=2, amp=0.8)
        else:
            for _ in range(4):
                x = rng.randint(8, TILE_W - 12)
                y = rng.randint(6, TILE_H - 9)
                art.dpx(x, y, cols[3])

    elif name in ("gravel",):
        cols = _pal("path")
        art.diamond(mix(cols[0], rgb(120, 120, 124), 0.4))
        _noise(art, _pal("stone") + cols, 230, rng)

    elif name == "stone_paved":
        cols = _pal("stone")
        art.diamond(cols[1])
        # paving slabs: 4 diamonds inside the tile
        for (ox, oy) in ((0, -8), (16, 0), (0, 8), (-16, 0)):
            iso_diamond(art, art.cx + ox, art.cy + oy, 30, 15, rng.choice(cols))
            iso_diamond(art, art.cx + ox, art.cy + oy, 30, 15, None, outline=darken(cols[3], 0.15))
        _noise(art, cols, 90, rng, inset=1.0)

    elif name in ("water_shallow", "water_mid", "water_deep", "water_river"):
        base = {
            "water_shallow": rgb(*PAL["water"][0]),
            "water_mid": rgb(*PAL["water"][1]),
            "water_deep": rgb(*PAL["deep"][0]),
            "water_river": rgb(*PAL["water"][2]),
        }[name]
        art.diamond(base)
        grad = Image.new("RGBA", (TILE_W, TILE_H), (0, 0, 0, 0))
        for y in range(TILE_H):
            t = y / float(TILE_H - 1)
            c = mix(lighten(base, 0.16), darken(base, 0.22), t)
            for x in range(TILE_W):
                if art.inside(x + 0.5, y + 0.5):
                    grad.putpixel((x, y), c)
        grad_big = grad.resize((TILE_W * art.ss, TILE_H * art.ss), Image.NEAREST)
        art.img.paste(grad_big, (0, 0), grad_big)
        hi = lighten(base, 0.45)
        lo = darken(base, 0.18)
        _wave_lines(art, rng, hi, lo, rows=3 if name != "water_deep" else 2, amp=1.0)
        for _ in range(6):
            x = rng.randint(6, TILE_W - 8)
            y = rng.randint(6, TILE_H - 8)
            if art.inside(x, y, 3):
                art.px(x, y, lighten(base, 0.28))

    elif name in ("deck", "deck_wet", "bridge"):
        cols = _pal("wood")
        base = cols[0] if name != "deck_wet" else mix(cols[0], rgb(70, 90, 110), 0.3)
        art.diamond(base)
        # planks run along one iso axis
        for i in range(-4, 5):
            y0 = art.cy + i * 4
            for x in range(TILE_W):
                y = int(round(y0 - (x - art.cx) * 0.5))
                if 0 <= y < TILE_H:
                    art.dpx(x, y, darken(base, 0.35), inset=1.0)
        _noise(art, [cols[2], cols[1]], 70, rng, inset=2.0)
        if name == "bridge":
            for x in range(TILE_W):
                art.dpx(x, int(round(art.cy - (x - art.cx) * 0.5 - 1)), cols[3], inset=1.0)
                art.dpx(x, int(round(art.cy - (x - art.cx) * 0.5 + 1)), cols[3], inset=1.0)

    elif name in ("snow_a", "snow_b", "snow_grass"):
        cols = _pal("snow")
        art.diamond(cols[0])
        _noise(art, cols, 180, rng)
        if name == "snow_grass":
            gc = _pal("grass")
            for _ in range(40):
                x = rng.randint(4, TILE_W - 5)
                y = rng.randint(4, TILE_H - 5)
                if rng.random() < 0.6:
                    art.dpx(x, y, rng.choice(gc), inset=2.0)
        else:
            for _ in range(3):
                x = rng.randint(10, TILE_W - 14)
                y = rng.randint(8, TILE_H - 10)
                art.ellipse(x, y, x + 6, y + 2, cols[1])

    elif name == "ice":
        cols = _pal("ice")
        art.diamond(cols[0])
        _noise(art, cols, 150, rng)
        for _ in range(4):
            x0 = rng.randint(8, TILE_W - 16)
            y0 = rng.randint(6, TILE_H - 10)
            art.line([(x0, y0), (x0 + rng.randint(4, 12), y0 + rng.randint(-2, 3))], cols[3], 1)
        for i in range(TILE_W // 2):
            art.px(TILE_W // 2 - i, TILE_H // 2 - i // 2, lighten(cols[3], 0.25))

    elif name == "cliff":
        cols = _pal("stone")
        art.diamond(cols[2])
        _noise(art, cols, 190, rng)
        for _ in range(5):
            x = rng.randint(6, TILE_W - 10)
            y = rng.randint(6, TILE_H - 9)
            if art.inside(x, y, 3):
                art.poly([(x, y), (x + 4, y + 1), (x + 2, y + 3), (x - 1, y + 2)], cols[3])

    return art.reduce(palette=None, threshold=90)


def build(path, seed=1234):
    """Render tiles.png as a strict grid and return the region table."""
    rng = random.Random(seed)
    grid = Image.new("RGBA", (COLS * TILE_W, ROWS * TILE_H), (0, 0, 0, 0))
    regions = {}
    for i, name in enumerate(TILE_ORDER):
        cx, cy = (i % COLS) * TILE_W, (i // COLS) * TILE_H
        grid.paste(_paint(name, rng), (cx, cy))
        regions[name] = [cx, cy, TILE_W, TILE_H]
    grid.save(path)
    return {"file": "tiles.png", "size": [grid.width, grid.height], "regions": regions}
