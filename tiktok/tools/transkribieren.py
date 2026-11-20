"""Wortgenaue Zeiten für ein Voiceover: python3 transkribieren.py take1.mp3 [take2.mp3 ...]
Schreibt <name>_words.json neben die Audiodatei und gibt den erkannten Text aus."""
import json, subprocess, sys
import numpy as np
from faster_whisper import WhisperModel
m = WhisperModel('small', device='cpu', compute_type='int8')
for f in sys.argv[1:]:
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', f, '-f', 's16le', '-ac', '1', '-ar', '16000', '-'], capture_output=True).stdout
    audio = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    segs, _ = m.transcribe(audio, language='de', word_timestamps=True)
    words, text = [], []
    for s in segs:
        text.append(s.text)
        words += [{'w': w.word.strip(), 's': round(w.start, 2), 'e': round(w.end, 2)} for w in s.words]
    json.dump(words, open(f.rsplit('.', 1)[0] + '_words.json', 'w'), ensure_ascii=False)
    print('=====', f); print(''.join(text))
