"""UI kit: nine-slice panels, slots, buttons, icons, bars and the pixel logo."""

import math
import random

from pixlib import Art, darken, lighten, mix, outline_image, rgb, with_alpha

DARK = rgb(28, 24, 30)

# normalise: every glyph must be 5 columns x 7 rows
_GLYPHS = {
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "C": [".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."],
    "D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "G": [".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "I": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"],
    "J": ["..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."],
    "K": ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
    "L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
    "M": ["#...#", "##.##", "#.#.#", "#...#", "#...#", "#...#", "#...#"],
    "N": ["#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    "Q": [".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "U": ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "V": ["#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "W": ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"],
    "X": ["#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"],
    "Y": ["#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."],
    "Z": ["#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"],
    "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", "#####"],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["####.", "....#", "....#", ".###.", "....#", "....#", "####."],
    "4": ["#...#", "#...#", "#...#", "#####", "....#", "....#", "....#"],
    "5": ["#####", "#....", "#....", "####.", "....#", "#...#", ".###."],
    "6": [".###.", "#...#", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "#...#", ".###."],
    " ": ["....."] * 7,
    "-": [".....", ".....", ".....", "#####", ".....", ".....", "....."],
    ".": [".....", ".....", ".....", ".....", ".....", ".##..", ".##.."],
    ":": [".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."],
    "!": ["..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."],
    "?": [".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."],
    "/": ["....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."],
}


def text_size(s, scale=1, spacing=1):
    return ((5 + spacing) * len(s) - spacing) * scale, 7 * scale


def draw_text(art, s, x, y, col, scale=1, spacing=1):
    for i, ch in enumerate(s.upper()):
        g = _GLYPHS.get(ch, _GLYPHS[" "])
        for ry, row in enumerate(g):
            for rx, c in enumerate(row):
                if c == "#":
                    art.rect(x + (i * (5 + spacing) + rx) * scale, y + ry * scale,
                             x + (i * (5 + spacing) + rx) * scale + scale, y + ry * scale + scale, col)


# --------------------------------------------------------------------------- #
def _panel(w, h, bg, border, hi, lo):
    a = Art(w, h, ss=2)
    a.rect(1, 1, w - 1, h - 1, bg)
    a.rect(0, 0, w, h, None, outline=border, width=1)
    a.rect(2, 2, w - 2, 3, hi)
    a.rect(2, h - 3, w - 2, h - 2, lo)
    a.rect(2, 2, 3, h - 2, hi)
    a.rect(w - 3, 2, w - 2, h - 2, lo)
    for y in range(3, h - 3, 2):
        a.rect(3, y, w - 3, y + 1, with_alpha(darken(bg, 0.06), 60))
    return a.reduce(threshold=90)


def _slot(size, sel=False):
    a = Art(size, size, ss=2)
    a.rect(1, 1, size - 1, size - 1, rgb(46, 40, 48))
    a.rect(0, 0, size, size, None, outline=rgb(96, 84, 72) if not sel else rgb(246, 214, 110), width=1)
    a.rect(2, 2, size - 2, 3, rgb(66, 58, 66))
    if sel:
        a.rect(1, 1, size - 1, size - 1, None, outline=rgb(255, 240, 170), width=1)
    return a.reduce(threshold=90)


def _button(w, h, base, txt=rgb(248, 244, 232)):
    a = Art(w, h, ss=2)
    a.rect(1, 1, w - 1, h - 1, base)
    a.rect(0, 0, w, h, None, outline=darken(base, 0.45), width=1)
    a.rect(2, 2, w - 2, 4, lighten(base, 0.22))
    a.rect(2, h - 4, w - 2, h - 2, darken(base, 0.22))
    return a.reduce(threshold=90)


def _circle_icon(size, draw):
    a = Art(size, size, ss=2)
    draw(a, size)
    return outline_image(a.reduce(threshold=90), DARK)


def build(atlas, rng):
    # panels / slots / buttons
    atlas.add("panel", _panel(24, 24, rgb(58, 46, 42), rgb(24, 20, 24), rgb(96, 80, 66), rgb(30, 24, 26)))
    atlas.add("panel_light", _panel(24, 24, rgb(226, 212, 178), rgb(96, 78, 58), rgb(248, 240, 214), rgb(176, 156, 120)))
    atlas.add("panel_blue", _panel(24, 24, rgb(40, 56, 82), rgb(16, 22, 34), rgb(74, 100, 138), rgb(22, 30, 46)))
    atlas.add("slot", _slot(20))
    atlas.add("slot_sel", _slot(20, sel=True))
    atlas.add("button", _button(44, 18, rgb(96, 122, 82)))
    atlas.add("button_hover", _button(44, 18, rgb(122, 152, 100)))
    atlas.add("button_pressed", _button(44, 18, rgb(70, 92, 62)))
    atlas.add("button_red", _button(44, 18, rgb(150, 78, 70)))

    # --- small icons ----------------------------------------------------- #
    def ic_gold(a, s):
        a.ellipse(2, 2, s - 2, s - 2, rgb(196, 150, 44))
        a.ellipse(3, 3, s - 3, s - 3, rgb(250, 220, 120))
        a.rect(s / 2 - 1, 4, s / 2 + 1, s - 4, rgb(196, 150, 44))

    def ic_energy(a, s):
        a.poly([(s * 0.55, 1), (s * 0.22, s * 0.55), (s * 0.46, s * 0.55), (s * 0.40, s - 1),
                (s * 0.78, s * 0.42), (s * 0.54, s * 0.42)], rgb(246, 214, 96))

    def ic_clock(a, s):
        a.ellipse(1, 1, s - 1, s - 1, rgb(226, 220, 200))
        a.ellipse(3, 3, s - 3, s - 3, rgb(70, 62, 58))
        a.line([(s / 2, s / 2), (s / 2, 4)], rgb(240, 236, 220), 1)
        a.line([(s / 2, s / 2), (s - 5, s / 2 + 2)], rgb(240, 236, 220), 1)

    def ic_fish(a, s):
        a.ellipse(3, s * 0.3, s - 4, s * 0.72, rgb(126, 186, 216))
        a.poly([(4, s * 0.5), (1, s * 0.28), (1, s * 0.72)], rgb(126, 186, 216))
        a.px(int(s - 6), int(s * 0.44), DARK)

    def ic_rod(a, s):
        a.line([(2, s - 2), (s - 2, 2)], rgb(196, 156, 96), 2)
        a.arc((s * 0.5, s * 0.4, s - 2, s - 2), 200, 350, rgb(220, 220, 214), 1)

    def ic_heart(a, s):
        a.poly([(s / 2, s - 2), (1, s * 0.5), (2, 2), (s / 2, s * 0.35), (s - 2, 2), (s - 1, s * 0.5)], rgb(226, 84, 96))

    def ic_star(a, s):
        a.poly([(s / 2, 1), (s * 0.62, s * 0.4), (s - 1, s * 0.4), (s * 0.68, s * 0.62),
                (s * 0.78, s - 1), (s / 2, s * 0.72), (s * 0.22, s - 1), (s * 0.32, s * 0.62),
                (1, s * 0.4), (s * 0.38, s * 0.4)], rgb(246, 214, 96))

    def ic_quest(a, s):
        a.rect(3, 2, s - 3, s - 2, rgb(232, 220, 186))
        a.ellipse(1, 1, 6, 6, rgb(214, 198, 158))
        for i in range(3):
            a.rect(5, 5 + i * 4, s - 5 - i % 2 * 3, 6 + i * 4, rgb(140, 122, 92))

    def ic_bed(a, s):
        a.rect(1, s * 0.45, s - 1, s - 2, rgb(146, 104, 62))
        a.rect(2, s * 0.3, s - 2, s * 0.5, rgb(206, 96, 96))
        a.rect(3, s * 0.28, s * 0.42, s * 0.44, rgb(236, 232, 220))

    def ic_bag(a, s):
        a.rect(3, s * 0.35, s - 3, s - 2, rgb(150, 110, 70))
        a.arc((s * 0.3, 1, s * 0.7, s * 0.5), 180, 360, rgb(120, 88, 56), 2)
        a.rect(s / 2 - 2, s * 0.55, s / 2 + 2, s * 0.7, rgb(226, 182, 68))

    atlas.add("ic_gold", _circle_icon(16, ic_gold))
    atlas.add("ic_energy", _circle_icon(16, ic_energy))
    atlas.add("ic_clock", _circle_icon(16, ic_clock))
    atlas.add("ic_fish", _circle_icon(18, ic_fish))
    atlas.add("ic_rod", _circle_icon(16, ic_rod))
    atlas.add("ic_heart", _circle_icon(14, ic_heart))
    atlas.add("ic_star", _circle_icon(14, ic_star))
    atlas.add("ic_quest", _circle_icon(16, ic_quest))
    atlas.add("ic_bed", _circle_icon(16, ic_bed))
    atlas.add("ic_bag", _circle_icon(16, ic_bag))

    # --- weather --------------------------------------------------------- #
    def w_sun(a, s):
        a.ellipse(s * 0.28, s * 0.28, s * 0.72, s * 0.72, rgb(250, 214, 92))
        for i in range(8):
            ang = i / 8.0 * math.tau
            a.line([(s / 2 + math.cos(ang) * s * 0.36, s / 2 + math.sin(ang) * s * 0.36),
                    (s / 2 + math.cos(ang) * s * 0.48, s / 2 + math.sin(ang) * s * 0.48)], rgb(250, 214, 92), 1)

    def w_cloud(a, s, rain=None):
        for (cx, cy, r) in ((s * 0.38, s * 0.42, s * 0.22), (s * 0.58, s * 0.38, s * 0.26), (s * 0.74, s * 0.46, s * 0.18)):
            a.ellipse(cx - r, cy - r, cx + r, cy + r, rgb(216, 220, 228))
        a.rect(s * 0.2, s * 0.46, s * 0.86, s * 0.58, rgb(196, 202, 212))
        if rain:
            for i in range(3):
                a.line([(s * (0.3 + i * 0.2), s * 0.64), (s * (0.26 + i * 0.2), s * 0.86)], rain, 2)

    def w_storm(a, s):
        w_cloud(a, s)
        a.poly([(s * 0.55, s * 0.5), (s * 0.4, s * 0.76), (s * 0.52, s * 0.74), (s * 0.44, s * 0.96),
                (s * 0.68, s * 0.66), (s * 0.54, s * 0.68)], rgb(250, 226, 110))

    def w_snow(a, s):
        w_cloud(a, s)
        for i in range(3):
            cx = s * (0.3 + i * 0.2)
            a.px(int(cx), int(s * 0.74), rgb(240, 248, 255))
            a.px(int(cx) + 1, int(s * 0.82), rgb(240, 248, 255))

    atlas.add("w_sun", _circle_icon(18, w_sun))
    atlas.add("w_cloud", _circle_icon(18, lambda a, s: w_cloud(a, s)))
    atlas.add("w_rain", _circle_icon(18, lambda a, s: w_cloud(a, s, rgb(116, 176, 226))))
    atlas.add("w_storm", _circle_icon(18, w_storm))
    atlas.add("w_snow", _circle_icon(18, w_snow))

    # --- seasons --------------------------------------------------------- #
    def season(a, s, col, col2):
        a.ellipse(2, 2, s - 2, s - 2, col)
        a.ellipse(4, 3, s - 5, s - 6, col2)
        a.line([(s / 2, s - 3), (s / 2, s * 0.4)], rgb(120, 88, 56), 2)

    atlas.add("s_spring", _circle_icon(16, lambda a, s: season(a, s, rgb(140, 206, 126), rgb(240, 178, 206))))
    atlas.add("s_summer", _circle_icon(16, lambda a, s: season(a, s, rgb(96, 176, 88), rgb(250, 214, 92))))
    atlas.add("s_autumn", _circle_icon(16, lambda a, s: season(a, s, rgb(214, 132, 62), rgb(240, 186, 84))))
    atlas.add("s_winter", _circle_icon(16, lambda a, s: season(a, s, rgb(186, 214, 236), rgb(240, 248, 255))))

    # --- bars ------------------------------------------------------------ #
    def bar(w, h, bg, border, fill=None):
        a = Art(w, h, ss=2)
        a.rect(1, 1, w - 1, h - 1, bg)
        a.rect(0, 0, w, h, None, outline=border, width=1)
        if fill is not None:
            a.rect(2, 2, w - 2, h - 2, fill)
        return a.reduce(threshold=90)

    atlas.add("bar_bg", bar(64, 10, rgb(30, 26, 30), rgb(16, 14, 18)))
    atlas.add("bar_energy", bar(62, 8, rgb(0, 0, 0, 0), rgb(0, 0, 0, 0), rgb(126, 196, 96)))
    atlas.add("bar_time", bar(62, 8, rgb(0, 0, 0, 0), rgb(0, 0, 0, 0), rgb(126, 168, 226)))
    atlas.add("catch_bg", bar(14, 96, rgb(28, 40, 52), rgb(14, 20, 28)))
    atlas.add("catch_fill", bar(12, 94, rgb(0, 0, 0, 0), rgb(0, 0, 0, 0), rgb(120, 214, 140)))
    atlas.add("prog_bg", bar(14, 120, rgb(40, 32, 30), rgb(16, 12, 14)))
    atlas.add("prog_fill", bar(12, 118, rgb(0, 0, 0, 0), rgb(0, 0, 0, 0), rgb(240, 196, 84)))
    atlas.add("fish_marker", _circle_icon(12, ic_fish))
    atlas.add("treasure_marker", _circle_icon(12, lambda a, s: (
        a.ellipse(2, 2, s - 2, s - 2, rgb(226, 182, 68)), a.px(int(s / 2), int(s / 2), rgb(120, 90, 30)))))

    # --- cursor / misc --------------------------------------------------- #
    def cursor(a, s):
        a.poly([(2, 1), (2, s - 3), (6, s - 7), (9, s - 1), (12, s - 2), (9, s - 8), (14, s - 8)], rgb(248, 246, 238))
        a.line([(2, 1), (2, s - 3)], DARK, 1)

    a = Art(16, 20, ss=2)
    cursor(a, 18)
    atlas.add("cursor", outline_image(a.reduce(threshold=90), DARK))

    a = Art(16, 12, ss=2)
    a.poly([(8, 10), (2, 2), (14, 2)], rgb(246, 214, 96))
    atlas.add("prompt_arrow", outline_image(a.reduce(threshold=90), DARK))

    a = Art(14, 22, ss=2)
    a.ellipse(1, 1, 13, 13, rgb(246, 236, 210))
    a.rect(6, 12, 8, 20, rgb(246, 236, 210))
    a.rect(6, 3, 8, 9, rgb(206, 92, 78))
    a.px(6, 17, rgb(206, 92, 78))
    atlas.add("exclam", outline_image(a.reduce(threshold=90), DARK))

    # --- logo ------------------------------------------------------------ #
    word = "STARDW"
    scale = 5
    tw, th = text_size(word, scale, spacing=2)
    a = Art(tw + 8, th + 10, ss=2)
    draw_text(a, word, 5, 6, rgb(24, 30, 44), scale=scale, spacing=2)
    draw_text(a, word, 4, 4, rgb(120, 168, 214), scale=scale, spacing=2)
    draw_text(a, word, 4, 3, rgb(186, 226, 250), scale=scale, spacing=2)
    # hook flourish under the word
    a.arc((tw * 0.42, th + 2, tw * 0.42 + 18, th + 16), 0, 200, rgb(226, 226, 220), 2)
    atlas.add("logo", outline_image(a.reduce(threshold=90), DARK))
    return _GLYPHS
