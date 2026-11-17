"""fillgaps.py <clean 48k wav> <words.json> <lang>: the recogniser sometimes skips a whole phrase. Find speech that has no
words on it (>= 1.2 s), transcribe just that stretch, and merge the words in."""
import sys, json, numpy as np, soundfile as sf
from faster_whisper import WhisperModel
a, sr = sf.read(sys.argv[1], dtype="float32"); W = json.load(open(sys.argv[2])); lang = sys.argv[3]
H = int(0.02 * sr); nf = len(a) // H; e = 10 * np.log10(np.mean(a[:nf * H].reshape(nf, H) ** 2, axis=1) + 1e-12); vo = e > np.percentile(e, 95) - 21
cov = np.zeros(nf, bool)
for s, t, _ in W: cov[int(max(s, t - 0.8) * sr / H):int(t * sr / H) + 1] = True      # a word "lasting" seconds is hiding a skipped phrase
un = vo & ~cov
# close small holes, then collect stretches
from scipy.ndimage import binary_closing, binary_opening
un = binary_opening(binary_closing(un, np.ones(25)), np.ones(15)); ed = np.flatnonzero(np.diff(np.concatenate([[0], un.astype(np.int8), [0]])))
gaps = [(ed[k] * H / sr, ed[k + 1] * H / sr) for k in range(0, len(ed), 2) if (ed[k + 1] - ed[k]) * H / sr >= 1.2]
if not gaps: print("no untranscribed speech"); sys.exit()
m = WhisperModel("medium.en" if lang == "en" else "medium", device="cpu", compute_type="int8", cpu_threads=10)
for g0, g1 in gaps:
    x = a[int(max(0, g0 - 0.4) * sr):int((g1 + 0.4) * sr)]; x16 = np.interp(np.arange(0, len(x), 3.0), np.arange(len(x)), x).astype(np.float32)
    segs, _ = m.transcribe(x16, word_timestamps=True, vad_filter=False, condition_on_previous_text=False, beam_size=5, language=lang)
    new = [[round(max(0, g0 - 0.4) + w.start, 3), round(max(0, g0 - 0.4) + w.end, 3), w.word.strip()] for s_ in segs for w in s_.words]
    new = [w for w in new if g0 - 0.2 <= (w[0] + w[1]) / 2 <= g1 + 0.2]
    print(f"{g0:7.1f}-{g1:7.1f}: {' '.join(w[2] for w in new)}")
    W = [w for w in W if not (g0 - 0.1 <= (w[0] + w[1]) / 2 <= g1 + 0.1)] + new
W.sort(key=lambda w: w[0]); json.dump(W, open(sys.argv[2], "w"), ensure_ascii=False)
