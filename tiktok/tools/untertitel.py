"""Erzeugt TikTok-Untertitel (.ass) aus Skript + Whisper-Wortzeiten.

Nutzung: python3 untertitel.py skript.md take_words.json ausgabe.ass
Der Sprechertext wird aus dem Abschnitt "## Sprechertext" der skript.md gelesen,
Regieanweisungen in [eckigen Klammern] werden entfernt. Die Schreibweise kommt
aus dem Skript, die Zeiten aus der Transkription.
"""
import difflib, json, re, sys

def script_words(md):
    body = md.split('## Sprechertext', 1)[1].split('\n---', 1)[0]
    body = '\n'.join(l for l in body.splitlines()[1:] if not l.startswith('#'))
    body = re.sub(r'\[[^\]]*\]', ' ', body)
    # reine Satzzeichen-Token („…“, „—“) nicht als eigenen Untertitel zeigen
    return [w for w in body.split() if re.search(r'\w', w)]

norm = lambda w: re.sub(r'[^\wäöüß]', '', w.lower())

def align(sw, ww):
    a = [norm(w) for w in sw]; b = [norm(w['w']) for w in ww]
    times = [None] * len(sw)
    for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            times[blk.a + k] = (ww[blk.b + k]['s'], ww[blk.b + k]['e'])
    # Lücken (andere Schreibweise) linear auffüllen
    i = 0
    while i < len(times):
        if times[i] is None:
            j = i
            while j < len(times) and times[j] is None: j += 1
            t0 = times[i-1][1] if i else 0.0
            t1 = times[j][0] if j < len(times) else t0 + 0.4 * (j - i)
            step = (t1 - t0) / (j - i)
            for k in range(i, j): times[k] = (t0 + step*(k-i), t0 + step*(k-i+1))
            i = j
        else: i += 1
    return times

def chunks(sw, times, max_words=3, max_chars=18):
    out, cur = [], []
    for idx, w in enumerate(sw):
        cur.append(idx)
        text = ' '.join(sw[k] for k in cur)
        # Ordnungszahlen wie „15.“ oder „26.“ sind kein Satzende
        end_punct = re.search(r'[.,:;?!…—“"]$', w) and not re.fullmatch(r'\d+\.', w)
        if end_punct or len(cur) >= max_words or len(text) >= max_chars:
            out.append(cur); cur = []
    if cur: out.append(cur)
    return [(times[c[0]][0], times[c[-1]][1], ' '.join(sw[k] for k in c)) for c in out]

def ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f'{h}:{m:02d}:{s:05.2f}'

HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,Inter ExtraBold,86,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,7,3,2,80,80,560,1
Style: Gelb,Inter ExtraBold,86,&H0034D4FF,&H0034D4FF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,7,3,2,80,80,560,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

if __name__ == '__main__':
    md, wj, out = sys.argv[1:4]
    sw = script_words(open(md, encoding='utf-8').read())
    ww = json.load(open(wj, encoding='utf-8'))
    cs = chunks(sw, align(sw, ww))
    lines = [HEADER]
    for i, (s, e, text) in enumerate(cs):
        nxt = cs[i+1][0] if i + 1 < len(cs) else e + 0.5
        e = min(max(e + 0.15, s + 0.35), nxt)  # kurz stehen lassen, nicht überlappen
        text = text.replace('„', '').replace('“', '').replace('"', '').strip(' —')
        style = 'Gelb' if re.search(r'\b(NIEMAND|KEIN|tot\.?|Mord\??)\b', text) else 'Sub'
        pop = r'{\fscx85\fscy85\t(0,90,\fscx100\fscy100)}'
        lines.append(f'Dialogue: 0,{ts(s)},{ts(e)},{style},,0,0,0,,{pop}{text.upper()}\n')
    open(out, 'w', encoding='utf-8').writelines(lines)
    print(f'{len(cs)} Untertitel geschrieben -> {out}')
