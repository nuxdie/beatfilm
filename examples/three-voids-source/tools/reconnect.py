#!/usr/bin/env python3
"""reconnect.py place|museum — from a 'Connection Lost' screen, the server list, or in-game on another server."""
import sys,os,time
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); import mcctl as m
ROW={"place":350,"museum":494}[sys.argv[1]]
def title(): return m.sh("xdotool","getwindowfocus","getwindowname")
m.focus()
if "Multiplayer" in title():            # connected somewhere -> disconnect
    m.to_game(); m.key("Escape"); time.sleep(0.8); m.click(1280,750); time.sleep(3)
else:
    m.click(1280,718); time.sleep(2.5)   # 'Back to Server List' (harmless on the list itself)
    if "Multiplayer" in title(): sys.exit("unexpected: still connected")
for attempt in range(4):
    m.click(1200,ROW,2); time.sleep(14)
    if "Multiplayer" in title() and m.ingame_state(): print("connected",sys.argv[1]); print(m.log(3)); sys.exit(0)
    m.focus(); m.click(1280,654); time.sleep(1); m.click(1280,718); time.sleep(20)   # dismiss error screens, wait, retry
sys.exit("failed to connect")
