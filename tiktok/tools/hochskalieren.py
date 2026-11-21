"""Schärft und vergrößert die Szenenbilder mit Real-ESRGAN (realesr-general-x4v3, läuft auf CPU).

Nutzung (im Ordner der Folge):
    python3 ../tools/hochskalieren.py            # alle Bilder aus bilder/ -> bilder_hd/
Die HD-Bilder (lange Seite 2560 px) nutzt render.py automatisch, wenn vorhanden.
bilder_hd/ ist in .gitignore, weil es jederzeit neu erzeugt werden kann.
Modell: /home/user/models/realesr-general-x4v3.pth
(https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth)
"""
import glob, os, sys, time
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from PIL import Image

MODELL = os.environ.get('ESRGAN_MODELL', '/home/user/models/realesr-general-x4v3.pth')
ZIEL = 2560          # lange Seite der Ausgabe
KACHEL, RAND = 256, 12


class SRVGGNetCompact(nn.Module):
    def __init__(self, feat=64, conv=32, scale=4):
        super().__init__()
        self.scale = scale
        body = [nn.Conv2d(3, feat, 3, 1, 1), nn.PReLU(num_parameters=feat)]
        for _ in range(conv):
            body += [nn.Conv2d(feat, feat, 3, 1, 1), nn.PReLU(num_parameters=feat)]
        body += [nn.Conv2d(feat, 3 * scale * scale, 3, 1, 1)]
        self.body = nn.ModuleList(body)
        self.up = nn.PixelShuffle(scale)

    def forward(self, x):
        out = x
        for m in self.body:
            out = m(out)
        return self.up(out) + F.interpolate(x, scale_factor=self.scale, mode='nearest')


def lade_modell():
    net = SRVGGNetCompact()
    sd = torch.load(MODELL, map_location='cpu')
    net.load_state_dict(sd.get('params', sd))
    return net.eval()


@torch.no_grad()
def hochskalieren(net, img):
    x = torch.from_numpy(np.asarray(img.convert('RGB'), dtype=np.float32) / 255).permute(2, 0, 1)[None]
    _, _, h, w = x.shape
    out = torch.zeros(1, 3, h * 4, w * 4)
    for y in range(0, h, KACHEL):
        for xx in range(0, w, KACHEL):
            y0, x0 = max(y - RAND, 0), max(xx - RAND, 0)
            y1, x1 = min(y + KACHEL + RAND, h), min(xx + KACHEL + RAND, w)
            t = net(x[:, :, y0:y1, x0:x1])
            ty, tx = (y - y0) * 4, (xx - x0) * 4
            hh, ww = min(KACHEL, h - y) * 4, min(KACHEL, w - xx) * 4
            out[:, :, y * 4:y * 4 + hh, xx * 4:xx * 4 + ww] = t[:, :, ty:ty + hh, tx:tx + ww]
    arr = (out[0].clamp(0, 1).permute(1, 2, 0).numpy() * 255 + 0.5).astype(np.uint8)
    big = Image.fromarray(arr)
    s = ZIEL / max(big.size)
    return big.resize((round(big.width * s), round(big.height * s)), Image.LANCZOS)


def main():
    torch.set_num_threads(os.cpu_count() or 4)
    os.makedirs('bilder_hd', exist_ok=True)
    net = None
    for p in sorted(glob.glob('bilder/*')):
        ziel = os.path.join('bilder_hd', os.path.splitext(os.path.basename(p))[0] + '.png')
        if os.path.exists(ziel):
            continue
        img = Image.open(p)
        if max(img.size) >= ZIEL:
            img.convert('RGB').save(ziel); continue
        net = net or lade_modell()
        t = time.time()
        hochskalieren(net, img).save(ziel)
        print(f'{os.path.basename(p)}: {img.size} -> HD in {time.time() - t:.0f}s', flush=True)


if __name__ == '__main__':
    main()
