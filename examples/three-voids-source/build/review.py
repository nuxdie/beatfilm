#!/usr/bin/env python3
"""review.py <out.jpg> ID [ID...] — one frame per narration beat (taken 60% into the beat) with the beat text under it."""
import sys, subprocess, io, importlib.util, textwrap
from PIL import Image, ImageDraw, ImageFont
sys.argv, args = [sys.argv[0]], sys.argv[1:]
sp = importlib.util.spec_from_file_location("a", "/home/n/Videos/three-voids/build/assemble.py"); a = importlib.util.module_from_spec(sp); sp.loader.exec_module(a)
T = a.durations(); N = dict(a.NARR.NARR); f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
cells = []
for sid in args[1:]:
    st = a.BEATS[sid] + [T[sid]]; bl = N[sid].split(" | ")
    for i, txt in enumerate(bl):
        t = st[i] + (st[i + 1] - st[i]) * 0.6
        raw = subprocess.check_output(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{t:.2f}", "-i", f"{a.SEG}/{sid}.mp4", "-frames:v", "1", "-vf", "scale=480:270", "-f", "image2pipe", "-c:v", "png", "-"])
        c = Image.new("RGB", (480, 350), (20, 20, 20)); c.paste(Image.open(io.BytesIO(raw)), (0, 0))
        ImageDraw.Draw(c).text((6, 274), f"{sid}.{i} @{st[i]:.1f}s\n" + "\n".join(textwrap.wrap(txt, 60)[:3]), font=f, fill=(240, 240, 240)); cells.append(c)
cols = 4; W = Image.new("RGB", (cols * 480, 350 * -(-len(cells) // cols)))
for i, c in enumerate(cells): W.paste(c, (i % cols * 480, i // cols * 350))
W.save(args[0], quality=85)
