import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'score'))
from cues import CueTimeline

class CueTests(unittest.TestCase):
    def test_fractional_cue_and_end_use_rendered_shot_start(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'timeline.json'
            p.write_text(json.dumps([{'id':'A','start':12,'dur':10,'beats':[0,3,7]}]))
            t=CueTimeline(p)
            self.assertEqual(t.at('A',1.5,offset=.2),17.2)
            self.assertEqual(t.at('A',3),22)
            self.assertEqual(t.end('A'),22)
            with self.assertRaises(ValueError): t.at('A',4)
            with self.assertRaises(ValueError): t.at('A',-1)
