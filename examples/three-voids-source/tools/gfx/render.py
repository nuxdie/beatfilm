#!/usr/bin/env python3
"""Three Voids -- graphics renderer.

    tools/gfx/render.py <ID> [--dur SECONDS] [--set key=value ...] [--out FILE]
    tools/gfx/render.py all [-j N]         render every clip at its default duration
    tools/gfx/render.py contact            rebuild clips/gfx/contact.jpg
    tools/gfx/render.py list               IDs, default durations, tunable beats

Everything is headless: Chrome (--headless=new, via tools/gfx/dom.mjs) for the UI /
text scenes, PIL for camera moves (float-box Lanczos resampling, so moves are
sub-pixel exact), frames piped straight into ffmpeg.  No frame dumps on disk.
"""
import argparse, json, math, os, subprocess, sys, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = ROOT / "clips" / "gfx"
TMP = Path("/home/n/Games/three-voids-raw/tmp")
CACHE = TMP / "gfx-cache"
ART = ROOT / "Daniel Conway - Art Block_files"
FPS = 60
CHAT_BG = (26, 26, 26)

# est seconds from SHOTLIST.md; default duration = est * 1.4
EST = dict(CAM=10, HL=10, TRI=20, GRID=12, CHAT=10, U5m=8, C1=6, C2=13, C3=10, C4=30, C5=4, P1a=18, P1b=26, P1c=24, S4a_left=5, S4b_left=14,
           S4c_left=30, S4d=13, U5a=6, U5b=5, U5c=20, U5d=50, U6a=9, U6b=20, U6c=15, U6d=8,
           U6e=12, U6f=28, E1=42, E4=9, E5=6)
ALIAS = dict(S4a="S4a_left", S4b="S4b_left", S4c="S4c_left")
DOM = {"U5m", "C5", "P1a", "U5a", "U5b", "U5c", "U5d", "U6a", "U6b", "E4", "E5"}


def default_dur(i):
    return round(EST[i] * 1.4, 2)


# ------------------------------------------------------------------ easing
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ss(t, a, b):
    x = clamp((t - a) / (b - a))
    return x * x * (3 - 2 * x)


def sm(t, a, b):
    x = clamp((t - a) / (b - a))
    return x * x * x * (x * (x * 6 - 15) + 10)


def glide(t, T):
    """0 -> ~1 over T with a soft landing, then keeps creeping forever (so a trimmed
    tail never shows a move that has visibly died)."""
    return 0.92 * sm(t, 0, T) + 0.08 * t / T


def eased_time(t, ramp=2.0):
    """time with a soft start: speed ramps 0 -> 1 over `ramp` seconds."""
    return t * t / (2 * ramp) if t < ramp else t - ramp / 2


def lerp(a, b, x):
    return a + (b - a) * x


def cam_lerp(A, B, p):
    """interpolate (cx, cy, h); zoom is interpolated in log space."""
    return (lerp(A[0], B[0], p), lerp(A[1], B[1], p), math.exp(lerp(math.log(A[2]), math.log(B[2]), p)))


def cam_path(keys, u):
    """Catmull-Rom through [(u_i, (cx, cy, h))], C1-continuous; holds the end velocity past the last key."""
    us = [k[0] for k in keys]
    pts = [np.array([k[1][0], k[1][1], math.log(k[1][2])]) for k in keys]
    n = len(keys)
    tang = []
    for i in range(n):
        if i == 0:
            m = (pts[1] - pts[0]) / (us[1] - us[0]) * 0.6
        elif i == n - 1:
            m = (pts[-1] - pts[-2]) / (us[-1] - us[-2]) * 0.6
        else:
            m = (pts[i + 1] - pts[i - 1]) / (us[i + 1] - us[i - 1])
        tang.append(m)
    if u >= us[-1]:
        p = pts[-1] + tang[-1] * (u - us[-1])
    else:
        i = max(0, max(j for j in range(n - 1) if us[j] <= u or j == 0))
        d = us[i + 1] - us[i]
        s = clamp((u - us[i]) / d)
        h00, h10, h01, h11 = 2 * s**3 - 3 * s**2 + 1, s**3 - 2 * s**2 + s, -2 * s**3 + 3 * s**2, s**3 - s**2
        p = h00 * pts[i] + h10 * d * tang[i] + h01 * pts[i + 1] + h11 * d * tang[i + 1]
    return (p[0], p[1], math.exp(p[2]))


# ------------------------------------------------------------------ plates + camera
class Plate:
    """An image you can point a camera at. Camera = (cx, cy, h) in the plate's own
    coordinate system (for the painting: pixels of the 1920x2400 original)."""

    def __init__(self, img, scale=1.0, pad=(0, 0), bg=(0, 0, 0)):
        self.scale = scale
        px, py = pad
        self.pad = pad
        canvas = Image.new(img.mode, (img.width + 2 * px, img.height + 2 * py), bg if img.mode == "RGB" else 0)
        canvas.paste(img, (px, py))
        self.im = canvas

    def shoot(self, cam, w, h):
        cx, cy, ch = cam
        cw = ch * w / h
        s, (px, py) = self.scale, self.pad
        box = ((cx - cw / 2) * s + px, (cy - ch / 2) * s + py, (cx + cw / 2) * s + px, (cy + ch / 2) * s + py)
        assert box[0] >= 0 and box[1] >= 0 and box[2] <= self.im.width and box[3] <= self.im.height, (cam, box)
        return np.asarray(self.im.resize((w, h), Image.LANCZOS, box=box))


_cache = {}
_lock = threading.RLock()


def memo(fn):
    def wrap(*a):
        k = (fn.__name__,) + a
        with _lock:
            if k not in _cache:
                _cache[k] = fn(*a)
            return _cache[k]
    return wrap


def _main_img():
    return Image.open(ART / "daniel-conway-art-block_MJ9i.jpg").convert("RGB")


@memo
def painting():
    """the 1920x2400 painting on black (wide shots)."""
    return Plate(_main_img(), 1.0, pad=(1300, 60))


HS = 3080 / 1920  # scale of the artist's own close-up crop relative to the 1920x2400 image


@memo
def painting_hi():
    """1.6x plate for detail shots: the painting upscaled, with the artist's own
    close-up crop (real extra detail around the figure) registered and feathered in."""
    hi = _main_img().resize((3080, 3850), Image.LANCZOS)
    close = Image.open(ART / "daniel-conway-art-block-close_MJ9i.jpg").convert("RGB")
    w, h = close.size
    f = 48
    ax = np.minimum(np.arange(w), np.arange(w)[::-1]) / f
    ay = np.minimum(np.arange(h), np.arange(h)[::-1]) / f
    a = np.clip(np.minimum.outer(ay, ax), 0, 1)
    a = a * a * (3 - 2 * a)
    hi.paste(close, (1026, 1579), Image.fromarray((a * 255).astype(np.uint8)))
    return Plate(hi, HS, pad=(2100, 340))


@memo
def painting_white():
    """illustration only: the same plate with the black disc turned into blank-canvas white."""
    im = painting_hi().im; a = np.asarray(im).astype(np.float32)
    s, (px, py) = HS, (2100, 340); cx, cy, R = 961.0, 1114.0, 694.0
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]].astype(np.float32)
    inside = np.clip((R * s - 3 - np.hypot(xx - (cx * s + px), yy - (cy * s + py))) / 3, 0, 1)
    dark = np.clip((50 - a.max(2)) / 22, 0, 1)
    m = (inside * dark)[..., None]
    out = a * (1 - m) + np.array([246, 243, 236], np.float32) * m
    pl = Plate.__new__(Plate); pl.scale = s; pl.pad = (px, py); pl.im = Image.fromarray(out.astype(np.uint8)); return pl


DISC = (961.0, 1114.0, 694.0)  # centre x, y, radius of the black disc in painting pixels


@memo
def masks():
    """line-art overlays in painting coordinates: ring = the visible arc of the disc's
    edge (it stops where the figure / hill overlap the disc), border = the painting's frame."""
    a = np.asarray(_main_img()).astype(np.int16)
    cx, cy, R = DISC
    n = 1440
    th = np.arange(n) * 2 * math.pi / n
    def samp(r):
        x = np.clip(np.round(cx + r * np.cos(th)).astype(int), 0, 1919)
        y = np.clip(np.round(cy + r * np.sin(th)).astype(int), 0, 2399)
        return a[y, x].max(1)
    vis = ((samp(R - 9) < 12) & (samp(R - 16) < 12) & (samp(R + 9) > 24)).astype(np.float32)
    k = 13  # close small gaps (petals crossing the edge), then soften the arc ends
    pad = np.concatenate([vis[-k:], vis, vis[:k]])
    med = np.array([np.median(pad[i:i + 2 * k + 1]) for i in range(n)])
    pad = np.concatenate([med[-k:], med, med[:k]])
    vis = np.convolve(pad, np.ones(9) / 9, "same")[k:-k]
    yy, xx = np.mgrid[0:2400, 0:1920].astype(np.float32)
    d = np.abs(np.hypot(xx - cx, yy - cy) - R)
    ang = (np.arctan2(yy - cy, xx - cx) % (2 * math.pi)) / (2 * math.pi) * n
    lw = 5.0
    ring = np.clip(lw / 2 + 0.5 - d, 0, 1) * vis[np.round(ang).astype(int) % n]
    e = np.minimum(np.minimum(xx, 1919 - xx), np.minimum(yy, 2399 - yy))
    border = np.clip(lw / 2 + 0.5 - np.abs(e - 5), 0, 1)
    mk = lambda m: Plate(Image.fromarray((m * 255).astype(np.uint8)), 1.0, pad=(1300, 60))
    return mk(ring), mk(border)


def chat_plate(name, w, h, dsf, params, scene="PLATE_chat", bg=CHAT_BG):
    """a still of a DOM scene from Chrome (cached), plus element rects in CSS px."""
    CACHE.mkdir(parents=True, exist_ok=True)
    src = max((HERE / f).stat().st_mtime for f in ("scenes.html", "dom.mjs"))
    png = CACHE / f"{name}.png"
    if not png.exists() or png.stat().st_mtime < src:
        subprocess.run(["node", str(HERE / "dom.mjs"), "plate", scene, str(png), str(w), str(h), str(dsf),
                        json.dumps(params)], check=True)
    img = Image.open(png).convert("RGB")
    rects = json.loads(Path(str(png) + ".json").read_text())
    return Plate(img, dsf, pad=(60 * dsf, 60 * dsf), bg=bg), rects


@memo
def prompt_img(caret):
    """the empty prompt window, 1920x1080, with the caret on or off."""
    return chat_plate(f"prompt_{caret}", 1920, 1080, 1, {"_t": 0.1 if caret else 0.7}, scene="U5b", bg=(0, 0, 0))[0].im.crop((60, 60, 1980, 1140))


@memo
def chat_hl(which):
    return chat_plate("chat_hl_" + which, 1920, 1080, 3, {"hl": which})


@memo
def chat_full():
    return chat_plate("chat_full", 1920, 1080, 3, {})


@memo
def chat_dim():
    return chat_plate("chat_dim", 1920, 1080, 3, {"dim": 1})


@memo
def chat_narrow():
    return chat_plate("chat_narrow", 958, 1080, 2, {"narrow": 1})


def rc(r):
    return (r["x"] + r["w"] / 2, r["y"] + r["h"] / 2)



# ------------------------------------------------------------------ painting highlights (whole painting stays in frame)
REG = {  # soft regions in painting pixels: ("p", polygon) / ("e", cx, cy, rx, ry)
    "woman": [("p", [(930, 1140), (1110, 1140), (1185, 1290), (1150, 1480), (1515, 1515), (1505, 1735), (1265, 2000),
                     (880, 2000), (870, 1640), (675, 1575), (685, 1365), (900, 1365)])],
    "figure": [("p", [(930, 1140), (1110, 1140), (1185, 1290), (1150, 1480), (1515, 1515), (1505, 1735), (1265, 2000),
                      (880, 2000), (880, 1600), (930, 1365)])],
    "dress": [("p", [(1085, 1490), (1515, 1505), (1515, 1745), (1265, 1995), (895, 1995), (895, 1640)])],
    "tools": [("e", 800, 1445, 250, 180)],
    "brush": [("e", 795, 1412, 105, 62)],
    "poppies": [("p", [(0, 2030), (900, 1985), (1380, 1800), (1920, 1720), (1920, 2400), (0, 2400)])],
    "mountains": [("p", [(0, 700), (260, 690), (345, 1000), (300, 1570), (0, 1570)]),
                  ("p", [(1640, 1240), (1920, 1200), (1920, 1625), (1480, 1625)])],
    "lake": [("e", 1690, 1695, 275, 88)],
    "clouds": [("p", [(0, 60), (330, 60), (610, 560), (430, 770), (0, 770)]), ("p", [(1640, 520), (1920, 500), (1920, 1195), (1600, 1195)])],
    "petals": [("e", 1180, 2150, 340, 205)],
    "edge": [("e", 700, 1650, 150, 150)],
}
PX0, PS = 528.0, 0.45       # the full painting on a 1920x1080 frame: left edge and scale


@memo
def region_mask(name):
    """HxW float mask (0..1) of a painting region, in frame pixels, with a soft edge."""
    from PIL import ImageDraw, ImageFilter
    if name in ("out", "disc", "all"):
        yy, xx = np.mgrid[0:1080, 0:1920].astype(np.float32)
        d = np.hypot((xx - PX0) / PS - DISC[0], yy / PS - DISC[1]) - DISC[2]
        inp = ((xx >= PX0) & (xx < PX0 + 864)).astype(np.float32)
        if name == "all": return inp
        m = np.clip(d * PS / 3 + 0.5, 0, 1)
        return (m if name == "out" else 1 - m) * inp
    k = 2
    im = Image.new("L", (1920 * k, 1080 * k), 0); d = ImageDraw.Draw(im)
    for sh in REG[name]:
        if sh[0] == "p": d.polygon([((PX0 + x * PS) * k, y * PS * k) for x, y in sh[1]], fill=255)
        else: _, cx, cy, rx, ry = sh; d.ellipse([(PX0 + (cx - rx) * PS) * k, (cy - ry) * PS * k, (PX0 + (cx + rx) * PS) * k, (cy + ry) * PS * k], fill=255)
    im = im.filter(ImageFilter.GaussianBlur(24 * k)).resize((1920, 1080), Image.BILINEAR)
    return np.asarray(im).astype(np.float32) / 255


@memo
def ring_mask():
    """the disc's visible edge as a 1080p line mask (thicker than the split-screen one)."""
    ring = masks()[0].shoot(FULL, 1920, 1080).astype(np.float32) / 255
    from PIL import ImageFilter
    im = Image.fromarray((np.clip(ring * 1.7, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))
    return np.asarray(im).astype(np.float32) / 255


def loupe_layer(sx, sy, side):
    """magnifier: 1.6x detail of the painting around (sx, sy) shown in the black margin; returns (rgb float, alpha float)."""
    from PIL import ImageDraw
    R = 205; lx = 264 if side < 0 else 1656; ly = 430 if side < 0 else 650
    det = painting_hi().shoot((sx, sy, 2 * R / 1.55), 2 * R, 2 * R)
    k = 3
    a = Image.new("L", (1920 * k, 1080 * k), 0); d = ImageDraw.Draw(a)
    px, py = PX0 + sx * PS, sy * PS; r0 = R / 1.55 * PS
    ang = math.atan2(ly - py, lx - px)
    d.line([((px + r0 * math.cos(ang)) * k, (py + r0 * math.sin(ang)) * k), ((lx - R * math.cos(ang)) * k, (ly - R * math.sin(ang)) * k)], fill=255, width=2 * k)
    d.ellipse([(px - r0) * k, (py - r0) * k, (px + r0) * k, (py + r0) * k], outline=255, width=2 * k)
    d.ellipse([(lx - R - 3) * k, (ly - R - 3) * k, (lx + R + 3) * k, (ly + R + 3) * k], fill=255)
    line = np.asarray(a.resize((1920, 1080), Image.LANCZOS)).astype(np.float32) / 255
    c = Image.new("L", (1920 * k, 1080 * k), 0); ImageDraw.Draw(c).ellipse([(lx - R) * k, (ly - R) * k, (lx + R) * k, (ly + R) * k], fill=255)
    inner = np.asarray(c.resize((1920, 1080), Image.LANCZOS)).astype(np.float32) / 255
    rgb = np.full((1080, 1920, 3), 255, np.float32)
    rgb[ly - R:ly + R, lx - R:lx + R] = det * inner[ly - R:ly + R, lx - R:lx + R, None] + 255 * (1 - inner[ly - R:ly + R, lx - R:lx + R, None])
    return rgb, line


def hl_scene(P, W=1920, H=1080):
    """P["_hl"] = [[t0, t1, name, ...]]: name = a REG region | out | ring | white | all | loupe (sx, sy, side).
    Everything outside the active regions is dimmed; the painting itself never moves."""
    ev = P.get("_hl", []); FADE = float(P.get("fade", 1.0)); floor = float(P.get("floor", 0.52)); HOLD = 0.45
    base = painting_hi().shoot(FULL, W, H).astype(np.float32)
    white = painting_white().shoot(FULL, W, H).astype(np.float32) if any(e[2] == "white" for e in ev) else None
    loupes = {i: loupe_layer(*e[3:6]) for i, e in enumerate(ev) if e[2] == "loupe"}
    fin = float(P.get("fadein", 0)); fout = float(P.get("fadeout", 0)); dur = float(P.get("_dur", 1e9))
    def f(t):
        D = 0.0; M = None; ring = 0.0; wa = 0.0; lp = []
        for i, e in enumerate(ev):
            fd = min(FADE, (e[1] - e[0]) * 0.45)                 # long, eased fades; short events get proportionally shorter ones
            a = sm(t, e[0], e[0] + fd) * (1 - sm(t, e[1] - fd, e[1]))
            # the dimming itself holds a little longer than each region, so the light glides from one part to the next
            ad = sm(t, e[0] - HOLD, e[0] - HOLD + fd) * (1 - sm(t, e[1] + HOLD - fd, e[1] + HOLD))
            if a <= 0 and ad <= 0: continue
            nm = e[2]
            if nm == "white": wa = max(wa, a); continue
            if nm == "loupe": lp.append((i, a)); continue
            if nm == "ring": ring = max(ring, a); D = max(D, 0.45 * ad); m = region_mask("disc") * a
            elif nm == "all": m = region_mask("all") * a
            else: D = max(D, ad); m = region_mask(nm) * a
            M = m if M is None else np.maximum(M, m)
        fr = base if wa <= 0 else base * (1 - wa) + white * wa
        if D > 0:
            fr = fr * (1 - D * (1 - floor) * (1 - (M if M is not None else 0)))[..., None]
        if ring > 0:
            ln = (ring_mask() * ring * 0.62)[..., None]; fr = fr * (1 - ln) + 255 * ln
        for i, a in lp:
            rgb, al = loupes[i]; al = (al * a * 0.9)[..., None]; fr = fr * (1 - al) + rgb * al
        g = (ss(t, 0, fin) if fin else 1.0) * ((1 - ss(t, dur - fout, dur)) if fout else 1.0)
        if g < 1: fr = fr * g
        return np.clip(fr + 0.5, 0, 255).astype(np.uint8)
    return W, H, f


# ------------------------------------------------------------------ three voids side by side / the prompt, multiplied
def pil_font(sz, weight=500):
    from PIL import ImageFont
    return ImageFont.truetype(str(HERE / "fonts" / f"inter-latin-{weight}-normal.ttf"), sz)


@memo
def spawn_panel():
    """today's spawn from above (2b2t Atlas tiles), 1920x2400, the obsidian roof in the middle."""
    sys.path.insert(0, str(HERE.parent / "map")); import tiles as T
    hb = 4300.0; wb = hb * 0.8
    src = T.place(1, int(-wb / 2) - 8, int(-hb / 2) - 8, int(wb / 2) + 8, int(hb / 2) + 8)
    im = T.view(src, 0, 260, hb, 1920, 2400, Image.LANCZOS)
    bg = Image.new("RGBA", (1920, 2400), (6, 6, 10, 255)); bg.alpha_composite(im); return bg.convert("RGB")


@memo
def tri_wall():
    """one wall with the three voids hung on it at painting resolution: painting | spawn | prompt."""
    GAP = 165; PW, PH = 1920, 2400; MX, MY = 251, 520
    Wc = 3 * PW + 2 * GAP + 2 * MX; Hc = round(Wc * 9 / 16)
    wall = Image.new("RGB", (Wc, Hc), (0, 0, 0)); MY = (Hc - PH) // 2 - 130
    xs = [MX + i * (PW + GAP) for i in range(3)]
    wall.paste(_main_img(), (xs[0], MY)); wall.paste(spawn_panel(), (xs[1], MY))
    from PIL import ImageDraw
    d = ImageDraw.Draw(wall); d.rectangle([xs[2] - 3, MY - 3, xs[2] + PW + 2, MY + PH + 2], outline=(52, 52, 52), width=6)
    wall.paste(prompt_img(1), (xs[2], MY + (PH - 1080) // 2))
    pl = Plate.__new__(Plate); pl.scale = 1.0; pl.pad = (0, 0); pl.im = wall
    return pl, xs, MY, (Wc, Hc)


def tri_scene(dur, P, W=1920, H=1080):
    """cues (seconds): a, b, c = the painting / spawn / prompt panel is singled out; x = push in to the prompt until it fills the frame."""
    from PIL import ImageDraw
    g = lambda k, d: float(P.get(k, d))
    ta, tb_, tc, tx = g("a", 3), g("b", 6), g("c", 9), g("x", 11); mv = g("move", 2.2); fin = g("fadein", 0.7)
    pl, xs, MY, (Wc, Hc) = tri_wall(); PW, PH = 1920, 2400
    A = (Wc / 2, Hc / 2, float(Hc)); B = (xs[2] + PW / 2, MY + PH / 2, 1080.0)
    k = H / Hc
    heads = ["THE PAINTING", "THE SERVER", "THE PROMPT"]; subs = ["a landscape around the hole", "sixteen years of junk around it", "nothing"]
    cap = []
    for i in range(3):
        im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im); cx = (xs[i] + PW / 2) * k; y = (MY + PH) * k + 34
        f = pil_font(19, 600); tw = d.textlength(heads[i], font=f) + 4.2 * (len(heads[i]) - 1); x = cx - tw / 2
        for ch in heads[i]: d.text((x, y), ch, font=f, fill=150); x += d.textlength(ch, font=f) + 4.2
        im2 = Image.new("L", (W, H), 0); d2 = ImageDraw.Draw(im2); f2 = pil_font(30, 400)
        d2.text((cx - d2.textlength(subs[i], font=f2) / 2, y + 40), subs[i], font=f2, fill=255)
        cap.append((np.asarray(im).astype(np.float32) / 255, np.asarray(im2).astype(np.float32) / 255))
    rest = pl.shoot(A, W, H).astype(np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cols = [((xx >= (xs[i] - 80) * k) & (xx < (xs[i] + PW + 80) * k)).astype(np.float32) for i in range(3)]
    def f(t):
        u = sm(t, tx, tx + mv)
        lit = [1.0, 1.0, 1.0]; times = [ta, tb_, tc]
        cur = max([i for i in range(3) if t >= times[i]] or [-1])
        if cur >= 0:
            x = sm(t, times[cur], times[cur] + 1.1)
            for i in range(3):
                prev = 1.0 if cur == 0 else (1.0 if i == cur - 1 else 0.45)
                lit[i] = lerp(prev, 1.0 if i == cur else 0.45, x)
        if u <= 0:
            fr = rest * sum(cols[i] * lit[i] for i in range(3))[..., None]
            for i in range(3):
                h_, s_ = cap[i]; sa = ss(t, times[i], times[i] + 0.7) * (0.35 + 0.65 * (lit[i] - 0.45) / 0.55) if t >= times[i] else 0.0
                al = (h_ * (0.5 + 0.5 * lit[i]) + s_ * sa)[..., None]; fr = fr * (1 - al) + 255 * al
        else:
            cam = cam_lerp(A, B, u); fr = pl.shoot(cam, W, H).astype(np.float32)
            # the other panels fall away as we push in
            sx = lambda X: (X - cam[0]) * H / cam[2] + W / 2
            m = np.clip((xx - sx(xs[2] - 80)) / 8, 0, 1)
            fr = fr * (m * 1.0 + (1 - m) * 0.3 * (1 - ss(u, 0.0, 0.5)))[..., None]
        if t < fin: fr = fr * ss(t, 0, fin)
        return np.clip(fr + 0.5, 0, 255).astype(np.uint8)
    return W, H, f


def grid_scene(dur, P, W=1920, H=1080):
    """the empty prompt, repeated: the camera pulls back from one screen to n1 screens across.
    _keys = [[t, screens_across], ...]; lit0 = share of screens already on; more = time the rest start to switch on."""
    keys = P.get("_keys") or [[0, 1], [dur, 20]]
    ts = [k[0] for k in keys]; ls = [math.log(k[1]) for k in keys]
    lit0 = float(P.get("lit0", 0.3)); more = float(P.get("more", dur * 0.6)); wave = float(P.get("wave", 2.5)); first = float(P.get("first", 0.0))
    GAPF = 0.06; rng = np.random.default_rng(int(P.get("seed", 5)))
    NMAX = int(max(k[1] for k in keys) * 1.15) + 4; C = NMAX // 2
    rnd = rng.random((2 * NMAX + 1, 2 * NMAX + 1)); phase = rng.random((2 * NMAX + 1, 2 * NMAX + 1))
    from PIL import ImageDraw
    on = []
    for c in (1, 0):        # every screen gets a bezel so it still reads as a screen when it is small
        im = prompt_img(c).copy(); ImageDraw.Draw(im).rounded_rectangle([4, 4, 1915, 1075], radius=36, outline=(70, 70, 74), width=9); on.append(im)
    off = np.asarray(Image.new("RGB", (1920, 1080), (0, 0, 0))).copy()
    _o = Image.new("RGB", (1920, 1080), (0, 0, 0)); ImageDraw.Draw(_o).rounded_rectangle([4, 4, 1915, 1075], radius=36, outline=(30, 30, 32), width=9); on.append(_o)
    cache = {}
    def tile(P_, c):
        if (P_, c) not in cache:
            if len(cache) > 6: cache.clear()
            tw = round(P_ / (1 + GAPF)); th = round(tw * 9 / 16)
            cache[(P_, c)] = np.asarray(on[c].resize((tw, th), Image.LANCZOS)).astype(np.float32)
        return cache[(P_, c)]
    def n_at(t):
        if t <= ts[0]: return math.exp(ls[0])
        if t >= ts[-1]: return math.exp(ls[-1])
        j = max(q for q in range(len(ts) - 1) if ts[q] <= t); x = (t - ts[j]) / (ts[j + 1] - ts[j])
        x = x * x * (3 - 2 * x) if len(ts) == 2 else x
        return math.exp(lerp(ls[j], ls[j + 1], x))
    def f(t):
        n = n_at(t); pitch = W / n * (1 + GAPF) if n > 1.001 else W * (1 + GAPF)
        # integer-pitch canvas, then one exact resample
        Pp = int(math.ceil(pitch)); tw = round(Pp / (1 + GAPF)); th = round(tw * 9 / 16); Pv = round(Pp * 9 / 16)
        nx = int(math.ceil(W / pitch / 2 + 0.5)); ny = int(math.ceil(H / (pitch * 9 / 16) / 2 + 0.5))
        can = np.zeros(((2 * ny + 1) * Pv, (2 * nx + 1) * Pp, 3), np.float32)
        for j in range(-ny, ny + 1):
            for i in range(-nx, nx + 1):
                r = rnd[C + j, C + i]; d = math.hypot(i, j)
                if i == 0 and j == 0: b = 1.0
                elif r < lit0: b = ss(t, first + 0.25 * d, first + 0.25 * d + 0.8)
                else: b = ss(t, more + r * wave, more + r * wave + 0.9)
                x0 = (i + nx) * Pp + (Pp - tw) // 2; y0 = (j + ny) * Pv + (Pv - th) // 2
                if b <= 0.004:
                    can[y0:y0 + th, x0:x0 + tw] = tile(Pp, 2); continue      # a screen that is still off
                c = 0 if ((t + phase[C + j, C + i] * 1.06) % 1.06) < 0.53 else 1
                can[y0:y0 + th, x0:x0 + tw] = tile(Pp, c) * b + tile(Pp, 2) * (1 - b)
        sc = pitch / Pp; cw, chh = W / sc, H / sc; cx, cy = can.shape[1] / 2, can.shape[0] / 2
        im = Image.fromarray(np.clip(can + 0.5, 0, 255).astype(np.uint8))
        return np.asarray(im.resize((W, H), Image.LANCZOS if sc < 1 else Image.BICUBIC, box=(cx - cw / 2, cy - chh / 2, cx + cw / 2, cy + chh / 2)))
    return W, H, f

# ------------------------------------------------------------------ camera scenes
FULL = (960.0, 1200.0, 2400.0)
BRUSH = (788.0, 1418.0)  # the brush tip, painting pixels


def scene(i, dur, P):
    """returns (width, height, frame_fn(t) -> uint8 HxWx3)."""
    W, H = 1920, 1080
    g = lambda k, d: float(P.get(k, d))

    if i == "HL":
        return hl_scene({**P, "_dur": dur})
    if i == "TRI":
        return tri_scene(dur, P)
    if i == "GRID":
        return grid_scene(dur, P)
    if i == "CHAT":
        # camera over the finished reply: _keys = [[t, target, zoom]], target = full | label | p1..p4 | comp; _hl = [[t0, t1, "p1"]] dims the rest
        plate, R = chat_full()
        R = dict(R); R["full"] = dict(x=0, y=0, w=1920, h=1080); R["comp"] = dict(x=300, y=926, w=1320, h=78)
        def tgt(name, zoom):
            if name == "full": return (960.0, 540.0, 1080.0 / zoom)
            x, y = rc(R[name] if name in R else R["#" + name]); h = 1080.0 / zoom
            x = min(max(x + (40 if name == "label" else 0), h * 8 / 9 - 40), 1920 - h * 8 / 9 + 40)
            return (x, min(max(y, h / 2 - 50), 1080 - h / 2 + 50), h)
        keys = [(k[0], tgt(k[1], k[2])) for k in P["_keys"]]; hl = P.get("_hl", [])
        def f(t):
            j = max([q for q in range(len(keys)) if keys[q][0] <= t] or [0])
            if j >= len(keys) - 1 or t <= keys[0][0]: cam = keys[j][1]
            else: cam = cam_lerp(keys[j][1], keys[j + 1][1], sm(t, keys[j][0], keys[j + 1][0]))
            fr = plate.shoot(cam, W, H)
            for t0, t1, which in hl:
                a = ss(t, t0, t0 + 0.9) * (1 - ss(t, t1 - 0.9, t1))
                if a > 0: fr = (fr * (1 - a) + chat_hl(which)[0].shoot(cam, W, H) * a + 0.5).astype(np.uint8)
            return fr
        return W, H, f

    if i == "CAM":
        # generic painting camera: P["_keys"] = [[t, cx, cy, h], ...] (painting px), optional P["_white"] = [[t0, t1], ...]
        keys = [(k[0], (k[1], k[2], k[3])) for k in P["_keys"]]
        if len(keys) == 1: keys.append((keys[0][0] + 1e6, keys[0][1]))
        wh = P.get("_white", [])
        ts = [k[0] for k in keys]; vals = np.array([[k[1][0], k[1][1], math.log(k[1][2])] for k in keys])
        dl = [(vals[j + 1] - vals[j]) / (ts[j + 1] - ts[j]) for j in range(len(keys) - 1)]
        tg = [dl[0] * 0]                                  # monotone cubic: no overshoot, eases out of the first and into the last key
        for j in range(1, len(keys) - 1):
            a_, b_ = dl[j - 1], dl[j]
            tg.append(np.where(a_ * b_ > 0, 2 * a_ * b_ / np.where(a_ + b_ == 0, 1, a_ + b_), 0.0))
        tg.append(dl[-1] * 0)
        def mono(t):
            if t <= ts[0]: p = vals[0]
            elif t >= ts[-1]: p = vals[-1]
            else:
                j = max(q for q in range(len(ts) - 1) if ts[q] <= t); d = ts[j + 1] - ts[j]; x = (t - ts[j]) / d
                h00, h10, h01, h11 = 2 * x**3 - 3 * x**2 + 1, x**3 - 2 * x**2 + x, -2 * x**3 + 3 * x**2, x**3 - x**2
                p = h00 * vals[j] + h10 * d * tg[j] + h01 * vals[j + 1] + h11 * d * tg[j + 1]
            return (p[0], p[1], math.exp(p[2]))
        def f(t):
            cam = mono(t)
            a = max([ss(t, a0, a0 + 0.7) * (1 - ss(t, a1 - 0.7, a1)) for a0, a1 in wh] or [0])
            fr = painting_hi().shoot(cam, W, H)
            if a > 0:
                fr = (fr * (1 - a) + painting_white().shoot(cam, W, H) * a + 0.5).astype(np.uint8)
            return fr
        return W, H, f

    if i == "C1":
        black, fade = g("black", 1.5), g("fade", 2.5)
        base = painting().shoot(FULL, W, H).astype(np.float32)
        def f(t):
            a = ss(t, black, black + fade)
            return (base * a + 0.5).astype(np.uint8)
        return W, H, f

    if i == "C2":
        rate = g("rate", 0.0016)  # zoom per second
        def f(t):
            te = eased_time(t, 2.5)
            return painting().shoot((960, 1200 + 0.9 * te, 2400 / (1 + rate * te)), W, H)
        return W, H, f

    if i == "C3":
        A, B = (960, 1212, 2340), (960, 1545, 1062)
        T = g("move", dur * 0.78)
        return W, H, lambda t: painting_hi().shoot(cam_lerp(A, B, glide(t, T)), W, H)

    if i == "C4":
        keys = [(0.00, (836, 1404, 600)),      # the brush tip against the black
                (0.20, (862, 1418, 580)),
                (0.50, (1262, 1905, 640)),     # petals / poppies
                (0.82, (760, 1700, 640)),      # the flat black edge of the disc
                (1.00, (665, 1622, 600))]
        return W, H, lambda t: painting_hi().shoot(cam_path(keys, t / dur), W, H)

    if i == "P1b":
        tau = g("tau", 16.0)
        def f(t):
            e = math.exp(-t / tau)
            return painting().shoot((960, 1200 + 62 * e, 2400 * (1 - 0.07 * e)), W, H)
        return W, H, f

    if i == "P1c":
        A, B = (930, 1404, 860), (BRUSH[0] - 6, BRUSH[1] - 4, 600)
        T = g("move", dur * 0.75)
        return W, H, lambda t: painting_hi().shoot(cam_lerp(A, B, glide(t, T)), W, H)

    if i in ("S4a_left", "S4b_left", "S4c_left"):
        w = 960
        base = painting().shoot(FULL, w, H).astype(np.float32)
        ring, border = (m.shoot(FULL, w, H).astype(np.float32)[..., None] / 255 for m in masks())
        t0, d = g("t0", 0.6), g("fade", 1.3)
        dim_to = g("dim", 0.38)
        def f(t):
            if i == "S4a_left":
                ra = ba = 0.0; dim = 1.0
            elif i == "S4b_left":      # landscape = everything between the frame and the disc
                ra = ba = ss(t, t0, t0 + d); dim = 1.0
            else:                      # the disc alone; the landscape recedes
                x = ss(t, t0, t0 + d)
                ra, ba, dim = 1.0, 1.0 - x, lerp(1.0, dim_to, x)
            line = np.clip(ring * ra + border * ba, 0, 1) * 0.92
            return np.clip(base * dim * (1 - line) + 255 * line + 0.5, 0, 255).astype(np.uint8)
        return w, H, f

    if i == "S4d":
        A, B = (960, 1492, 1080), (1022, 1500, 1000)
        T = g("move", min(6.0, dur * 0.45))
        def f(t):
            cx, cy, h = cam_lerp(A, B, sm(t, 0, T))
            return painting_hi().shoot((cx, cy, h / (1 + 0.0004 * max(0.0, t - T * 0.8))), W, H)
        return W, H, f

    if i in ("U6c", "U6d"):
        plate, R = chat_full()
        x, y = rc(R["#label"] if i == "U6c" else R["#p4"])
        zoom = g("zoom", 2.3 if i == "U6c" else 2.15)
        hold = g("hold", 0.6)
        A, B = (960, 540, 1080), (x + (40 if i == "U6c" else 30), y, 1080 / zoom)
        T = g("move", min(dur * 0.6, 7.0 if i == "U6c" else 5.0))
        def f(t):
            cx, cy, h = cam_lerp(A, B, sm(t, hold, hold + T))
            return plate.shoot((cx, cy, h / (1 + 0.0012 * max(0.0, t - hold - T * 0.8))), W, H)
        return W, H, f

    if i == "U6f":
        (pa, R), (pb, _) = chat_full(), chat_dim()
        x, y = rc(R["#p1"])
        t0, d = g("t0", 1.0), g("fade", 1.4)
        A, B = (960, 540, 1080), (lerp(960, x, 0.6), lerp(540, y, 0.6), 1080 / g("zoom", 1.13))
        T = g("move", dur * 0.75)
        def f(t):
            cam = cam_lerp(A, B, glide(max(0.0, t - t0), T))
            a = ss(t, t0, t0 + d)
            if a <= 0:
                return pa.shoot(cam, W, H)
            if a >= 1:
                return pb.shoot(cam, W, H)
            return (pa.shoot(cam, W, H) * (1 - a) + pb.shoot(cam, W, H) * a + 0.5).astype(np.uint8)
        return W, H, f

    if i in ("U6e", "E1"):
        hw, gut = 958, 4
        plate, R = chat_narrow()
        rate = g("rate", 0.0010 if i == "U6e" else 0.0005)
        ry = R["#reply"]["y"] + R["#reply"]["h"] / 2
        def f(t):
            te = eased_time(t, 3.0)
            z = 1 + rate * te
            if i == "U6e":   # the woman with her brush raised
                left = painting_hi().shoot((1004, 1545 - 6 * z, 1170 / z), hw, H)
            else:            # the whole painting, fitted to the half
                left = painting().shoot((960, 1200 + 0.3 * te, 2400 / z), hw, H)
            right = plate.shoot((479, lerp(540, ry, 1 - 1 / z), 1080 / z), hw, H)
            out = np.zeros((H, W, 3), np.uint8)
            # sides are singled out in turn: la..ra = the painting, ra..both = the reply, then both
            la, ra, bo = g("la", 1e9), g("ra", 1e9), g("both", 1e9)
            dl = sm(t, ra, ra + 1.1) * (1 - sm(t, bo, bo + 1.1)); dr = sm(t, la, la + 1.1) * (1 - sm(t, ra, ra + 1.1))
            out[:, :hw] = left if dl <= 0 else (left * (1 - 0.5 * dl)).astype(np.uint8)
            out[:, hw + gut:] = right if dr <= 0 else (right * (1 - 0.5 * dr)).astype(np.uint8)
            return out
        return W, H, f

    raise SystemExit(f"unknown shot {i}")


# ------------------------------------------------------------------ encode
def ffmpeg_cmd(inp, out):
    return ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inp,
            "-vf", "scale=in_range=full:out_range=tv:out_color_matrix=bt709:flags=accurate_rnd+full_chroma_int+lanczos,format=yuv420p",
            "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-threads", "4",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
            "-r", str(FPS), "-an", "-movflags", "+faststart", str(out)]


def render(i, dur=None, P=None, out=None, workers=3):
    i = ALIAS.get(i, i)
    if i not in EST:
        raise SystemExit(f"unknown shot {i}; try: {' '.join(EST)}")
    dur = float(dur) if dur else default_dur(i)
    P = P or {}
    out = Path(out) if out else OUT / f"{i}.mp4"
    OUT.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    tmp = TMP / f".gfx-{i}-{os.getpid()}.mp4"
    n = round(dur * FPS)
    try:
        if i in DOM:
            node = subprocess.Popen(["node", str(HERE / "dom.mjs"), "frames", i, str(dur), str(FPS), "1920", "1080",
                                     json.dumps(P)], stdout=subprocess.PIPE)
            ff = subprocess.Popen(ffmpeg_cmd(["-f", "image2pipe", "-c:v", "png", "-framerate", str(FPS), "-i", "-"], tmp),
                                  stdin=node.stdout)
            node.stdout.close()
            if ff.wait() or node.wait():
                raise SystemExit(f"{i}: render failed")
        else:
            w, h, fn = scene(i, dur, P)
            ff = subprocess.Popen(ffmpeg_cmd(["-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
                                              "-framerate", str(FPS), "-i", "-"], tmp), stdin=subprocess.PIPE)
            fn(0.0)  # build plates once, outside the pool
            with ThreadPoolExecutor(workers) as ex:
                for k0 in range(0, n, workers * 4):
                    for fr in ex.map(fn, [k / FPS for k in range(k0, min(n, k0 + workers * 4))]):
                        assert fr.shape == (h, w, 3), fr.shape
                        ff.stdin.write(fr.tobytes())
            ff.stdin.close()
            if ff.wait():
                raise SystemExit(f"{i}: ffmpeg failed")
        os.replace(tmp, out) if tmp.stat().st_dev == out.parent.stat().st_dev else (
            subprocess.run(["cp", str(tmp), str(out)], check=True), tmp.unlink())
    finally:
        if tmp.exists():
            tmp.unlink()
    print(f"{i}: {dur:g}s -> {out}", flush=True)


def contact():
    from PIL import ImageDraw, ImageFont
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    ids = list(EST)
    cols, tw, th = 5, 480, 270
    rows = math.ceil(len(ids) / cols)
    sheet = Image.new("RGB", (cols * tw, rows * (th + 30)), (18, 18, 18))
    d = ImageDraw.Draw(sheet)
    for k, i in enumerate(ids):
        f = OUT / f"{i}.mp4"
        if not f.exists():
            continue
        dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                             "csv=p=0", str(f)]).decode())
        at = {"C1": 0.9, "U5a": 0.9, "E4": 0.33, "U6a": 0.55, "U5d": 0.1, "U6b": 0.6}.get(i, 0.6) * dur
        raw = subprocess.check_output(["ffmpeg", "-v", "error", "-ss", f"{at:.3f}", "-i", str(f), "-frames:v", "1",
                                       "-vf", f"scale=-1:{th}", "-f", "image2pipe", "-c:v", "png", "-"])
        import io
        im = Image.open(io.BytesIO(raw)).convert("RGB")
        x, y = (k % cols) * tw, (k // cols) * (th + 30)
        sheet.paste(im, (x + (tw - im.width) // 2, y + 30))
        d.text((x + 8, y + 4), f"{i}   {dur:.1f}s", fill=(235, 235, 235), font=font)
    sheet.save(OUT / "contact.jpg", quality=90)
    print(OUT / "contact.jpg")


def main():
    os.nice(15)  # a game is being filmed on this machine; stay out of its way
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("id")
    ap.add_argument("--dur", type=float)
    ap.add_argument("--set", action="append", default=[], metavar="key=value", help="override a beat / parameter (see README)")
    ap.add_argument("--out")
    ap.add_argument("--json", help="extra parameters as a JSON object (camera keys etc.)")
    ap.add_argument("--still", type=float, metavar="T", help="write one frame at time T (PNG, to --out) instead of a clip")
    ap.add_argument("-j", type=int, default=3)
    a = ap.parse_args()
    if a.id == "list":
        for i in EST:
            print(f"{i:9s} est {EST[i]:>3}s  default {default_dur(i):g}s")
    elif a.id == "contact":
        contact()
    elif a.id == "all":
        with ThreadPoolExecutor(a.j) as ex:
            list(ex.map(lambda i: subprocess.run([sys.executable, __file__, i], check=False), EST))
        contact()
    else:
        P = {}
        for kv in a.set:
            k, v = kv.split("=", 1)
            P[k] = float(v)
        if a.json:
            P.update(json.loads(a.json))
        if a.still is not None:
            i = ALIAS.get(a.id, a.id)
            dur = a.dur or default_dur(i)
            if i in DOM:
                subprocess.run(["node", str(HERE / "dom.mjs"), "plate", i, a.out, "1920", "1080", "1",
                                json.dumps({**P, "_t": a.still, "_dur": dur})], check=True)
                os.remove(a.out + ".json")
            else:
                Image.fromarray(scene(i, dur, P)[2](a.still)).save(a.out)
        else:
            render(a.id, a.dur, P, a.out)


if __name__ == "__main__":
    main()
