"""verify_narration.py — re-transcribe the cut clips and list every difference from the script."""
import json, re, difflib, importlib.util, subprocess, sys
ROOT = "/home/n/Videos/three-voids"; T = "/home/n/Games/three-voids-raw/tmp"
sp = importlib.util.spec_from_file_location("n", ROOT + "/build/narration.py"); N = importlib.util.module_from_spec(sp); sp.loader.exec_module(N)
ids = [s for s, t in N.NARR if t]
open(T + "/cat.txt", "w").write("".join(f"file '{ROOT}/narration/{i}.wav'\n" for i in ids))
subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", T + "/cat.txt", "-ar", "16000", "-ac", "1", T + "/bed16k.wav"], check=True)
subprocess.run([sys.executable, ROOT + "/build/transcribe.py", T + "/bed16k.wav", T + "/bed_words.json"], check=True, capture_output=True)
SAME = {"16": "sixteen", "colors": "colours", "gray": "grey", "traveled": "travelled", "realized": "realised", "recognized": "recognised"}
def norm(w):
    w = re.sub(r"[^a-z0-9]", "", w.lower().replace("'", "").replace("’", "")); return SAME.get(w, w)
W = [w for w in json.load(open(T + "/bed_words.json")) if norm(w[2])]
a = [norm(w) for _, t in N.NARR for w in t.replace(" | ", " ").split() if norm(w)]; b = [norm(w[2]) for w in W]
sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag != "equal": print(f"{tag:8s} @{W[min(j1, len(W) - 1)][0]:6.1f}s script: {' '.join(a[i1:i2])!r:40s} heard: {' '.join(b[j1:j2])!r}")
print("match ratio", round(sm.ratio(), 4), len(a), "script words,", len(b), "heard")
