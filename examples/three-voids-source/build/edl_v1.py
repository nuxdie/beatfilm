# Edit decision list. Each shot = list of parts; 'w' = share of the shot's duration, 'd' = fixed seconds.
# video parts: src (2560x1080 game capture, centre-cropped to 1920 unless crop:'none'), ss, speed, grade, cropx/pan
# still parts: kind:'still', kb=[[cx,cy,h],...] in units of image height. split parts: left gfx half + right game half.
G = "clips/gfx/"; R = "raw/"; S = "stills/"
def gfx(i, **k): return dict(src=G + i + ".mp4", crop="none", **k)
EXTRA = {"M3b": 2.2, "S4a": 1.0, "U5a": 2.5, "U5b": 1.0, "M2a": 1.0}     # extra seconds on top of narration length
EDL = {
 "C1": [gfx("C1")], "C2": [gfx("C2")], "C3": [gfx("C3")], "C4": [gfx("C4")], "C5": [gfx("C5")],
 "P1a": [gfx("P1a")], "P1b": [gfx("P1b")], "P1c": [gfx("P1c")],
 "M2a": [dict(src=R + "MA1b_walk_along_long.mkv", ss=2.3)],
 "M2b": [dict(src=R + "MA2_track_slow.mkv", ss=2.0, d=23.5),
         dict(kind="still", src=S + "MA11_memes.png", kb=[[0.9, 0.6, 0.7], [1.6, 0.55, 0.7]], w=1),
         dict(kind="still", src=S + "MA5_full.png", kb=[[1.185, 0.5, 1.0], [1.185, 0.5, 0.86]], w=1)],
 "M2c": [dict(kind="still", src=S + "MA6_sky_dither.png", kb=[[1.62, 0.42, 0.42], [1.85, 0.5, 0.42]], w=1),
         dict(kind="still", src=S + "MA10_ship.png", kb=[[1.3, 0.5, 0.85], [1.38, 0.5, 0.6]], w=1),
         dict(kind="still", src=S + "MA8_woman.png", kb=[[1.2, 0.5, 0.95], [1.22, 0.55, 0.7]], w=1.3)],
 "M2d": [dict(kind="still", src=S + "MA9_sign.png", kb=[[1.0, 0.45, 0.8], [1.12, 0.41, 0.32]], ease="out")],
 "M3a": [dict(src=R + "B1b_vow_flyover.mkv", ss=2.5, w=1.1), dict(src=R + "B3_vow_orbit.mkv", ss=4, w=1)],
 "M3b": [dict(src=R + "G2_vow_griefed_flyover.mkv", ss=3)],
 "M3c": [dict(src=R + "SP2_spawn_pan.mkv", ss=6)],
 "M3d": [dict(src=R + "H3_nether60k_low.mkv", ss=6, speed=1.5, grade="nether")],
 "M3e": [dict(src=R + "SP1b_spawn_glide_east_day.mkv", ss=3, w=1), dict(src=R + "SP3_lavacast_rise.mkv", ss=3, w=1),
         dict(src=R + "W1_giant_walls_5k.mkv", ss=3, w=0.7), dict(src=R + "SP4_roof_circuit_glide.mkv", ss=4, w=0.8)],
 "S4a": [dict(kind="split", left=G + "S4a_left.mp4", src=R + "SP5_roof_topdown.mkv", ss=4)],
 "S4b": [dict(kind="split", left=G + "S4b_left.mp4", src=R + "B3_vow_orbit.mkv", ss=13)],
 "S4c": [dict(kind="split", left=G + "S4c_left.mp4", src=R + "SP2_spawn_pan.mkv", ss=24)],
 "S4d": [gfx("S4d", d=6.0), dict(src=R + "PS1_player_spawn_DAY.mkv", ss=2.5)],
 "M4e": [dict(src=R + "H4_nether_diag.mkv", ss=5, speed=3, grade="nether", w=1), dict(src=R + "W2_wall_canyon_road.mkv", ss=3, speed=1.5, w=1),
         dict(src=R + "PY2_pyramid_rise.mkv", ss=4, speed=1.5, w=1), dict(src=R + "SP4_roof_circuit_glide.mkv", ss=16, speed=1.5, w=1)],
 "U5a": [gfx("U5a")], "U5b": [gfx("U5b")], "U5c": [gfx("U5c")], "U5d": [gfx("U5d")],
 "U6a": [gfx("U6a")], "U6b": [gfx("U6b")], "U6c": [gfx("U6c")], "U6d": [gfx("U6d")], "U6e": [gfx("U6e")], "U6f": [gfx("U6f")],
 "E1": [gfx("E1")],
 "E2": [dict(src=R + "H5_nether_negX.mkv", ss=6, speed=2, grade="nether", w=1), dict(src=R + "W1_giant_walls_5k.mkv", ss=9, w=0.8),
        dict(src=R + "PY1_pyramid_walk_lookup.mkv", ss=3, w=1), dict(src=R + "SP3_lavacast_rise.mkv", ss=20, w=0.7),
        dict(src=R + "MA2_track_slow.mkv", ss=8, w=1), dict(kind="still", src=S + "MA5_full.png", kb=[[1.185, 0.5, 0.9], [1.185, 0.5, 1.0]], w=1)],
 "E3": [dict(src=R + "MA4_walk_up.mkv", ss=2.2)],
 "E4": [dict(kind="still", src=S + "MA5_full.png", kb=[[1.185, 0.5, 1.0], [1.185, 0.40, 0.05]], ease="smooth", fadeout=0.5, w=1), gfx("E4", ss=1.2, d=3.6)],
 "E5": [gfx("E5")],
}
