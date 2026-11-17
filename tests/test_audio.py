"""Regression checks for recording selection and unsafe dub/caption output."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import numpy as np
import soundfile as sf

ROOT=Path(__file__).resolve().parents[1]

class AudioTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.p=Path(self.tmp.name)
        for d in ['build','narration','out','.cache/tmp']: (self.p/d).mkdir(parents=True,exist_ok=True)
        (self.p/'project.json').write_text('{}')
        (self.p/'build/narration.py').write_text('NARR=[("A","alpha beta gamma delta"),("B","epsilon zeta eta theta")]\nFIXED={}\n')
        (self.p/'build/edl.py').write_text('EDL={}\nEXTRA={}\n')
    def run_tool(self,*args):
        return subprocess.run([sys.executable,str(ROOT/'beatfilm.py'),'--project',str(self.p),*args],capture_output=True,text=True)
    def test_real_audio_cut_has_positive_timings_and_uses_retake(self):
        words='alpha beta gamma delta alpha beta gamma delta epsilon zeta eta theta'.split()
        W=[[i*.5+.1,i*.5+.35,w] for i,w in enumerate(words)]
        (self.p/'narration/words.json').write_text(json.dumps(W))
        sr=48000; audio=np.zeros(7*sr,np.float32)
        for a,b,_ in W:
            x=np.arange(round((b-a)*sr))/sr
            v=.12*np.sin(2*np.pi*180*x)*np.sin(np.pi*x/(b-a))**2
            start=round(a*sr); audio[start:start+len(v)]=v
        src=self.p/'recording.wav'; sf.write(src,audio,sr)
        r=self.run_tool('align',str(src),'--no-refine')
        self.assertEqual(r.returncode,0,r.stderr)
        timings=json.loads((self.p/'build/timings.json').read_text())
        self.assertEqual(set(timings),{'A','B'})
        self.assertTrue(all(v>0 for row in timings.values() for v in row))
        report=(self.p/'narration/alignment-report.txt').read_text()
        self.assertIn('[A]     2.1-',report)
        self.assertTrue((self.p/'narration/A.wav').exists())
    def test_unfittable_dub_does_not_publish_output(self):
        (self.p/'narration/ru').mkdir()
        sr=48000; t=np.arange(4*sr)/sr
        sf.write(self.p/'narration/ru/A.wav',.1*np.sin(2*np.pi*180*t),sr)
        (self.p/'build/timings_ru.json').write_text('{"A":[4.9]}')
        (self.p/'out/timeline.json').write_text('[{"id":"A","start":0,"dur":1,"beats":[0]}]')
        r=self.run_tool('dub','ru')
        self.assertNotEqual(r.returncode,0)
        self.assertIn('shorten or rerecord',r.stderr)
        self.assertFalse((self.p/'out/film-final-ru.mp4').exists())
    def test_captions_refuse_unmatched_transcript(self):
        (self.p/'.cache/tmp/final_words.json').write_text('[[0,1,"unrelated"]]')
        r=self.run_tool('captions')
        self.assertNotEqual(r.returncode,0)
        self.assertIn('refusing to invent',r.stderr)
        self.assertFalse((self.p/'out/film.srt').exists())

if __name__=='__main__': unittest.main()
