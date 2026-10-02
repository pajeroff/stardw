#!/usr/bin/env python3
"""
Procedural Pixel-Art Asset Generator for Stardw (Godot 4.7)
Generates all game spritesheets, tilesets, world object sprites, and UI icons
using pure Python (standard library struct + zlib, zero external dependencies).

Generated assets:
- assets/sprites/player_spritesheet.png (192x1792: 6 cols x 56 rows of 32x32 frames)
  8 directions x 7 animations (idle, walk, run, axe, pickaxe, water, interact)
- assets/sprites/player_preview_sheet.png (labeled preview contact sheet)
- assets/tilesets/world_tileset.png (256x80: 16 cols x 5 rows of 16x16 tiles)
- assets/objects/tree_oak.png (32x48)
- assets/objects/tree_pine.png (32x48)
- assets/objects/tree_birch.png (32x48)
- assets/objects/tree_stump.png (16x16)
- assets/objects/bush_berry.png (16x16)
- assets/objects/rock_large.png (32x32)
- assets/objects/rock_small.png (16x16)
- assets/objects/rock_ore.png (16x16)
- assets/objects/log_fallen.png (32x16)
- assets/ui/icon_axe.png (16x16)
- assets/ui/icon_pickaxe.png (16x16)
- assets/ui/icon_water.png (16x16)
- assets/ui/icon_hand.png (16x16)
- icon.png (64x64)
"""

import math
import os
import random
import struct
import zlib
from typing import List, Tuple

RGBA = Tuple[int, int, int, int]
TRANSPARENT: RGBA = (0, 0, 0, 0)


class Canvas:
    def __init__(self, width: int, height: int, bg: RGBA = TRANSPARENT):
        self.width = width
        self.height = height
        self.pixels: List[RGBA] = [bg] * (width * height)

    def clear(self, color: RGBA = TRANSPARENT) -> None:
        self.pixels = [color] * (self.width * self.height)

    def set_px(self, x: int, y: int, color: RGBA) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            if color[3] == 0:
                return
            if color[3] == 255:
                self.pixels[y * self.width + x] = color
            else:
                # Alpha blend over existing pixel
                dst = self.pixels[y * self.width + x]
                sa = color[3] / 255.0
                da = dst[3] / 255.0
                out_a = sa + da * (1.0 - sa)
                if out_a <= 0:
                    self.pixels[y * self.width + x] = TRANSPARENT
                else:
                    r = int((color[0] * sa + dst[0] * da * (1.0 - sa)) / out_a)
                    g = int((color[1] * sa + dst[1] * da * (1.0 - sa)) / out_a)
                    b = int((color[2] * sa + dst[2] * da * (1.0 - sa)) / out_a)
                    self.pixels[y * self.width + x] = (
                        max(0, min(255, r)),
                        max(0, min(255, g)),
                        max(0, min(255, b)),
                        max(0, min(255, int(out_a * 255))),
                    )

    def get_px(self, x: int, y: int) -> RGBA:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.pixels[y * self.width + x]
        return TRANSPARENT

    def fill_rect(self, x: int, y: int, w: int, h: int, color: RGBA) -> None:
        for py in range(y, y + h):
            for px in range(x, x + w):
                self.set_px(px, py, color)

    def fill_ellipse(self, cx: float, cy: float, rx: float, ry: float, color: RGBA) -> None:
        x0 = int(math.floor(cx - rx - 1))
        x1 = int(math.ceil(cx + rx + 1))
        y0 = int(math.floor(cy - ry - 1))
        y1 = int(math.ceil(cy + ry + 1))
        for py in range(y0, y1 + 1):
            for px in range(x0, x1 + 1):
                dx = (px - cx) / max(0.001, rx)
                dy = (py - cy) / max(0.001, ry)
                if dx * dx + dy * dy <= 1.0:
                    self.set_px(px, py, color)

    def draw_line(self, x0: int, y0: int, x1: int, y1: int, color: RGBA, thickness: int = 1) -> None:
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for i in range(steps + 1):
            t = i / steps
            px = int(round(x0 + (x1 - x0) * t))
            py = int(round(y0 + (y1 - y0) * t))
            if thickness <= 1:
                self.set_px(px, py, color)
            else:
                r = thickness // 2
                self.fill_rect(px - r, py - r, thickness, thickness, color)

    def blit(self, src: "Canvas", dx: int, dy: int) -> None:
        for y in range(src.height):
            for x in range(src.width):
                c = src.get_px(x, y)
                if c[3] > 0:
                    self.set_px(dx + x, dy + y, c)

    def save_png(self, filepath: str) -> None:
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        raw_rows = bytearray()
        for y in range(self.height):
            raw_rows.append(0)  # Filter type 0 (None)
            row_start = y * self.width
            for x in range(self.width):
                r, g, b, a = self.pixels[row_start + x]
                raw_rows.extend((r, g, b, a))

        def make_chunk(chunk_type: bytes, data: bytes) -> bytes:
            chunk = struct.pack(">I", len(data)) + chunk_type + data
            crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
            return chunk + struct.pack(">I", crc)

        ihdr = struct.pack(">IIBBBBB", self.width, self.height, 8, 6, 0, 0, 0)
        compressed = zlib.compress(bytes(raw_rows), level=9)
        png_data = (
            b"\x89PNG\r\n\x1a\n"
            + make_chunk(b"IHDR", ihdr)
            + make_chunk(b"IDAT", compressed)
            + make_chunk(b"IEND", b"")
        )
        with open(filepath, "wb") as f:
            f.write(png_data)


# =============================================================================
# COLOR PALETTE (Warm Stardew-inspired 16-bit Pixel Art Palette)
# =============================================================================
OUTLINE = (28, 22, 36, 255)
SHADOW_ALPHA = (16, 14, 28, 95)

# Character colors
SKIN_LIGHT = (255, 218, 185, 255)
SKIN_MID = (240, 188, 148, 255)
SKIN_DARK = (204, 144, 108, 255)
BLUSH = (238, 138, 130, 255)

HAIR_LIGHT = (168, 94, 52, 255)
HAIR_MID = (128, 66, 36, 255)
HAIR_DARK = (86, 40, 22, 255)

HAT_STRAW_LIGHT = (246, 218, 122, 255)
HAT_STRAW_MID = (222, 180, 82, 255)
HAT_STRAW_DARK = (178, 132, 48, 255)
HAT_BAND = (196, 56, 56, 255)

SHIRT_LIGHT = (92, 178, 112, 255)
SHIRT_MID = (64, 142, 86, 255)
SHIRT_DARK = (44, 102, 64, 255)

OVERALL_LIGHT = (82, 128, 198, 255)
OVERALL_MID = (56, 96, 162, 255)
OVERALL_DARK = (38, 68, 122, 255)
BUTTON_GOLD = (245, 208, 76, 255)

SCARF_LIGHT = (232, 84, 72, 255)
SCARF_DARK = (176, 48, 42, 255)

BOOT_LIGHT = (118, 74, 46, 255)
BOOT_DARK = (76, 44, 26, 255)

EYE_COLOR = (34, 32, 52, 255)
EYE_WHITE = (250, 250, 252, 255)

# Tool colors
WOOD_LIGHT = (188, 132, 78, 255)
WOOD_DARK = (128, 82, 44, 255)
STEEL_LIGHT = (232, 240, 248, 255)
STEEL_MID = (172, 186, 204, 255)
STEEL_DARK = (112, 126, 146, 255)
SWOOSH_WHITE = (240, 248, 255, 190)
SWOOSH_BLUE = (150, 215, 255, 150)
SPARK_GOLD = (255, 230, 96, 255)
WATER_CAN_BLUE = (92, 164, 224, 255)
WATER_CAN_DARK = (56, 114, 172, 255)
WATER_DROP_LIGHT = (145, 225, 255, 235)
WATER_DROP_MID = (75, 175, 245, 220)


# =============================================================================
# 1. CHARACTER SPRITESHEET GENERATOR (8 Directions x 7 Animations)
# =============================================================================
DIRECTIONS = [
    "down",        # Row +0: S  (Вниз)
    "down_right",  # Row +1: SE (Вниз-Вправо)
    "right",       # Row +2: E  (Вправо)
    "up_right",    # Row +3: NE (Вверх-Вправо)
    "up",          # Row +4: N  (Вверх)
    "up_left",     # Row +5: NW (Вверх-Влево)
    "left",        # Row +6: W  (Влево)
    "down_left",   # Row +7: SW (Вниз-Влево)
]

ANIMATIONS = [
    ("idle", 4),      # rows 0..7
    ("walk", 6),      # rows 8..15
    ("run", 6),       # rows 16..23
    ("axe", 6),       # rows 24..31
    ("pickaxe", 6),   # rows 32..39
    ("water", 6),     # rows 40..47
    ("interact", 4),  # rows 48..55
]


def draw_character_frame(direction: str, anim: str, frame_idx: int, total_frames: int) -> Canvas:
    c = Canvas(32, 32)
    phase = (frame_idx / float(total_frames)) * 2.0 * math.pi

    # Direction decomposition:
    # dx: -1 (left), 0 (center), +1 (right)
    # dy: -1 (up), 0 (side), +1 (down)
    dx = 0
    dy = 0
    if "left" in direction:
        dx = -1
    elif "right" in direction:
        dx = 1
    if "up" in direction:
        dy = -1
    elif "down" in direction:
        dy = 1

    is_diagonal = (dx != 0 and dy != 0)
    is_back = (dy == -1)
    is_front = (dy == 1)
    is_side = (dy == 0)

    # Animation offsets
    bob_y = 0
    lean_x = 0
    lean_y = 0
    left_leg_y = 0
    right_leg_y = 0
    left_leg_x = 0
    right_leg_x = 0
    left_arm_y = 0
    right_arm_y = 0
    left_arm_x = 0
    right_arm_x = 0
    blink = False

    if anim == "idle":
        bob_y = 1 if frame_idx in (1, 2) else 0
        blink = (frame_idx == 3)
    elif anim == "walk":
        # 6-frame smooth walk cycle
        walk_bob = [0, -1, 0, 0, -1, 0]
        leg_swing = [-2, -1, 1, 2, 1, -1]
        bob_y = walk_bob[frame_idx % 6]
        swing = leg_swing[frame_idx % 6]
        if is_side:
            left_leg_x = swing
            right_leg_x = -swing
            left_leg_y = -1 if swing > 0 else 0
            right_leg_y = -1 if swing < 0 else 0
            left_arm_x = -swing
            right_arm_x = swing
        elif is_diagonal:
            left_leg_x = int(round(swing * 0.7))
            right_leg_x = -int(round(swing * 0.7))
            left_leg_y = -1 if swing > 0 else 1
            right_leg_y = -1 if swing < 0 else 1
            left_arm_x = -int(round(swing * 0.7))
            right_arm_x = int(round(swing * 0.7))
        else:
            left_leg_y = -1 if swing > 0 else 1
            right_leg_y = -1 if swing < 0 else 1
            left_arm_y = 1 if swing > 0 else -1
            right_arm_y = 1 if swing < 0 else -1
    elif anim == "run":
        # 6-frame energetic run cycle with forward lean and dust puffs
        run_bob = [-1, -2, 0, -1, -2, 0]
        leg_swing = [-3, -2, 2, 3, 2, -2]
        bob_y = run_bob[frame_idx % 6]
        lean_x = dx
        lean_y = 1 if dy >= 0 else 0
        swing = leg_swing[frame_idx % 6]
        if is_side:
            left_leg_x = swing
            right_leg_x = -swing
            left_leg_y = -2 if abs(swing) >= 2 and swing > 0 else 0
            right_leg_y = -2 if abs(swing) >= 2 and swing < 0 else 0
            left_arm_x = -swing
            right_arm_x = swing
            left_arm_y = -1
            right_arm_y = -1
        elif is_diagonal:
            left_leg_x = swing // 2
            right_leg_x = -swing // 2
            left_leg_y = -2 if swing > 0 else 1
            right_leg_y = -2 if swing < 0 else 1
            left_arm_x = -swing // 2
            right_arm_x = swing // 2
            left_arm_y = -1
            right_arm_y = -1
        else:
            left_leg_y = -2 if swing > 0 else 1
            right_leg_y = -2 if swing < 0 else 1
            left_arm_y = -2 if swing < 0 else 1
            right_arm_y = -2 if swing > 0 else 1
    elif anim in ("axe", "pickaxe"):
        # Windup (0,1), swing (2,3), impact (4), recover (5)
        if frame_idx in (0, 1):
            bob_y = -1
            right_arm_y = -3
            left_arm_y = -2
        elif frame_idx in (2, 3):
            bob_y = 1
            lean_x = dx
            lean_y = dy
            right_arm_y = 2
            left_arm_y = 1
        elif frame_idx == 4:
            bob_y = 1
            right_arm_y = 2
        else:
            bob_y = 0
    elif anim == "water":
        # Tilt watering can forward and pour water drops
        bob_y = 1 if frame_idx in (1, 2, 3, 4) else 0
        right_arm_y = 1
        left_arm_y = 1
    elif anim == "interact":
        # Cheerful wave / gather animation
        jump = [0, -2, -3, -1]
        bob_y = jump[frame_idx % 4]
        right_arm_y = -4 if frame_idx in (1, 2) else -2
        left_arm_y = -2 if frame_idx in (1, 2) else 0

    # Ground shadow under feet
    c.fill_ellipse(15.5, 28.0, 6.5, 2.3, SHADOW_ALPHA)

    # Run dust particles behind feet
    if anim == "run" and frame_idx in (1, 4):
        dust_x = 16 - dx * 6
        dust_y = 27 - dy * 2
        c.fill_ellipse(dust_x, dust_y, 2.2, 1.5, (235, 225, 200, 180))
        c.set_px(dust_x - dx * 2, dust_y - 2, (245, 240, 220, 140))

    cx = 16 + lean_x
    cy = 16 + bob_y + lean_y

    # -------------------------------------------------------------------------
    # LEGS & BOOTS
    # -------------------------------------------------------------------------
    lx_base = cx - 3 + left_leg_x
    rx_base = cx + 1 + right_leg_x
    if is_side:
        lx_base = cx - 1 + left_leg_x
        rx_base = cx - 1 + right_leg_x

    ly_base = 23 + bob_y + left_leg_y
    ry_base = 23 + bob_y + right_leg_y

    # Draw back leg first if side/diagonal
    legs = [
        (lx_base, ly_base, OVERALL_DARK, BOOT_DARK),
        (rx_base, ry_base, OVERALL_MID, BOOT_LIGHT),
    ]
    if dx < 0:
        legs.reverse()

    for leg_x, leg_y, pant_col, boot_col in legs:
        # Pant leg
        c.fill_rect(leg_x, leg_y, 3, 3, OUTLINE)
        c.fill_rect(leg_x + 1, leg_y, 1, 2, pant_col)
        # Boot
        c.fill_rect(leg_x, leg_y + 2, 3, 3, OUTLINE)
        c.fill_rect(leg_x + 1, leg_y + 2, 2 if dx >= 0 else 1, 2, boot_col)

    # -------------------------------------------------------------------------
    # TORSO (Tunic + Overalls + Scarf)
    # -------------------------------------------------------------------------
    torso_x = cx - 5
    torso_y = cy + 1
    torso_w = 10
    torso_h = 8

    # Outline of torso
    c.fill_rect(torso_x, torso_y, torso_w, torso_h, OUTLINE)
    # Tunic base
    c.fill_rect(torso_x + 1, torso_y + 1, torso_w - 2, torso_h - 2, SHIRT_MID)
    c.fill_rect(torso_x + 2, torso_y + 1, torso_w - 4, 2, SHIRT_LIGHT)

    # Overalls over tunic
    c.fill_rect(torso_x + 1, torso_y + 4, torso_w - 2, 3, OVERALL_MID)
    c.fill_rect(torso_x + 2, torso_y + 5, torso_w - 4, 2, OVERALL_DARK)

    if is_front or (is_diagonal and dy > 0):
        strap_shift = dx * 1
        # Overall straps & gold buttons
        c.fill_rect(torso_x + 2 + strap_shift, torso_y + 1, 1, 4, OVERALL_MID)
        c.fill_rect(torso_x + 7 + strap_shift, torso_y + 1, 1, 4, OVERALL_MID)
        c.set_px(torso_x + 2 + strap_shift, torso_y + 4, BUTTON_GOLD)
        c.set_px(torso_x + 7 + strap_shift, torso_y + 4, BUTTON_GOLD)
        # Front bib
        c.fill_rect(torso_x + 3 + strap_shift, torso_y + 3, 4, 3, OVERALL_LIGHT)
    elif is_back or (is_diagonal and dy < 0):
        # Back crossed straps & backpack pouch
        c.fill_rect(torso_x + 2, torso_y + 1, 6, 5, OVERALL_DARK)
        c.fill_rect(torso_x + 3, torso_y + 2, 4, 4, BOOT_LIGHT)
        c.fill_rect(torso_x + 3, torso_y + 2, 4, 1, HAT_STRAW_MID)
    else:
        # Side view strap
        c.fill_rect(torso_x + 3, torso_y + 1, 3, 5, OVERALL_LIGHT)
        c.set_px(torso_x + 4, torso_y + 4, BUTTON_GOLD)

    # Red scarf around neck (flutters when running!)
    scarf_y = torso_y
    c.fill_rect(torso_x + 2, scarf_y, 6, 2, SCARF_DARK)
    c.fill_rect(torso_x + 3, scarf_y, 4, 1, SCARF_LIGHT)
    if anim == "run":
        tail_x = cx - dx * 5 if dx != 0 else cx - 4
        c.fill_rect(tail_x, scarf_y + (frame_idx % 2), 3, 2, SCARF_LIGHT)

    # -------------------------------------------------------------------------
    # ARMS & HANDS (Left & Right)
    # -------------------------------------------------------------------------
    l_arm_pos = (torso_x - 2 + left_arm_x, torso_y + 1 + left_arm_y)
    r_arm_pos = (torso_x + torso_w - 1 + right_arm_x, torso_y + 1 + right_arm_y)

    def draw_arm(ax: int, ay: int, shade: RGBA) -> None:
        c.fill_rect(ax, ay, 3, 5, OUTLINE)
        c.fill_rect(ax + 1, ay + 1, 1, 2, shade)
        c.fill_rect(ax + 1, ay + 3, 1, 1, SKIN_MID)

    if is_side:
        # Only draw back arm before head, front arm after
        front_ax = cx - 1 + right_arm_x
        front_ay = torso_y + 1 + right_arm_y
        draw_arm(front_ax, front_ay, SHIRT_LIGHT)
    else:
        draw_arm(l_arm_pos[0], l_arm_pos[1], SHIRT_DARK if dx > 0 else SHIRT_LIGHT)
        draw_arm(r_arm_pos[0], r_arm_pos[1], SHIRT_LIGHT if dx >= 0 else SHIRT_DARK)

    # -------------------------------------------------------------------------
    # HEAD, HAIR, FACE (All 8 Directions Distinct!)
    # -------------------------------------------------------------------------
    hx = cx - 6
    hy = cy - 9
    hw = 12
    hh = 10

    # Head outline & base skin
    c.fill_rect(hx + 1, hy, hw - 2, hh, OUTLINE)
    c.fill_rect(hx, hy + 1, hw, hh - 2, OUTLINE)
    c.fill_rect(hx + 1, hy + 1, hw - 2, hh - 2, SKIN_MID)
    c.fill_rect(hx + 2, hy + 2, hw - 4, hh - 4, SKIN_LIGHT)

    # Hair & facial features per direction (all 8 directions!)
    if direction == "down":
        # Hair bangs
        c.fill_rect(hx + 1, hy + 1, hw - 2, 3, HAIR_MID)
        c.fill_rect(hx + 2, hy + 1, hw - 4, 2, HAIR_LIGHT)
        c.set_px(hx + 1, hy + 4, HAIR_DARK)
        c.set_px(hx + hw - 2, hy + 4, HAIR_DARK)
        # Eyes
        eye_h = 1 if blink else 2
        c.fill_rect(hx + 3, hy + 5, 2, eye_h, EYE_COLOR)
        c.fill_rect(hx + 7, hy + 5, 2, eye_h, EYE_COLOR)
        if not blink:
            c.set_px(hx + 3, hy + 5, EYE_WHITE)
            c.set_px(hx + 7, hy + 5, EYE_WHITE)
        # Rosy cheeks
        c.set_px(hx + 2, hy + 7, BLUSH)
        c.set_px(hx + 9, hy + 7, BLUSH)

    elif direction == "down_right":
        # 3/4 view facing SE
        c.fill_rect(hx + 1, hy + 1, hw - 2, 3, HAIR_MID)
        c.fill_rect(hx + 1, hy + 2, 2, 5, HAIR_DARK)  # Left side hair lock
        eye_h = 1 if blink else 2
        c.fill_rect(hx + 5, hy + 5, 2, eye_h, EYE_COLOR)
        c.fill_rect(hx + 9, hy + 5, 1, eye_h, EYE_COLOR)
        if not blink:
            c.set_px(hx + 5, hy + 5, EYE_WHITE)
        c.set_px(hx + 4, hy + 7, BLUSH)
        c.set_px(hx + 10, hy + 7, BLUSH)

    elif direction == "down_left":
        # 3/4 view facing SW
        c.fill_rect(hx + 1, hy + 1, hw - 2, 3, HAIR_MID)
        c.fill_rect(hx + hw - 3, hy + 2, 2, 5, HAIR_DARK)  # Right side hair lock
        eye_h = 1 if blink else 2
        c.fill_rect(hx + 2, hy + 5, 1, eye_h, EYE_COLOR)
        c.fill_rect(hx + 5, hy + 5, 2, eye_h, EYE_COLOR)
        if not blink:
            c.set_px(hx + 6, hy + 5, EYE_WHITE)
        c.set_px(hx + 1, hy + 7, BLUSH)
        c.set_px(hx + 7, hy + 7, BLUSH)

    elif direction == "right":
        # Pure profile right (E)
        c.fill_rect(hx + 1, hy + 1, 5, hh - 2, HAIR_DARK)
        c.fill_rect(hx + 2, hy + 1, 5, 3, HAIR_MID)
        eye_h = 1 if blink else 2
        c.fill_rect(hx + 8, hy + 5, 2, eye_h, EYE_COLOR)
        if not blink:
            c.set_px(hx + 8, hy + 5, EYE_WHITE)
        c.set_px(hx + 7, hy + 7, BLUSH)

    elif direction == "left":
        # Pure profile left (W)
        c.fill_rect(hx + 6, hy + 1, 5, hh - 2, HAIR_DARK)
        c.fill_rect(hx + 5, hy + 1, 5, 3, HAIR_MID)
        eye_h = 1 if blink else 2
        c.fill_rect(hx + 2, hy + 5, 2, eye_h, EYE_COLOR)
        if not blink:
            c.set_px(hx + 3, hy + 5, EYE_WHITE)
        c.set_px(hx + 4, hy + 7, BLUSH)

    elif direction == "up":
        # Full back of head covered in layered hair (N)
        c.fill_rect(hx + 1, hy + 1, hw - 2, hh - 2, HAIR_DARK)
        c.fill_rect(hx + 2, hy + 1, hw - 4, hh - 3, HAIR_MID)
        c.fill_rect(hx + 3, hy + 2, hw - 6, 3, HAIR_LIGHT)

    elif direction == "up_right":
        # 3/4 back-right view (NE): mostly hair + right cheek/ear glimpse
        c.fill_rect(hx + 1, hy + 1, hw - 3, hh - 2, HAIR_DARK)
        c.fill_rect(hx + 2, hy + 1, hw - 4, hh - 3, HAIR_MID)
        c.fill_rect(hx + hw - 3, hy + 4, 2, 4, SKIN_MID)
        c.set_px(hx + hw - 2, hy + 5, EYE_COLOR)

    elif direction == "up_left":
        # 3/4 back-left view (NW): mostly hair + left cheek/ear glimpse
        c.fill_rect(hx + 2, hy + 1, hw - 3, hh - 2, HAIR_DARK)
        c.fill_rect(hx + 2, hy + 1, hw - 4, hh - 3, HAIR_MID)
        c.fill_rect(hx + 1, hy + 4, 2, 4, SKIN_MID)
        c.set_px(hx + 1, hy + 5, EYE_COLOR)

    # -------------------------------------------------------------------------
    # STRAW EXPLORER HAT (Adds strong silhouette & readability)
    # -------------------------------------------------------------------------
    hat_y = hy - 2
    # Brim
    c.fill_rect(hx - 2, hat_y + 2, hw + 4, 3, OUTLINE)
    c.fill_rect(hx - 1, hat_y + 3, hw + 2, 1, HAT_STRAW_MID)
    # Crown
    c.fill_rect(hx + 1, hat_y - 1, hw - 2, 4, OUTLINE)
    c.fill_rect(hx + 2, hat_y, hw - 4, 2, HAT_STRAW_LIGHT)
    c.fill_rect(hx + 2, hat_y + 2, hw - 4, 1, HAT_BAND)

    # -------------------------------------------------------------------------
    # TOOL / ACTION OVERLAYS (Axe, Pickaxe, Watering Can, Interact)
    # -------------------------------------------------------------------------
    # Compute aim vector based on 8-direction
    aim_x = dx
    aim_y = dy
    if aim_x == 0 and aim_y == 0:
        aim_y = 1

    if anim in ("axe", "pickaxe"):
        # Swing progress across frames 0..5
        if frame_idx in (0, 1):
            # Raised overhead
            tx = cx + aim_x * 2
            ty = cy - 10
            c.draw_line(cx + aim_x * 2, cy - 2, tx, ty, WOOD_DARK, 2)
            if anim == "axe":
                c.fill_rect(tx - 2, ty - 2, 5, 4, STEEL_LIGHT)
                c.fill_rect(tx - 1, ty - 1, 3, 2, STEEL_MID)
            else:
                c.draw_line(tx - 3, ty - 1, tx + 3, ty + 1, STEEL_LIGHT, 2)
        elif frame_idx in (2, 3, 4):
            # Extending toward target direction with motion arc
            reach = 7 if frame_idx == 2 else 9
            tx = cx + aim_x * reach
            ty = cy + 2 + aim_y * reach
            c.draw_line(cx + aim_x * 2, cy + 2, tx, ty, WOOD_LIGHT, 2)
            if anim == "axe":
                c.fill_rect(tx - 2, ty - 2, 5, 5, OUTLINE)
                c.fill_rect(tx - 1, ty - 1, 3, 3, STEEL_LIGHT)
            else:
                c.draw_line(tx - aim_y * 3, ty + aim_x * 3, tx + aim_y * 3, ty - aim_x * 3, STEEL_LIGHT, 2)

            # Swoosh arc & impact sparks
            if frame_idx in (2, 3):
                c.draw_line(cx + aim_x * 5 - aim_y * 4, cy - 3, tx, ty, SWOOSH_WHITE, 1)
                c.draw_line(cx + aim_x * 4 - aim_y * 3, cy - 2, tx, ty, SWOOSH_BLUE, 1)
            if frame_idx == 4:
                # Impact particles!
                for ox, oy in [(-2, -2), (2, -1), (-1, 2), (3, 1)]:
                    c.set_px(tx + ox, ty + oy, SPARK_GOLD if anim == "pickaxe" else WOOD_LIGHT)

    elif anim == "water":
        # Hold watering can in target direction and pour droplets
        wx = cx + aim_x * 6
        wy = cy + 2 + aim_y * 5
        c.fill_rect(wx - 3, wy - 2, 6, 5, OUTLINE)
        c.fill_rect(wx - 2, wy - 1, 4, 3, WATER_CAN_BLUE)
        c.fill_rect(wx - 2, wy + 1, 4, 1, WATER_CAN_DARK)
        # Spout
        spout_x = wx + aim_x * 3
        spout_y = wy + aim_y * 2
        c.draw_line(wx, wy, spout_x, spout_y, STEEL_MID, 1)
        # Animated water droplets on frames 1..4
        if frame_idx in (1, 2, 3, 4):
            drop_offset = frame_idx - 1
            for d_i in range(3):
                drop_x = spout_x + aim_x * (2 + d_i) + (d_i - 1)
                drop_y = spout_y + aim_y * 2 + ((drop_offset + d_i) % 3) + 1
                c.set_px(drop_x, drop_y, WATER_DROP_LIGHT)
                c.set_px(drop_x, drop_y + 1, WATER_DROP_MID)

    elif anim == "interact":
        # Sparkle / heart / exclamation above head
        if frame_idx in (1, 2):
            c.set_px(cx - 5, hy - 4, SPARK_GOLD)
            c.set_px(cx + 5, hy - 4, SPARK_GOLD)
            c.set_px(cx, hy - 6, SPARK_GOLD)

    return c


def generate_player_spritesheet() -> None:
    cols = 6
    rows = len(ANIMATIONS) * len(DIRECTIONS)  # 7 * 8 = 56 rows
    sheet = Canvas(cols * 32, rows * 32)

    row_idx = 0
    for anim_name, frame_count in ANIMATIONS:
        for dir_name in DIRECTIONS:
            for col_idx in range(cols):
                effective_frame = col_idx % frame_count
                frame_canvas = draw_character_frame(dir_name, anim_name, effective_frame, frame_count)
                sheet.blit(frame_canvas, col_idx * 32, row_idx * 32)
            row_idx += 1

    sheet.save_png("assets/sprites/player_spritesheet.png")
    print(f"Generated assets/sprites/player_spritesheet.png ({sheet.width}x{sheet.height}, {rows} rows x {cols} cols)")

    # Also generate a compact 8-directions x 7-animations showcase sheet (2x pixel scale = 512x448)
    showcase = Canvas(len(DIRECTIONS) * 64, len(ANIMATIONS) * 64, (32, 38, 48, 255))
    for a_idx, (anim_name, frame_count) in enumerate(ANIMATIONS):
        # Pick the most expressive action frame for each animation row
        sample_frame = 2 if anim_name in ("axe", "pickaxe", "water") else (1 if anim_name != "idle" else 0)
        for d_idx, dir_name in enumerate(DIRECTIONS):
            cell_bg = (42, 50, 64, 255) if (a_idx + d_idx) % 2 == 0 else (34, 40, 52, 255)
            showcase.fill_rect(d_idx * 64 + 1, a_idx * 64 + 1, 62, 62, cell_bg)
            fc = draw_character_frame(dir_name, anim_name, sample_frame, frame_count)
            for py in range(32):
                for px in range(32):
                    col = fc.get_px(px, py)
                    if col[3] > 0:
                        showcase.fill_rect(d_idx * 64 + px * 2, a_idx * 64 + py * 2, 2, 2, col)
    showcase.save_png("assets/sprites/player_8dir_showcase.png")
    print(f"Generated assets/sprites/player_8dir_showcase.png ({showcase.width}x{showcase.height})")


# =============================================================================
# 2. WORLD TILESET GENERATOR (16x16 Tiles, 16 cols x 5 rows = 256x80)
# =============================================================================
def generate_world_tileset() -> None:
    cols, rows = 16, 5
    atlas = Canvas(cols * 16, rows * 16)
    rng = random.Random(42)

    def draw_tile(col: int, row: int, base_color: RGBA, noise_colors: List[RGBA], density: float = 0.18) -> Canvas:
        t = Canvas(16, 16, base_color)
        for y in range(16):
            for x in range(16):
                if rng.random() < density:
                    t.set_px(x, y, rng.choice(noise_colors))
        atlas.blit(t, col * 16, row * 16)
        return t

    # -------------------------------------------------------------------------
    # ROW 0: Water tiles
    # Cols 0..3: Deep Water (variants/frames)
    # Cols 4..7: Shallow Lake Water (variants/frames)
    # Cols 8..11: River Water with directional flow ripples
    # Cols 12..15: Water Lilypads & Reeds on water
    # -------------------------------------------------------------------------
    DEEP_WATER = (36, 92, 168, 255)
    DEEP_SHADE = [(30, 78, 148, 255), (46, 108, 188, 255)]
    SHALLOW_WATER = (58, 138, 208, 255)
    SHALLOW_SHADE = [(48, 122, 192, 255), (78, 158, 224, 255), (125, 195, 242, 255)]
    RIVER_WATER = (50, 126, 198, 255)

    for i in range(4):
        t = draw_tile(i, 0, DEEP_WATER, DEEP_SHADE, 0.22)
        # Wave highlight
        wx = (i * 4 + 2) % 12
        t.draw_line(wx, 5 + (i % 2), wx + 3, 5 + (i % 2), (82, 148, 218, 255))
        t.draw_line((wx + 6) % 12, 11, (wx + 6) % 12 + 3, 11, (82, 148, 218, 255))
        atlas.blit(t, i * 16, 0)

    for i in range(4):
        t = draw_tile(4 + i, 0, SHALLOW_WATER, SHALLOW_SHADE, 0.20)
        wx = (i * 3 + 3) % 11
        t.draw_line(wx, 4, wx + 4, 4, (150, 215, 250, 255))
        t.draw_line((wx + 5) % 11, 12, (wx + 5) % 11 + 3, 12, (150, 215, 250, 255))
        atlas.blit(t, (4 + i) * 16, 0)

    for i in range(4):
        t = draw_tile(8 + i, 0, RIVER_WATER, SHALLOW_SHADE, 0.20)
        # River current foam streaks
        for ry in (3, 8, 13):
            sx = (i * 3 + ry) % 10
            t.draw_line(sx, ry, sx + 4, ry, (185, 232, 255, 255))
        atlas.blit(t, (8 + i) * 16, 0)

    for i in range(4):
        t = draw_tile(12 + i, 0, SHALLOW_WATER, SHALLOW_SHADE, 0.15)
        # Green lilypad with notch and small lotus flower
        t.fill_ellipse(8, 8, 4.5, 3.5, (56, 148, 72, 255))
        t.fill_ellipse(7.5, 7.5, 3.2, 2.4, (82, 178, 92, 255))
        t.set_px(11, 8, SHALLOW_WATER)
        if i % 2 == 0:
            t.fill_rect(7, 6, 3, 2, (248, 152, 184, 255))
            t.set_px(8, 6, (255, 230, 110, 255))
        atlas.blit(t, (12 + i) * 16, 0)

    # -------------------------------------------------------------------------
    # ROW 1: Ground Terrain
    # Cols 0..3: Sand / Shoreline
    # Cols 4..7: Meadow Grass
    # Cols 8..11: Forest Moss / Rich Dark Grass
    # Cols 12..15: Dirt Trail / Path
    # -------------------------------------------------------------------------
    SAND_BASE = (232, 204, 142, 255)
    SAND_SHADE = [(216, 184, 122, 255), (244, 220, 164, 255), (194, 162, 104, 255)]
    GRASS_BASE = (94, 174, 82, 255)
    GRASS_SHADE = [(78, 154, 68, 255), (114, 192, 96, 255), (66, 138, 58, 255)]
    FOREST_BASE = (64, 138, 68, 255)
    FOREST_SHADE = [(52, 118, 56, 255), (82, 158, 82, 255), (44, 102, 48, 255)]
    DIRT_BASE = (176, 132, 88, 255)
    DIRT_SHADE = [(156, 114, 72, 255), (194, 150, 104, 255), (138, 98, 60, 255)]

    for i in range(4):
        t = draw_tile(i, 1, SAND_BASE, SAND_SHADE, 0.25)
        # Small shell / pebble detail
        if i == 2:
            t.fill_rect(5, 9, 2, 2, (250, 238, 215, 255))
        atlas.blit(t, i * 16, 16)

    for i in range(4):
        t = draw_tile(4 + i, 1, GRASS_BASE, GRASS_SHADE, 0.25)
        # Grass blades
        bx, by = 3 + i * 2, 5 + (i % 3) * 3
        t.set_px(bx, by, (132, 208, 106, 255))
        t.set_px(bx + 1, by - 1, (132, 208, 106, 255))
        t.set_px(bx + 2, by, (70, 144, 60, 255))
        atlas.blit(t, (4 + i) * 16, 16)

    for i in range(4):
        t = draw_tile(8 + i, 1, FOREST_BASE, FOREST_SHADE, 0.28)
        # Moss / clover patch
        mx, my = 4 + (i * 3) % 8, 4 + (i * 2) % 8
        t.fill_rect(mx, my, 2, 2, (98, 178, 92, 255))
        atlas.blit(t, (8 + i) * 16, 16)

    for i in range(4):
        t = draw_tile(12 + i, 1, DIRT_BASE, DIRT_SHADE, 0.26)
        atlas.blit(t, (12 + i) * 16, 16)

    # -------------------------------------------------------------------------
    # ROW 2: Bridges & Watered Soil & Cobblestone
    # Cols 0..3: Wooden Bridge Horizontal & Vertical planks
    # Cols 4..7: Watered Rich Grass / Wet Soil (when player uses watering can)
    # Cols 8..11: Stone Stepping Path
    # Cols 12..15: Shoreline Foam Overlays (N, S, E, W)
    # -------------------------------------------------------------------------
    for i in range(4):
        t = Canvas(16, 16, SHALLOW_WATER)
        if i < 2:
            # Horizontal bridge planks
            t.fill_rect(0, 1, 16, 14, OUTLINE)
            for px in range(0, 16, 4):
                t.fill_rect(px, 2, 3, 12, WOOD_LIGHT if (px // 4) % 2 == 0 else WOOD_DARK)
                t.set_px(px + 1, 3, OUTLINE)
                t.set_px(px + 1, 12, OUTLINE)
            # Rails
            t.fill_rect(0, 1, 16, 2, (212, 158, 98, 255))
            t.fill_rect(0, 13, 16, 2, (142, 92, 50, 255))
        else:
            # Vertical bridge planks
            t.fill_rect(1, 0, 14, 16, OUTLINE)
            for py in range(0, 16, 4):
                t.fill_rect(2, py, 12, 3, WOOD_LIGHT if (py // 4) % 2 == 0 else WOOD_DARK)
                t.set_px(3, py + 1, OUTLINE)
                t.set_px(12, py + 1, OUTLINE)
            t.fill_rect(1, 0, 2, 16, (212, 158, 98, 255))
            t.fill_rect(13, 0, 2, 16, (142, 92, 50, 255))
        atlas.blit(t, i * 16, 32)

    for i in range(4):
        # Watered lush soil/grass with dewdrops
        t = draw_tile(4 + i, 2, (52, 128, 78, 255), [(42, 108, 66, 255), (68, 152, 96, 255)], 0.25)
        t.set_px(4 + i * 2, 5, WATER_DROP_LIGHT)
        t.set_px(11 - i * 2, 11, WATER_DROP_LIGHT)
        atlas.blit(t, (4 + i) * 16, 32)

    for i in range(4):
        # Cobblestone / stepping stones on grass
        t = draw_tile(8 + i, 2, GRASS_BASE, GRASS_SHADE, 0.20)
        t.fill_ellipse(5, 5, 3.5, 2.8, STEEL_DARK)
        t.fill_ellipse(4.8, 4.6, 2.6, 2.0, STEEL_MID)
        t.fill_ellipse(11, 11, 3.5, 2.8, STEEL_DARK)
        t.fill_ellipse(10.8, 10.6, 2.6, 2.0, STEEL_MID)
        atlas.blit(t, (8 + i) * 16, 32)

    for i in range(4):
        # Shoreline water-to-sand foam edges (N, S, W, E)
        t = draw_tile(12 + i, 2, SHALLOW_WATER, SHALLOW_SHADE, 0.18)
        if i == 0:  # North shore
            t.fill_rect(0, 0, 16, 5, SAND_BASE)
            t.fill_rect(0, 5, 16, 2, (215, 245, 255, 255))
        elif i == 1:  # South shore
            t.fill_rect(0, 11, 16, 5, SAND_BASE)
            t.fill_rect(0, 9, 16, 2, (215, 245, 255, 255))
        elif i == 2:  # West shore
            t.fill_rect(0, 0, 5, 16, SAND_BASE)
            t.fill_rect(5, 0, 2, 16, (215, 245, 255, 255))
        else:  # East shore
            t.fill_rect(11, 0, 5, 16, SAND_BASE)
            t.fill_rect(9, 0, 2, 16, (215, 245, 255, 255))
        atlas.blit(t, (12 + i) * 16, 32)

    # -------------------------------------------------------------------------
    # ROW 3: Decor Overlay Tiles (Transparent background!)
    # Cols 0..3: Flowers (Red Poppy, Yellow Dandelion, Bluebell, White Daisy)
    # Cols 4..7: Tall Grass Tufts (4 variants)
    # Cols 8..11: Forest Mushrooms & Fallen Leaves
    # Cols 12..15: Small Pebbles & Shells
    # -------------------------------------------------------------------------
    flower_colors = [
        ((235, 65, 65, 255), (255, 215, 70, 255)),   # Red poppy
        ((250, 215, 55, 255), (235, 145, 35, 255)),  # Yellow dandelion
        ((95, 165, 245, 255), (245, 245, 255, 255)), # Bluebell
        ((250, 250, 252, 255), (250, 205, 65, 255)), # White daisy
    ]
    for i, (petal, center) in enumerate(flower_colors):
        t = Canvas(16, 16)
        for fx, fy in [(5, 6), (11, 10), (4, 12)]:
            # Stem & leaves
            t.fill_rect(fx, fy + 1, 1, 3, (52, 128, 52, 255))
            t.set_px(fx - 1, fy + 2, (74, 158, 68, 255))
            # Petals
            t.set_px(fx - 1, fy, petal)
            t.set_px(fx + 1, fy, petal)
            t.set_px(fx, fy - 1, petal)
            t.set_px(fx, fy + 1, petal)
            t.set_px(fx, fy, center)
        atlas.blit(t, i * 16, 48)

    for i in range(4):
        t = Canvas(16, 16)
        for gx, gy in [(4, 12), (8, 10), (12, 13)]:
            t.draw_line(gx, gy, gx - 2, gy - 4, (58, 138, 56, 255))
            t.draw_line(gx + 1, gy, gx + 1, gy - 5, (86, 174, 76, 255))
            t.draw_line(gx + 2, gy, gx + 4, gy - 4, (116, 198, 96, 255))
        atlas.blit(t, (4 + i) * 16, 48)

    for i in range(4):
        t = Canvas(16, 16)
        # Cute red/spotted forest mushrooms
        for mx, my in [(5, 9), (11, 12)]:
            t.fill_rect(mx, my, 2, 3, (242, 232, 212, 255))
            t.fill_ellipse(mx + 0.5, my - 0.5, 3.0, 2.0, (218, 56, 52, 255))
            t.set_px(mx, my - 1, (255, 250, 240, 255))
            t.set_px(mx + 2, my - 1, (255, 250, 240, 255))
        atlas.blit(t, (8 + i) * 16, 48)

    for i in range(4):
        t = Canvas(16, 16)
        t.fill_ellipse(6, 10, 2.2, 1.5, STEEL_MID)
        t.set_px(5, 9, STEEL_LIGHT)
        t.fill_ellipse(11, 7, 1.8, 1.2, STEEL_DARK)
        atlas.blit(t, (12 + i) * 16, 48)

    # -------------------------------------------------------------------------
    # ROW 4: Extra Biome Tiles (Flower Meadow, Sandy Grass, Mossy Rock Ground)
    # -------------------------------------------------------------------------
    for i in range(16):
        t = draw_tile(i, 4, GRASS_BASE, GRASS_SHADE, 0.22)
        atlas.blit(t, i * 16, 64)

    atlas.save_png("assets/tilesets/world_tileset.png")
    print(f"Generated assets/tilesets/world_tileset.png ({atlas.width}x{atlas.height})")


# =============================================================================
# 3. WORLD COLLIDABLE OBJECTS (Trees, Bushes, Rocks, Stumps, Logs)
# =============================================================================
def generate_world_objects() -> None:
    # 1. Oak Tree (32x48) - Clustered pixel-art foliage
    oak = Canvas(32, 48)
    oak.fill_ellipse(16, 44, 10, 3.5, SHADOW_ALPHA)
    # Trunk & roots
    oak.fill_rect(12, 28, 8, 16, OUTLINE)
    oak.fill_rect(13, 29, 6, 14, WOOD_DARK)
    oak.fill_rect(14, 29, 3, 14, WOOD_LIGHT)
    oak.fill_rect(10, 41, 12, 3, OUTLINE)
    oak.fill_rect(11, 41, 10, 2, WOOD_DARK)
    # Multi-cluster canopy outlines
    clusters = [(10, 20, 7, 7), (22, 20, 7, 7), (16, 12, 9, 8), (16, 21, 10, 7)]
    for cx, cy, rx, ry in clusters:
        oak.fill_ellipse(cx, cy, rx + 1.2, ry + 1.2, OUTLINE)
    for cx, cy, rx, ry in clusters:
        oak.fill_ellipse(cx, cy, rx, ry, (42, 106, 52, 255))
        oak.fill_ellipse(cx - 0.5, cy - 1.0, rx * 0.82, ry * 0.82, (64, 142, 68, 255))
        oak.fill_ellipse(cx - 1.0, cy - 2.0, rx * 0.58, ry * 0.58, (92, 178, 86, 255))
    oak.fill_ellipse(13, 9, 4.5, 3.5, (132, 208, 106, 255))
    oak.save_png("assets/objects/tree_oak.png")

    # 2. Pine Tree (32x48)
    pine = Canvas(32, 48)
    pine.fill_ellipse(16, 44, 9, 3.2, SHADOW_ALPHA)
    pine.fill_rect(13, 33, 6, 11, OUTLINE)
    pine.fill_rect(14, 34, 4, 9, WOOD_DARK)
    # 3 triangular pine tiers
    tiers = [(34, 13, 13), (24, 11, 12), (14, 8, 11)]
    for base_y, half_w, height in tiers:
        for y in range(height):
            t = y / float(max(1, height - 1))
            w = max(1, int(round(half_w * t)))
            py = base_y - height + y
            pine.fill_rect(16 - w - 1, py, w * 2 + 2, 2, OUTLINE)
            col = (36, 94, 62, 255) if y > height * 0.65 else ((52, 126, 78, 255) if y > height * 0.3 else (78, 158, 96, 255))
            pine.fill_rect(16 - w, py, w * 2, 1, col)
    pine.save_png("assets/objects/tree_pine.png")

    # 3. Birch Tree (32x48)
    birch = Canvas(32, 48)
    birch.fill_ellipse(16, 44, 9, 3.0, SHADOW_ALPHA)
    birch.fill_rect(13, 26, 6, 18, OUTLINE)
    birch.fill_rect(14, 27, 4, 16, (238, 234, 226, 255))
    for by in (30, 34, 38, 41):
        birch.fill_rect(14, by, 2, 1, (62, 58, 56, 255))
    b_clusters = [(11, 19, 6.5, 6.5), (21, 19, 6.5, 6.5), (16, 12, 8.5, 7.5), (16, 20, 8.5, 6.5)]
    for cx, cy, rx, ry in b_clusters:
        birch.fill_ellipse(cx, cy, rx + 1.2, ry + 1.2, OUTLINE)
    for cx, cy, rx, ry in b_clusters:
        birch.fill_ellipse(cx, cy, rx, ry, (118, 168, 64, 255))
        birch.fill_ellipse(cx - 0.5, cy - 1.0, rx * 0.78, ry * 0.78, (158, 202, 78, 255))
    birch.fill_ellipse(14, 10, 5, 4, (198, 228, 104, 255))
    birch.save_png("assets/objects/tree_birch.png")

    # 4. Tree Stump (16x16)
    stump = Canvas(16, 16)
    stump.fill_ellipse(8, 13, 6, 2.2, SHADOW_ALPHA)
    stump.fill_rect(4, 6, 8, 7, OUTLINE)
    stump.fill_rect(5, 7, 6, 5, WOOD_DARK)
    stump.fill_ellipse(8, 6, 4, 2, (226, 184, 128, 255))
    stump.set_px(8, 6, WOOD_DARK)
    stump.save_png("assets/objects/tree_stump.png")

    # 5. Berry Bush (16x16)
    bush = Canvas(16, 16)
    bush.fill_ellipse(8, 13, 6.5, 2.2, SHADOW_ALPHA)
    bush.fill_ellipse(8, 8, 6.5, 5.5, OUTLINE)
    bush.fill_ellipse(8, 8, 5.5, 4.5, (48, 122, 58, 255))
    bush.fill_ellipse(7, 7, 4.2, 3.4, (78, 162, 76, 255))
    for bx, by in [(5, 7), (9, 6), (11, 9), (6, 10)]:
        bush.set_px(bx, by, (228, 54, 64, 255))
        bush.set_px(bx, by - 1, (255, 140, 150, 255))
    bush.save_png("assets/objects/bush_berry.png")

    # 6. Large Mossy Boulder (32x32)
    boulder = Canvas(32, 32)
    boulder.fill_ellipse(16, 27, 11, 3.5, SHADOW_ALPHA)
    boulder.fill_ellipse(16, 18, 12, 9, OUTLINE)
    boulder.fill_ellipse(16, 18, 11, 8, STEEL_DARK)
    boulder.fill_ellipse(15, 16, 9, 6.5, STEEL_MID)
    boulder.fill_ellipse(13, 14, 5, 3.5, STEEL_LIGHT)
    # Moss cap on top
    boulder.fill_ellipse(17, 12, 6, 2.5, (76, 158, 74, 255))
    boulder.save_png("assets/objects/rock_large.png")

    # 7. Small Mineable Rock (16x16)
    rock = Canvas(16, 16)
    rock.fill_ellipse(8, 13, 6, 2, SHADOW_ALPHA)
    rock.fill_ellipse(8, 9, 6, 4.5, OUTLINE)
    rock.fill_ellipse(8, 9, 5, 3.5, STEEL_DARK)
    rock.fill_ellipse(7, 8, 3.5, 2.5, STEEL_MID)
    rock.fill_rect(5, 6, 3, 2, STEEL_LIGHT)
    rock.save_png("assets/objects/rock_small.png")

    # 8. Copper/Gold Ore Rock (16x16)
    ore = Canvas(16, 16)
    ore.blit(rock, 0, 0)
    for ox, oy in [(6, 8), (10, 7), (8, 10), (5, 10)]:
        ore.fill_rect(ox, oy, 2, 2, (242, 168, 58, 255))
        ore.set_px(ox, oy, (255, 232, 120, 255))
    ore.save_png("assets/objects/rock_ore.png")

    # 9. Fallen Forest Log (32x16)
    log = Canvas(32, 16)
    log.fill_ellipse(16, 13, 13, 2.5, SHADOW_ALPHA)
    log.fill_rect(3, 5, 26, 8, OUTLINE)
    log.fill_rect(4, 6, 24, 6, WOOD_DARK)
    log.fill_rect(4, 6, 24, 2, WOOD_LIGHT)
    log.fill_ellipse(4, 9, 2, 3, (226, 184, 128, 255))
    log.fill_ellipse(14, 6, 5, 1.5, (78, 162, 76, 255))
    log.save_png("assets/objects/log_fallen.png")

    print("Generated world object sprites in assets/objects/")


# =============================================================================
# 4. UI TOOL ICONS & PROJECT ICON
# =============================================================================
def generate_ui_and_icons() -> None:
    # Axe Icon (16x16)
    axe = Canvas(16, 16)
    axe.draw_line(3, 13, 12, 4, OUTLINE, 3)
    axe.draw_line(3, 13, 12, 4, WOOD_LIGHT, 1)
    axe.fill_rect(8, 2, 6, 6, OUTLINE)
    axe.fill_rect(9, 3, 4, 4, STEEL_MID)
    axe.fill_rect(11, 3, 2, 4, STEEL_LIGHT)
    axe.save_png("assets/ui/icon_axe.png")

    # Pickaxe Icon (16x16)
    pick = Canvas(16, 16)
    pick.draw_line(3, 13, 12, 4, OUTLINE, 3)
    pick.draw_line(3, 13, 12, 4, WOOD_LIGHT, 1)
    pick.draw_line(7, 2, 14, 9, OUTLINE, 3)
    pick.draw_line(7, 2, 14, 9, STEEL_LIGHT, 1)
    pick.save_png("assets/ui/icon_pickaxe.png")

    # Watering Can Icon (16x16)
    water = Canvas(16, 16)
    water.fill_rect(4, 6, 8, 7, OUTLINE)
    water.fill_rect(5, 7, 6, 5, WATER_CAN_BLUE)
    water.fill_rect(3, 4, 4, 3, OUTLINE)
    water.fill_rect(4, 5, 2, 2, WATER_CAN_DARK)
    water.draw_line(11, 9, 14, 6, OUTLINE, 3)
    water.draw_line(11, 9, 14, 6, STEEL_LIGHT, 1)
    water.save_png("assets/ui/icon_water.png")

    # Hand / Interact Icon (16x16)
    hand = Canvas(16, 16)
    hand.fill_ellipse(8, 9, 5, 5, OUTLINE)
    hand.fill_ellipse(8, 9, 4, 4, SKIN_LIGHT)
    hand.fill_rect(5, 4, 6, 4, SKIN_MID)
    hand.save_png("assets/ui/icon_hand.png")

    # Project Icon (64x64) - 2x scaled character on lush island
    icon = Canvas(64, 64, (50, 126, 198, 255))
    icon.fill_ellipse(32, 46, 26, 12, (232, 204, 142, 255))
    icon.fill_ellipse(32, 45, 23, 10, (94, 174, 82, 255))
    char_frame = draw_character_frame("down_right", "walk", 1, 6)
    for y in range(32):
        for x in range(32):
            px = char_frame.get_px(x, y)
            if px[3] > 0:
                icon.fill_rect(x * 2, y * 2 - 4, 2, 2, px)
    icon.save_png("icon.png")
    print("Generated UI icons in assets/ui/ and icon.png")


if __name__ == "__main__":
    generate_player_spritesheet()
    generate_world_tileset()
    generate_world_objects()
    generate_ui_and_icons()
    print("All pixel-art assets generated successfully!")
