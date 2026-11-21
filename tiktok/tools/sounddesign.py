"""Sounddesign für die Videos: dunkler Drone-Teppich, Whoosh bei Bildwechseln,
Impact am Anfang. Alles wird synthetisch erzeugt (keine Lizenzfragen).

mix(stimme_mp3, tempo, whoosh_zeiten, dauer, ziel_wav)
  - Stimme wird mit ffmpeg atempo beschleunigt (Tonhöhe bleibt gleich)
  - Drone wird unter der Stimme automatisch leiser (Ducking)
  - Ergebnis wird auf TikTok-Lautheit (-14 LUFS) normalisiert
"""
import subprocess
import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000
RNG = np.random.default_rng(7)


def lade(pfad, tempo=1.0):
    af = f'atempo={tempo:.4f}' if abs(tempo - 1) > 1e-3 else 'anull'
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', pfad, '-af', af, '-ac', '1', '-ar', str(SR),
                          '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def db(x):
    return 10 ** (x / 20)


def drone(n):
    t = np.arange(n) / SR
    out = np.zeros(n)
    for f, a in [(55.0, 1.0), (82.41, 0.55), (110.0, 0.3), (164.81, 0.12), (41.2, 0.5)]:
        for det in (-0.12, 0.12):
            ph = RNG.uniform(0, 2 * np.pi)
            out += a * np.sin(2 * np.pi * (f + det) * t + ph)
    lfo = 0.75 + 0.25 * np.sin(2 * np.pi * 0.07 * t) * np.sin(2 * np.pi * 0.031 * t + 1)
    out *= lfo
    # Wind: gefiltertes Rauschen, langsam an- und abschwellend
    wind = sosfilt(butter(2, [120, 700], 'bandpass', fs=SR, output='sos'), RNG.standard_normal(n))
    wind *= 0.6 + 0.4 * np.sin(2 * np.pi * 0.05 * t + 2)
    out = out / np.max(np.abs(out)) + 1.4 * wind / np.max(np.abs(wind))
    return out / np.max(np.abs(out))


def whoosh(dauer=0.55):
    n = int(dauer * SR)
    noise = RNG.standard_normal(n)
    out = np.zeros(n)
    # Bandpass, dessen Mittenfrequenz hoch und wieder runter läuft (in Blöcken)
    blk = 512
    for i in range(0, n, blk):
        p = i / n
        fc = 300 + 3500 * np.sin(np.pi * p) ** 2
        sos = butter(2, [fc * 0.6, min(fc * 1.6, SR / 2 - 100)], 'bandpass', fs=SR, output='sos')
        out[i:i + blk] = sosfilt(sos, noise[max(i - 2048, 0):i + blk])[-len(noise[i:i + blk]):]
    env = np.sin(np.pi * np.linspace(0, 1, n)) ** 1.5
    out *= env
    return out / np.max(np.abs(out))


def impact(dauer=2.2):
    n = int(dauer * SR)
    t = np.arange(n) / SR
    f = 32 + 40 * np.exp(-t * 6)                       # Pitch fällt
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.2)
    hit = sosfilt(butter(2, 900, 'lowpass', fs=SR, output='sos'), RNG.standard_normal(n)) * np.exp(-t * 25)
    out = boom + 0.6 * hit / np.max(np.abs(hit))
    return out / np.max(np.abs(out))


def einfuegen(spur, clip, zeit, pegel):
    i = int(zeit * SR)
    if i >= len(spur):
        return
    k = min(len(clip), len(spur) - i)
    spur[i:i + k] += clip[:k] * pegel


def mix(stimme_pfad, tempo, whoosh_zeiten, dauer, ziel):
    v = lade(stimme_pfad, tempo)
    n = int(dauer * SR)
    voice = np.zeros(n)
    voice[:min(n, len(v))] = v[:n]

    # Ducking: Hüllkurve der Stimme (50 ms), geglättet
    win = int(0.05 * SR)
    env = np.sqrt(np.convolve(voice ** 2, np.ones(win) / win, 'same'))
    env = sosfilt(butter(1, 3, 'lowpass', fs=SR, output='sos'), env)
    spricht = np.clip(env / (0.3 * np.max(env)), 0, 1)
    bed = drone(n) * (db(-27) + (db(-19) - db(-27)) * (1 - spricht))
    fade = np.minimum(1, np.arange(n) / (0.3 * SR))
    fade *= np.minimum(1, (n - np.arange(n)) / (1.5 * SR))
    bed *= fade

    fx = np.zeros(n)
    w = whoosh()
    for z in whoosh_zeiten:
        einfuegen(fx, w, max(z - 0.3, 0), db(-21))
    einfuegen(fx, impact(), 0.0, db(-10))

    out = voice / max(np.max(np.abs(voice)), 1e-6) * db(-3) + bed + fx
    out = out / max(np.max(np.abs(out)), 1e-6) * db(-1)
    roh = ziel + '.roh.f32'
    out.astype(np.float32).tofile(roh)
    # Lautheit in zwei Durchgängen messen und linear anpassen (TikTok: ca. -14 LUFS)
    # vorher leicht komprimieren (Stimme präsenter, Spitzen kleiner), dann normalisieren
    ln = 'acompressor=threshold=0.1:ratio=3:attack=5:release=150:makeup=2,loudnorm=I=-14:TP=-1.5:LRA=11'
    r = subprocess.run(['ffmpeg', '-hide_banner', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', roh,
                        '-af', ln + ':print_format=json', '-f', 'null', '-'], capture_output=True, text=True)
    import json as _j
    m = _j.loads(r.stderr[r.stderr.rindex('{'):r.stderr.rindex('}') + 1])
    ln += (f":measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
           f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', roh,
                    '-af', ln, '-ar', str(SR), '-ac', '2', ziel], check=True)
    import os
    os.remove(roh)
