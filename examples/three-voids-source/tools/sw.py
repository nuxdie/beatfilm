#!/usr/bin/env python3
"""sw.py <Warp> [up_secs=0] [pitch=20] — warp, rise, save 4-direction sheet scout/w_<Warp>.jpg"""
import sys,os,time,signal
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); import mcctl as m, cam
from PIL import Image
ALL=["F3","c","space","shift","w","a","s","d","Control_L"]
def release():
    for k in ALL: m.keyup(k)
signal.signal(signal.SIGALRM,lambda *a:(release(),os._exit(3))); signal.alarm(100)
try:
    w=sys.argv[1]; up=float(sys.argv[2]) if len(sys.argv)>2 else 0; pitch=float(sys.argv[3]) if len(sys.argv)>3 else 20
    assert m.to_game(); m.chat("/warp "+w); time.sleep(6); cam.fly_on()
    if up: cam.hold(["space"],up)
    p=cam.pos(); sheet=Image.new("RGB",(1600,676))
    for i,yaw in enumerate([0,90,180,270]):
        cam.face(yaw,pitch,0.25); time.sleep(1.0); sheet.paste(m.grab().resize((800,338)),((i%2)*800,(i//2)*338))
    sheet.save(f"/home/n/Videos/three-voids/scout/w_{w}.jpg",quality=80); print(w,p)
finally: release()
