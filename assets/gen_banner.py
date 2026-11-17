#!/usr/bin/env python3
"""Generates assets/banner-dark.svg and assets/banner-light.svg: name over flowing contour lines."""
import math
import os
import random

W, H = 1200, 320
GX, GY = 150, 40          # noise grid
LEVELS = 16
random.seed(11)
OUT = os.path.dirname(os.path.abspath(__file__))

perm = list(range(256))
random.shuffle(perm)
perm += perm


def grad(h, x, y):
    a = h / 256 * math.tau
    return math.cos(a) * x + math.sin(a) * y


def noise(x, y):
    xi, yi = int(math.floor(x)) & 255, int(math.floor(y)) & 255
    xf, yf = x - math.floor(x), y - math.floor(y)
    u, v = xf * xf * (3 - 2 * xf), yf * yf * (3 - 2 * yf)
    aa, ab = perm[perm[xi] + yi], perm[perm[xi] + yi + 1]
    ba, bb = perm[perm[xi + 1] + yi], perm[perm[xi + 1] + yi + 1]
    x1 = grad(aa, xf, yf) + u * (grad(ba, xf - 1, yf) - grad(aa, xf, yf))
    x2 = grad(ab, xf, yf - 1) + u * (grad(bb, xf - 1, yf - 1) - grad(ab, xf, yf - 1))
    return x1 + v * (x2 - x1)


def fbm(x, y):
    v, a = 0.0, 0.5
    for _ in range(4):
        v += a * noise(x, y)
        x, y, a = x * 2.03 + 3.1, y * 2.03 + 1.7, a * 0.5
    return v


def field():
    s = 0.011
    f = [[0.0] * (GX + 1) for _ in range(GY + 1)]
    for j in range(GY + 1):
        for i in range(GX + 1):
            x, y = i * s * 1.0, j * s * 1.0 * (H / GY) / (W / GX)
            qx, qy = fbm(x, y), fbm(x + 5.2, y + 1.3)
            f[j][i] = fbm(x + 1.6 * qx, y + 1.6 * qy)
    return f


def contours(f, level):
    """Marching squares -> list of polylines in pixel coordinates."""
    sx, sy = W / GX, H / GY
    segs = []

    def lerp(a, b, va, vb):
        t = (level - va) / (vb - va) if vb != va else 0.5
        return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)

    for j in range(GY):
        for i in range(GX):
            p = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            v = [f[j][i], f[j][i + 1], f[j + 1][i + 1], f[j + 1][i]]
            edges = []
            for k in range(4):
                a, b = k, (k + 1) % 4
                if (v[a] < level) != (v[b] < level):
                    edges.append(lerp(p[a], p[b], v[a], v[b]))
            if len(edges) == 2:
                segs.append(tuple(edges))
            elif len(edges) == 4:
                segs.append((edges[0], edges[1]))
                segs.append((edges[2], edges[3]))
    # join segments into chains
    key = lambda pt: (round(pt[0], 4), round(pt[1], 4))  # noqa: E731
    ends = {}
    for idx, (a, b) in enumerate(segs):
        ends.setdefault(key(a), []).append(idx)
        ends.setdefault(key(b), []).append(idx)
    used, lines = set(), []
    for idx in range(len(segs)):
        if idx in used:
            continue
        used.add(idx)
        chain = list(segs[idx])
        for forward in (True, False):
            while True:
                tip = chain[-1] if forward else chain[0]
                nxt = next((n for n in ends.get(key(tip), []) if n not in used), None)
                if nxt is None:
                    break
                used.add(nxt)
                a, b = segs[nxt]
                other = b if key(a) == key(tip) else a
                if forward:
                    chain.append(other)
                else:
                    chain.insert(0, other)
        if len(chain) > 6:
            lines.append([(x * sx, y * sy) for x, y in chain])
    return lines


def path(pts):
    return "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts[::2] + [pts[-1]])


def svg(lines, dark):
    bg, fg, dim = ("#0b0d12", "#eceef4", "#868c9c") if dark else ("#f7f8fa", "#14161c", "#5b6170")
    a1, a2 = ("#7dd3c0", "#8b9cf0") if dark else ("#1f9e86", "#5468d4")
    paths, pulses = [], []
    for n, (lvl, group) in enumerate(lines):
        major = n % 4 == 0
        op = (0.38 if major else 0.16) if dark else (0.42 if major else 0.18)
        for pts in group:
            d = path(pts)
            paths.append(f'<path d="{d}" stroke-opacity="{op}" stroke-width="{1.3 if major else 0.9}"/>')
            if major and len(pts) > 40:
                dur = 9 + (len(pulses) * 3.7) % 9
                pulses.append(f'<path d="{d}" class="p" style="animation-duration:{dur:.1f}s;animation-delay:-{(len(pulses) * 2.3) % dur:.1f}s"/>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="qateralong">
<defs>
<linearGradient id="g" x1="0" x2="1"><stop offset="0" stop-color="{a1}"/><stop offset="1" stop-color="{a2}"/></linearGradient>
<linearGradient id="t" x1="0" x2="1"><stop offset=".35" stop-color="{fg}"/><stop offset=".8" stop-color="{a1}"/><stop offset="1" stop-color="{a2}"/></linearGradient>
<radialGradient id="v" cx=".3" cy=".55" r=".55"><stop offset="0" stop-color="{bg}" stop-opacity=".92"/><stop offset="1" stop-color="{bg}" stop-opacity="0"/></radialGradient>
<clipPath id="c"><rect width="{W}" height="{H}" rx="18"/></clipPath>
</defs>
<style>
.l path{{fill:none;stroke:url(#g);stroke-linecap:round}}
.p{{fill:none;stroke:{a1};stroke-width:2;stroke-linecap:round;stroke-opacity:.85;stroke-dasharray:40 1400;animation:flow linear infinite}}
@keyframes flow{{from{{stroke-dashoffset:1440}}to{{stroke-dashoffset:0}}}}
.cur{{animation:blink 1.1s steps(1) infinite}}
@keyframes blink{{50%{{opacity:0}}}}
@media (prefers-reduced-motion: reduce){{.p,.cur{{animation:none}}.p{{display:none}}}}
text{{font-family:ui-monospace,SFMono-Regular,"JetBrains Mono",Menlo,Consolas,"Liberation Mono",monospace}}
</style>
<g clip-path="url(#c)">
<rect width="{W}" height="{H}" fill="{bg}"/>
<g class="l">{chr(10).join(paths)}</g>
{chr(10).join(pulses)}
<rect width="{W}" height="{H}" fill="url(#v)"/>
<text x="72" y="168" font-size="76" font-weight="800" letter-spacing="-4" fill="url(#t)">qateralong</text>
<rect class="cur" x="505" y="112" width="30" height="62" fill="{a1}"/>
<text x="76" y="222" font-size="22" fill="{dim}"><tspan fill="{a1}">$</tspan> rust · java · go — arch + hyprland</text>
</g>
</svg>
'''


def main():
    f = field()
    vals = sorted(v for row in f for v in row)
    lo, hi = vals[len(vals) // 50], vals[-len(vals) // 50]
    lines = []
    for k in range(LEVELS):
        lvl = lo + (hi - lo) * (k + 0.5) / LEVELS
        lines.append((lvl, contours(f, lvl)))
    for dark in (True, False):
        name = "banner-dark.svg" if dark else "banner-light.svg"
        with open(os.path.join(OUT, name), "w") as fh:
            fh.write(svg(lines, dark))
        print(name, os.path.getsize(os.path.join(OUT, name)))


if __name__ == "__main__":
    main()
