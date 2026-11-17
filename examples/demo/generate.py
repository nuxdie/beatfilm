"""Generate deterministic stand-in voice clips and a beat-cued score. No downloads."""
import importlib.util
from pathlib import Path
import json
import sys
import numpy as np
import soundfile as sf
from config import ROOT, TOOLROOT
sys.path.insert(0,str(Path(TOOLROOT)/'score'))
from engine import SR, fm_bell

def load(name):
    sp=importlib.util.spec_from_file_location(name,Path(ROOT)/'build'/f'{name}.py')
    mod=importlib.util.module_from_spec(sp); sp.loader.exec_module(mod); return mod
N=load('narration'); timings=json.loads((Path(ROOT)/'build/timings.json').read_text())
(Path(ROOT)/'narration').mkdir(exist_ok=True)
notes=[]; now=0
for j,(sid,text) in enumerate(N.NARR):
    beats=timings[sid]; dur=sum(beats)
    clip=np.zeros(round((dur-.9)*SR),np.float32)
    cursor=0
    for k,b in enumerate(beats):
        # Audible pulses as placeholders, explicitly not synthesized speech.
        for off in [.25,.7,1.15,1.6,2.05]:
            t=cursor+off; n=round(.18*SR); start=round(t*SR)
            if start+n<=len(clip):
                x=np.arange(n)/SR
                clip[start:start+n]=.12*np.sin(2*np.pi*(180+j*50+k*30)*x)*np.sin(np.pi*x/.18)**2
        notes.append((60+j*4+k*7,now+cursor,now+cursor+1,.05))
        cursor+=b
    sf.write(Path(ROOT)/'narration'/f'{sid}.wav',clip,SR)
    now+=dur
music=fm_bell(notes,now,seed=42)
sf.write(Path(ROOT)/'out/film-score.wav',np.column_stack([music,music]),SR,subtype='PCM_24')
print(f'Generated {now:.2f}s of beat-cued demo audio; rerun after timing changes.')
