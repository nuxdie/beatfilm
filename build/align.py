#!/usr/bin/env python3
"""align.py — turn one long narration recording into per-shot audio + per-beat timings.

    1. build/transcribe.py <16k wav> narration/words.json          (word timings, faster-whisper)
    2. build/align.py narration/<recording>                        (this file)

Aligns the script (build/narration.py) to the transcript, always preferring the LAST reading of every line (retakes come
after the fluffed attempt), trims pauses longer than MAXGAP, writes narration/<ID>.wav (cleaned and levelled) and
build/timings.json = {ID: [length of every picture beat]}, which is what assemble.py and score/score.py are timed from.
"""
import sys, os, re, json, subprocess, importlib.util, hashlib
import numpy as np
from config import ROOT, TMP, SEG, TOOLROOT, ENC, CFG
sp = importlib.util.spec_from_file_location("narr", ROOT + "/build/narration.py"); N = importlib.util.module_from_spec(sp); sp.loader.exec_module(N)
sp = importlib.util.spec_from_file_location("edl", ROOT + "/build/edl.py"); EDLM = importlib.util.module_from_spec(sp); sp.loader.exec_module(EDLM)
LANG = sys.argv[sys.argv.index("--lang") + 1] if "--lang" in sys.argv else "en"      # --lang ru: a second-language track (clips only; the cut keeps its timings)
if LANG != "en":
    sp = importlib.util.spec_from_file_location("narr2", f"{ROOT}/build/narration_{LANG}.py"); N2 = importlib.util.module_from_spec(sp); sp.loader.exec_module(N2)
    _d = dict(getattr(N2, "NARR_" + LANG.upper())); N.NARR = [(sid, _d.get(sid, "")) for sid, _ in N.NARR]
SUF = "" if LANG == "en" else "-" + LANG; OUTD = ROOT + "/narration" + ("" if LANG == "en" else "/" + LANG); os.makedirs(OUTD, exist_ok=True)
TIMINGS = ROOT + "/build/timings" + ("" if LANG == "en" else "_" + LANG) + ".json"
LEAD = 0.35        # narration starts this long after the cut
TAIL = 0.55        # and the shot holds this long after the last word
MAXGAP = 0.80      # longest pause kept inside a shot
PRE, POST = 0.10, 0.16   # padding around a phrase when a pause is trimmed
PIC = 0.12         # the picture changes this long before the first word of a beat
SAME = {"16": "sixteen", "colors": "colours", "gray": "grey", "traveled": "travelled", "realized": "realised", "recognized": "recognised", "ok": "okay"}
def norm(w):
    w = re.sub(r"[^a-zа-я0-9]", "", w.lower().replace("ё", "е").replace("’", "").replace("'", "")); return SAME.get(w, w)

words = [w for w in json.load(open(ROOT + "/narration/words" + SUF + ".json")) if norm(w[2])]
tw = [norm(w[2]) for w in words]
script = []          # (shot, beat, word)
for sid, text in N.NARR:
    for bi, btxt in enumerate(text.split(" | ") if text else []):
        for w in btxt.replace('-', ' ').split():       # the recogniser writes 'кто -то' / 'in -game' as two tokens
            if norm(w): script.append((sid, bi, norm(w)))
sw = [s[2] for s in script]; n, m = len(sw), len(tw)
def lcs_late(a, lo, hi):
    """align script words a to transcript words tw[lo:hi]; every match is taken as late as possible. -> {i: j}"""
    b = tw[lo:hi]; n_, m_ = len(a), len(b); dp = np.zeros((n_ + 1, m_ + 1), np.int32); ba = np.array([hash(x) for x in b])
    for i in range(1, n_ + 1):
        dp[i, 1:] = np.maximum.accumulate(np.maximum(dp[i - 1, 1:], dp[i - 1, :-1] + (ba == hash(a[i - 1]))))
    out = {}; i, j = n_, m_
    while i > 0 and j > 0:
        if a[i - 1] == b[j - 1] and dp[i, j] == dp[i - 1, j - 1] + 1: out[i - 1] = lo + j - 1; i -= 1; j -= 1
        elif dp[i, j] == dp[i - 1, j]: i -= 1          # skip an unrecognised script word before giving up transcript words
        else: j -= 1
    return out
# shots are read in order and a retake always follows the fluffed attempt, so work backwards from the end of the
# recording: each shot is looked for only in the stretch just before the shot that follows it
OK = 0.88 if LANG == "en" else 0.62      # share of a paragraph's words that must be recognised (other languages are transcribed less exactly)
RUNS = {}; ENDS = {}; LT = {}; bound = m
for sid, text in reversed(N.NARR):
    if not text: continue
    idx = [k for k, s_ in enumerate(script) if s_[0] == sid]; a = [sw[k] for k in idx]
    hi = bound; mm = []; run = []
    for attempt in range(40):
        for widen in (1.35, 2.5, 6.0, 1e6):
            lo = max(0, hi - int(len(a) * widen) - 12); mt = lcs_late(a, lo, hi)
            mm = sorted((idx[i], j) for i, j in mt.items())
            if not mm: continue
            run = [mm[-1]]
            for q in reversed(mm[:-1]):
                if run[0][1] - q[1] <= 7: run.insert(0, q)
                else: break
            if len(run) / len(idx) >= OK: break
        if len(run) / len(idx) >= OK: break
        if not run: raise ValueError(f"{sid}: no matching transcript words")
        hi = run[-1][1]                    # a stray phrase from another paragraph: look further back
    if not mm or len(run) / len(idx) < OK:
        raise ValueError(f"{sid}: no sufficiently complete reading found; inspect transcript or add an override")
    LT[sid] = (run[0][0] - idx[0], idx[-1] - run[-1][0])
    RUNS[sid] = run; bound = run[0][1]
order = [sid for sid, text in N.NARR if text]
for q, sid in enumerate(order):        # unrecognised words at either end still belong to the clip, but never another shot's words
    run = RUNS[sid]; lead, trail = LT[sid]
    prev_end = RUNS[order[q - 1]][-1][1] if q else -1; next_start = RUNS[order[q + 1]][0][1] if q + 1 < len(order) else m
    j0 = run[0][1]; j1 = run[-1][1]
    for _ in range(lead + 2 if lead else 0):
        if j0 - 1 > prev_end and words[j0][0] - words[j0 - 1][1] < 0.5: j0 -= 1
    for _ in range(trail + 2 if trail else 0):
        if j1 + 1 < next_start and words[j1 + 1][0] - words[j1][1] < 0.5: j1 += 1
    ENDS[sid] = (j0, j1)
print(f"script {n} words, transcript {m} words")
if "--runs" in sys.argv:
    for sid in order: print(sid, RUNS[sid][0][1], RUNS[sid][-1][1], f"{len(RUNS[sid])}/{sum(1 for s_ in script if s_[0] == sid)}", words[RUNS[sid][0][1]][0])
    sys.exit()

src = sys.argv[1]; clean = TMP + "/narr_clean" + SUF + ".wav"
h = hashlib.sha256()
with open(src, 'rb') as stream:
    for chunk in iter(lambda: stream.read(1024 * 1024), b''): h.update(chunk)
h.update(open(__file__, 'rb').read())
clean_signature = h.hexdigest(); clean_stamp = clean + '.sha256'
if not os.path.exists(clean) or not os.path.exists(clean_stamp) or open(clean_stamp).read() != clean_signature:
    pre = "highpass=f=75,afftdn=nr=10:nf=-48,acompressor=threshold=-30dB:ratio=2.5:attack=8:release=160"
    r = subprocess.run(["ffmpeg", "-nostdin", "-i", src, "-af", pre + ",ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1]); gain = -17.0 - I
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", src, "-af", f"{pre},volume={gain:.2f}dB,alimiter=limit=0.84:attack=3:release=80,aresample=48000", "-ac", "1", clean], check=True)
    open(clean_stamp, "w").write(clean_signature)
    print(f"cleaned: measured {I:.1f} LUFS, gain {gain:+.1f} dB")
import soundfile as sf
audio, sr = sf.read(clean, dtype="float32"); assert sr == 48000

import pyloudnorm as pyln
METER = pyln.Meter(48000); LEVELS = []
HOP = int(0.02 * sr); nf = len(audio) // HOP
edb = 10 * np.log10(np.mean(audio[:nf * HOP].reshape(nf, HOP) ** 2, axis=1) + 1e-12)
THR = np.percentile(edb, 95) - 21          # well above the room noise (about -43 dB here)
VO = edb > THR
SPAN = {}
START_AT = CFG.get("alignment_starts", {}).get(LANG, {})      # 'I should say where I found it' is read twice in a row; use the second
print(f"speech level {np.percentile(edb, 95):.1f} dB, floor {np.percentile(edb, 10):.1f} dB, voice threshold {THR:.1f} dB")
timings = {}; report = []
for sid, text in N.NARR:
    if not text: continue
    idx = [k for k, s in enumerate(script) if s[0] == sid]; run = RUNS[sid]
    cov = len(run) / len(idx)
    j0, j1 = ENDS[sid]
    # Cut on the audio itself, not on the recogniser's word times (those drift across long pauses):
    # the shot runs from its first to its last word, widened to the edges of the speech around them,
    # and every silence longer than MAXGAP inside it is shortened to MAXGAP.
    q_ = order.index(sid)
    lo_t = SPAN[order[q_ - 1]][1] if q_ else 0.0                       # never reach into the previous shot
    hi_t = words[ENDS[order[q_ + 1]][0]][0] + 0.05 if q_ + 1 < len(order) else len(audio) / sr
    A = max(lo_t, words[j0][0]); B = min(hi_t, max(words[j1][1], A + 0.2))
    if sid in START_AT: lo_t = A = START_AT[sid]          # hand-set start (source seconds) where a repeat could not be told apart automatically
    ia, ib = int((A + 0.02 if sid in START_AT else max(A, words[j0][1] - 0.08)) * sr / HOP), int(B * sr / HOP)     # anchor on the END of the first word: its start time is often early
    while ia > int(lo_t * sr / HOP) and VO[max(0, ia - 13):ia].any(): ia -= 1          # back to the start of the speech we are in (0.26 s of quiet ends it)
    lim = int(hi_t * sr / HOP)
    while ib < min(lim, len(VO) - 1) and VO[ib:ib + 15].any(): ib += 1                   # forward to the end of the last word
    vo = VO[ia:ib]; edges = np.flatnonzero(np.diff(np.concatenate([[0], vo.astype(np.int8), [0]])))
    regs = [((ia + edges[k]) * HOP / sr, (ia + edges[k + 1]) * HOP / sr) for k in range(0, len(edges), 2)]       # voiced regions (s)
    if not regs: regs = [(A, B)]
    pieces = []; tmap = []; out_t = 0.0; seg_start = max(lo_t, regs[0][0] - PRE)
    for k, (r0, r1) in enumerate(regs):
        nxt = regs[k + 1][0] if k + 1 < len(regs) else None
        if nxt is None:
            b = min(r1 + 0.28, hi_t); pieces.append((seg_start, b)); tmap.append((seg_start, out_t)); out_t += b - seg_start
        elif nxt - r1 > MAXGAP:
            b = r1 + (MAXGAP - PRE); pieces.append((seg_start, b)); tmap.append((seg_start, out_t)); out_t += b - seg_start; seg_start = nxt - PRE
    SPAN[sid] = (pieces[0][0], pieces[-1][1])
    def out_time(t):
        """source time -> time in the trimmed clip; a time that fell inside a removed pause snaps to the next kept speech."""
        for k in range(len(pieces)):
            if t < pieces[k][0]: return tmap[k][1] + PRE
            if t <= pieces[k][1]: return tmap[k][1] + (t - pieces[k][0])
        return out_t
    keep = list(range(j0, j1 + 1))
    lost = [f"{words[j][2]}@{words[j][0]:.1f}" for j in keep if not any(p0 <= (words[j][0] + words[j][1]) / 2 <= p1 for p0, p1 in pieces)]
    if lost: print(f"  {sid}: words outside the kept audio: {' '.join(lost)}")
    f = int(0.012 * sr); chunks = []
    for a_, b_ in pieces:
        c = audio[int(a_ * sr):int(b_ * sr)].copy(); c[:f] *= np.linspace(0, 1, f); c[-f:] *= np.linspace(1, 0, f); chunks.append(c)
    clip = np.concatenate(chunks)
    try:                                   # every paragraph at the same loudness (the reading drifts over twenty minutes)
        lc = METER.integrated_loudness(np.pad(clip, (0, max(0, int(0.5 * sr) - len(clip)))))
        gdb = max(-5.0, min(5.0, -17.0 - lc)) if lc > -60 else 0.0
    except Exception: gdb = 0.0
    clip = np.clip(clip * 10 ** (gdb / 20), -0.94, 0.94); LEVELS.append((sid, gdb))
    sf.write(f"{OUTD}/{sid}.wav", clip, sr, subtype="PCM_16")
    speech = len(clip) / sr
    # beat starts: first matched word of each beat (interpolated from neighbours when it was not recognised)
    nb = len(text.split(" | ")); bst = [0.0]
    for b in range(1, nb):
        first = min(k for k in idx if script[k][1] == b)
        after = [x for x in run if x[0] >= first]
        if after and after[0][0] == first: t = out_time(words[after[0][1]][0])
        elif after:                                   # first word unmatched: back off by an average word length per missing word
            t = out_time(words[after[0][1]][0]) - 0.28 * (after[0][0] - first)
        else: t = speech
        bst.append(max(bst[-1] + 0.3, LEAD + t - PIC))
    total = LEAD + speech + TAIL + EDLM.EXTRA.get(sid, 0)
    timings[sid] = [round(y - x, 3) for x, y in zip(bst, bst[1:] + [total])]
    said = " ".join(words[j][2] for j in keep)
    report.append(f"[{sid}] {words[j0][0]:7.1f}-{words[j1][1]:7.1f}s  speech {speech:5.1f}s  coverage {cov:4.0%}  cuts {len(pieces) - 1}\n    {said}\n")
    if cov < 0.9: print(f"  CHECK {sid}: only {cov:.0%} of the script words were recognised in the chosen reading")
json.dump(timings, open(TIMINGS, "w"), indent=1)
open(ROOT + "/narration/alignment-report" + SUF + ".txt", "w").write("\n".join(report))
tot = sum(sum(v) for v in timings.values()) + sum(N.FIXED.values())
print("per-clip level corrections (dB):", " ".join(f"{a}{b:+.1f}" for a, b in LEVELS))
print(f"wrote {len(timings)} clips, build/timings.json; video length will be {tot / 60:.2f} min")
if "--debug" in sys.argv:
    sid = sys.argv[sys.argv.index("--debug") + 1]; idx = [k for k, s_ in enumerate(script) if s_[0] == sid]; d = dict(RUNS[sid])
    print(" ".join(f"{sw[k]}:{d.get(k, '-')}" for k in idx))

# ---- second look at every clip's start: a false start the recogniser merged into the real one ("I should say... I should say
# where I found it") shows up when the clip itself is transcribed. If the script's first words occur twice, keep the last.
if "--no-refine" not in sys.argv:
    from faster_whisper import WhisperModel
    wm = WhisperModel("medium.en" if LANG == "en" else "medium", device="cpu", compute_type="int8", cpu_threads=10)
    for sid in order:
        clip, _ = sf.read(f"{OUTD}/{sid}.wav", dtype="float32")
        c16 = np.interp(np.arange(0, len(clip), 3.0), np.arange(len(clip)), clip).astype(np.float32)       # 48k -> 16k (speech only, good enough)
        segs, _ = wm.transcribe(c16, word_timestamps=True, vad_filter=True, condition_on_previous_text=False, beam_size=5, language=LANG)
        cw = [[w.start, w.end, norm(w.word)] for s_ in segs for w in s_.words if norm(w.word)]
        a = [s_[2] for s_ in script if s_[0] == sid]; b = [x[2] for x in cw]
        k = min(5, len(a)); head = a[:k]
        occ = [j for j in range(len(b) - k + 1) if sum(x == y for x, y in zip(b[j:j + k], head)) >= k - 1]      # places the opening words are said
        if len(occ) >= 2 and occ[-1] <= len(b) - len(a) * 0.8:           # said again later, and the rest of the paragraph still follows
            e0 = cw[occ[-1]][1]; nh = len(clip) // HOP
            ce = 10 * np.log10(np.mean(clip[:nh * HOP].reshape(nh, HOP) ** 2, axis=1) + 1e-12) > THR
            i = int(max(0, e0 - 0.08) * sr / HOP)
            while i > 0 and ce[max(0, i - 13):i].any(): i -= 1
            cut = max(0.0, i * HOP / sr - PRE)
            if cut > 0.4:
                clip = clip[int(cut * sr):].copy(); clip[:f] *= np.linspace(0, 1, f); sf.write(f"{OUTD}/{sid}.wav", clip, sr, subtype="PCM_16")
                tm = timings[sid]; first = tm[0] - cut
                if first < 0.6:                                    # the first beat was inside the removed part: give its time to the next one
                    if len(tm) > 1: tm[1] += first - 0.6
                    first = 0.6
                tm[0] = round(first, 3); print(f"  {sid}: removed a {cut:.1f}s false start ({' '.join(b[:occ[-1]])!r})")
    json.dump(timings, open(TIMINGS, "w"), indent=1)
    print(f"after refining: {(sum(sum(v) for v in timings.values()) + sum(N.FIXED.values())) / 60:.2f} min")
