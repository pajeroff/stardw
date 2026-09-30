"""Effects: bobber, splashes, ripples, weather particles, critters, glows."""

import math
import random

from pixlib import Art, darken, lighten, mix, outline_image, rgb, with_alpha

DARK = rgb(30, 28, 36)


def _fin(a):
    return a.reduce(threshold=80)


def bobber(a, w, h, dip=0):
    cx = w / 2.0
    a.rect(cx - 0.6, 1, cx + 0.6, h * 0.35, rgb(60, 54, 50))
    a.ellipse(cx - w * 0.34, h * (0.30 + dip * 0.06), cx + w * 0.34, h * (0.72 + dip * 0.06), rgb(222, 74, 62))
    a.ellipse(cx - w * 0.34, h * (0.50 + dip * 0.06), cx + w * 0.34, h * (0.74 + dip * 0.06), rgb(240, 236, 226))
    a.ellipse(cx - w * 0.20, h * (0.34 + dip * 0.06), cx - w * 0.02, h * (0.44 + dip * 0.06), rgb(246, 140, 128))
    a.ellipse(cx - 1.2, 0, cx + 1.2, h * 0.16, rgb(240, 236, 226))


def splash(a, w, h, t):
    """t in 0..1 -> expanding crown of droplets."""
    cx, cy = w / 2.0, h * 0.78
    r = 4 + t * (w * 0.42)
    col = rgb(198, 228, 244)
    col2 = rgb(236, 248, 255)
    n = 10
    for i in range(n):
        ang = math.pi + (i / (n - 1.0)) * math.pi
        x = cx + math.cos(ang) * r
        y = cy + math.sin(ang) * r * 0.55 - t * 5
        s = max(1.0, 2.4 - t * 1.6)
        a.ellipse(x - s, y - s, x + s, y + s, col2 if i % 2 else col)
    a.arc((cx - r, cy - r * 0.5, cx + r, cy + r * 0.5), 180, 360, with_alpha(col, 200), 1)
    if t < 0.5:
        a.ellipse(cx - 3 + t * 2, cy - 6 - t * 6, cx + 3 - t * 2, cy + 1 - t * 4, with_alpha(col2, 200))


def ripple(a, w, h, t):
    cx, cy = w / 2.0, h / 2.0
    for i in range(2):
        tt = max(0.05, t - i * 0.22)
        rx = 5 + tt * (w * 0.44)
        ry = rx * 0.5
        alpha = int(210 * max(0.0, 1.0 - tt))
        if alpha > 8:
            a.ellipse(cx - rx, cy - ry, cx + rx, cy + ry, None, outline=with_alpha(rgb(226, 244, 255), alpha), width=1)


def sparkle(a, s, t):
    c = rgb(255, 252, 220)
    n = int(2 + t * 3)
    for i in range(n):
        ang = i / float(n) * math.tau + t
        r = 2 + t * 4
        x, y = s / 2.0 + math.cos(ang) * r, s / 2.0 + math.sin(ang) * r
        a.px(int(x), int(y), c)
    a.px(int(s / 2), int(s / 2), rgb(255, 255, 255))
    if t > 0.5:
        a.px(int(s / 2) + 1, int(s / 2), with_alpha(c, 180))
        a.px(int(s / 2) - 1, int(s / 2), with_alpha(c, 180))


def leaf(a, s, t):
    ang = t * math.tau
    col = rgb(206, 132, 56) if t < 0.5 else rgb(186, 112, 48)
    a.ellipse(s / 2 - 4, s / 2 - 2 + math.sin(ang) * 2, s / 2 + 4, s / 2 + 2 + math.sin(ang) * 2, col)
    a.line([(s / 2 - 3, s / 2 + math.sin(ang) * 2), (s / 2 + 3, s / 2 + math.sin(ang) * 2)], darken(col, 0.3), 1)


def bird(a, w, h, t):
    col = rgb(70, 74, 88)
    flap = [0.0, 0.5, 1.0][t % 3]
    dy = (1 - flap) * 3
    a.line([(2, h / 2 + dy), (w / 2, h / 2 - 1), (w - 2, h / 2 + dy)], col, 2)
    a.px(int(w / 2), int(h / 2 - 1), rgb(52, 56, 68))


def build(atlas, rng):
    # --- bobber ----------------------------------------------------------- #
    for i, dip in enumerate((0, 1)):
        a = Art(12, 18, ss=2)
        bobber(a, 12, 18, dip)
        atlas.add("bobber_%d" % i, outline_image(_fin(a), DARK))

    # --- splash / ripple -------------------------------------------------- #
    for i in range(5):
        a = Art(36, 26, ss=2)
        splash(a, 36, 26, i / 4.0)
        atlas.add("splash_%d" % i, _fin(a))
    atlas.anims_note = None
    for i in range(4):
        a = Art(56, 30, ss=2)
        ripple(a, 56, 30, i / 3.0)
        atlas.add("ripple_%d" % i, _fin(a))
    for i in range(3):
        a = Art(16, 16, ss=2)
        sparkle(a, 16, i / 2.0)
        atlas.add("sparkle_%d" % i, _fin(a))

    # --- weather particles ------------------------------------------------ #
    a = Art(4, 14, ss=2)
    a.line([(2, 1), (1, 13)], rgb(168, 208, 240), 2)
    atlas.add("raindrop", _fin(a))

    a = Art(9, 9, ss=2)
    for i in range(3):
        ang = i / 3.0 * math.pi
        a.line([(4.5 - math.cos(ang) * 4, 4.5 - math.sin(ang) * 4), (4.5 + math.cos(ang) * 4, 4.5 + math.sin(ang) * 4)],
               rgb(236, 246, 255), 1)
    atlas.add("snowflake", _fin(a))

    for i in range(4):
        a = Art(12, 12, ss=2)
        leaf(a, 12, i / 4.0)
        atlas.add("leaf_%d" % i, _fin(a))

    for i in range(3):
        a = Art(20, 12, ss=2)
        bird(a, 20, 12, i)
        atlas.add("bird_%d" % i, _fin(a))

    for i, r in enumerate((2.0, 3.0)):
        a = Art(10, 10, ss=2)
        a.ellipse(5 - r, 5 - r, 5 + r, 5 + r, with_alpha(rgb(250, 240, 150), 220))
        a.ellipse(5 - r * 0.5, 5 - r * 0.5, 5 + r * 0.5, 5 + r * 0.5, rgb(255, 255, 230))
        atlas.add("firefly_%d" % i, _fin(a))

    # --- misc ------------------------------------------------------------- #
    for i in range(3):
        a = Art(14, 14, ss=2)
        for _ in range(3 + i * 2):
            x = rng.uniform(2, 12)
            y = rng.uniform(2, 12)
            r = rng.uniform(1.0, 2.0 + i * 0.5)
            a.ellipse(x - r, y - r, x + r, y + r, with_alpha(rgb(226, 220, 206), 150 - i * 30))
        atlas.add("dust_%d" % i, _fin(a))

    a = Art(40, 18, ss=2)
    a.ellipse(2, 3, 38, 16, with_alpha(rgb(16, 30, 16), 96))
    a.ellipse(6, 6, 34, 14, with_alpha(rgb(16, 30, 16), 70))
    atlas.add("shadow", _fin(a))

    a = Art(56, 56, ss=2)
    for i in range(12):
        r = 26 - i * 2
        a.ellipse(28 - r, 28 - r, 28 + r, 28 + r, with_alpha(rgb(255, 240, 170), 26))
    atlas.add("glow_warm", _fin(a))

    a = Art(56, 56, ss=2)
    for i in range(12):
        r = 26 - i * 2
        a.ellipse(28 - r, 28 - r, 28 + r, 28 + r, with_alpha(rgb(150, 220, 255), 26))
    atlas.add("glow_cool", _fin(a))

    a = Art(10, 10, ss=2)
    a.px(4, 3, rgb(255, 255, 255))
    a.px(5, 4, with_alpha(rgb(255, 255, 255), 200))
    a.px(3, 5, with_alpha(rgb(255, 255, 255), 160))
    atlas.add("water_sparkle", _fin(a))

    a = Art(20, 22, ss=2)
    for i in range(3):
        x = 3 + i * 5
        y = 14 - i * 4
        a.rect(x, y - 5, x + 4, y, None, outline=rgb(240, 240, 246), width=1)
    atlas.add("zzz", _fin(a))

    a = Art(14, 16, ss=2)
    a.ellipse(2, 9, 8, 15, rgb(240, 240, 246))
    a.rect(7, 2, 9, 11, rgb(240, 240, 246))
    a.poly([(9, 2), (13, 1), (13, 5), (9, 6)], rgb(240, 240, 246))
    atlas.add("note", _fin(a))

    a = Art(12, 12, ss=2)
    a.poly([(6, 11), (1, 6), (2, 2), (6, 5), (10, 2), (11, 6)], rgb(236, 106, 118))
    atlas.add("heart_small", _fin(a))

    a = Art(24, 24, ss=2)
    a.ellipse(2, 2, 22, 22, with_alpha(rgb(255, 244, 190), 120))
    a.ellipse(6, 6, 18, 18, with_alpha(rgb(255, 250, 220), 160))
    atlas.add("target_ring", _fin(a))

    # animations table for fx
    anims = {
        "splash": {"frames": [atlas.regions["splash_%d" % i][:4] for i in range(5)], "fps": 14},
        "ripple": {"frames": [atlas.regions["ripple_%d" % i][:4] for i in range(4)], "fps": 8},
        "sparkle": {"frames": [atlas.regions["sparkle_%d" % i][:4] for i in range(3)], "fps": 10},
        "leaf": {"frames": [atlas.regions["leaf_%d" % i][:4] for i in range(4)], "fps": 6},
        "bird": {"frames": [atlas.regions["bird_%d" % i][:4] for i in range(3)], "fps": 8},
        "firefly": {"frames": [atlas.regions["firefly_%d" % i][:4] for i in range(2)], "fps": 3},
        "dust": {"frames": [atlas.regions["dust_%d" % i][:4] for i in range(3)], "fps": 10},
        "bobber": {"frames": [atlas.regions["bobber_%d" % i][:4] for i in range(2)], "fps": 4},
    }
    return anims
