#!/usr/bin/env python3
"""Build the game's softly filtered Stardew-inspired isometric art assets.

The source illustrations live in assets/ai_raw. Sprites are resized directly to their
runtime resolution with premultiplied-alpha Lanczos filtering; they are not quantized
to a coarse logical-pixel grid. The ground atlas is painted at 4x and antialiased to
64x40 cells so it stays compatible with the existing Godot TileSet.
"""

from __future__ import annotations

import math
import os
import random
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
FRAME_SIZE = 96
TILE_WIDTH = 64
TILE_HEIGHT = 32
TILE_CELL_HEIGHT = 40
ATLAS_COLUMNS = 16
ATLAS_ROWS = 5
SUPERSAMPLE = 4
AI_TEXTURE_PATHS = {
    "grass": Path("assets/ai_raw/ai_meadow_texture.png"),
    "water": Path("assets/ai_raw/ai_water_texture.png"),
}
AI_TEXTURE_CACHE: dict[str, Image.Image | None] = {}

for directory in (
    "assets/sprites",
    "assets/tilesets",
    "assets/objects",
    "assets/ui",
):
    os.makedirs(directory, exist_ok=True)


def crop_to_alpha(image: Image.Image) -> Image.Image:
    """Crop transparent margins without being confused by RGB under alpha=0."""
    rgba = image.convert("RGBA")
    bbox = rgba.getchannel("A").getbbox()
    return rgba.crop(bbox) if bbox else rgba


def resize_rgba(
    image: Image.Image,
    size: tuple[int, int],
    resample: Image.Resampling = Image.Resampling.LANCZOS,
) -> Image.Image:
    """Resize RGBA art in premultiplied-alpha space to prevent dark/white halos."""
    rgba = np.asarray(image.convert("RGBA"), dtype=np.float32)
    alpha = rgba[:, :, 3:4] / 255.0
    premultiplied = rgba[:, :, :3] * alpha

    premultiplied_image = Image.fromarray(
        np.clip(np.round(premultiplied), 0, 255).astype(np.uint8), "RGB"
    )
    alpha_image = Image.fromarray(np.clip(np.round(alpha[:, :, 0] * 255), 0, 255).astype(np.uint8), "L")
    resized_rgb = np.asarray(premultiplied_image.resize(size, resample), dtype=np.float32)
    resized_alpha = np.asarray(alpha_image.resize(size, resample), dtype=np.float32) / 255.0

    rgb = np.where(
        resized_alpha[:, :, None] > 1e-4,
        resized_rgb / np.maximum(resized_alpha[:, :, None], 1e-4),
        0.0,
    )
    output = np.dstack(
        (
            np.clip(np.round(rgb), 0, 255).astype(np.uint8),
            np.clip(np.round(resized_alpha * 255), 0, 255).astype(np.uint8),
        )
    )
    return Image.fromarray(output, "RGBA")


def extract_clean_rgba(
    image: Image.Image,
    white_threshold: int = 230,
    chroma_threshold: int = 30,
    min_hole_area: int = 90,
    strip_floor_shadow: bool = False,
) -> Image.Image:
    """Remove the white studio backdrop while preserving small white details.

    Border-connected white pixels are flood-filled by Pillow's C implementation. Small
    enclosed regions (eye highlights, pale flowers, etc.) are retained; larger enclosed
    white areas are treated as accidental background holes.
    """
    rgba = np.array(image.convert("RGBA"), dtype=np.uint8, copy=True)
    height, width, _ = rgba.shape
    rgb = rgba[:, :, :3].astype(np.int16)
    min_channel = rgb.min(axis=2)
    max_channel = rgb.max(axis=2)
    is_white = (min_channel >= white_threshold) & ((max_channel - min_channel) <= chroma_threshold)

    if strip_floor_shadow:
        yy = np.arange(height)[:, None]
        taupe_shadow = (yy > int(height * 0.62)) & (min_channel >= 68) & ((max_channel - min_channel) <= 50)
        is_white |= taupe_shadow

    white_mask = Image.fromarray((is_white.astype(np.uint8) * 255), "L")
    border_points: list[tuple[int, int]] = []
    border_points.extend((x, 0) for x in range(width))
    if height > 1:
        border_points.extend((x, height - 1) for x in range(width))
    border_points.extend((0, y) for y in range(1, max(1, height - 1)))
    if width > 1:
        border_points.extend((width - 1, y) for y in range(1, max(1, height - 1)))

    for point in border_points:
        if white_mask.getpixel(point) == 255:
            ImageDraw.floodfill(white_mask, point, 128, thresh=0)

    white_components = np.asarray(white_mask, dtype=np.uint8) == 255
    background = np.asarray(white_mask, dtype=np.uint8) == 128
    if white_components.any():
        remaining = white_components.copy()
        ys, xs = np.nonzero(white_components)
        for start_y, start_x in zip(ys.tolist(), xs.tolist()):
            if not remaining[start_y, start_x]:
                continue
            queue: deque[tuple[int, int]] = deque([(start_y, start_x)])
            remaining[start_y, start_x] = False
            component: list[tuple[int, int]] = []
            while queue:
                y, x = queue.popleft()
                component.append((y, x))
                if y > 0 and remaining[y - 1, x]:
                    remaining[y - 1, x] = False
                    queue.append((y - 1, x))
                if y + 1 < height and remaining[y + 1, x]:
                    remaining[y + 1, x] = False
                    queue.append((y + 1, x))
                if x > 0 and remaining[y, x - 1]:
                    remaining[y, x - 1] = False
                    queue.append((y, x - 1))
                if x + 1 < width and remaining[y, x + 1]:
                    remaining[y, x + 1] = False
                    queue.append((y, x + 1))
            if len(component) >= min_hole_area:
                cy, cx = zip(*component)
                background[np.asarray(cy), np.asarray(cx)] = True

    rgba[background] = (0, 0, 0, 0)
    return Image.fromarray(rgba, "RGBA")


def adjust_color(image: Image.Image, saturation: float = 1.0, contrast: float = 1.0) -> Image.Image:
    """Make a restrained color adjustment without changing the alpha channel."""
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    rgb = Image.merge("RGB", rgba.split()[:3])
    if saturation != 1.0:
        rgb = ImageEnhance.Color(rgb).enhance(saturation)
    if contrast != 1.0:
        rgb = ImageEnhance.Contrast(rgb).enhance(contrast)
    return Image.merge("RGBA", (*rgb.split(), alpha))


def recolor_oak_to_sakura(oak_image: Image.Image) -> Image.Image:
    """Create a spring blossom palette from the oak canopy while retaining its shading."""
    rgba = np.array(oak_image.convert("RGBA"), dtype=np.float32)
    red, green, blue, alpha = rgba[:, :, 0], rgba[:, :, 1], rgba[:, :, 2], rgba[:, :, 3]
    foliage = (alpha > 20) & (green > red + 10)
    luminance = (red * 0.25 + green * 0.65 + blue * 0.10) / 255.0
    new_red = np.clip(154.0 + luminance * 100.0, 0, 255)
    new_green = np.clip(61.0 + (luminance**1.25) * 155.0, 0, 255)
    new_blue = np.clip(100.0 + (luminance**1.15) * 130.0, 0, 255)
    rgba[:, :, 0] = np.where(foliage, new_red, red)
    rgba[:, :, 1] = np.where(foliage, new_green, green)
    rgba[:, :, 2] = np.where(foliage, new_blue, blue)
    return Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8), "RGBA")


def fit_smooth_object(
    image: Image.Image,
    target_width: int,
    target_height: int,
    bottom_pad: int = 6,
    shadow_radius_x: int = 28,
    shadow_radius_y: int = 12,
    shadow_y_offset: int = -8,
    saturation: float = 1.0,
) -> Image.Image:
    """Fit an illustrated object to its runtime canvas with soft filtered edges."""
    cropped = crop_to_alpha(adjust_color(image, saturation=saturation, contrast=1.02))
    source_width, source_height = cropped.size
    available_width = max(1, target_width - 8)
    available_height = max(1, target_height - bottom_pad - 3)
    scale = min(available_width / float(source_width), available_height / float(source_height))
    resized_width = max(1, int(round(source_width * scale)))
    resized_height = max(1, int(round(source_height * scale)))
    sprite = resize_rgba(cropped, (resized_width, resized_height))
    sprite = sprite.filter(ImageFilter.UnsharpMask(radius=0.55, percent=38, threshold=5))

    canvas = Image.new("RGBA", (target_width, target_height), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (target_width, target_height), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    center_x = target_width // 2
    center_y = target_height - bottom_pad + shadow_y_offset
    shadow_draw.ellipse(
        (
            center_x - shadow_radius_x,
            center_y - shadow_radius_y,
            center_x + shadow_radius_x,
            center_y + shadow_radius_y,
        ),
        fill=(34, 43, 38, 78),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=2.2))
    canvas.alpha_composite(shadow)

    paste_x = (target_width - resized_width) // 2
    paste_y = target_height - bottom_pad - resized_height
    canvas.alpha_composite(sprite, (paste_x, paste_y))
    return canvas


def build_world_objects() -> None:
    print("Building softly filtered Stardew-inspired trees, rocks, and forest props...")

    raw = Path("assets/ai_raw")
    oak = extract_clean_rgba(Image.open(raw / "sdv_tree_oak.png"), min_hole_area=90)
    willow = extract_clean_rgba(Image.open(raw / "sdv_tree_willow.png"), min_hole_area=90)
    pine = extract_clean_rgba(Image.open(raw / "sdv_tree_pine.png"), min_hole_area=90)
    birch = extract_clean_rgba(Image.open(raw / "sdv_tree_birch.png"), min_hole_area=280)
    maple = extract_clean_rgba(Image.open(raw / "sdv_tree_maple.png"), min_hole_area=90)
    cherry = recolor_oak_to_sakura(oak)
    cedar = extract_clean_rgba(Image.open(raw / "iso_tree_ancient_fir.png"), min_hole_area=90)
    poplar = extract_clean_rgba(Image.open(raw / "iso_tree_poplar.png"), min_hole_area=90)

    tree_specs = [
        (oak, "tree_oak.png", 160, 176, 8, 42, 18, -12, 0.94),
        (willow, "tree_willow.png", 168, 176, 8, 46, 19, -12, 0.96),
        (pine, "tree_pine.png", 144, 192, 8, 34, 15, -10, 0.96),
        (birch, "tree_birch.png", 144, 176, 8, 34, 15, -10, 0.97),
        (maple, "tree_maple.png", 160, 176, 8, 42, 18, -12, 0.98),
        (cherry, "tree_cherry.png", 168, 176, 8, 44, 18, -12, 0.98),
        (cedar, "tree_cedar.png", 152, 192, 8, 38, 16, -10, 0.98),
        (poplar, "tree_poplar.png", 128, 196, 8, 30, 14, -10, 0.98),
    ]
    for source, filename, width, height, pad, rx, ry, yoff, saturation in tree_specs:
        result = fit_smooth_object(source, width, height, pad, rx, ry, yoff, saturation)
        result.save(Path("assets/objects") / filename)

    rock_specs = [
        ("iso_rock_boulder.png", "rock_large.png", 112, 96, 6, 42, 18, -12, 90),
        ("iso_rock_slate.png", "rock_slate.png", 112, 96, 6, 42, 18, -12, 90),
        ("iso_rock_sandstone.png", "rock_sandstone.png", 116, 96, 6, 44, 19, -12, 80),
        ("iso_rock_mossy_cluster.png", "rock_river.png", 108, 88, 6, 42, 18, -11, 250),
        ("iso_rock_limestone.png", "rock_limestone.png", 112, 92, 6, 42, 18, -11, 200),
        ("iso_rock_basalt.png", "rock_basalt.png", 116, 96, 6, 44, 19, -12, 120),
        ("iso_rock_flat_stepping.png", "rock_flat.png", 116, 88, 6, 44, 18, -11, 150),
        ("iso_rock_limestone.png", "rock_small.png", 72, 60, 4, 26, 11, -7, 200),
    ]
    for source_name, filename, width, height, pad, rx, ry, yoff, min_hole in rock_specs:
        source = extract_clean_rgba(Image.open(raw / source_name), min_hole_area=min_hole)
        result = fit_smooth_object(source, width, height, pad, rx, ry, yoff, saturation=0.98)
        result.save(Path("assets/objects") / filename)

    # Stump, berry bush, and fallen log are assembled from the same hand-painted source art.
    oak_crop = crop_to_alpha(oak)
    oak_width, oak_height = oak_crop.size
    trunk = oak_crop.crop(
        (int(oak_width * 0.22), int(oak_height * 0.58), int(oak_width * 0.78), oak_height)
    )
    trunk_draw = ImageDraw.Draw(trunk)
    trunk_width, trunk_height = trunk.size
    ring_box = (
        int(trunk_width * 0.18),
        2,
        int(trunk_width * 0.82),
        int(trunk_height * 0.36),
    )
    trunk_draw.ellipse(ring_box, fill=(74, 43, 27, 255), outline=(54, 31, 23, 255), width=5)
    trunk_draw.ellipse(
        (int(trunk_width * 0.22), 7, int(trunk_width * 0.78), int(trunk_height * 0.32)),
        fill=(219, 166, 105, 255),
    )
    trunk_draw.ellipse(
        (int(trunk_width * 0.32), 13, int(trunk_width * 0.68), int(trunk_height * 0.26)),
        fill=(177, 122, 72, 255),
    )
    fit_smooth_object(trunk, 64, 56, 6, 22, 10, -6, saturation=0.98).save(
        "assets/objects/tree_stump.png"
    )

    canopy = oak_crop.crop(
        (int(oak_width * 0.14), int(oak_height * 0.04), int(oak_width * 0.86), int(oak_height * 0.56))
    )
    canopy_width, canopy_height = canopy.size
    berry_draw = ImageDraw.Draw(canopy)
    for x_ratio, y_ratio in ((0.30, 0.40), (0.46, 0.28), (0.64, 0.34), (0.72, 0.52), (0.38, 0.62), (0.55, 0.54)):
        x = int(canopy_width * x_ratio)
        y = int(canopy_height * y_ratio)
        radius = max(9, int(canopy_width * 0.047))
        berry_draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            fill=(193, 53, 69, 255),
            outline=(96, 39, 39, 255),
            width=max(3, radius // 5),
        )
        berry_draw.ellipse(
            (x - radius // 2, y - radius // 2, x - radius // 6, y - radius // 6),
            fill=(255, 190, 144, 255),
        )
    fit_smooth_object(canopy, 68, 60, 6, 25, 11, -7, saturation=0.98).save(
        "assets/objects/bush_berry.png"
    )

    fallen_log = trunk.rotate(72, expand=True, resample=Image.Resampling.BICUBIC)
    fit_smooth_object(fallen_log, 96, 56, 6, 36, 12, -6, saturation=0.98).save(
        "assets/objects/log_fallen.png"
    )


DIRECTIONS = [
    "down",
    "down_right",
    "right",
    "up_right",
    "up",
    "up_left",
    "left",
    "down_left",
]

ANIMATION_FRAME_COUNT = 16

ANIMATIONS = [
    ("idle", ANIMATION_FRAME_COUNT),
    ("walk", ANIMATION_FRAME_COUNT),
    ("run", ANIMATION_FRAME_COUNT),
    ("axe", ANIMATION_FRAME_COUNT),
    ("pickaxe", ANIMATION_FRAME_COUNT),
    ("water", ANIMATION_FRAME_COUNT),
    ("interact", ANIMATION_FRAME_COUNT),
]


def bilinear_warp_rgba(image_array: np.ndarray, source_x: np.ndarray, source_y: np.ndarray) -> np.ndarray:
    """Bilinearly warp a transparent RGBA pose with correct premultiplied alpha."""
    height, width, _ = image_array.shape
    x0 = np.floor(source_x).astype(np.int32)
    y0 = np.floor(source_y).astype(np.int32)
    x1 = x0 + 1
    y1 = y0 + 1
    wx = (source_x - x0)[:, :, None]
    wy = (source_y - y0)[:, :, None]
    valid = (x0 >= 0) & (x1 < width) & (y0 >= 0) & (y1 < height)
    x0c = np.clip(x0, 0, width - 1)
    x1c = np.clip(x1, 0, width - 1)
    y0c = np.clip(y0, 0, height - 1)
    y1c = np.clip(y1, 0, height - 1)

    rgba = image_array.astype(np.float32)
    premultiplied = rgba.copy()
    premultiplied[:, :, :3] *= rgba[:, :, 3:4] / 255.0
    p00 = premultiplied[y0c, x0c]
    p10 = premultiplied[y0c, x1c]
    p01 = premultiplied[y1c, x0c]
    p11 = premultiplied[y1c, x1c]
    interpolated = (
        p00 * (1.0 - wx) * (1.0 - wy)
        + p10 * wx * (1.0 - wy)
        + p01 * (1.0 - wx) * wy
        + p11 * wx * wy
    )

    alpha = interpolated[:, :, 3:4]
    rgb = np.where(alpha > 1.0, interpolated[:, :, :3] / np.maximum(alpha / 255.0, 1e-4), 0.0)
    output = np.zeros_like(image_array)
    output[:, :, :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    output[:, :, 3] = np.where(valid, np.clip(alpha[:, :, 0], 0, 255), 0).astype(np.uint8)
    return output


def draw_action_overlay(
    canvas: Image.Image,
    direction: str,
    action: str,
    frame_index: int,
    frame_count: int,
    bob_offset: float,
) -> None:
    """Draw smooth, higher-resolution tool sprites over the matching action frames."""
    scale = 3
    overlay = Image.new("RGBA", (FRAME_SIZE * scale, FRAME_SIZE * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    logical_scale = 2 * scale  # original animation coordinates used a 48x48 canvas
    facing_x = -1 if "left" in direction else 1
    hand_x = 24 + facing_x * 5
    hand_y = 27 + bob_offset

    def point(x: float, y: float) -> tuple[int, int]:
        return (int(round(x * logical_scale)), int(round(y * logical_scale)))

    def line(points: list[tuple[float, float]], color: tuple[int, int, int, int], width: float) -> None:
        draw.line([point(x, y) for x, y in points], fill=color, width=max(1, int(round(width * scale))), joint="curve")

    if action in ("axe", "pickaxe"):
        t = frame_index / float(max(1, frame_count - 1))
        angle = (-1.15 + t * 2.1) * facing_x
        tip_x = hand_x + math.sin(angle) * 8
        tip_y = hand_y - math.cos(angle) * 8
        line([(hand_x, hand_y), (tip_x, tip_y)], (68, 44, 30, 255), 2.2)
        line([(hand_x, hand_y), (tip_x, tip_y)], (156, 102, 59, 255), 1.25)
        px = math.cos(angle) * 3
        py = math.sin(angle) * 3
        if action == "axe":
            blade = [
                point(tip_x, tip_y),
                point(tip_x + px, tip_y + py - 1.5),
                point(tip_x + px + facing_x * 2, tip_y + py + 2.5),
            ]
            draw.polygon(blade, fill=(194, 204, 203, 255), outline=(68, 55, 47, 255))
            line([(tip_x + px * 0.25, tip_y + py * 0.25 - 0.8), (tip_x + px, tip_y + py - 1.2)], (245, 239, 218, 255), 0.65)
        else:
            line(
                [(tip_x - px, tip_y - py), (tip_x + px, tip_y + py)],
                (62, 53, 47, 255),
                3.0,
            )
            line(
                [(tip_x - px, tip_y - py), (tip_x + px, tip_y + py)],
                (187, 197, 197, 255),
                1.6,
            )
    elif action == "water":
        cx = hand_x + facing_x * 4
        cy = hand_y + 1
        x0, y0 = point(cx - 2.5, cy - 2.5)
        x1, y1 = point(cx + 2.5, cy + 2.0)
        draw.rounded_rectangle((x0, y0, x1, y1), radius=2 * scale, fill=(73, 139, 184, 255), outline=(43, 83, 113, 255), width=scale)
        line([(cx + facing_x * 1.7, cy - 1.4), (cx + facing_x * 5.5, cy + 0.2)], (183, 207, 210, 255), 1.5)
        if frame_index in (2, 3, 4, 5):
            drop_y = cy + 3 + ((frame_index - 2) % 3)
            draw.ellipse((*point(cx + facing_x * 6 - 0.7, drop_y - 0.8), *point(cx + facing_x * 6 + 0.7, drop_y + 0.8)), fill=(141, 214, 238, 230))
            draw.ellipse((*point(cx + facing_x * 4 - 0.5, drop_y + 1.4), *point(cx + facing_x * 4 + 0.5, drop_y + 2.4)), fill=(203, 237, 240, 220))
    elif action == "interact" and frame_index in (1, 2, 3, 4, 5):
        sparkle_x = 24 + facing_x * 8
        sparkle_y = 21 - (1 if frame_index in (2, 3, 4) else 0)
        center = point(sparkle_x, sparkle_y)
        radius = 3.5 * scale
        diamond = [
            (center[0], int(center[1] - radius)),
            (int(center[0] + radius * 0.55), center[1]),
            (center[0], int(center[1] + radius)),
            (int(center[0] - radius * 0.55), center[1]),
        ]
        draw.polygon(diamond, fill=(255, 231, 145, 255), outline=(181, 127, 54, 255))
        draw.ellipse((center[0] - 2 * scale, center[1] - 2 * scale, center[0] + 2 * scale, center[1] + 2 * scale), fill=(255, 252, 222, 255))

    overlay = resize_rgba(overlay, (FRAME_SIZE, FRAME_SIZE))
    canvas.alpha_composite(overlay)


def render_smooth_explorer_frame(
    high_resolution_pose: Image.Image,
    direction: str,
    animation: str,
    frame_index: int,
    frame_count: int,
) -> Image.Image:
    """Render a single 96px animation frame without the old 2x coarse pixel grid."""
    phase = (frame_index / float(frame_count)) * 2.0 * math.pi
    wave = math.sin(phase)
    smooth_bob = 0.5 * (1.0 - math.cos(2.0 * phase))
    bell = math.sin((frame_index / float(frame_count)) * math.pi) ** 2
    horizontal = -1.0 if "left" in direction else (1.0 if "right" in direction else 0.0)

    pose_width, pose_height = high_resolution_pose.size
    pad = 32
    buffer = Image.new("RGBA", (pose_width + pad * 2, pose_height + pad * 2), (0, 0, 0, 0))
    buffer.alpha_composite(high_resolution_pose, (pad, pad))
    rgba = np.asarray(buffer, dtype=np.uint8)
    height, width, _ = rgba.shape
    yy, xx = np.meshgrid(
        np.arange(height, dtype=np.float32),
        np.arange(width, dtype=np.float32),
        indexing="ij",
    )
    y_norm = np.clip((yy - pad) / float(max(1, pose_height)), 0.0, 1.0)
    x_rel = (xx - width * 0.5) / float(max(1, pose_width * 0.5))
    leg_t = np.clip((y_norm - 0.58) / 0.42, 0.0, 1.0)
    leg_weight = 0.5 * (1.0 - np.cos(math.pi * leg_t))
    upper_weight = 1.0 - leg_weight
    src_x = xx.copy()
    src_y = yy.copy()
    bob_offset = 0.0

    if animation == "idle":
        src_y -= wave * 1.8 * upper_weight
    elif animation == "walk":
        bob_offset = -1.6 * smooth_bob
        side_sign = np.tanh(x_rel * 2.5)
        src_y -= wave * side_sign * 5.8 * leg_weight
        src_x -= wave * 2.5 * leg_weight
        src_x += wave * 1.7 * upper_weight * (y_norm * 0.8)
    elif animation == "run":
        bob_offset = -2.2 * smooth_bob
        side_sign = np.tanh(x_rel * 2.5)
        lean = (horizontal if horizontal else 0.3) * 3.8 * (1.0 - y_norm)
        src_x -= lean
        src_y -= wave * side_sign * 7.0 * leg_weight
        src_x -= wave * 3.1 * leg_weight
        src_x += wave * 2.5 * upper_weight * y_norm
    elif animation in ("axe", "pickaxe"):
        swing = wave * bell
        src_x -= swing * (horizontal if horizontal else 0.4) * 4.2 * upper_weight
        src_y -= swing * 2.8 * upper_weight
    elif animation == "water":
        src_x -= bell * (horizontal if horizontal else 0.4) * 3.5 * upper_weight
        src_y -= bell * 2.4 * upper_weight
    elif animation == "interact":
        bob_offset = -1.4 * bell
        src_y += bell * 2.6 * upper_weight * np.clip(x_rel, 0.0, 1.0)

    warped = bilinear_warp_rgba(rgba, src_x, src_y)
    silhouette = crop_to_alpha(Image.fromarray(warped, "RGBA"))
    body_height = 74
    body_width = max(24, int(round(silhouette.width * body_height / float(max(1, silhouette.height)))))
    body = resize_rgba(silhouette, (body_width, body_height))

    canvas = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.ellipse((32, 79, 64, 91), fill=(45, 42, 36, 96))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=3.0))
    canvas.alpha_composite(shadow)

    baseline = 85 + int(round(bob_offset))
    canvas.alpha_composite(body, ((FRAME_SIZE - body_width) // 2, baseline - body_height))

    if animation in ("axe", "pickaxe", "water", "interact"):
        draw_action_overlay(canvas, direction, animation, frame_index, frame_count, bob_offset)
    return canvas


def build_explorer_spritesheet() -> None:
    print("Building high-resolution 8-direction Explorer animations...")
    source_dir = Path("assets/ai_raw")
    poses = {
        "down": "ai_character_south.png",
        "down_left": "ai_character_south_east.png",
        "right": "ai_character_east.png",
        "up_left": "ai_character_north_east.png",
        "up": "ai_character_north.png",
    }
    cleaned: dict[str, Image.Image] = {}
    for direction, filename in poses.items():
        image = extract_clean_rgba(
            Image.open(source_dir / filename),
            min_hole_area=120,
            strip_floor_shadow=True,
        )
        cleaned[direction] = crop_to_alpha(image)

    def normalize_pose(image: Image.Image, target_height: int = 216) -> Image.Image:
        width, height = image.size
        target_width = max(1, int(round(width * target_height / float(max(1, height)))))
        return resize_rgba(image, (target_width, target_height))

    down = normalize_pose(cleaned["down"])
    down_left = normalize_pose(cleaned["down_left"])
    right = normalize_pose(cleaned["right"])
    up_left = normalize_pose(cleaned["up_left"])
    up = normalize_pose(cleaned["up"])

    poses_by_direction = {
        "down": down,
        "down_right": down_left.transpose(Image.Transpose.FLIP_LEFT_RIGHT),
        "right": right,
        "up_right": up_left.transpose(Image.Transpose.FLIP_LEFT_RIGHT),
        "up": up,
        "up_left": up_left,
        "left": right.transpose(Image.Transpose.FLIP_LEFT_RIGHT),
        "down_left": down_left,
    }

    columns = ANIMATION_FRAME_COUNT
    rows = len(ANIMATIONS) * len(DIRECTIONS)
    sheet = Image.new("RGBA", (columns * FRAME_SIZE, rows * FRAME_SIZE), (0, 0, 0, 0))
    showcase = Image.new(
        "RGBA",
        (len(DIRECTIONS) * FRAME_SIZE, len(ANIMATIONS) * FRAME_SIZE),
        (235, 226, 208, 255),
    )
    showcase_draw = ImageDraw.Draw(showcase)

    row_index = 0
    for animation_index, (animation, frame_count) in enumerate(ANIMATIONS):
        sample_frame = 4 if animation != "idle" else 0
        for direction_index, direction in enumerate(DIRECTIONS):
            pose = poses_by_direction[direction]
            for column in range(columns):
                frame = render_smooth_explorer_frame(pose, direction, animation, column, frame_count)
                sheet.alpha_composite(frame, (column * FRAME_SIZE, row_index * FRAME_SIZE))
                if column == sample_frame:
                    x = direction_index * FRAME_SIZE
                    y = animation_index * FRAME_SIZE
                    background = (236, 228, 211, 255) if (animation_index + direction_index) % 2 == 0 else (226, 216, 198, 255)
                    showcase_draw.rectangle((x + 1, y + 1, x + FRAME_SIZE - 2, y + FRAME_SIZE - 2), fill=background)
                    showcase.alpha_composite(frame, (x, y))
            row_index += 1

    sheet.save("assets/sprites/player_spritesheet.png", optimize=True)
    showcase.save("assets/sprites/player_8dir_showcase.png", optimize=True)

    icon = Image.new("RGBA", (128, 128), (64, 127, 105, 255))
    icon_draw = ImageDraw.Draw(icon)
    icon_draw.ellipse((12, 84, 116, 121), fill=(212, 176, 111, 255))
    icon_draw.ellipse((17, 82, 111, 112), fill=(86, 148, 76, 255))
    icon.alpha_composite(render_smooth_explorer_frame(poses_by_direction["down_right"], "down_right", "idle", 0, ANIMATION_FRAME_COUNT), (16, 12))
    icon.save("icon.png", optimize=True)
    print(f"Saved {sheet.width}x{sheet.height} sprite sheet and 8-direction showcase.")


def mix_color(first: tuple[int, int, int], second: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return tuple(int(round(a * (1.0 - amount) + b * amount)) for a, b in zip(first, second))


def shade_color(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(round(channel * factor)))) for channel in color)


def _scaled_point(point: tuple[float, float], scale: int) -> tuple[int, int]:
    return (int(round(point[0] * scale)), int(round(point[1] * scale)))


def ai_surface_patch(kind: str, variant: int, base: tuple[int, int, int]) -> Image.Image | None:
    """Crop and palette-map one AI-painted source texture into a runtime-sized tile patch."""
    if kind in ("deep_water", "shallow_water", "river", "lilypad"):
        source_key = "water"
    elif kind in ("meadow", "forest_grass", "clover", "sakura_lawn", "autumn_grass"):
        source_key = "grass"
    else:
        return None

    if source_key not in AI_TEXTURE_CACHE:
        source_path = AI_TEXTURE_PATHS[source_key]
        if not source_path.exists():
            AI_TEXTURE_CACHE[source_key] = None
        else:
            with Image.open(source_path) as source_image:
                AI_TEXTURE_CACHE[source_key] = source_image.convert("RGB")

    source = AI_TEXTURE_CACHE[source_key]
    if source is None:
        return None

    width, height = source.size
    if width < TILE_WIDTH or height < TILE_HEIGHT:
        source = source.resize(
            (max(TILE_WIDTH, width), max(TILE_HEIGHT, height)),
            Image.Resampling.LANCZOS,
        )
        width, height = source.size

    seed = sum(ord(char) for char in kind) * 17 + variant * 1_237 + (811 if source_key == "water" else 173)
    rng = random.Random(seed)
    x = rng.randint(0, width - TILE_WIDTH)
    y = rng.randint(0, height - TILE_HEIGHT)
    patch = source.crop((x, y, x + TILE_WIDTH, y + TILE_HEIGHT))
    pixels = np.asarray(patch, dtype=np.float32)
    luminance = pixels[:, :, 0] * 0.22 + pixels[:, :, 1] * 0.68 + pixels[:, :, 2] * 0.10
    center = float(np.median(luminance))
    contrast = np.clip((luminance - center) / max(45.0, center), -0.62, 0.46)
    brightness = 1.0 + contrast * 0.72
    chroma = (pixels - pixels.mean(axis=(0, 1), keepdims=True)) * 0.12
    recolored = np.asarray(base, dtype=np.float32)[None, None, :] * brightness[:, :, None] + chroma
    return Image.fromarray(np.clip(np.round(recolored), 0, 255).astype(np.uint8), "RGB")


def draw_tile_texture(
    kind: str,
    variant: int,
    base: tuple[int, int, int],
    left_face: tuple[int, int, int],
    right_face: tuple[int, int, int],
) -> Image.Image:
    """Paint one textured 64x40 isometric ground cell at 4x, then filter it down."""
    scale = SUPERSAMPLE
    high_size = (TILE_WIDTH * scale, TILE_CELL_HEIGHT * scale)
    tile = Image.new("RGBA", high_size, (0, 0, 0, 0))
    tile_draw = ImageDraw.Draw(tile)

    left_face_points = [(0, 16), (32, 32), (32, 40), (0, 24)]
    right_face_points = [(32, 32), (64, 16), (64, 24), (32, 40)]
    tile_draw.polygon([_scaled_point(point, scale) for point in left_face_points], fill=(*left_face, 255))
    tile_draw.polygon([_scaled_point(point, scale) for point in right_face_points], fill=(*right_face, 255))

    rng = random.Random(82_031 + variant * 1_009 + sum(ord(char) for char in kind) * 31)
    top = Image.new("RGBA", high_size, (*base, 255))
    ai_patch = ai_surface_patch(kind, variant, base)
    if ai_patch is not None:
        patch_high = ai_patch.resize((TILE_WIDTH * scale, TILE_HEIGHT * scale), Image.Resampling.NEAREST)
        top.paste(patch_high, (0, 0))
    detail = ImageDraw.Draw(top)

    def point(x: float, y: float) -> tuple[int, int]:
        return _scaled_point((x, y), scale)

    def line(
        points: list[tuple[float, float]],
        color: tuple[int, int, int],
        width: float = 1.0,
    ) -> None:
        detail.line(
            [point(x, y) for x, y in points],
            fill=(*color, 255),
            width=max(1, int(round(width * scale))),
            joint="curve",
        )

    def ellipse(
        box: tuple[float, float, float, float],
        fill: tuple[int, int, int],
        outline: tuple[int, int, int] | None = None,
        width: float = 0.8,
    ) -> None:
        scaled = tuple(int(round(value * scale)) for value in box)
        detail.ellipse(
            scaled,
            fill=(*fill, 255),
            outline=(*outline, 255) if outline else None,
            width=max(1, int(round(width * scale))),
        )

    def rounded_rect(
        box: tuple[float, float, float, float],
        fill: tuple[int, int, int],
        outline: tuple[int, int, int],
        radius: float = 1.0,
    ) -> None:
        scaled = tuple(int(round(value * scale)) for value in box)
        detail.rounded_rectangle(
            scaled,
            radius=max(1, int(round(radius * scale))),
            fill=(*fill, 255),
            outline=(*outline, 255),
            width=max(1, scale),
        )

    if kind in ("deep_water", "shallow_water", "river", "lilypad"):
        if kind == "deep_water":
            wave_dark, wave_light, sparkle = (44, 112, 160), (103, 172, 208), (200, 230, 236)
        elif kind == "shallow_water":
            wave_dark, wave_light, sparkle = (67, 143, 164), (127, 194, 194), (223, 239, 216)
        elif kind == "river":
            wave_dark, wave_light, sparkle = (49, 119, 156), (119, 183, 195), (215, 236, 230)
        else:
            wave_dark, wave_light, sparkle = (63, 132, 156), (117, 183, 184), (222, 238, 213)
        for index in range(5 if ai_patch is not None else 8):
            y = rng.uniform(4.0, 28.0)
            x = rng.uniform(5.0, 45.0)
            length = rng.uniform(5.0, 15.0)
            shift = (variant * 2.2 + index * 1.1) % 4.0
            wave = [(x + shift, y), (x + length * 0.38 + shift, y - 0.8), (x + length * 0.72 + shift, y + 0.2), (x + length + shift, y - 0.35)]
            line(wave, wave_light if index % 3 else wave_dark, 0.85 if index % 3 else 0.7)
            if index % 3 == 1:
                line([(wave[0][0], y + 1.0), (wave[2][0] + 1.0, y + 1.2)], wave_dark, 0.55)
        for _ in range(2 if ai_patch is not None else 3):
            x = rng.uniform(8, 56)
            y = rng.uniform(5, 25)
            line([(x, y), (x + 1.1, y - 0.7), (x + 2.4, y)], sparkle, 0.7)
        if kind == "lilypad":
            for x, y in ((21 + variant % 3, 17), (42 - variant % 4, 23)):
                ellipse((x - 5.3, y - 2.4, x + 5.0, y + 2.3), (71, 145, 74), (46, 104, 59), 0.65)
                line([(x - 3.5, y + 0.5), (x - 0.4, y - 0.1), (x + 3.0, y - 0.8)], (125, 186, 97), 0.65)
                if variant % 2 == 0 and x < 30:
                    for dx, dy in ((-1.2, -1.1), (0.0, -2.0), (1.2, -1.0)):
                        ellipse((x + dx - 0.9, y + dy - 0.9, x + dx + 0.9, y + dy + 0.9), (239, 174, 176))
                    ellipse((x - 0.9, y - 2.1, x + 0.9, y - 0.4), (242, 211, 114))

    elif kind in ("meadow", "forest_grass", "clover", "sakura_lawn", "autumn_grass"):
        if kind == "meadow":
            accents = [(97, 157, 78), (135, 186, 88), (76, 139, 71), (160, 191, 105)]
            blade_colors = [(61, 126, 62), (126, 177, 88), (88, 151, 70)]
        elif kind == "forest_grass":
            accents = [(58, 119, 69), (74, 134, 73), (93, 143, 78), (47, 105, 65)]
            blade_colors = [(42, 103, 59), (100, 151, 82), (66, 123, 71)]
        elif kind == "clover":
            accents = [(56, 124, 67), (83, 151, 75), (106, 163, 84), (65, 137, 70)]
            blade_colors = [(51, 112, 60), (114, 163, 83), (76, 138, 69)]
        elif kind == "sakura_lawn":
            accents = [(103, 160, 77), (136, 184, 92), (83, 143, 70), (227, 159, 174)]
            blade_colors = [(73, 133, 63), (146, 188, 99), (105, 156, 72)]
        else:
            accents = [(112, 147, 66), (154, 166, 69), (197, 147, 64), (90, 132, 63)]
            blade_colors = [(69, 112, 56), (184, 138, 65), (126, 156, 68)]

        for _ in range(18 if ai_patch is not None else 42):
            x = rng.uniform(2.0, 62.0)
            y = rng.uniform(1.0, 30.0)
            radius_x = rng.uniform(0.5, 2.4)
            radius_y = rng.uniform(0.45, 1.5)
            color = rng.choice(accents)
            ellipse((x - radius_x, y - radius_y, x + radius_x, y + radius_y), color)
        for _ in range(7 if ai_patch is not None else 12):
            x = rng.uniform(5.0, 59.0)
            y = rng.uniform(4.0, 28.0)
            height = rng.uniform(1.5, 3.8)
            color = rng.choice(blade_colors)
            line([(x, y), (x - rng.uniform(0.5, 1.1), y - height)], color, 0.8)
            line([(x + 0.5, y), (x + rng.uniform(0.6, 1.4), y - height * 0.7)], rng.choice(blade_colors), 0.7)
        for _ in range(5 if kind in ("meadow", "clover") else 3):
            x = rng.uniform(6.0, 58.0)
            y = rng.uniform(5.0, 27.0)
            leaf_color = rng.choice(accents)
            for dx, dy in ((-1.0, 0.0), (0.0, -0.8), (1.0, 0.0)):
                ellipse((x + dx - 0.9, y + dy - 0.7, x + dx + 0.9, y + dy + 0.7), leaf_color)
        if kind == "autumn_grass":
            for _ in range(5):
                x, y = rng.uniform(6.0, 58.0), rng.uniform(4.0, 28.0)
                ellipse((x - 1.0, y - 0.5, x + 1.0, y + 0.5), rng.choice(((221, 135, 60), (232, 183, 78), (190, 90, 61))))
        elif kind == "sakura_lawn":
            for _ in range(5):
                x, y = rng.uniform(6.0, 58.0), rng.uniform(4.0, 28.0)
                ellipse((x - 0.8, y - 0.5, x + 0.8, y + 0.5), (240, 183, 194))

    elif kind == "sand":
        for _ in range(48):
            x, y = rng.uniform(2.0, 62.0), rng.uniform(1.0, 30.0)
            color = rng.choice(((226, 188, 126), (198, 153, 94), (240, 210, 155), (216, 175, 112)))
            radius = rng.uniform(0.28, 0.8)
            ellipse((x - radius, y - radius * 0.65, x + radius, y + radius * 0.65), color)
        for _ in range(5):
            x, y = rng.uniform(5.0, 58.0), rng.uniform(4.0, 28.0)
            ellipse((x - 1.6, y - 0.8, x + 1.8, y + 0.9), (175, 134, 88), (222, 184, 130), 0.5)

    elif kind == "cobble":
        stone_colors = ((162, 146, 126), (174, 158, 138), (147, 133, 117), (183, 165, 144))
        for row, y in enumerate((3.5, 9.0, 14.5, 20.0, 25.5)):
            x = -2.0 + (row % 2) * 4.4 + (variant % 2) * 1.3
            while x < 67:
                stone_width = rng.uniform(4.4, 7.2)
                stone_height = rng.uniform(2.1, 3.1)
                color = rng.choice(stone_colors)
                outline = (111, 92, 74)
                rounded_rect((x, y, x + stone_width, y + stone_height), color, outline, 1.2)
                line([(x + 1.0, y + 0.8), (x + stone_width - 1.4, y + 0.8)], (207, 192, 170), 0.55)
                x += stone_width + rng.uniform(0.4, 1.2)

    elif kind == "bridge":
        wood_light = (200, 145, 91)
        wood_dark = (122, 77, 49)
        for row, y in enumerate(range(-8, 40, 5)):
            offset = (variant * 1.2 + row % 2) % 3
            line([(-6 + offset, y), (19 + offset, y + 12.5)], wood_dark, 1.0)
            line([(-5 + offset, y - 0.7), (18 + offset, y + 11.2)], wood_light, 0.55)
        for y in (6, 16, 25):
            for x in (13 + variant, 47 - variant):
                ellipse((x - 0.45, y - 0.45, x + 0.45, y + 0.45), (84, 57, 39))

    elif kind == "soil":
        for _ in range(22):
            x, y = rng.uniform(3.0, 61.0), rng.uniform(2.0, 29.0)
            radius_x, radius_y = rng.uniform(1.0, 3.5), rng.uniform(0.3, 1.1)
            ellipse((x - radius_x, y - radius_y, x + radius_x, y + radius_y), rng.choice(((118, 77, 49), (151, 100, 59), (132, 85, 52))))
        for y in (8.0, 16.0, 24.0):
            line([(5, y), (18, y + 1), (30, y + 0.2), (44, y + 1.1), (59, y + 0.1)], (91, 59, 41), 0.65)
        for _ in range(8):
            x, y = rng.uniform(4.0, 60.0), rng.uniform(3.0, 28.0)
            ellipse((x - 0.6, y - 0.45, x + 0.6, y + 0.45), (116, 160, 80))

    elif kind in ("slate", "sandstone"):
        for _ in range(12):
            x, y = rng.uniform(4.0, 60.0), rng.uniform(3.0, 28.0)
            width = rng.uniform(3.0, 7.0)
            height = rng.uniform(1.7, 3.3)
            color = rng.choice(((134, 143, 151), (155, 159, 161), (111, 124, 132), (174, 172, 164))) if kind == "slate" else rng.choice(((196, 144, 91), (221, 169, 112), (178, 119, 74), (233, 189, 134)))
            outline = shade_color(color, 0.68)
            rounded_rect((x, y, x + width, y + height), color, outline, 0.8)
            line([(x + 0.7, y + 0.7), (x + width - 1.0, y + 0.7)], mix_color(color, (250, 231, 191), 0.38), 0.55)

    top_mask = Image.new("L", high_size, 0)
    mask_draw = ImageDraw.Draw(top_mask)
    diamond = [(32, 0), (64, 16), (32, 32), (0, 16)]
    mask_draw.polygon([_scaled_point(point, scale) for point in diamond], fill=255)
    top.putalpha(top_mask)
    tile.alpha_composite(top)

    # A light north edge and a warm, soft south edge give the slabs the cozy hand-painted depth of farm-game tiles.
    tile_draw = ImageDraw.Draw(tile)
    north_edge = mix_color(base, (247, 239, 204), 0.20)
    south_edge = mix_color(base, left_face, 0.28)
    tile_draw.line([_scaled_point(point, scale) for point in ((1, 15), (32, 0.7), (63, 15))], fill=(*north_edge, 255), width=max(1, scale))
    tile_draw.line([_scaled_point(point, scale) for point in ((0.6, 16), (32, 31.5), (63.4, 16))], fill=(*south_edge, 255), width=max(1, scale))
    tile_draw.line([_scaled_point(point, scale) for point in ((1, 23.5), (32, 39.2), (63, 23.5))], fill=(*shade_color(left_face, 0.78), 255), width=max(1, scale))

    return resize_rgba(tile, (TILE_WIDTH, TILE_CELL_HEIGHT))


def make_decoration(kind: str, variant: int) -> Image.Image:
    """Create a small transparent ground accent for atlas row three."""
    scale = SUPERSAMPLE
    high_size = (TILE_WIDTH * scale, TILE_CELL_HEIGHT * scale)
    art = Image.new("RGBA", high_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(art)

    def point(x: float, y: float) -> tuple[int, int]:
        return _scaled_point((x, y), scale)

    def line(points: list[tuple[float, float]], color: tuple[int, int, int], width: float = 1.0) -> None:
        draw.line([point(x, y) for x, y in points], fill=(*color, 255), width=max(1, int(round(width * scale))), joint="curve")

    def ellipse(box: tuple[float, float, float, float], fill: tuple[int, int, int], outline: tuple[int, int, int] | None = None, width: float = 0.7) -> None:
        scaled = tuple(int(round(value * scale)) for value in box)
        draw.ellipse(scaled, fill=(*fill, 255), outline=(*outline, 255) if outline else None, width=max(1, int(round(width * scale))) if outline else 1)

    # A soft oval anchors each tuft to the ground without making the overlay a full tile.
    shadow = Image.new("RGBA", high_size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.ellipse((22 * scale, 24 * scale, 42 * scale, 30 * scale), fill=(37, 49, 36, 55))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=1.8 * scale))
    art.alpha_composite(shadow)

    if kind == "flowers":
        palette = ((225, 111, 101), (242, 199, 91), (214, 139, 174), (247, 235, 210))
        for index, (x, y) in enumerate(((20, 20), (31, 15), (40, 23), (49, 18))):
            bloom = palette[(variant + index) % len(palette)]
            line([(x, y + 5), (x + 0.2, y + 1.8)], (62, 111, 57), 0.85)
            ellipse((x - 2.5, y + 2.4, x - 0.2, y + 3.8), (87, 145, 68))
            ellipse((x + 0.4, y + 3.2, x + 2.6, y + 4.3), (91, 148, 71))
            for dx, dy in ((-1.2, 0.0), (1.2, 0.0), (0.0, -1.1), (0.0, 1.1)):
                ellipse((x + dx - 1.1, y + dy - 1.1, x + dx + 1.1, y + dy + 1.1), bloom)
            ellipse((x - 0.7, y - 0.7, x + 0.7, y + 0.7), (247, 218, 126))
    elif kind == "grass_tuft":
        for x, base_y in ((23, 26), (32, 24), (41, 27)):
            line([(x, base_y), (x - 2.0 - variant % 2, base_y - 7)], (64, 121, 59), 1.3)
            line([(x, base_y), (x + 0.4, base_y - 8)], (108, 163, 74), 1.8)
            line([(x, base_y), (x + 2.5, base_y - 5.8)], (78, 137, 62), 1.2)
            line([(x - 0.2, base_y - 1), (x - 3.0, base_y - 4.4)], (131, 178, 88), 0.8)
    elif kind == "mushrooms":
        for x, y, cap in ((23, 22, (180, 75, 60)), (34, 19, (208, 119, 71)), (44, 23, (168, 72, 59))):
            line([(x, y + 4), (x, y + 0.5)], (229, 213, 176), 2.2)
            ellipse((x - 3.0, y - 1.7, x + 3.0, y + 1.0), cap, (96, 58, 46), 0.65)
            ellipse((x - 1.6, y - 1.2, x - 0.8, y - 0.2), (245, 223, 184))
            line([(x - 2.0, y + 1.0), (x + 2.0, y + 1.0)], (237, 221, 185), 0.6)
    else:
        rng = random.Random(9200 + variant * 71)
        for _ in range(7):
            x = rng.uniform(19, 48)
            y = rng.uniform(17, 26)
            color = rng.choice(((134, 142, 145), (171, 172, 162), (105, 119, 126), (190, 178, 154)))
            ellipse((x - 2.3, y - 1.2, x + 2.4, y + 1.3), color, shade_color(color, 0.68), 0.6)
            line([(x - 1.3, y - 0.4), (x + 0.3, y - 0.8)], (218, 211, 192), 0.45)

    return resize_rgba(art, (TILE_WIDTH, TILE_CELL_HEIGHT))


def build_stardew_isometric_tileset() -> None:
    """Build the existing 16x5 atlas layout with warmer, richer hand-painted tile art."""
    print("Painting 4x supersampled Stardew-inspired ground tiles...")
    atlas = Image.new(
        "RGBA",
        (ATLAS_COLUMNS * TILE_WIDTH, ATLAS_ROWS * TILE_CELL_HEIGHT),
        (0, 0, 0, 0),
    )

    palettes = {
        "deep_water": ((63, 128, 178), (40, 94, 139), (32, 78, 123)),
        "shallow_water": ((93, 159, 177), (63, 124, 145), (48, 103, 128)),
        "river": ((73, 139, 175), (48, 106, 139), (36, 88, 122)),
        "lilypad": ((82, 149, 169), (53, 113, 136), (42, 95, 120)),
        "sand": ((218, 179, 121), (183, 137, 88), (158, 111, 74)),
        "meadow": ((119, 177, 92), (83, 139, 77), (65, 115, 67)),
        "forest_grass": ((83, 139, 82), (59, 113, 70), (46, 93, 61)),
        "cobble": ((164, 139, 111), (127, 102, 82), (105, 82, 67)),
        "bridge": ((177, 119, 72), (139, 83, 51), (112, 65, 43)),
        "soil": ((139, 94, 61), (105, 68, 49), (86, 55, 42)),
        "slate": ((133, 143, 151), (100, 112, 123), (81, 93, 105)),
        "autumn_grass": ((145, 160, 84), (107, 131, 67), (84, 108, 59)),
        "sakura_lawn": ((124, 177, 96), (87, 139, 75), (68, 116, 65)),
        "sandstone": ((202, 151, 101), (166, 111, 75), (139, 86, 62)),
        "clover": ((94, 158, 82), (65, 126, 69), (49, 103, 61)),
    }

    def place_ground(row: int, start_column: int, kind: str, count: int) -> None:
        base, left, right = palettes[kind]
        for variant in range(count):
            tile = draw_tile_texture(kind, variant, base, left, right)
            atlas.paste(tile, (start_column * TILE_WIDTH + variant * TILE_WIDTH, row * TILE_CELL_HEIGHT))

    place_ground(0, 0, "deep_water", 4)
    place_ground(0, 4, "shallow_water", 4)
    place_ground(0, 8, "river", 4)
    place_ground(0, 12, "lilypad", 4)
    place_ground(1, 0, "sand", 4)
    place_ground(1, 4, "meadow", 4)
    place_ground(1, 8, "forest_grass", 4)
    place_ground(1, 12, "cobble", 4)
    place_ground(2, 0, "bridge", 4)
    place_ground(2, 4, "soil", 4)
    place_ground(2, 8, "slate", 4)
    place_ground(2, 12, "autumn_grass", 4)

    decorations = ("flowers", "grass_tuft", "mushrooms", "pebbles")
    for group_index, kind in enumerate(decorations):
        for variant in range(4):
            tile = make_decoration(kind, variant)
            atlas.paste(tile, ((group_index * 4 + variant) * TILE_WIDTH, 3 * TILE_CELL_HEIGHT))

    place_ground(4, 0, "sakura_lawn", 4)
    place_ground(4, 4, "sandstone", 4)
    place_ground(4, 8, "clover", 8)

    atlas.save("assets/tilesets/world_tileset.png", optimize=True)
    print(f"Saved {atlas.width}x{atlas.height} tileset with 80 variants.")


if __name__ == "__main__":
    build_world_objects()
    build_explorer_spritesheet()
    build_stardew_isometric_tileset()
    print("All softly filtered Stardew-inspired game assets built successfully.")
