#!/usr/bin/env python3
"""Scouting CLI for the Minecraft client (HUD must stay hidden with F1; it is hidden now).
  scout.py warp <Name>            teleport, enable flight, print position + server reply
  scout.py tp <x> <y> <z> [dim]   (2b2t.place only) teleport; dim = overworld|nether|end
  scout.py scroll up|down <n>     spectator fly speed
  scout.py pos                    print (dim,x,y,z,yaw,pitch)
  scout.py face <yaw> <pitch>     absolute look. yaw 0=south(+z) 90=west(-x) 180=north(-z) 270=east(+x); pitch +down/-up
  scout.py fly <keys> <secs>      hold keys, e.g. 'w' (9 b/s) 'w+Control_L' (20 b/s) 'space' (up 7.5 b/s) 'shift' (down) 'w+Control_L+space'
  scout.py shot <label>           save scout/<label>.jpg (1280px) + scout/<label>.png full-res; prints pos
  scout.py chat "<text>"          send chat/command, print last log lines
"""
import sys,os,time,signal
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); import mcctl as m, cam
ALL=["F3","c","space","shift","w","a","s","d","Control_L"]
def release():
    for k in ALL: m.keyup(k)
signal.signal(signal.SIGALRM,lambda *a:(release(),sys.exit("TIMEOUT")))
signal.alarm(110)
ROOT="/home/n/Videos/three-voids/scout/"
try:
    a=sys.argv[1:]; assert m.to_game(),"could not get in game"
    if a[0]=="warp":
        m.chat("/warp "+a[1]); time.sleep(7); print(m.log(3).strip()); cam.fly_on(); print(cam.pos())
    elif a[0]=="tp":
        m.chat("/tp "+" ".join(a[1:])); time.sleep(float(os.environ.get("TPWAIT","6"))); print(m.log(2).strip()); print(cam.pos())
    elif a[0]=="scroll":
        import subprocess
        subprocess.run(["xdotool","click","--repeat",a[2],"--delay","60","4" if a[1]=="up" else "5"])
    elif a[0]=="survey":
        # survey <label> <x> <y> <z> [dim] [pitch]: 4 views (S,W,N,E) tiled 2x2 -> scout/<label>.jpg
        from PIL import Image
        m.chat("/tp "+" ".join(a[2:6])); time.sleep(float(os.environ.get("TPWAIT","7")))
        pitch=float(a[6]) if len(a)>6 else 25
        sheet=Image.new("RGB",(1600,676))
        for i,yaw in enumerate([0,90,180,270]):
            cam.face(yaw,pitch,0.25); time.sleep(float(os.environ.get("SETTLE","1.2")))
            sheet.paste(m.grab().resize((800,338)),((i%2)*800,(i//2)*338))
        sheet.save(ROOT+a[1]+".jpg",quality=85); print(ROOT+a[1]+".jpg  views: TL=south(+z) TR=west(-x) BL=north(-z) BR=east(+x)")
    elif a[0]=="sky":
        # sky: look straight up, report sky brightness (day ~ >120 blue), then restore pitch
        d,x,y,z,yw,pt=cam.pos(); cam.look(0,-90-pt-0.01+0.0,0.3) if pt>-89 else None; time.sleep(0.6)
        im=m.grab().resize((16,8)); px=list(im.getdata()); r=sum(p[0] for p in px)/len(px); g=sum(p[1] for p in px)/len(px); b=sum(p[2] for p in px)/len(px)
        cam.face(None,pt,0.3); print("sky rgb %.0f %.0f %.0f"%(r,g,b), "DAY" if b>150 else "NIGHT/DUSK")
    elif a[0]=="goto":
        # goto <x> <y> <z> [speed b/s=9]: fly there (museum creative-style flight). keeps final facing of travel direction
        import math
        tx,ty,tz=map(float,a[1:4]); spd=float(a[4]) if len(a)>4 else 9.0
        for it in range(8):
            d,x,y,z,yw,pt=cam.pos(); dx,dy,dz=tx-x,ty-y,tz-z; hd=math.hypot(dx,dz)
            if hd<0.35 and abs(dy)<0.3: break
            if abs(dy)>=0.3: cam.hold(["space" if dy>0 else "shift"],max(0.05,min(8,abs(dy)/7.5*(0.9 if abs(dy)>3 else 0.5))))
            if hd>=0.35:
                yaw=math.degrees(math.atan2(-dx,dz))%360; cam.face(yaw,None,0.25)
                keys=["w"]; t=hd/spd
                if hd<4: t=hd/4.3*0.8; keys=["w"]  # short hop
                cam.hold(keys,max(0.05,min(10,t*0.92))); time.sleep(0.5)
        print(cam.pos())
    elif a[0]=="pos": print(cam.pos())
    elif a[0]=="face": cam.face(float(a[1]),float(a[2])); time.sleep(0.3); print(cam.pos())
    elif a[0]=="fly":
        cam.hold(a[1].split("+"),float(a[2])); time.sleep(0.3); print(cam.pos())
    elif a[0]=="shot":
        time.sleep(0.5); im=m.grab(); im.save(ROOT+a[1]+".png"); im.resize((1280,540)).save(ROOT+a[1]+".jpg",quality=85); print(ROOT+a[1]+".jpg", cam.pos())
    elif a[0]=="chat":
        m.chat(a[1]); time.sleep(2); print(m.log(6))
finally:
    release()
