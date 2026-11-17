"""End-to-end render in an isolated project; validates stale-cache recovery too."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1]

def run(*args):
    r=subprocess.run(list(map(str,args)),check=True,capture_output=True,text=True)
    print(r.stdout,flush=True)
    return r.stdout

def probe(p):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(p)]))

with tempfile.TemporaryDirectory(prefix='beatfilm-test-') as d:
    p=Path(d)/'project'
    shutil.copytree(ROOT/'examples/demo',p,ignore=shutil.ignore_patterns('out','.cache','narration','__pycache__'))
    def tool(*a): return run(sys.executable,ROOT/'beatfilm.py','--project',p,*a)
    tool('demo'); tool('assemble','--guide')
    meta=probe(p/'out/film-final.mp4')
    assert abs(float(meta['format']['duration'])-30)<.1
    assert {s['codec_type'] for s in meta['streams']}=={'video','audio'}
    decoded=subprocess.check_output(['ffmpeg','-v','error','-i',str(p/'out/film-final.mp4'),'-vn','-f','f32le','-ac','2','-ar','48000','-'])
    audio=np.frombuffer(decoded,dtype=np.float32)
    assert np.isfinite(audio).all() and .001<float(np.sqrt(np.mean(audio**2)))<1
    assert float(np.abs(audio).max())<=1, 'encoded audio must not clip'
    video=next(s for s in meta['streams'] if s['codec_type']=='video')
    assert (video['width'],video['height'],video['avg_frame_rate'])==(1920,1080,'60/1')
    tool('review',p/'out/review.jpg','A','B','C')
    assert (p/'out/review.jpg').stat().st_size>1000
    report=(p/'out/mix-report.txt').read_text(); assert 'true peak' in report
    second=tool('assemble','--reuse'); assert all(f'{sid}: reused' in second for sid in 'ABC')
    def frame():
        b=subprocess.check_output(['ffmpeg','-v','error','-ss','4','-i',str(p/'out/film-final.mp4'),'-frames:v','1','-f','image2pipe','-c:v','png','-'])
        return hashlib.sha256(b).hexdigest()
    before=frame()
    (p/'build/timings.json').write_text('{"A":[3,7],"B":[5,5],"C":[5,5]}')
    tool('demo'); changed=tool('assemble','--reuse'); assert 'A: rendered' in changed
    assert frame()!=before,'changing a beat must change the corresponding rendered picture'
    # Fit stand-ins to the unchanged picture, without downloading ASR weights.
    (p/'narration/ru').mkdir()
    for sid in 'ABC': shutil.copy2(p/'narration'/f'{sid}.wav',p/'narration/ru'/f'{sid}.wav')
    shutil.copy2(p/'build/timings.json',p/'build/timings_ru.json')
    tool('dub','ru')
    assert abs(float(probe(p/'out/film-final-ru.mp4')['format']['duration'])-30)<.1
    print('PASS: render, streams, duration, guide, review, mix, reuse, changed cue, dub',flush=True)
