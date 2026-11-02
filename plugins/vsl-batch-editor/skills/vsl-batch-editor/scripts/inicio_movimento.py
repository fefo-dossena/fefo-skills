#!/usr/bin/env python3
"""Segundo em que o clipe do Kling/Seedance começa a se mexer: os primeiros quadros saem parados, 'posando' (pedido do
Fefo, BATCH#2820/2822). Diferença entre quadros na fps original (cinza 64x114); início = 1º ponto em que a média móvel
(5 quadros) chega a 45% da mediana do clipe inteiro. Limitado a `maxs`.

Uso: python3 inicio_movimento.py <clipes.mp4...>
Imprime o trecho parado detectado e o `inicio` sugerido para a cena no plano.json (pelo menos PULA_INICIO)."""
import os, re, statistics, subprocess, sys
FF = os.path.expanduser("~/bin/ffmpeg") if os.path.exists(os.path.expanduser("~/bin/ffmpeg")) else "ffmpeg"
PULA_INICIO = 0.5

def inicio(mp4, frac=0.45, maxs=1.0):
    w, h = 64, 114
    p = subprocess.run([FF, "-i", mp4, "-vf", f"scale={w}:{h},format=gray", "-f", "rawvideo", "-"], capture_output=True)
    fps = float(re.search(r"([\d.]+) fps", p.stderr.decode()).group(1)); raw = p.stdout; n = w * h
    fr = [raw[i:i + n] for i in range(0, len(raw) - n + 1, n)]
    d = [sum(abs(a - b) for a, b in zip(fr[i], fr[i + 1])) / n for i in range(len(fr) - 1)]
    med = statistics.median(d); k = 5
    for i in range(len(d) - k):
        if sum(d[i:i + k]) / k >= frac * med: return round(min(i / fps, maxs), 2), med
    return maxs, med

if __name__ == "__main__":
    for f in sys.argv[1:]:
        t, m = inicio(f)
        print(f"parado {t:.2f} s  ->  inicio {max(PULA_INICIO, t):.2f}  (mediana {m:.2f})  {os.path.basename(f)}")
