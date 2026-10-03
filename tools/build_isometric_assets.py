#!/usr/bin/env python3
"""
Builds Crisp, True Low-Res Pixel-Art Isometric Assets for Godot 4.7 (Zero Blur / Zero Soapiness):
  - Unified Pixel Grid: 1 logical pixel = 2x2 texels (NEAREST neighbor, 100% sharp edges, zero Gaussian blur!).
  - Character: ~16x34 logical pixels (68px tall on 96x96 canvas) — matching the exact pixel count (~15x32 px)
    of the user's reference image, with a crisp 1-logical-pixel dark brown outline (#261710), warm palette,
    and ZERO equipment across all 8 directions and 7 animations (8 frames each).
  - 19 World Objects (8 Trees + 8 Pure Natural Rocks without ore + 3 Forest Props):
    Quantized to the exact same 2x2 logical pixel grid with crisp binary alpha (0/255), clean 1-logical-pixel
    dark brown outlines, cluster-quantized Stardew Valley colors, and crisp pixel-art shadows.
  - Isometric Tileset (assets/tilesets/world_tileset.png, 1024x200, 64x40 cells = 32x20 logical pixels per tile):
    Hand-crafted crisp pixel-art grass blades, clovers, interlocking cobblestones, wooden planks, and water ripples
    with seamless edges and zero blur.
"""

import math
import os
import random
from collections import deque
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

os.makedirs("assets/sprites", exist_ok=True)
os.makedirs("assets/tilesets", exist_ok=True)
os.makedirs("assets/objects", exist_ok=True)
os.makedirs("assets/ui", exist_ok=True)

PIXEL_SCALE = 2  # 1 logical pixel = 2x2 texels everywhere in the game!
OUTLINE_RGB = (38, 23, 16)  # Crisp dark-brown pixel outline (#261710) matching reference


# =============================================================================
# 0. CLEAN FOREGROUND EXTRACTION & CRISP PIXEL-GRID QUANTIZATION (ZERO BLUR!)
# =============================================================================
def extract_clean_rgba(
    im: Image.Image,
    white_thresh: int = 230,
    chroma_thresh: int = 30,
    min_hole_area: int = 90,
    strip_floor_shadow: bool = False,
) -> Image.Image:
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

    rgba[bg_mask, 3] = 0
    return Image.fromarray(rgba, "RGBA")


def crop_to_alpha(im: Image.Image) -> Image.Image:
    bbox = im.getbbox()
    if not bbox:
        return im
    return im.crop(bbox)


def to_crisp_pixel_art(
    im: Image.Image,
    logical_w: int,
    logical_h: int,
    color_step: int = 16,
    sat_boost: float = 1.18,
    contrast_boost: float = 1.12,
    outline_rgb: tuple = OUTLINE_RGB,
) -> Image.Image:
    """
    Converts a high-res RGBA sprite into a 100% CRISP low-res pixel-art sprite at
    (logical_w x logical_h) logical pixels:
      1. Downsamples RGB & Alpha to (logical_w, logical_h) using box/area averaging (no blurry halo)
      2. Applies a strict binary alpha threshold (alpha = 0 or 255 -> ZERO semi-transparent soapiness!)
      3. Quantizes colors into clean flat pixel clusters (color_step)
      4. Enforces a clean, continuous 1-logical-pixel dark brown outline (#261710) around the silhouette
      5. Upscales by PIXEL_SCALE (2x) using NEAREST so every logical pixel is a razor-sharp 2x2 square!
    """
    rgba = im.convert("RGBA")
    arr = np.array(rgba, dtype=np.float32)
    alpha = arr[:, :, 3:4] / 255.0

    # Premultiply RGB before area downsampling so white background never bleeds into edge pixels
    pre_rgb = arr[:, :, :3] * alpha
    pre_im = Image.fromarray(np.clip(pre_rgb, 0, 255).astype(np.uint8), "RGB")
    a_im = Image.fromarray(arr[:, :, 3].astype(np.uint8), "L")

    small_pre = pre_im.resize((logical_w, logical_h), Image.Resampling.BOX)
    small_a = a_im.resize((logical_w, logical_h), Image.Resampling.BOX)

    s_pre_arr = np.array(small_pre, dtype=np.float32)
    s_a_arr = np.array(small_a, dtype=np.float32) / 255.0

    # Un-premultiply on solid pixels
    solid = s_a_arr >= 0.38
    rgb_unpre = np.where(
        s_a_arr[:, :, None] > 0.05,
        s_pre_arr / np.maximum(s_a_arr[:, :, None], 0.05),
        0.0,
    )
    rgb_im = Image.fromarray(np.clip(rgb_unpre, 0, 255).astype(np.uint8), "RGB")
    rgb_im = ImageEnhance.Color(rgb_im).enhance(sat_boost)
    rgb_im = ImageEnhance.Contrast(rgb_im).enhance(contrast_boost)

    q_arr = np.array(rgb_im, dtype=np.float32)
    # Posterize to clean pixel-art color clusters
    q_arr = np.round(q_arr / float(color_step)) * float(color_step)
    q_arr = np.clip(q_arr, 0, 255).astype(np.uint8)

    out_small = np.zeros((logical_h, logical_w, 4), dtype=np.uint8)
    out_small[solid, :3] = q_arr[solid]
    out_small[solid, 3] = 255  # 100% opaque or 100% transparent — ZERO blurry semi-transparency!

    # Remove isolated single stray pixels
    for y in range(logical_h):
        for x in range(logical_w):
            if out_small[y, x, 3] > 0:
                neighbors = 0
                for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if 0 <= ny < logical_h and 0 <= nx < logical_w and out_small[ny, nx, 3] > 0:
                        neighbors += 1
                if neighbors == 0:
                    out_small[y, x] = (0, 0, 0, 0)

    # Apply crisp 1-logical-pixel dark brown outline on exterior boundary pixels
    if outline_rgb is not None:
        is_solid = out_small[:, :, 3] > 0
        is_edge = np.zeros((logical_h, logical_w), dtype=bool)
        for y in range(logical_h):
            for x in range(logical_w):
                if is_solid[y, x]:
                    if (
                        y == 0 or y == logical_h - 1 or x == 0 or x == logical_w - 1
                        or not is_solid[y - 1, x] or not is_solid[y + 1, x]
                        or not is_solid[y, x - 1] or not is_solid[y, x + 1]
                    ):
                        is_edge[y, x] = True
        # Blend edge pixel 65% toward dark brown outline so outline is crisp and colored
        out_small[is_edge, 0] = ((out_small[is_edge, 0].astype(np.int16) * 35 + outline_rgb[0] * 65) // 100).astype(np.uint8)
        out_small[is_edge, 1] = ((out_small[is_edge, 1].astype(np.int16) * 35 + outline_rgb[1] * 65) // 100).astype(np.uint8)
        out_small[is_edge, 2] = ((out_small[is_edge, 2].astype(np.int16) * 35 + outline_rgb[2] * 65) // 100).astype(np.uint8)

    small_rgba = Image.fromarray(out_small, "RGBA")
    return small_rgba.resize((logical_w * PIXEL_SCALE, logical_h * PIXEL_SCALE), Image.Resampling.NEAREST)


def fit_crisp_pixel_object(
    im: Image.Image,
    target_w: int,
    target_h: int,
    bottom_pad: int = 6,
    shadow_rx: int = 28,
    shadow_ry: int = 12,
    shadow_y_off: int = -8,
    color_step: int = 16,
    sat_boost: float = 1.22,
) -> Image.Image:
    """
    Fits an object onto (target_w x target_h) canvas on the exact 2x2 logical pixel grid
    with a crisp pixel-art elliptical ground shadow (zero Gaussian blur!).
    """
    cropped = crop_to_alpha(im)
    cw, ch = cropped.size

    log_canvas_w = target_w // PIXEL_SCALE
    log_canvas_h = target_h // PIXEL_SCALE
    log_bpad = bottom_pad // PIXEL_SCALE

    avail_w = log_canvas_w - 4
    avail_h = log_canvas_h - log_bpad - 2
    scale = min(avail_w / float(cw), avail_h / float(ch))
    log_w = max(1, int(round(cw * scale)))
    log_h = max(1, int(round(ch * scale)))

    crisp_sprite = to_crisp_pixel_art(
        cropped,
        log_w,
        log_h,
        color_step=color_step,
        sat_boost=sat_boost,
        contrast_boost=1.14,
        outline_rgb=OUTLINE_RGB,
    )

    # Draw crisp pixel-art shadow at logical resolution, then upscale 2x with NEAREST
    shadow_log = Image.new("RGBA", (log_canvas_w, log_canvas_h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_log)
    scx = log_canvas_w // 2
    scy = log_canvas_h - log_bpad + (shadow_y_off // PIXEL_SCALE)
    srx = shadow_rx // PIXEL_SCALE
    sry = shadow_ry // PIXEL_SCALE
    s_draw.ellipse(
        [scx - srx, scy - sry, scx + srx, scy + sry],
        fill=(18, 24, 32, 95),
    )
    canvas = shadow_log.resize((target_w, target_h), Image.Resampling.NEAREST)

    paste_x = ((log_canvas_w - log_w) // 2) * PIXEL_SCALE
    paste_y = (log_canvas_h - log_bpad - log_h) * PIXEL_SCALE
    canvas.alpha_composite(crisp_sprite, (paste_x, paste_y))
    return canvas


def recolor_oak_to_stardew_sakura(oak_im: Image.Image) -> Image.Image:
    arr = np.array(oak_im.convert("RGBA"), dtype=np.float32)
    r, g, b, a = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]
    is_foliage = (a > 20) & (g > r + 10)
    lum = (r * 0.25 + g * 0.65 + b * 0.10) / 255.0
    new_r = np.clip(148.0 + lum * 135.0, 0, 255)
    new_g = np.clip(50.0 + (lum ** 1.25) * 195.0, 0, 255)
    new_b = np.clip(90.0 + (lum ** 1.15) * 165.0, 0, 255)
    arr[:, :, 0] = np.where(is_foliage, new_r, r)
    arr[:, :, 1] = np.where(is_foliage, new_g, g)
    arr[:, :, 2] = np.where(is_foliage, new_b, b)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


# =============================================================================
# 1. BUILD 19 CRISP PIXEL-ART WORLD OBJECTS (8 Trees, 8 Rocks, 3 Props)
# =============================================================================
def build_world_objects() -> None:
    print("Building 19 crisp low-res pixel-art world objects (zero blur)...")

    sdv_oak = extract_clean_rgba(Image.open("assets/ai_raw/sdv_tree_oak.png"), min_hole_area=90)
    sdv_willow = extract_clean_rgba(Image.open("assets/ai_raw/sdv_tree_willow.png"), min_hole_area=90)
    sdv_pine = extract_clean_rgba(Image.open("assets/ai_raw/sdv_tree_pine.png"), min_hole_area=90)
    sdv_birch = extract_clean_rgba(Image.open("assets/ai_raw/sdv_tree_birch.png"), min_hole_area=280)
    sdv_maple = extract_clean_rgba(Image.open("assets/ai_raw/sdv_tree_maple.png"), min_hole_area=90)
    sdv_cherry = recolor_oak_to_stardew_sakura(sdv_oak)
    sdv_cedar = extract_clean_rgba(Image.open("assets/ai_raw/iso_tree_ancient_fir.png"), min_hole_area=90)
    sdv_poplar = extract_clean_rgba(Image.open("assets/ai_raw/iso_tree_poplar.png"), min_hole_area=90)

    tree_outputs = [
        (sdv_oak,    "assets/objects/tree_oak.png",    160, 176, 8, 42, 18, -12, 16, 1.20),
        (sdv_willow, "assets/objects/tree_willow.png", 168, 176, 8, 46, 19, -12, 16, 1.20),
        (sdv_pine,   "assets/objects/tree_pine.png",   144, 192, 8, 34, 15, -10, 16, 1.22),
        (sdv_birch,  "assets/objects/tree_birch.png",  144, 176, 8, 34, 15, -10, 16, 1.22),
        (sdv_maple,  "assets/objects/tree_maple.png",  160, 176, 8, 42, 18, -12, 16, 1.22),
        (sdv_cherry, "assets/objects/tree_cherry.png", 168, 176, 8, 44, 18, -12, 16, 1.22),
        (sdv_cedar,  "assets/objects/tree_cedar.png",  152, 192, 8, 38, 16, -10, 18, 1.30),
        (sdv_poplar, "assets/objects/tree_poplar.png", 128, 196, 8, 30, 14, -10, 18, 1.30),
    ]
    for clean_im, dst_path, tw, th, bpad, srx, sry, syoff, cstep, sat in tree_outputs:
        out = fit_crisp_pixel_object(clean_im, tw, th, bpad, srx, sry, syoff, color_step=cstep, sat_boost=sat)
        out.save(dst_path)

    rock_specs = [
        ("assets/ai_raw/iso_rock_boulder.png",       "assets/objects/rock_large.png",     112, 96, 6, 42, 18, -12, 90),
        ("assets/ai_raw/iso_rock_slate.png",         "assets/objects/rock_slate.png",     112, 96, 6, 42, 18, -12, 90),
        ("assets/ai_raw/iso_rock_sandstone.png",     "assets/objects/rock_sandstone.png", 116, 96, 6, 44, 19, -12, 80),
        ("assets/ai_raw/iso_rock_mossy_cluster.png", "assets/objects/rock_river.png",     108, 88, 6, 42, 18, -11, 250),
        ("assets/ai_raw/iso_rock_limestone.png",     "assets/objects/rock_limestone.png", 112, 92, 6, 42, 18, -11, 200),
        ("assets/ai_raw/iso_rock_basalt.png",        "assets/objects/rock_basalt.png",    116, 96, 6, 44, 19, -12, 120),
        ("assets/ai_raw/iso_rock_flat_stepping.png", "assets/objects/rock_flat.png",      116, 88, 6, 44, 18, -11, 150),
        ("assets/ai_raw/iso_rock_limestone.png",     "assets/objects/rock_small.png",      72, 60, 4, 26, 11, -7,  200),
    ]
    for src_path, dst_path, tw, th, bpad, srx, sry, syoff, min_hole in rock_specs:
        clean = extract_clean_rgba(Image.open(src_path), min_hole_area=min_hole)
        out = fit_crisp_pixel_object(clean, tw, th, bpad, srx, sry, syoff, color_step=18, sat_boost=1.25)
        out.save(dst_path)

    # 3 Crisp Pixel-Art Forest Props
    oak_crop = crop_to_alpha(sdv_oak)
    ow, oh = oak_crop.size
    trunk_slice = oak_crop.crop((int(ow * 0.22), int(oh * 0.58), int(ow * 0.78), oh))
    s_draw = ImageDraw.Draw(trunk_slice)
    tw_s, th_s = trunk_slice.size
    s_draw.ellipse([int(tw_s * 0.18), 2, int(tw_s * 0.82), int(th_s * 0.36)], fill=(64, 34, 18, 255))
    s_draw.ellipse([int(tw_s * 0.22), 6, int(tw_s * 0.78), int(th_s * 0.32)], fill=(228, 174, 108, 255))
    s_draw.ellipse([int(tw_s * 0.32), 12, int(tw_s * 0.68), int(th_s * 0.26)], fill=(188, 132, 74, 255))
    fit_crisp_pixel_object(trunk_slice, 64, 56, 6, 22, 10, -6, color_step=16, sat_boost=1.20).save("assets/objects/tree_stump.png")

    canopy_cluster = oak_crop.crop((int(ow * 0.14), int(oh * 0.04), int(ow * 0.86), int(oh * 0.56)))
    cw_c, ch_c = canopy_cluster.size
    b_draw = ImageDraw.Draw(canopy_cluster)
    for bx_f, by_f in [(0.30, 0.40), (0.46, 0.28), (0.64, 0.34), (0.72, 0.52), (0.38, 0.62), (0.55, 0.54)]:
        bx, by = int(cw_c * bx_f), int(ch_c * by_f)
        r_b = max(8, int(cw_c * 0.045))
        b_draw.ellipse([bx - r_b, by - r_b, bx + r_b, by + r_b], fill=(232, 46, 64, 255), outline=(92, 16, 26, 255), width=3)
    fit_crisp_pixel_object(canopy_cluster, 68, 60, 6, 25, 11, -7, color_step=16, sat_boost=1.22).save("assets/objects/bush_berry.png")

    bark_rot = trunk_slice.rotate(72, expand=True, resample=Image.Resampling.NEAREST)
    fit_crisp_pixel_object(bark_rot, 96, 56, 6, 36, 12, -6, color_step=16, sat_boost=1.20).save("assets/objects/log_fallen.png")


# =============================================================================
# 2. CRISP PIXEL-ART EXPLORER (~16x34 LOGICAL PIXELS = 68PX TALL AT 2X NEAREST)
#    Matches the exact pixel count of the user's reference image!
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


def render_crisp_explorer_frame(
    hi_pose: Image.Image,
    dir_name: str,
    anim_name: str,
    frame_idx: int,
    total_frames: int,
) -> Image.Image:
    """
    Deforms the high-res pose smoothly, then quantizes the frame onto a crisp 48x48 logical
    pixel grid (where the character is 34 logical pixels tall x ~16 logical pixels wide,
    matching the user's reference image!), applies a crisp 1-logical-pixel dark outline,
    and scales 2x with NEAREST to 96x96!
    """
    phase = (frame_idx / float(total_frames)) * 2.0 * math.pi
    s1 = math.sin(phase)
    c1 = math.cos(phase)
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
    whole_bob_log = 0

    if anim_name == "idle":
        breath = s1 * 2.2
        src_y -= breath * w_upper

    elif anim_name == "walk":
        whole_bob_log = -1 if smooth_bob > 0.55 else 0
        side_sign = np.tanh(x_rel * 2.5)
        src_y -= s1 * side_sign * 6.5 * w_leg
        src_x -= s1 * 2.8 * w_leg
        src_x += s1 * 2.0 * w_upper * (y_norm * 0.8)

    elif anim_name == "run":
        whole_bob_log = -1 if smooth_bob > 0.35 else 0
        side_sign = np.tanh(x_rel * 2.5)
        lean_amount = (dx if dx != 0 else 0.3) * 4.2 * (1.0 - y_norm)
        src_x -= lean_amount
        src_y -= s1 * side_sign * 8.5 * w_leg
        src_x -= s1 * 3.8 * w_leg
        src_x += s1 * 3.0 * w_upper * y_norm

    elif anim_name in ("axe", "pickaxe"):
        swing_wave = math.sin(phase) * bell
        lean = swing_wave * (dx if dx != 0 else 0.4) * 5.0 * w_upper
        src_x -= lean
        src_y -= swing_wave * 3.5 * w_upper

    elif anim_name == "water":
        src_x -= bell * (dx if dx != 0 else 0.4) * 4.2 * w_upper
        src_y -= bell * 3.0 * w_upper

    elif anim_name == "interact":
        whole_bob_log = -1 if bell > 0.5 else 0
        src_y += bell * 3.2 * w_upper * np.clip(x_rel, 0.0, 1.0)

    warped_arr = bilinear_warp_rgba(arr, src_x, src_y)
    warped_crop = crop_to_alpha(Image.fromarray(warped_arr, "RGBA"))

    # Target logical character height: 34 logical pixels (~15-16 logical pixels wide),
    # which is the EXACT pixel density of the user's reference image!
    LOG_CHAR_H = 34
    wc_w, wc_h = warped_crop.size
    log_char_w = max(12, int(round(wc_w * (LOG_CHAR_H / float(max(1, wc_h))))))

    crisp_char = to_crisp_pixel_art(
        warped_crop,
        log_char_w,
        LOG_CHAR_H,
        color_step=16,
        sat_boost=1.16,
        contrast_boost=1.12,
        outline_rgb=OUTLINE_RGB,
    )

    # Place onto 48x48 logical canvas (96x96 texels at PIXEL_SCALE=2)
    LOG_CANVAS = 48
    shadow_log = Image.new("RGBA", (LOG_CANVAS, LOG_CANVAS), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_log)
    s_draw.ellipse([24 - 7, 42 - 3, 24 + 7, 42 + 3], fill=(18, 24, 32, 95))
    canvas = shadow_log.resize((96, 96), Image.Resampling.NEAREST)

    paste_x = ((LOG_CANVAS - log_char_w) // 2) * PIXEL_SCALE
    paste_y = (43 - LOG_CHAR_H + whole_bob_log) * PIXEL_SCALE
    canvas.alpha_composite(crisp_char, (paste_x, paste_y))

    # Draw crisp low-res pixel-art tool overlays ONLY during action animations
    if anim_name in ("axe", "pickaxe", "water", "interact"):
        tool_log = Image.new("RGBA", (LOG_CANVAS, LOG_CANVAS), (0, 0, 0, 0))
        td = ImageDraw.Draw(tool_log)
        facing_x = -1 if "left" in dir_name else (1 if "right" in dir_name else 1)
        hx = 24 + facing_x * 5
        hy = 27 + whole_bob_log

        if anim_name in ("axe", "pickaxe"):
            swing_t = frame_idx / float(max(1, total_frames - 1))
            ang = (-1.15 + swing_t * 2.1) * facing_x
            tx = int(round(hx + math.sin(ang) * 8))
            ty = int(round(hy - math.cos(ang) * 8))
            # Wooden handle
            td.line([(hx, hy), (tx, ty)], fill=(158, 102, 54, 255), width=1)
            px = int(round(math.cos(ang) * 3))
            py = int(round(math.sin(ang) * 3))
            if anim_name == "axe":
                td.polygon(
                    [(tx, ty), (tx + px, ty + py - 1), (tx + px + facing_x, ty + py + 2)],
                    fill=(208, 218, 230, 255),
                )
            else:
                td.line([(tx - px, ty - py), (tx + px, ty + py)], fill=(192, 204, 218, 255), width=1)
        elif anim_name == "water":
            cx = hx + facing_x * 4
            cy = hy + 1 + (1 if bell > 0.4 else 0)
            td.rectangle([cx - 2, cy - 2, cx + 2, cy + 1], fill=(92, 162, 216, 255))
            spout_x = cx + facing_x * 4
            td.line([(cx + facing_x * 2, cy - 1), (spout_x, cy + 1)], fill=(120, 188, 238, 255), width=1)
            if frame_idx in (2, 3, 4, 5):
                drop_y = cy + 2 + ((frame_idx - 2) % 3)
                td.point((spout_x + facing_x, drop_y), fill=(116, 206, 255, 255))
                td.point((spout_x, drop_y + 2), fill=(160, 228, 255, 255))
        elif anim_name == "interact":
            if frame_idx in (1, 2, 3, 4, 5):
                sx = 24 + facing_x * 8
                sy = 21 - (1 if bell > 0.5 else 0)
                td.line([(sx - 2, sy), (sx + 2, sy)], fill=(255, 232, 120, 255), width=1)
                td.line([(sx, sy - 2), (sx, sy + 2)], fill=(255, 232, 120, 255), width=1)
                td.point((sx, sy), fill=(255, 252, 215, 255))

        t_arr = np.array(tool_log, dtype=np.uint8)
        th, tw, _ = t_arr.shape
        t_solid = t_arr[:, :, 3] > 0
        for ty_i in range(1, th - 1):
            for tx_i in range(1, tw - 1):
                if not t_solid[ty_i, tx_i]:
                    if (
                        t_solid[ty_i - 1, tx_i] or t_solid[ty_i + 1, tx_i]
                        or t_solid[ty_i, tx_i - 1] or t_solid[ty_i, tx_i + 1]
                    ):
                        t_arr[ty_i, tx_i] = (OUTLINE_RGB[0], OUTLINE_RGB[1], OUTLINE_RGB[2], 255)
        tool_crisp = Image.fromarray(t_arr, "RGBA").resize((96, 96), Image.Resampling.NEAREST)
        canvas.alpha_composite(tool_crisp, (0, 0))

    return canvas


def build_explorer_spritesheet() -> None:
    print("Building Crisp Low-Res Pixel-Art Explorer Spritesheet (~16x34 logical pixels, 2x NEAREST)...")
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
                frame_im = render_crisp_explorer_frame(pose_hi, dir_name, anim_name, col_idx, frame_count)
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
    hero_icon = render_crisp_explorer_frame(p_down_right, "down_right", "idle", 0, 8)
    icon.alpha_composite(hero_icon, (16, 16))
    icon.save("icon.png")
    print(f"Saved crisp pixel-art Explorer spritesheet ({sheet.size[0]}x{sheet.size[1]})")


# =============================================================================
# 3. CRISP PIXEL-ART ISOMETRIC TILESET (32x20 LOGICAL PIXELS SCALED 2X NEAREST -> 64x40)
#    Zero blur, rich hand-crafted pixel-art grass blades, cobbles, planks, and ripples!
# =============================================================================
def build_crisp_isometric_tileset() -> None:
    print("Building Crisp Pixel-Art Isometric Tileset (1024x200, 2x NEAREST from 32x20 logical grid)...")
    LOG_W = 32
    LOG_H = 16
    LOG_SKIRT = 4
    LOG_CELL_H = LOG_H + LOG_SKIRT  # 20 logical pixels -> 40 texels at 2x NEAREST
    COLS, ROWS = 16, 5

    hw = LOG_W / 2.0  # 16.0
    hh = LOG_H / 2.0  # 8.0

    yy, xx = np.meshgrid(np.arange(LOG_CELL_H, dtype=np.float32), np.arange(LOG_W, dtype=np.float32), indexing="ij")
    # Crisp Manhattan diamond mask on 32x16 logical grid
    dx = np.abs(xx + 0.5 - hw) / hw
    dy = np.abs(yy + 0.5 - hh) / hh
    in_diamond = (dx + dy <= 1.04) & (yy < LOG_H)

    bot_y_at_x = hh + (1.0 - dx) * hh
    in_skirt = (yy >= bot_y_at_x - 0.8) & (yy < bot_y_at_x + LOG_SKIRT) & (dx <= 1.02)
    in_tile = in_diamond | in_skirt

    def make_crisp_iso_tile(
        base_rgb: tuple,
        shade_rgb: tuple,
        light_rgb: tuple,
        skirt_rgb: tuple,
        seed_offset: int,
        pixel_art_fn=None,
    ) -> Image.Image:
        arr = np.zeros((LOG_CELL_H, LOG_W, 4), dtype=np.uint8)
        for c_i in range(3):
            plane = np.where(in_skirt, skirt_rgb[c_i], base_rgb[c_i])
            plane = np.where(in_diamond, base_rgb[c_i], plane)
            arr[:, :, c_i] = plane.astype(np.uint8)
        arr[:, :, 3] = np.where(in_tile, 255, 0).astype(np.uint8)

        # Deterministic pixel-art cluster pattern inside diamond (leaving 2px border uniform for seamless tiling!)
        rng = random.Random(1000 + seed_offset * 97)
        for _ in range(9):
            cx = rng.randint(6, LOG_W - 7)
            cy = rng.randint(3, LOG_H - 4)
            if in_diamond[cy, cx]:
                col = light_rgb if rng.random() < 0.5 else shade_rgb
                for ox, oy in [(0, 0), (1, 0), (0, 1)]:
                    ny, nx = cy + oy, cx + ox
                    if 0 <= ny < LOG_H and 0 <= nx < LOG_W and in_diamond[ny, nx]:
                        arr[ny, nx, :3] = col

        if pixel_art_fn is not None:
            pixel_art_fn(arr, in_diamond, seed_offset)

        log_im = Image.fromarray(arr, "RGBA")
        return log_im.resize((LOG_W * PIXEL_SCALE, LOG_CELL_H * PIXEL_SCALE), Image.Resampling.NEAREST)

    atlas = Image.new("RGBA", (COLS * 64, ROWS * 40), (0, 0, 0, 0))

    def put_px(arr, mask, x, y, rgb):
        if 0 <= y < LOG_H and 0 <= x < LOG_W and mask[y, x]:
            arr[y, x, :3] = rgb

    # ROW 0: Crisp Pixel-Art Water Tiles (Deep, Shallow, River, Lilypads)
    for i in range(4):
        def deep_wave(arr, mask, idx):
            for wx, wy in [(11 + (idx % 3), 6), (17 - (idx % 2), 9), (13, 11)]:
                put_px(arr, mask, wx, wy, (125, 194, 245))
                put_px(arr, mask, wx + 1, wy, (165, 218, 255))
                put_px(arr, mask, wx + 2, wy, (125, 194, 245))
        t = make_crisp_iso_tile((44, 108, 178), (38, 96, 164), (54, 122, 194), (36, 90, 154), i, deep_wave)
        atlas.alpha_composite(t, (i * 64, 0))

    for i in range(4):
        def shallow_wave(arr, mask, idx):
            for wx, wy in [(10 + (idx % 3), 6), (18 - (idx % 2), 8), (14, 11)]:
                put_px(arr, mask, wx, wy, (190, 238, 255))
                put_px(arr, mask, wx + 1, wy, (230, 250, 255))
                put_px(arr, mask, wx + 2, wy, (190, 238, 255))
        t = make_crisp_iso_tile((64, 144, 210), (56, 132, 198), (76, 158, 222), (52, 124, 188), 10 + i, shallow_wave)
        atlas.alpha_composite(t, ((4 + i) * 64, 0))

    for i in range(4):
        def river_wave(arr, mask, idx):
            for wx, wy in [(10 + (idx % 4), 5), (15 + (idx % 3), 8), (12 + (idx % 2), 11)]:
                put_px(arr, mask, wx, wy, (205, 244, 255))
                put_px(arr, mask, wx + 1, wy, (240, 252, 255))
                put_px(arr, mask, wx + 2, wy + 1, (180, 230, 250))
        t = make_crisp_iso_tile((58, 136, 204), (50, 124, 192), (70, 150, 218), (48, 118, 182), 20 + i, river_wave)
        atlas.alpha_composite(t, ((8 + i) * 64, 0))

    for i in range(4):
        def lilypad_px(arr, mask, idx):
            for lx, ly in [(12, 7), (19, 9)]:
                for dy_l in (-1, 0, 1):
                    for dx_l in (-2, -1, 0, 1, 2):
                        if abs(dx_l) + abs(dy_l) <= 2:
                            put_px(arr, mask, lx + dx_l, ly + dy_l, (68, 162, 68) if dy_l <= 0 else (48, 128, 52))
                if idx % 2 == 0 and lx == 12:
                    put_px(arr, mask, lx, ly - 1, (252, 158, 192))
                    put_px(arr, mask, lx + 1, ly - 1, (255, 224, 102))
        t = make_crisp_iso_tile((64, 144, 210), (56, 132, 198), (76, 158, 222), (52, 124, 188), 30 + i, lilypad_px)
        atlas.alpha_composite(t, ((12 + i) * 64, 0))

    # ROW 1: Sand Shore (0..3), Sunny Meadow Grass (4..7), Forest Grass (8..11), Interlocking Cobble Path (12..15)
    for i in range(4):
        def sand_px(arr, mask, idx):
            for sx, sy in [(11 + idx, 7), (18 - idx, 9), (14, 11)]:
                put_px(arr, mask, sx, sy, (196, 142, 82))
                put_px(arr, mask, sx + 1, sy, (242, 198, 136))
        t = make_crisp_iso_tile((224, 174, 108), (212, 160, 96), (236, 188, 122), (216, 166, 102), 40 + i, sand_px)
        atlas.alpha_composite(t, (i * 64, 40))

    for i in range(4):
        def meadow_px(arr, mask, idx):
            # Crisp 3-pixel grass blades & clovers
            pts = [(10 + idx, 6), (18 - idx, 7), (13, 10), (20, 9), (15, 5)]
            for gx, gy in pts:
                put_px(arr, mask, gx, gy, (68, 142, 56))
                put_px(arr, mask, gx, gy - 1, (118, 202, 88))
                put_px(arr, mask, gx + 1, gy, (106, 190, 80))
        t = make_crisp_iso_tile((88, 168, 72), (78, 154, 64), (98, 182, 82), (84, 162, 68), 50 + i, meadow_px)
        atlas.alpha_composite(t, ((4 + i) * 64, 40))

    for i in range(4):
        def forest_px(arr, mask, idx):
            pts = [(11 + idx, 6), (17 - idx, 8), (13, 10), (19, 7)]
            for gx, gy in pts:
                put_px(arr, mask, gx, gy, (48, 114, 54))
                put_px(arr, mask, gx, gy - 1, (88, 168, 86))
                put_px(arr, mask, gx + 1, gy, (76, 154, 76))
        t = make_crisp_iso_tile((64, 138, 68), (56, 126, 60), (74, 152, 78), (60, 132, 64), 60 + i, forest_px)
        atlas.alpha_composite(t, ((8 + i) * 64, 40))

    for i in range(4):
        def cobble_road_px(arr, mask, idx):
            # Rich interlocking pixel-art cobblestones scattered across the whole path tile
            stones = [
                (8, 6, 3, 2), (13, 4, 4, 2), (19, 5, 3, 2),
                (6, 8, 3, 2), (11, 7, 4, 3), (17, 8, 4, 2), (22, 8, 3, 2),
                (10, 11, 4, 2), (16, 11, 4, 2), (13, 13, 3, 2),
            ]
            for sx, sy, sw, sh in stones:
                ox = (idx + sy) % 2
                for py in range(sy, sy + sh):
                    for px in range(sx + ox, sx + ox + sw):
                        if (px == sx + ox or py == sy):
                            put_px(arr, mask, px, py, (194, 182, 166))
                        elif (px == sx + ox + sw - 1 or py == sy + sh - 1):
                            put_px(arr, mask, px, py, (112, 92, 74))
                        else:
                            put_px(arr, mask, px, py, (164, 152, 138))
        t = make_crisp_iso_tile((192, 138, 86), (178, 124, 74), (206, 152, 98), (184, 130, 80), 70 + i, cobble_road_px)
        atlas.alpha_composite(t, ((12 + i) * 64, 40))

    # ROW 2: Wooden Bridge (0..3), Watered Soil (4..7), Slate Ground (8..11), Autumn Grass (12..15)
    for i in range(4):
        def bridge_px(arr, mask, idx):
            for y in range(LOG_H):
                for x in range(LOG_W):
                    if mask[y, x]:
                        # Diagonal isometric plank seams every 4 pixels
                        if (x + y * 2) % 5 == 0:
                            arr[y, x, :3] = (98, 56, 28)
                        elif (x + y * 2) % 5 == 1:
                            arr[y, x, :3] = (214, 154, 96)
                        # Top-left and bottom-right wooden guard rails
                        d_top_left = abs((hw - x) * 0.5 + (0 - y))
                        if y <= 3 and x < hw and mask[y, x]:
                            arr[y, x, :3] = (228, 174, 112)
                        elif y >= LOG_H - 3 and x >= hw and mask[y, x]:
                            arr[y, x, :3] = (138, 84, 44)
        t = make_crisp_iso_tile((186, 124, 72), (172, 112, 62), (202, 138, 84), (142, 88, 46), 80 + i, bridge_px)
        atlas.alpha_composite(t, (i * 64, 80))

    for i in range(4):
        t = make_crisp_iso_tile((118, 78, 48), (106, 68, 40), (132, 90, 58), (112, 72, 44), 90 + i)
        atlas.alpha_composite(t, ((4 + i) * 64, 80))

    for i in range(4):
        t = make_crisp_iso_tile((122, 128, 142), (110, 116, 130), (136, 142, 156), (116, 122, 136), 100 + i)
        atlas.alpha_composite(t, ((8 + i) * 64, 80))

    for i in range(4):
        def autumn_px(arr, mask, idx):
            for lx, ly in [(10 + idx, 6), (18 - idx, 8), (14, 10), (20, 7)]:
                col = (238, 126, 48) if (lx + idx) % 2 == 0 else (246, 192, 58)
                put_px(arr, mask, lx, ly, col)
                put_px(arr, mask, lx + 1, ly, col)
        t = make_crisp_iso_tile((124, 166, 64), (112, 152, 56), (138, 180, 74), (118, 160, 60), 110 + i, autumn_px)
        atlas.alpha_composite(t, ((12 + i) * 64, 80))

    # ROW 3: Crisp Pixel-Art Ground Decor Overlays (Wildflowers, Grass Tufts, Mushrooms, Pebbles)
    flower_sets = [
        ((238, 68, 72), (255, 224, 82)),
        ((252, 208, 62), (228, 134, 32)),
        ((250, 162, 196), (255, 242, 188)),
        ((246, 246, 252), (248, 204, 64)),
    ]
    for i, (petal_c, center_c) in enumerate(flower_sets):
        arr = np.zeros((LOG_CELL_H, LOG_W, 4), dtype=np.uint8)
        for fx, fy in [(11, 7), (18, 6), (14, 10), (21, 9)]:
            arr[fy + 1, fx] = (54, 128, 52, 255)
            for ox, oy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                arr[fy + oy, fx + ox] = (*petal_c, 255)
            arr[fy, fx] = (*center_c, 255)
        t = Image.fromarray(arr, "RGBA").resize((64, 40), Image.Resampling.NEAREST)
        atlas.alpha_composite(t, (i * 64, 120))

    for i in range(4):
        arr = np.zeros((LOG_CELL_H, LOG_W, 4), dtype=np.uint8)
        for gx, gy in [(11, 8), (17, 7), (14, 11), (20, 9)]:
            arr[gy, gx] = (54, 132, 52, 255)
            arr[gy - 1, gx - 1] = (78, 164, 68, 255)
            arr[gy - 1, gx] = (98, 186, 80, 255)
            arr[gy - 2, gx] = (118, 202, 92, 255)
            arr[gy - 1, gx + 1] = (78, 164, 68, 255)
        t = Image.fromarray(arr, "RGBA").resize((64, 40), Image.Resampling.NEAREST)
        atlas.alpha_composite(t, ((4 + i) * 64, 120))

    for i in range(4):
        arr = np.zeros((LOG_CELL_H, LOG_W, 4), dtype=np.uint8)
        for mx, my in [(12, 8), (19, 9), (15, 6)]:
            arr[my + 1, mx] = (240, 226, 202, 255)
            for ox in (-1, 0, 1):
                arr[my, mx + ox] = (224, 56, 50, 255)
            arr[my - 1, mx] = (255, 246, 232, 255)
        t = Image.fromarray(arr, "RGBA").resize((64, 40), Image.Resampling.NEAREST)
        atlas.alpha_composite(t, ((8 + i) * 64, 120))

    for i in range(4):
        arr = np.zeros((LOG_CELL_H, LOG_W, 4), dtype=np.uint8)
        for px, py in [(11, 7), (18, 6), (14, 10), (20, 9)]:
            arr[py, px] = (142, 148, 158, 255)
            arr[py, px + 1] = (186, 192, 202, 255)
            arr[py + 1, px] = (108, 114, 124, 255)
        t = Image.fromarray(arr, "RGBA").resize((64, 40), Image.Resampling.NEAREST)
        atlas.alpha_composite(t, ((12 + i) * 64, 120))

    # ROW 4: Sakura Spring Lawn (0..3), Warm Sandstone (4..7), Lush Clover Lawn (8..15)
    for i in range(4):
        def sakura_lawn_px(arr, mask, idx):
            for px, py in [(10 + idx, 6), (18 - idx, 8), (14, 10), (20, 7)]:
                put_px(arr, mask, px, py, (252, 172, 202))
                put_px(arr, mask, px + 1, py, (255, 212, 228))
        t = make_crisp_iso_tile((96, 178, 78), (84, 164, 68), (110, 192, 88), (92, 172, 74), 120 + i, sakura_lawn_px)
        atlas.alpha_composite(t, (i * 64, 160))

    for i in range(4):
        t = make_crisp_iso_tile((210, 158, 108), (196, 144, 96), (224, 172, 122), (204, 152, 104), 130 + i)
        atlas.alpha_composite(t, ((4 + i) * 64, 160))

    for i in range(8):
        t = make_crisp_iso_tile((78, 160, 68), (68, 146, 60), (90, 174, 78), (74, 154, 64), 140 + i)
        atlas.alpha_composite(t, ((8 + i) * 64, 160))

    atlas.save("assets/tilesets/world_tileset.png")
    print("Saved crisp pixel-art assets/tilesets/world_tileset.png")


if __name__ == "__main__":
    build_world_objects()
    build_explorer_spritesheet()
    build_crisp_isometric_tileset()
    print("All crisp low-res pixel-art isometric assets built successfully!")
