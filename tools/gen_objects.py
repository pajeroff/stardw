"""Props, plants, buildings and the campfire animation frames."""

import math
import random

from PIL import Image

from pixlib import Art, darken, lighten, mix, outline_image, rgb, shade, with_alpha

DARK = rgb(30, 26, 34)

WOOD = [rgb(154, 110, 68), rgb(134, 92, 56), rgb(174, 130, 86), rgb(110, 74, 44)]
STONE = [rgb(146, 148, 156), rgb(120, 122, 130), rgb(170, 172, 180), rgb(98, 100, 108)]
LEAF = [rgb(70, 132, 56), rgb(86, 152, 66), rgb(56, 112, 46), rgb(104, 170, 78)]
AUTUMN = [rgb(206, 120, 48), rgb(226, 156, 58), rgb(176, 92, 40), rgb(240, 186, 84)]
SNOW = [rgb(238, 245, 252), rgb(216, 230, 244), rgb(250, 253, 255)]


# --------------------------------------------------------------------------- #
# trees
# --------------------------------------------------------------------------- #
def _canopy(art, cx, cy, rx, ry, cols, rng, blobs=16, jag=0.5):
    for _ in range(blobs):
        a = rng.uniform(0, math.tau)
        rr = rng.uniform(0.2, 1.0) ** jag
        x = cx + math.cos(a) * rx * rr
        y = cy + math.sin(a) * ry * rr * 0.85
        r = rng.uniform(rx * 0.30, rx * 0.55)
        art.ellipse(x - r, y - r * 0.8, x + r, y + r * 0.8, rng.choice(cols))
    # top-light
    for _ in range(max(4, blobs // 3)):
        a = rng.uniform(math.pi * 1.1, math.pi * 1.9)
        x = cx + math.cos(a) * rx * 0.6
        y = cy + math.sin(a) * ry * 0.6
        r = rng.uniform(rx * 0.14, rx * 0.28)
        art.ellipse(x - r, y - r * 0.8, x + r, y + r * 0.8, lighten(cols[-1], 0.12))


def tree(w, h, cols, trunk_cols, rng, kind="oak", snow=False, blossoms=None):
    art = Art(w, h, ss=2)
    cx = w / 2.0
    # shadow
    art.ellipse(cx - w * 0.30, h - 8, cx + w * 0.30, h - 1, with_alpha(rgb(20, 40, 20), 70))
    # trunk
    tw = max(4, w // 10)
    ty0 = h * 0.46
    art.poly([(cx - tw, h - 6), (cx - tw * 0.6, ty0), (cx + tw * 0.6, ty0), (cx + tw, h - 6)], trunk_cols[1])
    art.line([(cx - tw * 0.2, h - 6), (cx - tw * 0.1, ty0 + 2)], trunk_cols[2], 1)
    art.px(int(cx + tw * 0.3), int(h - 9), trunk_cols[3])
    # roots
    art.line([(cx - tw - 2, h - 6), (cx - tw + 1, h - 9)], trunk_cols[3], 2)
    art.line([(cx + tw + 2, h - 6), (cx + tw - 1, h - 9)], trunk_cols[3], 2)

    if kind == "bare":
        # winter: bare branches + snow caps
        for i in range(6):
            a = -math.pi / 2 + rng.uniform(-1.1, 1.1)
            ln = rng.uniform(h * 0.20, h * 0.34)
            x0, y0 = cx + rng.uniform(-3, 3), ty0 + rng.uniform(-4, 6)
            x1, y1 = x0 + math.cos(a) * ln, y0 + math.sin(a) * ln
            art.line([(x0, y0), (x1, y1)], trunk_cols[2], 2)
            art.line([(x1, y1), (x1 + rng.uniform(-6, 6), y1 - rng.uniform(2, 8))], trunk_cols[2], 1)
            if snow:
                art.line([(x0 - 1, y0 - 1), (x1, y1 - 1)], SNOW[0], 1)
        return art.reduce(threshold=90)

    rx, ry = w * 0.46, h * 0.34
    cy = h * 0.34
    _canopy(art, cx, cy, rx, ry, cols, rng, blobs=22)
    if kind == "pine":
        # stacked triangles
        for i in range(4):
            yy = h * 0.62 - i * h * 0.15
            ww = w * (0.44 - i * 0.075)
            hh = h * 0.22
            c = cols[(i + 1) % len(cols)]
            art.poly([(cx, yy - hh), (cx + ww, yy), (cx - ww, yy)], c)
            art.poly([(cx, yy - hh), (cx + ww * 0.5, yy - hh * 0.35), (cx - ww * 0.2, yy - hh * 0.1)], lighten(c, 0.18))
        if snow:
            for i in range(4):
                yy = h * 0.62 - i * h * 0.15
                ww = w * (0.44 - i * 0.075)
                art.poly([(cx, yy - h * 0.22), (cx + ww * 0.7, yy - h * 0.13), (cx - ww * 0.7, yy - h * 0.13)], SNOW[0])
        return art.reduce(threshold=90)

    if snow:
        for _ in range(14):
            x = cx + rng.uniform(-rx, rx) * 0.8
            y = cy + rng.uniform(-ry, ry) * 0.5 - ry * 0.25
            r = rng.uniform(3, 7)
            art.ellipse(x - r, y - r * 0.6, x + r, y + r * 0.6, SNOW[0])
    if blossoms:
        for _ in range(22):
            x = cx + rng.uniform(-rx, rx) * 0.9
            y = cy + rng.uniform(-ry, ry) * 0.9
            art.px(int(x), int(y), rng.choice(blossoms))
            art.px(int(x) + 1, int(y), lighten(rng.choice(blossoms), 0.2))
    return art.reduce(threshold=90)


# --------------------------------------------------------------------------- #
# small props
# --------------------------------------------------------------------------- #
def rock(w, h, rng, mossy=False, snow=False):
    art = Art(w, h, ss=2)
    cx, cy = w / 2.0, h * 0.62
    art.ellipse(cx - w * 0.42, h - 5, cx + w * 0.42, h - 1, with_alpha(rgb(20, 30, 20), 60))
    pts = []
    n = 8
    for i in range(n):
        a = i / n * math.tau
        rr = rng.uniform(0.75, 1.0)
        pts.append((cx + math.cos(a) * w * 0.42 * rr, cy + math.sin(a) * h * 0.40 * rr))
    art.poly(pts, STONE[1])
    art.poly([(cx - w * 0.28, cy - h * 0.22), (cx + w * 0.06, cy - h * 0.34), (cx + w * 0.28, cy - h * 0.06),
              (cx - w * 0.05, cy + h * 0.06)], STONE[2])
    art.poly([(cx - w * 0.3, cy + h * 0.12), (cx + w * 0.3, cy + h * 0.10), (cx + w * 0.12, cy + h * 0.32),
              (cx - w * 0.18, cy + h * 0.28)], STONE[3])
    for _ in range(18):
        art.px(rng.randint(3, w - 4), rng.randint(3, h - 3), rng.choice(STONE))
    if mossy:
        for _ in range(26):
            x = rng.randint(2, w - 3)
            y = rng.randint(int(h * 0.4), h - 2)
            art.px(x, y, rng.choice([rgb(88, 142, 62), rgb(70, 122, 52), rgb(104, 158, 72)]))
    if snow:
        for _ in range(16):
            x = rng.randint(3, w - 4)
            y = rng.randint(2, int(h * 0.5))
            art.px(x, y, SNOW[0])
    im = art.reduce(threshold=90)
    return outline_image(im, DARK)


def bush(w, h, rng, berry=False, cols=None):
    art = Art(w, h, ss=2)
    cols = cols or [rgb(74, 132, 58), rgb(92, 152, 70), rgb(58, 110, 46)]
    art.ellipse(2, h - 5, w - 2, h - 1, with_alpha(rgb(20, 40, 20), 60))
    for _ in range(9):
        x = rng.uniform(w * 0.2, w * 0.8)
        y = rng.uniform(h * 0.35, h * 0.85)
        r = rng.uniform(w * 0.18, w * 0.34)
        art.ellipse(x - r, y - r, x + r, y + r * 0.85, rng.choice(cols))
    for _ in range(6):
        x = rng.uniform(w * 0.25, w * 0.7)
        y = rng.uniform(h * 0.28, h * 0.6)
        r = rng.uniform(w * 0.08, w * 0.16)
        art.ellipse(x - r, y - r, x + r, y + r, lighten(cols[1], 0.2))
    if berry:
        for _ in range(8):
            x = rng.randint(4, w - 5)
            y = rng.randint(int(h * 0.35), h - 4)
            art.px(x, y, rgb(214, 62, 74))
            art.px(x + 1, y, rgb(240, 110, 120))
    im = art.reduce(threshold=90)
    return outline_image(im, DARK)


def reeds(w, h, rng, cattail=False):
    art = Art(w, h, ss=2)
    green = [rgb(96, 148, 66), rgb(118, 168, 78), rgb(78, 128, 56)]
    for i in range(9 if not cattail else 7):
        x = rng.uniform(w * 0.15, w * 0.85)
        top = rng.uniform(h * 0.05, h * 0.45)
        bend = rng.uniform(-6, 6)
        c = rng.choice(green)
        art.line([(x, h - 2), (x + bend * 0.4, (h + top) / 2), (x + bend, top)], c, 2)
        if cattail and i % 3 == 0:
            art.ellipse(x + bend - 2, top - 1, x + bend + 2, top + 6, rgb(120, 82, 48))
    im = art.reduce(threshold=90)
    return outline_image(im, DARK)


def lily(w, h, rng, flower=False):
    art = Art(w, h, ss=2)
    cx, cy = w / 2.0, h / 2.0
    art.ellipse(1, 2, w - 1, h - 2, rgb(74, 138, 58))
    art.ellipse(3, 4, w - 3, h - 4, rgb(96, 162, 70))
    art.poly([(cx, cy), (cx + w * 0.32, cy - h * 0.16), (cx + w * 0.30, cy + h * 0.20)], (0, 0, 0, 0))
    for _ in range(12):
        art.px(rng.randint(3, w - 4), rng.randint(3, h - 4), rgb(116, 178, 84))
    if flower:
        for i in range(5):
            a = i / 5.0 * math.tau
            art.ellipse(cx + math.cos(a) * 3 - 2, cy + math.sin(a) * 2 - 2,
                        cx + math.cos(a) * 3 + 2, cy + math.sin(a) * 2 + 2, rgb(240, 150, 190))
        art.px(int(cx), int(cy), rgb(250, 226, 120))
    im = art.reduce(threshold=90)
    return outline_image(im, DARK)


def log(w, h, rng):
    art = Art(w, h, ss=2)
    art.ellipse(2, h - 5, w - 2, h - 1, with_alpha(rgb(20, 30, 20), 60))
    art.rect(3, h * 0.35, w - 3, h - 5, WOOD[1])
    for y in range(int(h * 0.35), h - 5, 2):
        art.rect(3, y, w - 3, y + 1, darken(WOOD[1], 0.15))
    art.ellipse(w - 11, h * 0.30, w - 1, h - 4, WOOD[2])
    art.ellipse(w - 9, h * 0.34, w - 3, h - 6, WOOD[0])
    art.ellipse(w - 7, h * 0.42, w - 5, h - 9, WOOD[3])
    for _ in range(14):
        art.px(rng.randint(3, w - 4), rng.randint(int(h * 0.35), h - 6), rng.choice(WOOD))
    im = art.reduce(threshold=90)
    return outline_image(im, DARK)


def pier_post(w, h, rng):
    art = Art(w, h, ss=2)
    art.rect(3, 4, w - 3, h - 2, WOOD[1])
    art.rect(3, 4, 6, h - 2, WOOD[2])
    art.rect(w - 6, 4, w - 3, h - 2, WOOD[3])
    art.ellipse(2, 2, w - 2, 7, WOOD[2])
    art.ellipse(3, 3, w - 3, 6, WOOD[0])
    for y in range(8, h - 2, 5):
        art.rect(3, y, w - 3, y + 1, WOOD[3])
    im = art.reduce(threshold=90)
    return outline_image(im, DARK)


def fence(w, h, rng):
    art = Art(w, h, ss=2)
    art.rect(4, 6, 9, h - 2, WOOD[1])
    art.rect(w - 9, 6, w - 4, h - 2, WOOD[1])
    art.rect(4, 6, 6, h - 2, WOOD[2])
    art.rect(w - 9, 6, w - 7, h - 2, WOOD[2])
    art.rect(0, int(h * 0.36), w, int(h * 0.36) + 4, WOOD[0])
    art.rect(0, int(h * 0.36), w, int(h * 0.36) + 1, WOOD[2])
    art.rect(0, int(h * 0.62), w, int(h * 0.62) + 3, WOOD[1])
    im = art.reduce(threshold=90)
    return outline_image(im, DARK)


def crate(w, h, rng):
    art = Art(w, h, ss=2)
    art.rect(2, 4, w - 2, h - 2, WOOD[1])
    art.rect(2, 4, w - 2, 8, WOOD[2])
    art.line([(3, 5), (w - 3, h - 3)], WOOD[3], 2)
    art.line([(w - 3, 5), (3, h - 3)], WOOD[3], 2)
    art.rect(2, 4, w - 2, h - 2, None, outline=WOOD[3], width=2)
    im = art.reduce(threshold=90)
    return outline_image(im, DARK)


def barrel(w, h, rng):
    art = Art(w, h, ss=2)
    art.ellipse(3, 4, w - 3, h - 2, WOOD[1])
    art.rect(3, 6, w - 3, h - 5, WOOD[1])
    art.ellipse(4, 3, w - 4, 9, WOOD[2])
    for y in (int(h * 0.34), int(h * 0.72)):
        art.rect(3, y, w - 3, y + 2, rgb(96, 98, 106))
    art.ellipse(5, 4, w - 5, 8, WOOD[0])
    im = art.reduce(threshold=90)
    return outline_image(im, DARK)


def sign(w, h, rng, text_colour=rgb(226, 208, 160)):
    art = Art(w, h, ss=2)
    art.rect(w / 2 - 2, h * 0.42, w / 2 + 2, h - 2, WOOD[1])
    art.rect(2, 4, w - 2, h * 0.46, WOOD[0])
    art.rect(2, 4, w - 2, h * 0.46, None, outline=WOOD[3], width=2)
    for i in range(3):
        y = int(h * 0.16) + i * 4
        art.rect(5, y, w - 5 - (i % 2) * 4, y + 1, text_colour)
    im = art.reduce(threshold=90)
    return outline_image(im, DARK)


def lamp(w, h, rng, lit=True):
    art = Art(w, h, ss=2)
    art.rect(w / 2 - 2, h * 0.3, w / 2 + 2, h - 2, rgb(70, 72, 80))
    art.rect(w / 2 - 3, h * 0.3, w / 2 - 1, h - 2, rgb(96, 98, 108))
    art.poly([(w / 2 - 6, h * 0.30), (w / 2 + 6, h * 0.30), (w / 2 + 4, h * 0.16), (w / 2 - 4, h * 0.16)],
             rgb(60, 62, 70))
    glow = rgb(255, 214, 120) if lit else rgb(120, 118, 110)
    art.ellipse(w / 2 - 4, h * 0.17, w / 2 + 4, h * 0.29, glow)
    art.ellipse(w / 2 - 2, h * 0.19, w / 2 + 2, h * 0.26, lighten(glow, 0.5))
    im = art.reduce(threshold=90)
    return outline_image(im, DARK)


def boat(w, h, rng):
    art = Art(w, h, ss=2)
    art.ellipse(4, h - 6, w - 4, h - 1, with_alpha(rgb(10, 40, 60), 70))
    art.poly([(2, h * 0.42), (w - 2, h * 0.42), (w - 10, h - 4), (10, h - 4)], WOOD[1])
    art.poly([(6, h * 0.46), (w - 6, h * 0.46), (w - 12, h - 7), (12, h - 7)], rgb(60, 44, 30))
    art.poly([(2, h * 0.42), (w - 2, h * 0.42), (w - 4, h * 0.5), (4, h * 0.5)], WOOD[2])
    for x in range(12, w - 12, 8):
        art.rect(x, h * 0.5, x + 4, h * 0.5 + 2, WOOD[0])
    im = art.reduce(threshold=90)
    return outline_image(im, DARK)


def well(w, h, rng):
    art = Art(w, h, ss=2)
    art.ellipse(4, h - 8, w - 4, h - 1, with_alpha(rgb(20, 30, 20), 60))
    art.ellipse(4, h * 0.5, w - 4, h - 2, STONE[1])
    art.ellipse(7, h * 0.55, w - 7, h - 6, rgb(30, 60, 90))
    art.rect(6, h * 0.16, 9, h * 0.6, WOOD[1])
    art.rect(w - 9, h * 0.16, w - 6, h * 0.6, WOOD[1])
    art.poly([(2, h * 0.20), (w - 2, h * 0.20), (w / 2, 2)], rgb(150, 74, 62))
    art.poly([(4, h * 0.19), (w - 4, h * 0.19), (w / 2, 4)], rgb(178, 96, 76))
    im = art.reduce(threshold=90)
    return outline_image(im, DARK)


def board(w, h, rng):
    art = Art(w, h, ss=2)
    art.rect(5, h * 0.5, 9, h - 2, WOOD[1])
    art.rect(w - 9, h * 0.5, w - 5, h - 2, WOOD[1])
    art.rect(2, 3, w - 2, h * 0.55, WOOD[0])
    art.rect(2, 3, w - 2, h * 0.55, None, outline=WOOD[3], width=2)
    # pinned notes
    for i, col in enumerate([rgb(236, 230, 200), rgb(226, 214, 180), rgb(240, 236, 210)]):
        x = 5 + i * 9
        art.rect(x, 7, x + 7, int(h * 0.42), col)
        art.px(x + 3, 8, rgb(190, 60, 60))
        for yy in range(10, int(h * 0.40), 3):
            art.rect(x + 1, yy, x + 6, yy + 1, rgb(150, 140, 120))
    im = art.reduce(threshold=90)
    return outline_image(im, DARK)


def chest(w, h, rng, open_=False):
    art = Art(w, h, ss=2)
    art.rect(2, h * 0.42, w - 2, h - 2, WOOD[1])
    if open_:
        art.poly([(2, h * 0.42), (w - 2, h * 0.42), (w - 5, 2), (5, 2)], WOOD[2])
        art.rect(5, int(h * 0.42), w - 5, int(h * 0.55), rgb(60, 42, 26))
        art.px(int(w / 2), int(h * 0.48), rgb(250, 220, 120))
    else:
        art.poly([(2, h * 0.42), (w - 2, h * 0.42), (w - 2, h * 0.24), (w / 2, h * 0.14), (2, h * 0.24)], WOOD[2])
        art.rect(w / 2 - 3, h * 0.36, w / 2 + 3, h * 0.56, rgb(214, 176, 74))
        art.px(int(w / 2), int(h * 0.48), rgb(120, 90, 30))
    art.rect(2, h * 0.42, w - 2, h - 2, None, outline=WOOD[3], width=1)
    im = art.reduce(threshold=90)
    return outline_image(im, DARK)


def flower(w, h, rng, col):
    art = Art(w, h, ss=2)
    art.line([(w / 2, h - 2), (w / 2, h * 0.45)], rgb(88, 142, 62), 2)
    art.ellipse(w / 2 - 4, h * 0.5, w / 2 - 1, h * 0.6, rgb(96, 152, 68))
    cx, cy = w / 2, h * 0.36
    for i in range(5):
        a = i / 5.0 * math.tau - math.pi / 2
        art.ellipse(cx + math.cos(a) * 2.4 - 2, cy + math.sin(a) * 2.4 - 2,
                    cx + math.cos(a) * 2.4 + 2, cy + math.sin(a) * 2.4 + 2, col)
    art.ellipse(cx - 1.6, cy - 1.6, cx + 1.6, cy + 1.6, rgb(250, 224, 110))
    im = art.reduce(threshold=90)
    return outline_image(im, DARK)


def mushroom(w, h, rng, col=rgb(206, 86, 74)):
    art = Art(w, h, ss=2)
    art.rect(w / 2 - 2, h * 0.5, w / 2 + 2, h - 2, rgb(232, 224, 200))
    art.ellipse(2, 2, w - 2, h * 0.62, col)
    art.ellipse(4, 3, w - 6, h * 0.42, lighten(col, 0.2))
    for _ in range(4):
        art.px(rng.randint(4, w - 5), rng.randint(3, int(h * 0.5)), rgb(244, 240, 226))
    im = art.reduce(threshold=90)
    return outline_image(im, DARK)


def tall_grass(w, h, rng):
    art = Art(w, h, ss=2)
    cols = [rgb(104, 158, 72), rgb(126, 178, 86), rgb(86, 138, 60)]
    for i in range(8):
        x = rng.uniform(2, w - 3)
        art.line([(x, h - 2), (x + rng.uniform(-3, 3), rng.uniform(2, h * 0.5))], rng.choice(cols), 2)
    im = art.reduce(threshold=90)
    return outline_image(im, DARK)


# --------------------------------------------------------------------------- #
# buildings (front-facing 2.5D, like Stardew's farm buildings)
# --------------------------------------------------------------------------- #
def _wall(art, x0, y0, x1, y1, base, rng, plank=True):
    art.rect(x0, y0, x1, y1, base)
    if plank:
        for y in range(int(y0), int(y1), 4):
            art.rect(x0, y, x1, y + 1, darken(base, 0.16))
            art.rect(x0, y + 1, x1, y + 2, lighten(base, 0.05))
    for _ in range(20):
        art.px(rng.randint(int(x0) + 1, int(x1) - 2), rng.randint(int(y0) + 1, int(y1) - 2),
               mix(base, rgb(0, 0, 0), rng.uniform(0, 0.12)))


def _roof(art, cx, top, half_w, drop, col_a, col_b, rng):
    art.poly([(cx - half_w - 6, top + drop), (cx, top), (cx + half_w + 6, top + drop),
              (cx + half_w + 2, top + drop + 8), (cx - half_w - 2, top + drop + 8)], col_b)
    art.poly([(cx - half_w - 6, top + drop), (cx, top), (cx + half_w + 6, top + drop)], col_a)
    for i in range(int(half_w * 2)):
        x = cx - half_w + i
        art.px(int(x), int(top + drop - abs(i - half_w) * (drop / max(1.0, half_w))), darken(col_a, 0.12))


def building(w, h, rng, kind="house"):
    art = Art(w, h, ss=2)
    cx = w / 2.0
    ground = h - 6
    if kind == "house":
        wall = rgb(196, 168, 126)
        roof = rgb(158, 78, 66)
        roof_hi = rgb(186, 100, 84)
        bx0, bx1 = w * 0.16, w * 0.84
        by0 = h * 0.42
        _wall(art, bx0, by0, bx1, ground, wall, rng)
        _roof(art, cx, h * 0.14, (bx1 - bx0) / 2, h * 0.16, roof_hi, roof, rng)
        # chimney
        art.rect(bx1 - 18, h * 0.18, bx1 - 8, h * 0.36, STONE[1])
        art.rect(bx1 - 19, h * 0.16, bx1 - 7, h * 0.20, STONE[2])
        # door
        art.rect(cx - 9, ground - 26, cx + 9, ground, rgb(116, 78, 46))
        art.rect(cx - 7, ground - 24, cx + 7, ground - 2, rgb(146, 100, 60))
        art.px(int(cx + 4), ground - 14, rgb(240, 214, 120))
        # windows (warm light)
        for wx in (bx0 + 8, bx1 - 22):
            art.rect(wx, by0 + 10, wx + 14, by0 + 24, rgb(90, 62, 40))
            art.rect(wx + 2, by0 + 12, wx + 12, by0 + 22, rgb(255, 214, 130))
            art.rect(wx + 6, by0 + 12, wx + 8, by0 + 22, rgb(90, 62, 40))
            art.rect(wx + 2, by0 + 16, wx + 12, by0 + 18, rgb(90, 62, 40))
        # step
        art.rect(cx - 12, ground - 2, cx + 12, ground + 3, STONE[1])
        art.rect(bx0, ground - 2, bx1, ground, darken(wall, 0.3))
    else:  # shop
        wall = rgb(150, 168, 176)
        roof = rgb(72, 108, 138)
        roof_hi = rgb(92, 132, 164)
        bx0, bx1 = w * 0.12, w * 0.88
        by0 = h * 0.46
        _wall(art, bx0, by0, bx1, ground, wall, rng)
        _roof(art, cx, h * 0.20, (bx1 - bx0) / 2, h * 0.13, roof_hi, roof, rng)
        # awning stripes
        for i in range(7):
            x = bx0 + 4 + i * ((bx1 - bx0 - 8) / 7)
            art.poly([(x, by0 + 6), (x + (bx1 - bx0 - 8) / 7, by0 + 6),
                      (x + (bx1 - bx0 - 8) / 7 - 2, by0 + 14), (x - 2, by0 + 14)],
                     rgb(226, 106, 92) if i % 2 == 0 else rgb(240, 236, 220))
        # big window with fish
        art.rect(cx - 30, by0 + 18, cx + 6, by0 + 40, rgb(40, 62, 78))
        art.rect(cx - 28, by0 + 20, cx + 4, by0 + 38, rgb(120, 190, 210))
        art.poly([(cx - 22, by0 + 28), (cx - 12, by0 + 25), (cx - 12, by0 + 31)], rgb(226, 148, 62))
        art.poly([(cx - 12, by0 + 28), (cx - 6, by0 + 24), (cx - 6, by0 + 32)], rgb(226, 148, 62))
        art.px(int(cx - 20), by0 + 27, rgb(20, 24, 30))
        # door
        art.rect(cx + 12, ground - 28, cx + 30, ground, rgb(96, 70, 46))
        art.rect(cx + 14, ground - 26, cx + 28, ground - 2, rgb(126, 92, 58))
        art.rect(cx + 16, ground - 24, cx + 26, ground - 16, rgb(150, 200, 210))
        # sign board
        art.rect(bx0 + 4, by0 - 4, bx0 + 30, by0 + 6, rgb(226, 206, 150))
        art.rect(bx0 + 6, by0 - 2, bx0 + 28, by0 + 4, rgb(120, 92, 56))
        art.rect(bx0, ground - 2, bx1, ground, darken(wall, 0.35))
    im = art.reduce(threshold=90)
    return outline_image(im, DARK)


# --------------------------------------------------------------------------- #
# campfire animation
# --------------------------------------------------------------------------- #
def campfire_frame(w, h, rng, t):
    art = Art(w, h, ss=2)
    cx, cy = w / 2.0, h - 8
    # stone ring
    for i in range(7):
        a = i / 7.0 * math.tau
        art.ellipse(cx + math.cos(a) * 10 - 3, cy + math.sin(a) * 4 - 2,
                    cx + math.cos(a) * 10 + 3, cy + math.sin(a) * 4 + 3, STONE[1 if i % 2 else 2])
    # logs
    art.line([(cx - 9, cy), (cx + 6, cy - 3)], WOOD[1], 4)
    art.line([(cx + 9, cy), (cx - 6, cy - 3)], WOOD[3], 4)
    # flames
    flick = math.sin(t * 1.7) * 2.0
    layers = [
        (rgb(214, 72, 40), 1.00, 0.0),
        (rgb(240, 148, 44), 0.74, 0.5),
        (rgb(250, 214, 92), 0.46, 1.0),
        (rgb(255, 246, 200), 0.24, 1.4),
    ]
    for col, sc, ph in layers:
        hh = (h * 0.62) * sc + flick * sc
        ww = 9 * sc
        wob = math.sin(t * 2.3 + ph) * 2.0 * sc
        art.poly([(cx - ww, cy - 2), (cx + wob, cy - hh), (cx + ww, cy - 2)], col)
        art.ellipse(cx - ww, cy - hh * 0.55, cx + ww, cy - 1, col)
    for _ in range(5):
        x = cx + rng.uniform(-7, 7)
        y = cy - rng.uniform(h * 0.3, h * 0.75)
        art.px(int(x), int(y), rgb(255, 226, 140))
    return art.reduce(threshold=90)


# --------------------------------------------------------------------------- #
def build(atlas, rng):
    """Draw every prop into `atlas` (a pixlib.Atlas)."""
    rng = rng

    # --- trees ------------------------------------------------------------ #
    atlas.add("tree_oak", tree(64, 96, LEAF, WOOD, rng, "oak"))
    atlas.add("tree_oak_big", tree(80, 112, LEAF, WOOD, rng, "oak"))
    atlas.add("tree_autumn", tree(64, 96, AUTUMN, WOOD, rng, "oak"))
    atlas.add("tree_blossom", tree(64, 96, LEAF, WOOD, rng, "oak",
                                  blossoms=[rgb(246, 178, 206), rgb(252, 210, 228), rgb(236, 140, 186)]))
    atlas.add("tree_pine", tree(56, 96, [rgb(46, 96, 58), rgb(58, 116, 68), rgb(38, 82, 50), rgb(70, 132, 78)],
                                WOOD, rng, "pine"))
    atlas.add("tree_pine_snow", tree(56, 96, [rgb(46, 96, 58), rgb(58, 116, 68), rgb(38, 82, 50), rgb(70, 132, 78)],
                                     WOOD, rng, "pine", snow=True))
    atlas.add("tree_bare", tree(56, 92, LEAF, WOOD, rng, "bare", snow=True))
    atlas.add("tree_bare_small", tree(40, 64, LEAF, WOOD, rng, "bare"))
    atlas.add("tree_oak_small", tree(40, 62, LEAF, WOOD, rng, "oak"))
    atlas.add("stump", rock(30, 22, rng))

    # --- plants / nature -------------------------------------------------- #
    atlas.add("bush", bush(34, 30, rng))
    atlas.add("bush_berry", bush(34, 30, rng, berry=True))
    atlas.add("bush_winter", bush(34, 30, rng, cols=[rgb(126, 122, 112), rgb(146, 142, 132), rgb(104, 100, 92)]))
    atlas.add("reeds", reeds(30, 40, rng))
    atlas.add("cattail", reeds(30, 40, rng, cattail=True))
    atlas.add("lily_pad", lily(30, 18, rng))
    atlas.add("lily_flower", lily(30, 18, rng, flower=True))
    atlas.add("log", log(44, 24, rng))
    atlas.add("rock_small", rock(26, 20, rng))
    atlas.add("rock_big", rock(42, 34, rng))
    atlas.add("rock_mossy", rock(38, 30, rng, mossy=True))
    atlas.add("rock_snow", rock(34, 28, rng, snow=True))
    atlas.add("tall_grass", tall_grass(26, 26, rng))
    atlas.add("flower_red", flower(18, 22, rng, rgb(214, 82, 74)))
    atlas.add("flower_blue", flower(18, 22, rng, rgb(96, 138, 226)))
    atlas.add("flower_yellow", flower(18, 22, rng, rgb(240, 206, 84)))
    atlas.add("mushroom", mushroom(18, 18, rng))
    atlas.add("mushroom_blue", mushroom(18, 18, rng, rgb(96, 148, 214)))

    # --- man made --------------------------------------------------------- #
    atlas.add("pier_post", pier_post(18, 32, rng))
    atlas.add("fence", fence(34, 26, rng))
    atlas.add("crate", crate(30, 28, rng))
    atlas.add("barrel", barrel(26, 30, rng))
    atlas.add("sign_fish", sign(32, 36, rng))
    atlas.add("sign_village", sign(32, 36, rng))
    atlas.add("lamp", lamp(22, 48, rng, lit=True))
    atlas.add("lamp_off", lamp(22, 48, rng, lit=False))
    atlas.add("boat", boat(70, 38, rng))
    atlas.add("well", well(52, 58, rng))
    atlas.add("quest_board", board(42, 46, rng))
    atlas.add("chest_closed", chest(34, 28, rng, open_=False))
    atlas.add("chest_open", chest(34, 28, rng, open_=True))
    atlas.add("house", building(140, 132, rng, "house"))
    atlas.add("shop", building(148, 136, rng, "shop"))

    # --- campfire animation (4 frames) ------------------------------------ #
    frames = [campfire_frame(34, 38, rng, i * 0.9) for i in range(4)]
    rects = []
    for i, f in enumerate(frames):
        atlas.add("campfire_%d" % i, f)
        rects.append(atlas.regions["campfire_%d" % i][:4])
    return {"campfire": {"frames": rects, "fps": 8}}
