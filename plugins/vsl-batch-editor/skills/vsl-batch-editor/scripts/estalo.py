"""Estalo do fim dos clipes do Seedance (modulos/04_falas.md): acha o pico de ~20 ms nos últimos 120 ms do ÁUDIO (que às
vezes é mais curto que o vídeo; o teto "duração − 0,08 s" do fluxo.py conta pelo vídeo) e, se o corte automático termina
depois do começo dele, propõe 08_auto/cortes/<clipe>.manual.json terminando 8 ms antes. Sem pico claro e corte a menos de
60 ms do fim do áudio: termina 65 ms antes do fim. Nunca mexe em .manual.json que já existe.
Veio da BATCH#3215 (23/10/2026: 7 de 25 falas passavam do estalo).
Uso (depois do `fluxo.py fazer --ate cortes`): python3 estalo.py <batch> [--gravar] <clipe> ...   (ex.: F01 F16_visiovance H1)"""
import json, os, subprocess, sys
import numpy as np

B = sys.argv[1].rstrip("/"); gravar = "--gravar" in sys.argv; nomes = [a for a in sys.argv[2:] if a != "--gravar"]
for n in nomes:
    mp4 = f"{B}/03_avatar/{'hooks' if n.startswith('H') else 'hold'}/{n}.mp4"
    auto = f"{B}/08_auto/cortes/{n}.json"
    if not os.path.exists(mp4) or not os.path.exists(auto):
        print(f"{n:16} sem {'clipe' if not os.path.exists(mp4) else 'corte automático (rode fazer --ate cortes)'}"); continue
    x = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", mp4, "-ac", "1", "-ar", "48000", "-f", "s16le", "-"],
                                     capture_output=True).stdout, np.int16).astype(float) / 32768
    da = len(x) / 48000; w = int(0.005 * 48000)
    t0 = da - 0.16; seg = x[int(t0 * 48000):]
    db = np.array([20 * np.log10(np.sqrt(np.mean(seg[i:i + w] ** 2)) + 1e-9) for i in range(0, len(seg) - w, w)])
    ts = t0 + np.arange(len(db)) * 0.005
    janela = (ts > da - 0.12) & (ts < da - 0.02)
    k = np.argmax(np.where(janela, db, -200))
    base = np.median(db[max(0, k - 8):max(1, k - 2)])
    estalo = db[k] - base >= 6
    ini = ts[k] - 0.005 if estalo else None
    cortes = json.load(open(auto))
    fim = cortes[-1][1]
    man = f"{B}/08_auto/cortes/{n}.manual.json"
    msg = f"{n:16} áudio {da:.3f}  pico {ts[k]:.3f} ({db[k]:.0f} dB, base {base:.0f})  {'ESTALO' if estalo else 'sem pico claro'}  corte termina {fim:.3f}"
    novo = None
    if estalo and fim > ini:
        novo = [list(s) for s in cortes]; novo[-1][1] = round(ini - 0.008, 3)
        msg += f"  -> manual {novo[-1][1]:.3f}"
    elif not estalo and fim > da - 0.06:
        novo = [list(s) for s in cortes]; novo[-1][1] = round(da - 0.065, 3)
        msg += f"  -> manual {novo[-1][1]:.3f} (sem pico: corta 65 ms antes do fim)"
    if novo and gravar:
        if os.path.exists(man): msg += " (já existe manual, não mexi)"
        else: json.dump(novo, open(man, "w")); msg += " (gravado)"
    print(msg)
