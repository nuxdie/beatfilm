"""transcribe.py <audio> <out.json>: word-level transcript (faster-whisper, CPU)."""
import sys, json
from faster_whisper import WhisperModel
LANG = sys.argv[3] if len(sys.argv) > 3 else "en"
m = WhisperModel("medium.en" if LANG == "en" else "medium", device="cpu", compute_type="int8", cpu_threads=10)
import soundfile as sf
audio, sr = sf.read(sys.argv[1], dtype='float32'); assert sr == 16000
segs, info = m.transcribe(audio, word_timestamps=True, vad_filter=True, condition_on_previous_text=False, beam_size=5, language=LANG,
                          initial_prompt="Daniel Conway, Art Block, 2b2t, Minecraft, map art, spawn, griefing, obsidian, anarchy server." if LANG == "en" else "Дэниел Конуэй, Art Block, 2b2t, Майнкрафт, мап-арт, спавн, хайвеи, гриферить, обсидиан, анархический сервер, промпт.")
words = []
for s in segs:
    for w in s.words: words.append([round(w.start, 3), round(w.end, 3), w.word.strip()])
    print(f"{s.start:7.1f} {s.text}", flush=True)
json.dump(words, open(sys.argv[2], "w"))
