#!/usr/bin/env python3
"""
Builds smooth, anti-aliased isometric 2D assets for Godot 4.7 from raw AI sprites:
  1. 19 Natural World Objects (8 Tree varieties + 8 pure natural Rock varieties with NO ore + 3 Forest Props)
     using pre-filtered Gaussian anti-aliasing + LANCZOS resampling so pixels never look harsh or jagged.
  2. Equipment-Free Traveler-Explorer Spritesheet (assets/sprites/player_spritesheet.png, 768x5376, 8 cols x 56 rows)
     with ZERO staff, ZERO backpack, ZERO equipment on the character across all 8 directions and 7 states,
     using C-infinity smooth sinusoidal sub-pixel deformation (no sharp |sin| cusps or frame snaps).
  3. Seamless 4x-Supersampled Isometric Tileset (assets/tilesets/world_tileset.png, 1024x200, 64x40 cells).
"""

import math
import os
import random
from collections import deque
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps

os.makedirs("assets/sprites", exist_ok=True)
os.makedirs("assets/tilesets", exist_ok=True)
os.makedirs("assets/objects", exist_ok=True)
os.makedirs("assets/ui", exist_ok=True)


# =============================================================================
# 0. SMOOTH ANTI-ALIASED BACKGROUND REMOVAL & PRE-FILTERED DOWNSCALING
# =============================================================================
def remove_white_bg_smooth(
    im: Image.Image,
    white_thresh: int = 234,
    chroma_thresh: int = 26,
    min_hole_area: int = 90,
    strip_floor_shadow: bool = False,
) -> Image.Image:
    """
    Removes white background from high-res AI sprites and applies soft anti-aliased
    alpha feathering + color decontamination so edges are velvety smooth.
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
        is_gray_shadow = (yy_grid > int(h * 0.65)) & (min_c >= 115) & ((max_c - min_c) <= 22)
        is_white = is_white | is_gray_shadow

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

    # Smooth alpha contour with Gaussian blur to eliminate staircase/jagged edges
    alpha_f = (~bg_mask).astype(np.float32) * 255.0
    alpha_img = Image.fromarray(alpha_f.astype(np.uint8), "L")
    alpha_smooth = alpha_img.filter(ImageFilter.GaussianBlur(radius=1.15))
    alpha_arr = np.array(alpha_smooth, dtype=np.float32)
    alpha_arr = np.clip((alpha_arr - 42.0) * (255.0 / 213.0), 0.0, 255.0).astype(np.uint8)
    rgba[:, :, 3] = alpha_arr

    # Decontaminate semi-transparent white edge pixels
    edge_zone = (alpha_arr > 0) & (alpha_arr < 225) & (min_c > 195)
    rgba[edge_zone, 0] = (rgba[edge_zone, 0].astype(np.int16) * 7 // 10).astype(np.uint8)
    rgba[edge_zone, 1] = (rgba[edge_zone, 1].astype(np.int16) * 7 // 10).astype(np.uint8)
    rgba[edge_zone, 2] = (rgba[edge_zone, 2].astype(np.int16) * 7 // 10).astype(np.uint8)

    return Image.fromarray(rgba, "RGBA")


def crop_to_alpha(im: Image.Image) -> Image.Image:
    bbox = im.getbbox()
    if not bbox:
        return im
    return im.crop(bbox)


def smooth_prefiltered_resize(im: Image.Image, new_w: int, new_h: int) -> Image.Image:
    """
    Downscales a high-res RGBA image without LANCZOS ringing or harsh pixel staircase artifacts:
    1) Pre-filters RGB with a gentle Gaussian low-pass kernel proportional to downscale ratio
    2) Downscales premultiplied RGBA with LANCZOS
    3) Applies a subtle 0.30px anti-aliasing polish so internal pixel art lines are soft on the eyes.
    """
    cw, ch = im.size
    ratio = max(cw / float(max(1, new_w)), ch / float(max(1, new_h)))
    pre_sigma = max(0.4, min(1.35, ratio * 0.18))

    arr = np.array(im.convert("RGBA"), dtype=np.float32)
    alpha = arr[:, :, 3:4] / 255.0
    pre = arr.copy()
    pre[:, :, :3] *= alpha

    pre_im = Image.fromarray(np.clip(pre, 0, 255).astype(np.uint8), "RGBA")
    pre_im = pre_im.filter(ImageFilter.GaussianBlur(radius=pre_sigma))
    resized_pre = pre_im.resize((new_w, new_h), Image.Resampling.LANCZOS)
    # Gentle post-softening on premultiplied buffer so pixels never look sharp/harsh
    resized_pre = resized_pre.filter(ImageFilter.GaussianBlur(radius=0.32))

    r_arr = np.array(resized_pre, dtype=np.float32)
    r_alpha = r_arr[:, :, 3:4] / 255.0
    rgb_out = np.where(r_alpha > 1e-3, r_arr[:, :, :3] / np.maximum(r_alpha, 1e-3), 0.0)
    out = np.zeros_like(r_arr, dtype=np.uint8)
    out[:, :, :3] = np.clip(rgb_out, 0, 255).astype(np.uint8)
    out[:, :, 3] = np.clip(r_arr[:, :, 3], 0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def fit_smooth_with_iso_shadow(
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

    resized = smooth_prefiltered_resize(cropped, new_w, new_h)

    shadow_layer = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_layer)
    scx = target_w // 2
    scy = target_h - bottom_pad + shadow_y_off
    s_draw.ellipse(
        [scx - shadow_rx, scy - shadow_ry, scx + shadow_rx, scy + shadow_ry],
        fill=(12, 18, 28, 96),
    )
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=3.0))

    paste_x = (target_w - new_w) // 2
    paste_y = target_h - bottom_pad - new_h
    shadow_layer.alpha_composite(resized, (paste_x, paste_y))
    return shadow_layer


# =============================================================================
# 1. PROCESS 19 NATURAL WORLD OBJECT VARIETIES (8 Trees, 8 Pure Rocks, 3 Props)
# =============================================================================
def build_world_objects() -> None:
    print("Building 19 smooth natural world object varieties (8 trees, 8 ore-free rocks, 3 props)...")

    # 8 Natural Tree Varieties
    tree_specs = [
        ("assets/ai_raw/iso_tree_oak.png",         "assets/objects/tree_oak.png",    160, 176, 8, 42, 18, -12, 90),
        ("assets/ai_raw/iso_tree_willow.png",      "assets/objects/tree_willow.png", 168, 176, 8, 46, 19, -12, 90),
        ("assets/ai_raw/iso_tree_pine.png",        "assets/objects/tree_pine.png",   144, 192, 8, 34, 15, -10, 90),
        ("assets/ai_raw/iso_tree_birch.png",       "assets/objects/tree_birch.png",  144, 176, 8, 34, 15, -10, 400),
        ("assets/ai_raw/iso_tree_maple.png",       "assets/objects/tree_maple.png",  160, 176, 8, 42, 18, -12, 90),
        ("assets/ai_raw/iso_tree_cherry.png",      "assets/objects/tree_cherry.png", 168, 176, 8, 44, 18, -12, 500),
        ("assets/ai_raw/iso_tree_ancient_fir.png", "assets/objects/tree_cedar.png",  152, 192, 8, 38, 16, -10, 90),
        ("assets/ai_raw/iso_tree_poplar.png",      "assets/objects/tree_poplar.png", 128, 196, 8, 30, 14, -10, 90),
    ]
    raw_cache = {}
    for src_path, dst_path, tw, th, bpad, srx, sry, syoff, min_hole in tree_specs:
        clean = remove_white_bg_smooth(Image.open(src_path), min_hole_area=min_hole)
        raw_cache[dst_path] = clean
        out = fit_smooth_with_iso_shadow(clean, tw, th, bpad, srx, sry, syoff)
        out.save(dst_path)

    # 8 Pure Natural Rock Varieties (NO ore, NO crystals!)
    rock_specs = [
        ("assets/ai_raw/iso_rock_boulder.png",       "assets/objects/rock_large.png",     112, 96, 6, 42, 18, -12, 90),
        ("assets/ai_raw/iso_rock_slate.png",         "assets/objects/rock_slate.png",     112, 96, 6, 42, 18, -12, 90),
        ("assets/ai_raw/iso_rock_sandstone.png",     "assets/objects/rock_sandstone.png", 116, 96, 6, 44, 19, -12, 80),
        ("assets/ai_raw/iso_rock_mossy_cluster.png", "assets/objects/rock_river.png",     108, 88, 6, 42, 18, -11, 250),
        ("assets/ai_raw/iso_rock_limestone.png",     "assets/objects/rock_limestone.png", 112, 92, 6, 42, 18, -11, 200),
        ("assets/ai_raw/iso_rock_basalt.png",        "assets/objects/rock_basalt.png",    116, 96, 6, 44, 19, -12, 120),
        ("assets/ai_raw/iso_rock_flat_stepping.png", "assets/objects/rock_flat.png",      116, 88, 6, 44, 18, -11, 150),
        ("assets/ai_raw/iso_rock_limestone.png",     "assets/objects/rock_small.png",      72, 60, 5, 26, 11, -7,  200),
    ]
    for src_path, dst_path, tw, th, bpad, srx, sry, syoff, min_hole in rock_specs:
        clean = remove_white_bg_smooth(Image.open(src_path), min_hole_area=min_hole)
        out = fit_smooth_with_iso_shadow(clean, tw, th, bpad, srx, sry, syoff)
        out.save(dst_path)

    # 3 Smooth Forest Props (Stump, Berry Bush, Fallen Log)
    oak_crop = crop_to_alpha(raw_cache["assets/objects/tree_oak.png"])
    ow, oh = oak_crop.size
    trunk_slice = oak_crop.crop((int(ow * 0.24), int(oh * 0.62), int(ow * 0.76), oh))
    stump_hi = fit_smooth_with_iso_shadow(trunk_slice, 128, 112, bottom_pad=10, shadow_rx=46, shadow_ry=20, shadow_y_off=-12)
    s_draw = ImageDraw.Draw(stump_hi)
    s_draw.ellipse([38, 26, 90, 52], fill=(54, 36, 22, 255))
    s_draw.ellipse([42, 28, 86, 50], fill=(214, 168, 112, 255))
    s_draw.ellipse([48, 32, 80, 46], fill=(182, 134, 82, 255))
    s_draw.ellipse([54, 35, 74, 43], fill=(224, 182, 126, 255))
    smooth_prefiltered_resize(stump_hi, 64, 56).save("assets/objects/tree_stump.png")

    canopy_cluster = oak_crop.crop((int(ow * 0.18), int(oh * 0.06), int(ow * 0.82), int(oh * 0.56)))
    bush_hi = fit_smooth_with_iso_shadow(canopy_cluster, 136, 120, bottom_pad=10, shadow_rx=50, shadow_ry=22, shadow_y_off=-14)
    b_draw = ImageDraw.Draw(bush_hi)
    for bx, by in [(44, 48), (60, 36), (80, 40), (92, 56), (52, 68), (70, 60), (86, 72), (36, 64), (66, 46)]:
        b_draw.ellipse([bx - 5, by - 5, bx + 5, by + 5], fill=(165, 24, 36, 255))
        b_draw.ellipse([bx - 4, by - 4, bx + 4, by + 4], fill=(232, 48, 62, 255))
        b_draw.ellipse([bx - 2, by - 3, bx, by - 1], fill=(255, 175, 185, 255))
    smooth_prefiltered_resize(bush_hi, 68, 60).save("assets/objects/bush_berry.png")

    willow_crop = crop_to_alpha(raw_cache["assets/objects/tree_willow.png"])
    ww, wh = willow_crop.size
    bark_slice = willow_crop.crop((int(ww * 0.28), int(wh * 0.55), int(ww * 0.72), int(wh * 0.96)))
    bark_rot = bark_slice.rotate(72, expand=True, resample=Image.Resampling.BICUBIC)
    log_hi = fit_smooth_with_iso_shadow(bark_rot, 192, 112, bottom_pad=12, shadow_rx=74, shadow_ry=24, shadow_y_off=-12)
    l_draw = ImageDraw.Draw(log_hi)
    for mx, my in [(72, 44), (108, 50), (88, 38)]:
        l_draw.rectangle([mx - 2, my, mx + 3, my + 10], fill=(240, 228, 205, 255))
        l_draw.ellipse([mx - 8, my - 7, mx + 9, my + 3], fill=(218, 48, 44, 255))
        l_draw.ellipse([mx - 4, my - 5, mx - 1, my - 2], fill=(255, 245, 230, 255))
        l_draw.ellipse([mx + 2, my - 4, mx + 5, my - 1], fill=(255, 245, 230, 255))
    smooth_prefiltered_resize(log_hi, 96, 56).save("assets/objects/log_fallen.png")


# =============================================================================
# 2. EQUIPMENT-FREE TRAVELER-EXPLORER (ALL 8 TRUE ANGLES, C-INFINITY SMOOTH ANIMS)
# =============================================================================
DIRECTIONS = [
    "down",        # 0: S  (explorer_south.png)
    "down_right",  # 1: SE (explorer_front.png)
    "right",       # 2: E  (explorer_side_stand.png)
    "up_right",    # 3: NE (explorer_back.png)
    "up",          # 4: N  (explorer_diag_up.png)
    "up_left",     # 5: NW (explorer_back.png mirrored)
    "left",        # 6: W  (explorer_side_stand.png mirrored)
    "down_left",   # 7: SW (explorer_front.png mirrored)
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


def normalize_explorer_pose(im: Image.Image, target_h: int = 156) -> Image.Image:
    cropped = crop_to_alpha(im)
    cw, ch = cropped.size
    scale = target_h / float(ch)
    nw = max(1, int(round(cw * scale)))
    return smooth_prefiltered_resize(cropped, nw, target_h)


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


def render_smooth_explorer_frame(
    pose_2x: Image.Image,
    stride_pose_2x: Image.Image,
    dir_name: str,
    anim_name: str,
    frame_idx: int,
    total_frames: int,
) -> Image.Image:
    """
    Renders a single 96x96 frame from 2x supersampled buffer (192x192) using C-infinity
    smooth harmonic curves (no |sin| cusps, no sudden frame snaps, and ZERO equipment).
    """
    SS = 2
    CW, CH = 96 * SS, 96 * SS
    canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))

    phase = (frame_idx / float(total_frames)) * 2.0 * math.pi
    s1 = math.sin(phase)
    c1 = math.cos(phase)
    # C-infinity smooth double-frequency bobbing wave: sin^2(phase) = 0.5 * (1 - cos(2*phase))
    # Replaces sharp |sin(phase)| so velocity never jumps discontinuously!
    smooth_bob = 0.5 * (1.0 - math.cos(2.0 * phase))

    # Smooth bell-curve envelope for non-looping actions (starts at 0, peaks at 1, returns smoothly to 0)
    bell = math.sin((frame_idx / float(total_frames)) * math.pi) ** 2

    dx = -1.0 if "left" in dir_name else (1.0 if "right" in dir_name else 0.0)
    dy = -1.0 if "up" in dir_name else (1.0 if "down" in dir_name else 0.0)

    pw, ph = pose_2x.size
    pad = 28
    buf = Image.new("RGBA", (pw + pad * 2, ph + pad * 2), (0, 0, 0, 0))
    buf.paste(pose_2x, (pad, pad))
    arr = np.array(buf)
    bh, bw, _ = arr.shape

    yy, xx = np.meshgrid(np.arange(bh, dtype=np.float32), np.arange(bw, dtype=np.float32), indexing="ij")
    y_norm = np.clip((yy - pad) / float(max(1, ph)), 0.0, 1.0)
    x_rel = (xx - (bw * 0.5)) / float(max(1, pw * 0.5))

    leg_t = np.clip((y_norm - 0.52) / 0.48, 0.0, 1.0)
    w_leg = 0.5 * (1.0 - np.cos(math.pi * leg_t))
    w_upper = 1.0 - w_leg

    src_x = xx.copy()
    src_y = yy.copy()
    whole_bob_y = 0.0
    shadow_scale = 1.0

    if anim_name == "idle":
        # Gentle C-infinity sinusoidal breathing
        breath = s1 * 1.6
        sway = c1 * 0.6
        src_y -= breath * w_upper
        src_x -= sway * w_upper * (1.0 - y_norm)

    elif anim_name == "walk":
        whole_bob_y = -smooth_bob * 2.4
        shadow_scale = 1.0 - 0.05 * smooth_bob
        side_sign = np.tanh(x_rel * 2.4)
        # Smooth alternating leg lift + subtle horizontal swing
        src_y -= s1 * side_sign * 3.8 * w_leg
        src_x -= s1 * 1.6 * w_leg
        # Gentle upper torso & arm counter-swing
        src_x += s1 * 1.2 * w_upper * (y_norm * 0.8)

    elif anim_name == "run":
        whole_bob_y = -smooth_bob * 3.8 - 0.8
        shadow_scale = 0.92 - 0.07 * smooth_bob
        side_sign = np.tanh(x_rel * 2.4)
        lean_amount = (dx if dx != 0 else 0.3) * 3.2 * (1.0 - y_norm)
        src_x -= lean_amount
        src_y -= s1 * side_sign * 5.0 * w_leg
        src_x -= s1 * 2.2 * w_leg
        src_x += s1 * 1.8 * w_upper * y_norm

    elif anim_name in ("axe", "pickaxe"):
        # Smooth natural body reach/lean gesture (NO equipment drawn on character!)
        swing_wave = math.sin(phase) * bell
        whole_bob_y = -swing_wave * 2.0
        lean = swing_wave * (dx if dx != 0 else 0.4) * 3.6 * w_upper
        src_x -= lean
        src_y -= swing_wave * 2.2 * w_upper

    elif anim_name == "water":
        # Smooth forward bend/reach (NO equipment drawn on character!)
        whole_bob_y = bell * 1.6
        src_x -= bell * (dx if dx != 0 else 0.4) * 3.0 * w_upper
        src_y -= bell * 2.0 * w_upper

    elif anim_name == "interact":
        # Smooth explorer inspection / gathering reach
        whole_bob_y = -bell * 3.0
        src_y += bell * 2.0 * w_upper * np.clip(x_rel, 0.0, 1.0)

    warped_arr = bilinear_warp_rgba(arr, src_x, src_y)
    warped_im = Image.fromarray(warped_arr, "RGBA")

    # Soft ground shadow
    shadow_im = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_im)
    srx = int(30 * shadow_scale)
    sry = int(13 * shadow_scale)
    s_draw.ellipse([96 - srx, 168 - sry, 96 + srx, 168 + sry], fill=(10, 14, 24, 95))
    shadow_im = shadow_im.filter(ImageFilter.GaussianBlur(radius=2.6))
    canvas.alpha_composite(shadow_im)

    paste_x = (CW - bw) // 2
    paste_y = int(round(172 - pad - ph + whole_bob_y))
    canvas.alpha_composite(warped_im, (paste_x, paste_y))

    return smooth_prefiltered_resize(canvas, 96, 96)


def build_explorer_spritesheet() -> None:
    print("Building Smooth Equipment-Free Explorer Spritesheet (8 true angles x 56 rows x 8 frames)...")
    south_clean = remove_white_bg_smooth(Image.open("assets/ai_raw/explorer_south.png"), min_hole_area=120, strip_floor_shadow=True)
    front_clean = remove_white_bg_smooth(Image.open("assets/ai_raw/explorer_front.png"), min_hole_area=120, strip_floor_shadow=True)
    side_stand_clean = remove_white_bg_smooth(Image.open("assets/ai_raw/explorer_side_stand.png"), min_hole_area=120, strip_floor_shadow=True)
    side_stride_clean = remove_white_bg_smooth(Image.open("assets/ai_raw/explorer_side.png"), min_hole_area=120, strip_floor_shadow=True)
    back_clean = remove_white_bg_smooth(Image.open("assets/ai_raw/explorer_back.png"), min_hole_area=120, strip_floor_shadow=True)
    up_clean = remove_white_bg_smooth(Image.open("assets/ai_raw/explorer_diag_up.png"), min_hole_area=120, strip_floor_shadow=True)

    p_south = normalize_explorer_pose(south_clean, target_h=156)
    p_front_right = normalize_explorer_pose(front_clean, target_h=156)
    p_front_left = p_front_right.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    p_side_right = normalize_explorer_pose(side_stand_clean, target_h=156)
    p_side_left = p_side_right.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    p_stride_right = normalize_explorer_pose(side_stride_clean, target_h=156)
    p_stride_left = p_stride_right.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    p_back_right = normalize_explorer_pose(back_clean, target_h=156)
    p_back_left = p_back_right.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    p_up = normalize_explorer_pose(up_clean, target_h=156)

    dir_poses = {
        "down":       p_south,
        "down_right": p_front_right,
        "right":      p_side_right,
        "up_right":   p_back_right,
        "up":         p_up,
        "up_left":    p_back_left,
        "left":       p_side_left,
        "down_left":  p_front_left,
    }
    stride_poses = {
        "right": p_stride_right,
        "left":  p_stride_left,
    }

    cols = 8
    rows = len(ANIMATIONS) * len(DIRECTIONS)  # 56 rows
    frame_size = 96
    sheet = Image.new("RGBA", (cols * frame_size, rows * frame_size), (0, 0, 0, 0))
    showcase = Image.new("RGBA", (len(DIRECTIONS) * frame_size, len(ANIMATIONS) * frame_size), (24, 30, 42, 255))
    sc_draw = ImageDraw.Draw(showcase)

    row_idx = 0
    for a_idx, (anim_name, frame_count) in enumerate(ANIMATIONS):
        sample_f = 2 if anim_name != "idle" else 0
        for d_idx, dir_name in enumerate(DIRECTIONS):
            pose_2x = dir_poses[dir_name]
            s_pose_2x = stride_poses.get(dir_name)
            for col_idx in range(cols):
                frame_im = render_smooth_explorer_frame(pose_2x, s_pose_2x, dir_name, anim_name, col_idx, frame_count)
                sheet.alpha_composite(frame_im, (col_idx * frame_size, row_idx * frame_size))
                if col_idx == sample_f:
                    cx0, cy0 = d_idx * frame_size, a_idx * frame_size
                    bg_col = (34, 42, 56, 255) if (a_idx + d_idx) % 2 == 0 else (28, 35, 48, 255)
                    sc_draw.rectangle([cx0 + 1, cy0 + 1, cx0 + frame_size - 2, cy0 + frame_size - 2], fill=bg_col)
                    showcase.alpha_composite(frame_im, (cx0, cy0))
            row_idx += 1

    sheet.save("assets/sprites/player_spritesheet.png")
    showcase.save("assets/sprites/player_8dir_showcase.png")

    icon = Image.new("RGBA", (128, 128), (36, 94, 152, 255))
    idraw = ImageDraw.Draw(icon)
    idraw.ellipse([12, 78, 116, 118], fill=(224, 196, 138, 255))
    idraw.ellipse([18, 80, 110, 114], fill=(82, 162, 76, 255))
    hero_icon = render_smooth_explorer_frame(p_front_right, None, "down_right", "idle", 0, 8)
    icon.alpha_composite(hero_icon, (16, 16))
    icon.save("icon.png")
    print(f"Saved smooth Explorer spritesheet ({sheet.size[0]}x{sheet.size[1]})")


# =============================================================================
# 3. 4X-SUPERSAMPLED VELVETY-SMOOTH ISOMETRIC TILESET (1024x200)
# =============================================================================
def build_smooth_isometric_tileset() -> None:
    print("Building 4x-Supersampled Smooth Isometric Tileset (1024x200)...")
    TILE_W = 64
    TILE_H = 32
    SKIRT_H = 8
    CELL_H = TILE_H + SKIRT_H  # 40
    COLS, ROWS = 16, 5

    SS = 4
    SW, SH, S_TILE_H, S_SKIRT = TILE_W * SS, CELL_H * SS, TILE_H * SS, SKIRT_H * SS
    hw = SW / 2.0
    hh = S_TILE_H / 2.0

    yy, xx = np.meshgrid(np.arange(SH, dtype=np.float32), np.arange(SW, dtype=np.float32), indexing="ij")
    dx = np.abs(xx + 0.5 - hw) / hw
    dy = np.abs(yy + 0.5 - hh) / hh
    dist_diamond = dx + dy

    # Soft anti-aliased diamond top mask with slight 1.015 bleed so adjacent tiles never leave hairline gaps
    diamond_alpha = np.clip((1.018 - dist_diamond) * 28.0, 0.0, 1.0)
    diamond_alpha[yy >= S_TILE_H] = 0.0

    bot_y_at_x = hh + (1.0 - dx) * hh
    in_skirt = (yy >= bot_y_at_x - 2.0) & (yy < bot_y_at_x + S_SKIRT) & (dx <= 1.0)
    left_skirt = in_skirt & (xx < hw)
    right_skirt = in_skirt & (xx >= hw)

    def make_smooth_iso_tile(
        base_rgb: tuple,
        accent_rgb: tuple,
        left_skirt_rgb: tuple,
        right_skirt_rgb: tuple,
        seed_offset: int,
        detail_fn=None,
    ) -> Image.Image:
        phase1 = (seed_offset * 1.7) % 6.28
        phase2 = (seed_offset * 2.9) % 6.28
        wave = (
            np.sin(xx * 0.035 + yy * 0.055 + phase1) * 0.5
            + np.cos(xx * 0.028 - yy * 0.065 + phase2) * 0.5
        )
        blend = np.clip((wave + 1.0) * 0.5, 0.0, 1.0)
        sun = ((hw - xx) * 0.035 + (hh - yy) * 0.08)

        arr = np.zeros((SH, SW, 4), dtype=np.uint8)
        for c_i in range(3):
            top_c = base_rgb[c_i] * (1.0 - blend) + accent_rgb[c_i] * blend + sun
            col_plane = np.zeros((SH, SW), dtype=np.float32)
            col_plane = np.where(left_skirt, left_skirt_rgb[c_i], col_plane)
            col_plane = np.where(right_skirt, right_skirt_rgb[c_i], col_plane)
            col_plane = np.where(diamond_alpha > 0.01, top_c, col_plane)
            arr[:, :, c_i] = np.clip(col_plane, 0.0, 255.0).astype(np.uint8)

        alpha_plane = np.where(in_skirt, 255.0, diamond_alpha * 255.0)
        arr[:, :, 3] = np.clip(alpha_plane, 0.0, 255.0).astype(np.uint8)

        im = Image.fromarray(arr, "RGBA")
        if detail_fn is not None:
            detail_fn(ImageDraw.Draw(im), seed_offset)
        # Soft blur at 4x supersample before LANCZOS downscale for velvety-smooth tiles
        im = im.filter(ImageFilter.GaussianBlur(radius=1.1))
        return im.resize((TILE_W, CELL_H), Image.Resampling.LANCZOS)

    atlas = Image.new("RGBA", (COLS * TILE_W, ROWS * CELL_H), (0, 0, 0, 0))

    # ROW 0: Smooth Water Tiles (Deep Lake, Shallow Turquoise, Flowing River, Lilypads)
    for i in range(4):
        def deep_ripples(d: ImageDraw.ImageDraw, idx: int):
            for wy in (40, 64, 88):
                wx = 84 + ((idx * 22 + wy) % 68)
                d.arc([wx, wy - 8, wx + 44, wy + 12], start=200, end=340, fill=(108, 176, 238, 140), width=4)
        t = make_smooth_iso_tile((32, 84, 152), (44, 104, 176), (26, 70, 132), (22, 60, 118), i, deep_ripples)
        atlas.alpha_composite(t, (i * TILE_W, 0))

    for i in range(4):
        def shallow_ripples(d: ImageDraw.ImageDraw, idx: int):
            for wy in (36, 60, 84):
                wx = 76 + ((idx * 26 + wy) % 76)
                d.arc([wx, wy - 8, wx + 48, wy + 12], start=200, end=340, fill=(175, 234, 255, 155), width=4)
        t = make_smooth_iso_tile((56, 138, 202), (76, 162, 220), (46, 118, 178), (40, 106, 164), 10 + i, shallow_ripples)
        atlas.alpha_composite(t, ((4 + i) * TILE_W, 0))

    for i in range(4):
        def river_ripples(d: ImageDraw.ImageDraw, idx: int):
            for rx, ry in [(88, 44), (128, 64), (104, 84), (152, 56)]:
                ox = ((idx * 14) % 32) - 16
                d.line([(rx + ox, ry), (rx + ox + 32, ry + 14)], fill=(195, 240, 255, 160), width=4)
        t = make_smooth_iso_tile((50, 128, 192), (70, 152, 214), (42, 110, 170), (36, 98, 156), 20 + i, river_ripples)
        atlas.alpha_composite(t, ((8 + i) * TILE_W, 0))

    for i in range(4):
        def lilypad_detail(d: ImageDraw.ImageDraw, idx: int):
            for lx, ly in [(100, 56), (156, 72)]:
                d.ellipse([lx - 22, ly - 11, lx + 22, ly + 11], fill=(64, 152, 74, 255), outline=(38, 96, 46, 210), width=3)
                if idx % 2 == 0 and lx == 100:
                    d.ellipse([lx - 9, ly - 11, lx + 9, ly + 3], fill=(248, 162, 192, 255))
                    d.ellipse([lx - 4, ly - 6, lx + 4, ly], fill=(255, 232, 108, 255))
        t = make_smooth_iso_tile((56, 138, 202), (76, 162, 220), (46, 118, 178), (40, 106, 164), 30 + i, lilypad_detail)
        atlas.alpha_composite(t, ((12 + i) * TILE_W, 0))

    # ROW 1: Sand Shore (0..3), Sunlit Meadow Grass (4..7), Emerald Forest Grass (8..11), Cobblestone Road (12..15)
    # Harmonious skirts prevent dark grid lines between adjacent ground tiles!
    for i in range(4):
        t = make_smooth_iso_tile((224, 198, 142), (236, 212, 158), (204, 178, 124), (192, 166, 114), 40 + i)
        atlas.alpha_composite(t, (i * TILE_W, CELL_H))

    for i in range(4):
        def meadow_blades(d: ImageDraw.ImageDraw, idx: int):
            for gx, gy in [(88 + idx * 8, 56), (144, 48 + idx * 4), (116, 80), (164 - idx * 6, 68)]:
                d.line([(gx, gy), (gx - 5, gy - 11)], fill=(108, 186, 82, 170), width=3)
                d.line([(gx + 4, gy), (gx + 7, gy - 12)], fill=(122, 198, 92, 170), width=3)
        t = make_smooth_iso_tile((82, 158, 66), (98, 174, 78), (72, 142, 58), (64, 130, 52), 50 + i, meadow_blades)
        atlas.alpha_composite(t, ((4 + i) * TILE_W, CELL_H))

    for i in range(4):
        def forest_clover(d: ImageDraw.ImageDraw, idx: int):
            for mx, my in [(96, 52 + idx * 4), (152, 68), (120 + idx * 4, 84)]:
                d.ellipse([mx - 12, my - 6, mx + 12, my + 6], fill=(66, 142, 72, 165))
        t = make_smooth_iso_tile((52, 118, 60), (66, 136, 72), (46, 106, 52), (40, 96, 46), 60 + i, forest_clover)
        atlas.alpha_composite(t, ((8 + i) * TILE_W, CELL_H))

    for i in range(4):
        def road_cobble(d: ImageDraw.ImageDraw, idx: int):
            stones = [(96, 52, 20, 10), (140, 44, 22, 10), (116, 72, 24, 12), (164, 68, 18, 10), (88, 76, 16, 8)]
            for sx, sy, srw, srh in stones:
                ox = (idx % 2) * 8 - 4
                d.ellipse([sx + ox - srw, sy - srh, sx + ox + srw, sy + srh], fill=(144, 138, 132, 215), outline=(92, 84, 76, 180), width=3)
        t = make_smooth_iso_tile((162, 128, 92), (176, 142, 104), (144, 112, 78), (132, 102, 70), 70 + i, road_cobble)
        atlas.alpha_composite(t, ((12 + i) * TILE_W, CELL_H))

    # ROW 2: Wooden Bridge (0..3), Watered Soil (4..7), Highland Slate (8..11), Autumn Maple/Birch Grass (12..15)
    for i in range(4):
        def bridge_deck(d: ImageDraw.ImageDraw, idx: int):
            for step in range(-72, 88, 24):
                d.line([(128 + step - 48, 64 + step // 2 - 24), (128 + step + 48, 64 + step // 2 + 24)], fill=(92, 60, 34, 190), width=4)
            d.line([(16, 60), (128, 8)], fill=(216, 168, 110, 255), width=7)
            d.line([(128, 116), (240, 60)], fill=(134, 90, 50, 255), width=7)
        t = make_smooth_iso_tile((172, 122, 76), (188, 138, 88), (136, 92, 52), (116, 76, 42), 80 + i, bridge_deck)
        atlas.alpha_composite(t, (i * TILE_W, CELL_H * 2))

    for i in range(4):
        t = make_smooth_iso_tile((48, 112, 76), (60, 128, 88), (42, 98, 66), (36, 88, 58), 90 + i)
        atlas.alpha_composite(t, ((4 + i) * TILE_W, CELL_H * 2))

    for i in range(4):
        t = make_smooth_iso_tile((98, 108, 122), (114, 126, 140), (86, 96, 108), (76, 86, 98), 100 + i)
        atlas.alpha_composite(t, ((8 + i) * TILE_W, CELL_H * 2))

    for i in range(4):
        def autumn_leaves(d: ImageDraw.ImageDraw, idx: int):
            for lx, ly in [(92 + idx * 8, 60), (144, 52 + idx * 4), (120, 80), (168 - idx * 8, 64)]:
                col = (238, 142, 52, 200) if (lx + idx) % 2 == 0 else (244, 196, 64, 200)
                d.ellipse([lx - 8, ly - 4, lx + 8, ly + 4], fill=col)
        t = make_smooth_iso_tile((106, 150, 60), (126, 168, 68), (94, 136, 52), (84, 124, 46), 110 + i, autumn_leaves)
        atlas.alpha_composite(t, ((12 + i) * TILE_W, CELL_H * 2))

    # ROW 3: Smooth Ground Decor Overlays (Flowers, Soft Grass Tufts, Forest Mushrooms, River Pebbles)
    flower_sets = [
        ((238, 72, 78, 240), (255, 224, 86, 245)),
        ((252, 212, 66, 240), (232, 142, 38, 245)),
        ((248, 168, 198, 240), (255, 242, 192, 245)),
        ((248, 248, 252, 240), (250, 206, 72, 245)),
    ]
    for i, (petal_c, center_c) in enumerate(flower_sets):
        t = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
        d = ImageDraw.Draw(t)
        for fx, fy in [(88, 56), (136, 44), (112, 76), (168, 64), (132, 88)]:
            d.line([(fx, fy + 4), (fx, fy + 18)], fill=(58, 136, 58, 215), width=4)
            d.ellipse([fx - 10, fy - 8, fx + 10, fy + 8], fill=petal_c)
            d.ellipse([fx - 4, fy - 4, fx + 4, fy + 4], fill=center_c)
        t = t.filter(ImageFilter.GaussianBlur(radius=1.0))
        atlas.alpha_composite(t.resize((TILE_W, CELL_H), Image.Resampling.LANCZOS), (i * TILE_W, CELL_H * 3))

    for i in range(4):
        t = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
        d = ImageDraw.Draw(t)
        for gx, gy in [(88, 68), (128, 56), (160, 76), (112, 88)]:
            d.line([(gx, gy), (gx - 12, gy - 22)], fill=(62, 142, 62, 210), width=4)
            d.line([(gx + 4, gy), (gx + 4, gy - 26)], fill=(88, 174, 76, 210), width=4)
            d.line([(gx + 8, gy), (gx + 20, gy - 20)], fill=(116, 198, 92, 210), width=4)
        t = t.filter(ImageFilter.GaussianBlur(radius=1.0))
        atlas.alpha_composite(t.resize((TILE_W, CELL_H), Image.Resampling.LANCZOS), ((4 + i) * TILE_W, CELL_H * 3))

    for i in range(4):
        t = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
        d = ImageDraw.Draw(t)
        for mx, my in [(96, 60), (148, 72), (124, 48)]:
            d.rectangle([mx - 4, my, mx + 4, my + 16], fill=(242, 230, 208, 245))
            d.ellipse([mx - 14, my - 10, mx + 14, my + 4], fill=(222, 60, 56, 245))
            d.ellipse([mx - 6, my - 6, mx - 2, my - 2], fill=(255, 248, 235, 245))
            d.ellipse([mx + 4, my - 4, mx + 8, my], fill=(255, 248, 235, 245))
        t = t.filter(ImageFilter.GaussianBlur(radius=1.0))
        atlas.alpha_composite(t.resize((TILE_W, CELL_H), Image.Resampling.LANCZOS), ((8 + i) * TILE_W, CELL_H * 3))

    for i in range(4):
        t = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
        d = ImageDraw.Draw(t)
        for px, py in [(92, 60), (144, 52), (124, 80), (168, 68)]:
            d.ellipse([px - 14, py - 8, px + 14, py + 8], fill=(142, 152, 164, 225))
            d.ellipse([px - 8, py - 6, px + 4, py + 2], fill=(188, 198, 210, 225))
        t = t.filter(ImageFilter.GaussianBlur(radius=1.0))
        atlas.alpha_composite(t.resize((TILE_W, CELL_H), Image.Resampling.LANCZOS), ((12 + i) * TILE_W, CELL_H * 3))

    # ROW 4: Additional Biome Varieties (Cherry Blossom Lawn 0..3, Warm Sandstone Ground 4..7, Lush Clover 8..15)
    for i in range(4):
        def blossom_petals(d: ImageDraw.ImageDraw, idx: int):
            for px, py in [(88 + idx * 8, 56), (148, 48 + idx * 4), (116, 76), (164 - idx * 6, 68)]:
                d.ellipse([px - 6, py - 4, px + 6, py + 4], fill=(250, 178, 206, 205))
        t = make_smooth_iso_tile((86, 162, 76), (104, 178, 88), (76, 146, 66), (68, 134, 58), 120 + i, blossom_petals)
        atlas.alpha_composite(t, (i * TILE_W, CELL_H * 4))

    for i in range(4):
        t = make_smooth_iso_tile((198, 152, 108), (214, 168, 122), (178, 134, 92), (164, 122, 82), 130 + i)
        atlas.alpha_composite(t, ((4 + i) * TILE_W, CELL_H * 4))

    for i in range(8):
        t = make_smooth_iso_tile((68, 144, 62), (84, 162, 74), (58, 128, 54), (52, 116, 48), 140 + i)
        atlas.alpha_composite(t, ((8 + i) * TILE_W, CELL_H * 4))

    atlas.save("assets/tilesets/world_tileset.png")
    print("Saved 4x-supersampled smooth assets/tilesets/world_tileset.png")


if __name__ == "__main__":
    build_world_objects()
    build_explorer_spritesheet()
    build_smooth_isometric_tileset()
    print("All smooth high-res assets built successfully!")
