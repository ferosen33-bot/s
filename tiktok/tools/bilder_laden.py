"""Lädt fertige ElevenLabs-Bilder aus gespeicherten Status-Antworten herunter.
Nutzung: python3 bilder_laden.py <zielordner> <zuordnung.json> <status1.txt> [status2.txt ...]
zuordnung.json: [["Prompt-Anfang", "szenenname"], ...]; Dateien heißen szenenname_1.png, _2 ...
Doppelte Generierungen (überlappende Abfragen) werden nur einmal geladen."""
import json, os, subprocess, sys, collections
out, mp = sys.argv[1], json.load(open(sys.argv[2]))
os.makedirs(out, exist_ok=True)
seen, items = set(), []
for f in sys.argv[3:]:
    for g in json.load(open(f))['generations']:
        if g['id'] in seen: continue
        seen.add(g['id'])
        p = g['prompt'].replace('Vertical 9:16. ', '')
        name = next((n for k, n in mp if p.startswith(k)), 'unbekannt')
        if g['status'] != 'completed':
            print('NICHT FERTIG:', name, g['status'], g.get('error_message', '')); continue
        items.append((name, g['content_url']))
cnt, procs = collections.Counter(), []
for n, u in sorted(items):
    cnt[n] += 1
    procs.append(subprocess.Popen(['curl', '-sS', '-o', os.path.join(out, f'{n}_{cnt[n]}.png'), u]))
for p in procs: p.wait()
print(len(items), 'Bilder:', dict(cnt))
