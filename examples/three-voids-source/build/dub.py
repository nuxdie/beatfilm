#!/usr/bin/env python3
"""dub.py <lang> — fit a second-language narration onto the finished cut and mix it over the score.

Needs narration/<lang>/<ID>.wav and build/timings_<lang>.json (from align.py --lang <lang>) and out/timeline.json (the cut).
Every paragraph must fit its shot. A paragraph that is too long is sped up a little (TEMPO_MAX at most, pitch kept);
sentences that begin on a picture beat are then moved onto that beat by lengthening the pause before them, never by
cutting inside a phrase.  Writes out/three-voids-audio-<lang>.wav (+ .m4a) and out/three-voids-final-<lang>.mp4.
"""
import sys, os, json, subprocess, itertools, importlib.util
import numpy as np, soundfile as sf
ROOT = "/home/n/Videos/three-voids"; SEG = "/home/n/Games/three-voids-raw/seg"; OUT = ROOT + "/out"; TMP = "/home/n/Games/three-voids-raw/tmp"
LANG = sys.argv[1]; SR = 48000
LEAD, PIC, TEMPO_MAX, END_GAP, PAUSE_MIN = 0.35, 0.12, 1.13, 0.15, 0.32
TL = json.load(open(OUT + "/timeline.json")); T2 = json.load(open(f"{ROOT}/build/timings_{LANG}.json"))
total = TL[-1]["start"] + TL[-1]["dur"]; bed = np.zeros(int((total + 1) * SR), np.float32)
carry = 0.0; rows = []
for q, x in enumerate(TL):
    sid = x["id"]; p = f"{ROOT}/narration/{LANG}/{sid}.wav"
    if not os.path.exists(p): carry = 0.0; continue
    clip, sr = sf.read(p, dtype="float32"); assert sr == SR
    d = len(clip) / SR; start = max(LEAD, carry + 0.12)                 # carry: the previous paragraph ran a little into this shot
    nxt_has = q + 1 < len(TL) and os.path.exists(f"{ROOT}/narration/{LANG}/{TL[q + 1]['id']}.wav")
    room = x["dur"] - start - END_GAP; cutmap = []
    if d > room:                       # too long: first take the air out of the pauses (down to PAUSE_MIN), only then speed it up
        H = int(0.02 * SR); nf = len(clip) // H; e = 10 * np.log10(np.mean(clip[:nf * H].reshape(nf, H) ** 2, axis=1) + 1e-12); vo = e > np.percentile(e, 95) - 21
        ed = np.flatnonzero(np.diff(np.concatenate([[1], vo.astype(np.int8), [1]])))       # silent runs
        sil = [(ed[k] * H / SR, ed[k + 1] * H / SR) for k in range(0, len(ed) - 1, 2) if (ed[k + 1] - ed[k]) * H / SR > PAUSE_MIN + 0.06]
        spare = sum(b - a - PAUSE_MIN for a, b in sil); want = min(spare, d - room); frac = want / spare if spare > 0 else 0
        keep = []; pos0 = 0.0
        for a_, b_ in sil:
            rm = (b_ - a_ - PAUSE_MIN) * frac; mid = (a_ + b_) / 2; keep.append((pos0, mid - rm / 2)); cutmap.append((mid, rm)); pos0 = mid + rm / 2
        keep.append((pos0, d)); f = int(0.006 * SR); parts = []
        for a_, b_ in keep:
            c = clip[int(a_ * SR):int(b_ * SR)].copy()
            if len(c) > 2 * f: c[:f] *= np.linspace(0, 1, f); c[-f:] *= np.linspace(1, 0, f)
            parts.append(c)
        clip = np.concatenate(parts); d = len(clip) / SR
    tempo = min(TEMPO_MAX, max(1.0, d / room)); lvl0 = float(np.sqrt(np.mean(clip ** 2)))
    if tempo > 1.004:
        t_in, t_out = TMP + "/dub_in.wav", TMP + "/dub_out.wav"; sf.write(t_in, clip, SR)
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", t_in, "-af", f"rubberband=tempo={tempo:.4f}:transients=smooth:formant=preserved", t_out], check=True)
        clip, _ = sf.read(t_out, dtype="float32"); d = len(clip) / SR
        clip *= lvl0 / (float(np.sqrt(np.mean(clip ** 2))) + 1e-9)          # the stretcher changes the level a little; put it back
    # sentence starts in the clip (seconds) and the picture beats they belong to
    bs = [b - LEAD + PIC for b in itertools.accumulate(T2[sid])][:-1]
    bs = [(b - sum(rm for mid, rm in cutmap if mid < b)) / tempo for b in bs]
    eb = x["beats"][1:]
    H = int(0.02 * SR); nf = len(clip) // H; e = 10 * np.log10(np.mean(clip[:nf * H].reshape(nf, H) ** 2, axis=1) + 1e-12); thr = np.percentile(e, 95) - 21
    segs = []; a0 = 0.0; target = [None]
    for b, ebt in zip(bs, eb):
        i = int(b * SR / H)
        quiet = [k for k in range(max(1, i - 12), min(nf - 1, i + 4)) if e[k] < thr and e[k - 1] < thr and e[k + 1] < thr]      # a real pause at this boundary?
        if quiet and b - a0 > 0.5 and len(bs) < 40:
            cut = quiet[len(quiet) // 2] * H / SR; segs.append((a0, cut)); a0 = cut; target.append(ebt)
    segs.append((a0, d))
    pos = start; placed = []; rem = [sum(s1 - s0 for s0, s1 in segs[i:]) for i in range(len(segs))]
    limit = x["dur"] - END_GAP + (0.3 if nxt_has else 0.0)             # may lean 0.3 s into the next shot at most
    for i, (s0, s1) in enumerate(segs):
        st = pos if target[i] is None else max(pos, target[i] + PIC - 0.02)
        st = max(pos, min(st, limit - rem[i]))                           # never push later than still fits
        piece = clip[int(s0 * SR):int(s1 * SR)].copy(); f = int(0.008 * SR)
        if i: piece[:f] *= np.linspace(0, 1, f)
        if i < len(segs) - 1: piece[-f:] *= np.linspace(1, 0, f)
        k0 = int((x["start"] + st) * SR); bed[k0:k0 + len(piece)] += piece[:len(bed) - k0]; placed.append(st); pos = st + (s1 - s0)
    over = pos - x["dur"]; carry = max(0.0, over)
    drift = [placed[i] - (target[i] + PIC) for i in range(1, len(segs))]
    rows.append((sid, tempo, len(segs), max(drift) if drift else 0.0, over))
sf.write(SEG + f"/narration_bed_{LANG}.wav", bed, SR, subtype="PCM_24")
print("shot  tempo  parts  latest-sentence-vs-picture(s)  end-vs-shot-end(s)")
for sid, tempo, n, dr, over in rows: print(f"{sid:5s} {tempo:5.2f}  {n:3d}   {dr:6.2f}   {over:6.2f}" + ("   <-- runs into the next shot" if over > 0 else ""))
print(f"sped up: {sum(1 for r in rows if r[1] > 1.004)} of {len(rows)} paragraphs, most {max(r[1] for r in rows):.2f}x")
audio = f"{OUT}/three-voids-audio-{LANG}.wav"
r = subprocess.run([sys.executable, ROOT + "/build/mix.py", SEG + f"/narration_bed_{LANG}.wav", OUT + "/three-voids-score.wav", audio], capture_output=True, text=True)
if r.returncode: sys.exit(r.stderr[-2000:])
print(r.stdout); open(f"{OUT}/mix-report-{LANG}.txt", "w").write(r.stdout)
dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", OUT + "/three-voids-final.mp4"], capture_output=True, text=True).stdout.strip()
subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", audio, "-t", dur, "-c:a", "aac", "-b:a", "256k", f"{OUT}/three-voids-audio-{LANG}.m4a"], check=True)
subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", OUT + "/three-voids-final.mp4", "-i", f"{OUT}/three-voids-audio-{LANG}.m4a", "-map", "0:v", "-map", "1:a", "-c", "copy", "-shortest", "-movflags", "+faststart",
                f"{OUT}/three-voids-final-{LANG}.mp4"], check=True)
print("wrote", f"{OUT}/three-voids-audio-{LANG}.m4a", "and", f"{OUT}/three-voids-final-{LANG}.mp4")
