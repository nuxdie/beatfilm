"""Place score cues against the rendered picture timeline, including fractional beats."""
import json
import math
from pathlib import Path

class CueTimeline:
    def __init__(self, path):
        rows=json.loads(Path(path).read_text())
        if not rows: raise ValueError('timeline is empty')
        self.shots={row['id']:row for row in rows}
        if len(self.shots)!=len(rows): raise ValueError('duplicate shot IDs')
        self.duration=max(row['start']+row['dur'] for row in rows)

    def at(self, shot, beat=0, offset=0):
        row=self.shots[shot]; starts=row['beats']+[row['dur']]
        if not math.isfinite(beat) or not 0<=beat<=len(starts)-1:
            raise ValueError('beat index outside shot')
        if beat==len(starts)-1: t=row['dur']
        else:
            i=int(beat); t=starts[i]+(starts[i+1]-starts[i])*(beat-i)
        return row['start']+t+offset

    def end(self, shot):
        row=self.shots[shot]
        return row['start']+row['dur']
