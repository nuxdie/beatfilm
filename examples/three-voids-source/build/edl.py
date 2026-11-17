# Edit decision list. Each shot = list of parts; 'w' = share of the shot's duration, 'd' = fixed seconds.
# video parts: src (2560x1080 game capture, centre-cropped to 1920 unless crop:'none'), ss, speed, grade, cropx/pan
# still parts: kind:'still', kb=[[cx,cy,h],...] in units of image height. split parts: left gfx half + right game half.
# 'b' = the (fractional) narration beat a part starts on; beats are the ' | ' marks in narration.py.
# Everything is anchored to beats, so when the real narration timings go into build/timings.json the picture follows.
G = "clips/gfx/"; R = "raw/"; S = "stills/"
def gfx(i, **k): return dict(src=G + i + ".mp4", crop="none", **k)
BEATW = {"M3c": 3.0}     # extra weight per beat (in words): lists where every item needs its own breath
EXTRA = {"M3b": 3.0, "M3c": 3.5, "S4a": 1.0, "U5a": 2.5, "U5b": 1.0, "M2a": 1.0, "E4": 2.5, "U6a": 1.0}     # extra seconds on top of narration length
def mp(shot, **k):
    part = {x: k.pop(x) for x in ("b", "w", "d", "cuts") if x in k}
    return dict(kind="map", shot=shot, args=k, **part)
def v(name, ss=2.5, **k): return dict(src=R + name + ".mkv", ss=ss, **k)
def st(name, kb, **k): return dict(kind="still", src=S + name + ".png", kb=kb, **k)
def g(i, **k): return dict(kind="gfxr", id=i, **k)                 # graphics scene rendered to length; cues/keys/ev are in beats
def hl(*ev, **k): return g("HL", ev=list(ev), **k)                 # the whole painting, parts lit in turn: (beat0, beat1, region)
def split(left, name, ss, **k): return dict(kind="split", leftr=left, src=R + name + ".mkv", ss=ss, **k)
PETALS = (1180, 2150, 1); EDGE = (700, 1650, -1)                  # magnifier: painting x, y, side of the frame
EDL = {
 # ---- the painting: it never moves; the part being talked about is lit and the rest falls back
 "C1": [gfx("C1")],
 "C2": [hl((0.12, 0.7, "woman"), (0.5, 1.0, "poppies"),                       # a woman / a hillside of poppies
           (1.05, 1.5, "mountains"), (1.42, 1.75, "lake"), (1.68, 2.02, "clouds"),   # mountains, a lake, clouds
           (2.08, 2.95, "dress"))],                                              # the dress, blown to the right
 "C3": [hl((0.1, 0.95, "tools"), (1.3, 2.0, "ring"))],                           # palette and brush / the black circle
 "C4": [hl((0.25, 1.0, "petals"), (0.25, 1.0, "loupe", *PETALS),                 # single petals (magnifier)
           (1.05, 2.0, "ring"), (1.05, 2.0, "loupe", *EDGE),                     # flat black, a hole cut in the file
           (2.1, 3.0, "woman"),                                                  # what is she doing
           (3.05, 4.0, "out"),                                                   # black over a finished world?
           (4.05, 5.0, "ring"), (4.3, 5.0, "brush"))],                           # the bit she hasn't got to yet
 "C5": [gfx("C5")],
 "P1a": [g("P1a", cues={"title": 1, "desc": 2, "quote": 3})],
 "P1b": [hl((0.1, 0.95, "tools"),                                                # she isn't painting the circle
            (1.05, 1.6, "ring"), (1.5, 2.0, "woman"),                            # the circle is the canvas / she's stuck
            (2.1, 3.0, "out"),                                                   # the landscape, postcard pretty
            (4.05, 5.0, "out"),                                                  # the most paintable place there is
            (5.05, 6.0, "figure"),                                               # her back to it
            (6.1, 7.0, "ring"), (6.1, 7.0, "brush"))],                           # nothing
 "P1c": [hl((0.4, 1.02, "white"), (1.08, 2.0, "ring"),                           # a blank canvas is white / he made it black
            (2.1, 3.0, "white"), (3.1, 4.0, "ring"))],                           # a white canvas ... / this one swallows
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
         v("SP4_roof_circuit_glide", 4, b=8),                                   # obsidian lasts
         v("PY1_pyramid_walk_lookup", 3, b=9)],                                 # built with that in mind
 # ---- the same picture
 "S4a": [dict(kind="split", left=G + "S4a_left.mp4", src=R + "SP5_roof_topdown.mkv", ss=4)],
 "S4b": [split(g("S4b_left", set={"t0": 0.5}), "B3_vow_orbit", 13),             # the landscape is the bases
         split(g("S4b_left", set={"t0": -9}), "N8_imperator", 4, b=1),          # the thing used the normal way
         split(g("S4b_left", set={"t0": -9}), "N3_wintermelon", 5, b=2)],       # nice to look at, seen before
 "S4c": [split(g("S4c_left", set={"t0": 0.4}), "SP2_spawn_pan", 24),            # the black circle is spawn
         hl((1.05, 2.0, "out"), b=1),                                           # the painting without the circle
         v("N12_olympus", 3, b=2), v("N6_mecca", 6), v("N4_eastmarch", 7),      # a server with some nice bases
         split(g("S4c_left", set={"t0": -9}), "SP5_roof_topdown", 8, b=3)],     # the part that looks broken
 "S4d": [hl((0.1, 1.0, "ring")),                                                # a blank canvas has no rules
         v("SP4_roof_circuit_glide", 9, b=1),                                   # neither does this server
         hl((2.05, 3.0, "figure"), b=2), v("PS1_player_spawn_DAY", 2.5, b=2.42)],   # she's a new player standing at spawn
 "M4e": [hl((0.1, 1.0, "figure")),                                              # the painting stops there, with her stuck
         v("H4_nether_diag", 5, b=1, speed=3, grade="nether"),                  # people kept going
         v("W2_wall_canyon_road", 3, b=2, speed=1.5), v("PY2_pyramid_rise", 4, speed=1.5),   # weirder than any base
         v("SP4_roof_circuit_glide", 16, b=3, speed=1.5),                       # what comes after the painting
         mp("years", b=4, h0=1500, h1=2300, xf=0.35)],                          # sixteen years
 # ---- the third void
 "U5a": [g("U5a", set={"black": 1.5})],
 "U5b": [g("U5b")],
 "U5c": [g("U5c", cues={"t1": 1, "t2": 2, "t3": 3, "t4": 4.3})],               # each label is underlined as it is read
 "U5d": [g("U5d", cues={"mark": 0.45}, set={"in0": 0.3, "in1": 2.2}),          # the painting on top: the box is where she stands
         g("TRI", b=1, cues={"a": 2, "b": 3, "c": 4, "x": 4.4}, set={"move": 2.0}),   # the three voids side by side, then into the prompt
         g("U5m", b=5, cues={"chip": (5, 0.25), "off": 6}),                     # the model behind the box
         hl((7.05, 8.0, "out"), (7.45, 8.0, "figure"), b=7),                    # the view didn't help her
         g("GRID", b=8, keys=[(8, 1), (9, 3.4), (10, 8), (11, 15)], cues={"first": (8, 0.5), "more": 10}, set={"lit0": 0.3, "wave": 2.0})],
 "U6a": [g("U6a", cues={"start": 1, "send": 1.9})],
 "U6b": [g("U6b", cues={"h1": 1, "h3": 2, "hb": 3, "hoff": 3.85}, set={"stream": 0.5, "label": 0.2, "rate": 45}),
         hl((4.05, 5.0, "out"), b=4)],                                          # that's the landscape again
 "U6c": [g("CHAT", keys=[(0, "full", 1), (0.15, "full", 1), (1.0, "label", 2.3), (4, "label", 2.45)])],
 "U6d": [g("CHAT", keys=[(0, "full", 1), (0.1, "full", 1), (0.8, "p4", 2.15), (1.1, "p4", 2.15), (1.75, "comp", 1.9), (2, "comp", 1.95)])],
 "U6e": [g("U6e", cues={"la": 1, "ra": 2, "both": 3})],
 "U6f": [g("U6f", set={"t0": 0.6}),                                             # the first idea, alone
         hl((6.05, 7.0, "figure"), b=5)],                                       # what Conway did / the woman is him
 # ---- ending
 "E1": [g("E1", cues={"la": 1, "ra": 2, "both": 3}),                            # Conway / the model / both
        g("U5b", b=4),                                                          # what's coming
        g("GRID", b=5, keys=[(5, 1), (6, 9), (7, 20), (8, 26)], cues={"first": (5, 0.3), "more": 6}, set={"lit0": 0.3, "wave": 2.2, "seed": 9}),
        g("CHAT", b=8, keys=[(8, "full", 1), (9, "p1", 1.12)], ev=[((8, -2), (9, 3), "p1")]),   # the tool wanted a portrait of itself
        g("U5b", b=9)],                                                         # so what does a human build?
 "E2": [v("N2_sv3", 3, w=1), v("N9_kingslanding", 3, w=1),
        mp("zoomout", b=1, h0=4e5, h1=4e7, hold0=0, hold1=0.3, ease="linear", cap=1),   # roads to get away from each other
        v("W1_giant_walls_5k", 9, b=2, w=1), v("PY1_pyramid_walk_lookup", 5, w=1), v("X5_fortjoe", 3, w=1),   # walls, pyramids, a crater
        st("MA11_memes", [[1.3, 0.75, 0.5], [1.75, 0.8, 0.42]], b=3),            # a wall of shrimp memes
        st("MA5_full", [[1.185, 0.5, 0.9], [1.185, 0.5, 1.0]], b=4)],
 "E3": [v("MA4_walk_up", 2.2),                                                  # no answer yet
        g("U5b", b=1),                                                          # typed nothing
        hl((2.3, 3.0, "figure"), b=2, set={"fadein": 0.5})],                    # Conway's trick
 "E4": [dict(kind="still", src=S + "MA5_full.png", kb=[[1.185, 0.5, 1.0], [1.185, 0.40, 0.2]], ease="smooth", fadeout=0.4),
        g("E4", b=1, set={"t0": 0.0})],                                         # what would you build?
 "E5": [g("E5")],
}
