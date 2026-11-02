#!/usr/bin/env python3
"""Ritmo do AD: aponta trecho sem mudança na tela acima do limite (SOP do Daniel: algo muda a cada 1 a 3 s).
Compara os quadros do MP4: corte, troca de b-roll e punch-in contam como mudança; legenda trocando não conta.
Zoom lento contínuo não é detectado: confira no vídeo antes de mexer.

  python3 ritmo.py <AD.mp4> [<AD2.mp4> ...] [--limite 3.0] [--sensivel 0.3]

Sai com código 1 se algum AD tiver trecho acima do limite.
"""
import argparse, subprocess, sys
import numpy as np

FF = "ffmpeg"; FPS = 15; W, H = 90, 160   # o ~/bin/ffmpeg entra na fila
VAL_PIXEL = 20                            # diferença de cinza que conta como pixel mudado

def mudancas(mp4, sensivel):
    """Tempos (s) em que boa parte da imagem mudou de um quadro para o outro, e a duração do vídeo."""
    raw = subprocess.run([FF, "-nostdin", "-v", "error", "-i", mp4, "-vf", f"fps={FPS},scale={W}:{H},format=gray",
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.int16)
    frac = (np.abs(fr[1:] - fr[:-1]) > VAL_PIXEL).mean(axis=(1, 2))
    return [(i + 1) / FPS for i, f in enumerate(frac) if f >= sensivel], len(fr) / FPS

def trechos_longos(tempos, dur, limite):
    marcas = [0.0] + tempos + [dur]
    return [(a, b) for a, b in zip(marcas, marcas[1:]) if b - a > limite]

def mmss(t): return f"{int(t // 60)}:{t % 60:04.1f}"

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("mp4", nargs="+")
    ap.add_argument("--limite", type=float, default=3.0); ap.add_argument("--sensivel", type=float, default=0.3)
    a = ap.parse_args(); ruim = False
    for mp4 in a.mp4:
        tempos, dur = mudancas(mp4, a.sensivel); longos = trechos_longos(tempos, dur, a.limite)
        print(f"{mp4.rsplit('/', 1)[-1]}: {dur:.0f} s, {len(tempos)} mudanças, {len(longos)} trecho(s) acima de {a.limite:g} s")
        for s, e in longos: print(f"  {mmss(s)} a {mmss(e)} ({e - s:.1f} s)")
        ruim = ruim or bool(longos)
    sys.exit(1 if ruim else 0)

if __name__ == "__main__": main()
