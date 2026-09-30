"""Static project validator (no engine required).

Cross-checks that everything the GDScript references actually exists:
  * preload()/load() resource paths
  * Art.tex()/Art.frames()/Art.atlas() names in assets/manifest.json
  * DB fish ids have art in the fish atlas (and vice-versa)
  * item icon ids exist in the manifest
  * InputMap action names used are registered in art.gd
  * scene ext_resource script paths exist
  * project.godot autoload paths exist
  * every manifest rect fits inside its PNG

Run:  python3 tools/validate_project.py
"""

import json
import os
import re
import sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))

errors = []
warnings = []


def rel(p):
    return os.path.relpath(p, ROOT)


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def gd_files():
    out = []
    for base in ("scripts",):
        for root, _, files in os.walk(os.path.join(ROOT, base)):
            for f in files:
                if f.endswith(".gd"):
                    out.append(os.path.join(root, f))
    return out


manifest = json.load(open(os.path.join(ROOT, "assets", "manifest.json"), encoding="utf-8"))
region_names = set()
for at in manifest["atlases"]:
    region_names.update(manifest["atlases"][at]["regions"].keys())
anim_names = set(manifest["anims"].keys())
fish_art = set(manifest["atlases"]["fish"]["regions"].keys())

gdscripts = gd_files()
all_text = {rel(p): read(p) for p in gdscripts}

# ---------------------------------------------------------------- res paths
for name, text in all_text.items():
    for m in re.finditer(r'(?:preload|load)\(\s*"res://([^"]+)"', text):
        p = os.path.join(ROOT, m.group(1))
        if not os.path.exists(p):
            errors.append("%s: missing resource res://%s" % (name, m.group(1)))

# ------------------------------------------------------- Art.tex / frames
for name, text in all_text.items():
    for fn in ("tex", "frames", "atlas"):
        for m in re.finditer(r'Art\.' + fn + r'\(\s*"([^"%+]+)"', text):
            key = m.group(1)
            if fn == "frames":
                if key not in anim_names:
                    errors.append("%s: unknown animation '%s'" % (name, key))
            elif fn == "atlas":
                if key not in manifest["atlases"]:
                    errors.append("%s: unknown atlas '%s'" % (name, key))
            else:
                if key not in region_names:
                    errors.append("%s: unknown atlas region '%s'" % (name, key))

# dynamic region prefixes -- at least the concrete frames must exist
dyn_prefixes = ["bobber_%d", "walk_", "idle_", "cast_", "hold_", "reel_", "char_", "s_", "w_"]
for pre in ["walk_down", "idle_down", "cast_down", "hold_down", "reel_down",
            "walk_up", "walk_left", "walk_right", "bobber_0", "bobber_1",
            "s_spring", "s_winter", "w_sun", "w_snow", "campfire_0"]:
    if pre not in region_names and pre not in anim_names:
        errors.append("expected dynamic region/anim missing: %s" % pre)

# ------------------------------------------------------- DB fish <-> art
db_text = all_text["scripts/autoload/db.gd"]
db_fish = set(re.findall(r'"([a-z0-9_]+)":\s*\{[^}]*?"water"', db_text))
for f in db_fish:
    if f not in fish_art:
        errors.append("DB fish '%s' has no art in fish atlas" % f)
for f in fish_art:
    if f not in db_fish:
        warnings.append("fish art '%s' not in DB (unused)" % f)

# item icons referenced from hud/shop must exist
for name, text in all_text.items():
    for m in re.finditer(r'U\.icon\(\s*"([^"]+)"', text):
        if m.group(1) not in region_names:
            errors.append("%s: icon '%s' missing" % (name, m.group(1)))

# ------------------------------------------------------- input actions
registered = set(re.findall(r'_add\("([a-z_]+)"', all_text["scripts/autoload/art.gd"]))
for name, text in all_text.items():
    for m in re.finditer(r'is_action(?:_just)?_pressed\("([a-z_]+)"\)', text):
        a = m.group(1)
        if a not in registered and not a.startswith("ui_"):
            errors.append("%s: unregistered input action '%s'" % (name, a))

# ------------------------------------------------------- scenes
for root, _, files in os.walk(os.path.join(ROOT, "scenes")):
    for f in files:
        if f.endswith(".tscn"):
            t = read(os.path.join(root, f))
            for m in re.finditer(r'path="res://([^"]+)"', t):
                if not os.path.exists(os.path.join(ROOT, m.group(1))):
                    errors.append("%s: missing ext_resource %s" % (f, m.group(1)))

# ------------------------------------------------------- autoloads
proj = read(os.path.join(ROOT, "project.godot"))
for m in re.finditer(r'="\*res://([^"]+)"', proj):
    if not os.path.exists(os.path.join(ROOT, m.group(1))):
        errors.append("project.godot: missing autoload %s" % m.group(1))

# ------------------------------------------------------- manifest bounds
for at in manifest["atlases"]:
    png = os.path.join(ROOT, "assets", manifest["atlases"][at]["file"])
    with Image.open(png) as im:
        W, H = im.size
    for rn, r in manifest["atlases"][at]["regions"].items():
        if isinstance(r[0], list):
            continue
        x, y, w, h = r[0], r[1], r[2], r[3]
        if x < 0 or y < 0 or x + w > W or y + h > H:
            errors.append("atlas %s: region %s out of bounds" % (at, rn))

# ------------------------------------------------------- audio files
for a in ["cast", "splash", "reel", "bite", "catch", "coin", "ui", "error", "sleep",
          "upgrade", "step", "thunder", "page"]:
    if not os.path.exists(os.path.join(ROOT, "assets", "sfx", a + ".wav")):
        errors.append("missing sfx %s.wav" % a)
for a in ["day", "night", "rain"]:
    if not os.path.exists(os.path.join(ROOT, "assets", "music", a + ".wav")):
        errors.append("missing music %s.wav" % a)

print("=== VALIDATION ===")
for w in warnings:
    print("warn:", w)
if errors:
    print("ERRORS (%d):" % len(errors))
    for e in errors:
        print("  -", e)
    sys.exit(1)
print("OK -- %d scripts, %d regions, %d anims, %d fish, no missing references"
      % (len(gdscripts), len(region_names), len(anim_names), len(db_fish)))
