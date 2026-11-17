#!/usr/bin/env python3
"""Confere o export quadro a quadro, em cada metade do split:
tela preta (mesmo de 1 quadro), plano curto e piscada (take que aparece por poucos quadros).
Uso: conferir_quadros.py arquivo.mp4 [mais.mp4 ...] [--min 8]
Sai com código 1 se achar algo; os quadros suspeitos ficam listados com tempo e quadro."""
import re, subprocess, sys
import numpy as np

W, H = 108, 192
# A legenda do meio fica fora das regiões para não contar como corte.
REGIOES = {"cima": (0, 88), "baixo": (104, 192)}
MIN_PADRAO = 8  # quadros (~0,27 s a 30 fps)
DIF_TAKE = 8    # diferença média (0-255) para contar como outro take
DIF_HIST = 0.2  # na metade do b-roll, o histograma também precisa mudar


def hist(x, y):
    """Distância de histograma (0 a 1): câmera mexendo no mesmo take muda pouco; take diferente muda muito."""
    hx = np.histogram(x, bins=16, range=(0, 255))[0] / x.size
    hy = np.histogram(y, bins=16, range=(0, 255))[0] / y.size
    return np.abs(hx - hy).sum() / 2


def quadros(arq):
    cmd = ["ffmpeg", "-v", "error", "-i", arq, "-map", "0:v:0", "-vf", f"scale={W}:{H}:flags=area,format=gray",
           "-f", "rawvideo", "-"]
    dados = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(dados, np.uint8).reshape(-1, H, W).astype(np.float32)


def cortes(r):
    d = np.abs(r[1:] - r[:-1]).mean(axis=(1, 2))
    saida = []
    for i, v in enumerate(d):
        viz = np.r_[d[max(0, i - 8):i], d[i + 1:i + 9]]
        if v > 10 and v > 3 * (np.median(viz) + 1):
            saida.append(i + 1)
    return saida


def piscadas(r, maximo=4):
    """Trecho de 1 a `maximo` quadros que difere dos dois lados, com os dois lados parecidos entre si."""
    saida = []
    n = len(r)
    for t in range(1, maximo + 1):
        for i in range(1, n - t):
            antes, depois = r[i - 1], r[i + t]
            meio = r[i:i + t].mean(axis=0)
            lados = np.abs(antes - depois).mean()
            if lados < 6 and np.abs(meio - antes).mean() > 3 * lados + 10:
                saida.append((i, t))
    return saida


def resolucao(arq):
    """Regra da Trendscale: 720 no lado menor."""
    txt = subprocess.run(["ffmpeg", "-hide_banner", "-i", arq], capture_output=True, text=True).stderr
    m = re.search(r"Video:.*?(\d{3,5})x(\d{3,5})", txt)
    return int(m[1]), int(m[2])


def conferir(arq, minimo):
    q = quadros(arq)
    problemas = 0
    w, h = resolucao(arq)
    print(f"{arq.rsplit('/', 1)[-1]}: {len(q)} quadros, {w}x{h}")
    if min(w, h) != 720:
        print(f"  RESOLUCAO {w}x{h}: tem que ser 720 no lado menor")
        problemas += 1
    for nome, (a, b) in REGIOES.items():
        r = q[:, a:b]
        escuro = [i for i in range(len(r)) if np.percentile(r[i], 99.5) < 40]   # só preto mesmo: fundo preto com objeto ou cena escura não contam
        cs = cortes(r)
        limites = [0] + cs + [len(r)]
        # Plano curto só conta se o take for outro: diferente do quadro antes e do quadro depois (movimento forte não é take).
        curtos = [(a_, b_ - a_) for a_, b_ in zip(limites, limites[1:]) if b_ - a_ < minimo and 0 < a_ and b_ < len(r)
                  and np.abs(r[a_:b_].mean(axis=0) - r[a_ - 1]).mean() > DIF_TAKE
                  and np.abs(r[a_:b_].mean(axis=0) - r[b_]).mean() > DIF_TAKE
                  and (nome == "cima" or min(hist(r[a_:b_], r[a_ - 1]), hist(r[a_:b_], r[b_])) > DIF_HIST)]
        pisc = piscadas(r)
        print(f"  {nome}: {len(cs)} cortes, menor plano {min(limites[i + 1] - limites[i] for i in range(len(limites) - 1))} quadros")
        for i in escuro:
            print(f"    PRETO   {i / 30:7.2f} s (quadro {i})")
        for i, n in curtos:
            print(f"    CURTO   {i / 30:7.2f} s (quadro {i}), {n} quadros")
        for i, n in pisc:
            print(f"    PISCADA {i / 30:7.2f} s (quadro {i}), {n} quadros")
        problemas += len(escuro) + len(curtos) + len(pisc)
    return problemas


if __name__ == "__main__":
    args = sys.argv[1:]
    minimo = MIN_PADRAO
    if "--min" in args:
        k = args.index("--min")
        minimo = int(args[k + 1])
        del args[k:k + 2]
    total = sum(conferir(a, minimo) for a in args)
    print("OK: nada encontrado" if not total else f"{total} ocorrências para olhar")
    sys.exit(1 if total else 0)
