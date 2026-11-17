#!/usr/bin/env python3
"""Scripted camera moves + screen recording for Minecraft (spectator mode).
Mouse: 0.15 deg per pixel at sensitivity 0.5 (yaw right = +dx, pitch down = +dy)."""
import ctypes, time, subprocess, math, sys, os, threading
sys.path.insert(0, os.path.dirname(__file__)); import mcctl as m
_x=ctypes.CDLL("libX11.so.6"); _t=ctypes.CDLL("libXtst.so.6")
_x.XOpenDisplay.restype=ctypes.c_void_p
_t.XTestFakeRelativeMotionEvent.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_ulong]
_x.XFlush.argtypes=[ctypes.c_void_p]
_d=_x.XOpenDisplay(None)
DEG=1/0.15
def rel(dx,dy):
    _t.XTestFakeRelativeMotionEvent(_d,int(dx),int(dy),0); _x.XFlush(_d)
def ease(u,kind="smooth"):
    if kind=="linear": return u
    if kind=="in": return u*u
    if kind=="out": return 1-(1-u)**2
    return u*u*(3-2*u) if kind=="smooth" else u
def look(yaw=0,pitch=0,dur=0.4,kind="smooth",hz=240):
    """rotate camera by yaw/pitch degrees over dur seconds."""
    tx,ty=yaw*DEG,pitch*DEG; sx=sy=0.0; t0=time.perf_counter()
    while True:
        u=min(1,(time.perf_counter()-t0)/dur) if dur>0 else 1
        e=ease(u,kind); wx,wy=tx*e,ty*e
        dx,dy=round(wx-sx),round(wy-sy)
        if dx or dy: rel(dx,dy); sx+=dx; sy+=dy
        if u>=1: break
        time.sleep(1/hz)
class Rec:
    """with Rec('name'): ... -> raw/name.mkv (2560x1080@60 hevc)"""
    def __init__(s,name,fps=60,q=21):
        s.path=name if "/" in name else f"/home/n/Videos/three-voids/raw/{name}.mkv"; s.fps=fps; s.q=q
    def __enter__(s):
        s.p=subprocess.Popen(["ffmpeg","-loglevel","error","-y","-f","x11grab","-framerate",str(s.fps),"-video_size","2560x1080","-i",":0.0+1080,1080",
          "-c:v","hevc_nvenc","-preset","p5","-rc","constqp","-qp",str(s.q),"-pix_fmt","yuv420p",s.path],stdin=subprocess.PIPE)
        time.sleep(1.0); return s
    def __exit__(s,*a):
        time.sleep(0.3); s.p.communicate(b"q",timeout=20)
def hold(keys,dur):
    for k in keys: m.keydown(k)
    time.sleep(dur)
    for k in keys: m.keyup(k)
def move(keys=(),dur=1.0,yaw=0,pitch=0,kind="linear"):
    """hold movement keys while rotating camera."""
    for k in keys: m.keydown(k)
    try: look(yaw,pitch,dur,kind)
    finally:
        for k in keys: m.keyup(k)
def _clip():
    for i in range(4):
        try:
            o=subprocess.run([sys.executable,os.path.join(os.path.dirname(os.path.abspath(__file__)),"clip.py")],capture_output=True,text=True,timeout=4).stdout.strip()
            if o.startswith("/execute"): return o
        except subprocess.TimeoutExpired: pass
        time.sleep(0.3)
    raise RuntimeError("clipboard")
def pos():
    """F3+C -> (dim,x,y,z,yaw,pitch)"""
    for attempt in range(3):
        m.keydown("F3"); time.sleep(0.15); m.keydown("c"); time.sleep(0.08); m.keyup("c"); time.sleep(0.08); m.keyup("F3"); time.sleep(0.4)
        try:
            p=_clip().split(); return (p[2].split(":")[1],float(p[6]),float(p[7]),float(p[8]),float(p[9])%360,float(p[10]))
        except Exception: time.sleep(0.5)
    raise RuntimeError("pos failed")
def face(yaw=None,pitch=None,dur=0.3):
    """absolute orientation. MC yaw: 0=south(+z), 90=west(-x), 180=north, 270=east."""
    d,x,y,z,cy,cp=pos(); dy=0 if yaw is None else ((yaw-cy+180)%360-180); dp=0 if pitch is None else pitch-cp
    look(dy,dp,dur)
def fly_on():
    """double-tap space to start flying (call once after each warp; harmless check via pos)."""
    y0=pos()[2]; time.sleep(0.5); 
    if abs(pos()[2]-y0)<0.01:
        hold(["space"],0.4); y1=pos()[2]; time.sleep(0.6); y2=pos()[2]
        if y1-y0>2 and abs(y2-y1)<0.3: return True   # already flying
    m.keydown("space"); time.sleep(0.06); m.keyup("space"); time.sleep(0.09); m.keydown("space"); time.sleep(0.06); m.keyup("space"); time.sleep(0.3)
    return True
