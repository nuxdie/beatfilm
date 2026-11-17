import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.p=Path(self.tmp.name)
        for d in ['build','narration','assets']: (self.p/d).mkdir()
        (self.p/'project.json').write_text('{}')
        (self.p/'build/narration.py').write_text('NARR=[("A","alpha beta gamma delta"),("B","epsilon zeta eta theta")]\nFIXED={}\n')
        (self.p/'build/edl.py').write_text('EDL={"A":[{"kind":"black"}],"B":[{"kind":"black"}]}\nEXTRA={}\n')
        self.env={**os.environ,'BEATFILM_PROJECT':str(self.p),'PYTHONPATH':str(ROOT/'build')}
    def run_tool(self,*args):
        return subprocess.run([sys.executable,str(ROOT/'beatfilm.py'),'--project',str(self.p),*args],capture_output=True,text=True,env=self.env)
    def test_selects_later_complete_retake(self):
        words='alpha beta gamma delta alpha beta gamma delta epsilon zeta eta theta'.split()
        (self.p/'narration/words.json').write_text(json.dumps([[i*.5,i*.5+.25,w] for i,w in enumerate(words)]))
        r=self.run_tool('align','unused.wav','--runs')
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn('A 4 7 4/4 2.0',r.stdout)
        self.assertIn('B 8 11 4/4 4.0',r.stdout)
    def test_missing_transcript_fails_before_editing(self):
        (self.p/'narration/words.json').write_text('[[0,1,"unrelated"]]')
        r=self.run_tool('align','unused.wav','--runs')
        self.assertNotEqual(r.returncode,0)
        self.assertIn('no matching transcript words',r.stderr)
        self.assertFalse((self.p/'build/timings.json').exists())
    def test_invalid_durations_fail_before_render(self):
        (self.p/'build/timings.json').write_text('{"A":[-1],"B":[2]}')
        r=self.run_tool('assemble','--only','A')
        self.assertNotEqual(r.returncode,0)
        self.assertIn('beat durations must be positive',r.stderr)
    def test_asset_content_not_mtime_invalidates_cache(self):
        f=self.p/'assets/image.txt'; f.write_text('before'); stamp=f.stat()
        def fingerprint():
            r=subprocess.run([sys.executable,'-c','from config import project_fingerprint; print(project_fingerprint())'],env=self.env,capture_output=True,text=True,check=True)
            return r.stdout.strip()
        first=fingerprint(); f.write_text('after!'); os.utime(f,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
        self.assertNotEqual(first,fingerprint())

if __name__=='__main__': unittest.main()
