# Edit decision list. Each shot = list of parts; 'w' = share of the shot's duration, 'd' = fixed seconds.
# video parts: src (2560x1080 game capture, centre-cropped to 1920 unless crop:'none'), ss, speed, grade, cropx/pan
# still parts: kind:'still', kb=[[cx,cy,h],...] in units of image height. split parts: left gfx half + right game half.
G = "clips/gfx/"; R = "raw/"; S = "stills/"
def gfx(i, **k): return dict(src=G + i + ".mp4", crop="none", **k)
BEATW = {"M3c": 3.0}     # extra weight per beat (in words): lists where every item needs its own breath
EXTRA = {"M3b": 3.0, "M3c": 3.5, "S4a": 1.0, "U5a": 2.5, "U5b": 1.0, "M2a": 1.0}     # extra seconds on top of narration length
def cam(keys, **k): return dict(kind="cam", keys=keys, **k)
def mp(shot, **k):
    part = {x: k.pop(x) for x in ("b", "w", "d", "cuts") if x in k}
    return dict(kind="map", shot=shot, args=k, **part)
def v(name, ss=2.5, **k): return dict(src=R + name + ".mkv", ss=ss, **k)
def st(name, kb, **k): return dict(kind="still", src=S + name + ".png", kb=kb, **k)
# 'b' = the (fractional) narration beat a part starts on; beats are the ' | ' marks in narration.py.
# painting camera keys: (beat, (cx, cy, view height)) in pixels of the 1920x2400 painting.
FULLP = (960, 1200, 2400)
EDL = {
 "C1": [gfx("C1")],
 "C2": [cam([(0, FULLP), (0.9, (1030, 1650, 1250)),            # a woman on a hillside of poppies
             (1.4, (760, 1120, 1150)), (1.9, (1180, 1250, 1250)),  # mountains, lake, clouds
             (2.7, (1270, 1690, 800)), (3, (1285, 1692, 780))])],  # the dress, blown to the right
 "C3": [cam([(0, (790, 1480, 440)), (0.9, (820, 1455, 420)),   # palette and brush
             (1.75, (961, 1150, 1750)), (2, (961, 1140, 1800))])], # the huge black circle
 "C4": [cam([(0, (1262, 1905, 640)), (0.9, (1180, 1960, 600)),     # single petals
             (1.3, (760, 1700, 640)), (2.15, (660, 1620, 600)),     # flat black edge
             (2.7, (900, 1440, 820)), (3.0, (905, 1436, 800)),     # what is she doing
             (3.6, (960, 1250, 2300)), (4.0, (960, 1240, 2250)),   # black over a finished world?
             (4.7, (820, 1420, 600)), (5, (800, 1418, 560))])],    # the bit she hasn't got to yet
 "C5": [gfx("C5")],
 "P1a": [dict(kind="gfxr", id="P1a", cues={"title": 1, "desc": 2, "quote": 3})],
 "P1b": [cam([(0, (860, 1400, 760)), (0.9, (890, 1385, 800)),      # she isn't painting the circle
              (1.5, (961, 1160, 1750)), (2.0, (961, 1160, 1800)),  # the circle is the canvas
              (2.6, (420, 1150, 1000)), (3.5, (1500, 1300, 1000)), # the landscape, postcard pretty
              (4.4, FULLP), (4.9, (965, 1215, 2330)),              # the most paintable place there is
              (5.5, (1022, 1500, 1000)), (6.0, (1020, 1495, 980)), # her back to it
              (6.6, (900, 1410, 640)), (7, (880, 1405, 600))])],   # nothing
 "P1c": [cam([(0, (930, 1404, 900)), (1, (945, 1300, 1500)), (2, (961, 1200, 1900)), (3, (900, 1350, 1300)),
              (3.8, (800, 1418, 600)), (4.1, (800, 1418, 590)), (4.8, FULLP), (5, (960, 1200, 2410))],
             white=[(0.45, 1.05), (2.1, 3.0)])],                   # "a blank canvas is white" / "a white canvas ..."
 "M2a": [gfx("P1a", ss=18.5), v("MA1b_walk_along_long", 2.3, b=1)],
 "M2b": [v("MA2_track_slow", 2.0),                                              # this is the 2b2t museum
         v("SP1b_spawn_glide_east_day", 3, b=1),                                # the oldest anarchy server
         mp("drift", b=2, h0=5400, h1=3400, sub="2b2t spawn today, seen from above"),   # same world since 2010
         v("X1_homeland", 3, b=3), v("X3_melons", 3),                           # no rules, grief
         v("N6_mecca", 2.5, b=4), v("N7_skymasons", 2.5),                       # the museum keeps copies
         st("MA11_memes", [[0.9, 0.6, 0.7], [1.6, 0.55, 0.7]], b=5),            # a lot of it is map art
         mp("drift", b=6, w=1.2, h0=34, h1=2500, z0=40, z1=40, ease="linear", sub="the roof over spawn, block by block"),
         st("MA5_full", [[1.185, 0.5, 1.0], [1.185, 0.5, 0.86]], w=1)],
 "M2c": [st("MA10_ship", [[1.12, 0.62, 0.2], [1.18, 0.56, 0.22]]),              # grainy
         st("MA10_ship", [[1.15, 0.55, 0.6], [1.3, 0.52, 0.85]], b=1),          # the ship next to it
         st("MA5_full", [[1.185, 0.45, 0.8], [1.185, 0.38, 0.62]], b=2),        # one flat black shape
         st("MA8_woman", [[1.72, 0.84, 0.36], [1.45, 0.42, 0.6]], b=3)],        # strong orange and blue
 "M2d": [dict(kind="still", src=S + "MA9_sign.png", kb=[[1.0, 0.45, 0.8], [1.12, 0.41, 0.32]], ease="out")],
 "M3a": [v("N3_wintermelon", 2.5),                                              # two kinds of structures
         v("N4_eastmarch", 3, b=1),                                             # the first kind is bases
         v("N1_endhaven", 2.5, b=2), v("N8_imperator", 3),                      # far out, a place to live, secret
         v("B1b_vow_flyover", 2.5, b=3),                                        # a normal Minecraft thing
         v("N10_hatehart_before", 3, b=4)],                                     # only lasts until somebody finds it
 "M3b": [v("X2_hatehart", 2.5, w=1.2), v("X4_templar", 6, w=1), v("G2_vow_griefed_flyover", 3, w=1)],
 "M3c": [mp("drift", h0=22000, h1=52000, sub="the land around spawn, from above"),
         v("SP2_spawn_pan", 6, b=1), v("H3_nether60k_low", 6, b=2, speed=1.5, grade="nether"), v("W1_giant_walls_5k", 3, b=3),
         v("PY1_pyramid_walk_lookup", 3, b=4), v("N5_eastmarch_stairs", 5.5, b=5)],
 "M3d": [v("H3_nether60k_low", 14, speed=1.5, grade="nether"),
         mp("zoomout", b=1, h0=2600, h1=66e6, hold0=0.4, hold1=1.5, cap=1)],
 "M3e": [v("SP1b_spawn_glide_east_day", 12),                                    # nobody designed it
         mp("years", b=1, h0=1230, h1=2300),                                    # sixteen years in the same place
         v("SP3_lavacast_rise", 3, b=2),                                        # more like terrain / the way I put it
         v("N11_melons_before", 3, b=4),                                        # a game with rules being played
         v("SP2_spawn_pan", 24, b=5),                                           # its players with no rules
         v("W1_giant_walls_5k", 9, b=6),                                        # nobody wrote any down
         v("X3_melons", 8, b=7),                                                # found -> destroyed
         v("SP4_roof_circuit_glide", 4, b=8),                                         # obsidian lasts
         v("PY1_pyramid_walk_lookup", 3, b=9)],                                 # built with that in mind
 "S4a": [dict(kind="split", left=G + "S4a_left.mp4", src=R + "SP5_roof_topdown.mkv", ss=4)],
 "S4b": [dict(kind="split", left=G + "S4b_left.mp4", src=R + "B3_vow_orbit.mkv", ss=13)],
 "S4c": [dict(kind="split", left=G + "S4c_left.mp4", src=R + "SP2_spawn_pan.mkv", ss=24)],
 "S4d": [gfx("S4d", d=6.0), dict(src=R + "PS1_player_spawn_DAY.mkv", ss=2.5)],
 "M4e": [dict(src=R + "H4_nether_diag.mkv", ss=5, speed=3, grade="nether", w=1), dict(src=R + "W2_wall_canyon_road.mkv", ss=3, speed=1.5, w=1),
         dict(src=R + "PY2_pyramid_rise.mkv", ss=4, speed=1.5, w=1), dict(src=R + "SP4_roof_circuit_glide.mkv", ss=16, speed=1.5, w=1)],
 "U5a": [gfx("U5a")], "U5b": [gfx("U5b")], "U5c": [gfx("U5c")], "U5d": [gfx("U5d")],
 "U6a": [gfx("U6a")], "U6b": [gfx("U6b")], "U6c": [gfx("U6c")], "U6d": [gfx("U6d")], "U6e": [gfx("U6e")], "U6f": [gfx("U6f")],
 "E1": [gfx("E1")],
 "E2": [v("N2_sv3", 3, w=1), v("N9_kingslanding", 3, w=1),
        mp("zoomout", b=1, h0=4e5, h1=4e7, hold0=0, hold1=0.3, ease="linear", cap=1),   # roads to get away from each other
        v("W1_giant_walls_5k", 9, b=2, w=1), v("PY1_pyramid_walk_lookup", 5, w=1), v("X5_fortjoe", 3, w=1),   # walls, pyramids, a crater
        st("MA11_memes", [[1.3, 0.75, 0.5], [1.75, 0.8, 0.42]], b=3),            # a wall of shrimp memes
        st("MA5_full", [[1.185, 0.5, 0.9], [1.185, 0.5, 1.0]], b=4)],
 "E3": [dict(src=R + "MA4_walk_up.mkv", ss=2.2)],
 "E4": [dict(kind="still", src=S + "MA5_full.png", kb=[[1.185, 0.5, 1.0], [1.185, 0.40, 0.05]], ease="smooth", fadeout=0.5, w=1), gfx("E4", ss=1.2, d=3.6)],
 "E5": [dict(kind="gfxr", id="E5")],
}
