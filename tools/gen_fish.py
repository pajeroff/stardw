"""Parametric fish painter -- every fish in the game is drawn from a spec."""

import math
import random

from pixlib import Art, darken, lighten, mix, outline_image, rgb, shade, with_alpha

DARK = rgb(28, 30, 40)

# id: (w, h, shape, pattern, tail, dorsal, extras, palette)
# palette keys: body, belly, fin, mark, accent
FISH = [
    # ---- common lake / river ------------------------------------------- #
    ("carp",        56, 30, "oval",  "saddle",   "round",   "small",  (),      dict(body=(150, 132, 76),  belly=(214, 196, 140), fin=(120, 104, 58),  mark=(110, 96, 52),   accent=(196, 172, 100))),
    ("perch",       54, 28, "oval",  "stripes_v","fork",    "spiky",  (),      dict(body=(126, 156, 74),  belly=(226, 226, 186), fin=(196, 108, 60),  mark=(52, 84, 44),    accent=(236, 156, 60))),
    ("roach",       48, 24, "oval",  "gradient", "fork",    "small",  (),      dict(body=(168, 178, 176), belly=(236, 238, 232), fin=(196, 128, 96),  mark=(120, 132, 132), accent=(226, 176, 140))),
    ("bream",       52, 32, "round", "gradient", "fork",    "small",  (),      dict(body=(142, 148, 122), belly=(222, 220, 190), fin=(176, 156, 110), mark=(96, 104, 84),   accent=(200, 196, 150))),
    ("minnow",      34, 16, "long",  "stripe_h", "fork",    "none",   (),      dict(body=(176, 196, 190), belly=(236, 244, 238), fin=(150, 176, 176), mark=(110, 140, 140), accent=(220, 236, 230))),
    ("loach",       46, 18, "eel",   "spots",    "round",   "none",   ("whiskers",), dict(body=(158, 138, 96), belly=(214, 196, 150), fin=(128, 110, 74), mark=(104, 88, 58), accent=(196, 176, 126))),
    ("bluegill",    44, 30, "round", "gradient", "round",   "small",  (),      dict(body=(86, 132, 176),  belly=(222, 214, 150), fin=(196, 156, 74),  mark=(46, 84, 132),   accent=(126, 176, 214))),
    ("sunfish",     46, 32, "round", "stripes_v","fan",     "small",  (),      dict(body=(214, 168, 72),  belly=(246, 226, 160), fin=(226, 128, 60),  mark=(150, 104, 40),  accent=(250, 206, 110))),
    ("bass",        58, 32, "oval",  "stripes_h","fork",    "spiky",  (),      dict(body=(96, 138, 88),   belly=(222, 228, 196), fin=(126, 168, 108), mark=(56, 92, 56),    accent=(176, 208, 140))),
    ("trout",       58, 26, "long",  "spots",    "fork",    "small",  (),      dict(body=(146, 152, 148), belly=(226, 214, 190), fin=(176, 148, 128), mark=(196, 96, 92),   accent=(236, 176, 150))),
    ("salmon",      62, 28, "long",  "spots",    "fork",    "small",  (),      dict(body=(156, 168, 176), belly=(238, 214, 196), fin=(150, 162, 170), mark=(96, 112, 124),  accent=(236, 140, 120))),
    ("pike",        76, 28, "long",  "marble",   "fan",     "small",  ("teeth",), dict(body=(110, 138, 84), belly=(224, 226, 186), fin=(148, 168, 96), mark=(62, 86, 52),  accent=(196, 208, 130))),
    ("zander",      70, 30, "long",  "stripes_v","fork",    "spiky",  ("teeth",), dict(body=(140, 148, 128), belly=(228, 228, 202), fin=(168, 168, 140), mark=(74, 84, 66), accent=(206, 210, 176))),
    ("catfish",     78, 34, "long",  "gradient", "fan",     "none",   ("whiskers",), dict(body=(84, 92, 92), belly=(176, 176, 162), fin=(66, 74, 76), mark=(52, 58, 60),  accent=(136, 144, 140))),
    ("gar",         74, 22, "long",  "spots",    "pointed", "none",   ("teeth",), dict(body=(116, 128, 86), belly=(200, 206, 160), fin=(94, 106, 68), mark=(66, 78, 50),  accent=(176, 188, 132))),
    ("eel",         72, 20, "eel",   "gradient", "pointed", "none",   (),      dict(body=(72, 82, 74),    belly=(150, 158, 138), fin=(58, 66, 60),    mark=(40, 48, 44),    accent=(124, 136, 118))),
    ("goldfish",    40, 26, "round", "gradient", "fan",     "small",  (),      dict(body=(238, 166, 62),  belly=(252, 216, 130), fin=(240, 130, 62),  mark=(206, 116, 40),  accent=(252, 226, 160))),
    ("koi",         52, 28, "oval",  "saddle",   "fan",     "small",  (),      dict(body=(240, 236, 226), belly=(250, 248, 240), fin=(226, 158, 128), mark=(216, 92, 68),   accent=(246, 200, 170))),
    ("piranha",     44, 26, "round", "gradient", "fork",    "small",  ("teeth",), dict(body=(118, 142, 138), belly=(226, 190, 130), fin=(196, 92, 74),  mark=(52, 72, 72),    accent=(226, 128, 96))),
    # ---- ocean ---------------------------------------------------------- #
    ("herring",     50, 22, "long",  "stripe_h", "fork",    "none",   (),      dict(body=(148, 178, 200), belly=(232, 240, 244), fin=(126, 156, 180), mark=(96, 130, 158),  accent=(206, 226, 240))),
    ("sardine",     44, 20, "long",  "stripe_h", "fork",    "none",   (),      dict(body=(156, 186, 196), belly=(236, 244, 246), fin=(132, 164, 176), mark=(104, 140, 154), accent=(214, 234, 240))),
    ("flounder",    56, 26, "flat",  "spots",    "fan",     "none",   ("top_eyes",), dict(body=(142, 130, 104), belly=(224, 214, 186), fin=(116, 104, 82), mark=(92, 82, 62), accent=(196, 184, 152))),
    ("tuna",        80, 34, "shark", "stripe_h", "fork",    "sail",   (),      dict(body=(72, 106, 148),  belly=(226, 232, 236), fin=(214, 186, 96),  mark=(38, 66, 104),   accent=(126, 168, 206))),
    ("swordfish",   86, 32, "shark", "gradient", "fork",    "sail",   ("bill",),  dict(body=(84, 116, 152), belly=(216, 226, 232), fin=(120, 152, 180), mark=(46, 74, 108),   accent=(146, 184, 214))),
    ("pufferfish",  46, 42, "puffer","spots",    "fan",     "none",   ("spikes",), dict(body=(216, 186, 120), belly=(244, 232, 190), fin=(186, 148, 88),  mark=(148, 116, 62),  accent=(250, 224, 168))),
    ("ray",         72, 40, "ray",   "spots",    "pointed", "none",   (),      dict(body=(126, 132, 148), belly=(216, 212, 216), fin=(104, 110, 126), mark=(82, 88, 104),   accent=(176, 182, 196))),
    ("seahorse",    30, 44, "seahorse", "stripes_v", "none", "small", (),      dict(body=(216, 158, 96),  belly=(246, 208, 150), fin=(236, 186, 120), mark=(166, 108, 56),  accent=(250, 226, 180))),
    ("jellyfish",   44, 44, "jelly", "gradient", "none",    "none",   (),      dict(body=(186, 156, 226), belly=(232, 214, 246), fin=(156, 126, 206), mark=(126, 96, 186),  accent=(226, 206, 250))),
    ("anglerfish",  56, 38, "round", "gradient", "fan",     "none",   ("teeth", "lure"), dict(body=(58, 60, 78), belly=(110, 112, 132), fin=(42, 44, 60), mark=(30, 32, 46), accent=(120, 210, 220))),
    ("ghostfish",   54, 28, "long",  "gradient", "fan",     "none",   ("ghost",), dict(body=(196, 214, 226), belly=(238, 246, 250), fin=(176, 198, 214), mark=(150, 176, 196), accent=(226, 240, 248))),
    ("icefish",     52, 24, "long",  "spots",    "fork",    "small",  ("ghost",), dict(body=(166, 206, 226), belly=(232, 246, 252), fin=(136, 186, 214), mark=(112, 168, 200), accent=(216, 240, 250))),
    ("sturgeon",    84, 30, "shark", "saddle",   "fork",    "small",  ("whiskers",), dict(body=(108, 112, 112), belly=(196, 196, 186), fin=(84, 88, 90), mark=(62, 66, 68), accent=(166, 170, 168))),
    # ---- legendaries ---------------------------------------------------- #
    ("moon_carp",   64, 36, "oval",  "marble",   "fan",     "sail",   ("glow",), dict(body=(148, 176, 226), belly=(232, 240, 252), fin=(112, 148, 214), mark=(96, 126, 196), accent=(226, 236, 252))),
    ("crimson_pike",86, 32, "long",  "marble",   "fan",     "spiky",  ("teeth", "glow"), dict(body=(168, 62, 58), belly=(236, 176, 150), fin=(124, 40, 44), mark=(96, 28, 34), accent=(246, 156, 120))),
    ("ice_leviathan",92, 38, "shark", "stripes_v", "fork",  "sail",   ("glow", "spikes"), dict(body=(126, 196, 226), belly=(228, 248, 254), fin=(96, 168, 206), mark=(76, 140, 180), accent=(206, 240, 252))),
    ("deep_ghost",  70, 40, "round", "gradient", "fan",     "none",   ("ghost", "lure"), dict(body=(96, 132, 148), belly=(186, 214, 224), fin=(72, 106, 124), mark=(52, 82, 98), accent=(176, 236, 240))),
    ("golden_dragon",88, 34, "long", "stripes_v", "fan",    "sail",   ("glow", "whiskers"), dict(body=(226, 176, 62), belly=(252, 228, 150), fin=(196, 128, 42), mark=(166, 104, 32), accent=(252, 236, 176))),
    ("ancient_koi", 66, 34, "oval",  "saddle",   "fan",     "sail",   ("glow",), dict(body=(236, 122, 96),  belly=(252, 226, 200), fin=(206, 88, 72),   mark=(166, 58, 52),   accent=(250, 200, 160))),
]

FISH_IDS = [f[0] for f in FISH]


# --------------------------------------------------------------------------- #
def _pal(p, key):
    return rgb(*p[key])


def _silhouette(a, w, h, shape, rng):
    """Draw the opaque body silhouette (white) so it can be used as a mask."""
    col = rgb(255, 255, 255)
    if shape == "oval":
        a.ellipse(w * 0.16, h * 0.24, w * 0.90, h * 0.80, col)
        a.poly([(w * 0.80, h * 0.34), (w * 0.99, h * 0.50), (w * 0.80, h * 0.66)], col)
    elif shape == "long":
        a.ellipse(w * 0.10, h * 0.24, w * 0.86, h * 0.80, col)
        a.poly([(w * 0.76, h * 0.32), (w * 0.99, h * 0.50), (w * 0.76, h * 0.70)], col)
    elif shape == "round":
        a.ellipse(w * 0.18, h * 0.14, w * 0.88, h * 0.88, col)
        a.poly([(w * 0.78, h * 0.34), (w * 0.99, h * 0.52), (w * 0.78, h * 0.70)], col)
    elif shape == "flat":
        a.ellipse(w * 0.10, h * 0.16, w * 0.88, h * 0.92, col)
        a.poly([(w * 0.80, h * 0.30), (w * 0.99, h * 0.54), (w * 0.80, h * 0.76)], col)
    elif shape == "eel":
        for i in range(40):
            t = i / 39.0
            x = w * (0.06 + t * 0.88)
            y = h * 0.52 + math.sin(t * math.pi * 2.2) * h * 0.16
            r = h * (0.30 - t * 0.16)
            a.ellipse(x - r, y - r, x + r, y + r, col)
        a.poly([(w * 0.86, h * 0.38), (w * 0.99, h * 0.50), (w * 0.86, h * 0.62)], col)
    elif shape == "shark":
        a.ellipse(w * 0.12, h * 0.22, w * 0.86, h * 0.82, col)
        a.poly([(w * 0.72, h * 0.30), (w * 1.00, h * 0.52), (w * 0.72, h * 0.72)], col)
    elif shape == "puffer":
        a.ellipse(w * 0.14, h * 0.14, w * 0.86, h * 0.86, col)
    elif shape == "ray":
        a.poly([(w * 0.50, h * 0.18), (w * 0.86, h * 0.44), (w * 0.50, h * 0.74), (w * 0.14, h * 0.44)], col)
        a.rect(w * 0.02, h * 0.44, w * 0.5, h * 0.50, col)
    elif shape == "seahorse":
        for i in range(30):
            t = i / 29.0
            x = w * (0.60 - math.sin(t * math.pi * 1.4) * 0.24)
            y = h * (0.14 + t * 0.74)
            r = w * (0.30 - t * 0.16)
            a.ellipse(x - r, y - r, x + r, y + r, col)
    elif shape == "jelly":
        a.ellipse(w * 0.10, h * 0.06, w * 0.90, h * 0.58, col)
        for i in range(6):
            x = w * (0.20 + i * 0.12)
            a.rect(x, h * 0.5, x + w * 0.03, h * 0.92, col)


def _fill_body(a, w, h, shape, p, rng):
    top = _pal(p, "body")
    belly = _pal(p, "belly")
    for y in range(h + 1):
        t = y / float(h)
        c = mix(darken(top, 0.12), belly, max(0.0, min(1.0, (t - 0.15) / 0.75)))
        a.rect(0, y, w, y + 1, c)


def _pattern(a, w, h, kind, p, rng):
    mark = _pal(p, "mark")
    acc = _pal(p, "accent")
    if kind == "stripes_v":
        for i in range(int(w / 6)):
            x = w * 0.18 + i * 6 + rng.uniform(-1, 1)
            a.poly([(x, h * 0.1), (x + 3, h * 0.1), (x + 2, h * 0.9), (x - 1, h * 0.9)],
                   with_alpha(mark, 200))
    elif kind == "stripe_h":
        for i in range(3):
            y = h * (0.30 + i * 0.14)
            a.rect(0, y, w, y + 2, with_alpha(mark, 170))
    elif kind == "spots":
        for _ in range(int(w * h / 55)):
            x = rng.uniform(w * 0.14, w * 0.92)
            y = rng.uniform(h * 0.20, h * 0.82)
            r = rng.uniform(1.0, 2.2)
            a.ellipse(x - r, y - r, x + r, y + r, with_alpha(mark, 190))
    elif kind == "saddle":
        for _ in range(int(w / 12) + 2):
            x = rng.uniform(w * 0.2, w * 0.9)
            y = rng.uniform(h * 0.16, h * 0.5)
            r = rng.uniform(3.0, 6.0)
            a.ellipse(x - r, y - r * 0.7, x + r, y + r * 0.7, with_alpha(mark, 170))
    elif kind == "marble":
        for _ in range(9):
            x0 = rng.uniform(w * 0.16, w * 0.86)
            y0 = rng.uniform(h * 0.22, h * 0.78)
            pts = [(x0, y0)]
            for _ in range(5):
                x0 += rng.uniform(-5, 5)
                y0 += rng.uniform(-3, 3)
                pts.append((x0, y0))
            a.line(pts, with_alpha(mark, 180), 2)
    elif kind == "gradient":
        pass


def _scales(a, w, h, p, rng, chance=0.25):
    acc = _pal(p, "accent")
    for y in range(int(h * 0.25), int(h * 0.85), 3):
        for x in range(int(w * 0.16), int(w * 0.9), 3):
            if rng.random() < chance:
                a.arc((x, y, x + 3, y + 3), 0, 180, with_alpha(lighten(acc, 0.2), 110), 1)


def _tail_and_fins(a, w, h, shape, tail, dorsal, p, rng):
    fin = _pal(p, "fin")
    fin_d = darken(fin, 0.25)
    cx, cy = w * 0.5, h * 0.5
    if tail == "fork":
        a.poly([(w * 0.16, h * 0.50), (w * 0.02, h * 0.12), (w * 0.13, h * 0.44),
                (w * 0.02, h * 0.88), (w * 0.16, h * 0.56)], fin)
        a.line([(w * 0.15, h * 0.52), (w * 0.04, h * 0.18)], fin_d, 1)
        a.line([(w * 0.15, h * 0.54), (w * 0.04, h * 0.82)], fin_d, 1)
    elif tail == "round":
        a.ellipse(w * 0.02, h * 0.24, w * 0.20, h * 0.76, fin)
    elif tail == "fan":
        a.poly([(w * 0.17, h * 0.50), (w * 0.01, h * 0.20), (w * 0.01, h * 0.80)], fin)
        for i in range(4):
            a.line([(w * 0.16, h * 0.5), (w * 0.02, h * (0.24 + i * 0.17))], fin_d, 1)
    elif tail == "pointed":
        a.poly([(w * 0.16, h * 0.48), (w * 0.01, h * 0.40), (w * 0.10, h * 0.60)], fin)
    if shape in ("ray", "jelly", "seahorse"):
        pass
    if dorsal == "small":
        a.poly([(w * 0.40, h * 0.26), (w * 0.56, h * 0.04), (w * 0.66, h * 0.26)], fin)
        a.line([(w * 0.56, h * 0.06), (w * 0.56, h * 0.24)], fin_d, 1)
    elif dorsal == "spiky":
        for i in range(5):
            x = w * (0.34 + i * 0.07)
            a.poly([(x, h * 0.28), (x + 2, h * 0.06 - i % 2 * h * 0.06), (x + 4, h * 0.28)], fin)
    elif dorsal == "sail":
        a.poly([(w * 0.30, h * 0.26), (w * 0.52, h * -0.02), (w * 0.74, h * 0.26)], fin)
        for i in range(5):
            x = w * (0.34 + i * 0.08)
            a.line([(x, h * 0.24), (x + 1, h * 0.04)], fin_d, 1)
    # pectoral + anal fins
    if shape not in ("ray", "jelly", "seahorse"):
        a.poly([(w * 0.56, h * 0.62), (w * 0.44, h * 0.88), (w * 0.62, h * 0.72)], fin)
        a.poly([(w * 0.30, h * 0.72), (w * 0.36, h * 0.94), (w * 0.42, h * 0.72)], fin)


def _details(a, w, h, shape, extras, p, rng):
    dark = DARK
    belly = _pal(p, "belly")
    acc = _pal(p, "accent")
    ex, ey = (w * 0.80, h * 0.42)
    if "top_eyes" in extras:
        ex, ey = (w * 0.72, h * 0.28)
        a.ellipse(ex - 2.6, ey - 2.6, ex + 2.6, ey + 2.6, rgb(246, 246, 236))
        a.disc(ex, ey, 1.4, dark)
        a.px(int(ex + 1), int(ey - 1), rgb(255, 255, 255))
    else:
        a.ellipse(ex - 3.2, ey - 3.2, ex + 3.2, ey + 3.2, rgb(244, 244, 234))
        a.ellipse(ex - 2.0, ey - 2.0, ex + 2.0, ey + 2.0, rgb(52, 44, 40))
        a.disc(ex, ey, 1.1, rgb(14, 12, 14))
        a.px(int(ex + 1), int(ey - 1), rgb(255, 255, 255))
    # mouth
    a.line([(w * 0.985, h * 0.56), (w * 0.90, h * 0.60)], dark, 1)
    # gill
    a.arc((w * 0.68, h * 0.30, w * 0.80, h * 0.70), 100, 260, with_alpha(dark, 150), 1)
    if "teeth" in extras:
        for i in range(4):
            x = w * (0.90 + i * 0.02)
            a.poly([(x, h * 0.58), (x + 1.5, h * 0.63), (x + 3, h * 0.58)], rgb(250, 250, 240))
    if "whiskers" in extras:
        a.line([(w * 0.96, h * 0.58), (w * 1.00, h * 0.72)], dark, 1)
        a.line([(w * 0.94, h * 0.60), (w * 0.96, h * 0.78)], dark, 1)
    if "bill" in extras:
        a.poly([(w * 0.96, h * 0.50), (w * 1.00, h * 0.52), (w * 0.96, h * 0.55)], rgb(206, 206, 206))
    if "spikes" in extras:
        for i in range(14):
            ang = i / 14.0 * math.tau
            x0 = w * 0.5 + math.cos(ang) * w * 0.36
            y0 = h * 0.5 + math.sin(ang) * h * 0.36
            x1 = w * 0.5 + math.cos(ang) * w * 0.46
            y1 = h * 0.5 + math.sin(ang) * h * 0.46
            a.line([(x0, y0), (x1, y1)], darken(_pal(p, "fin"), 0.1), 1)
    if "lure" in extras:
        a.line([(w * 0.84, h * 0.24), (w * 0.90, h * 0.06), (w * 0.98, h * 0.10)], dark, 1)
        a.disc(w * 0.98, h * 0.10, 2.4, acc)
        a.px(int(w * 0.98), int(h * 0.10 - 1), rgb(255, 255, 255))
    if "ghost" in extras:
        a.rect(0, 0, w, h, with_alpha(rgb(255, 255, 255), 26))
    if "glow" in extras:
        a.ellipse(w * 0.1, h * 0.1, w * 0.95, h * 0.9, with_alpha(acc, 40))


def draw_fish(spec, rng):
    fid, w, h, shape, pattern, tail, dorsal, extras, p = spec
    sil = Art(w, h, ss=2)
    _silhouette(sil, w, h, shape, rng)
    mask = sil.alpha_mask(1)

    body = Art(w, h, ss=2)
    _fill_body(body, w, h, shape, p, rng)
    _pattern(body, w, h, pattern, p, rng)
    _scales(body, w, h, p, rng)
    body.keep_only(mask)

    art = Art(w, h, ss=2)
    _tail_and_fins(art, w, h, shape, tail, dorsal, p, rng)
    art.overlay(body)
    _details(art, w, h, shape, extras, p, rng)

    im = art.reduce(threshold=80)
    if "ghost" in extras:
        import numpy as _np
        from PIL import Image as _I
        arr = _np.asarray(im).copy()
        arr[..., 3] = (arr[..., 3] * 0.72).astype("uint8")
        im = _I.fromarray(arr, "RGBA")
    return outline_image(im, DARK)


def build(atlas, rng):
    for spec in FISH:
        atlas.add(spec[0], draw_fish(spec, rng))
    return FISH_IDS
