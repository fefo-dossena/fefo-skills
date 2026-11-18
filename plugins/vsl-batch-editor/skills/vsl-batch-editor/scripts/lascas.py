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
mx = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else None
if "--max" in sys.argv: args.remove(str(mx))
mp4 = args[0]; pos = json.load(open(args[1])) if len(args) > 1 else []

def fps_de(arq):
    """fps real do vídeo (EV exporta 60 desde 18/11/2026; TS 30). Os limites em quadros valem para 30 e escalam."""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                        "-of", "csv=p=0", arq], capture_output=True, text=True)
    try:
        a, _, b = r.stdout.strip().split(",")[0].partition("/"); v = float(a) / float(b or 1)
        return v if 1 < v < 241 else 30.0
    except (ValueError, ZeroDivisionError):
        return 30.0

FPS = fps_de(mp4); K = FPS / 30                      # K = 2 a 60 fps: 12 quadros de 30 = 24 de 60 (mesma duração, 0,4 s)
mx = mx if mx is not None else int(round(12 * K))
raw = subprocess.run([FF, "-nostdin", "-v", "error", "-i", mp4, "-vf", f"fps={FPS:g},scale=90:160,format=gray", "-f", "rawvideo", "-"],
                     capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, 160, 90).astype(np.float32)
mask = np.ones((160, 90), bool); mask[int(160 * 0.55):int(160 * 0.9), :] = False   # legenda (y 0,66-0,84)
d = np.array([np.abs(fr[i + 1] - fr[i])[mask].mean() for i in range(len(fr) - 1)])
# a 60 fps a diferença de um quadro para o outro cai à metade no movimento e não no corte: a mediana da janela (mesma
# duração, ±0,5 s) fica menor e o corte continua bem acima dela; o piso de 12 continua valendo
J = int(round(15 * K))
cut = [i + 1 for i in range(len(d)) if d[i] > 12 and d[i] > 3 * np.median(d[max(0, i - J):i + J])]
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
    print(f"  {a / FPS:7.2f}-{b / FPS:7.2f}s  {n:2d} quadros  {onde((a + b) / 2 / FPS):8s} "
          f"(antes {onde(a / FPS - 0.05)}, depois {onde(b / FPS + 0.02)}){'  A-B-A' if aba else ''}")
    achou += 1
print(f"{mp4.rsplit('/', 1)[-1]}: {len(cut)} cortes, {achou} plano(s) com até {mx} quadros")
