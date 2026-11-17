"""Project settings and content-based render dependencies (no import-time rendering)."""
import hashlib
import json
import os
from pathlib import Path

TOOLROOT = str(Path(__file__).resolve().parent.parent)
ROOT = str(Path(os.environ.get('BEATFILM_PROJECT', Path(TOOLROOT) / 'examples/demo')).resolve())
CFG = json.loads((Path(ROOT) / 'project.json').read_text())
TMP = str(Path(ROOT) / '.cache/tmp')
SEG = str(Path(ROOT) / '.cache/segments')
for directory in (TMP, SEG, str(Path(ROOT) / 'out')):
    Path(directory).mkdir(parents=True, exist_ok=True)
codec = CFG.get('encoder', 'libx264')
if codec == 'libx264':
    ENC = ['-c:v', codec, '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-r', '60']
elif codec == 'h264_nvenc':
    ENC = ['-c:v', codec, '-preset', 'p6', '-rc', 'constqp', '-qp', '17', '-pix_fmt', 'yuv420p', '-r', '60']
else:
    raise ValueError('encoder must be libx264 or h264_nvenc')


def project_fingerprint():
    """Conservative invalidation: hash project inputs and toolkit source, never outputs.

    Cache is local to one process; inputs must not be edited during a build.
    External symlinked files are read by content. Large media will cost a hash pass.
    """
    if hasattr(project_fingerprint, '_value'):
        return project_fingerprint._value
    h = hashlib.sha256()
    for base, names in [(Path(ROOT), ['project.json', 'build', 'tools', 'assets', 'raw', 'stills', 'clips', 'narration']),
                        (Path(TOOLROOT), ['build', 'score'])]:
        for name in names:
            p = base / name
            files = [p] if p.is_file() else sorted(p.rglob('*')) if p.exists() else []
            for f in files:
                if not f.is_file() or '__pycache__' in f.parts or f.suffix in {'.pyc', '.log'}:
                    continue
                h.update(str(f.relative_to(base)).encode())
                with f.open('rb') as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                        h.update(chunk)
    project_fingerprint._value = h.hexdigest()
    return project_fingerprint._value
