#!/usr/bin/env python3
"""
Builds Stardew Valley style 2D Isometric assets for Godot 4.7:
  1. Stardew Valley Isometric Traveler-Explorer (assets/sprites/player_spritesheet.png, 768x5376, 8 cols x 56 rows)
     from assets/ai_raw/sdv_explorer_*.png (cute 3-heads-tall ConcernedApe style villager/explorer with NO backpack,
     NO staff, and NO equipment, across all 8 true isometric directions and 7 smooth 8-frame animations).
  2. 19 Stardew Valley Isometric World Objects (8 Trees + 8 Pure Natural Rocks with NO ore + 3 Forest Props)
     in warm, vibrant ConcernedApe palette with soft colored outlines and smooth anti-aliased resampling.
  3. Seamless Stardew Valley Isometric Tileset (assets/tilesets/world_tileset.png, 1024x200, 64x40 cells)
     with zero diamond grid seams and cozy Pelican Town / Cindersap Forest colors.
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


# =============================================================================
# 0. CLEAN BACKGROUND REMOVAL & SMOOTH PRE-FILTERED RESIZING
# =============================================================================
def remove_white_bg_sdv(
    im: Image.Image,
    white_thresh: int = 232,
    chroma_thresh: int = 28,
    min_hole_area: int = 90,
    strip_floor_shadow: bool = False,
    strip_ground_patch: bool = False,
) -> Image.Image:
    """
    Removes white background from Stardew-style AI sprites using exterior BFS flood-fill
    plus optional removal of baked-in floor shadow under character boots.
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
        # Strip gray/taupe oval floor shadow around boots while stopping at dark brown boot outlines (min_c < 45)
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

    # Smooth anti-aliased alpha edge
    alpha_f = (~bg_mask).astype(np.float32) * 255.0
    alpha_img = Image.fromarray(alpha_f.astype(np.uint8), "L")
    alpha_smooth = alpha_img.filter(ImageFilter.GaussianBlur(radius=0.95))
    alpha_arr = np.array(alpha_smooth, dtype=np.float32)
    alpha_arr = np.clip((alpha_arr - 38.0) * (255.0 / 217.0), 0.0, 255.0).astype(np.uint8)
    rgba[:, :, 3] = alpha_arr

    # Decontaminate any bright white fringe on semi-transparent outline pixels
    edge_zone = (alpha_arr > 0) & (alpha_arr < 225) & (min_c > 195)
    rgba[edge_zone, 0] = (rgba[edge_zone, 0].astype(np.int16) * 6 // 10).astype(np.uint8)
    rgba[edge_zone, 1] = (rgba[edge_zone, 1].astype(np.int16) * 6 // 10).astype(np.uint8)
    rgba[edge_zone, 2] = (rgba[edge_zone, 2].astype(np.int16) * 6 // 10).astype(np.uint8)

    return Image.fromarray(rgba, "RGBA")


def crop_to_alpha(im: Image.Image) -> Image.Image:
    bbox = im.getbbox()
    if not bbox:
        return im
    return im.crop(bbox)


def smooth_prefiltered_resize(im: Image.Image, new_w: int, new_h: int, post_blur: float = 0.25) -> Image.Image:
    """
    Downscales a high-res RGBA sprite using premultiplied alpha + Gaussian anti-aliasing pre-filter
    + LANCZOS so Stardew pixel clusters look warm, cohesive, and soft on the eyes (never jagged).
    """
    cw, ch = im.size
    ratio = max(cw / float(max(1, new_w)), ch / float(max(1, new_h)))
    pre_sigma = max(0.35, min(1.2, ratio * 0.15))

    arr = np.array(im.convert("RGBA"), dtype=np.float32)
    alpha = arr[:, :, 3:4] / 255.0
    pre = arr.copy()
    pre[:, :, :3] *= alpha

    pre_im = Image.fromarray(np.clip(pre, 0, 255).astype(np.uint8), "RGBA")
    pre_im = pre_im.filter(ImageFilter.GaussianBlur(radius=pre_sigma))
    resized_pre = pre_im.resize((new_w, new_h), Image.Resampling.LANCZOS)
    if post_blur > 0.0:
        resized_pre = resized_pre.filter(ImageFilter.GaussianBlur(radius=post_blur))

    r_arr = np.array(resized_pre, dtype=np.float32)
    r_alpha = r_arr[:, :, 3:4] / 255.0
    rgb_out = np.where(r_alpha > 1e-3, r_arr[:, :, :3] / np.maximum(r_alpha, 1e-3), 0.0)
    out = np.zeros_like(r_arr, dtype=np.uint8)
    out[:, :, :3] = np.clip(rgb_out, 0, 255).astype(np.uint8)
    out[:, :, 3] = np.clip(r_arr[:, :, 3], 0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def stylize_to_stardew_palette(im: Image.Image, warmth: float = 1.08, sat: float = 1.22, contrast: float = 1.08, add_warm_outline: bool = True) -> Image.Image:
    """
    Harmonizes any sprite to ConcernedApe's warm, vibrant Stardew Valley color palette
    and adds a warm dark-umbrian colored outline (#3b2114) around the silhouette.
    """
    rgba = im.convert("RGBA")
    r, g, b, a = rgba.split()
    rgb = Image.merge("RGB", (r, g, b))
    rgb = ImageEnhance.Color(rgb).enhance(sat)
    rgb = ImageEnhance.Contrast(rgb).enhance(contrast)

    arr = np.array(rgb, dtype=np.float32)
    # Warm golden sunlight shift on highlights, cozy slate-violet shift in deep shadows
    lum = (arr[:, :, 0] * 0.299 + arr[:, :, 1] * 0.587 + arr[:, :, 2] * 0.114) / 255.0
    arr[:, :, 0] = np.clip(arr[:, :, 0] * warmth + lum * 6.0, 0, 255)
    arr[:, :, 1] = np.clip(arr[:, :, 1] * (1.0 + (warmth - 1.0) * 0.6) + lum * 3.0, 0, 255)
    arr[:, :, 2] = np.clip(arr[:, :, 2] * (2.0 - warmth) + (1.0 - lum) * 8.0, 0, 255)

    # Gentle posterization (24 levels per channel) for authentic 16-bit SNES / Stardew Valley shading
    arr = np.round(arr / 10.0) * 10.0
    out_rgba = np.zeros((arr.shape[0], arr.shape[1], 4), dtype=np.uint8)
    out_rgba[:, :, :3] = np.clip(arr, 0, 255).astype(np.uint8)
    a_arr = np.array(a, dtype=np.uint8)
    out_rgba[:, :, 3] = a_arr

    if add_warm_outline:
        # Detect 1px silhouette perimeter and tint with Stardew Valley's warm dark brown-umber outline
        a_max = np.array(a.filter(ImageFilter.MaxFilter(3)), dtype=np.int16)
        a_min = np.array(a.filter(ImageFilter.MinFilter(3)), dtype=np.int16)
        border = (a_arr > 45) & (a_min < 30) & (a_max > 120)
        out_rgba[border, 0] = (out_rgba[border, 0].astype(np.int16) * 4 // 10 + 34).astype(np.uint8)
        out_rgba[border, 1] = (out_rgba[border, 1].astype(np.int16) * 4 // 10 + 20).astype(np.uint8)
        out_rgba[border, 2] = (out_rgba[border, 2].astype(np.int16) * 4 // 10 + 16).astype(np.uint8)

    return Image.fromarray(out_rgba, "RGBA")


def recolor_oak_to_stardew_sakura(oak_im: Image.Image) -> Image.Image:
    """Transforms the Stardew Valley Oak/Maple canopy into a lush Stardew Valley Cherry Blossom Sakura tree."""
    arr = np.array(oak_im.convert("RGBA"), dtype=np.float32)
    r, g, b, a = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]
    # Foliage pixels in sdv_tree_oak have green > red + 12
    is_foliage = (a > 20) & (g > r + 10)
    lum = (r * 0.25 + g * 0.65 + b * 0.10) / 255.0

    # Map foliage luminance to Stardew Valley sakura blossom pinks (#8c2d52 -> #d95b82 -> #ff9ebb -> #ffdbe8)
    new_r = np.clip(145.0 + lum * 135.0, 0, 255)
    new_g = np.clip(48.0 + (lum ** 1.25) * 195.0, 0, 255)
    new_b = np.clip(88.0 + (lum ** 1.15) * 165.0, 0, 255)

    arr[:, :, 0] = np.where(is_foliage, new_r, r)
    arr[:, :, 1] = np.where(is_foliage, new_g, g)
    arr[:, :, 2] = np.where(is_foliage, new_b, b)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


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

    resized = smooth_prefiltered_resize(cropped, new_w, new_h, post_blur=0.22)

    shadow_layer = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_layer)
    scx = target_w // 2
    scy = target_h - bottom_pad + shadow_y_off
    s_draw.ellipse(
        [scx - shadow_rx, scy - shadow_ry, scx + shadow_rx, scy + shadow_ry],
        fill=(16, 22, 32, 88),
    )
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=2.6))

    paste_x = (target_w - new_w) // 2
    paste_y = target_h - bottom_pad - new_h
    shadow_layer.alpha_composite(resized, (paste_x, paste_y))
    return shadow_layer


# =============================================================================
# 1. BUILD 19 STARDEW VALLEY ISOMETRIC WORLD OBJECTS (8 Trees, 8 Rocks, 3 Props)
# =============================================================================
def build_world_objects() -> None:
    print("Building 19 Stardew Valley style isometric world objects (8 trees, 8 ore-free rocks, 3 props)...")

    # Direct Stardew Valley AI trees
    sdv_oak = remove_white_bg_sdv(Image.open("assets/ai_raw/sdv_tree_oak.png"), min_hole_area=90)
    sdv_willow = remove_white_bg_sdv(Image.open("assets/ai_raw/sdv_tree_willow.png"), min_hole_area=90)
    sdv_pine = remove_white_bg_sdv(Image.open("assets/ai_raw/sdv_tree_pine.png"), min_hole_area=90)
    sdv_birch = remove_white_bg_sdv(Image.open("assets/ai_raw/sdv_tree_birch.png"), min_hole_area=280)
    sdv_maple = remove_white_bg_sdv(Image.open("assets/ai_raw/sdv_tree_maple.png"), min_hole_area=90)
    sdv_cherry = recolor_oak_to_stardew_sakura(sdv_oak)
    sdv_cedar = stylize_to_stardew_palette(
        remove_white_bg_sdv(Image.open("assets/ai_raw/iso_tree_ancient_fir.png"), min_hole_area=90),
        warmth=1.08, sat=1.30, contrast=1.12, add_warm_outline=True
    )
    sdv_poplar = stylize_to_stardew_palette(
        remove_white_bg_sdv(Image.open("assets/ai_raw/iso_tree_poplar.png"), min_hole_area=90),
        warmth=1.10, sat=1.32, contrast=1.12, add_warm_outline=True
    )

    tree_outputs = [
        (sdv_oak,    "assets/objects/tree_oak.png",    160, 176, 8, 42, 18, -12),
        (sdv_willow, "assets/objects/tree_willow.png", 168, 176, 8, 46, 19, -12),
        (sdv_pine,   "assets/objects/tree_pine.png",   144, 192, 8, 34, 15, -10),
        (sdv_birch,  "assets/objects/tree_birch.png",  144, 176, 8, 34, 15, -10),
        (sdv_maple,  "assets/objects/tree_maple.png",  160, 176, 8, 42, 18, -12),
        (sdv_cherry, "assets/objects/tree_cherry.png", 168, 176, 8, 44, 18, -12),
        (sdv_cedar,  "assets/objects/tree_cedar.png",  152, 192, 8, 38, 16, -10),
        (sdv_poplar, "assets/objects/tree_poplar.png", 128, 196, 8, 30, 14, -10),
    ]
    for clean_im, dst_path, tw, th, bpad, srx, sry, syoff in tree_outputs:
        out = fit_smooth_with_iso_shadow(clean_im, tw, th, bpad, srx, sry, syoff)
        out.save(dst_path)

    # 8 Pure Natural Rocks stylized to Stardew Valley warm pixel palette (NO ore, NO crystals!)
    rock_specs = [
        ("assets/ai_raw/iso_rock_boulder.png",       "assets/objects/rock_large.png",     112, 96, 6, 42, 18, -12, 90,  1.06, 1.25),
        ("assets/ai_raw/iso_rock_slate.png",         "assets/objects/rock_slate.png",     112, 96, 6, 42, 18, -12, 90,  1.02, 1.25),
        ("assets/ai_raw/iso_rock_sandstone.png",     "assets/objects/rock_sandstone.png", 116, 96, 6, 44, 19, -12, 80,  1.12, 1.28),
        ("assets/ai_raw/iso_rock_mossy_cluster.png", "assets/objects/rock_river.png",     108, 88, 6, 42, 18, -11, 250, 1.06, 1.30),
        ("assets/ai_raw/iso_rock_limestone.png",     "assets/objects/rock_limestone.png", 112, 92, 6, 42, 18, -11, 200, 1.08, 1.22),
        ("assets/ai_raw/iso_rock_basalt.png",        "assets/objects/rock_basalt.png",    116, 96, 6, 44, 19, -12, 120, 1.04, 1.25),
        ("assets/ai_raw/iso_rock_flat_stepping.png", "assets/objects/rock_flat.png",      116, 88, 6, 44, 18, -11, 150, 1.10, 1.26),
        ("assets/ai_raw/iso_rock_limestone.png",     "assets/objects/rock_small.png",      72, 60, 5, 26, 11, -7,  200, 1.08, 1.22),
    ]
    for src_path, dst_path, tw, th, bpad, srx, sry, syoff, min_hole, warmth, sat in rock_specs:
        clean = remove_white_bg_sdv(Image.open(src_path), min_hole_area=min_hole)
        sdv_rock = stylize_to_stardew_palette(clean, warmth=warmth, sat=sat, contrast=1.10, add_warm_outline=True)
        out = fit_smooth_with_iso_shadow(sdv_rock, tw, th, bpad, srx, sry, syoff)
        out.save(dst_path)

    # 3 Stardew Valley Forest Props (Stump, Berry Bush, Fallen Log) from sdv_oak
    oak_crop = crop_to_alpha(sdv_oak)
    ow, oh = oak_crop.size
    trunk_slice = oak_crop.crop((int(ow * 0.22), int(oh * 0.58), int(ow * 0.78), oh))
    stump_hi = fit_smooth_with_iso_shadow(trunk_slice, 128, 112, bottom_pad=10, shadow_rx=46, shadow_ry=20, shadow_y_off=-12)
    s_draw = ImageDraw.Draw(stump_hi)
    s_draw.ellipse([36, 26, 92, 54], fill=(74, 38, 20, 255))
    s_draw.ellipse([40, 28, 88, 51], fill=(232, 178, 112, 255))
    s_draw.ellipse([47, 32, 81, 47], fill=(196, 138, 78, 255))
    s_draw.ellipse([53, 35, 75, 44], fill=(242, 194, 128, 255))
    smooth_prefiltered_resize(stump_hi, 64, 56).save("assets/objects/tree_stump.png")

    canopy_cluster = oak_crop.crop((int(ow * 0.14), int(oh * 0.04), int(ow * 0.86), int(oh * 0.56)))
    bush_hi = fit_smooth_with_iso_shadow(canopy_cluster, 136, 120, bottom_pad=10, shadow_rx=50, shadow_ry=22, shadow_y_off=-14)
    b_draw = ImageDraw.Draw(bush_hi)
    for bx, by in [(44, 48), (60, 36), (80, 40), (92, 56), (52, 68), (70, 60), (86, 72), (36, 64), (66, 46)]:
        b_draw.ellipse([bx - 6, by - 6, bx + 6, by + 6], fill=(122, 20, 34, 255))
        b_draw.ellipse([bx - 4, by - 4, bx + 5, by + 5], fill=(238, 54, 72, 255))
        b_draw.ellipse([bx - 2, by - 3, bx + 1, by], fill=(255, 190, 200, 255))
    smooth_prefiltered_resize(bush_hi, 68, 60).save("assets/objects/bush_berry.png")

    bark_rot = trunk_slice.rotate(72, expand=True, resample=Image.Resampling.BICUBIC)
    log_hi = fit_smooth_with_iso_shadow(bark_rot, 192, 112, bottom_pad=12, shadow_rx=74, shadow_ry=24, shadow_y_off=-12)
    l_draw = ImageDraw.Draw(log_hi)
    for mx, my in [(72, 44), (108, 50), (88, 38)]:
        l_draw.rectangle([mx - 3, my, mx + 3, my + 10], fill=(245, 232, 208, 255))
        l_draw.ellipse([mx - 9, my - 7, mx + 9, my + 3], fill=(228, 56, 48, 255))
        l_draw.ellipse([mx - 4, my - 5, mx - 1, my - 2], fill=(255, 248, 232, 255))
        l_draw.ellipse([mx + 2, my - 4, mx + 5, my - 1], fill=(255, 248, 232, 255))
    smooth_prefiltered_resize(log_hi, 96, 56).save("assets/objects/log_fallen.png")


# =============================================================================
# 2. STARDEW VALLEY ISOMETRIC TRAVELER-EXPLORER (NO EQUIPMENT, 8 ANGLES, 8 FRAMES)
# =============================================================================
DIRECTIONS = [
    "down",        # 0: S  (sdv_explorer_south.png)
    "down_right",  # 1: SE (sdv_explorer_front.png mirrored -> faces bottom-right)
    "right",       # 2: E  (sdv_explorer_side.png)
    "up_right",    # 3: NE (sdv_explorer_back.png mirrored -> faces top-right)
    "up",          # 4: N  (sdv_explorer_up.png)
    "up_left",     # 5: NW (sdv_explorer_back.png -> faces top-left)
    "left",        # 6: W  (sdv_explorer_side.png mirrored -> faces left)
    "down_left",   # 7: SW (sdv_explorer_front.png -> faces bottom-left)
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


def normalize_explorer_pose(im: Image.Image, target_h: int = 148) -> Image.Image:
    cropped = crop_to_alpha(im)
    cw, ch = cropped.size
    scale = target_h / float(ch)
    nw = max(1, int(round(cw * scale)))
    return smooth_prefiltered_resize(cropped, nw, target_h, post_blur=0.20)


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
    dir_name: str,
    anim_name: str,
    frame_idx: int,
    total_frames: int,
) -> Image.Image:
    SS = 2
    CW, CH = 96 * SS, 96 * SS
    canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))

    phase = (frame_idx / float(total_frames)) * 2.0 * math.pi
    s1 = math.sin(phase)
    c1 = math.cos(phase)
    # C-infinity smooth harmonic wave (no sharp |sin| corners)
    smooth_bob = 0.5 * (1.0 - math.cos(2.0 * phase))
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
    # In Stardew chibi proportions, legs are y_norm > 0.62
    y_norm = np.clip((yy - pad) / float(max(1, ph)), 0.0, 1.0)
    x_rel = (xx - (bw * 0.5)) / float(max(1, pw * 0.5))

    leg_t = np.clip((y_norm - 0.60) / 0.40, 0.0, 1.0)
    w_leg = 0.5 * (1.0 - np.cos(math.pi * leg_t))
    w_upper = 1.0 - w_leg

    src_x = xx.copy()
    src_y = yy.copy()
    whole_bob_y = 0.0
    shadow_scale = 1.0

    if anim_name == "idle":
        breath = s1 * 1.5
        sway = c1 * 0.5
        src_y -= breath * w_upper
        src_x -= sway * w_upper * (1.0 - y_norm)

    elif anim_name == "walk":
        whole_bob_y = -smooth_bob * 2.4
        shadow_scale = 1.0 - 0.05 * smooth_bob
        side_sign = np.tanh(x_rel * 2.5)
        src_y -= s1 * side_sign * 4.0 * w_leg
        src_x -= s1 * 1.8 * w_leg
        src_x += s1 * 1.4 * w_upper * (y_norm * 0.8)

    elif anim_name == "run":
        whole_bob_y = -smooth_bob * 3.8 - 0.8
        shadow_scale = 0.92 - 0.07 * smooth_bob
        side_sign = np.tanh(x_rel * 2.5)
        lean_amount = (dx if dx != 0 else 0.3) * 3.0 * (1.0 - y_norm)
        src_x -= lean_amount
        src_y -= s1 * side_sign * 5.2 * w_leg
        src_x -= s1 * 2.4 * w_leg
        src_x += s1 * 2.0 * w_upper * y_norm

    elif anim_name in ("axe", "pickaxe"):
        swing_wave = math.sin(phase) * bell
        whole_bob_y = -swing_wave * 2.0
        lean = swing_wave * (dx if dx != 0 else 0.4) * 3.6 * w_upper
        src_x -= lean
        src_y -= swing_wave * 2.2 * w_upper

    elif anim_name == "water":
        whole_bob_y = bell * 1.6
        src_x -= bell * (dx if dx != 0 else 0.4) * 3.0 * w_upper
        src_y -= bell * 2.0 * w_upper

    elif anim_name == "interact":
        whole_bob_y = -bell * 3.0
        src_y += bell * 2.0 * w_upper * np.clip(x_rel, 0.0, 1.0)

    warped_arr = bilinear_warp_rgba(arr, src_x, src_y)
    warped_im = Image.fromarray(warped_arr, "RGBA")

    shadow_im = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_im)
    srx = int(32 * shadow_scale)
    sry = int(14 * shadow_scale)
    s_draw.ellipse([96 - srx, 168 - sry, 96 + srx, 168 + sry], fill=(16, 22, 32, 92))
    shadow_im = shadow_im.filter(ImageFilter.GaussianBlur(radius=2.4))
    canvas.alpha_composite(shadow_im)

    paste_x = (CW - bw) // 2
    paste_y = int(round(172 - pad - ph + whole_bob_y))
    canvas.alpha_composite(warped_im, (paste_x, paste_y))

    return smooth_prefiltered_resize(canvas, 96, 96, post_blur=0.18)


def build_explorer_spritesheet() -> None:
    print("Building Stardew Valley Style Equipment-Free Explorer Spritesheet (8 cols x 56 rows of 96x96)...")
    south_clean = remove_white_bg_sdv(Image.open("assets/ai_raw/sdv_explorer_south.png"), min_hole_area=120, strip_floor_shadow=True)
    front_sw_clean = remove_white_bg_sdv(Image.open("assets/ai_raw/sdv_explorer_front.png"), min_hole_area=120, strip_floor_shadow=True)
    side_e_clean = remove_white_bg_sdv(Image.open("assets/ai_raw/sdv_explorer_side.png"), min_hole_area=120, strip_floor_shadow=True)
    back_nw_clean = remove_white_bg_sdv(Image.open("assets/ai_raw/sdv_explorer_back.png"), min_hole_area=120, strip_floor_shadow=True)
    up_n_clean = remove_white_bg_sdv(Image.open("assets/ai_raw/sdv_explorer_up.png"), min_hole_area=120, strip_floor_shadow=True)

    p_south = normalize_explorer_pose(south_clean, target_h=148)
    p_down_left = normalize_explorer_pose(front_sw_clean, target_h=148)
    p_down_right = p_down_left.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    p_right = normalize_explorer_pose(side_e_clean, target_h=148)
    p_left = p_right.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    p_up_left = normalize_explorer_pose(back_nw_clean, target_h=148)
    p_up_right = p_up_left.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    p_up = normalize_explorer_pose(up_n_clean, target_h=148)

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
    rows = len(ANIMATIONS) * len(DIRECTIONS)  # 56 rows
    frame_size = 96
    sheet = Image.new("RGBA", (cols * frame_size, rows * frame_size), (0, 0, 0, 0))
    showcase = Image.new("RGBA", (len(DIRECTIONS) * frame_size, len(ANIMATIONS) * frame_size), (32, 38, 52, 255))
    sc_draw = ImageDraw.Draw(showcase)

    row_idx = 0
    for a_idx, (anim_name, frame_count) in enumerate(ANIMATIONS):
        sample_f = 2 if anim_name != "idle" else 0
        for d_idx, dir_name in enumerate(DIRECTIONS):
            pose_2x = dir_poses[dir_name]
            for col_idx in range(cols):
                frame_im = render_smooth_explorer_frame(pose_2x, dir_name, anim_name, col_idx, frame_count)
                sheet.alpha_composite(frame_im, (col_idx * frame_size, row_idx * frame_size))
                if col_idx == sample_f:
                    cx0, cy0 = d_idx * frame_size, a_idx * frame_size
                    bg_col = (42, 50, 66, 255) if (a_idx + d_idx) % 2 == 0 else (35, 42, 56, 255)
                    sc_draw.rectangle([cx0 + 1, cy0 + 1, cx0 + frame_size - 2, cy0 + frame_size - 2], fill=bg_col)
                    showcase.alpha_composite(frame_im, (cx0, cy0))
            row_idx += 1

    sheet.save("assets/sprites/player_spritesheet.png")
    showcase.save("assets/sprites/player_8dir_showcase.png")

    icon = Image.new("RGBA", (128, 128), (58, 134, 202, 255))
    idraw = ImageDraw.Draw(icon)
    idraw.ellipse([12, 78, 116, 118], fill=(232, 182, 112, 255))
    idraw.ellipse([18, 80, 110, 114], fill=(92, 182, 78, 255))
    hero_icon = render_smooth_explorer_frame(p_down_right, "down_right", "idle", 0, 8)
    icon.alpha_composite(hero_icon, (16, 16))
    icon.save("icon.png")
    print(f"Saved Stardew Valley style Explorer spritesheet ({sheet.size[0]}x{sheet.size[1]})")


# =============================================================================
# 3. SEAMLESS STARDEW VALLEY ISOMETRIC TILESET (1024x200)
#    Zero directional brightness jumps across diamond borders -> seamless lawn!
# =============================================================================
def build_stardew_isometric_tileset() -> None:
    print("Building Seamless Stardew Valley Isometric Tileset (1024x200)...")
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

    # Seamless diamond mask with slight bleed so adjacent tiles never show background seams
    diamond_alpha = np.clip((1.025 - dist_diamond) * 26.0, 0.0, 1.0)
    diamond_alpha[yy >= S_TILE_H] = 0.0

    bot_y_at_x = hh + (1.0 - dx) * hh
    in_skirt = (yy >= bot_y_at_x - 3.0) & (yy < bot_y_at_x + S_SKIRT) & (dx <= 1.02)

    # Interior-only weight (0 at all 4 diamond edges, 1 in center of tile)
    # Guarantees that all 4 edges of every tile have the EXACT same base_rgb -> 100% seamless tiling!
    interior_w = np.clip((1.0 - dist_diamond) * 1.8, 0.0, 1.0) ** 1.4

    def make_stardew_iso_tile(
        base_rgb: tuple,
        patch_rgb: tuple,
        skirt_rgb: tuple,
        seed_offset: int,
        detail_fn=None,
    ) -> Image.Image:
        phase1 = (seed_offset * 1.57) % 6.28
        phase2 = (seed_offset * 2.61) % 6.28
        wave = (
            np.sin(xx * 0.045 + yy * 0.075 + phase1) * 0.5
            + np.cos(xx * 0.038 - yy * 0.082 + phase2) * 0.5
        )
        # Apply organic color variation ONLY in the interior so tile borders match 100% seamlessly!
        blend = np.clip((wave + 1.0) * 0.5, 0.0, 1.0) * interior_w * 0.65

        arr = np.zeros((SH, SW, 4), dtype=np.uint8)
        for c_i in range(3):
            top_c = base_rgb[c_i] * (1.0 - blend) + patch_rgb[c_i] * blend
            col_plane = np.where(in_skirt, skirt_rgb[c_i], top_c)
            col_plane = np.where(diamond_alpha > 0.05, top_c, col_plane)
            arr[:, :, c_i] = np.clip(col_plane, 0.0, 255.0).astype(np.uint8)

        alpha_plane = np.where(in_skirt, 255.0, diamond_alpha * 255.0)
        arr[:, :, 3] = np.clip(alpha_plane, 0.0, 255.0).astype(np.uint8)

        im = Image.fromarray(arr, "RGBA")
        if detail_fn is not None:
            detail_fn(ImageDraw.Draw(im), seed_offset)
        im = im.filter(ImageFilter.GaussianBlur(radius=0.9))
        return im.resize((TILE_W, CELL_H), Image.Resampling.LANCZOS)

    atlas = Image.new("RGBA", (COLS * TILE_W, ROWS * CELL_H), (0, 0, 0, 0))

    # ROW 0: Stardew Valley Cerulean Water Tiles (Deep Lake, Shallow Pond, Flowing River, Lilypads)
    for i in range(4):
        def deep_ripples(d: ImageDraw.ImageDraw, idx: int):
            for wy in (44, 68):
                wx = 92 + ((idx * 20 + wy) % 56)
                d.arc([wx, wy - 6, wx + 38, wy + 10], start=200, end=340, fill=(135, 202, 250, 145), width=4)
        t = make_stardew_iso_tile((48, 114, 184), (62, 132, 202), (42, 102, 168), i, deep_ripples)
        atlas.alpha_composite(t, (i * TILE_W, 0))

    for i in range(4):
        def shallow_ripples(d: ImageDraw.ImageDraw, idx: int):
            for wy in (42, 66):
                wx = 88 + ((idx * 22 + wy) % 60)
                d.arc([wx, wy - 6, wx + 40, wy + 10], start=200, end=340, fill=(195, 240, 255, 160), width=4)
        t = make_stardew_iso_tile((68, 148, 214), (88, 168, 230), (60, 136, 198), 10 + i, shallow_ripples)
        atlas.alpha_composite(t, ((4 + i) * TILE_W, 0))

    for i in range(4):
        def river_ripples(d: ImageDraw.ImageDraw, idx: int):
            for rx, ry in [(96, 48), (132, 66), (112, 78)]:
                ox = ((idx * 12) % 24) - 12
                d.line([(rx + ox, ry), (rx + ox + 28, ry + 12)], fill=(210, 246, 255, 165), width=4)
        t = make_stardew_iso_tile((62, 140, 208), (82, 162, 224), (56, 128, 192), 20 + i, river_ripples)
        atlas.alpha_composite(t, ((8 + i) * TILE_W, 0))

    for i in range(4):
        def lilypad_detail(d: ImageDraw.ImageDraw, idx: int):
            for lx, ly in [(104, 56), (150, 70)]:
                d.ellipse([lx - 20, ly - 10, lx + 20, ly + 10], fill=(78, 174, 76, 255), outline=(44, 112, 48, 220), width=3)
                if idx % 2 == 0 and lx == 104:
                    d.ellipse([lx - 8, ly - 10, lx + 8, ly + 2], fill=(255, 168, 198, 255))
                    d.ellipse([lx - 3, ly - 5, lx + 3, ly], fill=(255, 236, 112, 255))
        t = make_stardew_iso_tile((68, 148, 214), (88, 168, 230), (60, 136, 198), 30 + i, lilypad_detail)
        atlas.alpha_composite(t, ((12 + i) * TILE_W, 0))

    # ROW 1: Pelican Town Golden Dirt/Sand (0..3), Sunny Meadow Grass (4..7), Cindersap Forest Grass (8..11), Country Cobble Path (12..15)
    for i in range(4):
        def warm_sand_pebbles(d: ImageDraw.ImageDraw, idx: int):
            for px, py in [(104 + idx * 6, 58), (146 - idx * 4, 68)]:
                d.ellipse([px - 5, py - 3, px + 5, py + 3], fill=(208, 152, 88, 180))
        t = make_stardew_iso_tile((228, 176, 108), (238, 190, 124), (222, 170, 102), 40 + i, warm_sand_pebbles)
        atlas.alpha_composite(t, (i * TILE_W, CELL_H))

    for i in range(4):
        def stardew_meadow_clover(d: ImageDraw.ImageDraw, idx: int):
            for gx, gy in [(96 + idx * 8, 56), (144 - idx * 6, 66), (122, 74)]:
                d.ellipse([gx - 6, gy - 3, gx + 6, gy + 3], fill=(116, 198, 86, 175))
        t = make_stardew_iso_tile((92, 176, 76), (108, 192, 88), (90, 172, 74), 50 + i, stardew_meadow_clover)
        atlas.alpha_composite(t, ((4 + i) * TILE_W, CELL_H))

    for i in range(4):
        def stardew_forest_moss(d: ImageDraw.ImageDraw, idx: int):
            for mx, my in [(102, 54 + idx * 4), (148, 68), (124, 78)]:
                d.ellipse([mx - 10, my - 5, mx + 10, my + 5], fill=(78, 162, 82, 160))
        t = make_stardew_iso_tile((66, 146, 72), (82, 164, 84), (64, 142, 70), 60 + i, stardew_forest_moss)
        atlas.alpha_composite(t, ((8 + i) * TILE_W, CELL_H))

    for i in range(4):
        def stardew_cobble_path(d: ImageDraw.ImageDraw, idx: int):
            stones = [(100, 54, 18, 9), (142, 48, 20, 9), (120, 70, 22, 10), (158, 66, 16, 8)]
            for sx, sy, srw, srh in stones:
                ox = (idx % 2) * 6 - 3
                d.ellipse([sx + ox - srw, sy - srh, sx + ox + srw, sy + srh], fill=(182, 168, 152, 225), outline=(118, 92, 68, 195), width=3)
        t = make_stardew_iso_tile((204, 146, 90), (218, 160, 102), (198, 140, 86), 70 + i, stardew_cobble_path)
        atlas.alpha_composite(t, ((12 + i) * TILE_W, CELL_H))

    # ROW 2: Pelican Town Wooden Bridge (0..3), Tilled/Watered Soil (4..7), Mountain Quarry Stone (8..11), Autumn Grass (12..15)
    for i in range(4):
        def stardew_bridge(d: ImageDraw.ImageDraw, idx: int):
            for step in range(-64, 80, 24):
                d.line([(128 + step - 44, 64 + step // 2 - 22), (128 + step + 44, 64 + step // 2 + 22)], fill=(112, 64, 32, 195), width=4)
            d.line([(20, 60), (128, 10)], fill=(232, 178, 114, 255), width=7)
            d.line([(128, 114), (236, 60)], fill=(154, 98, 52, 255), width=7)
        t = make_stardew_iso_tile((196, 132, 78), (212, 148, 92), (168, 108, 60), 80 + i, stardew_bridge)
        atlas.alpha_composite(t, (i * TILE_W, CELL_H * 2))

    for i in range(4):
        t = make_stardew_iso_tile((124, 82, 52), (138, 94, 62), (118, 78, 48), 90 + i)
        atlas.alpha_composite(t, ((4 + i) * TILE_W, CELL_H * 2))

    for i in range(4):
        t = make_stardew_iso_tile((128, 134, 148), (144, 150, 164), (124, 130, 144), 100 + i)
        atlas.alpha_composite(t, ((8 + i) * TILE_W, CELL_H * 2))

    for i in range(4):
        def stardew_autumn_leaves(d: ImageDraw.ImageDraw, idx: int):
            for lx, ly in [(98 + idx * 6, 58), (146, 54 + idx * 4), (124, 76)]:
                col = (242, 136, 56, 210) if (lx + idx) % 2 == 0 else (248, 196, 68, 210)
                d.ellipse([lx - 7, ly - 4, lx + 7, ly + 4], fill=col)
        t = make_stardew_iso_tile((128, 172, 68), (146, 188, 78), (124, 168, 66), 110 + i, stardew_autumn_leaves)
        atlas.alpha_composite(t, ((12 + i) * TILE_W, CELL_H * 2))

    # ROW 3: Stardew Valley Forage & Wildflowers (Dandelions/Poppies/Sakura, Clover Tufts, Red Mushrooms, Smooth Pebbles)
    flower_sets = [
        ((244, 82, 86, 245), (255, 228, 92, 250)),
        ((255, 214, 68, 245), (238, 146, 40, 250)),
        ((252, 172, 202, 245), (255, 244, 196, 250)),
        ((250, 250, 255, 245), (252, 210, 74, 250)),
    ]
    for i, (petal_c, center_c) in enumerate(flower_sets):
        t = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
        d = ImageDraw.Draw(t)
        for fx, fy in [(96, 56), (140, 48), (118, 74), (156, 66)]:
            d.line([(fx, fy + 4), (fx, fy + 16)], fill=(64, 146, 62, 220), width=4)
            d.ellipse([fx - 9, fy - 7, fx + 9, fy + 7], fill=petal_c)
            d.ellipse([fx - 4, fy - 4, fx + 4, fy + 4], fill=center_c)
        t = t.filter(ImageFilter.GaussianBlur(radius=0.85))
        atlas.alpha_composite(t.resize((TILE_W, CELL_H), Image.Resampling.LANCZOS), (i * TILE_W, CELL_H * 3))

    for i in range(4):
        t = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
        d = ImageDraw.Draw(t)
        for gx, gy in [(96, 66), (132, 56), (154, 72), (116, 80)]:
            d.line([(gx, gy), (gx - 10, gy - 20)], fill=(68, 152, 64, 215), width=4)
            d.line([(gx + 4, gy), (gx + 4, gy - 24)], fill=(96, 184, 78, 215), width=4)
            d.line([(gx + 8, gy), (gx + 18, gy - 18)], fill=(122, 204, 94, 215), width=4)
        t = t.filter(ImageFilter.GaussianBlur(radius=0.85))
        atlas.alpha_composite(t.resize((TILE_W, CELL_H), Image.Resampling.LANCZOS), ((4 + i) * TILE_W, CELL_H * 3))

    for i in range(4):
        t = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
        d = ImageDraw.Draw(t)
        for mx, my in [(102, 60), (146, 70), (126, 50)]:
            d.rectangle([mx - 4, my, mx + 4, my + 14], fill=(246, 234, 212, 250))
            d.ellipse([mx - 13, my - 9, mx + 13, my + 4], fill=(232, 64, 58, 250))
            d.ellipse([mx - 5, my - 5, mx - 1, my - 1], fill=(255, 250, 238, 250))
            d.ellipse([mx + 3, my - 4, mx + 7, my], fill=(255, 250, 238, 250))
        t = t.filter(ImageFilter.GaussianBlur(radius=0.85))
        atlas.alpha_composite(t.resize((TILE_W, CELL_H), Image.Resampling.LANCZOS), ((8 + i) * TILE_W, CELL_H * 3))

    for i in range(4):
        t = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
        d = ImageDraw.Draw(t)
        for px, py in [(98, 60), (142, 54), (124, 76)]:
            d.ellipse([px - 12, py - 7, px + 12, py + 7], fill=(156, 162, 172, 230))
            d.ellipse([px - 6, py - 5, px + 4, py + 1], fill=(198, 204, 214, 230))
        t = t.filter(ImageFilter.GaussianBlur(radius=0.85))
        atlas.alpha_composite(t.resize((TILE_W, CELL_H), Image.Resampling.LANCZOS), ((12 + i) * TILE_W, CELL_H * 3))

    # ROW 4: Sakura Spring Lawn (0..3), Warm Calico Sandstone (4..7), Lush Pelican Clover Lawn (8..15)
    for i in range(4):
        def blossom_petals(d: ImageDraw.ImageDraw, idx: int):
            for px, py in [(96 + idx * 6, 58), (146, 52 + idx * 4), (122, 74)]:
                d.ellipse([px - 6, py - 4, px + 6, py + 4], fill=(255, 182, 210, 215))
        t = make_stardew_iso_tile((102, 184, 82), (118, 198, 94), (98, 180, 80), 120 + i, blossom_petals)
        atlas.alpha_composite(t, (i * TILE_W, CELL_H * 4))

    for i in range(4):
        t = make_stardew_iso_tile((214, 162, 112), (228, 176, 126), (208, 156, 108), 130 + i)
        atlas.alpha_composite(t, ((4 + i) * TILE_W, CELL_H * 4))

    for i in range(8):
        t = make_stardew_iso_tile((82, 166, 72), (98, 182, 84), (78, 162, 70), 140 + i)
        atlas.alpha_composite(t, ((8 + i) * TILE_W, CELL_H * 4))

    atlas.save("assets/tilesets/world_tileset.png")
    print("Saved seamless Stardew Valley assets/tilesets/world_tileset.png")


if __name__ == "__main__":
    build_world_objects()
    build_explorer_spritesheet()
    build_stardew_isometric_tileset()
    print("All Stardew Valley style isometric assets built successfully!")
