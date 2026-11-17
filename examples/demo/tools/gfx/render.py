"""Minimal scene-renderer contract: scene ID, duration, named beat cues, output.

The generated panels and typography are original, with no external artwork.
"""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont

p = argparse.ArgumentParser()
p.add_argument('id')
p.add_argument('--dur', type=float, required=True)
p.add_argument('--out', type=Path, required=True)
p.add_argument('--set', action='append', default=[])
p.add_argument('--json', default='{}')
a = p.parse_args()
settings = dict(s.split('=',1) for s in a.set)
change = float(settings.get('change', a.dur/2))
if not 0 < change < a.dur: raise ValueError('cue must be inside the scene')
labels = {'A':('Start with an idea.','Give it a visible shape.'),
          'B':('Picture follows the sentence.','Music follows the picture.'),
          'C':('Change the timing once.','One clock. Everything follows.')}
font = os.environ.get('BEATFILM_FONT','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
with tempfile.TemporaryDirectory() as tmp:
    tmp=Path(tmp)
    for phase in range(2):
        im=Image.new('RGB',(1920,1080),(16,22,32)); d=ImageDraw.Draw(im)
        for k,label in enumerate(['SCRIPT','PICTURE','SCORE']):
            x=140+k*570; col=(111,220,176) if k==phase or k==2 else (65,78,96)
            d.rounded_rectangle((x,210,x+500,510),radius=25,fill=col)
            d.text((x+50,320),label,font=ImageFont.truetype(font,44),fill=(16,22,32))
        d.text((140,100),f'BEATFILM / {a.id} / BEAT {phase+1}',font=ImageFont.truetype(font,36),fill=(170,185,203))
        d.text((140,650),labels[a.id][phase],font=ImageFont.truetype(font,60),fill=(240,243,247))
        d.text((140,820),'Synthetic cue tones stand in for narration in this demo.',font=ImageFont.truetype(font,30),fill=(170,185,203))
        im.save(tmp/f'{phase}.png')
    listing=tmp/'frames.txt'
    listing.write_text(f"file '{tmp}/0.png'\nduration {change}\nfile '{tmp}/1.png'\nduration {a.dur-change}\nfile '{tmp}/1.png'\n")
    subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-f','concat','-safe','0','-i',str(listing),'-vf','fps=60,format=yuv420p','-t',str(a.dur),'-c:v','libx264','-preset','veryfast','-crf','20',str(a.out)],check=True)
