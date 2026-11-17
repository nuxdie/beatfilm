#!/usr/bin/env python3
"""mix.py <narration_bed.wav> <score.wav> <out.wav>  — voice + music balance and loudness master.

Voice is the reference. The music is trimmed so that, on average, it sits UNDER LU below the voice while someone is
speaking, comes up by OPEN dB in the gaps, and is never allowed closer than CLOSEST LU to the voice even in its loud
sections. The sum is mastered to TARGET LUFS integrated with a true-peak ceiling (YouTube plays -14 LUFS as is).
Prints a per-minute table so the balance can be checked without listening.
"""
import sys, math
import numpy as np, soundfile as sf, pyloudnorm as pyln
from scipy import signal
from scipy.ndimage import maximum_filter1d, minimum_filter1d, uniform_filter1d
TARGET, PEAK = -14.0, -1.6
UNDER, OPEN, CLOSEST = 19.0, 6.0, 15.0
FLOOR, LIFT, SOLO = 23.0, 6.0, 5.0
v, sr = sf.read(sys.argv[1], dtype="float32", always_2d=True); m, sr2 = sf.read(sys.argv[2], dtype="float32", always_2d=True); assert sr == sr2 == 48000
n = max(len(v), len(m)); pad = lambda x: np.pad(x, ((0, n - len(x)), (0, 0)))
v = pad(v); m = pad(m)
if v.shape[1] == 1: v = np.repeat(v, 2, axis=1)
if len(v) < sr * 3 or not np.isfinite(v).all() or not np.isfinite(m).all():
    raise ValueError('mix expects finite audio at least three seconds long')
if not np.any(np.abs(v) > 1e-5):
    raise ValueError('voice reference is silent; provide a voiced track or master music separately')
meter = pyln.Meter(sr)
def st_loud(x, win=3.0, hop=0.5):
    """short-term loudness curve (dB, K-weighting approximated by the meter on windows)."""
    w, h = int(win * sr), int(hop * sr); out = []
    for i in range(0, len(x) - w + 1, h):
        try: out.append(meter.integrated_loudness(x[i:i + w]))
        except Exception: out.append(-70.0)
    return np.maximum(np.array(out), -70.0), h, w
# speech activity: voice envelope, with look-ahead so the music is already down when a word starts
env = np.sqrt(uniform_filter1d(np.mean(v ** 2, axis=1), int(0.05 * sr)))
thr = 10 ** ((20 * math.log10(np.percentile(env[env > 1e-5], 60)) - 22) / 20)
act = (env > thr).astype(np.float32)
act = maximum_filter1d(act, int(0.9 * sr))                    # bridge pauses shorter than ~0.9 s, opens 0.45 s early
act = uniform_filter1d(uniform_filter1d(act, int(0.45 * sr)), int(0.45 * sr))      # smooth, about 0.9 s ramps
Lv = meter.integrated_loudness(v)
# static trim: music measured only where the voice is active
sp = act > 0.5
Lm_sp = meter.integrated_loudness(m[sp]) if sp.sum() > sr * 5 else meter.integrated_loudness(m)
trim = (Lv - UNDER) - Lm_sp
g = 10 ** ((trim + OPEN * (1 - act)) / 20)
m2 = m * g[:, None]
# safety: wherever the ducked music's short-term loudness would come closer than CLOSEST to the voice during speech, pull it back
cur, h, w = st_loud(m2); t_c = (np.arange(len(cur)) * h + w / 2) / sr
a_c = np.interp(t_c, np.arange(n) / sr, act)
over = np.where(a_c > 0.5, np.maximum(0, cur - (Lv - CLOSEST)), 0.0)
red = np.interp(np.arange(n) / sr, t_c, over); red = uniform_filter1d(maximum_filter1d(red, int(1.0 * sr)), int(1.5 * sr))
# floor: the quietest cues (the cursor pulse) must stay audible: lift anything more than FLOOR LU under the voice, up to LIFT dB
lift = np.clip((Lv - FLOOR) - cur, 0, LIFT) * (cur > -60)
lift = np.interp(np.arange(n) / sr, t_c, lift); lift = uniform_filter1d(lift, int(3.0 * sr))
# long gaps with no voice at all (opening, title card, credits): the music is the only thing there, so it comes up further
long_gap = 1 - maximum_filter1d((env > thr).astype(np.float32), int(3.0 * sr)); long_gap = uniform_filter1d(uniform_filter1d(long_gap, int(1.2 * sr)), int(1.2 * sr))
m2 *= (10 ** ((lift - red + SOLO * long_gap) / 20))[:, None]
mix = v + m2
L = meter.integrated_loudness(mix); mix *= 10 ** ((TARGET - L) / 20)
# look-ahead limiter, checked at 4x oversampling for true peak
c = 10 ** (PEAK / 20)
for _ in range(3):
    up = signal.resample_poly(mix, 4, 1, axis=0); pk = np.abs(up).reshape(-1, 4, 2).max(axis=(1, 2))[:n] if len(up) >= 4 * n else np.abs(mix).max(1)
    if pk.max() <= c * 1.001: break
    wl = int(0.005 * sr); e = maximum_filter1d(pk, 2 * wl + 1); gg = np.minimum(1.0, c * 0.98 / np.maximum(e, 1e-9))
    gg = uniform_filter1d(minimum_filter1d(gg, int(0.15 * sr) + 1), wl + 1); mix *= gg[:, None]
sf.write(sys.argv[3], mix, sr, subtype="PCM_24")
k = 10 ** ((TARGET - L) / 20)
print(f"voice {Lv:.1f} LUFS; music trim {trim:+.1f} dB (under speech {UNDER:.0f} LU below voice, +{OPEN:.0f} dB in gaps); extra pull-back up to {red.max():.1f} dB")
print(f"final: {meter.integrated_loudness(mix):.1f} LUFS integrated, true peak {20 * math.log10(np.abs(signal.resample_poly(mix, 4, 1, axis=0)).max()):.1f} dBTP, speech {100 * sp.mean():.0f}% of the time")
print(" min   voice   music(speech)  gap(LU)   music(in pauses)")
vv, mm = v * k, m2 * k
for a in range(0, n, 60 * sr):
    b = min(n, a + 60 * sr); s_ = sp[a:b]
    def L_(x):
        try: return meter.integrated_loudness(x) if len(x) > sr else float("nan")
        except Exception: return float("nan")
    lv, lm, lp = L_(vv[a:b][s_]), L_(mm[a:b][s_]), L_(mm[a:b][~s_])
    print(f"{a // sr // 60:4d}  {lv:6.1f}  {lm:9.1f}     {lv - lm:6.1f}    {lp:9.1f}")
