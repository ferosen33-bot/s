# Faceless TikTok-Kanal: Mystery & rätselhafte Geschichte

Sprache Deutsch · Ziel: Creator Rewards (Videos über 1 Minute) · 1 Video pro Tag

## Folgen
| # | Thema | Status |
|---|---|---|
| 1 | Kaspar Hauser | fertig: `01-kaspar-hauser/kaspar_hauser_tiktok.mp4` |
| 2 | Djatlow-Pass | fertig: `02-djatlow-pass/djatlow_pass_tiktok.mp4` |
| 3 | Mary Celeste | fertig: `03-mary-celeste/mary_celeste_tiktok.mp4` |
| 4 | Tanzwut 1518 | fertig: `04-tanzwut-1518/tanzwut_1518_tiktok.mp4` |
| 5 | Bernsteinzimmer | geplant |
| 6 | Voynich-Manuskript | geplant |
| 7 | Tunguska 1908 | geplant |
| 8 | Roanoke | geplant |
| 9 | Wow!-Signal | geplant |
| 10 | Antikythera-Mechanismus | geplant |

## Ablauf pro Folge
1. **Skript** (`skript.md`): Hook → Kontext → Steigerung → Theorien → offenes Ende mit Frage. Fakten prüfen.
2. **Stimme**: ElevenLabs, Stimme „Vitali – Deep German Narrator“, Modell eleven_v4 mit Regieanweisungen wie `[dramatically]`, `[whispers]`, `[pause]`.
3. **Wortzeiten**: Transkription mit faster-whisper → `audio/take1_words.json`.
4. **Bilder**: echte historische Bilder (gemeinfrei) + KI-Bilder im Ölgemälde-Stil für Szenen ohne echtes Material. KI-Bilder künftig direkt im Hochformat 9:16 erzeugen.
5. **Szenen** (`szenen.json`): pro Szene die ersten Wörter im Skript, das Bild und die Kamerafahrt.
6. **Rendern**: `python3 ../tools/render.py szenen.json`. Das Skript erzeugt Untertitel, Hook-Text, Kamerafahrten, Überblendungen und Filmkorn.

## Beim Hochladen in TikTok
- Schalter **„KI-generierte Inhalte“** aktivieren (KI-Stimme und KI-Bilder)
- Caption und Hashtags stehen in der jeweiligen `skript.md`
- Optional einen dunklen Ambient-Sound aus der TikTok-Bibliothek dazulegen, Lautstärke ca. 10–15 %
- Privates Konto (kein Business-Konto), abends 18–21 Uhr posten
