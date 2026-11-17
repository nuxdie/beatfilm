#!/usr/bin/env python3
"""take.py <name> <json-steps>  — record a scripted camera take to raw/<name>.mkv
steps: list of dicts executed in order while recording:
  {"keys":"w+Control_L","dur":20,"yaw":30,"pitch":-5,"kind":"smooth"}   (keys optional -> pure pan)
pre-roll/post-roll 1 s are added. Prints start/end pos."""
import sys,os,json,time,signal
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); import mcctl as m, cam
ALL=["F3","c","space","shift","w","a","s","d","Control_L"]
def release():
    for k in ALL: m.keyup(k)
name=sys.argv[1]; steps=json.loads(sys.argv[2])
tot=sum(s["dur"] for s in steps)+12
signal.signal(signal.SIGALRM,lambda *a:(release(),os._exit(3))); signal.alarm(int(tot)+25)
try:
    assert m.to_game(); p0=cam.pos(); time.sleep(1.2)   # let the 'copied' chat line not matter (HUD hidden)
    with cam.Rec(name):
        time.sleep(1.0)
        for s in steps:
            keys=[k for k in s.get("keys","").split("+") if k]
            cam.move(keys,s["dur"],s.get("yaw",0),s.get("pitch",0),s.get("kind","smooth"))
        time.sleep(1.0)
    print(name,"start",p0,"end",cam.pos(),"secs",tot-12)
finally:
    release()
