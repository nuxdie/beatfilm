from config import ENC
#!/usr/bin/env python3
"""kb.py <image> <out.mp4> <dur> <json [[cx,cy,h],[cx,cy,h],...]> [ease]
Smooth sub-pixel camera move over a still. Keyframes: centre (cx,cy) and view height h, all as fractions of the
image height (cx is in units of image height too, so 0..W/H). View is 16:9. Keyframes are evenly spaced."""
import sys, json, subprocess
from PIL import Image
img = Image.open(sys.argv[1]).convert("RGB"); out = sys.argv[2]; dur = float(sys.argv[3]); kf = json.loads(sys.argv[4])
ease = sys.argv[5] if len(sys.argv) > 5 else "smooth"
fo = float(sys.argv[6]) if len(sys.argv) > 6 else 0.0
W, H = img.size; n = max(1, round(dur * 60))
p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1920x1080", "-r", "60", "-i", "-",
                      *ENC, out], stdin=subprocess.PIPE)
def e(u):
    if ease == "linear": return u
    if ease == "out": return 1 - (1 - u) ** 2
    return u * u * (3 - 2 * u)
for i in range(n):
    u = i / max(1, n - 1)
    if len(kf) == 1: a = b = kf[0]; v = 0
    else:
        s = u * (len(kf) - 1); j = min(int(s), len(kf) - 2); v = e(s - j) if ease != "linear" else s - j; a, b = kf[j], kf[j + 1]
    cx = a[0] + (b[0] - a[0]) * v; cy = a[1] + (b[1] - a[1]) * v; h = a[2] * (b[2] / a[2]) ** v
    bh = h * H; bw = bh * 16 / 9; x0 = cx * H - bw / 2; y0 = cy * H - bh / 2
    x0 = min(max(0, x0), W - bw); y0 = min(max(0, y0), H - bh)
    fr = img.resize((1920, 1080), Image.LANCZOS, box=(x0, y0, x0 + bw, y0 + bh))
    rem = (n - 1 - i) / 60
    if fo and rem < fo: fr = fr.point(lambda v, k=rem / fo: int(v * k))
    p.stdin.write(fr.tobytes())
p.stdin.close()
if p.wait(): raise RuntimeError("still renderer failed")
