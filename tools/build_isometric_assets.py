#!/usr/bin/env python3
"""
High-Resolution Isometric Asset Builder for Stardw (Godot 4.7).
Processes the AI-generated HD pixel-art sprites in `assets/ai_raw/*.png`
to build:
1. Clean transparent-background Isometric World Objects (`assets/objects/*.png`):
   - tree_oak.png (160x176)
   - tree_pine.png (144x192)
   - tree_birch.png (144x176)
   - tree_willow.png (168x176)
   - rock_large.png (112x96)
   - rock_slate.png (112x96)
   - rock_ore.png (88x76)
   - rock_small.png (64x56)
   - tree_stump.png (64x56)
   - bush_berry.png (68x60)
   - log_fallen.png (96x56)
2. High-Resolution Traveler Character Spritesheet (`assets/sprites/player_spritesheet.png`):
   - 96x96 px per frame, 6 cols x 56 rows (576x5376 px)
   - 8 directions x 7 animations (idle, walk, run, axe, pickaxe, water, interact)
3. High-Resolution Isometric Diamond Tileset (`assets/tilesets/world_tileset.png`):
   - 64x32 isometric 2:1 diamond tiles (with 8px 3D depth bevel = 64x40 per cell, 16x5 grid = 1024x200)
   - Multiple varieties of grass (meadow, clover, dark forest moss, golden birch grass),
     stone/cobblestone paths, sandy shores, isometric wooden bridges, and animated water.
"""

from collections import deque
import math
import os
import random
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance

os.makedirs("assets/objects", exist_ok=True)
os.makedirs("assets/sprites", exist_ok=True)
os.makedirs("assets/tilesets", exist_ok=True)
os.makedirs("assets/ui", exist_ok=True)


def remove_white_bg_floodfill(
    im: Image.Image,
    white_thresh: int = 232,
    chroma_thresh: int = 28,
    remove_interior_white: bool = True,
) -> Image.Image:
    """Removes solid white background from AI pixel art via exterior BFS flood-fill + interior pure-white cleanup."""
    rgba = np.array(im.convert("RGBA"), dtype=np.uint8)
    h, w, _ = rgba.shape
    r = rgba[:, :, 0].astype(np.int16)
    g = rgba[:, :, 1].astype(np.int16)
    b = rgba[:, :, 2].astype(np.int16)

    min_c = np.minimum(np.minimum(r, g), b)
    max_c = np.maximum(np.maximum(r, g), b)
    is_bg_candidate = (min_c >= white_thresh) & ((max_c - min_c) <= chroma_thresh)

    visited = np.zeros((h, w), dtype=bool)
    q = deque()

    # Seed from all 4 borders
    for x in range(w):
        if is_bg_candidate[0, x]:
            visited[0, x] = True
            q.append((0, x))
        if is_bg_candidate[h - 1, x]:
            visited[h - 1, x] = True
            q.append((h - 1, x))
    for y in range(h):
        if is_bg_candidate[y, 0] and not visited[y, 0]:
            visited[y, 0] = True
            q.append((y, 0))
        if is_bg_candidate[y, w - 1] and not visited[y, w - 1]:
            visited[y, w - 1] = True
            q.append((y, w - 1))

    while q:
        cy, cx = q.popleft()
        for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx]:
                if is_bg_candidate[ny, nx]:
                    visited[ny, nx] = True
                    q.append((ny, nx))

    if remove_interior_white:
        # Also remove enclosed pure-white holes (e.g. between walking staff and leg or between tree roots)
        pure_white_hole = (min_c >= 236) & ((max_c - min_c) <= 18)
        visited |= pure_white_hole

    rgba[visited, 3] = 0

    # Strip 1-pixel bright anti-aliased fringe right next to transparent background
    alpha = rgba[:, :, 3] > 0
    eroded = alpha.copy()
    for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        shifted = np.zeros_like(alpha)
        if dy == -1:
            shifted[:-1, :] = alpha[1:, :]
        elif dy == -1:
            pass
        if dy == 1:
            shifted[1:, :] = alpha[:-1, :]
        elif dx == -1:
            shifted[:, :-1] = alpha[:, 1:]
        elif dx == 1:
            shifted[:, 1:] = alpha[:, :-1]
        eroded &= shifted

    border_px = alpha & (~eroded)
    bright_fringe = border_px & (min_c >= 190) & ((max_c - min_c) <= 38)
    rgba[bright_fringe, 3] = 0

    return Image.fromarray(rgba, "RGBA")


def crop_to_alpha(im: Image.Image) -> Image.Image:
    bbox = im.getbbox()
    if not bbox:
        return im
    return im.crop(bbox)


def fit_on_canvas_with_iso_shadow(
    im: Image.Image,
    target_w: int,
    target_h: int,
    bottom_pad: int = 6,
    shadow_rx: int = 28,
    shadow_ry: int = 12,
    shadow_y_off: int = -8,
) -> Image.Image:
    cropped = crop_to_alpha(im)
    cw, ch = cropped.size
    avail_w = target_w - 8
    avail_h = target_h - bottom_pad - 4
    scale = min(avail_w / float(cw), avail_h / float(ch))
    new_w = max(1, int(round(cw * scale)))
    new_h = max(1, int(round(ch * scale)))

    # Crisp nearest-neighbor downscale to preserve pixel-art edges
    resized = cropped.resize((new_w, new_h), Image.Resampling.NEAREST)

    canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # Draw soft 2:1 isometric elliptical shadow under object base
    scx = target_w // 2
    scy = target_h - bottom_pad + shadow_y_off
    draw.ellipse(
        [scx - shadow_rx, scy - shadow_ry, scx + shadow_rx, scy + shadow_ry],
        fill=(14, 18, 28, 95),
    )
    draw.ellipse(
        [scx - int(shadow_rx * 0.7), scy - int(shadow_ry * 0.7), scx + int(shadow_rx * 0.7), scy + int(shadow_ry * 0.7)],
        fill=(10, 14, 22, 125),
    )

    paste_x = (target_w - new_w) // 2
    paste_y = target_h - bottom_pad - new_h
    canvas.alpha_composite(resized, (paste_x, paste_y))
    return canvas


# =============================================================================
# 1. PROCESS AI WORLD OBJECTS (4 Trees, 4 Rocks, Stump, Berry Bush, Fallen Log)
# =============================================================================
def build_world_objects() -> dict:
    print("Processing AI-generated isometric trees, rocks, and forest props...")
    raw_oak = remove_white_bg_floodfill(Image.open("assets/ai_raw/iso_tree_oak.png"))
    raw_pine = remove_white_bg_floodfill(Image.open("assets/ai_raw/iso_tree_pine.png"))
    raw_birch = remove_white_bg_floodfill(Image.open("assets/ai_raw/iso_tree_birch.png"), remove_interior_white=False)
    raw_willow = remove_white_bg_floodfill(Image.open("assets/ai_raw/iso_tree_willow.png"))
    raw_boulder = remove_white_bg_floodfill(Image.open("assets/ai_raw/iso_rock_boulder.png"))
    raw_slate = remove_white_bg_floodfill(Image.open("assets/ai_raw/iso_rock_slate.png"))
    raw_ore = remove_white_bg_floodfill(Image.open("assets/ai_raw/iso_rock_crystal_ore.png"))

    # 1. Oak Tree (160x176)
    oak_img = fit_on_canvas_with_iso_shadow(raw_oak, 160, 176, bottom_pad=8, shadow_rx=42, shadow_ry=18, shadow_y_off=-12)
    oak_img.save("assets/objects/tree_oak.png")

    # 2. Pine Tree (144x192)
    pine_img = fit_on_canvas_with_iso_shadow(raw_pine, 144, 192, bottom_pad=8, shadow_rx=34, shadow_ry=15, shadow_y_off=-10)
    pine_img.save("assets/objects/tree_pine.png")

    # 3. Birch Tree (144x176)
    birch_img = fit_on_canvas_with_iso_shadow(raw_birch, 144, 176, bottom_pad=8, shadow_rx=34, shadow_ry=15, shadow_y_off=-10)
    birch_img.save("assets/objects/tree_birch.png")

    # 4. Weeping Willow Tree (168x176) - NEW tree variety!
    willow_img = fit_on_canvas_with_iso_shadow(raw_willow, 168, 176, bottom_pad=8, shadow_rx=46, shadow_ry=19, shadow_y_off=-12)
    willow_img.save("assets/objects/tree_willow.png")

    # 5. Large Mossy Granite Boulder (112x96)
    boulder_img = fit_on_canvas_with_iso_shadow(raw_boulder, 112, 96, bottom_pad=6, shadow_rx=44, shadow_ry=20, shadow_y_off=-14)
    boulder_img.save("assets/objects/rock_large.png")

    # 6. Dark Slate Rock Formation (112x96) - NEW rock variety!
    slate_img = fit_on_canvas_with_iso_shadow(raw_slate, 112, 96, bottom_pad=6, shadow_rx=44, shadow_ry=20, shadow_y_off=-14)
    slate_img.save("assets/objects/rock_slate.png")

    # 7. Crystal / Gold Ore Node (88x76)
    ore_img = fit_on_canvas_with_iso_shadow(raw_ore, 88, 76, bottom_pad=6, shadow_rx=34, shadow_ry=16, shadow_y_off=-10)
    ore_img.save("assets/objects/rock_ore.png")

    # 8. Small Mossy Fieldstone (64x56) - derived from AI boulder
    small_rock = fit_on_canvas_with_iso_shadow(raw_boulder, 64, 56, bottom_pad=5, shadow_rx=24, shadow_ry=11, shadow_y_off=-6)
    small_rock.save("assets/objects/rock_small.png")

    # 9. Tree Stump (64x56) - crafted from bottom trunk/roots of AI Oak Tree + cut wood rings
    oak_crop = crop_to_alpha(raw_oak)
    ow, oh = oak_crop.size
    trunk_slice = oak_crop.crop((int(ow * 0.24), int(oh * 0.62), int(ow * 0.76), oh))
    stump_canvas = fit_on_canvas_with_iso_shadow(trunk_slice, 64, 56, bottom_pad=5, shadow_rx=24, shadow_ry=11, shadow_y_off=-6)
    s_draw = ImageDraw.Draw(stump_canvas)
    # Draw isometric cut wood top ellipse
    s_draw.ellipse([19, 13, 45, 26], fill=(42, 28, 18, 255))
    s_draw.ellipse([21, 14, 43, 25], fill=(214, 168, 112, 255))
    s_draw.ellipse([24, 16, 40, 23], fill=(182, 134, 82, 255))
    s_draw.ellipse([27, 17, 37, 22], fill=(224, 182, 126, 255))
    s_draw.ellipse([30, 19, 34, 21], fill=(138, 92, 52, 255))
    stump_canvas.save("assets/objects/tree_stump.png")

    # 10. Wild Berry Bush (68x60) - crafted from lush leaf cluster of AI Oak Tree + pixel-art berries
    canopy_cluster = oak_crop.crop((int(ow * 0.18), int(oh * 0.06), int(ow * 0.82), int(oh * 0.56)))
    bush_canvas = fit_on_canvas_with_iso_shadow(canopy_cluster, 68, 60, bottom_pad=5, shadow_rx=26, shadow_ry=12, shadow_y_off=-7)
    b_draw = ImageDraw.Draw(bush_canvas)
    berry_spots = [
        (22, 24), (30, 18), (40, 20), (46, 28),
        (26, 34), (35, 30), (43, 36), (18, 32), (33, 23)
    ]
    for bx, by in berry_spots:
        b_draw.ellipse([bx - 3, by - 3, bx + 3, by + 3], fill=(32, 18, 24, 255))
        b_draw.ellipse([bx - 2, by - 2, bx + 2, by + 2], fill=(225, 42, 56, 255))
        b_draw.point((bx - 1, by - 1), fill=(255, 165, 175, 255))
    bush_canvas.save("assets/objects/bush_berry.png")

    # 11. Isometric Mossy Fallen Log (96x56)
    willow_crop = crop_to_alpha(raw_willow)
    ww, wh = willow_crop.size
    bark_slice = willow_crop.crop((int(ww * 0.28), int(wh * 0.55), int(ww * 0.72), int(wh * 0.96)))
    bark_rot = bark_slice.rotate(72, expand=True, resample=Image.Resampling.NEAREST)
    log_canvas = fit_on_canvas_with_iso_shadow(bark_rot, 96, 56, bottom_pad=6, shadow_rx=38, shadow_ry=13, shadow_y_off=-6)
    l_draw = ImageDraw.Draw(log_canvas)
    # Cute red-capped forest mushrooms on the fallen log
    for mx, my in [(36, 22), (54, 25), (44, 19)]:
        l_draw.rectangle([mx - 1, my, mx + 2, my + 5], fill=(240, 228, 205, 255))
        l_draw.ellipse([mx - 4, my - 4, mx + 5, my + 2], fill=(32, 20, 24, 255))
        l_draw.ellipse([mx - 3, my - 3, mx + 4, my + 1], fill=(224, 52, 48, 255))
        l_draw.point((mx - 1, my - 2), fill=(255, 245, 230, 255))
        l_draw.point((mx + 2, my - 1), fill=(255, 245, 230, 255))
    log_canvas.save("assets/objects/log_fallen.png")

    return {
        "oak": crop_to_alpha(raw_oak),
        "birch": crop_to_alpha(raw_birch),
        "willow": crop_to_alpha(raw_willow),
        "boulder": crop_to_alpha(raw_boulder),
        "slate": crop_to_alpha(raw_slate),
    }


# =============================================================================
# 2. HIGH-RES TRAVELER CHARACTER SPRITESHEET (96x96 per frame, 8 dirs x 7 anims)
# =============================================================================
DIRECTIONS = [
    "down",        # 0: S
    "down_right",  # 1: SE
    "right",       # 2: E
    "up_right",    # 3: NE
    "up",          # 4: N
    "up_left",     # 5: NW
    "left",        # 6: W
    "down_left",   # 7: SW
]

ANIMATIONS = [
    ("idle", 4),
    ("walk", 6),
    ("run", 6),
    ("axe", 6),
    ("pickaxe", 6),
    ("water", 6),
    ("interact", 4),
]


def normalize_pose(im: Image.Image, target_h: int = 80) -> Image.Image:
    cropped = crop_to_alpha(im)
    cw, ch = cropped.size
    scale = target_h / float(ch)
    nw = max(1, int(round(cw * scale)))
    nh = target_h
    return cropped.resize((nw, nh), Image.Resampling.NEAREST)


def animate_pose_frame(
    base_pose: Image.Image,
    alt_pose: Image.Image,
    dir_name: str,
    anim_name: str,
    frame_idx: int,
    total_frames: int,
) -> Image.Image:
    """Synthesizes a 96x96 frame from the extracted AI Traveler poses with limb stride, cloak sway, and tool overlays."""
    canvas = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    dx = -1 if "left" in dir_name else (1 if "right" in dir_name else 0)
    dy = -1 if "up" in dir_name else (1 if "down" in dir_name else 0)

    # Isometric ground shadow under traveler's boots
    shadow_scale = 1.0
    if anim_name in ("walk", "run") and frame_idx in (1, 4):
        shadow_scale = 0.88
    srx = int(18 * shadow_scale)
    sry = int(8 * shadow_scale)
    draw.ellipse([48 - srx, 84 - sry, 48 + srx, 84 + sry], fill=(12, 16, 26, 105))

    # Choose base pose (for walk/run, alternate with alt_pose if available)
    src = base_pose
    if anim_name in ("walk", "run") and alt_pose is not None and (frame_idx % 3 == 1):
        src = alt_pose
    elif anim_name == "interact" and alt_pose is not None:
        src = alt_pose

    pw, ph = src.size
    split_y = int(ph * 0.66)  # Upper body vs boots/legs
    upper = src.crop((0, 0, pw, split_y))
    lower = src.crop((0, split_y, pw, ph))

    bob_y = 0
    lean_x = 0
    stride_shift = 0
    cloak_flare = 0

    if anim_name == "idle":
        bob_y = 1 if frame_idx in (1, 2) else 0
    elif anim_name == "walk":
        bob_table = [0, -2, -1, 0, -2, -1]
        stride_table = [-2, -1, 1, 2, 1, -1]
        bob_y = bob_table[frame_idx % 6]
        stride_shift = stride_table[frame_idx % 6]
    elif anim_name == "run":
        bob_table = [-1, -3, -1, -1, -3, -1]
        stride_table = [-4, -2, 2, 4, 2, -2]
        bob_y = bob_table[frame_idx % 6]
        stride_shift = stride_table[frame_idx % 6]
        lean_x = dx * 2
        cloak_flare = 1 if frame_idx % 2 == 0 else -1
        # Dust puffs behind boots when sprinting
        if frame_idx in (1, 2, 4, 5):
            dust_x = 48 - (dx if dx != 0 else 1) * (14 + (frame_idx % 2) * 5)
            dust_y = 82 - dy * 3 - (frame_idx % 2) * 2
            draw.ellipse([dust_x - 5, dust_y - 4, dust_x + 5, dust_y + 4], fill=(228, 218, 196, 175))
            draw.ellipse([dust_x - 3, dust_y - 6, dust_x + 3, dust_y - 1], fill=(245, 238, 220, 145))
    elif anim_name in ("axe", "pickaxe"):
        if frame_idx in (0, 1):
            bob_y = -2
            lean_x = -dx * 2
        elif frame_idx in (2, 3, 4):
            bob_y = 2
            lean_x = dx * 3
    elif anim_name == "water":
        bob_y = 1 if frame_idx in (1, 2, 3, 4) else 0
        lean_x = dx * 1
    elif anim_name == "interact":
        jump_table = [0, -3, -4, -1]
        bob_y = jump_table[frame_idx % 4]

    base_x = (96 - pw) // 2 + lean_x
    base_y = 86 - ph + bob_y

    # Animate legs (left half vs right half of lower body) for walk/run cycles
    if stride_shift != 0:
        lw_half = pw // 2
        leg_l = lower.crop((0, 0, lw_half, ph - split_y))
        leg_r = lower.crop((lw_half, 0, pw, ph - split_y))
        if dx != 0:
            # Horizontal/diagonal stride
            canvas.alpha_composite(leg_l, (base_x + stride_shift, base_y + split_y - abs(stride_shift) // 2))
            canvas.alpha_composite(leg_r, (base_x + lw_half - stride_shift, base_y + split_y - abs(stride_shift) // 2))
        else:
            # Vertical stride (alternating boot lift)
            lift_l = -3 if stride_shift > 0 else 1
            lift_r = -3 if stride_shift < 0 else 1
            canvas.alpha_composite(leg_l, (base_x, base_y + split_y + lift_l))
            canvas.alpha_composite(leg_r, (base_x + lw_half, base_y + split_y + lift_r))
    else:
        canvas.alpha_composite(lower, (base_x, base_y + split_y))

    # Composite upper body (head, hood, cloak, backpack)
    canvas.alpha_composite(upper, (base_x, base_y + cloak_flare))

    # Draw high-res isometric tool / action effects
    aim_x = dx if dx != 0 else 0
    aim_y = dy if dy != 0 else (1 if dx == 0 else 0)
    hand_x = 48 + aim_x * 12 + lean_x
    hand_y = 52 + aim_y * 6 + bob_y

    if anim_name in ("axe", "pickaxe"):
        if frame_idx in (0, 1):
            # Raised overhead windup
            hx, hy = 48 - aim_x * 4, 24 + bob_y
            draw.line([(hand_x, hand_y - 6), (hx, hy)], fill=(42, 26, 16, 255), width=5)
            draw.line([(hand_x, hand_y - 6), (hx, hy)], fill=(184, 126, 72, 255), width=3)
            if anim_name == "axe":
                draw.polygon([(hx - 8, hy - 6), (hx + 8, hy - 2), (hx + 6, hy + 8), (hx - 6, hy + 4)], fill=(210, 224, 238, 255), outline=(28, 32, 42, 255))
            else:
                draw.line([(hx - 10, hy - 4), (hx + 10, hy + 4)], fill=(220, 232, 245, 255), width=4)
        elif frame_idx in (2, 3, 4):
            reach = 22 if frame_idx == 2 else 26
            tx = 48 + aim_x * reach + (8 if aim_x == 0 else 0)
            ty = 52 + aim_y * reach
            draw.line([(hand_x, hand_y), (tx, ty)], fill=(42, 26, 16, 255), width=5)
            draw.line([(hand_x, hand_y), (tx, ty)], fill=(196, 138, 82, 255), width=3)
            if anim_name == "axe":
                draw.polygon([(tx - 7, ty - 7), (tx + 9, ty - 4), (tx + 7, ty + 8), (tx - 5, ty + 5)], fill=(225, 238, 250, 255), outline=(28, 32, 42, 255))
            else:
                draw.line([(tx - aim_y * 9, ty + aim_x * 9), (tx + aim_y * 9, ty - aim_x * 9)], fill=(225, 238, 250, 255), width=4)

            # High-res pixel slash arc & impact sparks
            if frame_idx in (2, 3):
                angle_deg = int(round(math.degrees(math.atan2(aim_y, aim_x if aim_x != 0 else 0.2))))
                arc_box = [24, 26, 72, 74]
                draw.arc(arc_box, start=angle_deg - 48, end=angle_deg + 48, fill=(220, 242, 255, 195), width=2)
            if frame_idx == 4:
                spark_col = (255, 225, 85, 255) if anim_name == "pickaxe" else (218, 168, 102, 255)
                for ox, oy in [(-8, -6), (7, -5), (-5, 8), (9, 6), (0, -10)]:
                    draw.rectangle([tx + ox - 2, ty + oy - 2, tx + ox + 2, ty + oy + 2], fill=spark_col)

    elif anim_name == "water":
        wx = 48 + (aim_x if aim_x != 0 else 1) * 18
        wy = 54 + aim_y * 12
        # Copper/Blue Explorer Watering Vessel
        draw.rectangle([wx - 8, wy - 6, wx + 8, wy + 7], fill=(58, 126, 188, 255), outline=(24, 30, 44, 255), width=2)
        draw.rectangle([wx - 6, wy - 4, wx + 6, wy - 1], fill=(102, 178, 238, 255))
        spout_x = wx + (aim_x if aim_x != 0 else 1) * 12
        spout_y = wy + aim_y * 6
        draw.line([(wx, wy), (spout_x, spout_y)], fill=(185, 205, 225, 255), width=3)
        if frame_idx in (1, 2, 3, 4):
            for di in range(5):
                drop_x = spout_x + (aim_x if aim_x != 0 else 1) * (4 + di * 3) + ((di % 2) * 3 - 1)
                drop_y = spout_y + aim_y * 3 + ((frame_idx * 3 + di * 4) % 14)
                draw.ellipse([drop_x - 2, drop_y - 2, drop_x + 2, drop_y + 3], fill=(135, 225, 255, 235))

    elif anim_name == "interact":
        if frame_idx in (1, 2):
            for sx, sy in [(30, 14), (48, 8), (66, 14), (24, 26), (72, 26)]:
                draw.ellipse([sx - 3, sy - 3, sx + 3, sy + 3], fill=(255, 232, 98, 255))
                draw.point((sx, sy), fill=(255, 255, 255, 255))

    return canvas


def build_traveler_spritesheet() -> None:
    print("Building High-Res Traveler 8-Directional Spritesheet (96x96 px per frame)...")
    front_all = remove_white_bg_floodfill(Image.open("assets/ai_raw/traveler_front_iso.png"))
    back_iso = remove_white_bg_floodfill(Image.open("assets/ai_raw/traveler_back_iso.png"))
    side_iso = remove_white_bg_floodfill(Image.open("assets/ai_raw/traveler_side_iso.png"))

    # Slice the 3 poses from traveler_front_iso.png
    pose_front_walk = normalize_pose(front_all.crop((260, 60, 534, 725)), target_h=78)
    pose_front_staff = normalize_pose(front_all.crop((535, 60, 872, 725)), target_h=78)
    pose_back_left = normalize_pose(front_all.crop((875, 60, 1145, 725)), target_h=78)

    pose_back_right = normalize_pose(back_iso, target_h=78)
    pose_side_right = normalize_pose(side_iso, target_h=78)

    # Flipped counterparts for full 8-direction coverage
    pose_front_left = pose_front_walk.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    pose_front_left_staff = pose_front_staff.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    pose_side_left = pose_side_right.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    pose_back_right_alt = pose_back_left.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    pose_back_left_lantern = pose_back_right.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    dir_poses = {
        "down":       (pose_front_walk, pose_front_staff),
        "down_right": (pose_front_walk, pose_front_staff),
        "right":      (pose_side_right, pose_front_staff),
        "up_right":   (pose_back_right, pose_back_right_alt),
        "up":         (pose_back_left, pose_back_right),
        "up_left":    (pose_back_left_lantern, pose_back_left),
        "left":       (pose_side_left, pose_front_left_staff),
        "down_left":  (pose_front_left, pose_front_left_staff),
    }

    cols = 6
    rows = len(ANIMATIONS) * len(DIRECTIONS)  # 56 rows
    frame_size = 96
    sheet = Image.new("RGBA", (cols * frame_size, rows * frame_size), (0, 0, 0, 0))
    showcase = Image.new("RGBA", (len(DIRECTIONS) * frame_size, len(ANIMATIONS) * frame_size), (26, 32, 44, 255))
    sc_draw = ImageDraw.Draw(showcase)

    row_idx = 0
    for a_idx, (anim_name, frame_count) in enumerate(ANIMATIONS):
        sample_f = 2 if anim_name in ("axe", "pickaxe", "water") else (1 if anim_name != "idle" else 0)
        for d_idx, dir_name in enumerate(DIRECTIONS):
            base_p, alt_p = dir_poses[dir_name]
            for col_idx in range(cols):
                eff_f = col_idx % frame_count
                frame_im = animate_pose_frame(base_p, alt_p, dir_name, anim_name, eff_f, frame_count)
                sheet.alpha_composite(frame_im, (col_idx * frame_size, row_idx * frame_size))
                if col_idx == sample_f:
                    cx0, cy0 = d_idx * frame_size, a_idx * frame_size
                    bg_col = (36, 44, 58, 255) if (a_idx + d_idx) % 2 == 0 else (28, 35, 48, 255)
                    sc_draw.rectangle([cx0 + 1, cy0 + 1, cx0 + frame_size - 2, cy0 + frame_size - 2], fill=bg_col)
                    showcase.alpha_composite(frame_im, (cx0, cy0))
            row_idx += 1

    sheet.save("assets/sprites/player_spritesheet.png")
    showcase.save("assets/sprites/player_8dir_showcase.png")

    # Project icon (128x128) featuring the AI Traveler
    icon = Image.new("RGBA", (128, 128), (34, 88, 148, 255))
    idraw = ImageDraw.Draw(icon)
    idraw.ellipse([12, 76, 116, 118], fill=(218, 188, 126, 255))
    idraw.ellipse([18, 78, 110, 114], fill=(76, 152, 72, 255))
    hero_icon = animate_pose_frame(pose_front_staff, pose_front_walk, "down_right", "idle", 0, 4)
    icon.alpha_composite(hero_icon, (16, 16))
    icon.save("icon.png")
    print(f"Saved assets/sprites/player_spritesheet.png ({sheet.size[0]}x{sheet.size[1]})")


# =============================================================================
# 3. HIGH-RES ISOMETRIC DIAMOND TILESET (64x32 diamond in 64x40 cell, 16x5 grid)
# =============================================================================
def build_isometric_tileset(ai_sources: dict) -> None:
    print("Building High-Res Isometric Diamond Tileset (64x40 cells, 1024x200 atlas)...")
    TILE_W = 64
    TILE_H = 32
    SKIRT_H = 8
    CELL_H = TILE_H + SKIRT_H  # 40
    COLS, ROWS = 16, 5

    atlas = Image.new("RGBA", (COLS * TILE_W, ROWS * CELL_H), (0, 0, 0, 0))
    rng = random.Random(20261002)

    # Prebuild diamond mask (64x32) and 3D skirt masks (left skirt & right skirt)
    diamond_mask = np.zeros((CELL_H, TILE_W), dtype=bool)
    left_skirt_mask = np.zeros((CELL_H, TILE_W), dtype=bool)
    right_skirt_mask = np.zeros((CELL_H, TILE_W), dtype=bool)
    top_edge_mask = np.zeros((CELL_H, TILE_W), dtype=bool)

    hw = TILE_W / 2.0  # 32.0
    hh = TILE_H / 2.0  # 16.0
    for y in range(CELL_H):
        for x in range(TILE_W):
            dx = abs(x + 0.5 - hw) / hw
            dy = abs(y + 0.5 - hh) / hh
            if y < TILE_H and (dx + dy <= 1.02):
                diamond_mask[y, x] = True
                if dx + dy >= 0.92:
                    top_edge_mask[y, x] = True
            else:
                # Check if below the bottom V of the diamond for the 3D block skirt
                bot_y_at_x = hh + (1.0 - dx) * hh
                if y >= bot_y_at_x - 0.5 and y < bot_y_at_x + SKIRT_H:
                    if x < hw:
                        left_skirt_mask[y, x] = True
                    else:
                        right_skirt_mask[y, x] = True

    def make_iso_tile(
        top_palette: list,
        left_skirt_col: tuple,
        right_skirt_col: tuple,
        dither_scale: int = 2,
        decor_fn=None,
    ) -> Image.Image:
        arr = np.zeros((CELL_H, TILE_W, 4), dtype=np.uint8)
        for y in range(CELL_H):
            for x in range(TILE_W):
                if diamond_mask[y, x]:
                    # Pixel-art clustered noise shading across the isometric diamond
                    n_idx = ((x // dither_scale) * 17 + (y // dither_scale) * 31 + rng.randint(0, 5)) % len(top_palette)
                    col = list(top_palette[n_idx])
                    # Subtle isometric directional lighting (brighter NW, slightly deeper SE)
                    light = int(((hw - x) * 0.18 + (hh - y) * 0.35))
                    col[0] = max(0, min(255, col[0] + light))
                    col[1] = max(0, min(255, col[1] + light))
                    col[2] = max(0, min(255, col[2] + light))
                    arr[y, x] = col
                elif left_skirt_mask[y, x]:
                    arr[y, x] = left_skirt_col
                elif right_skirt_mask[y, x]:
                    arr[y, x] = right_skirt_col

        im = Image.fromarray(arr, "RGBA")
        if decor_fn is not None:
            decor_fn(ImageDraw.Draw(im), im)
        return im

    # Palettes sampled from AI assets
    DEEP_WATER_PAL = [(24, 68, 134, 255), (28, 78, 148, 255), (34, 90, 164, 255), (20, 58, 118, 255)]
    SHALLOW_WATER_PAL = [(44, 118, 184, 255), (52, 132, 198, 255), (64, 148, 212, 255), (38, 106, 170, 255)]
    RIVER_WATER_PAL = [(38, 108, 176, 255), (48, 124, 192, 255), (62, 142, 208, 255), (76, 158, 220, 255)]

    SAND_PAL = [(216, 186, 126, 255), (228, 198, 138, 255), (202, 170, 112, 255), (236, 210, 152, 255)]
    MEADOW_PAL = [(74, 146, 58, 255), (86, 162, 66, 255), (64, 132, 50, 255), (98, 176, 74, 255)]
    FOREST_PAL = [(42, 106, 52, 255), (52, 122, 60, 255), (34, 92, 44, 255), (64, 138, 68, 255)]
    ROAD_PAL = [(148, 112, 76, 255), (162, 124, 86, 255), (132, 98, 66, 255), (174, 138, 96, 255)]
    BIRCH_GRASS_PAL = [(108, 154, 54, 255), (124, 168, 62, 255), (94, 138, 48, 255), (146, 184, 72, 255)]
    SLATE_GROUND_PAL = [(78, 88, 102, 255), (92, 104, 118, 255), (66, 76, 88, 255), (108, 120, 134, 255)]
    WATERED_PAL = [(40, 104, 68, 255), (48, 118, 78, 255), (34, 90, 58, 255), (58, 134, 88, 255)]

    # ROW 0: Water Tiles (Deep, Shallow, River, Lilypads)
    for i in range(4):
        def add_deep_waves(d: ImageDraw.ImageDraw, _im: Image.Image, idx=i):
            for wy in (10, 16, 22):
                wx = 20 + ((idx * 6 + wy) % 18)
                d.line([(wx, wy), (wx + 8, wy - 2)], fill=(92, 158, 224, 210), width=1)
        t = make_iso_tile(DEEP_WATER_PAL, (18, 52, 108, 255), (14, 42, 92, 255), 2, add_deep_waves)
        atlas.alpha_composite(t, (i * TILE_W, 0))

    for i in range(4):
        def add_shallow_waves(d: ImageDraw.ImageDraw, _im: Image.Image, idx=i):
            for wy in (9, 15, 21):
                wx = 18 + ((idx * 5 + wy) % 20)
                d.line([(wx, wy), (wx + 9, wy - 2)], fill=(155, 220, 255, 225), width=1)
        t = make_iso_tile(SHALLOW_WATER_PAL, (32, 88, 148, 255), (26, 74, 128, 255), 2, add_shallow_waves)
        atlas.alpha_composite(t, ((4 + i) * TILE_W, 0))

    for i in range(4):
        def add_river_flow(d: ImageDraw.ImageDraw, _im: Image.Image, idx=i):
            for rx, ry in [(22, 11), (32, 16), (26, 21), (38, 14)]:
                ox = (idx * 3) % 8 - 4
                d.line([(rx + ox, ry), (rx + ox + 7, ry + 3)], fill=(195, 238, 255, 235), width=1)
        t = make_iso_tile(RIVER_WATER_PAL, (30, 84, 142, 255), (24, 70, 122, 255), 2, add_river_flow)
        atlas.alpha_composite(t, ((8 + i) * TILE_W, 0))

    for i in range(4):
        def add_lilypads(d: ImageDraw.ImageDraw, _im: Image.Image, idx=i):
            for lx, ly in [(26, 14), (40, 19)]:
                d.ellipse([lx - 6, ly - 3, lx + 6, ly + 3], fill=(46, 132, 58, 255), outline=(24, 68, 32, 255))
                d.ellipse([lx - 4, ly - 2, lx + 4, ly + 2], fill=(74, 168, 82, 255))
                if idx % 2 == 0 and lx == 26:
                    d.ellipse([lx - 2, ly - 3, lx + 2, ly + 1], fill=(248, 148, 182, 255))
                    d.point((lx, ly - 1), fill=(255, 232, 96, 255))
        t = make_iso_tile(SHALLOW_WATER_PAL, (32, 88, 148, 255), (26, 74, 128, 255), 2, add_lilypads)
        atlas.alpha_composite(t, ((12 + i) * TILE_W, 0))

    # ROW 1: Sand Shore (0..3), Meadow Grass (4..7), Dark Forest Grass (8..11), Cobblestone Road (12..15)
    for i in range(4):
        def add_sand_detail(d: ImageDraw.ImageDraw, _im: Image.Image, idx=i):
            for px, py in [(24 + idx * 3, 14), (38 - idx * 2, 19), (30, 11 + idx)]:
                d.ellipse([px - 2, py - 1, px + 2, py + 1], fill=(184, 154, 102, 255))
        t = make_iso_tile(SAND_PAL, (168, 136, 86, 255), (142, 112, 68, 255), 2, add_sand_detail)
        atlas.alpha_composite(t, (i * TILE_W, CELL_H))

    for i in range(4):
        def add_meadow_tufts(d: ImageDraw.ImageDraw, _im: Image.Image, idx=i):
            for gx, gy in [(22 + idx * 2, 14), (36, 12 + idx), (28, 20), (42 - idx * 2, 17)]:
                d.line([(gx, gy), (gx - 2, gy - 3)], fill=(116, 196, 86, 255), width=1)
                d.line([(gx + 1, gy), (gx + 2, gy - 4)], fill=(134, 212, 98, 255), width=1)
        t = make_iso_tile(MEADOW_PAL, (98, 72, 46, 255), (76, 54, 34, 255), 2, add_meadow_tufts)
        atlas.alpha_composite(t, ((4 + i) * TILE_W, CELL_H))

    for i in range(4):
        def add_forest_moss(d: ImageDraw.ImageDraw, _im: Image.Image, idx=i):
            for mx, my in [(24, 13 + idx), (38, 17), (30 + idx, 21)]:
                d.ellipse([mx - 3, my - 2, mx + 3, my + 2], fill=(74, 156, 78, 255))
                d.point((mx, my - 1), fill=(112, 192, 104, 255))
        t = make_iso_tile(FOREST_PAL, (78, 58, 38, 255), (58, 42, 28, 255), 2, add_forest_moss)
        atlas.alpha_composite(t, ((8 + i) * TILE_W, CELL_H))

    for i in range(4):
        def add_cobble_stones(d: ImageDraw.ImageDraw, _im: Image.Image, idx=i):
            stones = [(24, 13, 5, 3), (35, 11, 6, 3), (29, 18, 6, 3), (41, 17, 5, 3), (22, 19, 4, 2), (34, 23, 5, 2)]
            for sx, sy, srw, srh in stones:
                ox = (idx % 2) * 2 - 1
                d.ellipse([sx + ox - srw, sy - srh, sx + ox + srw, sy + srh], fill=(112, 108, 104, 255), outline=(58, 52, 48, 255))
                d.ellipse([sx + ox - srw + 1, sy - srh + 1, sx + ox + srw - 1, sy + srh - 1], fill=(148, 144, 138, 255))
        t = make_iso_tile(ROAD_PAL, (108, 78, 52, 255), (86, 60, 38, 255), 2, add_cobble_stones)
        atlas.alpha_composite(t, ((12 + i) * TILE_W, CELL_H))

    # ROW 2: Isometric Wooden Bridge (0..3), Watered Soil (4..7), Slate Ground (8..11), Golden Birch Grass (12..15)
    BRIDGE_PAL = [(164, 114, 68, 255), (178, 126, 76, 255), (146, 98, 56, 255), (192, 140, 88, 255)]
    for i in range(4):
        def add_bridge_planks(d: ImageDraw.ImageDraw, _im: Image.Image, idx=i):
            # Draw isometric plank seams & timber rails
            for step in range(-18, 22, 6):
                d.line([(32 + step - 12, 16 + step // 2 - 6), (32 + step + 12, 16 + step // 2 + 6)], fill=(68, 42, 24, 255), width=1)
            # Isometric side timber beams
            d.line([(4, 15), (32, 2)], fill=(214, 164, 106, 255), width=2)
            d.line([(32, 29), (60, 15)], fill=(122, 78, 42, 255), width=2)
        t = make_iso_tile(BRIDGE_PAL, (112, 72, 38, 255), (88, 54, 28, 255), 1, add_bridge_planks)
        atlas.alpha_composite(t, (i * TILE_W, CELL_H * 2))

    for i in range(4):
        def add_water_drops(d: ImageDraw.ImageDraw, _im: Image.Image, idx=i):
            for wx, wy in [(24 + idx * 2, 14), (38, 18), (30, 12)]:
                d.ellipse([wx - 2, wy - 1, wx + 2, wy + 2], fill=(125, 215, 255, 235))
        t = make_iso_tile(WATERED_PAL, (58, 44, 32, 255), (44, 32, 22, 255), 2, add_water_drops)
        atlas.alpha_composite(t, ((4 + i) * TILE_W, CELL_H * 2))

    for i in range(4):
        t = make_iso_tile(SLATE_GROUND_PAL, (54, 62, 72, 255), (42, 48, 58, 255), 2)
        atlas.alpha_composite(t, ((8 + i) * TILE_W, CELL_H * 2))

    for i in range(4):
        def add_golden_leaves(d: ImageDraw.ImageDraw, _im: Image.Image, idx=i):
            for lx, ly in [(22 + idx * 3, 15), (36, 13 + idx), (30, 20), (42 - idx * 2, 16)]:
                d.ellipse([lx - 2, ly - 1, lx + 2, ly + 1], fill=(238, 192, 58, 255))
        t = make_iso_tile(BIRCH_GRASS_PAL, (88, 66, 42, 255), (68, 50, 30, 255), 2, add_golden_leaves)
        atlas.alpha_composite(t, ((12 + i) * TILE_W, CELL_H * 2))

    # ROW 3: Isometric Ground Decor Overlays (Transparent background!)
    flower_sets = [
        ((235, 58, 64, 255), (255, 220, 72, 255)),   # Red poppies
        ((250, 210, 52, 255), (230, 138, 28, 255)),  # Sunbursts
        ((105, 168, 248, 255), (245, 248, 255, 255)),# Blue lupines
        ((248, 248, 252, 255), (250, 204, 64, 255)), # White daisies
    ]
    for i, (petal_c, center_c) in enumerate(flower_sets):
        t = Image.new("RGBA", (TILE_W, CELL_H), (0, 0, 0, 0))
        d = ImageDraw.Draw(t)
        for fx, fy in [(22, 14), (34, 11), (28, 19), (42, 16), (33, 22)]:
            d.line([(fx, fy + 1), (fx, fy + 5)], fill=(48, 122, 48, 255), width=1)
            d.ellipse([fx - 3, fy - 2, fx + 3, fy + 2], fill=petal_c, outline=(28, 32, 28, 220))
            d.point((fx, fy), fill=center_c)
        atlas.alpha_composite(t, (i * TILE_W, CELL_H * 3))

    for i in range(4):
        t = Image.new("RGBA", (TILE_W, CELL_H), (0, 0, 0, 0))
        d = ImageDraw.Draw(t)
        for gx, gy in [(22, 17), (32, 14), (40, 19), (28, 22)]:
            d.line([(gx, gy), (gx - 4, gy - 7)], fill=(48, 124, 52, 255), width=1)
            d.line([(gx + 1, gy), (gx + 1, gy - 8)], fill=(78, 164, 68, 255), width=1)
            d.line([(gx + 2, gy), (gx + 6, gy - 6)], fill=(112, 194, 86, 255), width=1)
        atlas.alpha_composite(t, ((4 + i) * TILE_W, CELL_H * 3))

    for i in range(4):
        t = Image.new("RGBA", (TILE_W, CELL_H), (0, 0, 0, 0))
        d = ImageDraw.Draw(t)
        for mx, my in [(24, 15), (37, 18), (31, 12)]:
            d.rectangle([mx - 1, my, mx + 1, my + 4], fill=(242, 230, 208, 255))
            d.ellipse([mx - 4, my - 3, mx + 4, my + 1], fill=(218, 52, 48, 255), outline=(32, 20, 24, 255))
            d.point((mx - 1, my - 2), fill=(255, 248, 235, 255))
            d.point((mx + 2, my - 1), fill=(255, 248, 235, 255))
        atlas.alpha_composite(t, ((8 + i) * TILE_W, CELL_H * 3))

    for i in range(4):
        t = Image.new("RGBA", (TILE_W, CELL_H), (0, 0, 0, 0))
        d = ImageDraw.Draw(t)
        for px, py in [(23, 15), (36, 13), (31, 20), (42, 17)]:
            d.ellipse([px - 4, py - 2, px + 4, py + 2], fill=(134, 144, 156, 255), outline=(44, 50, 58, 255))
            d.point((px - 1, py - 1), fill=(205, 215, 228, 255))
        atlas.alpha_composite(t, ((12 + i) * TILE_W, CELL_H * 3))

    # ROW 4: Additional Biome Varieties (Clover Meadow, Mossy Highland, Autumn Forest)
    for i in range(16):
        pal = BIRCH_GRASS_PAL if i >= 8 else (SLATE_GROUND_PAL if i >= 4 else MEADOW_PAL)
        t = make_iso_tile(pal, (82, 62, 40, 255), (64, 48, 30, 255), 2)
        atlas.alpha_composite(t, (i * TILE_W, CELL_H * 4))

    atlas.save("assets/tilesets/world_tileset.png")
    print(f"Saved assets/tilesets/world_tileset.png ({atlas.size[0]}x{atlas.size[1]})")


if __name__ == "__main__":
    sources = build_world_objects()
    build_traveler_spritesheet()
    build_isometric_tileset(sources)
    print("All High-Res Isometric AI Pixel-Art assets built successfully!")
