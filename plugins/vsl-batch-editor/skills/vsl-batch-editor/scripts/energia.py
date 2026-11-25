#!/usr/bin/env python3
"""Energia do vídeo contra a referência (método Katana do Lucas, 19/11/2026; _FLUXO/QUALIDADE_DO_BATCH.md).

Mede, por segundo, o que acontece na tela: cortes, flashes e segundos com movimento (câmera, zoom, ação).
Energia = (cortes + flashes + segundos com movimento) / duração. O nosso vídeo precisa ter pelo menos 60% da
energia do ref, no vídeo inteiro e no hook (0 a 3 s). Abaixo disso, falha.

O que fazer quando falha (não regere o clipe só por isso):
  - faltam cortes: ponha mais cenas (banco ou clipe já gerado) no trecho fraco;
  - falta movimento: movimento de câmera em código no b-roll (push, pan);
  - zoom na pessoa só onde o ref faz ("zoom": true no ref_estrutura.json).

  py energia.py <ref.mp4> <nosso.mp4> [--min 0.6] [--json]
Sai com 0 (passou), 1 (abaixo do mínimo) ou 2 (erro de uso ou de leitura).
"""
import json, subprocess, sys
import numpy as np

FF = "ffmpeg"; FPS = 15; W, H = 90, 160
VAL_PIXEL = 20          # diferença de cinza que conta como pixel mudado
CORTE = 0.30            # fração da imagem que muda num corte (igual ao ritmo.py); só conta se for pico isolado
MOVE = 0.06             # fração média de pixels mudando num segundo com movimento
FLASH = 35              # salto de luminância média (0-255) que volta em até 3 quadros
HOOK = 3.0


def sinal(mp4):
    raw = subprocess.run([FF, "-nostdin", "-v", "error", "-i", mp4, "-vf", f"fps={FPS},scale={W}:{H},format=gray",
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.int16)
    if len(fr) < FPS:
        raise ValueError(f"vídeo curto demais: {mp4}")
    frac = (np.abs(fr[1:] - fr[:-1]) > VAL_PIXEL).mean(axis=(1, 2))
    luma = fr.mean(axis=(1, 2))
    return frac, luma


def medir(mp4, ini=0.0, fim=None):
    """Conta cortes, flashes e segundos com movimento em [ini, fim)."""
    frac, luma = sinal(mp4)
    dur = len(luma) / FPS
    fim = min(fim or dur, dur)
    a, b = int(ini * FPS), max(int(fim * FPS) - 1, int(ini * FPS) + 1)
    f = frac[a:b]
    # Corte = pico ISOLADO de 1 quadro, bem acima da vizinhança (mesmo critério do trava_timeline.saltos_da_fonte).
    # Pico em 2 ou mais quadros seguidos, ou vizinhança toda alta, é movimento (câmera na mão tremida), não corte:
    # o hook do ref da 4618 é um plano só com tremor e contava 5 "cortes" em 3 s (19/11/2026).
    J = FPS // 2
    alto = f >= CORTE
    corte = np.zeros(len(f), bool)
    for i in range(len(f)):
        if not alto[i] or (i and alto[i - 1]) or (i + 1 < len(f) and alto[i + 1]):
            continue
        viz = np.concatenate([f[max(0, i - J):i], f[i + 1:i + 1 + J]])
        if len(viz) == 0 or f[i] >= 3 * max(float(np.median(viz)), 0.02):
            corte[i] = True
    cortes = int(corte.sum())
    lu = luma[a:b + 1]
    flashes = 0
    for i in range(1, len(lu) - 1):
        if abs(lu[i] - lu[i - 1]) >= FLASH and any(abs(lu[j] - lu[i - 1]) < FLASH / 2 for j in range(i + 1, min(i + 4, len(lu)))):
            flashes += 1
    seg_mov = 0
    for s in range(0, len(f), FPS):
        j = f[s:s + FPS]
        j = j[~corte[s:s + FPS]]          # o corte não conta como movimento
        if len(j) and j.mean() >= MOVE:
            seg_mov += 1
    d = max(fim - ini, 1e-6)
    return {"dur": round(d, 2), "cortes": cortes, "flashes": flashes, "seg_mov": seg_mov,
            "energia": round((cortes + flashes + seg_mov) / d, 3)}


def comparar(ref, nosso, minimo=0.6):
    r, n = medir(ref), medir(nosso)
    rh, nh = medir(ref, 0, HOOK), medir(nosso, 0, HOOK)
    out = {"ref": r, "nosso": n, "ref_hook": rh, "nosso_hook": nh, "minimo": minimo}
    out["razao"] = round(n["energia"] / r["energia"], 2) if r["energia"] > 0 else None
    out["razao_hook"] = round(nh["energia"] / rh["energia"], 2) if rh["energia"] > 0 else None
    falta = []
    for nome, x, y in (("vídeo", r, n), ("hook", rh, nh)):
        if x["energia"] > 0 and y["energia"] < minimo * x["energia"]:
            pq = []
            if y["cortes"] / y["dur"] < minimo * x["cortes"] / x["dur"]:
                pq.append(f"cortes {y['cortes'] / y['dur']:.2f}/s contra {x['cortes'] / x['dur']:.2f}/s do ref")
            if y["seg_mov"] / y["dur"] < minimo * x["seg_mov"] / x["dur"]:
                pq.append(f"movimento em {100 * y['seg_mov'] / y['dur']:.0f}% do tempo contra {100 * x['seg_mov'] / x['dur']:.0f}%")
            if y["flashes"] / y["dur"] < minimo * x["flashes"] / x["dur"]:
                pq.append(f"flashes {y['flashes']} contra {x['flashes']} do ref")
            falta.append(f"{nome}: {100 * y['energia'] / x['energia']:.0f}% da energia do ref" + (" (" + "; ".join(pq) + ")" if pq else ""))
    out["falta"] = falta
    return out


def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if len(a) != 2:
        sys.exit(__doc__)
    minimo = 0.6
    if "--min" in sys.argv:
        minimo = float(sys.argv[sys.argv.index("--min") + 1]); a = [x for x in a if x != sys.argv[sys.argv.index("--min") + 1]] or a
    try:
        o = comparar(a[0], a[1], minimo)
    except (subprocess.CalledProcessError, ValueError, OSError) as e:
        print(f"energia: não consegui medir: {e}", file=sys.stderr); sys.exit(2)
    if "--json" in sys.argv:
        print(json.dumps(o, ensure_ascii=False))
    r, n = o["ref"], o["nosso"]
    print(f"ref {r['energia']:.2f}/s ({r['cortes']} cortes, {r['flashes']} flashes, {r['seg_mov']} s com movimento em {r['dur']:.0f} s) · "
          f"nosso {n['energia']:.2f}/s ({n['cortes']} cortes, {n['flashes']} flashes, {n['seg_mov']} s em {n['dur']:.0f} s)")
    if o["falta"]:
        print("energia abaixo de " + f"{100 * minimo:.0f}% do ref — " + " | ".join(o["falta"])
              + ". Acrescente cortes (mais cenas, outro trecho do clipe) ou movimento real do clipe; tremor e punch-in em código"
              " não valem (Fefo, 19/11/2026: \"só movimento real\").")
        sys.exit(1)
    def pct(x, ref_e):
        return "ref sem energia nesse trecho (nada a comparar)" if x is None or not ref_e else f"{100 * x:.0f}% do ref"
    # Ref com hook parado (energia 0 em 0-3 s) não é "0%" (M1WK4B2 Naturva LFS, 19/11/2026: dizia "ok com 0% no hook").
    print(f"energia ok: vídeo {pct(o['razao'], o['ref']['energia'])}; hook {pct(o['razao_hook'], o['ref_hook']['energia'])}"
          f" (hook nosso {o['nosso_hook']['energia']:.2f}/s, ref {o['ref_hook']['energia']:.2f}/s)")


if __name__ == "__main__":
    main()
