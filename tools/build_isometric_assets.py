#!/usr/bin/env python3
"""
Smooth High-Resolution Isometric Asset Builder for Stardw (Godot 4.7).
Fixes jagged nearest-neighbor pixels and sharp animations by using:
1. LANCZOS anti-aliased downsampling + soft alpha contour feathering.
2. Equipment-free Traveler-Explorer character (from `assets/ai_raw/explorer_*.png`)
   with 8-frame sub-pixel bilinear-warped animations across all 8 directions x 7 states.
3. Expanded World Object Varieties (15 distinct objects in `assets/objects/`):
   - 7 Tree Varieties:
     * tree_oak.png (Ancient Oak)
     * tree_willow.png (Weeping Willow)
     * tree_pine.png (Northern Pine)
     * tree_birch.png (Golden Birch)
     * tree_maple.png (Autumn Red-Orange Maple)
     * tree_cherry.png (Blossoming Pink Cherry Tree)
     * tree_cedar.png (Mossy Woodland Cedar Fir)
   - 5 Rock Varieties:
     * rock_large.png (Mossy Granite Boulder)
     * rock_slate.png (Dark Slate Formation)
     * rock_sandstone.png (Warm Ochre Sandstone Formation)
     * rock_river.png (Mossy River Boulder Cluster with Flowers)
     * rock_ore.png (Amber/Gold Crystal Ore)
     * rock_crystal.png (Violet Amethyst & Quartz Geode Rock)
     * rock_small.png (Small Mossy Fieldstone)
   - 3 Forest Props:
     * tree_stump.png, bush_berry.png, log_fallen.png
4. Supersampled Smooth Isometric Tileset (`assets/tilesets/world_tileset.png`, 1024x200).
"""

from collections import deque
import math
import os
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

os.makedirs("assets/objects", exist_ok=True)
os.makedirs("assets/sprites", exist_ok=True)
os.makedirs("assets/tilesets", exist_ok=True)
os.makedirs("assets/ui", exist_ok=True)


def remove_white_bg_smart(
    im: Image.Image,
    white_thresh: int = 234,
    chroma_thresh: int = 26,
    min_hole_area: int = 90,
    strip_floor_shadow: bool = False,
) -> Image.Image:
    """
    Removes white background from AI sprites using:
    1) Exterior border BFS flood-fill
    2) Enclosed white background hole removal ONLY for holes >= min_hole_area pixels
       (removes background gaps between legs/arms/roots while preserving shirt fabric,
       eyes, blossoms, and highlights!)
    3) Soft anti-aliased alpha edge feathering so edges never look jagged.
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
        # Also treat neutral-gray floor shadow on white background as background
        yy_grid = np.arange(h)[:, None]
        is_gray_shadow = (yy_grid > int(h * 0.65)) & (min_c >= 115) & ((max_c - min_c) <= 22)
        is_white = is_white | is_gray_shadow

    visited = np.zeros((h, w), dtype=bool)
    bg_mask = np.zeros((h, w), dtype=bool)

    # Connected components of white pixels
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

    # Soften 1-2px bright halo along the exterior boundary
    alpha_f = (~bg_mask).astype(np.float32) * 255.0
    alpha_img = Image.fromarray(alpha_f.astype(np.uint8), "L")
    # Slight morphological erosion + Gaussian feather on alpha channel for smooth anti-aliased silhouette
    alpha_smooth = alpha_img.filter(ImageFilter.GaussianBlur(radius=0.75))
    alpha_arr = np.array(alpha_smooth, dtype=np.float32)
    alpha_arr = np.clip((alpha_arr - 38.0) * (255.0 / 217.0), 0.0, 255.0).astype(np.uint8)
    rgba[:, :, 3] = alpha_arr

    # Darken any remaining semi-transparent white fringe pixels so they don't glow white
    edge_zone = (alpha_arr > 0) & (alpha_arr < 220) & (min_c > 200)
    rgba[edge_zone, 0] = (rgba[edge_zone, 0].astype(np.int16) * 7 // 10).astype(np.uint8)
    rgba[edge_zone, 1] = (rgba[edge_zone, 1].astype(np.int16) * 7 // 10).astype(np.uint8)
    rgba[edge_zone, 2] = (rgba[edge_zone, 2].astype(np.int16) * 7 // 10).astype(np.uint8)

    return Image.fromarray(rgba, "RGBA")


def crop_to_alpha(im: Image.Image) -> Image.Image:
    bbox = im.getbbox()
    if not bbox:
        return im
    return im.crop(bbox)


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

    # Use LANCZOS anti-aliased resampling so textures are smooth and never jagged!
    resized = cropped.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # Render soft blurred isometric shadow under base
    shadow_layer = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_layer)
    scx = target_w // 2
    scy = target_h - bottom_pad + shadow_y_off
    s_draw.ellipse(
        [scx - shadow_rx, scy - shadow_ry, scx + shadow_rx, scy + shadow_ry],
        fill=(10, 14, 24, 115),
    )
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=2.2))

    paste_x = (target_w - new_w) // 2
    paste_y = target_h - bottom_pad - new_h
    shadow_layer.alpha_composite(resized, (paste_x, paste_y))
    return shadow_layer


# =============================================================================
# 1. PROCESS ALL 15 AI WORLD OBJECT VARIETIES (7 Trees, 7 Rocks, 3 Props)
# =============================================================================
def build_world_objects() -> None:
    print("Building 15 smooth high-res AI world object varieties (7 trees, 7 rocks, props)...")

    # Trees (7 varieties)
    tree_specs = [
        ("assets/ai_raw/iso_tree_oak.png",         "assets/objects/tree_oak.png",    160, 176, 8, 42, 18, -12, 90),
        ("assets/ai_raw/iso_tree_willow.png",      "assets/objects/tree_willow.png", 168, 176, 8, 46, 19, -12, 90),
        ("assets/ai_raw/iso_tree_pine.png",        "assets/objects/tree_pine.png",   144, 192, 8, 34, 15, -10, 90),
        ("assets/ai_raw/iso_tree_birch.png",       "assets/objects/tree_birch.png",  144, 176, 8, 34, 15, -10, 400),
        ("assets/ai_raw/iso_tree_maple.png",       "assets/objects/tree_maple.png",  160, 176, 8, 42, 18, -12, 90),
        ("assets/ai_raw/iso_tree_cherry.png",      "assets/objects/tree_cherry.png", 168, 176, 8, 44, 18, -12, 500),
        ("assets/ai_raw/iso_tree_ancient_fir.png", "assets/objects/tree_cedar.png",  152, 192, 8, 38, 16, -10, 90),
    ]
    raw_cache = {}
    for src_path, dst_path, tw, th, bpad, srx, sry, syoff, min_hole in tree_specs:
        clean = remove_white_bg_smart(Image.open(src_path), min_hole_area=min_hole)
        raw_cache[dst_path] = clean
        out = fit_smooth_with_iso_shadow(clean, tw, th, bpad, srx, sry, syoff)
        out.save(dst_path)

    # Rocks (7 varieties: large granite, dark slate, warm sandstone, mossy river cluster, amber ore, amethyst crystal, small rock)
    rock_specs = [
        ("assets/ai_raw/iso_rock_boulder.png",       "assets/objects/rock_large.png",     112, 96, 6, 42, 18, -12, 90),
        ("assets/ai_raw/iso_rock_slate.png",         "assets/objects/rock_slate.png",     112, 96, 6, 42, 18, -12, 90),
        ("assets/ai_raw/iso_rock_sandstone.png",     "assets/objects/rock_sandstone.png", 116, 96, 6, 44, 19, -12, 80),
        ("assets/ai_raw/iso_rock_mossy_cluster.png", "assets/objects/rock_river.png",     108, 88, 6, 42, 18, -11, 250),
        ("assets/ai_raw/iso_rock_crystal_ore.png",   "assets/objects/rock_ore.png",        88, 76, 6, 32, 15, -10, 200),
        ("assets/ai_raw/iso_rock_amethyst.png",      "assets/objects/rock_crystal.png",    96, 84, 6, 36, 16, -11, 300),
        ("assets/ai_raw/iso_rock_mossy_cluster.png", "assets/objects/rock_small.png",      68, 58, 5, 25, 11, -7,  250),
    ]
    for src_path, dst_path, tw, th, bpad, srx, sry, syoff, min_hole in rock_specs:
        clean = remove_white_bg_smart(Image.open(src_path), min_hole_area=min_hole)
        out = fit_smooth_with_iso_shadow(clean, tw, th, bpad, srx, sry, syoff)
        out.save(dst_path)

    # Props (Stump, Berry Bush, Fallen Log) smoothed with LANCZOS
    oak_crop = crop_to_alpha(raw_cache["assets/objects/tree_oak.png"])
    ow, oh = oak_crop.size
    trunk_slice = oak_crop.crop((int(ow * 0.24), int(oh * 0.62), int(ow * 0.76), oh))
    stump_hi = fit_smooth_with_iso_shadow(trunk_slice, 128, 112, bottom_pad=10, shadow_rx=46, shadow_ry=20, shadow_y_off=-12)
    s_draw = ImageDraw.Draw(stump_hi)
    s_draw.ellipse([38, 26, 90, 52], fill=(54, 36, 22, 255))
    s_draw.ellipse([42, 28, 86, 50], fill=(214, 168, 112, 255))
    s_draw.ellipse([48, 32, 80, 46], fill=(182, 134, 82, 255))
    s_draw.ellipse([54, 35, 74, 43], fill=(224, 182, 126, 255))
    stump_hi.resize((64, 56), Image.Resampling.LANCZOS).save("assets/objects/tree_stump.png")

    canopy_cluster = oak_crop.crop((int(ow * 0.18), int(oh * 0.06), int(ow * 0.82), int(oh * 0.56)))
    bush_hi = fit_smooth_with_iso_shadow(canopy_cluster, 136, 120, bottom_pad=10, shadow_rx=50, shadow_ry=22, shadow_y_off=-14)
    b_draw = ImageDraw.Draw(bush_hi)
    for bx, by in [(44, 48), (60, 36), (80, 40), (92, 56), (52, 68), (70, 60), (86, 72), (36, 64), (66, 46)]:
        b_draw.ellipse([bx - 5, by - 5, bx + 5, by + 5], fill=(165, 24, 36, 255))
        b_draw.ellipse([bx - 4, by - 4, bx + 4, by + 4], fill=(232, 48, 62, 255))
        b_draw.ellipse([bx - 2, by - 3, bx, by - 1], fill=(255, 175, 185, 255))
    bush_hi.resize((68, 60), Image.Resampling.LANCZOS).save("assets/objects/bush_berry.png")

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
    log_hi.resize((96, 56), Image.Resampling.LANCZOS).save("assets/objects/log_fallen.png")


# =============================================================================
# 2. SMOOTH SUB-PIXEL WARPED TRAVELER-EXPLORER (NO GEAR, 8 FRAMES PER ANIM)
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


def normalize_explorer_pose(im: Image.Image, target_h: int = 156) -> Image.Image:
    """Normalizes the Explorer sprite at 2x supersampled height (156px -> 78px on 96x96 canvas) with LANCZOS."""
    cropped = crop_to_alpha(im)
    cw, ch = cropped.size
    scale = target_h / float(ch)
    nw = max(1, int(round(cw * scale)))
    return cropped.resize((nw, target_h), Image.Resampling.LANCZOS)


def bilinear_warp_rgba(arr: np.ndarray, src_x: np.ndarray, src_y: np.ndarray) -> np.ndarray:
    """Smooth sub-pixel bilinear sampler for continuous deformation without seam lines or pixel popping."""
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
    # Premultiply RGB by alpha before interpolating so edges never bleed dark/white fringes
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
    dir_name: str,
    anim_name: str,
    frame_idx: int,
    total_frames: int,
) -> Image.Image:
    """
    Renders a single frame at 2x supersampled resolution (192x192) using continuous
    sinusoidal deformation fields, then downscales with LANCZOS to 96x96.
    """
    SS = 2  # Supersampling factor (192x192 -> 96x96)
    CW, CH = 96 * SS, 96 * SS
    canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))

    phase = (frame_idx / float(total_frames)) * 2.0 * math.pi
    s1 = math.sin(phase)
    c1 = math.cos(phase)
    s2 = math.sin(2.0 * phase)
    c2 = math.cos(2.0 * phase)

    dx = -1.0 if "left" in dir_name else (1.0 if "right" in dir_name else 0.0)
    dy = -1.0 if "up" in dir_name else (1.0 if "down" in dir_name else 0.0)

    # Place pose_2x on a padded working buffer for smooth continuous warping
    pw, ph = pose_2x.size
    pad = 28
    buf = Image.new("RGBA", (pw + pad * 2, ph + pad * 2), (0, 0, 0, 0))
    buf.paste(pose_2x, (pad, pad))
    arr = np.array(buf)
    bh, bw, _ = arr.shape

    yy, xx = np.meshgrid(np.arange(bh, dtype=np.float32), np.arange(bw, dtype=np.float32), indexing="ij")
    # Normalized coordinates within character body (y_norm: 0 at head top, 1 at boot bottom)
    y_norm = np.clip((yy - pad) / float(max(1, ph)), 0.0, 1.0)
    x_rel = (xx - (bw * 0.5)) / float(max(1, pw * 0.5))  # -1 (left) .. +1 (right)

    # Smooth cosine weights for lower body (legs: y_norm > 0.50) and upper body (torso/arms: y_norm < 0.65)
    leg_t = np.clip((y_norm - 0.50) / 0.50, 0.0, 1.0)
    w_leg = 0.5 * (1.0 - np.cos(math.pi * leg_t))  # 0 above hips, smoothly 1 at boots
    w_upper = 1.0 - w_leg

    src_x = xx.copy()
    src_y = yy.copy()
    whole_bob_y = 0.0
    shadow_scale = 1.0
    is_side_profile = dir_name in ("right", "left")

    # In explorer_side.png, the raw pose is captured mid-stride.
    # For standing states (idle, tools, interact), smoothly bring the feet together under the hips!
    if is_side_profile and anim_name not in ("walk", "run"):
        cx_body = bw * 0.5
        # Divide x offset from center by 0.58 in leg region -> compresses wide stride into relaxed standing stance
        leg_compress = 1.0 - 0.42 * w_leg
        src_x = cx_body + (xx - cx_body) / np.maximum(leg_compress, 0.35)

    if anim_name == "idle":
        # Gentle sinusoidal breathing of chest & head, boots stay planted
        breath = s1 * 2.0
        sway = c1 * 0.8
        src_y -= breath * w_upper
        src_x -= sway * w_upper * (1.0 - y_norm)

    elif anim_name == "walk":
        # Smooth 8-frame walk cycle: alternating vertical leg lift + gentle horizontal swing (zero boot shear!)
        whole_bob_y = -abs(s1) * 3.0
        shadow_scale = 1.0 - 0.07 * abs(s1)
        side_sign = np.tanh(x_rel * 2.6)
        if is_side_profile:
            cx_body = bw * 0.5
            stride_open = 0.62 + 0.38 * abs(s1)
            leg_scale = 1.0 - (1.0 - stride_open) * w_leg
            src_x = cx_body + (xx - cx_body) / np.maximum(leg_scale, 0.45)
            src_y -= s1 * side_sign * 4.2 * w_leg
        else:
            src_y -= s1 * side_sign * 4.8 * w_leg
            src_x -= s1 * 1.8 * w_leg
        # Subtle upper torso & arm counter-sway
        src_x += s1 * 1.5 * w_upper * (y_norm * 0.8)

    elif anim_name == "run":
        # Smooth 8-frame energetic run cycle: forward lean + clean alternating leg lift (zero boot shear!)
        whole_bob_y = -abs(s1) * 4.8 - 1.0
        shadow_scale = 0.90 - 0.10 * abs(s1)
        side_sign = np.tanh(x_rel * 2.6)
        lean_amount = (dx if dx != 0 else 0.35) * 4.0 * (1.0 - y_norm)
        src_x -= lean_amount
        if is_side_profile:
            cx_body = bw * 0.5
            stride_open = 0.65 + 0.42 * abs(s1)
            leg_scale = 1.0 - (1.0 - stride_open) * w_leg
            src_x = cx_body + (xx - cx_body) / np.maximum(leg_scale, 0.45) - lean_amount
            src_y -= s1 * side_sign * 6.0 * w_leg
        else:
            src_y -= s1 * side_sign * 6.2 * w_leg
            src_x -= s1 * 2.5 * w_leg
        src_x += s1 * 2.2 * w_upper * y_norm

    elif anim_name in ("axe", "pickaxe"):
        # Smooth windup (frames 0..2) -> smooth strike (frames 3..5) -> smooth recovery (frames 6..7)
        swing_curve = -math.sin(phase)  # -1 at windup, +1 at strike
        whole_bob_y = swing_curve * 2.2
        lean = swing_curve * (dx if dx != 0 else 0.5) * 5.0 * w_upper
        src_x -= lean
        src_y -= swing_curve * 2.8 * w_upper

    elif anim_name == "water":
        tilt = math.sin(phase * 0.5)  # Smooth forward tilt and hold
        src_x -= tilt * (dx if dx != 0 else 0.5) * 3.2 * w_upper
        src_y -= tilt * 1.8 * w_upper

    elif anim_name == "interact":
        # Smooth cheerful wave / discovery gesture
        wave = math.sin(phase * 0.5)
        whole_bob_y = -wave * 4.5
        src_y += wave * 2.5 * w_upper * np.clip(x_rel, 0.0, 1.0)

    warped_arr = bilinear_warp_rgba(arr, src_x, src_y)
    warped_im = Image.fromarray(warped_arr, "RGBA")

    # Draw soft blurred ground shadow under feet (clean elliptical shadow only)
    shadow_im = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_im)
    srx = int(32 * shadow_scale)
    sry = int(14 * shadow_scale)
    s_draw.ellipse([96 - srx, 168 - sry, 96 + srx, 168 + sry], fill=(10, 14, 24, 105))
    shadow_im = shadow_im.filter(ImageFilter.GaussianBlur(radius=2.2))
    canvas.alpha_composite(shadow_im)

    paste_x = (CW - bw) // 2
    paste_y = int(round(172 - pad - ph + whole_bob_y))

    # Build tool layer if using a tool (character has NO gear otherwise!)
    tool_layer = None
    if anim_name in ("axe", "pickaxe", "water"):
        tool_layer = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
        td = ImageDraw.Draw(tool_layer)
        aim_x = dx if dx != 0 else 0.65
        aim_y = dy * 0.45 if dy != 0 else 0.25
        t_norm = frame_idx / float(total_frames - 1)  # 0.0 .. 1.0

        if anim_name in ("axe", "pickaxe"):
            base_ang = math.atan2(aim_y, aim_x)
            swing_offset = math.cos(t_norm * math.pi) * (-0.95)
            ang = base_ang + swing_offset
            hx = 96 + aim_x * 22
            hy = 92 + aim_y * 10
            tx = hx + math.cos(ang) * 40
            ty = hy + math.sin(ang) * 40
            td.line([(hx, hy), (tx, ty)], fill=(58, 36, 18, 245), width=8)
            td.line([(hx, hy), (tx, ty)], fill=(192, 134, 78, 255), width=4)
            perp_x, perp_y = -math.sin(ang), math.cos(ang)
            if anim_name == "axe":
                blade = [
                    (tx - math.cos(ang) * 6, ty - math.sin(ang) * 6),
                    (tx + math.cos(ang) * 10 + perp_x * 15, ty + math.sin(ang) * 10 + perp_y * 15),
                    (tx + math.cos(ang) * 14 + perp_x * 4, ty + math.sin(ang) * 14 + perp_y * 4),
                    (tx - math.cos(ang) * 4 - perp_x * 6, ty - math.sin(ang) * 4 - perp_y * 6),
                ]
                td.polygon(blade, fill=(220, 232, 245, 255), outline=(42, 50, 64, 240))
            else:
                td.line(
                    [(tx - perp_x * 16, ty - perp_y * 16), (tx + perp_x * 16, ty + perp_y * 16)],
                    fill=(220, 232, 245, 255),
                    width=6,
                )
            if frame_idx in (3, 4, 5):
                deg = math.degrees(base_ang)
                r_arc = 42
                td.arc(
                    [hx - r_arc, hy - r_arc, hx + r_arc, hy + r_arc],
                    start=deg - 35,
                    end=deg + 35,
                    fill=(230, 246, 255, 125),
                    width=4,
                )

        elif anim_name == "water":
            wx = int(96 + aim_x * 28)
            wy = int(100 + aim_y * 12)
            td.rounded_rectangle([wx - 13, wy - 9, wx + 13, wy + 11], radius=5, fill=(68, 138, 202, 255), outline=(28, 42, 62, 240), width=3)
            spout_x = int(wx + aim_x * 20)
            spout_y = int(wy + aim_y * 10)
            td.line([(wx, wy), (spout_x, spout_y)], fill=(190, 212, 232, 255), width=5)
            if 1 <= frame_idx <= 6:
                for di in range(4):
                    drop_t = ((frame_idx * 0.22 + di * 0.25) % 1.0)
                    drx = int(spout_x + aim_x * 16 * drop_t + (di - 1.5) * 5)
                    dry = int(spout_y + aim_y * 10 * drop_t + drop_t * drop_t * 24)
                    td.ellipse([drx - 4, dry - 4, drx + 4, dry + 5], fill=(140, 225, 255, int(230 * (1.0 - drop_t * 0.5))))

        tool_layer = tool_layer.filter(ImageFilter.GaussianBlur(radius=0.55))

    # When facing UP (away from camera), tool is held in front of chest (behind body from camera view)
    if tool_layer is not None and "up" in dir_name:
        canvas.alpha_composite(tool_layer)
    canvas.alpha_composite(warped_im, (paste_x, paste_y))
    if tool_layer is not None and "up" not in dir_name:
        canvas.alpha_composite(tool_layer)

    return canvas.resize((96, 96), Image.Resampling.LANCZOS)


def build_explorer_spritesheet() -> None:
    print("Building Smooth Equipment-Free Explorer Spritesheet (8 cols x 56 rows of 96x96)...")
    front_clean = remove_white_bg_smart(Image.open("assets/ai_raw/explorer_front.png"), min_hole_area=120, strip_floor_shadow=True)
    side_clean = remove_white_bg_smart(Image.open("assets/ai_raw/explorer_side.png"), min_hole_area=120, strip_floor_shadow=True)
    back_clean = remove_white_bg_smart(Image.open("assets/ai_raw/explorer_back.png"), min_hole_area=120, strip_floor_shadow=True)
    up_clean = remove_white_bg_smart(Image.open("assets/ai_raw/explorer_diag_up.png"), min_hole_area=120, strip_floor_shadow=True)

    p_front_right = normalize_explorer_pose(front_clean, target_h=156)
    p_front_left = p_front_right.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    p_side_right = normalize_explorer_pose(side_clean, target_h=156)
    p_side_left = p_side_right.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    p_back_right = normalize_explorer_pose(back_clean, target_h=156)
    p_back_left = p_back_right.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    p_up = normalize_explorer_pose(up_clean, target_h=156)

    dir_poses = {
        "down":       p_front_right,
        "down_right": p_front_right,
        "right":      p_side_right,
        "up_right":   p_back_right,
        "up":         p_up,
        "up_left":    p_back_left,
        "left":       p_side_left,
        "down_left":  p_front_left,
    }

    cols = 8
    rows = len(ANIMATIONS) * len(DIRECTIONS)  # 56 rows
    frame_size = 96
    sheet = Image.new("RGBA", (cols * frame_size, rows * frame_size), (0, 0, 0, 0))
    showcase = Image.new("RGBA", (len(DIRECTIONS) * frame_size, len(ANIMATIONS) * frame_size), (24, 30, 42, 255))
    sc_draw = ImageDraw.Draw(showcase)

    row_idx = 0
    for a_idx, (anim_name, frame_count) in enumerate(ANIMATIONS):
        sample_f = 4 if anim_name in ("axe", "pickaxe", "water") else (2 if anim_name != "idle" else 0)
        for d_idx, dir_name in enumerate(DIRECTIONS):
            pose_2x = dir_poses[dir_name]
            for col_idx in range(cols):
                frame_im = render_smooth_explorer_frame(pose_2x, dir_name, anim_name, col_idx, frame_count)
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
    hero_icon = render_smooth_explorer_frame(p_front_right, "down_right", "idle", 0, 8)
    icon.alpha_composite(hero_icon, (16, 16))
    icon.save("icon.png")
    print(f"Saved smooth Explorer spritesheet ({sheet.size[0]}x{sheet.size[1]})")


# =============================================================================
# 3. SUPERSAMPLED SMOOTH ISOMETRIC TILESET (Zero harsh pixel noise!)
# =============================================================================
def build_smooth_isometric_tileset() -> None:
    print("Building Supersampled Smooth Isometric Tileset (1024x200)...")
    TILE_W = 64
    TILE_H = 32
    SKIRT_H = 8
    CELL_H = TILE_H + SKIRT_H  # 40
    COLS, ROWS = 16, 5

    # Render each tile at 2x supersampling (128x80) with smooth organic gradients, then LANCZOS to 64x40
    SS = 2
    SW, SH, S_TILE_H, S_SKIRT = TILE_W * SS, CELL_H * SS, TILE_H * SS, SKIRT_H * SS
    hw = SW / 2.0
    hh = S_TILE_H / 2.0

    yy, xx = np.meshgrid(np.arange(SH, dtype=np.float32), np.arange(SW, dtype=np.float32), indexing="ij")
    dx = np.abs(xx + 0.5 - hw) / hw
    dy = np.abs(yy + 0.5 - hh) / hh
    dist_diamond = dx + dy

    # Smooth anti-aliased diamond alpha mask
    diamond_alpha = np.clip((1.02 - dist_diamond) * 32.0, 0.0, 1.0)
    diamond_alpha[yy >= S_TILE_H] = 0.0

    bot_y_at_x = hh + (1.0 - dx) * hh
    in_skirt = (yy >= bot_y_at_x - 1.0) & (yy < bot_y_at_x + S_SKIRT) & (dx <= 1.0)
    left_skirt = in_skirt & (xx < hw)
    right_skirt = in_skirt & (xx >= hw)

    rng = random.Random(20261002)

    def make_smooth_iso_tile(
        base_rgb: tuple,
        accent_rgb: tuple,
        left_skirt_rgb: tuple,
        right_skirt_rgb: tuple,
        seed_offset: int,
        detail_fn=None,
    ) -> Image.Image:
        # Smooth low-frequency organic wave texture (no harsh per-pixel noise!)
        phase1 = (seed_offset * 1.7) % 6.28
        phase2 = (seed_offset * 2.9) % 6.28
        wave = (
            np.sin(xx * 0.09 + yy * 0.14 + phase1) * 0.5
            + np.cos(xx * 0.07 - yy * 0.16 + phase2) * 0.5
        )  # -1..+1
        blend = np.clip((wave + 1.0) * 0.5, 0.0, 1.0)
        # Soft directional sunlight from NW
        sun = ((hw - xx) * 0.10 + (hh - yy) * 0.22)

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
        return im.resize((TILE_W, CELL_H), Image.Resampling.LANCZOS)

    atlas = Image.new("RGBA", (COLS * TILE_W, ROWS * CELL_H), (0, 0, 0, 0))

    # ROW 0: Smooth Water Tiles (Deep Lake, Shallow Turquoise, Flowing River, Lilypads)
    for i in range(4):
        def deep_ripples(d: ImageDraw.ImageDraw, idx: int):
            for wy in (20, 32, 44):
                wx = 42 + ((idx * 11 + wy) % 34)
                d.arc([wx, wy - 4, wx + 22, wy + 6], start=200, end=340, fill=(108, 176, 238, 165), width=2)
        t = make_smooth_iso_tile((28, 78, 146), (38, 98, 172), (20, 56, 112), (16, 46, 96), i, deep_ripples)
        atlas.alpha_composite(t, (i * TILE_W, 0))

    for i in range(4):
        def shallow_ripples(d: ImageDraw.ImageDraw, idx: int):
            for wy in (18, 30, 42):
                wx = 38 + ((idx * 13 + wy) % 38)
                d.arc([wx, wy - 4, wx + 24, wy + 6], start=200, end=340, fill=(170, 232, 255, 185), width=2)
        t = make_smooth_iso_tile((52, 134, 198), (72, 158, 218), (36, 96, 152), (28, 82, 134), 10 + i, shallow_ripples)
        atlas.alpha_composite(t, ((4 + i) * TILE_W, 0))

    for i in range(4):
        def river_ripples(d: ImageDraw.ImageDraw, idx: int):
            for rx, ry in [(44, 22), (64, 32), (52, 42), (76, 28)]:
                ox = ((idx * 7) % 16) - 8
                d.line([(rx + ox, ry), (rx + ox + 16, ry + 7)], fill=(195, 240, 255, 190), width=2)
        t = make_smooth_iso_tile((46, 122, 188), (66, 148, 212), (32, 88, 144), (26, 74, 126), 20 + i, river_ripples)
        atlas.alpha_composite(t, ((8 + i) * TILE_W, 0))

    for i in range(4):
        def lilypad_detail(d: ImageDraw.ImageDraw, idx: int):
            for lx, ly in [(50, 28), (78, 36)]:
                d.ellipse([lx - 12, ly - 6, lx + 12, ly + 6], fill=(58, 148, 68, 255), outline=(32, 86, 40, 220), width=2)
                if idx % 2 == 0 and lx == 50:
                    d.ellipse([lx - 5, ly - 6, lx + 5, ly + 2], fill=(248, 156, 188, 255))
                    d.ellipse([lx - 2, ly - 3, lx + 2, ly], fill=(255, 232, 102, 255))
        t = make_smooth_iso_tile((52, 134, 198), (72, 158, 218), (36, 96, 152), (28, 82, 134), 30 + i, lilypad_detail)
        atlas.alpha_composite(t, ((12 + i) * TILE_W, 0))

    # ROW 1: Sand Shore (0..3), Sunlit Meadow Grass (4..7), Emerald Forest Grass (8..11), Cobblestone Road (12..15)
    for i in range(4):
        t = make_smooth_iso_tile((222, 194, 136), (236, 210, 154), (172, 142, 92), (148, 118, 74), 40 + i)
        atlas.alpha_composite(t, (i * TILE_W, CELL_H))

    for i in range(4):
        def meadow_blades(d: ImageDraw.ImageDraw, idx: int):
            for gx, gy in [(44 + idx * 4, 28), (72, 24 + idx * 2), (58, 40), (82 - idx * 3, 34)]:
                d.line([(gx, gy), (gx - 3, gy - 6)], fill=(112, 192, 84, 210), width=2)
                d.line([(gx + 2, gy), (gx + 4, gy - 7)], fill=(128, 206, 96, 210), width=2)
        t = make_smooth_iso_tile((78, 154, 62), (96, 174, 74), (98, 74, 48), (78, 56, 36), 50 + i, meadow_blades)
        atlas.alpha_composite(t, ((4 + i) * TILE_W, CELL_H))

    for i in range(4):
        def forest_clover(d: ImageDraw.ImageDraw, idx: int):
            for mx, my in [(48, 26 + idx * 2), (76, 34), (60 + idx * 2, 42)]:
                d.ellipse([mx - 6, my - 3, mx + 6, my + 3], fill=(68, 148, 74, 190))
        t = make_smooth_iso_tile((46, 112, 56), (62, 134, 68), (78, 58, 38), (58, 42, 28), 60 + i, forest_clover)
        atlas.alpha_composite(t, ((8 + i) * TILE_W, CELL_H))

    for i in range(4):
        def road_cobble(d: ImageDraw.ImageDraw, idx: int):
            stones = [(48, 26, 10, 5), (70, 22, 11, 5), (58, 36, 12, 6), (82, 34, 9, 5), (44, 38, 8, 4)]
            for sx, sy, srw, srh in stones:
                ox = (idx % 2) * 4 - 2
                d.ellipse([sx + ox - srw, sy - srh, sx + ox + srw, sy + srh], fill=(138, 134, 128, 235), outline=(78, 70, 64, 210), width=2)
        t = make_smooth_iso_tile((156, 120, 84), (172, 136, 96), (112, 82, 54), (88, 62, 40), 70 + i, road_cobble)
        atlas.alpha_composite(t, ((12 + i) * TILE_W, CELL_H))

    # ROW 2: Wooden Bridge (0..3), Watered Soil (4..7), Highland Slate/Sandstone (8..11), Autumn Maple/Birch Grass (12..15)
    for i in range(4):
        def bridge_deck(d: ImageDraw.ImageDraw, idx: int):
            for step in range(-36, 44, 12):
                d.line([(64 + step - 24, 32 + step // 2 - 12), (64 + step + 24, 32 + step // 2 + 12)], fill=(82, 52, 28, 210), width=2)
            d.line([(8, 30), (64, 4)], fill=(216, 168, 110, 255), width=4)
            d.line([(64, 58), (120, 30)], fill=(128, 84, 46, 255), width=4)
        t = make_smooth_iso_tile((168, 118, 72), (186, 134, 84), (112, 72, 38), (88, 54, 28), 80 + i, bridge_deck)
        atlas.alpha_composite(t, (i * TILE_W, CELL_H * 2))

    for i in range(4):
        t = make_smooth_iso_tile((44, 108, 72), (56, 126, 84), (58, 44, 32), (44, 32, 22), 90 + i)
        atlas.alpha_composite(t, ((4 + i) * TILE_W, CELL_H * 2))

    for i in range(4):
        t = make_smooth_iso_tile((92, 102, 116), (110, 122, 136), (58, 66, 76), (44, 50, 60), 100 + i)
        atlas.alpha_composite(t, ((8 + i) * TILE_W, CELL_H * 2))

    for i in range(4):
        def autumn_leaves(d: ImageDraw.ImageDraw, idx: int):
            for lx, ly in [(46 + idx * 4, 30), (72, 26 + idx * 2), (60, 40), (84 - idx * 4, 32)]:
                col = (238, 142, 52, 230) if (lx + idx) % 2 == 0 else (244, 196, 64, 230)
                d.ellipse([lx - 4, ly - 2, lx + 4, ly + 2], fill=col)
        t = make_smooth_iso_tile((104, 148, 56), (126, 168, 64), (88, 66, 42), (68, 50, 30), 110 + i, autumn_leaves)
        atlas.alpha_composite(t, ((12 + i) * TILE_W, CELL_H * 2))

    # ROW 3: Smooth Ground Decor Overlays (Flowers, Soft Grass Tufts, Forest Mushrooms, River Pebbles)
    flower_sets = [
        ((238, 68, 74, 255), (255, 224, 82, 255)),
        ((252, 212, 62, 255), (232, 142, 34, 255)),
        ((248, 164, 196, 255), (255, 242, 190, 255)),  # Soft cherry blossom petals / pink flowers
        ((248, 248, 252, 255), (250, 206, 68, 255)),
    ]
    for i, (petal_c, center_c) in enumerate(flower_sets):
        t = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
        d = ImageDraw.Draw(t)
        for fx, fy in [(44, 28), (68, 22), (56, 38), (84, 32), (66, 44)]:
            d.line([(fx, fy + 2), (fx, fy + 9)], fill=(54, 132, 54, 230), width=2)
            d.ellipse([fx - 5, fy - 4, fx + 5, fy + 4], fill=petal_c)
            d.ellipse([fx - 2, fy - 2, fx + 2, fy + 2], fill=center_c)
        atlas.alpha_composite(t.resize((TILE_W, CELL_H), Image.Resampling.LANCZOS), (i * TILE_W, CELL_H * 3))

    for i in range(4):
        t = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
        d = ImageDraw.Draw(t)
        for gx, gy in [(44, 34), (64, 28), (80, 38), (56, 44)]:
            d.line([(gx, gy), (gx - 6, gy - 12)], fill=(58, 138, 58, 230), width=2)
            d.line([(gx + 2, gy), (gx + 2, gy - 14)], fill=(86, 172, 74, 230), width=2)
            d.line([(gx + 4, gy), (gx + 10, gy - 11)], fill=(116, 198, 92, 230), width=2)
        atlas.alpha_composite(t.resize((TILE_W, CELL_H), Image.Resampling.LANCZOS), ((4 + i) * TILE_W, CELL_H * 3))

    for i in range(4):
        t = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
        d = ImageDraw.Draw(t)
        for mx, my in [(48, 30), (74, 36), (62, 24)]:
            d.rectangle([mx - 2, my, mx + 2, my + 8], fill=(242, 230, 208, 255))
            d.ellipse([mx - 7, my - 5, mx + 7, my + 2], fill=(222, 56, 52, 255))
            d.ellipse([mx - 3, my - 3, mx - 1, my - 1], fill=(255, 248, 235, 255))
            d.ellipse([mx + 2, my - 2, mx + 4, my], fill=(255, 248, 235, 255))
        atlas.alpha_composite(t.resize((TILE_W, CELL_H), Image.Resampling.LANCZOS), ((8 + i) * TILE_W, CELL_H * 3))

    for i in range(4):
        t = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
        d = ImageDraw.Draw(t)
        for px, py in [(46, 30), (72, 26), (62, 40), (84, 34)]:
            d.ellipse([px - 7, py - 4, px + 7, py + 4], fill=(138, 148, 160, 240))
            d.ellipse([px - 4, py - 3, px + 2, py + 1], fill=(185, 196, 208, 240))
        atlas.alpha_composite(t.resize((TILE_W, CELL_H), Image.Resampling.LANCZOS), ((12 + i) * TILE_W, CELL_H * 3))

    # ROW 4: Additional Biome Varieties (Cherry Blossom Lawn 0..3, Warm Sandstone Ground 4..7, Lush Clover 8..15)
    for i in range(4):
        def blossom_petals(d: ImageDraw.ImageDraw, idx: int):
            for px, py in [(44 + idx * 4, 28), (74, 24 + idx * 2), (58, 38), (82 - idx * 3, 34)]:
                d.ellipse([px - 3, py - 2, px + 3, py + 2], fill=(250, 176, 204, 225))
        t = make_smooth_iso_tile((82, 160, 72), (102, 178, 86), (92, 68, 44), (72, 52, 32), 120 + i, blossom_petals)
        atlas.alpha_composite(t, (i * TILE_W, CELL_H * 4))

    for i in range(4):
        t = make_smooth_iso_tile((196, 146, 98), (214, 164, 112), (146, 104, 68), (122, 84, 52), 130 + i)
        atlas.alpha_composite(t, ((4 + i) * TILE_W, CELL_H * 4))

    for i in range(8):
        t = make_smooth_iso_tile((72, 148, 64), (90, 168, 76), (88, 64, 42), (68, 48, 30), 140 + i)
        atlas.alpha_composite(t, ((8 + i) * TILE_W, CELL_H * 4))

    atlas.save("assets/tilesets/world_tileset.png")
    print("Saved smooth supersampled assets/tilesets/world_tileset.png")


if __name__ == "__main__":
    build_world_objects()
    build_explorer_spritesheet()
    build_smooth_isometric_tileset()
    print("All smooth high-res assets built successfully!")
