"""Planos curtos ("frames estranhos aparecendo por poucos frames", Fefo, BATCH#1977) num AD exportado.

Uso: python3 lascas.py <AD.mp4> [<broll_posicoes_ADn_p.json>] [--max 12]

Acha os cortes pela diferença entre quadros (ignora a faixa da legenda) e lista todo plano com até --max quadros,
dizendo se é avatar ou qual cena (pelo json de posições do fluxo). Marca "A-B-A" quando o quadro de antes e o de
depois do plano curto são parecidos: é uma piscada no meio de uma mesma imagem, o caso mais feio.
Passo fixo da checagem final, junto com o freezedetect (quadro congelado)."""
import json, subprocess, sys
import numpy as np

FF = "ffmpeg"
args = [a for a in sys.argv[1:] if not a.startswith("--")]
mx = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 12
if "--max" in sys.argv: args.remove(str(mx))
mp4 = args[0]; pos = json.load(open(args[1])) if len(args) > 1 else []
raw = subprocess.run([FF, "-nostdin", "-v", "error", "-i", mp4, "-vf", "fps=30,scale=90:160,format=gray", "-f", "rawvideo", "-"],
                     capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, 160, 90).astype(np.float32)
mask = np.ones((160, 90), bool); mask[int(160 * 0.55):int(160 * 0.9), :] = False   # legenda (y 0,66-0,84)
d = np.array([np.abs(fr[i + 1] - fr[i])[mask].mean() for i in range(len(fr) - 1)])
cut = [i + 1 for i in range(len(d)) if d[i] > 12 and d[i] > 3 * np.median(d[max(0, i - 15):i + 15])]
cuts = [0] + cut + [len(fr)]

def onde(t):
    for c, a, b, _ in pos:
        if a - 0.02 <= t < b + 0.1: return c
    return "avatar" if pos else "?"

achou = 0
for i in range(len(cuts) - 1):
    a, b = cuts[i], cuts[i + 1]; n = b - a
    if n > mx: continue
    aba = 0 < a and b < len(fr) and np.abs(fr[b] - fr[a - 1])[mask].mean() < 0.5 * min(d[a - 1], d[b - 1])
    print(f"  {a / 30:7.2f}-{b / 30:7.2f}s  {n:2d} quadros  {onde((a + b) / 60):8s} "
          f"(antes {onde(a / 30 - 0.05)}, depois {onde(b / 30 + 0.02)}){'  A-B-A' if aba else ''}")
    achou += 1
print(f"{mp4.rsplit('/', 1)[-1]}: {len(cut)} cortes, {achou} plano(s) com até {mx} quadros")
