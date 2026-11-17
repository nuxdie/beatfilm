#!/usr/bin/env python3
"""Run a production tool against a project directory."""
import argparse
import os
from pathlib import Path
import runpy
import sys

HERE = Path(__file__).resolve().parent
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--project', type=Path, default=HERE / 'examples/demo')
p.add_argument('tool', choices=['assemble', 'align', 'transcribe', 'fillgaps', 'verify_narration', 'captions', 'dub', 'mix', 'review', 'demo'])
p.add_argument('arguments', nargs=argparse.REMAINDER)
a = p.parse_args()
os.environ['BEATFILM_PROJECT'] = str(a.project.resolve())
sys.path.insert(0, str(HERE / 'build'))
sys.argv = [a.tool] + a.arguments
runpy.run_path(str(HERE / ('examples/demo/generate.py' if a.tool == 'demo' else f'build/{a.tool}.py')), run_name='__main__')
