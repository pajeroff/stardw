#!/usr/bin/env python3
"""
Builds High-Clarity 1:1 Pixel-Art Isometric Assets for Godot 4.7 (Stardew Valley Style):
  - True 1:1 Pixel Resolution (PIXEL_SCALE = 1):
    NO blocky 2x2 downsampling and NO Gaussian blur — every pixel is a crisp 1x1 texel rendered
    with Nearest filtering in Godot.
  - Readable, Expressive Stardew-Style Explorer (assets/sprites/player_spritesheet.png, 96x96 frames):
    74px tall at full 1:1 pixel resolution so facial features (eyes, hair, collar, vest, belt, boots)
    are 100% clear and readable across all 8 directions and 7 animations (8 frames each).
  - 19 Natural World Objects (8 Trees + 8 Pure Natural Rocks without ore + 3 Dedicated Forest Props):
    Built from clean Stardew-style sprites (including dedicated sdv_bush_berry.png, sdv_log_fallen.png,
    and sdv_tree_stump.png) at full 1:1 resolution with harmonized natural colors and crisp silhouettes.
  - Seamless 2:1 Isometric Terrain Tileset (assets/tilesets/world_tileset.png, 1024x200, 64x40 cells):
    Flush 64x32 isometric diamonds (NO protruding cliff skirts on ground tiles!) with rich multi-octave
    1x1 pixel-art grass tufts, rounded river-stone cobblestone paths, oak plank bridges, and shimmering water.
"""

import math
import os
from collections import deque
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

os.makedirs("assets/sprites", exist_ok=True)
os.makedirs("assets/tilesets", exist_ok=True)
os.makedirs("assets/objects", exist_ok=True)
os.makedirs("assets/ui", exist_ok=True)

OUTLINE_RGB = (42, 26, 18)


# =============================================================================
# 0. CLEAN FOREGROUND EXTRACTION & 1:1 CRISP SPRITE FITTING
# =============================================================================
def extract_clean_rgba(
    im: Image.Image,
    white_thresh: int = 232,
    chroma_thresh: int = 28,
    min_hole_area: int = 85,
    strip_floor_shadow: bool = False,
) -> Image.Image:
    """
    Removes exterior white background and large enclosed white holes between branches/roots,
    producing a clean RGBA image with crisp alpha edges and zero white halo.
    """
    rgba = np.array(im.convert("RGBA"), dtype=np.uint8)
    h, w, _ = rgba.shape
    r = rgba[:, :, 0].astype(np.int16)
    g = rgba[:, :, 1].astype(np.int16)
    b = rgba[:, :, 2].astype(np.int16)

    min_c = np.minimum(np.minimum(r, g), b)
    max_c = np.maximum(np.maximum(r, g), b)
    is_white = (min_c >= white_thresh) & ((max_c - min_c) <= chroma_thresh)

    if strip_floor_shadow:
        yy_grid = np.arange(h)[:, None]
        is_taupe_shadow = (yy_grid > int(h * 0.62)) & (min_c >= 68) & ((max_c - min_c) <= 50)
        is_white = is_white | is_taupe_shadow

    visited = np.zeros((h, w), dtype=bool)
    bg_mask = np.zeros((h, w), dtype=bool)

    for sy in range(h):
        for sx in range(w):
            if is_white[sy, sx] and not visited[sy, sx]:
                comp = []
                touches_border = False
                q = deque([(sy, sx)])
                visited[sy, sx] = True
                while q:
                    cy, cx = q.popleft()
                    comp.append((cy, cx))
                    if cy == 0 or cy == h - 1 or cx == 0 or cx == w - 1:
                        touches_border = True
                    for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                        if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and is_white[ny, nx]:
                            visited[ny, nx] = True
                            q.append((ny, nx))
                if touches_border or len(comp) >= min_hole_area:
                    for py, px in comp:
                        bg_mask[py, px] = True

    # Decontaminate 1px boundary next to background so white never fringes the outline
    near_bg = np.zeros((h, w), dtype=bool)
    near_bg[1:, :] |= bg_mask[:-1, :]
    near_bg[:-1, :] |= bg_mask[1:, :]
    near_bg[:, 1:] |= bg_mask[:, :-1]
    near_bg[:, :-1] |= bg_mask[:, 1:]
    fringe = near_bg & (~bg_mask) & (min_c >= 195) & ((max_c - min_c) <= 38)
    bg_mask |= fringe

    rgba[bg_mask, 3] = 0
    return Image.fromarray(rgba, "RGBA")


def crop_to_alpha(im: Image.Image) -> Image.Image:
    bbox = im.getbbox()
    if not bbox:
        return im
    return im.crop(bbox)


def resize_crisp_1to1(
    im: Image.Image,
    target_w: int,
    target_h: int,
    sat_factor: float = 1.0,
    contrast_factor: float = 1.04,
    add_outline: bool = False,
) -> Image.Image:
    """
    Resizes an RGBA sprite to exact (target_w, target_h) at 1:1 pixel resolution:
      - Premultiplies RGB before BOX/LANCZOS resampling so background never bleeds into edges
      - Applies subtle UnsharpMask on RGB so 1x1 pixel details (eyes, leaves, bark, stone facets) are sharp
      - Thresholds alpha cleanly (>= 105 -> 255, < 105 -> 0) so there is ZERO blurry semi-transparent halo
        when rendered with TEXTURE_FILTER_NEAREST in Godot!
    """
    rgba = im.convert("RGBA")
    arr = np.array(rgba, dtype=np.float32)
    alpha = arr[:, :, 3:4] / 255.0

    pre_rgb = arr[:, :, :3] * alpha
    pre_im = Image.fromarray(np.clip(pre_rgb, 0, 255).astype(np.uint8), "RGB")
    a_im = Image.fromarray(arr[:, :, 3].astype(np.uint8), "L")

    small_pre = pre_im.resize((target_w, target_h), Image.Resampling.LANCZOS)
    small_a = a_im.resize((target_w, target_h), Image.Resampling.LANCZOS)

    s_pre_arr = np.array(small_pre, dtype=np.float32)
    s_a_arr = np.array(small_a, dtype=np.float32) / 255.0

    solid = s_a_arr >= 0.42
    rgb_unpre = np.where(
        s_a_arr[:, :, None] > 0.05,
        s_pre_arr / np.maximum(s_a_arr[:, :, None], 0.05),
        0.0,
    )
    rgb_im = Image.fromarray(np.clip(rgb_unpre, 0, 255).astype(np.uint8), "RGB")
    if abs(sat_factor - 1.0) > 0.01:
        rgb_im = ImageEnhance.Color(rgb_im).enhance(sat_factor)
    if abs(contrast_factor - 1.0) > 0.01:
        rgb_im = ImageEnhance.Contrast(rgb_im).enhance(contrast_factor)
    rgb_im = rgb_im.filter(ImageFilter.UnsharpMask(radius=0.75, percent=115, threshold=3))

    out = np.zeros((target_h, target_w, 4), dtype=np.uint8)
    rgb_final = np.array(rgb_im, dtype=np.uint8)
    out[solid, :3] = rgb_final[solid]
    out[solid, 3] = 255

    if add_outline:
        is_solid = out[:, :, 3] > 0
        for y in range(target_h):
            for x in range(target_w):
                if is_solid[y, x]:
                    if (
                        y == 0 or y == target_h - 1 or x == 0 or x == target_w - 1
                        or not is_solid[y - 1, x] or not is_solid[y + 1, x]
                        or not is_solid[y, x - 1] or not is_solid[y, x + 1]
                    ):
                        # Subtle dark-brown edge darkening for un-outlined rocks
                        out[y, x, 0] = int((int(out[y, x, 0]) * 45 + OUTLINE_RGB[0] * 55) // 100)
                        out[y, x, 1] = int((int(out[y, x, 1]) * 45 + OUTLINE_RGB[1] * 55) // 100)
                        out[y, x, 2] = int((int(out[y, x, 2]) * 45 + OUTLINE_RGB[2] * 55) // 100)

    return Image.fromarray(out, "RGBA")


def fit_object_1to1(
    im: Image.Image,
    target_w: int,
    target_h: int,
    bottom_pad: int = 6,
    shadow_rx: int = 28,
    shadow_ry: int = 12,
    shadow_y_off: int = -8,
    sat_factor: float = 1.0,
    contrast_factor: float = 1.04,
    add_outline: bool = False,
) -> Image.Image:
    """
    Fits an object onto (target_w x target_h) at full 1:1 pixel resolution with a clean
    pixel-art ground shadow ellipse.
    """
    cropped = crop_to_alpha(im)
    cw, ch = cropped.size

    avail_w = target_w - 8
    avail_h = target_h - bottom_pad - 4
    scale = min(avail_w / float(cw), avail_h / float(ch))
    new_w = max(1, int(round(cw * scale)))
    new_h = max(1, int(round(ch * scale)))

    resized = resize_crisp_1to1(
        cropped,
        new_w,
        new_h,
        sat_factor=sat_factor,
        contrast_factor=contrast_factor,
        add_outline=add_outline,
    )

    canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(canvas)
    scx = target_w // 2
    scy = target_h - bottom_pad + shadow_y_off
    s_draw.ellipse(
        [scx - shadow_rx, scy - shadow_ry, scx + shadow_rx, scy + shadow_ry],
        fill=(18, 26, 32, 82),
    )

    paste_x = (target_w - new_w) // 2
    paste_y = target_h - bottom_pad - new_h
    canvas.alpha_composite(resized, (paste_x, paste_y))
    return canvas


def harmonize_willow_palette(im: Image.Image) -> Image.Image:
    """
    Shifts the overly cyan/mint hue of sdv_tree_willow.png toward a warm, natural
    Stardew Valley sage-emerald green while preserving its bark and dark outlines.
    """
    arr = np.array(im.convert("RGBA"), dtype=np.float32)
    r, g, b, a = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]
    # Foliage mask: green is dominant over red
    is_leaf = (a > 0) & (g > r * 1.08)
    # Warm up red channel slightly, tone down excessive blue/cyan, and keep natural green
    arr[is_leaf, 0] = np.clip(r[is_leaf] * 1.12 + 14.0, 0, 255)
    arr[is_leaf, 1] = np.clip(g[is_leaf] * 0.90, 0, 255)
    arr[is_leaf, 2] = np.clip(b[is_leaf] * 0.68, 0, 255)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def harmonize_oak_palette(im: Image.Image) -> Image.Image:
    """
    Softens overly neon lime highlights on sdv_tree_oak.png into warm Stardew forest green.
    """
    arr = np.array(im.convert("RGBA"), dtype=np.float32)
    r, g, b, a = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]
    is_leaf = (a > 0) & (g > r * 1.05)
    arr[is_leaf, 0] = np.clip(r[is_leaf] * 1.08 + 10.0, 0, 255)
    arr[is_leaf, 1] = np.clip(g[is_leaf] * 0.88, 0, 255)
    arr[is_leaf, 2] = np.clip(b[is_leaf] * 0.92 + 8.0, 0, 255)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def tint_foliage_warm_cherry(im: Image.Image) -> Image.Image:
    arr = np.array(im.convert("RGBA"), dtype=np.float32)
    r, g, b, a = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]
    is_leaf = (a > 0) & (g > r * 0.92) & (g > 45)
    lum = 0.28 * r + 0.58 * g + 0.14 * b
    arr[is_leaf, 0] = np.clip(lum[is_leaf] * 1.32 + 52.0, 0, 255)
    arr[is_leaf, 1] = np.clip(lum[is_leaf] * 0.72 + 24.0, 0, 255)
    arr[is_leaf, 2] = np.clip(lum[is_leaf] * 0.96 + 42.0, 0, 255)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


# =============================================================================
# 1. BUILD ALL 19 WORLD OBJECTS (8 TREES + 8 PURE ROCKS + 3 DEDICATED PROPS)
# =============================================================================
def build_world_objects() -> None:
    print("Building 19 high-clarity 1:1 pixel-art world objects...")

    # --- 8 Isometric Trees ---
    oak_raw = harmonize_oak_palette(extract_clean_rgba(Image.open("assets/ai_raw/sdv_tree_oak.png"), min_hole_area=70))
    fit_object_1to1(oak_raw, 156, 186, 8, 44, 18, -10, sat_factor=0.96).save("assets/objects/tree_oak.png")

    willow_raw = harmonize_willow_palette(extract_clean_rgba(Image.open("assets/ai_raw/sdv_tree_willow.png"), min_hole_area=70))
    fit_object_1to1(willow_raw, 168, 192, 8, 50, 20, -12, sat_factor=0.95).save("assets/objects/tree_willow.png")

    pine_raw = extract_clean_rgba(Image.open("assets/ai_raw/sdv_tree_pine.png"), min_hole_area=70)
    fit_object_1to1(pine_raw, 136, 198, 8, 38, 16, -10, sat_factor=1.02).save("assets/objects/tree_pine.png")

    birch_raw = extract_clean_rgba(Image.open("assets/ai_raw/sdv_tree_birch.png"), min_hole_area=65)
    fit_object_1to1(birch_raw, 140, 190, 8, 36, 15, -10, sat_factor=1.0).save("assets/objects/tree_birch.png")

    maple_raw = extract_clean_rgba(Image.open("assets/ai_raw/sdv_tree_maple.png"), min_hole_area=70)
    fit_object_1to1(maple_raw, 154, 188, 8, 44, 18, -10, sat_factor=1.02).save("assets/objects/tree_maple.png")

    cherry_raw = tint_foliage_warm_cherry(oak_raw)
    fit_object_1to1(cherry_raw, 156, 186, 8, 44, 18, -10, sat_factor=1.0).save("assets/objects/tree_cherry.png")

    cedar_raw = extract_clean_rgba(Image.open("assets/ai_raw/iso_tree_ancient_fir.png"), min_hole_area=70)
    fit_object_1to1(cedar_raw, 144, 204, 8, 40, 17, -10, sat_factor=1.05, add_outline=True).save("assets/objects/tree_cedar.png")

    poplar_raw = extract_clean_rgba(Image.open("assets/ai_raw/iso_tree_poplar.png"), min_hole_area=70)
    fit_object_1to1(poplar_raw, 118, 204, 8, 32, 14, -9, sat_factor=1.04, add_outline=True).save("assets/objects/tree_poplar.png")

    # --- 8 Pure Natural Isometric Rocks (ZERO ORE) ---
    boulder = extract_clean_rgba(Image.open("assets/ai_raw/iso_rock_boulder.png"))
    fit_object_1to1(boulder, 88, 72, 6, 33, 14, -9, sat_factor=0.95, add_outline=True).save("assets/objects/rock_large.png")

    slate = extract_clean_rgba(Image.open("assets/ai_raw/iso_rock_slate.png"))
    fit_object_1to1(slate, 84, 68, 6, 30, 13, -8, sat_factor=0.98, add_outline=True).save("assets/objects/rock_slate.png")

    sandstone = extract_clean_rgba(Image.open("assets/ai_raw/iso_rock_sandstone.png"))
    fit_object_1to1(sandstone, 88, 70, 6, 32, 14, -8, sat_factor=0.98, add_outline=True).save("assets/objects/rock_sandstone.png")

    mossy_cluster = extract_clean_rgba(Image.open("assets/ai_raw/iso_rock_mossy_cluster.png"))
    fit_object_1to1(mossy_cluster, 82, 62, 6, 30, 12, -8, sat_factor=0.95, add_outline=True).save("assets/objects/rock_river.png")

    limestone = extract_clean_rgba(Image.open("assets/ai_raw/iso_rock_limestone.png"))
    fit_object_1to1(limestone, 84, 66, 6, 30, 13, -8, sat_factor=0.98, add_outline=True).save("assets/objects/rock_limestone.png")

    basalt = extract_clean_rgba(Image.open("assets/ai_raw/iso_rock_basalt.png"))
    fit_object_1to1(basalt, 84, 72, 6, 30, 13, -8, sat_factor=0.98, add_outline=True).save("assets/objects/rock_basalt.png")

    flat_rock = extract_clean_rgba(Image.open("assets/ai_raw/iso_rock_flat_stepping.png"))
    fit_object_1to1(flat_rock, 78, 52, 5, 28, 11, -7, sat_factor=0.96, add_outline=True).save("assets/objects/rock_flat.png")

    fit_object_1to1(mossy_cluster, 58, 46, 5, 21, 9, -6, sat_factor=0.95, add_outline=True).save("assets/objects/rock_small.png")

    # --- 3 Dedicated Isometric Forest Props (Stump, Berry Bush, Fallen Log) ---
    stump_raw = extract_clean_rgba(Image.open("assets/ai_raw/sdv_tree_stump.png"), min_hole_area=60)
    fit_object_1to1(stump_raw, 64, 52, 5, 23, 10, -6, sat_factor=1.0).save("assets/objects/tree_stump.png")

    bush_raw = extract_clean_rgba(Image.open("assets/ai_raw/sdv_bush_berry.png"), min_hole_area=45)
    fit_object_1to1(bush_raw, 68, 60, 6, 25, 11, -7, sat_factor=1.0).save("assets/objects/bush_berry.png")

    log_raw = extract_clean_rgba(Image.open("assets/ai_raw/sdv_log_fallen.png"), min_hole_area=60)
    fit_object_1to1(log_raw, 96, 56, 6, 34, 12, -6, sat_factor=1.0).save("assets/objects/log_fallen.png")


# =============================================================================
# 2. HIGH-CLARITY 1:1 STARDEW EXPLORER (96x96 FRAMES, 74PX TALL, READABLE FACE!)
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
    ("idle", 8),
    ("walk", 8),
    ("run", 8),
    ("axe", 8),
    ("pickaxe", 8),
    ("water", 8),
    ("interact", 8),
]


def bilinear_warp_rgba(arr: np.ndarray, src_x: np.ndarray, src_y: np.ndarray) -> np.ndarray:
    h, w, _ = arr.shape
    x0 = np.floor(src_x).astype(np.int32)
    y0 = np.floor(src_y).astype(np.int32)
    x1 = x0 + 1
    y1 = y0 + 1

    wx = (src_x - x0)[:, :, None]
    wy = (src_y - y0)[:, :, None]

    valid = (x0 >= 0) & (x1 < w) & (y0 >= 0) & (y1 < h)
    x0_c = np.clip(x0, 0, w - 1)
    x1_c = np.clip(x1, 0, w - 1)
    y0_c = np.clip(y0, 0, h - 1)
    y1_c = np.clip(y1, 0, h - 1)

    f = arr.astype(np.float32)
    f_pre = f.copy()
    alpha_norm = f[:, :, 3:4] / 255.0
    f_pre[:, :, :3] *= alpha_norm

    p00 = f_pre[y0_c, x0_c]
    p10 = f_pre[y0_c, x1_c]
    p01 = f_pre[y1_c, x0_c]
    p11 = f_pre[y1_c, x1_c]

    interp = (
        p00 * (1.0 - wx) * (1.0 - wy)
        + p10 * wx * (1.0 - wy)
        + p01 * (1.0 - wx) * wy
        + p11 * wx * wy
    )
    out = np.zeros_like(arr)
    a_out = interp[:, :, 3:4]
    nonzero = a_out > 1.0
    rgb_out = np.where(nonzero, interp[:, :, :3] / np.maximum(a_out / 255.0, 1e-4), 0.0)
    out[:, :, :3] = np.clip(rgb_out, 0.0, 255.0).astype(np.uint8)
    out[:, :, 3] = np.where(valid, np.clip(a_out[:, :, 0], 0.0, 255.0), 0.0).astype(np.uint8)
    return out


def render_explorer_frame_1to1(
    hi_pose: Image.Image,
    dir_name: str,
    anim_name: str,
    frame_idx: int,
    total_frames: int,
) -> Image.Image:
    """
    Deforms the high-res pose smoothly, then resamples directly to 74px tall at 1:1 pixel
    resolution on the 96x96 canvas with binary alpha and crisp UnsharpMask so the character's
    eyes, hair, collar, vest, and boots are 100% clear and readable!
    """
    phase = (frame_idx / float(total_frames)) * 2.0 * math.pi
    s1 = math.sin(phase)
    smooth_bob = 0.5 * (1.0 - math.cos(2.0 * phase))
    bell = math.sin((frame_idx / float(total_frames)) * math.pi) ** 2

    dx = -1.0 if "left" in dir_name else (1.0 if "right" in dir_name else 0.0)

    pw, ph = hi_pose.size
    pad = 24
    buf = Image.new("RGBA", (pw + pad * 2, ph + pad * 2), (0, 0, 0, 0))
    buf.paste(hi_pose, (pad, pad))
    arr = np.array(buf)
    bh, bw, _ = arr.shape

    yy, xx = np.meshgrid(np.arange(bh, dtype=np.float32), np.arange(bw, dtype=np.float32), indexing="ij")
    y_norm = np.clip((yy - pad) / float(max(1, ph)), 0.0, 1.0)
    x_rel = (xx - (bw * 0.5)) / float(max(1, pw * 0.5))

    leg_t = np.clip((y_norm - 0.58) / 0.42, 0.0, 1.0)
    w_leg = 0.5 * (1.0 - np.cos(math.pi * leg_t))
    w_upper = 1.0 - w_leg

    src_x = xx.copy()
    src_y = yy.copy()
    whole_bob_px = 0

    if anim_name == "idle":
        breath = s1 * 1.8
        src_y -= breath * w_upper

    elif anim_name == "walk":
        whole_bob_px = int(round(-1.5 * smooth_bob))
        side_sign = np.tanh(x_rel * 2.5)
        src_y -= s1 * side_sign * 5.8 * w_leg
        src_x -= s1 * 2.4 * w_leg
        src_x += s1 * 1.8 * w_upper * (y_norm * 0.8)

    elif anim_name == "run":
        whole_bob_px = int(round(-2.2 * smooth_bob))
        side_sign = np.tanh(x_rel * 2.5)
        lean_amount = (dx if dx != 0 else 0.3) * 3.8 * (1.0 - y_norm)
        src_x -= lean_amount
        src_y -= s1 * side_sign * 7.8 * w_leg
        src_x -= s1 * 3.4 * w_leg
        src_x += s1 * 2.6 * w_upper * y_norm

    elif anim_name in ("axe", "pickaxe"):
        swing_wave = math.sin(phase) * bell
        lean = swing_wave * (dx if dx != 0 else 0.4) * 4.5 * w_upper
        src_x -= lean
        src_y -= swing_wave * 3.0 * w_upper

    elif anim_name == "water":
        src_x -= bell * (dx if dx != 0 else 0.4) * 3.8 * w_upper
        src_y -= bell * 2.6 * w_upper

    elif anim_name == "interact":
        whole_bob_px = int(round(-1.5 * bell))
        src_y += bell * 2.8 * w_upper * np.clip(x_rel, 0.0, 1.0)

    warped_arr = bilinear_warp_rgba(arr, src_x, src_y)
    warped_crop = crop_to_alpha(Image.fromarray(warped_arr, "RGBA"))

    CHAR_H = 74
    wc_w, wc_h = warped_crop.size
    char_w = max(24, int(round(wc_w * (CHAR_H / float(max(1, wc_h))))))

    crisp_char = resize_crisp_1to1(
        warped_crop,
        char_w,
        CHAR_H,
        sat_factor=1.04,
        contrast_factor=1.06,
        add_outline=False,
    )

    canvas = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(canvas)
    s_draw.ellipse([48 - 14, 84 - 6, 48 + 14, 84 + 6], fill=(18, 24, 32, 85))

    paste_x = (96 - char_w) // 2
    paste_y = 86 - CHAR_H + whole_bob_px
    canvas.alpha_composite(crisp_char, (paste_x, paste_y))

    # Draw 1:1 pixel-art tool overlays during action animations
    if anim_name in ("axe", "pickaxe", "water", "interact"):
        tool_layer = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
        td = ImageDraw.Draw(tool_layer)
        facing_x = -1 if "left" in dir_name else (1 if "right" in dir_name else 1)
        hx = 48 + facing_x * 10
        hy = 54 + whole_bob_px

        if anim_name in ("axe", "pickaxe"):
            swing_t = frame_idx / float(max(1, total_frames - 1))
            ang = (-1.15 + swing_t * 2.1) * facing_x
            tx = int(round(hx + math.sin(ang) * 16))
            ty = int(round(hy - math.cos(ang) * 16))
            td.line([(hx, hy), (tx, ty)], fill=(42, 26, 18, 255), width=4)
            td.line([(hx, hy), (tx, ty)], fill=(168, 108, 56, 255), width=2)
            px = int(round(math.cos(ang) * 6))
            py = int(round(math.sin(ang) * 6))
            if anim_name == "axe":
                blade = [(tx, ty), (tx + px, ty + py - 3), (tx + px + facing_x * 3, ty + py + 4)]
                td.polygon(blade, fill=(214, 224, 236, 255), outline=(42, 26, 18, 255))
            else:
                td.line([(tx - px, ty - py), (tx + px, ty + py)], fill=(42, 26, 18, 255), width=4)
                td.line([(tx - px, ty - py), (tx + px, ty + py)], fill=(198, 210, 224, 255), width=2)
        elif anim_name == "water":
            cx = hx + facing_x * 8
            cy = hy + 2 + int(round(bell * 3))
            td.rectangle([cx - 5, cy - 4, cx + 5, cy + 4], fill=(92, 164, 218, 255), outline=(42, 26, 18, 255))
            spout_x = cx + facing_x * 9
            td.line([(cx + facing_x * 5, cy - 1), (spout_x, cy + 2)], fill=(42, 26, 18, 255), width=3)
            td.line([(cx + facing_x * 5, cy - 1), (spout_x, cy + 2)], fill=(128, 194, 242, 255), width=1)
            if frame_idx in (2, 3, 4, 5):
                for d_i in range(3):
                    drop_y = cy + 5 + ((frame_idx * 2 + d_i * 3) % 8)
                    drop_x = spout_x + facing_x * (1 + d_i)
                    td.ellipse([drop_x - 1, drop_y - 1, drop_x + 1, drop_y + 1], fill=(135, 216, 255, 255))
        elif anim_name == "interact":
            if frame_idx in (1, 2, 3, 4, 5):
                sx = 48 + facing_x * 16
                sy = 42 - int(round(bell * 3))
                td.line([(sx - 4, sy), (sx + 4, sy)], fill=(255, 232, 115, 255), width=2)
                td.line([(sx, sy - 4), (sx, sy + 4)], fill=(255, 232, 115, 255), width=2)
                td.rectangle([sx - 1, sy - 1, sx + 1, sy + 1], fill=(255, 252, 220, 255))

        canvas.alpha_composite(tool_layer, (0, 0))

    return canvas


def build_explorer_spritesheet() -> None:
    print("Building High-Clarity 1:1 Explorer Spritesheet (74px tall on 96x96 frames)...")
    south_clean = crop_to_alpha(extract_clean_rgba(Image.open("assets/ai_raw/sdv_explorer_south.png"), min_hole_area=120, strip_floor_shadow=True))
    front_sw_clean = crop_to_alpha(extract_clean_rgba(Image.open("assets/ai_raw/sdv_explorer_front.png"), min_hole_area=120, strip_floor_shadow=True))
    side_e_clean = crop_to_alpha(extract_clean_rgba(Image.open("assets/ai_raw/sdv_explorer_side.png"), min_hole_area=120, strip_floor_shadow=True))
    back_nw_clean = crop_to_alpha(extract_clean_rgba(Image.open("assets/ai_raw/sdv_explorer_back.png"), min_hole_area=120, strip_floor_shadow=True))
    up_n_clean = crop_to_alpha(extract_clean_rgba(Image.open("assets/ai_raw/sdv_explorer_up.png"), min_hole_area=120, strip_floor_shadow=True))

    def norm_hi(im: Image.Image, h_target: int = 160) -> Image.Image:
        cw, ch = im.size
        nw = max(1, int(round(cw * (h_target / float(ch)))))
        return im.resize((nw, h_target), Image.Resampling.LANCZOS)

    p_south = norm_hi(south_clean)
    p_down_left = norm_hi(front_sw_clean)
    p_down_right = p_down_left.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    p_right = norm_hi(side_e_clean)
    p_left = p_right.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    p_up_left = norm_hi(back_nw_clean)
    p_up_right = p_up_left.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    p_up = norm_hi(up_n_clean)

    dir_poses = {
        "down":       p_south,
        "down_right": p_down_right,
        "right":      p_right,
        "up_right":   p_up_right,
        "up":         p_up,
        "up_left":    p_up_left,
        "left":       p_left,
        "down_left":  p_down_left,
    }

    cols = 8
    rows = len(ANIMATIONS) * len(DIRECTIONS)
    frame_size = 96
    sheet = Image.new("RGBA", (cols * frame_size, rows * frame_size), (0, 0, 0, 0))
    showcase = Image.new("RGBA", (len(DIRECTIONS) * frame_size, len(ANIMATIONS) * frame_size), (234, 226, 210, 255))
    sc_draw = ImageDraw.Draw(showcase)

    row_idx = 0
    for a_idx, (anim_name, frame_count) in enumerate(ANIMATIONS):
        sample_f = 2 if anim_name != "idle" else 0
        for d_idx, dir_name in enumerate(DIRECTIONS):
            pose_hi = dir_poses[dir_name]
            for col_idx in range(cols):
                frame_im = render_explorer_frame_1to1(pose_hi, dir_name, anim_name, col_idx, frame_count)
                sheet.alpha_composite(frame_im, (col_idx * frame_size, row_idx * frame_size))
                if col_idx == sample_f:
                    cx0, cy0 = d_idx * frame_size, a_idx * frame_size
                    bg_col = (236, 229, 214, 255) if (a_idx + d_idx) % 2 == 0 else (226, 218, 202, 255)
                    sc_draw.rectangle([cx0 + 1, cy0 + 1, cx0 + frame_size - 2, cy0 + frame_size - 2], fill=bg_col)
                    showcase.alpha_composite(frame_im, (cx0, cy0))
            row_idx += 1

    sheet.save("assets/sprites/player_spritesheet.png")
    showcase.save("assets/sprites/player_8dir_showcase.png")

    icon = Image.new("RGBA", (128, 128), (58, 134, 202, 255))
    idraw = ImageDraw.Draw(icon)
    idraw.ellipse([12, 78, 116, 118], fill=(232, 182, 112, 255))
    idraw.ellipse([18, 80, 110, 114], fill=(92, 182, 78, 255))
    hero_icon = render_explorer_frame_1to1(p_down_right, "down_right", "idle", 0, 8)
    icon.alpha_composite(hero_icon, (16, 16))
    icon.save("icon.png")
    print(f"Saved 1:1 Explorer spritesheet ({sheet.size[0]}x{sheet.size[1]})")


# =============================================================================
# 3. SEAMLESS 1:1 PIXEL-ART ISOMETRIC TILESET (64x40 CELLS, FLUSH 64x32 DIAMONDS)
#    Zero protruding 3D cliff skirts on ground tiles, harmonious Stardew Valley
#    palette, soft organic grass blade clusters, natural cobblestone roads & bridges!
# =============================================================================
TILE_W = 64
TILE_H = 32
CELL_H = 40


def hash2d(ix: int, iy: int, seed: int) -> float:
    n = (ix * 374761393 + iy * 668265263 + seed * 1442695041) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0x7FFFFFFF) / float(0x7FFFFFFF)


def smooth_noise(x: float, y: float, seed: int) -> float:
    ix = int(math.floor(x))
    iy = int(math.floor(y))
    fx = x - ix
    fy = y - iy
    ux = fx * fx * (3.0 - 2.0 * fx)
    uy = fy * fy * (3.0 - 2.0 * fy)
    v00 = hash2d(ix, iy, seed)
    v10 = hash2d(ix + 1, iy, seed)
    v01 = hash2d(ix, iy + 1, seed)
    v11 = hash2d(ix + 1, iy + 1, seed)
    return (v00 * (1.0 - ux) + v10 * ux) * (1.0 - uy) + (v01 * (1.0 - ux) + v11 * ux) * uy


def in_iso_diamond(x: int, y: int) -> bool:
    """
    Exact 64x32 2:1 isometric diamond coverage that tiles edge-to-edge without
    any gaps and WITHOUT protruding 3D cliff skirts!
    """
    if y < 0 or y >= TILE_H:
        return False
    dx = abs(x - 31.5)
    dy = abs(y - 15.5)
    return (dx + 2.0 * dy) <= 33.0


def edge_blend_weight(x: int, y: int) -> float:
    """
    Returns 0.0 near the diamond boundary and 1.0 inside the diamond interior,
    so all tiles smoothly converge to a harmonious edge tone at their borders
    (eliminating harsh grid lines between adjacent tiles!).
    """
    dx = abs(x - 31.5)
    dy = abs(y - 15.5)
    dist_from_edge = max(0.0, 32.5 - (dx + 2.0 * dy))
    return min(1.0, dist_from_edge / 6.0)


def make_grass_tile(
    base_rgb: tuple,
    mid_rgb: tuple,
    light_rgb: tuple,
    shade_rgb: tuple,
    edge_rgb: tuple,
    variant: int,
    flower_palette: list = None,
) -> Image.Image:
    im = Image.new("RGBA", (TILE_W, CELL_H), (0, 0, 0, 0))
    px = im.load()
    seed = 100 + variant * 37

    # 1. Organic multi-octave pixel-art grass base with edge harmonization
    for y in range(TILE_H):
        for x in range(TILE_W):
            if not in_iso_diamond(x, y):
                continue
            w_in = edge_blend_weight(x, y)
            n1 = smooth_noise(x * 0.16, y * 0.32, seed)
            n2 = smooth_noise(x * 0.38, y * 0.76, seed + 19)
            val = n1 * 0.68 + n2 * 0.32

            # Quantize to 4 soft Stardew pixel-art tones
            if val < 0.34:
                col = shade_rgb
            elif val < 0.56:
                col = base_rgb
            elif val < 0.76:
                col = mid_rgb
            else:
                col = light_rgb

            # Blend gently toward edge_rgb near the border for seamless tiling
            r = int(round(col[0] * w_in + edge_rgb[0] * (1.0 - w_in)))
            g = int(round(col[1] * w_in + edge_rgb[1] * (1.0 - w_in)))
            b = int(round(col[2] * w_in + edge_rgb[2] * (1.0 - w_in)))
            px[x, y] = (r, g, b, 255)

    # 2. Delicate 1x1 pixel grass tufts & blades inside the diamond
    rng = np.random.default_rng(seed + 777)
    for _ in range(26):
        gx = int(rng.integers(8, 56))
        gy = int(rng.integers(5, 27))
        if not in_iso_diamond(gx, gy) or edge_blend_weight(gx, gy) < 0.35:
            continue
        # 3-pixel miniature grass blade tuft
        if in_iso_diamond(gx, gy):
            px[gx, gy] = shade_rgb + (255,)
        if in_iso_diamond(gx, gy - 1):
            px[gx, gy - 1] = light_rgb + (255,)
        if in_iso_diamond(gx + 1, gy):
            px[gx + 1, gy] = mid_rgb + (255,)
        if in_iso_diamond(gx + 1, gy - 1) and rng.random() < 0.65:
            px[gx + 1, gy - 1] = light_rgb + (255,)

    # 3. Optional tiny flower buds / fallen autumn leaves
    if flower_palette:
        for _ in range(4):
            fx = int(rng.integers(14, 50))
            fy = int(rng.integers(7, 25))
            if in_iso_diamond(fx, fy) and edge_blend_weight(fx, fy) > 0.45:
                fcol = flower_palette[int(rng.integers(0, len(flower_palette)))]
                px[fx, fy] = fcol + (255,)
                if in_iso_diamond(fx + 1, fy):
                    px[fx + 1, fy] = fcol + (255,)
                if in_iso_diamond(fx, fy - 1):
                    px[fx, fy - 1] = (255, 246, 196, 255)

    return im


def make_sand_tile(base_rgb: tuple, light_rgb: tuple, shade_rgb: tuple, variant: int) -> Image.Image:
    im = Image.new("RGBA", (TILE_W, CELL_H), (0, 0, 0, 0))
    px = im.load()
    seed = 300 + variant * 41

    for y in range(TILE_H):
        for x in range(TILE_W):
            if not in_iso_diamond(x, y):
                continue
            w_in = edge_blend_weight(x, y)
            # Subtle isometric ripple + organic grain
            u = (x - 32.0) * 0.5 + (y - 16.0)
            ripple = 0.5 + 0.5 * math.sin(u * 0.42 + smooth_noise(x * 0.2, y * 0.4, seed) * 2.2)
            n = smooth_noise(x * 0.35, y * 0.70, seed + 11)
            v = ripple * 0.55 + n * 0.45
            if v < 0.35:
                col = shade_rgb
            elif v < 0.70:
                col = base_rgb
            else:
                col = light_rgb
            r = int(round(col[0] * w_in + base_rgb[0] * (1.0 - w_in)))
            g = int(round(col[1] * w_in + base_rgb[1] * (1.0 - w_in)))
            b = int(round(col[2] * w_in + base_rgb[2] * (1.0 - w_in)))
            px[x, y] = (r, g, b, 255)

    rng = np.random.default_rng(seed + 99)
    for _ in range(10):
        sx = int(rng.integers(12, 52))
        sy = int(rng.integers(6, 26))
        if in_iso_diamond(sx, sy) and edge_blend_weight(sx, sy) > 0.4:
            px[sx, sy] = shade_rgb + (255,)
            if in_iso_diamond(sx - 1, sy):
                px[sx - 1, sy] = light_rgb + (255,)
    return im


def make_cobblestone_road_tile(variant: int) -> Image.Image:
    """
    Warm country dirt path with closely-fitted rounded river-stone cobblestones
    at 1x1 pixel resolution and smooth edge transitions (no blocky brown diamond frame!).
    """
    im = Image.new("RGBA", (TILE_W, CELL_H), (0, 0, 0, 0))
    px = im.load()
    seed = 500 + variant * 53

    dirt_base = (186, 148, 102)
    dirt_shade = (164, 126, 82)
    dirt_light = (202, 164, 116)

    for y in range(TILE_H):
        for x in range(TILE_W):
            if not in_iso_diamond(x, y):
                continue
            n = smooth_noise(x * 0.25, y * 0.5, seed)
            col = dirt_shade if n < 0.38 else (dirt_base if n < 0.72 else dirt_light)
            px[x, y] = col + (255,)

    # Interlocking rounded cobblestones across the diamond
    stone_tones = [
        ((164, 156, 144), (192, 184, 172), (122, 114, 104)),
        ((152, 146, 138), (180, 174, 166), (114, 108, 98)),
        ((176, 164, 148), (202, 190, 174), (132, 120, 106)),
        ((144, 140, 134), (172, 168, 160), (108, 102, 94)),
    ]
    rng = np.random.default_rng(seed + 333)

    # Grid of jittered isometric cobbles covering the road surface
    for gy in range(4, 29, 4):
        row_shift = 3 if ((gy // 4) % 2 == 1) else 0
        for gx in range(8 + row_shift, 56, 6):
            cx = gx + int(rng.integers(-1, 2))
            cy = gy + int(rng.integers(-1, 2))
            if not in_iso_diamond(cx, cy) or edge_blend_weight(cx, cy) < 0.22:
                continue
            rx = int(rng.integers(2, 4))
            ry = 1 if rx == 2 else 2
            mid_s, hi_s, sh_s = stone_tones[int(rng.integers(0, len(stone_tones)))]

            for dy in range(-ry, ry + 1):
                for dx in range(-rx, rx + 1):
                    px_x, px_y = cx + dx, cy + dy
                    if not in_iso_diamond(px_x, px_y):
                        continue
                    dist = (dx * dx) / float(max(1, rx * rx)) + (dy * dy) / float(max(1, ry * ry))
                    if dist <= 1.05:
                        if dist > 0.72 and (dx + dy >= 1):
                            px[px_x, px_y] = sh_s + (255,)
                        elif dx + dy <= -1:
                            px[px_x, px_y] = hi_s + (255,)
                        else:
                            px[px_x, px_y] = mid_s + (255,)

    return im


def make_wooden_bridge_tile(variant: int) -> Image.Image:
    """
    Authentic 2:1 isometric oak-plank bridge (cross-planks running NE-SW across
    the river span, with warm woodgrain, plank seams, and sturdy side rails).
    """
    im = Image.new("RGBA", (TILE_W, CELL_H), (0, 0, 0, 0))
    px = im.load()
    seed = 700 + variant * 29

    plank_tones = [
        (184, 124, 68),
        (172, 112, 58),
        (196, 136, 78),
        (164, 106, 54),
    ]
    seam_col = (104, 62, 30)
    rail_top = (210, 152, 92)
    rail_side = (142, 88, 44)
    skirt_col = (112, 68, 34)

    for y in range(TILE_H):
        for x in range(TILE_W):
            if not in_iso_diamond(x, y):
                continue
            # Isometric coordinates along & across the bridge
            u = (x - 31.5) * 0.5 + (y - 15.5)   # along river (NW-SE)
            v = -(x - 31.5) * 0.5 + (y - 15.5)  # across river (NE-SW)

            # Side guard rails along the top-right and bottom-left bridge edges
            if abs(u) > 13.2:
                px[x, y] = (rail_top if u < 0 else rail_side) + (255,)
                continue

            plank_idx = int(math.floor((v + 32.0) / 3.5))
            plank_frac = (v + 32.0) / 3.5 - plank_idx
            if plank_frac < 0.16:
                px[x, y] = seam_col + (255,)
            else:
                base_p = plank_tones[(plank_idx + variant) % len(plank_tones)]
                grain = int(round((smooth_noise(u * 0.45, v * 0.25, seed) - 0.5) * 14.0))
                r = max(0, min(255, base_p[0] + grain))
                g = max(0, min(255, base_p[1] + grain))
                b = max(0, min(255, base_p[2] + grain))
                px[x, y] = (r, g, b, 255)

    # Subtle 2px wooden side thickness on the lower edge of the bridge over water
    for x in range(TILE_W):
        for y in range(16, TILE_H):
            if in_iso_diamond(x, y) and not in_iso_diamond(x, y + 1):
                for sy in range(1, 3):
                    if y + sy < CELL_H:
                        px[x, y + sy] = skirt_col + (255,)
                break

    return im


def make_water_tile(
    base_rgb: tuple,
    mid_rgb: tuple,
    light_rgb: tuple,
    variant: int,
    with_lilypad: bool = False,
) -> Image.Image:
    im = Image.new("RGBA", (TILE_W, CELL_H), (0, 0, 0, 0))
    px = im.load()
    seed = 900 + variant * 31

    for y in range(TILE_H):
        for x in range(TILE_W):
            if not in_iso_diamond(x, y):
                continue
            w_in = edge_blend_weight(x, y)
            wave = math.sin((x * 0.22) + (y * 0.44) + variant * 1.57)
            n = smooth_noise(x * 0.20, y * 0.40, seed)
            val = 0.5 + 0.28 * wave + 0.22 * (n - 0.5)
            if val < 0.38:
                col = base_rgb
            elif val < 0.72:
                col = mid_rgb
            else:
                col = light_rgb
            r = int(round(col[0] * w_in + mid_rgb[0] * (1.0 - w_in)))
            g = int(round(col[1] * w_in + mid_rgb[1] * (1.0 - w_in)))
            b = int(round(col[2] * w_in + mid_rgb[2] * (1.0 - w_in)))
            px[x, y] = (r, g, b, 255)

    # Delicate 1px water shimmer lines (animated by variant phase)
    shimmer_col = (min(255, light_rgb[0] + 42), min(255, light_rgb[1] + 42), min(255, light_rgb[2] + 32), 255)
    shift = (variant * 3) % 12
    for rx, ry, length in ((18 + shift, 11, 5), (34 - shift // 2, 18, 6), (26, 23 - (shift % 4), 4)):
        for dx in range(length):
            if in_iso_diamond(rx + dx, ry) and edge_blend_weight(rx + dx, ry) > 0.35:
                px[rx + dx, ry] = shimmer_col

    if with_lilypad:
        draw = ImageDraw.Draw(im)
        lx, ly = 28 + (variant % 2) * 5, 15 + ((variant // 2) % 2) * 3
        draw.ellipse([lx - 5, ly - 3, lx + 5, ly + 3], fill=(64, 152, 68, 255), outline=(38, 102, 44, 255))
        draw.ellipse([lx - 3, ly - 2, lx + 2, ly + 1], fill=(92, 182, 84, 255))
        if variant % 2 == 0:
            draw.rectangle([lx - 1, ly - 2, lx + 1, ly], fill=(252, 182, 206, 255))
            px[lx, ly - 1] = (255, 240, 150, 255)

    return im


def draw_decor_cell(atlas: Image.Image, col: int, row: int, kind: str, variant: int) -> None:
    cell = Image.new("RGBA", (TILE_W, CELL_H), (0, 0, 0, 0))
    px = cell.load()
    rng = np.random.default_rng(1400 + col * 53 + row * 19 + variant)

    if kind == "flowers":
        palettes = [
            [(238, 86, 82), (252, 132, 122)],
            [(248, 204, 68), (255, 232, 120)],
            [(232, 134, 204), (248, 178, 226)],
            [(242, 246, 252), (214, 226, 242)],
        ]
        petals = palettes[variant % 4]
        for _ in range(5):
            fx = int(rng.integers(18, 46))
            fy = int(rng.integers(10, 23))
            if in_iso_diamond(fx, fy):
                px[fx, fy + 1] = (54, 122, 52, 255)
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    if in_iso_diamond(fx + dx, fy + dy):
                        px[fx + dx, fy + dy] = petals[0] + (255,)
                px[fx, fy] = (255, 236, 116, 255)
    elif kind == "tufts":
        for _ in range(7):
            tx = int(rng.integers(16, 48))
            ty = int(rng.integers(9, 24))
            if in_iso_diamond(tx, ty):
                px[tx, ty] = (52, 114, 48, 255)
                px[tx, ty - 1] = (86, 158, 66, 255)
                px[tx + 1, ty - 1] = (118, 186, 78, 255)
                if ty - 2 >= 0:
                    px[tx, ty - 2] = (144, 204, 92, 255)
    elif kind == "mushrooms":
        for _ in range(3):
            mx = int(rng.integers(20, 44))
            my = int(rng.integers(11, 22))
            if in_iso_diamond(mx, my):
                px[mx, my] = (236, 222, 196, 255)
                px[mx, my + 1] = (212, 196, 168, 255)
                for dx in (-1, 0, 1):
                    px[mx + dx, my - 1] = (218, 72, 58, 255)
                px[mx, my - 2] = (236, 94, 74, 255)
                px[mx - 1, my - 1] = (252, 244, 228, 255)
    elif kind == "pebbles":
        for _ in range(5):
            px_x = int(rng.integers(18, 46))
            px_y = int(rng.integers(10, 23))
            if in_iso_diamond(px_x, px_y):
                px[px_x, px_y] = (146, 152, 160, 255)
                px[px_x + 1, px_y] = (118, 124, 132, 255)
                px[px_x, px_y - 1] = (176, 182, 190, 255)

    atlas.alpha_composite(cell, (col * TILE_W, row * CELL_H))


def build_isometric_tileset() -> None:
    print("Building Seamless 1:1 Pixel-Art Isometric Tileset (1024x200, flush 64x32 diamonds)...")
    atlas = Image.new("RGBA", (16 * TILE_W, 5 * CELL_H), (0, 0, 0, 0))

    def put(c: int, r: int, tile_im: Image.Image) -> None:
        atlas.alpha_composite(tile_im, (c * TILE_W, r * CELL_H))

    # Shared warm meadow edge color so all grass biomes blend together smoothly
    meadow_edge = (102, 164, 72)

    for v in range(4):
        # Row 0: Water (deep lake, shallow lake, river current, lilypad water)
        put(0 + v, 0, make_water_tile((42, 108, 168), (54, 124, 188), (72, 144, 208), v))
        put(4 + v, 0, make_water_tile((54, 126, 190), (68, 144, 208), (88, 164, 226), v))
        put(8 + v, 0, make_water_tile((48, 118, 182), (62, 136, 200), (84, 158, 220), v))
        put(12 + v, 0, make_water_tile((54, 126, 190), (68, 144, 208), (88, 164, 226), v, with_lilypad=True))

        # Row 1: Warm Sand (0..3), Lush Meadow Grass (4..7), Forest Grass (8..11), Cobblestone Road (12..15)
        put(0 + v, 1, make_sand_tile((216, 184, 126), (230, 200, 144), (196, 162, 106), v))
        put(4 + v, 1, make_grass_tile((98, 162, 70), (110, 174, 78), (124, 188, 88), (84, 146, 60), meadow_edge, v))
        put(8 + v, 1, make_grass_tile((76, 138, 62), (88, 152, 70), (102, 166, 78), (64, 122, 52), (86, 148, 66), v + 10))
        put(12 + v, 1, make_cobblestone_road_tile(v))

        # Row 2: Wooden Bridge (0..3), Rich Soil (4..7), Slate Highland (8..11), Warm Olive/Autumn Meadow (12..15)
        put(0 + v, 2, make_wooden_bridge_tile(v))
        put(4 + v, 2, make_sand_tile((138, 96, 62), (154, 110, 74), (118, 80, 50), v + 20))
        put(8 + v, 2, make_sand_tile((132, 138, 148), (148, 154, 164), (114, 120, 130), v + 30))
        put(
            12 + v, 2,
            make_grass_tile(
                (112, 164, 68), (126, 176, 76), (142, 190, 86), (96, 148, 58), meadow_edge, v + 20,
                flower_palette=[(228, 124, 54), (238, 168, 64)],
            ),
        )

        # Row 3: Transparent Isometric Ground Decorations
        draw_decor_cell(atlas, 0 + v, 3, "flowers", v)
        draw_decor_cell(atlas, 4 + v, 3, "tufts", v)
        draw_decor_cell(atlas, 8 + v, 3, "mushrooms", v)
        draw_decor_cell(atlas, 12 + v, 3, "pebbles", v)

        # Row 4: Spring Blossom Lawn (0..3), Warm Sandstone Plateau (4..7), Mossy Glade (8..15)
        put(
            0 + v, 4,
            make_grass_tile(
                (104, 168, 76), (116, 180, 84), (132, 194, 94), (90, 152, 66), meadow_edge, v + 30,
                flower_palette=[(248, 176, 204), (255, 210, 226)],
            ),
        )
        put(4 + v, 4, make_sand_tile((198, 154, 106), (214, 170, 122), (178, 136, 90), v + 40))
        put(8 + v, 4, make_grass_tile((86, 148, 66), (98, 162, 74), (112, 176, 84), (74, 134, 56), meadow_edge, v + 40))
        put(12 + v, 4, make_grass_tile((92, 156, 68), (104, 168, 76), (118, 182, 86), (80, 142, 58), meadow_edge, v + 50))

    atlas.save("assets/tilesets/world_tileset.png")
    print("Saved seamless 1:1 pixel-art assets/tilesets/world_tileset.png")


if __name__ == "__main__":
    build_world_objects()
    build_explorer_spritesheet()
    build_isometric_tileset()
    print("All high-clarity 1:1 pixel-art isometric assets built successfully!")
