"""Character sprite sheets: the angler, the shopkeeper and a dog companion."""

import math
import random

from pixlib import Art, darken, lighten, mix, outline_image, rgb, with_alpha

DARK = rgb(34, 28, 38)

SKIN = rgb(240, 198, 152)
SKIN_SH = rgb(214, 164, 120)
HAIR = rgb(104, 68, 42)
HAIR_HI = rgb(132, 90, 56)
SHIRT = rgb(76, 128, 176)
SHIRT_SH = rgb(56, 98, 142)
PANTS = rgb(94, 84, 66)
PANTS_SH = rgb(72, 64, 50)
BOOT = rgb(64, 52, 44)
HAT = rgb(214, 186, 122)
HAT_SH = rgb(178, 150, 92)
ROD = rgb(176, 138, 84)
ROD_HI = rgb(214, 176, 116)
LINE = rgb(238, 238, 232)

W, H = 32, 46


def _body(art, d, pose, t=0.0, rng=None, hat=True, dog=False):
    """Draw one frame. d in {'down','up','left'}; pose string."""
    bob = 0
    if pose.startswith("walk"):
        step = int(pose[-1])
        bob = 0 if step in (0, 2) else (-1 if step == 1 else 1)
    cx = W / 2.0

    # legs -----------------------------------------------------------------
    leg_y = 30 + bob // 2
    spread = 2
    if pose.startswith("walk"):
        step = int(pose[-1])
        offs = {0: (0, 0), 1: (-2, 2), 2: (0, 0), 3: (2, -2)}[step]
    else:
        offs = (0, 0)
    for i, ox in enumerate((-spread, spread)):
        lo = offs[i % 2] if pose.startswith("walk") else 0
        art.rect(cx + ox - 2.5, leg_y, cx + ox + 2.5, leg_y + 9, PANTS_SH if i == 0 else PANTS)
        art.rect(cx + ox - 3, leg_y + 8 + (1 if lo > 0 else 0), cx + ox + 3, leg_y + 11, BOOT)

    # torso ----------------------------------------------------------------
    ty = 18 + bob * 0.5
    art.rect(cx - 6, ty, cx + 6, ty + 13, SHIRT)
    art.rect(cx - 6, ty, cx - 3, ty + 13, SHIRT_SH)
    art.rect(cx - 6, ty + 9, cx + 6, ty + 13, darken(SHIRT, 0.18))
    # belt
    art.rect(cx - 6, ty + 11, cx + 6, ty + 12, rgb(84, 62, 44))
    # vest strap
    art.rect(cx - 1, ty + 1, cx + 1, ty + 10, rgb(226, 210, 168))

    # arms -----------------------------------------------------------------
    arm_col = SKIN
    if pose == "cast_0":
        # rod wound back over the shoulder
        art.rect(cx - 9, ty + 1, cx - 5, ty + 8, SHIRT_SH)
        art.rect(cx + 5, ty - 2, cx + 9, ty + 6, SHIRT)
        art.px(int(cx + 6), int(ty - 3), arm_col)
    elif pose in ("cast_1", "hold_0", "reel_0", "reel_1"):
        art.rect(cx - 9, ty + 2, cx - 5, ty + 9, SHIRT_SH)
        art.rect(cx + 4, ty + 2, cx + 9, ty + 9, SHIRT)
        art.px(int(cx + 7), int(ty + 2), arm_col)
        art.px(int(cx + 8), int(ty + 3), arm_col)
    else:
        swing = offs[0] if pose.startswith("walk") else 0
        art.rect(cx - 9, ty + 2 - swing * 0.5, cx - 5, ty + 10, SHIRT_SH)
        art.rect(cx + 5, ty + 2 + swing * 0.5, cx + 9, ty + 10, SHIRT)
        art.px(int(cx - 7), int(ty + 10), arm_col)
        art.px(int(cx + 7), int(ty + 10), arm_col)

    # head -----------------------------------------------------------------
    hy = 6 + bob
    if d == "up":
        art.ellipse(cx - 6, hy, cx + 6, hy + 12, HAIR)
        art.ellipse(cx - 5, hy + 1, cx + 3, hy + 6, HAIR_HI)
        art.rect(cx - 5, hy + 9, cx + 5, hy + 12, HAIR)
    elif d == "down":
        art.ellipse(cx - 6, hy, cx + 6, hy + 12, SKIN)
        art.ellipse(cx - 6, hy - 1, cx + 6, hy + 5, HAIR)
        art.ellipse(cx - 5, hy, cx + 1, hy + 4, HAIR_HI)
        art.px(int(cx - 3), int(hy + 7), DARK)
        art.px(int(cx + 3), int(hy + 7), DARK)
        art.px(int(cx - 1), int(hy + 9), SKIN_SH)
        art.px(int(cx + 1), int(hy + 9), SKIN_SH)
    else:  # side
        art.ellipse(cx - 6, hy, cx + 6, hy + 12, SKIN)
        art.ellipse(cx - 6, hy - 1, cx + 3, hy + 6, HAIR)
        art.ellipse(cx - 5, hy, cx - 1, hy + 4, HAIR_HI)
        art.px(int(cx + 3), int(hy + 7), DARK)
        art.px(int(cx + 5), int(hy + 8), SKIN_SH)
        art.rect(cx + 5, hy + 5, cx + 7, hy + 8, SKIN)  # nose

    # hat ------------------------------------------------------------------
    if hat:
        art.ellipse(cx - 9, hy - 3, cx + 9, hy + 3, HAT_SH)
        art.ellipse(cx - 8, hy - 4, cx + 8, hy + 2, HAT)
        art.ellipse(cx - 5, hy - 6, cx + 5, hy - 1, HAT)
        art.rect(cx - 5, hy - 3, cx + 5, hy - 2, rgb(120, 92, 62))

    # rod ------------------------------------------------------------------
    def rod_pts(angle_deg, length, hx, hy2):
        a = math.radians(angle_deg)
        return [(hx, hy2), (hx + math.cos(a) * length, hy2 + math.sin(a) * length)]

    hx = cx + 8 if d != "left" else cx - 8
    if pose == "cast_0":
        pts = rod_pts(-140 if d == "left" else -40, 20, hx, ty + 2)
        art.line(pts, ROD, 2)
        art.line([pts[1], (pts[1][0] + 2, pts[1][1] - 2)], ROD_HI, 1)
    elif pose == "cast_1":
        pts = rod_pts(35 if d != "left" else 145, 22, hx, ty + 3)
        art.line(pts, ROD, 2)
        art.line(pts, ROD_HI, 1)
    elif pose in ("hold_0", "reel_0", "reel_1"):
        lift = 0 if pose == "hold_0" else (0 if pose == "reel_0" else -2)
        pts = rod_pts(42 + lift if d != "left" else 138 - lift, 21, hx, ty + 4)
        art.line(pts, ROD, 2)
        art.line(pts, ROD_HI, 1)
        art.line([pts[1], (pts[1][0], pts[1][1] + 6)], LINE, 1)

    return art


def _frame(d, pose, rng, dog=False):
    art = Art(W, H, ss=2)
    art.ellipse(W / 2 - 8, H - 5, W / 2 + 8, H - 1, with_alpha(rgb(20, 32, 20), 60))
    _body(art, d, pose, rng=rng)
    im = art.reduce(threshold=90)
    if d == "left":
        im = im.transpose(Image.FLIP_LEFT_RIGHT) if False else im
    return outline_image(im, DARK)


def _dog_frame(art, rng, step):
    body = rgb(196, 146, 86)
    dark = rgb(158, 112, 60)
    y = 28 + (0 if step == 0 else 1)
    art.ellipse(6, y, 26, y + 10, body)
    art.ellipse(7, y + 1, 20, y + 6, lighten(body, 0.15))
    # head
    art.ellipse(22, y - 8, 34, y + 4, body)
    art.ellipse(23, y - 7, 30, y - 1, lighten(body, 0.2))
    art.ellipse(30, y - 3, 36, y + 2, dark)
    art.px(29, y - 4, DARK)
    art.ellipse(23, y - 10, 27, y - 4, dark)
    # legs
    for i, lx in enumerate((9, 14, 19, 23)):
        off = (0 if (i + step) % 2 == 0 else 2)
        art.rect(lx, y + 8, lx + 3, y + 13 + off, dark)
    # tail
    art.line([(6, y + 2), (2, y - 4 + step)], body, 3)
    return art


def _shopkeeper_frame(art, rng, t):
    """Willy-style shopkeeper behind the counter."""
    cx = W / 2.0
    bob = 0 if t == 0 else 1
    art.rect(cx - 9, 24 + bob, cx + 9, 42, rgb(64, 92, 128))
    art.rect(cx - 9, 24 + bob, cx - 5, 42, rgb(48, 72, 104))
    art.rect(cx - 9, 34 + bob, cx + 9, 36 + bob, rgb(196, 176, 120))
    art.ellipse(cx - 7, 10 + bob, cx + 7, 24 + bob, SKIN)
    art.ellipse(cx - 7, 8 + bob, cx + 7, 16 + bob, rgb(226, 226, 226))
    art.rect(cx - 6, 19 + bob, cx + 6, 24 + bob, rgb(226, 226, 226))  # beard
    art.px(int(cx - 3), int(17 + bob), DARK)
    art.px(int(cx + 3), int(17 + bob), DARK)
    art.ellipse(cx - 8, 6 + bob, cx + 8, 12 + bob, rgb(214, 176, 96))  # cap
    art.rect(cx - 8, 11 + bob, cx + 8, 13 + bob, rgb(178, 140, 70))
    return art


def build(atlas, rng):
    """Render all character frames into `atlas` and record animation tables."""
    dirs = ["down", "up", "left", "right"]
    poses = ["idle", "walk_0", "walk_1", "walk_2", "walk_3", "cast_0", "cast_1", "hold_0", "reel_0", "reel_1"]
    anims = {}
    for d in dirs:
        for pose in poses:
            art = Art(W, H, ss=2)
            art.ellipse(W / 2 - 8, H - 5, W / 2 + 8, H - 1, with_alpha(rgb(20, 32, 20), 60))
            _body(art, "left" if d == "right" else d, pose, rng=rng)
            im = outline_image(art.reduce(threshold=90), DARK)
            if d == "right":
                from PIL import Image as _I
                im = im.transpose(_I.FLIP_LEFT_RIGHT)
            atlas.add("char_%s_%s" % (d, pose), im)
        anims["walk_" + d] = {"frames": [atlas.regions["char_%s_walk_%d" % (d, i)][:4] for i in range(4)], "fps": 8}
        anims["idle_" + d] = {"frames": [atlas.regions["char_%s_idle" % d][:4]], "fps": 4}
        anims["cast_" + d] = {"frames": [atlas.regions["char_%s_cast_%d" % (d, i)][:4] for i in range(2)], "fps": 6}
        anims["hold_" + d] = {"frames": [atlas.regions["char_%s_hold_0" % d][:4]], "fps": 4}
        anims["reel_" + d] = {"frames": [atlas.regions["char_%s_reel_%d" % (d, i)][:4] for i in range(2)], "fps": 7}

    # --- dog -------------------------------------------------------------- #
    from PIL import Image as _I
    dog_frames = []
    for i in range(2):
        art = Art(38, 40, ss=2)
        _dog_frame(art, rng, i)
        im = outline_image(art.reduce(threshold=90), DARK)
        atlas.add("dog_%d" % i, im)
        dog_frames.append(atlas.regions["dog_%d" % i][:4])
    anims["dog"] = {"frames": dog_frames, "fps": 6}

    # --- shopkeeper ------------------------------------------------------- #
    sk = []
    for i in range(2):
        art = Art(W, H, ss=2)
        _shopkeeper_frame(art, rng, i)
        im = outline_image(art.reduce(threshold=90), DARK)
        atlas.add("keeper_%d" % i, im)
        sk.append(atlas.regions["keeper_%d" % i][:4])
    anims["keeper"] = {"frames": sk, "fps": 2}
    return anims
