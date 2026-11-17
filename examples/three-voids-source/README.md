# Three Voids — where everything is (overnight shoot + second pass, 13 Nov 2026)

## Watch first
- `out/three-voids-guide.mp4` — 720p review copy with the narration text burned in, sentence by sentence (shot.beat in brackets). 11m14s.
- `out/three-voids-roughcut.mp4` — clean 1920x1080 / 60 fps picture, silent, same cut.
- `out/timeline.json` — start time and length of every shot. `SHOTLIST.md` — the shot IDs against the script.

`out`, `raw`, `clips`, `stills` are symlinks into `/home/n/Games/three-voids-raw/` (the root disk was nearly full).

## Adding the narration
Timing is currently estimated from word count (2.5 words/s + pause). The script is 1,506 spoken words, so it runs ~11 min at that pace, not 9.
Two ways to retime to the real voice:
1. Put one audio file per shot in `narration/<ID>.wav` (IDs as in `build/narration.py`) — each shot takes its length from its file.
2. Or put shot lengths in `build/timings.json` (`{"C2": 11.4, ...}`), e.g. from timestamps in a single recording.
Then: `python3 build/assemble.py --guide` (about 10 min). With per-shot audio files present it also writes
`out/three-voids-final.mp4` with the narration laid in (tested with placeholder tones only). A single long recording
needs splitting per shot, or timestamps for `timings.json`, first.
Graphics shots can be re-rendered to an exact length: `tools/gfx/render.py <ID> --dur 11.3` (beats per clip in `clips/gfx/README.md`).

## Picture beats (how narration and picture stay in step)
In `build/narration.py` a ` | ` inside a shot's text marks a picture beat: the picture changes there. `build/edl.py` pins parts to
beats with `b=` (painting camera keys, map cuts and graphic highlights use the same beat numbers). Beat times are estimated from
word counts for now. With the real voice, give every beat its length in `build/timings.json` as a list
(`{"C4": [5.9, 5.6, 4.9, 3.2, 7.3], ...}`) and everything inside the shot follows; a single number or a per-shot audio file still
works, the beats are then spread by word count. `python3 build/review.py out.jpg M2b M3a` makes a frame-per-beat check sheet.

## Footage
- `raw/*.mkv` — 31 game takes, 2560x1080 / 60 fps HEVC (ultrawide; the edit crops the centre 1920, so there is room to reframe).
  MA* gallery (walk along the wall, slow tracking, walk-up) · PS* player at spawn, day + night · B* Valley of Wheat intact ·
  G* Valley of Wheat today · SP* spawn · W* giant lavacast walls · PY* Hardhat's Pyramid · H* nether highways.
  Second pass: N1–N12 bases from the museum (Endhaven, Space Valkyria 3, Wintermelon, Eastmarch + its sky staircase, Block Game
  Mecca, SkyMasons, Imperator's base, King's Landing, Olympus, Castle Hatehart and Valley of Melons intact) ·
  X1–X5 griefed sites on 2b2t.place today (Homeland under lava, Castle Hatehart and Valley of Melons under lavacasts,
  obsidian graffiti at The Last Templar, Fort Joe).
- Map shots are rendered from 2b2tatlas.com tiles by `tools/map/render.py` (`zoomout`: spawn to the whole world with the highway
  network and known locations · `years`: spawn in 2012, 2016, 2018, 2022, 2026 · `drift`: any move over today's map). Tiles are
  cached in `/home/n/Games/three-voids-raw/tiles`.
- `stills/*.png` — 9 lossless close-ups of the map art (full, sky dithering, disc, figure, the sign, the ship, the meme wall).
- `clips/gfx/*.mp4` — 25 rendered graphics shots (painting moves, artist page, prompt window, reply, splits, title, credit).
- `build/edl.py` — which take goes where. `scout/` — reference frames. `NOTES-coords.txt` — coordinates and warp names.

## Where it was filmed
- **2b2tmuseum.org**: map art wall = `/warp EndMapArtEvent` ("2026 New Year's Map Art Event"), Art Block at about x -29999631, z 25793.
  Also `/warp ValleyOfWheat`, `HardhatsPyramid`, `OverworldSpawnZeroZero`.
- **2b2t.place** (spectator, `/tp x y z overworld|nether|the_end`): spawn, the nether highways, present-day Valley of Wheat (13646, 0).

## Things that differ from the script — please check
- **"The same base after the grief: craters, lava, withers"** — the pair is Valley of Wheat: intact from the museum's world download,
  and the same coordinates today on 2b2t.place, where it is buried under mountain-sized cobblestone lavacasts. No craters or withers.
- **Spawn** is today's spawn: a black obsidian plain/roof with lavacast monoliths, not the classic lava-and-crater wasteland.
  The "crater at spawn" half of the split screen is the obsidian plain. No endless staircase was filmed.
- **"New player standing at spawn"** is your character seen from behind on the museum's spawn obsidian roof (day and night versions).
- 2b2t.place only has map data near spawn and along the highways; far bases (Eastmarch, the End bases) were empty there.
- The typed question in the prompt shot has the comma from the script; your real screenshot has none.
- "A blank canvas is white" (P1c): the disc is shown white for a moment as an illustration. That alters Conway's image on screen;
  remove `white=[...]` from P1c in `build/edl.py` if you would rather not.
- "Pyramids" is the inside of Hardhat's Pyramid frame (no exterior shot). "Staircases that go on forever" is the sky staircase at Eastmarch.
- The highway web is drawn from Atlas's highway list at overworld scale (the roads themselves are in the Nether). Red dots are
  Atlas's known locations, not only bases.
- End credits list the painting, 2b2t, 2b2t Museum, 2b2t.place, 2b2t Atlas (+ its map sources), the wiki and Minecraft.
  The AI app/model in the prompt shots is not credited: I do not know which one it was — tell me and I will add it.
- No narration, music or sound yet.

## Machine state
- Minecraft is still running on the museum at the Art Block spot. Its instance settings were changed for filming (fullscreen,
  render distance 32, 8 GB RAM, F8 = cinematic camera, no view bobbing). Originals: `build/options.txt.orig`, `build/instance.cfg.orig`
  (copy back with the game closed).
- Desktop settings I changed during the shoot (focus-stealing prevention, do-not-disturb) are restored. Workrave was stopped during
  filming and restarted afterwards (its timers restarted).

## Third pass (13 Nov 2026, afternoon)

- **The painting no longer moves.** In C2-C4, P1b, P1c (and wherever it returns later) the whole painting stays in frame and
  the part being talked about is lit while the rest falls back (`hl(...)` parts in `build/edl.py`, regions in `REG` in
  `tools/gfx/render.py`). Two beats use a small magnifier in the black margin (single petals, the flat edge of the disc).
- **Second half is cut to the sentences.** Every shot from S4b to E4 now has ` | ` beats in `build/narration.py`, and every
  label underline, highlight, camera move and cut is anchored to one. Nothing has its own clock any more.
- **The overlay section (U5d) is rebuilt:** painting under the interface (headline in the disc, box where she stands) ->
  the three voids side by side (painting / spawn from above / prompt), lit in turn, pushing into the prompt -> the model
  chip -> the painting again -> one prompt screen becoming a wall of them ("a lot more are about to"). The wall returns in E1.
- **Script change:** U5d now ends "A lot of people have already seen this screen, or something close to it. A lot more are
  about to." E1 says "a lot more people" to match. The script .md has both.

## The score

`out/three-voids-score.wav` (48 kHz / 24 bit, same length as the cut). Source: `score/score.py` (composition) and
`score/engine.py` (piano sampler, synth voices, reverb, tape). Method after github.com/nuxdie/claude-music (the C418-style
album toolkit), rebuilt here without sfizz/Surge: sampled pianos + numpy synthesis.

    /home/n/Games/three-voids-raw/musiclibs/venv/bin/python score/score.py [--stems]
    python3 build/assemble.py --guide --reuse        # lays it under the cut (and ducks it under narration when there is one)

Every cue is placed with `at("SHOT", beat)` from the same timings the picture uses, so after the narration timings change,
re-run score.py and the music follows. Sample libraries live in /home/n/Games/three-voids-raw/musiclibs
(Upright Piano KW, CC0; Salamander Grand Piano V3 by Alexander Holm, CC BY 3.0 - credited on the end card).

What it does: an upright piano on a wobbling cassette for the painting (a four-bar question that stops one note short of
home); the same tape with pad, sine lead and music box for the museum and bases; the music is cut dead at "sooner or later
somebody does", then drone, wind and a road-like pulse for spawn and the highways; the theme over the drone for "the same
picture"; closing the game cuts the tape. The prompt is clean: a sine "cursor" blip at the caret's rate and glass bells;
the model's reply is an instant, pretty arpeggio. In U6f the machine's voice plays the piano's theme and on "The woman in
the painting is him" the missing note finally sounds. E2 is the full museum tune. The last statement of the question, before
"What would you build?", leaves the note out again.
