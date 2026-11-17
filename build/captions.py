#!/usr/bin/env python3
"""captions.py — out/film.srt: the script's own text (correct spelling and punctuation) on the spoken word timings."""
import json, re, difflib, importlib.util, textwrap
from config import ROOT, TMP as T, TOOLROOT
sp = importlib.util.spec_from_file_location("n", ROOT + "/build/narration.py"); N = importlib.util.module_from_spec(sp); sp.loader.exec_module(N)
SAME = {"16": "sixteen", "colors": "colours", "gray": "grey", "traveled": "travelled", "realized": "realised", "recognized": "recognised"}
def norm(w):
    w = re.sub(r"[^a-z0-9]", "", w.lower().replace("'", "").replace("’", "")); return SAME.get(w, w)
W = [w for w in json.load(open(T + "/final_words.json")) if norm(w[2])]
S = [(sid, w) for sid, t in N.NARR for w in t.replace(" | ", " ").split()]        # (shot, word as written)
a = [norm(w) for _, w in S]; b = [norm(w[2]) for w in W]
st = [None] * len(S); en = [None] * len(S)
for i, j, k in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
    for q in range(k): st[i + q], en[i + q] = W[j + q][0], W[j + q][1]
known = [i for i in range(len(S)) if st[i] is not None]
if not known: raise ValueError("No transcript words match the script; refusing to invent caption timings")
for i in range(len(S)):                 # words the recogniser missed: spread between their neighbours
    if st[i] is None:
        p = max([k for k in known if k < i], default=None); nx = min([k for k in known if k > i], default=None)
        t0 = en[p] if p is not None else st[nx] - 0.3; t1 = st[nx] if nx is not None else t0 + 0.3
        n_ = (nx if nx is not None else i + 1) - (p if p is not None else i - 1); f = (i - (p if p is not None else i - 1)) / n_
        st[i] = t0 + (t1 - t0) * (f - 1 / n_); en[i] = t0 + (t1 - t0) * f
MAXC, MAXD = 76, 6.5
cues = []; cur = []
def flush():
    global cur
    if cur: cues.append(cur); cur = []
for i, (sid, w) in enumerate(S):
    if cur and (S[cur[0]][0] != sid or st[i] - en[cur[-1]] > 1.2): flush()
    cur.append(i); text = " ".join(S[k][1] for k in cur)
    nxt = S[i + 1][1] if i + 1 < len(S) else ""
    endsent = re.search(r'[.?!]["”]?$', w); comma = w.endswith((",", ":", ";"))
    dur = en[i] - st[cur[0]]
    if endsent and (len(text) > 26 or dur > 2.5): flush()
    elif comma and len(text) > 44: flush()
    elif len(text) + 1 + len(nxt) > MAXC or dur > MAXD: flush()
flush()
def ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60; return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")
out = []
for k, c in enumerate(cues):
    t0 = max(0, st[c[0]] - 0.05); t1 = en[c[-1]] + 0.45
    if k + 1 < len(cues): t1 = min(t1, st[cues[k + 1][0]] - 0.08)
    t1 = max(t1, t0 + 0.9)
    if k + 1 < len(cues): t1 = min(t1, st[cues[k + 1][0]] - 0.08)
    if t1 <= t0: raise ValueError("Caption timings overlap or run backwards; review the alignment")
    text = " ".join(S[i][1] for i in c); lines = textwrap.wrap(text, 42)
    if len(lines) > 2: lines = textwrap.wrap(text, (len(text) + 1) // 2 + 6)[:2] if len(textwrap.wrap(text, (len(text) + 1) // 2 + 6)) <= 2 else lines
    elif len(lines) == 2 and len(lines[1]) < 12: lines = textwrap.wrap(text, (len(text) + 1) // 2 + 4)
    out.append(f"{k + 1}\n{ts(t0)} --> {ts(t1)}\n" + "\n".join(lines) + "\n")
open(ROOT + "/out/film.srt", "w").write("\n".join(out))
ds = [en[c[-1]] - st[c[0]] for c in cues]; ln = [len(" ".join(S[i][1] for i in c)) for c in cues]
print(len(cues), "cues; longest", max(ln), "chars; duration", round(min(ds), 2), "-", round(max(ds), 2), "s; lines>2:", sum(o.count("\n") > 4 for o in out))
