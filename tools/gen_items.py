"""32x32 item icons: rods, baits, tackle, dishes, junk, treasure, resources."""

import math
import random

from pixlib import Art, darken, lighten, mix, outline_image, rgb, with_alpha

DARK = rgb(32, 28, 34)
S = 32


def _icon():
    return Art(S, S, ss=2)


def _fin(a):
    return outline_image(a.reduce(threshold=90), DARK)


# --------------------------------------------------------------------------- #
def rod(a, col, col2, reel=True, iridium=False):
    a.line([(5, 27), (27, 5)], col, 3)
    a.line([(6, 26), (26, 6)], col2, 1)
    a.line([(5, 27), (10, 22)], rgb(70, 50, 34), 4)
    if reel:
        a.ellipse(12, 15, 20, 23, rgb(96, 100, 110))
        a.ellipse(13, 16, 19, 22, rgb(150, 156, 166))
        a.ellipse(15, 18, 17, 20, rgb(70, 74, 82))
    if iridium:
        for i in range(4):
            a.px(9 + i * 4, 23 - i * 4, rgb(180, 120, 220))


def bait(a, cols, count=5):
    for i in range(count):
        x = 6 + (i % 3) * 8
        y = 12 + (i // 3) * 8
        a.ellipse(x, y, x + 7, y + 5, cols[i % len(cols)])
        a.ellipse(x + 1, y + 1, x + 4, y + 3, lighten(cols[i % len(cols)], 0.3))


def lure(a, col, hook=True, feather=False):
    a.ellipse(9, 12, 23, 20, col)
    a.poly([(9, 16), (4, 12), (4, 20)], lighten(col, 0.25))
    a.px(19, 14, DARK)
    if hook:
        a.arc((17, 17, 24, 25), 0, 200, rgb(200, 204, 212), 2)
    if feather:
        for i in range(3):
            a.line([(8, 16), (2, 12 + i * 4)], rgb(226, 90, 80), 1)


def dish(a, bowl, content, steam=True):
    a.ellipse(5, 16, 27, 28, bowl)
    a.ellipse(7, 14, 25, 22, content)
    a.ellipse(8, 15, 24, 20, lighten(content, 0.2))
    a.rect(12, 26, 20, 29, darken(bowl, 0.2))
    if steam:
        for i in range(3):
            a.arc((10 + i * 5, 4, 14 + i * 5, 14), 200, 340, with_alpha(rgb(255, 255, 255), 150), 1)


def junk_boot(a):
    a.poly([(9, 6), (17, 6), (17, 18), (26, 20), (26, 27), (9, 27)], rgb(112, 84, 60))
    a.poly([(10, 7), (16, 7), (16, 17), (10, 17)], rgb(88, 64, 46))
    a.rect(8, 25, 27, 29, rgb(70, 52, 38))
    a.rect(9, 22, 17, 24, rgb(150, 120, 88))


def junk_can(a):
    a.rect(9, 10, 23, 26, rgb(168, 172, 178))
    a.rect(9, 10, 23, 13, rgb(200, 204, 210))
    a.ellipse(9, 8, 23, 14, rgb(210, 214, 220))
    a.ellipse(12, 10, 20, 13, rgb(120, 124, 130))
    a.rect(11, 17, 21, 21, rgb(196, 60, 50))
    a.rect(12, 18, 20, 20, rgb(240, 230, 200))


def seaweed(a, col=rgb(74, 128, 74)):
    for i in range(4):
        x = 8 + i * 5
        a.line([(x, 27), (x + (3 if i % 2 else -3), 12 + i % 2 * 3)], col, 3)
        a.line([(x, 27), (x + (3 if i % 2 else -3), 12 + i % 2 * 3)], lighten(col, 0.25), 1)


def pearl(a):
    a.ellipse(10, 10, 22, 22, rgb(232, 228, 236))
    a.ellipse(11, 11, 20, 20, rgb(248, 244, 250))
    a.px(14, 13, rgb(255, 255, 255))
    a.arc((10, 10, 22, 22), 40, 200, with_alpha(rgb(180, 170, 200), 200), 1)


def ring(a, gem):
    a.arc((9, 9, 23, 23), 0, 360, rgb(226, 190, 84), 3)
    a.poly([(16, 4), (20, 9), (16, 13), (12, 9)], gem)
    a.poly([(16, 5), (18, 9), (16, 9)], lighten(gem, 0.5))


def gem(a, col):
    a.poly([(16, 4), (26, 13), (16, 28), (6, 13)], col)
    a.poly([(16, 4), (16, 28), (6, 13)], darken(col, 0.25))
    a.poly([(16, 6), (22, 13), (16, 20)], lighten(col, 0.4))
    a.px(13, 11, rgb(255, 255, 255))


def ore(a, col, col2):
    a.poly([(6, 22), (12, 10), (22, 8), (28, 18), (24, 27), (10, 28)], rgb(120, 122, 128))
    a.poly([(8, 21), (13, 12), (21, 10), (26, 18), (22, 25), (11, 26)], rgb(146, 148, 154))
    for (x, y, r) in ((13, 17, 3), (19, 14, 2), (20, 21, 3)):
        a.ellipse(x - r, y - r, x + r, y + r, col)
        a.ellipse(x - r + 1, y - r + 1, x + 1, y + 1, col2)


def resource(a, kind):
    if kind == "wood":
        a.rect(6, 12, 26, 24, rgb(146, 104, 62))
        for y in range(12, 24, 3):
            a.rect(6, y, 26, y + 1, rgb(118, 82, 48))
        a.ellipse(22, 12, 30, 24, rgb(176, 132, 84))
        a.ellipse(24, 14, 28, 22, rgb(146, 104, 62))
        a.ellipse(25, 16, 27, 20, rgb(176, 132, 84))
    elif kind == "stone":
        a.poly([(6, 20), (12, 10), (24, 12), (27, 22), (18, 27), (8, 25)], rgb(146, 148, 154))
        a.poly([(9, 19), (13, 13), (22, 14), (24, 21)], rgb(170, 172, 178))
    elif kind == "fiber":
        for i in range(5):
            a.line([(8 + i * 4, 28), (6 + i * 5, 8 + i % 2 * 4)], rgb(126, 168, 84), 2)


def book(a, cover, pages=rgb(238, 232, 210)):
    a.rect(6, 6, 26, 27, cover)
    a.rect(9, 8, 26, 25, pages)
    a.rect(6, 6, 9, 27, darken(cover, 0.25))
    for i in range(4):
        a.rect(12, 11 + i * 4, 23 - i % 2 * 3, 12 + i * 4, rgb(150, 142, 126))
    a.ellipse(13, 14, 21, 20, rgb(96, 150, 196))
    a.poly([(13, 17), (9, 14), (9, 20)], rgb(96, 150, 196))


def scroll(a):
    a.rect(8, 8, 24, 25, rgb(232, 220, 186))
    a.ellipse(6, 6, 12, 12, rgb(214, 198, 158))
    a.ellipse(20, 21, 26, 27, rgb(214, 198, 158))
    for i in range(4):
        a.rect(11, 12 + i * 3, 22 - i % 2 * 4, 13 + i * 3, rgb(140, 122, 92))
    a.px(20, 9, rgb(196, 60, 50))


def coin(a, size=1.0):
    r = 9 * size
    cx = cy = 16
    a.ellipse(cx - r, cy - r, cx + r, cy + r, rgb(196, 150, 44))
    a.ellipse(cx - r + 1, cy - r + 1, cx + r - 1, cy + r - 1, rgb(240, 196, 74))
    a.ellipse(cx - r + 3, cy - r + 3, cx + r - 3, cy + r - 3, rgb(250, 220, 120))
    a.rect(cx - 2, cy - 5, cx + 2, cy + 5, rgb(196, 150, 44))


def trophy(a):
    a.ellipse(9, 6, 23, 18, rgb(226, 182, 68))
    a.ellipse(11, 8, 21, 16, rgb(246, 210, 110))
    a.rect(14, 17, 18, 23, rgb(206, 160, 52))
    a.rect(10, 23, 22, 27, rgb(160, 120, 44))
    a.arc((4, 8, 12, 18), 90, 270, rgb(226, 182, 68), 2)
    a.arc((20, 8, 28, 18), 270, 90, rgb(226, 182, 68), 2)


def coffee(a):
    a.rect(10, 12, 22, 26, rgb(226, 226, 230))
    a.ellipse(10, 10, 22, 15, rgb(240, 240, 244))
    a.ellipse(12, 11, 20, 14, rgb(96, 62, 40))
    a.arc((21, 14, 28, 22), 270, 90, rgb(226, 226, 230), 2)
    for i in range(2):
        a.arc((13 + i * 5, 2, 17 + i * 5, 10), 200, 340, with_alpha(rgb(255, 255, 255), 170), 1)


def box(a, col, label):
    a.rect(5, 12, 27, 27, col)
    a.rect(5, 12, 27, 16, lighten(col, 0.15))
    a.rect(5, 12, 27, 27, None, outline=darken(col, 0.35), width=2)
    for x in range(9, 24, 4):
        a.rect(x, 19, x + 2, 21, darken(col, 0.3))


# --------------------------------------------------------------------------- #
def build(atlas, rng):
    # rods
    a = _icon(); rod(a, rgb(176, 138, 84), rgb(214, 176, 116)); atlas.add("rod_bamboo", _fin(a))
    a = _icon(); rod(a, rgb(126, 96, 66), rgb(166, 128, 88)); atlas.add("rod_fiberglass", _fin(a))
    a = _icon(); rod(a, rgb(120, 90, 160), rgb(180, 130, 220), iridium=True); atlas.add("rod_iridium", _fin(a))
    a = _icon(); rod(a, rgb(96, 76, 56), rgb(130, 104, 74), reel=False); atlas.add("rod_trainee", _fin(a))

    # baits
    a = _icon(); bait(a, [rgb(206, 132, 132), rgb(226, 158, 150)]); atlas.add("bait_worm", _fin(a))
    a = _icon(); bait(a, [rgb(232, 224, 176), rgb(246, 240, 206)]); atlas.add("bait_maggot", _fin(a))
    a = _icon(); bait(a, [rgb(236, 132, 96), rgb(250, 176, 140)]); atlas.add("bait_shrimp", _fin(a))
    a = _icon(); bait(a, [rgb(140, 214, 226), rgb(196, 244, 250)]); atlas.add("bait_glow", _fin(a))
    a = _icon(); box(a, rgb(150, 110, 70), "bait"); atlas.add("bait_box", _fin(a))

    # lures / tackle
    a = _icon(); lure(a, rgb(226, 176, 62)); atlas.add("lure_spinner", _fin(a))
    a = _icon(); lure(a, rgb(96, 176, 148), feather=True); atlas.add("lure_fly", _fin(a))
    a = _icon(); lure(a, rgb(196, 92, 92)); atlas.add("lure_trap", _fin(a))
    a = _icon(); a.ellipse(8, 10, 24, 26, rgb(176, 132, 84)); a.ellipse(10, 12, 22, 24, rgb(206, 162, 106))
    a.rect(15, 6, 17, 12, rgb(120, 90, 58)); atlas.add("tackle_cork", _fin(a))
    a = _icon(); lure(a, rgb(150, 156, 166), hook=True); atlas.add("tackle_barbed", _fin(a))
    a = _icon(); a.arc((6, 8, 26, 28), 0, 360, rgb(190, 194, 202), 4); a.ellipse(13, 15, 19, 21, rgb(150, 154, 162))
    atlas.add("tackle_magnet", _fin(a))
    a = _icon(); box(a, rgb(96, 120, 148), "tackle"); atlas.add("tackle_box", _fin(a))

    # dishes
    a = _icon(); dish(a, rgb(226, 226, 232), rgb(236, 148, 96)); atlas.add("dish_sushi", _fin(a))
    a = _icon(); dish(a, rgb(150, 110, 70), rgb(196, 132, 74), steam=True); atlas.add("dish_grill", _fin(a))
    a = _icon(); dish(a, rgb(210, 214, 220), rgb(196, 176, 116)); atlas.add("dish_soup", _fin(a))
    a = _icon(); dish(a, rgb(186, 122, 92), rgb(150, 96, 62), steam=False); atlas.add("dish_stew", _fin(a))
    a = _icon(); coffee(a); atlas.add("coffee", _fin(a))

    # junk
    a = _icon(); junk_boot(a); atlas.add("junk_boot", _fin(a))
    a = _icon(); junk_can(a); atlas.add("junk_can", _fin(a))
    a = _icon(); seaweed(a); atlas.add("junk_seaweed", _fin(a))
    a = _icon(); a.rect(4, 18, 28, 22, rgb(146, 116, 78)); a.ellipse(4, 16, 10, 24, rgb(166, 132, 90))
    atlas.add("junk_driftwood", _fin(a))
    a = _icon(); rod(a, rgb(120, 100, 80), rgb(150, 130, 108), reel=False); atlas.add("junk_oldrod", _fin(a))
    a = _icon(); a.arc((8, 8, 24, 24), 0, 360, rgb(190, 196, 204), 3); a.rect(10, 20, 22, 23, rgb(190, 196, 204))
    atlas.add("junk_glasses", _fin(a))

    # treasure
    a = _icon(); pearl(a); atlas.add("treasure_pearl", _fin(a))
    a = _icon(); ring(a, rgb(120, 200, 236)); atlas.add("treasure_ring", _fin(a))
    a = _icon(); gem(a, rgb(126, 206, 148)); atlas.add("treasure_emerald", _fin(a))
    a = _icon(); gem(a, rgb(126, 168, 236)); atlas.add("treasure_sapphire", _fin(a))
    a = _icon(); gem(a, rgb(236, 126, 148)); atlas.add("treasure_ruby", _fin(a))
    a = _icon(); a.ellipse(8, 14, 24, 24, rgb(226, 182, 68)); a.poly([(8, 16), (12, 6), (16, 14), (20, 6), (24, 16)],
                                                                      rgb(246, 210, 110))
    atlas.add("treasure_crown", _fin(a))
    a = _icon(); a.rect(9, 12, 23, 24, rgb(176, 138, 84)); a.poly([(9, 12), (16, 6), (23, 12)], rgb(146, 110, 66))
    a.rect(14, 15, 18, 19, rgb(226, 182, 68)); atlas.add("treasure_idol", _fin(a))
    a = _icon(); coin(a); atlas.add("coin", _fin(a))
    a = _icon(); coin(a); a.ellipse(6, 6, 16, 16, rgb(196, 150, 44)); a.ellipse(7, 7, 15, 15, rgb(250, 220, 120))
    atlas.add("coin_pile", _fin(a))

    # resources
    a = _icon(); resource(a, "wood"); atlas.add("wood", _fin(a))
    a = _icon(); resource(a, "stone"); atlas.add("stone", _fin(a))
    a = _icon(); resource(a, "fiber"); atlas.add("fiber", _fin(a))
    a = _icon(); ore(a, rgb(196, 116, 72), rgb(236, 156, 108)); atlas.add("ore_copper", _fin(a))
    a = _icon(); ore(a, rgb(206, 206, 212), rgb(238, 240, 244)); atlas.add("ore_iron", _fin(a))
    a = _icon(); ore(a, rgb(240, 200, 74), rgb(252, 232, 140)); atlas.add("ore_gold", _fin(a))

    # misc
    a = _icon(); book(a, rgb(96, 140, 96)); atlas.add("fish_dex", _fin(a))
    a = _icon(); scroll(a); atlas.add("quest_scroll", _fin(a))
    a = _icon(); trophy(a); atlas.add("trophy", _fin(a))
    a = _icon(); a.rect(10, 6, 22, 26, rgb(150, 110, 70)); a.ellipse(10, 4, 22, 10, rgb(176, 132, 88))
    a.arc((13, 2, 19, 10), 180, 360, rgb(120, 88, 56), 2); atlas.add("fish_basket", _fin(a))
    a = _icon(); a.poly([(16, 4), (19, 12), (27, 12), (21, 18), (23, 26), (16, 21), (9, 26), (11, 18), (5, 12), (13, 12)],
                        rgb(240, 208, 96)); atlas.add("star", _fin(a))
    a = _icon(); a.poly([(16, 27), (5, 16), (5, 10), (11, 6), (16, 11), (21, 6), (27, 10), (27, 16)],
                        rgb(226, 84, 96)); atlas.add("heart", _fin(a))
    return True
