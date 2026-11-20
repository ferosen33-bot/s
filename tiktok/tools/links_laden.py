"""Lädt Bilder aus einer Liste 'szene|session/generation|signatur' (eine pro Zeile).
Nutzung: python3 links_laden.py <zielordner> <expires> < liste.txt
Nummeriert pro Szene fortlaufend weiter, falls schon Dateien existieren."""
import os, subprocess, sys
out, exp = sys.argv[1], sys.argv[2]
B = 'https://elevenlabsusercontent.com/database/workspace/4bbeb3ac7c76488b918bcd077cb4d324/content_generation'
os.makedirs(out, exist_ok=True)
procs = []
for line in sys.stdin:
    if not line.strip(): continue
    name, path, sig = line.strip().split('|')
    n = 1
    while os.path.exists(os.path.join(out, f'{name}_{n}.png')): n += 1
    f = os.path.join(out, f'{name}_{n}.png'); open(f, 'wb').close()
    procs.append(subprocess.Popen(['curl', '-sS', '-o', f, f'{B}/{path}/content.png?Expires={exp}&KeyName=assets-cdn-key-1&Signature={sig}']))
for p in procs: p.wait()
print(len(procs), 'Bilder geladen')
