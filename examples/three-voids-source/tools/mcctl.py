#!/usr/bin/env python3
"""Minecraft control helpers (xdotool + x11grab). Monitor DP-0 at +1080,1080 2560x1080."""
import subprocess, time, sys, os, io
from PIL import Image
MON=(1080,1080,2560,1080)
INST="/home/n/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances/1.21.4(1)/minecraft"
LOG=INST+"/logs/latest.log"
def sh(*a): return subprocess.run(a,capture_output=True,text=True).stdout
def wid():
    for l in sh("wmctrl","-l").splitlines():
        if "Minecraft" in l and "1.21" in l: return l.split()[0]
def geom():
    for l in sh("wmctrl","-lG").splitlines():
        if "Minecraft" in l and "1.21" in l:
            p=l.split(); return tuple(map(int,p[2:6]))
def focus():
    w=wid(); subprocess.run(["wmctrl","-ia",w]); time.sleep(0.3)
    if not focused():
        subprocess.run(["xdotool","windowfocus","--sync",str(int(w,16))],timeout=5); time.sleep(0.3)
class FocusLost(Exception): pass
def focused():
    # X input focus (NOT the EWMH active window, which can disagree)
    return "Minecraft" in sh("xdotool","getwindowfocus","getwindowname")
def guard():
    """never send input unless Minecraft is the active window (else keys land in other apps)."""
    if focused(): return
    focus(); time.sleep(0.4)
    if not focused(): raise FocusLost("Minecraft is not the active window")
def key(*k,delay=40):
    guard(); subprocess.run(["xdotool","key","--delay",str(delay),*k])
def keydown(k): guard(); subprocess.run(["xdotool","keydown",k])
def keyup(k): subprocess.run(["xdotool","keyup",k])
def typ(s):
    for i in range(0,len(s),6):
        if not focused(): raise FocusLost("focus lost while typing")
        subprocess.run(["xdotool","type","--delay","18",s[i:i+6]])
def grab(region=None):
    x,y,w,h=region or MON
    out=subprocess.run(["ffmpeg","-loglevel","error","-f","x11grab","-video_size",f"{w}x{h}","-i",f":0.0+{x},{y}","-frames:v","1","-f","image2pipe","-vcodec","png","-"],capture_output=True).stdout
    return Image.open(io.BytesIO(out)).convert("RGB")
def is_gray_button(im,box):
    c=im.crop(box).resize((8,2)); px=list(c.getdata())
    return all(abs(r-g)<14 and abs(g-b)<14 and 70<r<190 for r,g,b in px)
def menu_open():
    """Game Menu detection: 'Back to Game' and 'Disconnect' buttons, relative to window."""
    x,y,w,h=geom(); im=grab((x,y,w,h)); cx=w//2
    # gui scale auto: buttons 408*s/2 wide; test near left/right ends away from text
    sc=w/1280 if False else 1
    def b(yc): 
        return is_gray_button(im,(cx-390,yc-6,cx-300,yc+6)) and is_gray_button(im,(cx+300,yc-6,cx+390,yc+6))
    return im
import ctypes
class _XFCI(ctypes.Structure):
    _fields_=[("x",ctypes.c_short),("y",ctypes.c_short),("width",ctypes.c_ushort),("height",ctypes.c_ushort),("xhot",ctypes.c_ushort),("yhot",ctypes.c_ushort),("serial",ctypes.c_ulong),("pixels",ctypes.POINTER(ctypes.c_ulong)),("atom",ctypes.c_ulong),("name",ctypes.c_char_p)]
_x11=ctypes.CDLL("libX11.so.6"); _xf=ctypes.CDLL("libXfixes.so.3")
_x11.XOpenDisplay.restype=ctypes.c_void_p; _xf.XFixesGetCursorImage.restype=ctypes.POINTER(_XFCI); _xf.XFixesGetCursorImage.argtypes=[ctypes.c_void_p]
_dpy=None
def cursor_hidden():
    global _dpy
    if _dpy is None: _dpy=_x11.XOpenDisplay(None)
    ci=_xf.XFixesGetCursorImage(_dpy).contents
    n=ci.width*ci.height
    return not any((ci.pixels[i]>>24)&0xff for i in range(n))
def ingame_state():
    """True if the cursor is hidden (GLFW disabled cursor => in game, no GUI)."""
    return cursor_hidden()
def to_game(maxtry=4):
    focus()
    for i in range(maxtry):
        if ingame_state(): return True
        key("Escape"); time.sleep(0.6)
    return ingame_state()
def chat(cmd):
    assert to_game(), "not in game"
    key("t"); time.sleep(0.5)
    try: typ(cmd)
    except FocusLost:
        focus(); key("Escape"); raise
    time.sleep(0.25)
    if not focused(): raise FocusLost("focus lost before Return")
    subprocess.run(["xdotool","key","Return"]); time.sleep(0.4)
def log(n=15):
    return "".join(open(LOG,errors="replace").readlines()[-n:])
def shot(path,scale=1280,crop=None):
    im=grab()
    if crop: im=im.crop(crop)
    if scale and im.width>scale: im=im.resize((scale,int(im.height*scale/im.width)))
    im.save(path,quality=88)
if __name__=="__main__":
    c=sys.argv[1]
    if c=="state": focus(); print("ingame" if ingame_state() else "gui")
    elif c=="game": print(to_game())
    elif c=="chat": chat(sys.argv[2]); time.sleep(float(sys.argv[3]) if len(sys.argv)>3 else 1.5); print(log(8))
    elif c=="shot": focus() if len(sys.argv)<4 else None; shot(sys.argv[2])
    elif c=="log": print(log(int(sys.argv[2]) if len(sys.argv)>2 else 15))
def click(x,y,n=1):
    """click at monitor-relative pixel coords (2560x1080 space)."""
    subprocess.run(["xdotool","mousemove",str(MON[0]+x),str(MON[1]+y)]); time.sleep(0.15)
    subprocess.run(["xdotool","click","--repeat",str(n),"--delay","90","1"]); time.sleep(0.2)
