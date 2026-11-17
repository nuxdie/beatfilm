#!/usr/bin/env python3
"""bt.py <Warp|-> <up_secs> <yaw> <pitch> <take_name> '<steps json>' [pre-move json: [["w",3],...]]
warp (or stay with '-'), rise, optional pre-moves, face, then record the take (HUD must be hidden)."""
import sys,os,time,signal,json,subprocess
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); import mcctl as m, cam
ALL=["F3","c","space","shift","w","a","s","d","Control_L"]
def release():
    for k in ALL: m.keyup(k)
signal.signal(signal.SIGALRM,lambda *a:(release(),os._exit(3))); signal.alarm(60)
try:
    w,up,yaw,pitch,name,steps=sys.argv[1],float(sys.argv[2]),float(sys.argv[3]),float(sys.argv[4]),sys.argv[5],sys.argv[6]
    pre=json.loads(sys.argv[7]) if len(sys.argv)>7 else []
    assert m.to_game()
    if w!="-": m.chat("/warp "+w); time.sleep(6); cam.fly_on()
    if up>0: cam.hold(["space"],up)
    for keys,d,*r in pre:
        if r: cam.face(r[0],None,0.25)
        cam.hold(keys.split("+"),d)
    cam.face(yaw,pitch,0.3); time.sleep(0.8)
finally: release()
signal.alarm(0)
sys.exit(subprocess.run([sys.executable,os.path.join(os.path.dirname(os.path.abspath(__file__)),"take.py"),name,steps]).returncode)
