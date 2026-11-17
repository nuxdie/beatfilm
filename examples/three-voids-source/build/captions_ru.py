#!/usr/bin/env python3
"""captions_ru.py — out/three-voids.ru.srt (Russian subtitles on the English cut's beat timings) and VOICEOVER-RU.md
(reading script with the time each paragraph has in the finished video, for a Russian audio track)."""
import json, sys, textwrap, importlib.util
ROOT = "/home/n/Videos/three-voids"
def load(p, n):
    sp = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
EN = load(ROOT + "/build/narration.py", "en"); RU = dict(load(ROOT + "/build/narration_ru.py", "ru").NARR_RU); EDL = load(ROOT + "/build/edl.py", "edl")
TL = {x["id"]: x for x in json.load(open(ROOT + "/out/timeline.json"))}
LEAD, TAIL = 0.35, 0.55
def ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60; return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")
cues = []; sheet = ["# Three Voids — русская озвучка", "",
    "Читай подряд, одним дублем или несколькими. Каждый нумерованный абзац — один кадр; между абзацами пауза около секунды.",
    "В скобках — сколько секунд этот абзац занимает в готовом видео. Картинка уже смонтирована под английский голос,",
    "поэтому старайся уложиться примерно в это время (плюс-минус 10% не страшно: я подгоню).",
    "Если оговорился — пауза, и весь абзац заново; в дело идёт последний полный дубль.", ""]
k = 0
for sid, text in EN.NARR:
    if not text: continue
    ru = RU[sid]; eb = text.split(" | "); rb = ru.split(" | "); assert len(eb) == len(rb), (sid, len(eb), len(rb))
    x = TL[sid]; st = x["beats"]; speech_end = x["dur"] - TAIL - EDL.EXTRA.get(sid, 0)
    k += 1; sheet += [f"**{k}. [{sid}]** ({speech_end - LEAD:.0f} с)", "", ru.replace(" | ", " "), ""]
    for i, b in enumerate(rb):
        t0 = x["start"] + (LEAD if i == 0 else st[i] + 0.1); t1 = x["start"] + (st[i + 1] if i + 1 < len(st) else speech_end + 0.4) - 0.06
        parts = [b]
        if len(textwrap.wrap(b, 42)) > 2:        # too long for two lines: split into even pieces that each fit
            n = 2
            while True:
                parts = textwrap.wrap(b, max(30, len(b) // n + 10))
                if all(len(textwrap.wrap(q, 42)) <= 2 for q in parts): break
                n += 1
        tot = sum(len(p) for p in parts); t = t0
        for p in parts:
            d = (t1 - t0) * len(p) / tot; cues.append((t, t + d - 0.04, p)); t += d
out = []
for i, (a, b, p) in enumerate(cues):
    lines = textwrap.wrap(p, 42)
    if len(lines) == 2 and len(lines[1]) < 12: lines = textwrap.wrap(p, len(p) // 2 + 5)
    out.append(f"{i + 1}\n{ts(a)} --> {ts(max(b, a + 0.8))}\n" + "\n".join(lines) + "\n")
open(ROOT + "/out/three-voids.ru.srt", "w").write("\n".join(out)); open(ROOT + "/VOICEOVER-RU.md", "w").write("\n".join(sheet))
ru_chars = sum(len(v.replace(" | ", " ")) for v in RU.values()); en_chars = sum(len(t.replace(" | ", " ")) for _, t in EN.NARR)
print(len(cues), "cues; max lines", max(o.count("\n") - 2 for o in out), "; RU/EN length", round(ru_chars / en_chars, 2))
# reading speed per shot: characters per second needed to fit
worst = sorted(((len(RU[s].replace(" | ", "")) / (TL[s]["dur"] - TAIL - LEAD - EDL.EXTRA.get(s, 0)), s) for s in RU), reverse=True)[:6]
print("tightest paragraphs (chars/s):", " ".join(f"{s}:{c:.1f}" for c, s in worst))
