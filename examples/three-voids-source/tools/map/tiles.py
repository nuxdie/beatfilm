"""Tile access for 2b2tatlas.com maps (cached on disk). World coords = overworld blocks (x east, z south).
place(layer, z): 512px tiles, 2**z blocks/px, tile (i,j) covers x in [i*512*2**z, ...), z likewise.
hist(slug, z): XYZ pyramid, 256px tiles, centre of world at tile 2**z/2."""
import os, io, subprocess, concurrent.futures as cf
from PIL import Image
CACHE = "/home/n/Games/three-voids-raw/tiles"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
def fetch(url):
    p = os.path.join(CACHE, url.split("://")[1].replace("/", "_"))
    if os.path.exists(p): return p if os.path.getsize(p) > 0 else None
    r = subprocess.run(["curl", "-s", "-f", "-A", UA, "--max-time", "40", "-o", p + ".part", url])
    if r.returncode == 0: os.rename(p + ".part", p); return p
    if os.path.exists(p + ".part"): os.remove(p + ".part")
    if r.returncode == 22: open(p, "w").close()      # 404: remember
    return None
def place_url(layer, z, i, j, a=0, b=0, c=0): return f"https://api.blackportal.cloud/tiles/place/{layer}/{z}/{a}/{b}/{c}/t.{i}.{j}.webp"
def mosaic(urlf, i0, j0, i1, j1, ts, bg=(0, 0, 0, 0)):
    """tiles i0..i1-1 x j0..j1-1 -> RGBA image"""
    im = Image.new("RGBA", ((i1 - i0) * ts, (j1 - j0) * ts), bg)
    jobs = [(i, j) for i in range(i0, i1) for j in range(j0, j1)]
    with cf.ThreadPoolExecutor(8) as ex: paths = list(ex.map(lambda t: fetch(urlf(*t)), jobs))
    for (i, j), p in zip(jobs, paths):
        if p:
            try: t = Image.open(p).convert("RGBA")
            except Exception: continue
            if t.size != (ts, ts): t = t.resize((ts, ts))
            im.paste(t, ((i - i0) * ts, (j - j0) * ts))
    return im
def place(z, x0, z0, x1, z1, layers=("base", "overlay"), **k):
    """composited place map for block rect -> (image, blocks_per_px, origin_x, origin_z)"""
    s = 512 * 2 ** z; i0, j0 = x0 // s, z0 // s; i1, j1 = -(-x1 // s), -(-z1 // s)
    out = None
    for l in layers:
        m = mosaic(lambda i, j: place_url(l, z, i, j, **k), i0, j0, i1, j1, 512)
        out = m if out is None else Image.alpha_composite(out, m)
    return out, 2 ** z, i0 * s, j0 * s
HIST = {2011: "spawn-fragment-july-2011-overworld-42a63b5587", 2012: "spawn-april-2012-overworld-93ab46ccd4", 2013: "spawn-september-2013-overworld-a93f0f1a2a",
        2016: "spawn-march-2016-overworld-d2df99bc60", 2018: "spawn-november-2017-overworld-c19cde133a", 2022: "spawn-november-2022-overworld-08159a7b85"}
def hist_tiles(year, z, i0, j0, i1, j1):
    return mosaic(lambda i, j: f"https://blackportal.cloud/AtlasTiles/{HIST[year]}/{z}/{j}/{i}.png", i0, j0, i1, j1, 256)
def hist(year, x0, z0, x1, z1, z=9):
    """historical render for block rect -> (image, blocks_per_px, origin_x, origin_z). z9 = 4 blocks/px, origin at px 64000."""
    bpp = 4 * 2 ** (9 - z); o = 64000 / 2 ** (9 - z)
    px0, py0 = o + x0 / bpp, o + z0 / bpp; px1, py1 = o + x1 / bpp, o + z1 / bpp
    i0, j0, i1, j1 = int(px0 // 256), int(py0 // 256), int(-(-px1 // 256)), int(-(-py1 // 256))
    return hist_tiles(year, z, i0, j0, i1, j1), bpp, (i0 * 256 - o) * bpp, (j0 * 256 - o) * bpp
def view(src, cx, cz, hb, w=1920, h=1080, resample=None):
    """crop a (image,bpp,ox,oz) source to a view centred cx,cz, hb blocks tall"""
    im, bpp, ox, oz = src; wb = hb * w / h
    box = ((cx - wb / 2 - ox) / bpp, (cz - hb / 2 - oz) / bpp, (cx + wb / 2 - ox) / bpp, (cz + hb / 2 - oz) / bpp)
    rs = resample if resample is not None else (Image.NEAREST if hb / h < bpp else Image.LANCZOS)
    if box[0] >= 0 and box[1] >= 0 and box[2] <= im.size[0] and box[3] <= im.size[1]: return im.resize((w, h), rs, box=box)
    return im.transform((w, h), Image.EXTENT, box, Image.BILINEAR if rs != Image.NEAREST else Image.NEAREST)
