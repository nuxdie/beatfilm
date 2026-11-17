#!/usr/bin/env python3
"""Map shots from 2b2tatlas.com tiles.  render.py <shot> <out.mp4> <dur> [k=v ...]   |   render.py <shot> --still <t> <out.png> <dur>
shots: zoomout  (overworld, spawn -> whole world, highways + known locations)   keys: h0,h1,hold0,hold1,lines,dots,dim,a
       years    (spawn 2012 -> today, same framing)                            keys: h0,h1
       drift    (slow move over today's map)                                   keys: x0,z0,h0,x1,z1,h1,a
"""
import sys, os, json, math, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import tiles as T
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); W, H = 1920, 1080
INTER = "/home/n/Games/three-voids-raw/tmp/Inter.ttf"
def font(sz, bold=False):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",):
        return ImageFont.truetype(p, sz)
def sm(u): u = max(0, min(1, u)); return u * u * (3 - 2 * u)
_src = {}
def source(z, a, hbmax, cx=0, cz=0):
    k = (z, a, cx, cz)
    if k not in _src and z > 10:
        im, bpp, ox, oz = source(10, a, H * 2 ** 11 * 1.05, cx, cz); f = 2 ** (z - 10)
        pad = (-im.size[0]) % f, (-im.size[1]) % f
        if any(pad):
            big = Image.new("RGBA", (im.size[0] + pad[0], im.size[1] + pad[1]), (0, 0, 0, 0)); big.paste(im, (0, 0)); im = big
        _src[k] = (im.reduce(f), bpp * f, ox, oz)
    if k not in _src:
        hb = hbmax; wb = hb * W / H
        _src[k] = T.place(z, int(cx - wb / 2) - 2, int(cz - hb / 2) - 2, int(cx + wb / 2) + 2, int(cz + hb / 2) + 2, a=a)
    return _src[k]
def mapview(cx, cz, hb, a=0, anchor=(0, 0)):
    """today's map at any scale; pyramid sources are centred on anchor."""
    z = max(0, min(17, int(math.floor(math.log2(max(hb / H, 1))))))
    cover = H * 2 ** (z + 1) * 1.05 + 2 * math.hypot(cx - anchor[0], cz - anchor[1])
    src = source(z, a, cover, *anchor)
    im = T.view(src, cx, cz, hb, W, H, Image.BILINEAR if hb / H >= 1 else Image.NEAREST)
    bg = Image.new("RGBA", (W, H), (6, 6, 10, 255)); bg.alpha_composite(im); return bg
def label(im, text, sub=None, credit="map: 2b2tatlas.com"):
    d = ImageDraw.Draw(im, "RGBA")
    if text:
        f = font(54, True); d.text((72 + 2, H - 150 + 2), text, font=f, fill=(0, 0, 0, 200)); d.text((72, H - 150), text, font=f, fill=(255, 255, 255, 255))
    if sub:
        f = font(24); d.text((74 + 1, H - 82 + 1), sub, font=f, fill=(0, 0, 0, 220)); d.text((74, H - 82), sub, font=f, fill=(235, 235, 235, 255))
    if credit:
        f = font(20); w = d.textlength(credit, font=f); d.text((W - 60 - w + 1, H - 58 + 1), credit, font=f, fill=(0, 0, 0, 220)); d.text((W - 60 - w, H - 58), credit, font=f, fill=(255, 255, 255, 170))
def nice(n):
    return f"{n:,.0f}".replace(",", " ")
def scalebar(im, hb, alpha=255):
    bpp = hb / H; target = 260 * bpp; e = 10 ** math.floor(math.log10(target)); v = max(x * e for x in (1, 2, 5) if x * e <= target)
    px = v / bpp; d = ImageDraw.Draw(im, "RGBA"); x0, y0 = 74, H - 190
    for off, col in ((2, (0, 0, 0, 200 * alpha // 255)), (0, (255, 255, 255, alpha))):
        d.line([(x0 + off, y0 + off), (x0 + px + off, y0 + off)], fill=col, width=3)
        d.line([(x0 + off, y0 - 7 + off), (x0 + off, y0 + 7 + off)], fill=col, width=3); d.line([(x0 + px + off, y0 - 7 + off), (x0 + px + off, y0 + 7 + off)], fill=col, width=3)
    return v

HW = json.load(open(HERE + "/hw.json")); LOC = [l for l in json.load(open(HERE + "/loc.json")) if l["dimension"] in (0, 1)]
def shot_zoomout(t, dur, P):
    h0, h1 = float(P.get("h0", 700)), float(P.get("h1", 66e6)); hold0, hold1 = float(P.get("hold0", 1.0)), float(P.get("hold1", 2.0))
    u = sm((t - hold0) / max(0.1, dur - hold0 - hold1)); u = u if P.get("ease", "smooth") == "smooth" else max(0, min(1, (t - hold0) / (dur - hold0 - hold1)))
    hb = h0 * (h1 / h0) ** u; a = int(P.get("a", 0)); k = 1 if a else 8
    im = mapview(0, 0, hb, a)
    dimk = float(P.get("dim", 0.45)); far = sm((math.log10(hb) - 4.3) / 1.2)         # dim the map as the lines take over
    if far > 0: im = Image.blend(im, Image.new("RGBA", (W, H), (6, 6, 10, 255)), far * dimk)
    ov = Image.new("RGBA", (W * 2, H * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(ov); s = 2 * H / hb
    def pt(x, z): return (W + x * s, H + z * s)
    if P.get("lines", "1") == "1":
        for h in HW:
            if h["dimension"] != 1 or not h["points"]: continue
            pts = [(p["x"] * k, p["z"] * k) for p in h["points"]]
            ext = max(max(abs(x), abs(z)) for x, z in pts); size = ext * s / 2      # px on screen
            axis = h["name"].endswith("Highway") and "Ring" not in h["name"]
            al = 1.0 if axis else sm((size - 25) / 60)
            if not axis and size > 40000: continue
            if al <= 0: continue
            la = sm((math.log10(hb) - 3.6) / 0.8)                                     # all lines appear once we are past spawn
            col = (255, 214, 120, int(235 * al * la)) if axis else (255, 255, 255, int(150 * al * la))
            if col[3] < 4: continue
            q = [pt(x, z) for x, z in pts]
            # clip far-away segments to keep coordinates sane
            lim = 60000
            q = [(max(-lim, min(lim, x)), max(-lim, min(lim, y))) for x, y in q]
            d.line(q, fill=col, width=5 if axis else 3)
    if P.get("dots", "1") == "1":
        da = sm((math.log10(hb) - 5.0) / 0.8)
        if da > 0:
            r = 5
            for l in LOC:
                x, z = (l["x"], l["z"]) if l["dimension"] == 0 else (l["x"] * 8, l["z"] * 8)
                X, Y = pt(x / (8 / k) if a else x, z / (8 / k) if a else z)
                if -10 < X < 2 * W + 10 and -10 < Y < 2 * H + 10: d.ellipse([X - r, Y - r, X + r, Y + r], fill=(255, 92, 72, int(230 * da)))
    im.alpha_composite(ov.resize((W, H), Image.LANCZOS))
    v = scalebar(im, hb)
    sub = nice(v) + " blocks"
    label(im, None, sub)
    if P.get("cap"):
        ca = sm((math.log10(hb) - 5.0) / 0.8); d2 = ImageDraw.Draw(im, "RGBA"); f = font(22)
        if ca > 0.02:
            x = 74; y = H - 232
            d2.line([(x, y - 46 + 12), (x + 46, y - 46 + 12)], fill=(255, 214, 120, int(235 * ca)), width=4); d2.text((x + 60, y - 46), "highways", font=f, fill=(255, 255, 255, int(235 * ca)))
            d2.ellipse([x + 16, y + 5, x + 28, y + 17], fill=(255, 92, 72, int(230 * ca))); d2.text((x + 60, y - 2), "known bases and builds", font=f, fill=(255, 255, 255, int(235 * ca)))
    return im

YEARS = [(2012, "April 2012"), (2016, "March 2016"), (2018, "January 2018"), (2022, "November 2022"), ("now", "2026, the obsidian roof"), ("base", "2026, underneath the roof")]
_yc = {}
def year_frame(key, hb):
    kk = (key, round(hb))
    if kk not in _yc:
        if len(_yc) > 400: _yc.clear()
        wb = hb * W / H; r = (int(-wb / 2) - 8, int(-hb / 2) - 8, int(wb / 2) + 8, int(hb / 2) + 8)
        if key == "base": src = _src.setdefault(("yb",), T.place(1, -3000, -1700, 3000, 1700, layers=("base",)))
        elif key == "now": src = _src.setdefault(("yn",), T.place(1, -3000, -1700, 3000, 1700))
        else: src = _src.setdefault(("y", key), T.hist(key, -3000, -1700, 3000, 1700))
        im = T.view(src, 0, 0, hb, W, H, Image.NEAREST if src[1] > hb / H else Image.BILINEAR)
        bg = Image.new("RGBA", (W, H), (6, 6, 10, 255)); bg.alpha_composite(im); _yc[kk] = bg
    return _yc[kk]
def shot_years(t, dur, P):
    h0, h1 = float(P.get("h0", 1500)), float(P.get("h1", 2400)); n = len(YEARS); xf = float(P.get("xf", 0.7))
    # optional explicit cut times: cuts=t1,t2,.. (start of each year after the first)
    cuts = [float(c) for c in P["cuts"].split(",")] if P.get("cuts") else [dur * (i + 1) / n for i in range(n - 1)]
    i = sum(1 for c in cuts if t >= c); hb = h0 * (h1 / h0) ** sm((t - cuts[1]) / max(0.1, cuts[2] + 1.0 - cuts[1]))   # stay tight for 2012/2016, widen into 2018
    im = year_frame(YEARS[i][0], hb).copy(); lab = YEARS[i][1]
    if i > 0 and t - cuts[i - 1] < xf:
        k = sm((t - cuts[i - 1]) / xf); im = Image.blend(year_frame(YEARS[i - 1][0], hb), im, k)
    label(im, lab, "2b2t spawn, 0 / 0")
    return im
def shot_drift(t, dur, P):
    g = lambda k, dv: float(P.get(k, dv)); u = t / dur if P.get("ease") == "linear" else sm(t / dur)
    cx = g("x0", 0) + (g("x1", 0) - g("x0", 0)) * u; cz = g("z0", 0) + (g("z1", 0) - g("z0", 0)) * u; hb = g("h0", 6000) * (g("h1", 5000) / g("h0", 6000)) ** u
    im = mapview(cx, cz, hb, int(P.get("a", 0)), anchor=(round((g("x0", 0) + g("x1", 0)) / 2), round((g("z0", 0) + g("z1", 0)) / 2)))
    label(im, P.get("title"), P.get("sub"))
    return im
SHOTS = {"zoomout": shot_zoomout, "years": shot_years, "drift": shot_drift}
def main():
    a = sys.argv[1:]; fn = SHOTS[a[0]]
    if a[1] == "--still":
        t = float(a[2]); out = a[3]; dur = float(a[4]); P = dict(x.split("=", 1) for x in a[5:]); fn(t, dur, P).convert("RGB").save(out); return
    out = a[1]; dur = float(a[2]); P = dict(x.split("=", 1) for x in a[3:]); n = round(dur * 60)
    p = subprocess.Popen(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", "60", "-i", "-",
                          "-c:v", "h264_nvenc", "-preset", "p6", "-rc", "constqp", "-qp", "17", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for i in range(n): p.stdin.write(fn(i / 60, dur, P).convert("RGB").tobytes())
    p.stdin.close(); p.wait()
if __name__ == "__main__": main()
