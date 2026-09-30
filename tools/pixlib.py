"""
pixlib.py -- tiny pixel-art toolkit used by the STARDW asset generator.

Everything in assets/ of this project is drawn by this library at runtime of the
generator (no external art is used). Drawings are produced at a supersampled
resolution and then reduced + snapped to a palette, which gives crisp,
consistently shaded pixel art.
"""

import math
import random

from PIL import Image, ImageDraw, ImageFilter

try:
    import numpy as np
except Exception:  # pragma: no cover - numpy comes with matplotlib/pillow usage
    np = None


# --------------------------------------------------------------------------- #
# colour helpers
# --------------------------------------------------------------------------- #
def rgb(r, g, b, a=255):
    return (int(r), int(g), int(b), int(a))


def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(4))


def shade(c, f):
    return (
        max(0, min(255, int(c[0] * f))),
        max(0, min(255, int(c[1] * f))),
        max(0, min(255, int(c[2] * f))),
        c[3],
    )


def lighten(c, amt):
    return mix(c, (255, 255, 255, c[3]), amt)


def darken(c, amt):
    return mix(c, (0, 0, 0, c[3]), amt)


def with_alpha(c, a):
    return (c[0], c[1], c[2], int(a))


def hexcol(h):
    h = h.lstrip("#")
    return rgb(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


# --------------------------------------------------------------------------- #
# drawing surface
# --------------------------------------------------------------------------- #
class Art:
    """Supersampled drawing surface that reduces to a pixel-art bitmap."""

    def __init__(self, w, h, ss=2):
        self.w, self.h, self.ss = int(w), int(h), int(ss)
        self.img = Image.new("RGBA", (self.w * ss, self.h * ss), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    # -- primitive wrappers (coordinates are in target pixels) -------------- #
    def _b(self, v):
        return v * self.ss

    @staticmethod
    def _alpha(fill):
        if fill is None:
            return 255
        return fill[3] if len(fill) > 3 else 255

    def _draw(self, fn, blend=None):
        """Run fn(drawer). When blend alpha < 255, draw into a layer and
        alpha-composite so translucent shapes blend instead of overwrite."""
        a = 255 if blend is None else blend
        if a >= 255:
            fn(self.d)
            return
        layer = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        fn(ImageDraw.Draw(layer))
        self.img = Image.alpha_composite(self.img, layer)
        self.d = ImageDraw.Draw(self.img)

    def rect(self, x0, y0, x1, y1, fill, outline=None, width=1):
        if fill is not None and self._alpha(fill) < 255:
            self._draw(lambda d: d.rectangle([self._b(x0), self._b(y0), self._b(x1), self._b(y1)], fill=fill),
                       blend=self._alpha(fill))
            if outline:
                self.d.rectangle([self._b(x0), self._b(y0), self._b(x1), self._b(y1)], outline=outline,
                                 width=int(width * self.ss))
            return
        self.d.rectangle(
            [self._b(x0), self._b(y0), self._b(x1), self._b(y1)],
            fill=fill,
            outline=outline,
            width=int(width * self.ss),
        )

    def ellipse(self, x0, y0, x1, y1, fill, outline=None, width=1):
        if fill is not None and self._alpha(fill) < 255:
            self._draw(lambda d: d.ellipse([self._b(x0), self._b(y0), self._b(x1), self._b(y1)], fill=fill),
                       blend=self._alpha(fill))
            if outline:
                self.d.ellipse([self._b(x0), self._b(y0), self._b(x1), self._b(y1)], outline=outline,
                               width=int(width * self.ss))
            return
        self.d.ellipse(
            [self._b(x0), self._b(y0), self._b(x1), self._b(y1)],
            fill=fill,
            outline=outline,
            width=int(width * self.ss),
        )

    def poly(self, pts, fill, outline=None, width=1):
        p = [self._b(v) for pt in pts for v in pt]
        if fill is not None and self._alpha(fill) < 255:
            self._draw(lambda d: d.polygon(p, fill=fill), blend=self._alpha(fill))
        else:
            self.d.polygon(p, fill=fill, outline=outline)
        if outline and width > 1:
            self.d.line(p + [p[0], p[1]], fill=outline, width=int(width * self.ss), joint="curve")

    def line(self, pts, fill, width=1):
        p = [self._b(v) for pt in pts for v in pt]
        if self._alpha(fill) < 255:
            self._draw(lambda d: d.line(p, fill=fill, width=max(1, int(width * self.ss)), joint="curve"),
                       blend=self._alpha(fill))
            return
        self.d.line(p, fill=fill, width=max(1, int(width * self.ss)), joint="curve")

    def px(self, x, y, fill):
        x, y = int(x), int(y)
        if self._alpha(fill) < 255:
            self._draw(lambda d: d.rectangle([x * self.ss, y * self.ss, (x + 1) * self.ss - 1, (y + 1) * self.ss - 1],
                                             fill=fill), blend=self._alpha(fill))
            return
        self.d.rectangle([x * self.ss, y * self.ss, (x + 1) * self.ss - 1, (y + 1) * self.ss - 1], fill=fill)

    def disc(self, cx, cy, r, fill):
        self.ellipse(cx - r, cy - r, cx + r, cy + r, fill)

    def arc(self, box, start, end, fill, width=1):
        if self._alpha(fill) < 255:
            self._draw(lambda d: d.arc([self._b(box[0]), self._b(box[1]), self._b(box[2]), self._b(box[3])],
                                       start=start, end=end, fill=fill, width=max(1, int(width * self.ss))),
                       blend=self._alpha(fill))
            return
        self.d.arc(
            [self._b(box[0]), self._b(box[1]), self._b(box[2]), self._b(box[3])],
            start=start,
            end=end,
            fill=fill,
            width=max(1, int(width * self.ss)),
        )

    def blur(self, radius):
        self.img = self.img.filter(ImageFilter.GaussianRadius(radius) if False else ImageFilter.GaussianBlur(radius))
        self.d = ImageDraw.Draw(self.img)

    def paste(self, img, x, y, mask=None):
        self.img.paste(img.resize((img.width * self.ss, img.height * self.ss), Image.NEAREST) if img.width != img.width * self.ss else img,
                       (int(x * self.ss), int(y * self.ss)), mask)

    # -- reduce -------------------------------------------------------------- #
    def reduce(self, palette=None, threshold=110, keep_alpha=False):
        im = self.img.resize((self.w, self.h), Image.BOX)
        if palette is None:
            return im.convert("RGBA")
        arr = np.asarray(im.convert("RGBA")).astype(np.int32)
        alpha = arr[..., 3]
        pal = np.array([list(c[:3]) for c in palette], dtype=np.int32)
        flat = arr[..., :3].reshape(-1, 3)
        # nearest palette colour for every pixel (vectorised)
        d = ((flat[:, None, :] - pal[None, :, :]) ** 2).sum(axis=2)
        idx = d.argmin(axis=1)
        out = pal[idx].reshape(self.h, self.w, 3)
        res = np.dstack([out, np.where(alpha >= threshold, 255, 0).astype(np.uint8)])
        if keep_alpha:
            res[..., 3] = np.where(alpha >= threshold, np.clip(alpha, 0, 255), 0)
        return Image.fromarray(res.astype(np.uint8), "RGBA")

    # -- masking helpers (used by the fish painter) ------------------------- #
    def alpha_mask(self, threshold=1):
        return np.asarray(self.img)[..., 3] > threshold

    def keep_only(self, mask):
        arr = np.asarray(self.img).copy()
        arr[..., 3] = np.where(mask, arr[..., 3], 0)
        self.img = Image.fromarray(arr, "RGBA")
        self.d = ImageDraw.Draw(self.img)
        return self

    def overlay(self, other):
        self.img = Image.alpha_composite(self.img, other.img)
        self.d = ImageDraw.Draw(self.img)
        return self

    def crop_pad(self, tw, th, anchor="bottom"):
        """Place the drawing into a tw x th transparent canvas."""
        out = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        y = th - self.h if anchor == "bottom" else 0
        out.paste(self.img.resize((self.w, self.h), Image.BOX), (0, y), self.img)
        return out


# --------------------------------------------------------------------------- #
# texture atlas
# --------------------------------------------------------------------------- #
class Atlas:
    """Very small shelf packer; records regions for manifest.json."""

    def __init__(self, name, width=1024, pad=2):
        self.name = name
        self.width = width
        self.pad = pad
        self.regions = {}
        self.rows = []          # list of (y, height, x_cursor)
        self.height = 0

    def add(self, key, img, fps=None):
        w, h = img.size
        placed = False
        for i, (y, rh, xc) in enumerate(self.rows):
            if h <= rh and xc + w <= self.width:
                self._put(key, img, xc, y, fps)
                self.rows[i] = (y, rh, xc + w + self.pad)
                placed = True
                break
        if not placed:
            y = self.height
            self._put(key, img, 0, y, fps)
            self.rows.append((y, h, w + self.pad))
            self.height = y + h + self.pad
        return self.regions[key]

    def _put(self, key, img, x, y, fps):
        w, h = img.size
        self._pending = getattr(self, "_pending", [])
        self._pending.append((key, img, x, y, fps))
        self.regions[key] = [x, y, w, h] + ([fps] if fps else [])

    def save(self, path):
        h = max(8, self.height)
        canvas = Image.new("RGBA", (self.width, h), (0, 0, 0, 0))
        for key, img, x, y, fps in getattr(self, "_pending", []):
            canvas.paste(img, (x, y), img)
        canvas.save(path)
        return {"file": self.name + ".png", "size": [self.width, h], "regions": self.regions}


# --------------------------------------------------------------------------- #
# misc pixel helpers
# --------------------------------------------------------------------------- #
def dither_mask(w, h, chance=0.5, rng=None):
    rng = rng or random
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    for y in range(h):
        for x in range(w):
            if rng.random() < chance:
                d.point((x, y), 255)
    return m


def checker_dither(art, x0, y0, x1, y1, col, phase=0):
    for y in range(int(y0), int(y1)):
        for x in range(int(x0), int(x1)):
            if (x + y + phase) % 2 == 0:
                art.px(x, y, col)


def speckle(art, x0, y0, x1, y1, cols, count, rng=None, alpha=None):
    rng = rng or random
    for _ in range(count):
        x = rng.randint(int(x0), int(x1) - 1)
        y = rng.randint(int(y0), int(y1) - 1)
        c = rng.choice(cols)
        if alpha is not None:
            c = with_alpha(c, alpha)
        art.px(x, y, c)


def outline_image(img, col, alpha_edge=40):
    """Add a 1px dark outline around every opaque pixel."""
    w, h = img.size
    arr = np.asarray(img.convert("RGBA"))
    a = arr[..., 3]
    out = arr.copy()
    pad = np.zeros((h + 2, w + 2), dtype=a.dtype)
    pad[1:-1, 1:-1] = a
    near = (
        pad[0:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, 0:-2] | pad[1:-1, 2:]
        | pad[0:-2, 0:-2] | pad[0:-2, 2:] | pad[2:, 0:-2] | pad[2:, 2:]
    )
    mask = (near > alpha_edge) & (a <= alpha_edge)
    out[mask] = (col[0], col[1], col[2], 255)
    return Image.fromarray(out, "RGBA")


def iso_diamond(art, cx, cy, w, h, fill, outline=None):
    hw, hh = w / 2.0, h / 2.0
    pts = [(cx, cy - hh), (cx + hw, cy), (cx, cy + hh), (cx - hw, cy)]
    art.poly(pts, fill, outline=outline)


def gradient_band(art, y0, y1, col_a, col_b, x0=0, x1=None):
    x1 = art.w if x1 is None else x1
    span = max(1, (y1 - y0))
    for y in range(int(y0), int(y1)):
        c = mix(col_a, col_b, (y - y0) / span)
        art.rect(x0, y, x1, y + 1, c)
