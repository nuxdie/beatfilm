"""Three Voids score: instruments and mixing tools. Everything is 48 kHz, stereo arrays are (2, N) float32.

Approach after github.com/nuxdie/claude-music (the C418-style album toolkit there): real sampled pianos, a few
synthesized voices, convolution room, cassette wow. This file does not need sfizz or a plugin host: the SFZ pianos
are played by a small sampler written here, pads and bells are additive / FM synthesis in numpy.
"""
import math, random, re, os
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy import signal

SR = 48000
LIBS = Path(os.environ.get("BEATFILM_SAMPLES", "samples"))
UPRIGHT = LIBS / "UprightPianoKW-SFZ+FLAC-20220221/UprightPianoKW-20220221.sfz"      # CC0, freepats
GRAND = LIBS / "SalamanderGrandPianoV3_44.1khz16bit/SalamanderGrandPianoV3.sfz"     # CC-BY 3.0, Alexander Holm

PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
def n(name):
    """'C4' -> 60, 'Bb2', 'F#5'."""
    i, pc = 1, PC[name[0]]
    while i < len(name) and name[i] in "b#": pc += -1 if name[i] == "b" else 1; i += 1
    return pc + 12 * (int(name[i:]) + 1)
def ns(s): return [n(x) for x in s.split()]
def hz(p): return 440.0 * 2 ** ((p - 69) / 12)
def db(x): return 10 ** (x / 20)


# ---------------------------------------------------------------- SFZ piano sampler
class Piano:
    """Plays a piano SFZ (key/velocity-mapped samples). note(), pedal(), render(length) -> (2, N)."""
    _samples = {}

    def __init__(self, sfz, release=None, veltrack=None):
        self.dir = Path(sfz).parent; self.regions = []; self.notes = []; self.pedals = []
        glob, grp = {}, {}
        txt = re.sub(r"//.*", "", Path(sfz).read_text(errors="ignore"))
        for head, body in re.findall(r"<(\w+)>([^<]*)", txt):
            ops = dict(re.findall(r"(\w+)=(\S+(?: [^=\s]+(?=\s|$))*)", body))
            if head == "global": glob = ops; grp = {}
            elif head == "group": grp = ops
            elif head == "region":
                o = {**glob, **grp, **ops}
                if "sample" not in o or o.get("trigger") == "release": continue
                if "key" in o: o.setdefault("lokey", o["key"]); o.setdefault("hikey", o["key"]); o.setdefault("pitch_keycenter", o["key"])
                if int(float(o.get("locc64", 0))) > 0: continue
                self.regions.append(dict(lo=int(o.get("lokey", 0)), hi=int(o.get("hikey", 127)), lov=int(o.get("lovel", 1)), hiv=int(o.get("hivel", 127)),
                                         kc=int(o.get("pitch_keycenter", 60)), tune=float(o.get("tune", 0)), sample=o["sample"].replace("\\", "/"),
                                         rel=float(o.get("ampeg_release", 0.6)), vt=float(o.get("amp_veltrack", 100))))
        self.release = release; self.veltrack = veltrack

    def note(self, pitch, start, end, vel):
        self.notes.append((int(pitch), max(0.0, start), max(start + 0.03, end), int(max(1, min(127, vel)))))

    def pedal(self, down, up): self.pedals.append((down, up))

    def _load(self, name):
        k = str(self.dir / name)
        if k not in Piano._samples:
            a, sr = sf.read(k, dtype="float32", always_2d=True, frames=int(sf.info(k).samplerate * 14))
            Piano._samples[k] = (np.ascontiguousarray(a.T), sr)
        return Piano._samples[k]

    def render(self, length):
        N = int(length * SR); out = np.zeros((2, N), np.float32)
        for p, s, e, v in self.notes:
            cand = [r for r in self.regions if r["lo"] <= p <= r["hi"] and r["lov"] <= v <= r["hiv"]]
            if not cand: continue
            r = cand[0]; a, sr = self._load(r["sample"])
            for d, u in self.pedals:                         # sustain pedal holds the note
                if d <= e < u: e = u
            rel = self.release or r["rel"]
            ratio = 2 ** ((p - r["kc"]) / 12 + r["tune"] / 1200) * sr / SR
            m = int(min(a.shape[1] / ratio - 2, (e - s + rel * 1.6) * SR)); i0 = int(s * SR); m = min(m, N - i0)
            if m <= 0: continue
            pos = np.arange(m) * ratio; tt = np.arange(m) / SR
            env = np.where(tt < e - s, 1.0, np.exp(-(tt - (e - s)) / (rel / 4.5))).astype(np.float32)
            env[-min(m, 480):] *= np.linspace(1, 0, min(m, 480))
            vt = (self.veltrack if self.veltrack is not None else r["vt"]) / 100
            g = (v / 127) ** (2 * vt)
            src = np.arange(a.shape[1])
            for c in range(2):
                out[c, i0:i0 + m] += (np.interp(pos, src[:int(pos[-1]) + 2], a[min(c, a.shape[0] - 1)][:int(pos[-1]) + 2]) * env * g).astype(np.float32)
        return out


# ---------------------------------------------------------------- synthesized voices (after claude-music album/kit.py)
def voice(notes, length, harm=(1.0,), vib=0.0, vib_rate=4.6, vib_delay=0.45, glide=0.0, att=0.06, rel=0.4, seed=0, detune=0.0):
    """Additive voice. notes: (pitch, start, end, amp). Delayed vibrato (cents), portamento between connected notes."""
    r = random.Random(seed); nn = int(length * SR); out = np.zeros(nn, np.float32)
    notes = sorted(notes, key=lambda x: x[1])
    for j, (p, s, e, a) in enumerate(notes):
        i0, i1 = int(s * SR), min(nn, int((e + rel) * SR))
        if i1 <= i0: continue
        tt = np.arange(i1 - i0) / SR; f = hz(p) * np.ones_like(tt)
        if glide and j and s - notes[j - 1][2] < 0.12: f = f * (hz(notes[j - 1][0]) / f) ** np.exp(-tt / glide)
        if vib: f = f * 2 ** (vib * np.clip((tt - vib_delay) / 0.8, 0, 1) * np.sin(2 * np.pi * vib_rate * tt + r.random() * 6) / 1200)
        w = np.zeros_like(tt)
        for d in ([0.0] if not detune else [-detune / 2, detune / 2]):
            ph = 2 * np.pi * np.cumsum(f * 2 ** (d / 1200)) / SR + r.random() * 6
            for k, h in enumerate(harm, 1): w += h * np.sin(k * ph)
        env = np.minimum(1, tt / att) * np.clip((e - s + rel - tt) / rel, 0, 1) ** 2
        out[i0:i1] += (a * w * env).astype(np.float32)
    return out


def fm_bell(notes, length, ratio=3.5, index=2.2, decay=2.5, idecay=0.6, seed=0):
    """FM bell / glassy key. notes: (pitch, start, _, amp)."""
    r = random.Random(seed); nn = int(length * SR); out = np.zeros(nn, np.float32)
    for p, s, _, a in notes:
        dec = decay * (2 ** (-(p - 72) / 24)); L = int(min(dec * 5, 14) * SR); i0 = int(s * SR); i1 = min(nn, i0 + L)
        if i1 <= i0: continue
        tt = np.arange(i1 - i0) / SR; f = hz(p)
        mod = index * np.exp(-tt / idecay) * np.sin(2 * np.pi * f * ratio * tt + r.random())
        out[i0:i1] += (a * np.sin(2 * np.pi * f * tt + mod) * np.exp(-tt / dec) * np.minimum(1, tt / 0.003)).astype(np.float32)
    return out


def music_box(notes, length, seed=0):
    """Comb-tine music box: bright inharmonic partials, fast decay, slight detune per tine."""
    r = random.Random(seed); nn = int(length * SR); out = np.zeros(nn, np.float32)
    parts = [(1.0, 1.0, 1.0), (2.0, 0.35, 0.5), (3.01, 0.12, 0.3), (5.43, 0.10, 0.15), (8.9, 0.05, 0.08)]
    for p, s, _, a in notes:
        f = hz(p) * 2 ** (r.uniform(-4, 4) / 1200); i0 = int(s * SR); dec = 1.6 * 2 ** (-(p - 72) / 18); i1 = min(nn, i0 + int(dec * 5 * SR))
        if i1 <= i0: continue
        tt = np.arange(i1 - i0) / SR
        w = sum(amp * np.sin(2 * np.pi * f * m * tt + r.random()) * np.exp(-tt / (dec * dm)) for m, amp, dm in parts)
        out[i0:i1] += (a * w * np.minimum(1, tt / 0.002)).astype(np.float32)
    return out


def pad(notes, length, cutoff=900.0, attack=2.0, release=4.0, detune=14.0, voices=3, seed=0, open_to=None, drift=6.0):
    """Analog-style pad: unison saws through a 24 dB low-pass, done additively (each harmonic is weighted by the
    filter response), so the cutoff can move per note without filter state. notes: (pitch, start, end, amp).
    open_to: cutoff the filter opens towards over the note. Returns stereo (voices are spread)."""
    r = random.Random(seed); nn = int(length * SR); out = np.zeros((2, nn), np.float32)
    for p, s, e, a in notes:
        i0, i1 = int(max(0, s) * SR), min(nn, int((e + release) * SR))
        if i1 <= i0: continue
        tt = np.arange(i1 - i0) / SR; f0 = hz(p)
        env = (1 - np.exp(-tt / (attack / 3))) * np.where(tt < e - s, 1.0, np.exp(-(tt - (e - s)) / (release / 4)))
        fc = cutoff if open_to is None else cutoff * (open_to / cutoff) ** np.clip(tt / max(0.1, e - s), 0, 1)
        kmax = int(min(40, (np.max(fc) * 3.2) / f0)) + 1
        for vi in range(voices):
            d = (vi - (voices - 1) / 2) / max(1, (voices - 1) / 2) * detune / 2 if voices > 1 else 0.0
            wob = drift * np.sin(2 * np.pi * r.uniform(0.07, 0.19) * tt + r.random() * 6)
            ph = 2 * np.pi * np.cumsum(f0 * 2 ** ((d + wob) / 1200)) / SR + r.random() * 6
            w = np.zeros_like(tt)
            for k in range(1, kmax + 1):
                w += np.sin(k * ph) / k / (1 + (k * f0 / fc) ** 4) ** 0.5
            panv = 0.5 + 0.4 * (vi - (voices - 1) / 2) / max(1, (voices - 1) / 2) if voices > 1 else 0.5
            y = (a * w * env / voices).astype(np.float32)
            out[0, i0:i1] += y * math.cos(panv * math.pi / 2); out[1, i0:i1] += y * math.sin(panv * math.pi / 2)
    return out


def noise(nsamp, seed=0): return np.random.default_rng(seed).normal(0, 1, nsamp).astype(np.float32)


def wind(length, seed=0, lo=250.0, hi=1400.0, rate=0.07):
    """Gusting wind: noise through slowly wandering band-passes (block-wise crossfaded), amplitude-swelling. Mono."""
    nn = int(length * SR); r = np.random.default_rng(seed); x = noise(nn, seed); tt = np.arange(nn) / SR
    ctrl = sum(np.sin(2 * np.pi * rate * k * tt + r.random() * 6) / k for k in (1, 1.7, 2.9)); ctrl = (ctrl - ctrl.min()) / (np.ptp(ctrl) + 1e-9)
    bands = np.geomspace(lo, hi, 7); out = np.zeros(nn, np.float32)
    for i, fc in enumerate(bands):
        sos = signal.butter(2, [fc / 1.25, fc * 1.25], "bandpass", fs=SR, output="sos")
        wgt = np.clip(1 - np.abs(ctrl * (len(bands) - 1) - i), 0, 1)
        out += (signal.sosfilt(sos, x) * wgt).astype(np.float32)
    return (out * (0.3 + 0.7 * ctrl ** 1.5)).astype(np.float32)


# ---------------------------------------------------------------- mixing
def st(x): return np.stack([x, x]) if x.ndim == 1 else x
def pan(x, p):
    """mono -> stereo, p in -1..1 (equal power)."""
    a = (p + 1) * math.pi / 4; return np.stack([x * math.cos(a), x * math.sin(a)]).astype(np.float32)
def rms_db(x): return 20 * math.log10(float(np.sqrt(np.mean(np.square(x)))) + 1e-12)
def at_level(x, level_db, ref=None):
    """scale so the loud parts sit at level_db RMS (measured over the loudest 30% of 0.4 s windows)."""
    m = st(x).mean(0); w = int(0.4 * SR); k = len(m) // w
    if k < 1: return x
    e = np.sqrt(np.mean(m[:k * w].reshape(k, w) ** 2, axis=1)); e = np.sort(e[e > 1e-6])
    if len(e) == 0: return x
    loud = float(np.sqrt(np.mean(e[int(len(e) * 0.7):] ** 2)))
    return (x * (db(level_db) / loud)).astype(np.float32)
def filt(x, kind, fc, order=2):
    sos = signal.butter(order, fc, kind, fs=SR, output="sos"); return signal.sosfilt(sos, x, axis=-1).astype(np.float32)
def lp(x, fc, order=2): return filt(x, "lowpass", fc, order)
def hp(x, fc, order=2): return filt(x, "highpass", fc, order)
def automate(x, points, length=None):
    """gain envelope from [(t, dB), ...], linear in dB between points."""
    nn = x.shape[-1]; tt = np.arange(nn) / SR
    g = np.interp(tt, [p[0] for p in points], [p[1] for p in points]); return (x * (10 ** (g / 20))).astype(np.float32)


_irs = {}
def room(x, decay=2.8, predelay=0.02, bright=6000.0, seed=1, wet=1.0):
    """Convolution reverb with a synthesized stereo impulse response: three noise bands with their own decay times
    (highs die first), sparse early reflections. Returns the wet signal only."""
    k = (decay, predelay, bright, seed)
    if k not in _irs:
        L = int((decay * 1.3 + predelay) * SR); r = np.random.default_rng(seed); tt = np.arange(L) / SR; ir = np.zeros((2, L), np.float32)
        for c in range(2):
            nz = r.normal(0, 1, L).astype(np.float32)
            lo = lp(nz, 500) * np.exp(-6.9 * tt / (decay * 1.15))
            mid = hp(lp(nz, 2500), 500) * np.exp(-6.9 * tt / decay)
            hi_ = hp(lp(nz, bright), 2500) * np.exp(-6.9 * tt / (decay * 0.55))
            tail = (lo + mid + 0.8 * hi_) * np.minimum(1, tt / 0.03)
            er = np.zeros(L, np.float32)
            for j in range(9): er[int(r.uniform(0.004, 0.07) * SR)] += r.uniform(-1, 1) * 0.5
            y = tail + lp(er, bright) * 6
            pd = int(predelay * SR); ir[c, pd:] = y[:L - pd]
        ir /= np.sqrt(np.sum(ir ** 2, axis=1, keepdims=True)).max()
        _irs[k] = ir
    ir = _irs[k]; x = st(x)
    return np.stack([(signal.oaconvolve(x[c], ir[c])[:x.shape[1]] * (wet * 0.35)).astype(np.float32) for c in range(2)])


def tape(x, wow_cents=6.0, flutter_cents=1.5, drive=1.6, hiss_db=-66.0, seed=7, depth=None):
    """Cassette character: wow & flutter, soft saturation, a little hiss. depth(t) in 0..1 scales the wow (0 = clean)."""
    rng = np.random.default_rng(seed); nn = x.shape[1]; tt = np.arange(nn) / SR
    cents = wow_cents * np.sin(2 * np.pi * 0.42 * tt) + 0.5 * wow_cents * np.sin(2 * np.pi * 0.13 * tt + 1) + flutter_cents * np.sin(2 * np.pi * 6.3 * tt)
    d = np.ones(nn) if depth is None else np.clip(depth(tt), 0, 1)
    rate = 2 ** (cents * d / 1200); pos = np.clip(np.cumsum(rate) - rate[0], 0, nn - 1)
    src = np.arange(nn); y = np.stack([np.interp(pos, src, c).astype(np.float32) for c in x]); del src, pos, rate, cents
    y = np.tanh(y * drive) / drive
    hiss = lp(hp(rng.normal(0, 1, y.shape).astype(np.float32), 1500), 9000)
    return (y + hiss * db(hiss_db) * np.abs(y).max() * d).astype(np.float32)


def limiter(x, ceiling_db=-1.0, look=0.005, rel=0.2):
    """look-ahead brickwall limiter (stereo-linked)."""
    from scipy.ndimage import maximum_filter1d, minimum_filter1d, uniform_filter1d
    c = db(ceiling_db); w = int(look * SR); pk = maximum_filter1d(np.abs(x).max(0), 2 * w + 1)
    g = np.minimum(1.0, c / np.maximum(pk, 1e-9))
    g = uniform_filter1d(minimum_filter1d(g, int(rel * SR) + 1), w + 1)
    return np.clip(x * g, -c, c).astype(np.float32)


def compress(x, thresh_db=-20.0, ratio=1.5, att=0.04, rel=0.3):
    """gentle feed-forward bus compressor (stereo-linked)."""
    lev = np.abs(x).max(0) + 1e-9
    aa, ar = math.exp(-1 / (att * SR)), math.exp(-1 / (rel * SR))
    e = signal.lfilter([1 - ar], [1, -ar], lev)                    # smoothed level (release-ish)
    over = np.maximum(0, 20 * np.log10(e + 1e-9) - thresh_db)
    g = 10 ** (-(over * (1 - 1 / ratio)) / 20)
    return (x * g).astype(np.float32)


def write(path, x):
    sf.write(str(path), np.clip(x.T, -1, 1), SR, subtype="PCM_24")
