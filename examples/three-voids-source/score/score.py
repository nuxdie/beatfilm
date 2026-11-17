#!/usr/bin/env python3
"""Three Voids — the score. Original music, written as code and rendered to out/three-voids-score.wav.

    /home/n/Games/three-voids-raw/musiclibs/venv/bin/python score/score.py [--stems]

The score follows the edit, not the clock: every cue is placed with at("SHOT", beat), read from the same shot and
beat timings the picture is cut to (build/narration.py + build/timings.json). Change the timings, re-run, and the
music moves with the picture.

Three ideas, one per void:
  the painting  — an upright piano on a cassette (C418-like broken chords, D major). Its theme is a question that
                  stops one note short of home; the missing note is the black circle.
  the server    — the same tape, warmer and busier for the museum and the bases (pad, sine lead, music box),
                  then a low drone, wind and a road-like pulse for spawn and the highways.
  the prompt    — no tape, no piano: one clean sine "cursor" pulse at the caret's own rate (1.06 s) and glass bells.
                  The machine's answer is a fast, pretty arpeggio (scenery). When the answer turns out to be a
                  self-portrait, the machine's voice plays the piano's theme, and the missing note finally sounds.
  The ending asks the question again and leaves the note out.
"""
import sys, os, math, random, importlib.util
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from engine import *          # noqa
import engine as E

_argv, sys.argv = sys.argv, [sys.argv[0]]
_sp = importlib.util.spec_from_file_location("asm", str(ROOT / "build/assemble.py")); A = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(A)
sys.argv = _argv
DUR = A.durations(); START = {}; _t = 0.0
for _sid, _ in A.NARR.NARR: START[_sid] = _t; _t += DUR[_sid]
TOTAL = _t
def at(sid, beat=0.0, off=0.0):
    """absolute time of a (fractional) narration beat of a shot."""
    return START[sid] + A.beat_time(sid, beat, DUR[sid]) + off
def end(sid): return START[sid] + DUR[sid]
LENGTH = TOTAL + 6.0
rng = random.Random(2022); nprng = np.random.default_rng(2022)

# ---------------------------------------------------------------- material
CH = {  # name: (arpeggio pool low -> high, pad voicing, sub)
    "D":     (ns("D2 A2 E3 F#3 A3 D4"), ns("F#3 A3 D4 E4"), n("D2")),
    "A/C#":  (ns("C#2 A2 E3 A3 B3 E4"), ns("E3 A3 B3 C#4"), n("C#2")),
    "Bm7":   (ns("B1 F#2 D3 A3 B3 D4"), ns("D3 F#3 A3 B3"), n("B1")),
    "Gmaj9": (ns("G1 D2 B2 F#3 A3 B3"), ns("F#3 A3 B3 D4"), n("G1")),
    "Asus":  (ns("A1 E2 B2 D3 E3 A3"), ns("E3 A3 B3 D4"), n("A1")),
    "Em9":   (ns("E2 B2 F#3 G3 B3 D4"), ns("G3 B3 D4 F#4"), n("E2")),
    "F#m7":  (ns("F#2 C#3 E3 A3 C#4 E4"), ns("E3 A3 C#4 E4"), n("F#2")),
    "D/F#":  (ns("F#2 D3 A3 D4 E4 A4"), ns("F#3 A3 D4 E4"), n("F#2")),
    "Dadd9": (ns("D2 A2 E3 A3 D4 E4"), ns("A3 D4 E4 A4"), n("D2")),
    # the dark side (spawn)
    "Dm9":   (ns("D2 A2 E3 F3 A3 D4"), ns("F3 A3 C4 E4"), n("D2")),
    "Bbmaj7": (ns("Bb1 F2 D3 A3 C4 D4"), ns("F3 A3 Bb3 D4"), n("Bb1")),
    "Gm9":   (ns("G1 D2 Bb2 F3 A3 Bb3"), ns("F3 A3 Bb3 D4"), n("G1")),
    "Asus4": (ns("A1 E2 A2 D3 E3 A3"), ns("E3 A3 D4 E4"), n("A1")),
    "Eb":    (ns("Eb2 Bb2 G3 Bb3 D4 G4"), ns("G3 Bb3 D4 F4"), n("Eb2")),
}
# the theme: a question (4 bars) that hangs on E, and the answer (4 bars) that only arrives late in the film
Q = [[(0, 2, "F#5"), (2, 1, "A5"), (3, 1, "E5")],
     [(0, 3, "D5")],
     [(0, 1, "B4"), (1, 1, "D5"), (2, 2, "F#5")],
     [(0, 3, "E5")]]
QP = ["D", "A/C#", "Bm7", "Gmaj9"]
ANS = [[(0, 2, "F#5"), (2, 1, "A5"), (3, 1, "B5")],
       [(0, 3, "A5"), (3, 1, "F#5")],
       [(0, 1, "G5"), (1, 1, "F#5"), (2, 2, "E5")],
       [(0, 4, "D5")]]
AP = ["D", "Bm7", "Gmaj9", "D"]            # bar 3 is Gmaj9 with Asus on beat 3
B_MEL = [[(0, 2, "D5"), (2, 1, "F#5"), (3, 1, "E5")],
         [(0, 3, "C#5"), (3, 1, "A4")],
         [(0, 1, "B4"), (1, 1, "D5"), (2, 2, "A5")],
         [(0, 4, "F#5")],
         [(0, 2, "G5"), (2, 2, "B4")],
         [(0, 2, "A4"), (2, 1, "C#5"), (3, 1, "E5")],
         [(0, 4, "F#5")],
         [(0, 2, "E5"), (2.5, 1.5, "D5")]]
BP = ["Bm7", "F#m7", "Gmaj9", "D/F#", "Em9", "F#m7", "Gmaj9", "Asus"]
# the museum tune (G Lydian side of the same scale)
M_MEL = [[(0, 3, "B4"), (3, 1, "D5")],
         [(0, 4, "A4")],
         [(0, 2, "G4"), (2, 2, "B4")],
         [(0, 3, "F#4"), (3, 1, "A4")],
         [(0, 3, "B4"), (3, 1, "D5")],
         [(0, 2, "F#5"), (2, 2, "D5")],
         [(0, 2, "E5"), (2, 1, "D5"), (3, 1, "B4")],
         [(0, 4, "A4")]]
MP = ["Gmaj9", "D/F#", "Em9", "Bm7", "Gmaj9", "D/F#", "Em9", "Asus"]

P_FULL = [0, 1, 2, 3, 4, 3, 2, 1]
P_RISE = [0, 1, 2, 3, 5, 4, 3, 2]
P_SPARSE = [0, None, 2, 3, None, 4, None, None]
P_HALF = [0, None, None, None, 2, None, 3, None]
P_ONE = [0, None, None, None, None, None, None, None]


class Sec:
    """a stretch of bars fitted exactly between two picture times."""
    def __init__(s, t0, t1, bpm, meter=4, bars=None):
        s.n = bars or max(1, round((t1 - t0) / (meter * 60 / bpm))); s.bl = (t1 - t0) / (s.n * meter); s.t0 = t0; s.t1 = t1; s.meter = meter
        s.bpm = 60 / s.bl
    def tb(s, bar, beat=0.0): return s.t0 + (bar * s.meter + beat) * s.bl
    def bar_at(s, t): return (t - s.t0) / (s.bl * s.meter)


# ---------------------------------------------------------------- tracks
up = Piano(UPRIGHT); gr = Piano(GRAND)
T = dict(pad=[], dark=[], lead=[], mach=[], bells=[], box=[], sub=[], pluck=[], pulse=[], swell=[], glass=[])
PINGS = [[] for _ in range(6)]
def jit(sd=0.010): return float(nprng.normal(0, sd))
def pnote(p, s, d, vel, both=False, inst=None):
    s = s + jit(); v = vel + rng.randint(-3, 3); (inst or up).note(p, s, s + d, v)
    if both: gr.note(p, s, s + d, v - 4)
def pedal(sec, bar): up.pedal(sec.tb(bar) + 0.03, sec.tb(bar + 1) - 0.02); gr.pedal(sec.tb(bar) + 0.03, sec.tb(bar + 1) - 0.02)
def arp(sec, bar, chord, pattern, vel=34, low=True):
    pool = CH[chord][0]
    for i, k in enumerate(pattern):
        if k is None: continue
        t0 = sec.tb(bar, i * 0.5)
        pnote(pool[k], t0, sec.tb(bar + 1) - t0 + 0.3, vel + (6 if i == 0 else 2 if i == 4 else 0) - (i % 2) * 3, both=low and k <= 1)
    pedal(sec, bar)
def melody(sec, bar0, mel, vel=46, octave=False, lag=0.018, up8=0, track=None, amp=0.5, bars=None):
    """track=None: the upright. track='lead'/'mach'/'box'/'bells': a synth voice."""
    for i, notes in enumerate(mel if bars is None else mel[:bars]):
        for b, d, nm in notes:
            t0 = sec.tb(bar0 + i, b) + lag; t1 = sec.tb(bar0 + i, b + d); p = n(nm) + up8
            if track is None:
                pnote(p, t0, t1 - t0 + 0.25, vel + (4 if b == 0 else 0))
                if octave: pnote(p - 12, t0 + 0.012, t1 - t0 + 0.25, vel - 12)
            elif track in ("box", "bells"): T[track].append((p, t0, t1 - t0, amp * (1.1 if b == 0 else 0.9)))
            else: T[track].append((p, t0 + 0.02, t1 - 0.03, amp))
def padbar(sec, bar, chord, amp=0.5, bars=1, track="pad"):
    for p in CH[chord][1]: T[track].append((p, sec.tb(bar) - 0.06, sec.tb(bar + bars) + 0.1, amp))
def subbar(sec, bar, chord, amp=0.5, bars=1): T["sub"].append((CH[chord][2] + (12 if CH[chord][2] < 36 else 0), sec.tb(bar), sec.tb(bar + bars) - 0.05, amp))
def knocks(t, vel=52, gap=1.15, notes=("D3", "A2", "D2")):
    """the three-note figure: three low notes, each lower than the last."""
    for i, nm in enumerate(notes):
        gr.note(n(nm), t + i * gap, t + i * gap + 5.0, vel - 4 * i); up.note(n(nm) + 12, t + i * gap + 0.01, t + i * gap + 4.0, vel - 14 - 4 * i)
def pulse(t0, t1, period=1.06, pitch="D6", amp=0.5, fade_in=0.0, fade_out=0.0):
    """the cursor: one soft sine blip per caret blink."""
    k = 0; t = t0
    while t < t1 - 0.05:
        a = amp * (min(1, (t - t0) / fade_in) if fade_in else 1) * (min(1, (t1 - t) / fade_out) if fade_out else 1)
        T["pulse"].append((n(pitch), t, t + 0.05, max(0.02, a))); k += 1; t = t0 + k * period
PENT = ns("D4 E4 F#4 A4 B4 D5 E5 F#5 A5 B5 D6 E6 F#6 A6")
def swarm(t0, t1, n0=0.4, n1=7.0, amp0=0.25, amp1=0.6, seed=1, hi=None):
    """the prompt, multiplied: pings arriving faster and faster, spread across the stereo field."""
    r = random.Random(seed); t = t0
    while t < t1:
        u = (t - t0) / (t1 - t0); rate = n0 * (n1 / n0) ** u
        pool = PENT[:int(5 + u * (len(PENT) - 5))] if hi is None else PENT[:hi]
        PINGS[r.randrange(6)].append((r.choice(pool), t, 0.3, (amp0 + (amp1 - amp0) * u) * r.uniform(0.6, 1.0)))
        t += r.expovariate(rate)
def run(t0, t1, chords, bpm=132, amp=0.5, updown=True, octaves=2, fade=0.0):
    """the machine's scenery: an even, pretty sixteenth-note arpeggio that starts instantly."""
    step = 60 / bpm / 4; k = 0; t = t0; nb = (t1 - t0) / len(chords)
    while t < t1 - 0.01:
        ch = chords[min(len(chords) - 1, int((t - t0) / nb))]; pool = sorted(set([p + 12 for p in CH[ch][0][1:]] + [p + 24 for p in CH[ch][0][2:]]))
        seq = pool + pool[-2:0:-1] if updown else pool
        a = amp * (1.0 if k % 4 == 0 else 0.72) * (min(1, (t1 - t) / fade) if fade else 1)
        T["pluck"].append((seq[k % len(seq)], t, t + step * 0.9, a)); k += 1; t = t0 + k * step
def thud(t, vel=96):
    for nm in ("D1", "A1", "D2"): gr.note(n(nm), t, t + 9, vel)
    gr.note(n("Eb2"), t + 0.02, t + 6, vel - 30)

# ================================================================= 1. the painting  (C1 .. C4)
s1 = Sec(at("C1"), at("C5"), 66)
N1 = s1.n
for bar in range(0, 2): padbar(s1, bar, "Dadd9", 0.28)                      # black -> the painting fades up
for t_, nm, v in [(at("C1", 0, 2.6), "A5", 30), (at("C1", 0, 4.2), "E6", 26), (at("C1", 0, 5.4), "D6", 24)]: pnote(n(nm), t_, 3.0, v)
gr.note(n("D2"), at("C1", 0, 1.6), at("C1", 0, 7.5), 34)
prog1 = (QP + QP + ["Bm7", "Gmaj9", "Em9", "Asus", "Bm7", "Gmaj9", "Em9", "Asus", "Asus", "Asus"])
for i in range(2, N1):
    ch = prog1[min(i - 2, len(prog1) - 1)]
    arp(s1, i, ch, P_SPARSE if i < 6 else (P_HALF if i < N1 - 2 else P_ONE), vel=31 if i < N1 - 2 else 27)
melody(s1, 2, Q, vel=44)                                                     # the question
melody(s1, 6, Q[:3], vel=45)
pnote(n("E5"), s1.tb(9) + 0.02, 3.0, 44)
for i in range(10, N1 - 1):                                                  # "is she painting black over a finished world?"
    for beat in ([1.5] if i % 2 else [0.5, 2.5]):
        pnote(rng.choice([p + 24 for p in CH[prog1[min(i - 2, len(prog1) - 1)]][0][3:]]), s1.tb(i, beat), 2.2, 24 + rng.randint(0, 4))
for i in range(6, N1 - 1): padbar(s1, i, prog1[min(i - 2, len(prog1) - 1)], 0.22)

# ---- title: three voids, three notes
knocks(at("C5", 0, 0.5), vel=50, gap=1.05)

# ================================================================= 2. the artist's note  (P1a .. P1c)
s2 = Sec(at("P1a", 0, 0.6), at("M2a", 0, 1.0), 66)
N2 = s2.n
prog2 = QP + QP + BP
for i in range(N2):
    ch = prog2[i] if i < min(len(prog2), N2 - 2) else ("Gmaj9" if i == N2 - 2 else "Asus")
    last = i >= N2 - 1
    arp(s2, i, ch, P_ONE if last else (P_SPARSE if i < 4 else (P_RISE if i % 4 == 3 else P_FULL)), vel=32 if i < 8 else 34)
    if 2 <= i < N2 - 1: padbar(s2, i, ch, 0.30 if i < 8 else 0.4)
melody(s2, 0, Q, vel=45)
melody(s2, 4, Q[:3], vel=47, octave=True)
pnote(n("E5"), s2.tb(7) + 0.02, 2.6, 45); pnote(n("C#5"), s2.tb(7, 3.0), 1.2, 30)
melody(s2, 8, B_MEL[:min(8, max(0, N2 - 10))], vel=48, octave=True)         # "a blank canvas is white, and he made it black"
if N2 - 2 >= 16:                                                             # "the way he got out of the block was to paint the block"
    melody(s2, N2 - 2, Q[:1], vel=42)
pnote(n("E5"), s2.tb(N2 - 1) + 0.02, 3.5, 40)

# ================================================================= 3. the museum  (M2a beat 1 "It was in Minecraft" .. M2d)
s3 = Sec(at("M2a", 1, 0.2), at("M3a"), 72)
N3 = s3.n
for i in range(N3):
    ch = (["Gmaj9", "D/F#"] + MP * 4)[i]
    last4 = i >= N3 - 4
    arp(s3, i, ch, P_HALF if i < 2 else (P_SPARSE if (i < 10 or last4) else (P_RISE if i % 2 else P_FULL)), vel=31 if i < 10 else 34)
    padbar(s3, i, ch, 0.42 if i < 2 else 0.5)
    if 10 <= i < N3 - 4: subbar(s3, i, ch, 0.4)
melody(s3, 2, M_MEL, track="lead", amp=0.5)                                  # the museum tune: a soft sine
k2 = max(0, min(8, N3 - 14))
melody(s3, 10, M_MEL[:k2], track="lead", amp=0.5)
melody(s3, 10, M_MEL[:k2], track="box", amp=0.45, up8=12)                    # ...and a music box an octave up
for i in range(10, 10 + k2):
    if i % 2 == 0: pnote(rng.choice([p + 24 for p in CH[MP[(i - 2) % 8]][0][3:]]), s3.tb(i, 1.5), 2.0, 26)
# M2d: "somebody rebuilt a painting called Art Block out of blocks": the piano's question, on the music box
melody(s3, N3 - 4, Q[:3], track="box", amp=0.5, up8=12)
melody(s3, N3 - 4, Q[:3], vel=38)

# ================================================================= 4. bases  (M3a), then the cut  (M3b)
s4 = Sec(at("M3a"), at("M3b"), 72)
N4 = s4.n
for i in range(N4):
    ch = MP[i % 8] if i < N4 - 1 else "Asus"
    arp(s4, i, ch, P_RISE if i % 2 else P_FULL, vel=36); padbar(s4, i, ch, 0.55); subbar(s4, i, ch, 0.45)
melody(s4, 0, M_MEL[:N4], vel=50, octave=True)
melody(s4, 0, M_MEL[:N4], track="box", amp=0.5, up8=12)
melody(s4, 0, M_MEL[:N4], track="lead", amp=0.42)
CUT = at("M3b")                                                              # "And sooner or later somebody does."
thud(CUT + 0.04)

# ================================================================= 5. spawn and the highways  (M3b .. M3e)
D0 = CUT + 0.3
T["dark"] += [(n("D1") + 12, D0, at("S4a") + 2, 0.55), (n("A1") + 12, D0 + 1.5, at("S4a") + 2, 0.4), (n("D3"), D0 + 4, at("M3d"), 0.22)]
T["dark"] += [(n("Eb3"), at("M3b", 0, 3.4), at("M3c"), 0.2)]
for i, (b, nm) in enumerate(zip([1, 2, 3, 4, 5], ["D4", "F4", "A4", "C5", "E5"])):       # spawn, highways, walls, pyramids, staircases
    T["bells"].append((n(nm), at("M3c", b, 0.05), 3.0, 0.55)); pnote(n(nm) - 24, at("M3c", b, 0.05), 3.5, 40, inst=gr)
gr.note(n("D2"), at("M3c", 0, 0.3), at("M3c", 1), 44)
# M3d: the roads. An even eighth-note line that keeps going, and climbs as the map pulls back
s5 = Sec(at("M3d"), at("M3e"), 88)
road = ns("D3 A3 D4 A3 E4 A3 D4 A3")
zoom0 = s5.bar_at(at("M3d", 1))
for i in range(s5.n):
    ch = ["Dm9", "Dm9", "Bbmaj7", "Bbmaj7", "Gm9", "Gm9", "Asus4", "Asus4"][i % 8]
    shift = 12 * max(0, min(2, int((i - zoom0) / 2 + 0.5))) if i >= zoom0 else 0
    for k in range(8):
        base = road[k] if ch == "Dm9" else CH[ch][0][[1, 3, 5, 3, 4, 3, 5, 3][k]] + 12
        T["pluck"].append((base + shift, s5.tb(i, k * 0.5), s5.tb(i, k * 0.5) + 0.2, 0.5 if k % 2 == 0 else 0.36))
    if i % 2 == 0:
        gr.note(CH[ch][2], s5.tb(i), s5.tb(i + 2), 46); padbar(s5, i, ch, 0.38, bars=2)
# M3e: spawn. Nobody designed it: slow chords with long gaps, low piano, wind
s6 = Sec(at("M3e"), at("S4a"), 60)
N6 = s6.n; dprog = ["Dm9", "Bbmaj7", "Gm9", "Asus4"]
for i in range(0, N6, 2):
    ch = dprog[(i // 2) % 4] if i < N6 - 2 else "Dm9"
    pool = CH[ch][0]
    for j, k in enumerate([0, 1, 2, 4]): pnote(pool[k], s6.tb(i, j * 0.75), 6.0, 36 - 2 * j, both=k <= 1)
    up.pedal(s6.tb(i) + 0.03, s6.tb(i + 2) - 0.05); gr.pedal(s6.tb(i) + 0.03, s6.tb(i + 2) - 0.05)
    padbar(s6, i, ch, 0.34, bars=2)
    pnote(rng.choice(pool[3:]) + 24, s6.tb(i + 1, 1.0), 3.0, 24)
T["lead"] += [(n("A4"), at("M3e", 4, 0.2), at("M3e", 4, 1.6), 0.4), (n("B4"), at("M3e", 4, 1.7), at("M3e", 5) - 0.2, 0.4)]   # "a game with rules being played": two notes of the museum tune
T["dark"] += [(n("Eb3"), at("M3e", 5, 0.1), at("M3e", 6), 0.24)]                                                              # "its players with no rules"
gr.note(n("D1"), at("M3e", 8, 0.1), at("M3e", 9) + 2, 60); gr.note(n("D2"), at("M3e", 8, 0.12), at("M3e", 9) + 2, 52)       # "obsidian is about the only thing that lasts"

# ================================================================= 6. the same picture  (S4a .. M4e): the theme over the drone
s7 = Sec(at("S4a", 0, 0.9), at("U5a"), 66)
N7 = s7.n
T["dark"] += [(n("D1") + 12, at("S4a"), at("U5a") - 0.05, 0.42), (n("A1") + 12, at("S4a"), at("U5a") - 0.05, 0.3)]
prog7 = (QP + QP + BP + QP + QP)
for i in range(N7):
    ch = prog7[i % len(prog7)]
    build = i >= N7 - 7                                                       # "on the server people kept going"
    arp(s7, i, ch, P_SPARSE if i < 4 else (P_HALF if i < 8 else (P_RISE if build and i % 2 else P_FULL)), vel=32 if not build else 37)
    if i >= 2: padbar(s7, i, ch, 0.3 if not build else 0.5)
    if build:
        subbar(s7, i, ch, 0.45)
        for k in range(8): T["pluck"].append((CH[ch][0][[1, 3, 5, 3, 4, 3, 5, 3][k]] + 12, s7.tb(i, k * 0.5), s7.tb(i, k * 0.5) + 0.2, 0.3 + 0.03 * (i - (N7 - 7))))
melody(s7, 0, Q, vel=45)                                                     # "I was looking at the painting again"
melody(s7, 4, Q[:3], vel=46); pnote(n("E5"), s7.tb(7) + 0.02, 2.6, 44)
k7 = max(0, min(8, N7 - 8 - 7))
melody(s7, 8, B_MEL[:k7], vel=46, octave=True)
melody(s7, N7 - 7, Q, vel=50, octave=True); melody(s7, N7 - 7, Q, track="box", amp=0.4, up8=12)
if N7 >= 10: melody(s7, N7 - 3, ANS[:3], vel=52, octave=True)                # the answer starts...
T["swell"] += [(p, at("U5a") - 4.2, at("U5a") - 0.02, 0.5) for p in CH["Asus"][1]]         # ...and the game is closed on it
GAME_OFF = at("U5a")

# ================================================================= 7. the third void  (U5a .. U5d): clean, no tape
p0 = at("U5a", 0, 1.5 + 2.6)                                                 # the caret's first blink
pulse(p0, at("U5d", 1), amp=0.5, fade_in=4.0)
T["glass"] += [(n("D5"), at("U5a", 0, 2.0), at("U5d"), 0.16), (n("A5"), at("U5b"), at("U5d"), 0.1)]
for b, nm in [(1, "D6"), (2, "E6"), (3, "F#6")]:                             # "Ask anything." "Full access" "No project"
    T["bells"].append((n(nm), at("U5c", b, 0.1), 2.5, 0.5))
for nm in ("A5", "E6", "A6"): T["bells"].append((n(nm), at("U5c", 4.3, 0.05), 4.0, 0.5))    # "What should we work on?"
T["bells"].append((n("D3") + 12, at("U5c", 5, 0.3), 5.0, 0.4))
# U5d: the painting laid over the prompt: the question, on glass
sO = Sec(at("U5d", 0, 0.8), at("U5d", 1), 66, bars=max(1, round((at("U5d", 1) - at("U5d", 0, 0.8)) / 3.64)))
melody(sO, 0, Q[:sO.n], track="bells", amp=0.45)
# three voids side by side: a piano chord / the drone / one bare sine
tA, tB, tC, tX = at("U5d", 2), at("U5d", 3), at("U5d", 4), at("U5d", 4.4)
for j, p in enumerate(ns("D3 A3 F#4 A4 E5")): up.note(p, tA + 0.05 + 0.06 * j, tA + 4.2, 46 - j)
up.pedal(tA, tB - 0.1)
T["dark"] += [(n("D2"), tB, tC + 0.3, 0.6), (n("A2"), tB + 0.2, tC + 0.3, 0.4)]
T["glass"] += [(n("D6"), tC + 0.1, at("U5d", 5) - 0.3, 0.3)]
pulse(tX + 0.6, at("U5d", 8), amp=0.5, fade_in=2.0)
tM = at("U5d", 5, 0.3)                                                       # "can build pretty much any software I can describe"
run(tM, min(tM + 3.6, at("U5d", 6) - 0.2), ["D", "A/C#", "Bm7", "Gmaj9"], amp=0.42, fade=1.2)
for j, nm in enumerate(("F#5", "A5")): pnote(n(nm), at("U5d", 7, 0.5 + 1.0 * j), 2.5, 40)   # "the same way the view didn't help her"
swarm(at("U5d", 8, 0.4), at("U6a"), n0=0.9, n1=9.0, seed=3)                  # "it's not just me": one cursor becomes many
pulse(at("U5d", 8), at("U6a"), amp=0.45)

# ================================================================= 8. handing over the brush  (U6a .. U6f)
pulse(at("U6a", 0, 0.3), at("U6a", 1.9), amp=0.45)
T["glass"] += [(n("D5"), at("U6a"), at("U6a", 1.9), 0.16)]
SEND = at("U6a", 1.9)
for nm in ("D5", "A5", "D6"): T["bells"].append((n(nm), SEND, 3.0, 0.45))
tR = at("U6b", 0, 0.5)                                                       # "It answered right away."
run(tR, at("U6b", 1), ["D", "A/C#", "Bm7", "Gmaj9"], amp=0.5)
run(at("U6b", 1), at("U6b", 3), ["D", "A/C#", "Bm7", "Gmaj9", "D", "A/C#", "Em9", "Asus"], amp=0.3)
run(at("U6b", 3), at("U6b", 4, 1.5), ["Gmaj9", "Asus"], amp=0.24, fade=3.0)
sL = Sec(at("U6b", 4), at("U6c"), 66, bars=max(1, round((at("U6c") - at("U6b", 4)) / 3.64)))   # "that's the landscape again"
for i in range(sL.n): arp(sL, i, QP[i % 4], P_HALF, vel=32); padbar(sL, i, QP[i % 4], 0.35)
melody(sL, 0, Q[:sL.n], vel=42)
# U6c: the grey label. Nothing but the cursor and a held tone; two neutral notes for "it recognised what kind of question this was"
pulse(at("U6c", 0, 0.5), at("U6e"), amp=0.45, fade_in=1.5)
T["glass"] += [(n("A4"), at("U6c", 1), at("U6d"), 0.2), (n("E5"), at("U6c", 2), at("U6d"), 0.12)]
for b, nm in [(3, "A5"), (3.5, "A5")]: T["bells"].append((n(nm), at("U6c", b), 2.0, 0.36))
knocks(at("U6d", 1, 0.2), vel=44, gap=0.95)                                   # "the question is back with me"
# U6e: she can't start / the model starts instantly
pnote(n("F#5"), at("U6e", 1, 0.15), 3.0, 44); pnote(n("D3"), at("U6e", 1, 0.15), 3.0, 34)
run(at("U6e", 2, 0.1), at("U6e", 3) - 0.3, ["D", "Bm7", "Gmaj9", "Asus"], amp=0.42, fade=1.5)
T["glass"] += [(n("D5"), at("U6e", 3), at("U6f"), 0.16)]
# U6f: the turn. The machine's own voice takes the piano's question; the piano joins; the missing note arrives
s8 = Sec(at("U6f", 0, 0.5), at("U6f", 6, 0.35), 64)
N8 = s8.n
prog8 = (QP + QP + AP + AP)
for i in range(N8):
    ch = prog8[i] if N8 - i > 3 else AP[3 - (N8 - i)]
    padbar(s8, i, ch, 0.25 + 0.3 * i / N8)
    if N8 - i <= 3:
        arp(s8, i, ch, P_FULL, vel=35 + (3 - (N8 - i))); subbar(s8, i, ch, 0.4)
        if N8 - i == 1: T["pad"] += [(p, s8.tb(i, 2), s8.tb(i + 1), 0.4) for p in CH["Asus"][1]]
melody(s8, 0, (Q + Q)[:max(0, N8 - 3)], track="mach", amp=0.5)                # "a model made entirely out of things other people said"
melody(s8, N8 - 3, ANS[:3], track="mach", amp=0.5)
melody(s8, N8 - 3, ANS[:3], vel=48, octave=True)                             # "it picked a self-portrait. Which is what Conway did."
HOME = at("U6f", 6, 0.35)                                                    # "The woman in the painting is him."
for j, nm in enumerate(["D2", "A2", "D3", "F#3", "A3", "D4", "F#4"]): up.note(n(nm), HOME + 0.05 * j, HOME + 7, 50 - j); gr.note(n(nm), HOME + 0.05 * j, HOME + 7, 44 - j) if j < 3 else None
up.note(n("D5"), HOME + 0.02, HOME + 7, 56); T["mach"].append((n("D5"), HOME, HOME + 3.2, 0.5)); T["bells"].append((n("D6"), HOME, 4, 0.4))
up.pedal(HOME - 0.02, at("E1", 0, 1.2)); gr.pedal(HOME - 0.02, at("E1", 0, 1.2))
for p in CH["Dadd9"][1]: T["pad"].append((p, HOME - 0.05, at("E1", 0, 1.5), 0.55))

# ================================================================= 9. ending
# E1 beats 0-3: both portraits. The whole theme, question and answer, piano and machine together
s9 = Sec(at("E1", 0, 1.3), at("E1", 4), 66)
N9 = s9.n
full = Q + ANS; fprog = QP + AP
for i in range(N9):
    j = i if N9 >= 8 else i + (8 - N9); ch = fprog[min(7, j)]
    arp(s9, i, ch, P_RISE if i % 2 else P_FULL, vel=36); padbar(s9, i, ch, 0.5); subbar(s9, i, ch, 0.42)
off9 = 0 if N9 >= 8 else 8 - N9
melody(s9, 0, full[off9:off9 + N9], vel=50, octave=True); melody(s9, 0, full[off9:off9 + N9], track="mach", amp=0.4)
# beats 4-7: what's coming. Cursor, then cursors
pulse(at("E1", 4, 0.2), at("E1", 9), amp=0.5)
T["glass"] += [(n("D5"), at("E1", 4), at("E1", 8), 0.16), (n("A5"), at("E1", 5), at("E1", 8), 0.12)]
swarm(at("E1", 5, 0.3), at("E1", 8), n0=0.8, n1=14.0, amp0=0.25, amp1=0.7, seed=11)
for i, ch in enumerate(["D", "Bm7", "Gmaj9", "Asus"]):
    tt0 = at("E1", 5) + i * (at("E1", 8) - at("E1", 5)) / 4
    for p in CH[ch][1]: T["pad"].append((p, tt0, tt0 + (at("E1", 8) - at("E1", 5)) / 4 + 0.2, 0.25 + 0.12 * i))
sP = Sec(at("E1", 8, 0.2), at("E1", 9), 66, bars=1)                          # "the tool itself wanted a portrait of itself"
melody(sP, 0, Q[:1], track="mach", amp=0.5)
# E2: sixteen years of people building anything they wanted: the museum tune, everything playing
sE = Sec(at("E2", 0, 0.4), at("E3"), 74)
NE = sE.n
for i in range(NE):
    ch = MP[i % 8] if i < NE - 1 else "Asus"
    arp(sE, i, ch, P_RISE if i % 2 else P_FULL, vel=38); padbar(sE, i, ch, 0.6); subbar(sE, i, ch, 0.5)
    for k in range(8): T["pluck"].append((CH[ch][0][[1, 3, 5, 3, 4, 3, 5, 3][k]] + 12, sE.tb(i, k * 0.5), sE.tb(i, k * 0.5) + 0.2, 0.3))
melody(sE, 0, M_MEL[:NE], vel=52, octave=True); melody(sE, 0, M_MEL[:NE], track="box", amp=0.5, up8=12); melody(sE, 0, M_MEL[:NE], track="lead", amp=0.45)
# E3: alone again. "...which I guess is Conway's trick."
sF = Sec(at("E3", 0, 0.6), at("E4", 1), 62)
NF = sF.n
for i in range(NF): arp(sF, i, QP[i % 4] if i < NF - 1 else "Asus", P_SPARSE if i < NF - 1 else P_ONE, vel=31)
melody(sF, max(0, NF - 5), Q, vel=43)
# E4: "What would you build?" The question again; the last note is left out
QEND = at("E4", 1)
pulse(QEND + 1.6, end("E5") - 2.0, amp=0.5, fade_in=1.0, fade_out=6.0)
T["glass"] += [(n("D5"), QEND + 1.6, end("E5") - 3, 0.14)]
# credits: the three notes of the title, once more
knocks(at("E5", 0, 5.6), vel=44, gap=1.15)

# ================================================================= render & mix
def analog(t):
    """1 = cassette (painting, server), 0 = clean (the prompt)."""
    pts = [(0, 1), (GAME_OFF - 0.05, 1), (GAME_OFF, 0), (at("U6f"), 0), (at("U6f", 5), 1), (at("E1", 4), 1), (at("E1", 4, 0.5), 0.15),
           (at("E2"), 0.15), (at("E2", 0, 0.5), 1), (QEND, 1), (QEND + 1.5, 0), (LENGTH, 0)]
    return np.interp(t, [p[0] for p in pts], [p[1] for p in pts])

print(f"total {TOTAL:.1f}s; sections: painting {s1.n} bars @{s1.bpm:.1f}, note {s2.n} @{s2.bpm:.1f}, museum {s3.n} @{s3.bpm:.1f}, bases {s4.n} @{s4.bpm:.1f}, "
      f"roads {s5.n} @{s5.bpm:.1f}, spawn {s6.n} @{s6.bpm:.1f}, same {s7.n} @{s7.bpm:.1f}, turn {s8.n} @{s8.bpm:.1f}, both {s9.n} @{s9.bpm:.1f}, server {sE.n} @{sE.bpm:.1f}, alone {sF.n} @{sF.bpm:.1f}", flush=True)
L = LENGTH; NS = int(L * SR)
STEMS = "--stems" in sys.argv; OUT = ROOT / "out"
analog_dry = np.zeros((2, NS), np.float32); clean_dry = np.zeros((2, NS), np.float32)
rev = {k: np.zeros((2, NS), np.float32) for k in ("piano", "hall", "clean")}       # reverb sends
def add(name, x, level, bus, send=None, amt=1.0, pn=None):
    """level a track, pan it if mono, add it to a bus and a reverb send, then let it go (keeps memory flat)."""
    x = E.at_level(x, level)
    if x.ndim == 1: x = pan(x, pn or 0.0)
    x = x[:, :NS]
    if STEMS: write(OUT / f"score-stem-{name}.wav", x[:, :int((TOTAL + 0.5) * SR)])
    bus += x
    if send: rev[send] += x * amt
    print(f"  {name}", flush=True)

add("piano", lp(hp(up.render(L), 58), 6500), -20, analog_dry, "piano")
add("grand", lp(hp(gr.render(L), 36), 2600), -28.5, analog_dry, "piano")
Piano._samples.clear()
add("pad", lp(hp(pad(T["pad"], L, cutoff=780, attack=2.4, release=4.0, detune=14, voices=3, seed=1), 110), 3200), -27, analog_dry, "hall")
add("drone", hp(pad(T["dark"], L, cutoff=240, attack=4.0, release=5.0, detune=22, voices=3, seed=2, open_to=420, drift=10), 30), -24, analog_dry, "hall")
add("swell", hp(pad(T["swell"], L, cutoff=600, attack=9.0, release=0.12, detune=16, voices=3, seed=3, open_to=2400), 120), -24, analog_dry, "hall")
add("lead", lp(hp(voice(T["lead"], L, harm=(1.0, 0.35, 0.12), vib=14, glide=0.07, att=0.09, rel=0.7, seed=5), 150), 4000), -24, analog_dry, "hall", 0.8, pn=-0.12)
add("box", lp(music_box(T["box"], L, seed=8), 8000), -29, analog_dry, "hall", pn=0.22)
add("sub", lp(voice(T["sub"], L, harm=(1.0,), att=0.4, rel=1.0, seed=9), 160), -27, analog_dry)
wnd = wind(L, seed=4, lo=220, hi=1100)
wnd = automate(wnd, [(0, -90), (CUT, -90), (CUT + 6, 0), (at("M3d"), -4), (at("M3e"), 0), (at("S4a"), -3), (at("S4b"), -12), (at("S4c"), -2), (at("S4d"), -10),
                     (GAME_OFF - 0.05, -8), (GAME_OFF, -90), (tB, -90), (tB + 0.8, -3), (tC, -3), (tC + 0.4, -90), (L, -90)])
add("wind", wnd, -36, analog_dry); del wnd
# the pluck line lives on the tape before the game is closed (the roads) and is clean afterwards (the machine)
plk = pan(E.at_level(lp(hp(voice(T["pluck"], L, harm=(1.0, 0.5, 0.3, 0.18, 0.1), att=0.004, rel=0.22, seed=10), 180), 3800), -28), -0.2)
plk = plk + 0.45 * np.roll(plk[::-1], int(0.34 * SR), axis=1)                 # echo, sides swapped
i_off = int(GAME_OFF * SR)
analog_dry[:, :i_off] += plk[:, :i_off]; rev["hall"][:, :i_off] += 0.6 * plk[:, :i_off]
clean_dry[:, i_off:NS] += plk[:, i_off:NS]; rev["clean"][:, i_off:NS] += plk[:, i_off:NS]; del plk
add("glass", lp(pad(T["glass"], L, cutoff=520, attack=2.5, release=3.0, detune=0, voices=1, seed=4, drift=0), 5000), -34, clean_dry, "clean", 0.5)
add("machine", lp(hp(voice(T["mach"], L, harm=(1.0, 0.0, 0.18, 0.0, 0.06), vib=6, glide=0.05, att=0.05, rel=0.5, seed=6), 150), 5000), -23, clean_dry, "clean", pn=0.1)
add("bells", lp(fm_bell(T["bells"], L, ratio=3.5, index=1.6, decay=2.8, seed=7), 7000), -27, clean_dry, "clean", pn=0.15)
add("pulse", lp(voice(T["pulse"], L, harm=(1.0, 0.15), att=0.004, rel=0.3, seed=11), 6000), -31, clean_dry, "clean", 1.6)
pings = np.zeros((2, NS), np.float32)
for i in range(6): pings += pan(fm_bell(PINGS[i], L, ratio=2.0, index=0.9, decay=1.6, seed=20 + i), -0.85 + 0.34 * i)[:, :NS]
add("pings", lp(pings, 7000), -27, clean_dry, "clean", 1.2); del pings
print("tracks done", flush=True)
amix = analog_dry; del analog_dry
amix += room(rev["piano"], decay=2.6, predelay=0.022, bright=6000, seed=1); rev["piano"] = None
amix += room(rev["hall"], decay=5.5, predelay=0.04, bright=5000, seed=2) * 0.9; rev["hall"] = None
# closing the game cuts the tape world dead (no reverb tail); it comes back with the piano later
i0 = int(GAME_OFF * SR); k = int(0.015 * SR)
gate = np.ones(NS, np.float32); gate[i0 - k:i0] = np.linspace(1, 0, k); j = int((GAME_OFF + 2.0) * SR); gate[i0:j] = 0; gate[j:j + SR] = np.linspace(0, 1, SR)
amix *= gate; del gate
mix = amix; mix += clean_dry; del clean_dry
mix += room(rev["clean"], decay=7.0, predelay=0.06, bright=7000, seed=3); rev["clean"] = None
mix = mix / (np.abs(mix).max() + 1e-9) * 0.7
mix = tape(mix, depth=analog)
mix = compress(hp(mix, 34), -20, 1.5)
mix = E.at_level(mix, -19.0)
mix = limiter(mix, -1.0)
fo = int(3.0 * SR); mix[:, -fo:] *= np.linspace(1, 0, fo)
mix = mix[:, :int((TOTAL + 0.5) * SR)]
write(OUT / "three-voids-score.wav", mix)
print("written", OUT / "three-voids-score.wav", f"{mix.shape[1] / SR:.1f}s  peak {20 * math.log10(np.abs(mix).max()):.1f} dB  rms {rms_db(mix):.1f} dB")
# section loudness table (quiet/loud contrast check)
marks = [("painting", 0, at("C5")), ("title", at("C5"), at("P1a")), ("note", at("P1a"), at("M2a")), ("museum", at("M2a"), at("M3a")), ("bases", at("M3a"), CUT),
         ("cut+spawn", CUT, at("M3d")), ("roads", at("M3d"), at("M3e")), ("spawn", at("M3e"), at("S4a")), ("same picture", at("S4a"), GAME_OFF),
         ("prompt", GAME_OFF, at("U5d")), ("three voids", at("U5d"), at("U6a")), ("asking", at("U6a"), at("U6c")), ("label", at("U6c"), at("U6f")),
         ("turn", at("U6f"), at("E1")), ("both", at("E1"), at("E1", 4)), ("coming", at("E1", 4), at("E2")), ("server", at("E2"), at("E3")),
         ("alone", at("E3"), QEND), ("question", QEND, TOTAL)]
for name, a, b in marks:
    seg = mix[:, int(a * SR):int(b * SR)]
    print(f"  {name:13s} {a:6.1f}-{b:6.1f}  rms {rms_db(seg):6.1f} dB  peak {20 * math.log10(np.abs(seg).max() + 1e-9):6.1f}")
