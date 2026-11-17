#!/usr/bin/env python3
"""Three Voids — assembly.
  assemble.py            build out/film-roughcut.mp4 (+ guide version with burned-in narration text)
  assemble.py --only M2b build just one segment (for checking)
Timing: build/timings.json {shot_id: seconds} overrides the word-count estimate (fill it from the real narration).
Narration audio: if narration/<ID>.wav (or .mp3/.m4a) exists it is laid under that segment and sets its duration (+pad).
"""
import json, os, subprocess, sys, math, importlib.util, shlex
from config import ROOT, TMP, SEG, TOOLROOT, ENC, CFG
OUT = ROOT + "/out"
os.makedirs(OUT, exist_ok=True); os.makedirs(SEG, exist_ok=True)
def load(p, name):
    sp = importlib.util.spec_from_file_location(name, p); mod = importlib.util.module_from_spec(sp); sp.loader.exec_module(mod); return mod
NARR = load(ROOT + "/build/narration.py", "narr")
_E = load(ROOT + "/build/edl.py", "edl"); EDL = _E.EDL; EXTRA = _E.EXTRA; BEATW = getattr(_E, "BEATW", {})
WPS = 2.5; PAD = 0.9


def run(cmd):
    if cmd[0] == "ffmpeg": cmd = ["ffmpeg", "-nostdin"] + cmd[1:]
    r = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if r.returncode: sys.exit("FAILED: " + " ".join(shlex.quote(c) for c in cmd) + "\n" + r.stderr[-2000:])

def probe(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip())

def narration_audio(sid):
    for ext in ("wav", "mp3", "m4a", "flac", "ogg"):
        p = f"{ROOT}/narration/{sid}.{ext}"
        if os.path.exists(p): return p

def spoken(text): return text.replace(" | ", " ")
BEATS = {}      # sid -> list of beat start times (seconds from the start of the shot), one per ' | ' beat
def durations():
    """shot lengths, and BEATS[sid] = where each picture beat starts.
    timings.json: {"ID": seconds} (beats spread by word count) or {"ID": [b0, b1, ...]} = length of every beat."""
    t = {}
    tj = ROOT + "/build/timings.json"
    over = json.load(open(tj)) if os.path.exists(tj) else {}
    for sid, text in NARR.NARR:
        a = narration_audio(sid); beats = [len(b.split()) for b in text.split(" | ")] if text else [1]
        o = over.get(sid)
        if isinstance(o, list):
            assert all(isinstance(v, (int, float)) and v > 0 for v in o), f"{sid}: beat durations must be positive"
            assert len(o) == len(beats), f"{sid}: timings.json has {len(o)} beats, narration.py has {len(beats)}"
            t[sid] = sum(o); st = [sum(o[:i]) for i in range(len(o))]
        else:
            if o is not None: t[sid] = float(o); speech = t[sid] - PAD
            elif a: speech = probe(a); t[sid] = speech + PAD + EXTRA.get(sid, 0)
            elif sid in NARR.FIXED: t[sid] = speech = NARR.FIXED[sid]
            else: speech = len(spoken(text).split()) / WPS; t[sid] = speech + PAD + EXTRA.get(sid, 0)
            lead = 0.35 if (a or text) else 0          # narration starts 0.35 s into the shot
            wb = [b + 0.8 + BEATW.get(sid, 0) for b in beats]
            if sid in BEATW and o is None: speech += EXTRA.get(sid, 0)      # spread the extra time through the list
            st = [0.0] + [lead + speech * sum(wb[:i]) / sum(wb) for i in range(1, len(beats))]
        BEATS[sid] = st
    return t
def beat_time(sid, b, total):
    """time of fractional beat index b (1.5 = halfway through beat 1)."""
    st = BEATS[sid] + [total]; i = min(int(b), len(st) - 2); return st[i] + (st[i + 1] - st[i]) * (b - i)

GRADE = {"nether": "eq=gamma=1.35:contrast=1.05:saturation=1.1", "night": "eq=gamma=1.25", None: None}

def vf_for(part, dur):
    """filter chain turning a source into 1920x1080@60 of length dur."""
    f = []
    sp = part.get("speed", 1.0)
    if sp != 1.0: f.append(f"setpts=PTS/{sp}")
    if part.get("crop") != "none":
        cx = part.get("cropx", 320)          # 2560x1080 source -> 1920 window
        if "pan" in part:                    # slow lateral reframing inside the ultrawide frame: (x0,x1)
            x0, x1 = part["pan"]; f.append(f"crop=1920:1080:'{x0}+({x1}-{x0})*min(t/{dur},1)':0")
        else: f.append(f"crop=1920:1080:{cx}:0")
    if "zoom" in part:                       # punch-in factor on game footage (static)
        z = part["zoom"]; zx, zy = part.get("zoomc", (0.5, 0.5))
        w, h = 1920 / z, 1080 / z
        f.append(f"crop={w:.0f}:{h:.0f}:{(1920-w)*zx:.0f}:{(1080-h)*zy:.0f},scale=1920:1080:flags=lanczos")
    g = GRADE.get(part.get("grade"))
    if g: f.append(g)
    if part.get("fadein"): f.append(f"fade=t=in:st=0:d={part['fadein']}")
    if part.get("fadeout"): f.append(f"fade=t=out:st={dur-part['fadeout']}:d={part['fadeout']}")
    f.append("fps=60,format=yuv420p,setsar=1")
    return ",".join(f)

import hashlib
from config import project_fingerprint
CACHE = SEG + "/cache"; os.makedirs(CACHE, exist_ok=True)
def cached(cmd, out, key_extra=""):
    """run a slow renderer once per distinct command; cmd must contain the placeholder '@OUT'."""
    deps = [c for c in cmd if c.endswith((".py", ".html", ".mjs")) and os.path.exists(c)]


    h = hashlib.sha256((json.dumps(cmd) + key_extra + project_fingerprint()).encode()).hexdigest()[:24]
    c = f"{CACHE}/{h}.mp4"
    if not os.path.exists(c):
        run([x if x != "@OUT" else c + ".tmp.mp4" for x in cmd]); os.rename(c + ".tmp.mp4", c)
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", c, "-vf", "fps=60,format=yuv420p,setsar=1", "-an", *ENC, out])
def gfx_cmd(part, dur, bt, size=None):
    B = lambda b: round(bt(b[0]) + b[1], 3) if isinstance(b, (tuple, list)) else round(bt(b), 3)
    cmd = [sys.executable, ROOT + "/tools/gfx/render.py", part["id"], "--dur", f"{dur:.4f}", "--out", "@OUT"]
    for k, b in part.get("cues", {}).items(): cmd += ["--set", f"{k}={B(b):.3f}"]
    for k, v in part.get("set", {}).items(): cmd += ["--set", f"{k}={v}"]
    J = {}
    if "keys" in part: J["_keys"] = [[B(k[0]), *k[1:]] for k in part["keys"]]
    if "ev" in part: J["_hl"] = [[B(e[0]), B(e[1]), *e[2:]] for e in part["ev"]]
    if J: cmd += ["--json", json.dumps(J)]
    return cmd
def render_part(part, dur, out, sid=None, t0=0.0, total=None):
    """t0 = where this part starts inside its shot; total = shot length (for beat -> time conversion)."""
    kind = part.get("kind", "video")
    bt = lambda b: beat_time(sid, b, total) - t0            # beat index -> seconds inside this part
    if kind == "cam":        # painting camera: keys [(beat, (cx, cy, h)), ...]; white=[(beat0, beat1)] shows the white-disc variant
        keys = [[round(bt(b), 3), *c] for b, c in part["keys"]]
        P = {"_keys": keys, "_white": [[round(bt(a), 3), round(bt(b), 3)] for a, b in part.get("white", [])]}
        cached([sys.executable, ROOT + "/tools/gfx/render.py", "CAM", "--dur", f"{dur:.4f}", "--json", json.dumps(P), "--out", "@OUT"], out); return
    if kind == "gfxr":       # (re-)render a graphics scene to this exact length. cues = {param: beat}, set = {param: value},
        # keys = [(beat, ...)] -> _keys, ev = [(beat0, beat1, ...)] -> _hl   (a beat may be (beat, +seconds))
        cached(gfx_cmd(part, dur, bt), out); return
    if kind == "map":        # tools/map/render.py shot; args = {k: v}; cuts = [beats] -> cuts=t1,t2,..
        cmd = [sys.executable, ROOT + "/tools/map/render.py", part["shot"], "@OUT", f"{dur:.4f}"] + [f"{k}={v}" for k, v in part.get("args", {}).items()]
        if "cuts" in part: cmd.append("cuts=" + ",".join(f"{bt(b):.3f}" for b in part["cuts"]))
        cached(cmd, out)
        if part.get("fadein") or part.get("fadeout"): pass
        return
    if kind == "still":
        run([sys.executable, TOOLROOT + "/build/kb.py", ROOT + "/" + part["src"], out, str(dur), json.dumps(part["kb"]), part.get("ease", "smooth"), str(part.get("fadeout", 0))])
        return
    if kind == "black":
        run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=black:s=1920x1080:r=60:d={dur}", *ENC, out]); return
    src = ROOT + "/" + part["src"]; sp = part.get("speed", 1.0)
    if kind == "split":                      # left: gfx 960x1080, right: game footage cropped to 960x1080
        if "leftr" in part:
            l = out + ".left.mp4"; cached(gfx_cmd(part["leftr"], dur, bt), l)
        else: l = ROOT + "/" + part["left"]
        rsp = part.get("speed", 1.0); rx = part.get("cropx", 800)
        rf = (f"setpts=PTS/{rsp}," if rsp != 1 else "") + f"crop=952:1080:{rx}:0" + ("," + GRADE[part["grade"]] if part.get("grade") else "")
        fc = (f"[0:v]fps=60,crop=952:1080:0:0[l];[1:v]{rf},fps=60[r];color=black:s=1920x1080:r=60[bg];"
              f"[bg][l]overlay=0:0[t];[t][r]overlay=968:0:shortest=0,format=yuv420p[v]")
        run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(part.get("lss", 0)), "-i", l, "-ss", str(part.get("ss", 0)), "-i", src,
             "-filter_complex", fc, "-map", "[v]", "-t", f"{dur:.3f}", *ENC, out]); return
    run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(part.get("ss", 0)), "-i", src, "-vf", vf_for(part, dur), "-t", f"{dur:.3f}", "-an", *ENC, out])

def part_times(sid, dur):
    """start time of every part. A part with 'b' starts at that (fractional) beat; parts without 'b' share the gap
    between the anchored parts around them by weight 'w' (or take fixed 'd' seconds)."""
    parts = EDL[sid]; n = len(parts); st = [None] * (n + 1); st[0] = 0.0; st[n] = dur
    for i, p in enumerate(parts):
        if "b" in p and i > 0: st[i] = beat_time(sid, p["b"], dur)
    i = 0
    while i < n:
        j = i + 1
        while st[j] is None: j += 1
        grp = parts[i:j]; span = st[j] - st[i]
        fixed = sum(p["d"] for p in grp if "d" in p); wsum = sum(p.get("w", 1) for p in grp if "d" not in p) or 1
        t = st[i]
        for k, p in enumerate(grp):
            st[i + k] = t; t += p["d"] if "d" in p else max(0.3, (span - fixed) * p.get("w", 1) / wsum)
        i = j
    f = [round(x * 60) / 60 for x in st]
    return f
def build_segment(sid, dur):
    parts = EDL[sid]; st = part_times(sid, dur)
    files = []
    for i, p in enumerate(parts):
        d = st[i + 1] - st[i]
        if d < 1 / 60: continue
        out = f"{SEG}/{sid}_{i}.mp4"
        if os.path.lexists(out): os.remove(out)
        render_part(p, d, out, sid, st[i], dur); files.append(out)
    lst = f"{SEG}/{sid}.txt"; open(lst, "w").write("".join(f"file '{f}'\n" for f in files))
    seg = f"{SEG}/{sid}.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", seg])
    return seg

def srt_time(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")

def main():
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    T = durations(); segs = []; t = 0.0; srt = []; table = []
    for n, (sid, text) in enumerate(NARR.NARR):
        if only and sid != only: t += T[sid]; continue
        if sid not in EDL: sys.exit(f"no EDL entry for {sid}")
        segp = f"{SEG}/{sid}.mp4"
        signature = hashlib.sha256((project_fingerprint() + sid + json.dumps(EDL[sid], sort_keys=True) + str(T[sid])).encode()).hexdigest()
        stamp = segp + ".sha256"
        reuse = "--reuse" in sys.argv and os.path.exists(segp) and os.path.exists(stamp) and open(stamp).read() == signature
        seg = segp if reuse else build_segment(sid, T[sid])
        open(stamp, "w").write(signature)
        print(f"{sid}: {'reused' if reuse else 'rendered'}", flush=True)
        real = probe(seg); segs.append(seg)
        table.append((sid, t, real))
        if text:
            # guide captions: split the narration into ~12-word chunks spread across the segment
            bl = text.split(" | "); st = BEATS[sid] + [real - 0.3]
            for bi, btxt in enumerate(bl):           # captions follow the picture beats
                words = btxt.split(); chunks = [" ".join(words[i:i + 12]) for i in range(0, len(words), 12)]
                b0 = st[bi] + (0.35 if bi == 0 else 0); per = (st[bi + 1] - b0) / len(chunks)
                for i, c in enumerate(chunks):
                    srt.append(f"{len(srt)+1}\n{srt_time(t + b0 + i*per)} --> {srt_time(t + b0 + (i+1)*per - 0.05)}\n[{sid}{'.' + str(bi) if len(bl) > 1 else ''}] {c}\n")
        t += real
        print(f"{sid:5s} {real:6.2f}s  (total {t/60:5.2f} min)", flush=True)
    if only: print("built", segs); return
    lst = SEG + "/all.txt"; open(lst, "w").write("".join(f"file '{f}'\n" for f in segs))
    clean = OUT + "/film-roughcut.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", "-movflags", "+faststart", clean])
    open(OUT + "/film-guide.srt", "w").write("\n".join(srt))
    json.dump([{"id": a, "start": round(b, 3), "dur": round(c, 3)} for a, b, c in table], open(OUT + "/timeline.json", "w"), indent=1)
    print("wrote", clean, f"{t/60:.2f} min")
    json.dump([{"id": a, "start": round(b, 3), "dur": round(c, 3), "beats": [round(x, 3) for x in BEATS[a]]} for a, b, c in table], open(OUT + "/timeline.json", "w"), indent=1)
    score = OUT + "/film-score.wav"; has_score = os.path.exists(score) and abs(probe(score) - t) < 3.0
    if os.path.exists(score) and not has_score: print("NOTE: the score does not match this cut's length; re-run score/score.py, then assemble.py --reuse")
    audio = None
    if any(narration_audio(sid) for sid, _ in NARR.NARR):
        # narration bed: each shot's narration (starting 0.35 s in), padded with silence to the shot length
        ins = []; fc = []; n = 0
        for sid, st, d in table:
            a = narration_audio(sid)
            if a: ins += ["-i", a]; fc.append(f"[{n}:a]aresample=48000,aformat=channel_layouts=stereo,adelay=350:all=1,apad,atrim=0:{d:.4f},asetpts=N/SR/TB[a{n}]")
            else: ins += ["-f", "lavfi", "-t", f"{d:.4f}", "-i", "anullsrc=r=48000:cl=stereo"]; fc.append(f"[{n}:a]atrim=0:{d:.4f},asetpts=N/SR/TB[a{n}]")
            n += 1
        fc.append("".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1[a]")
        wav = SEG + "/narration_bed.wav"
        run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", ";".join(fc), "-map", "[a]", wav])
        audio = wav
        if has_score:      # voice-referenced balance + loudness master (build/mix.py prints the numbers)
            audio = SEG + "/mix.wav"
            r = subprocess.run([sys.executable, TOOLROOT + "/build/mix.py", wav, score, audio], capture_output=True, text=True)
            if r.returncode: sys.exit("mix failed:\n" + r.stderr[-2000:])
            print(r.stdout, flush=True); open(OUT + "/mix-report.txt", "w").write(r.stdout)
        final = OUT + "/film-final.mp4"
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", clean, "-i", audio, "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", final])
        print("wrote", final)
    elif has_score:
        audio = score; tmp = OUT + "/.rc.mp4"
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", clean, "-i", score, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", tmp])
        os.replace(tmp, clean); print("added the score to", clean)
    if "--guide" in sys.argv:
        g = OUT + "/film-guide.mp4"
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", clean, *(["-i", audio] if audio else []), "-map", "0:v", *(["-map", "1:a", "-c:a", "aac", "-b:a", "192k", "-shortest"] if audio else []), "-vf",
             f"subtitles={OUT}/film-guide.srt:force_style='FontName=DejaVu Sans,FontSize=13,Outline=1,Shadow=0,MarginV=18',scale=1280:720",
             *ENC, g])
        print("wrote", g)
if __name__ == "__main__": main()
