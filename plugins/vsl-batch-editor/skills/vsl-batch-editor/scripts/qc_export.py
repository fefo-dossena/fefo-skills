#!/usr/bin/env python3
"""QC do export antes de subir (regra do Fefo, 03/11/2026, depois do "último aviso" do Dan).

Uso: fila python3 qc_export.py <export.mp4> <legendas.ass> [--saida pasta] [--palavras palavras.json] [--voz voz.wav]

1. Planos: acha os cortes, grava uma folha com um quadro de cada plano (tempo e duração) e lista os planos
   com menos de 1 s: candidatos a transição vaga (pedaço de plano entre dois inserts, corte interno de animação).
2. Voz × legenda: transcreve o áudio do export (faster-whisper, tempo por palavra; ou lê --palavras), alinha com o
   texto das legendas e lista:
   - legenda que entra fora da voz (mais de 0,25 s) ou sai antes de a fala acabar;
   - palavra ouvida que não está na legenda (palavra repetida em emenda, fala a mais, nome trocado);
   - palavra da legenda que ninguém disse (fala que caiu na montagem).
   Com --voz (o áudio só de voz, sem trilha, ex. o dialogo16k.wav da montagem), cada legenda apontada pela
   transcrição é conferida pela energia: se a voz começa a até 0,25 s do começo da legenda, ela sai da lista.
   A transcrição sozinha erra começo de palavra depois de pausa e com trilha por baixo.
3. Formato: 720 no lado menor.
4. Áudio contínuo: nenhum buraco nos tempos do áudio (a V4 da M1WK4B4 saiu com 2,9 s faltando em 6:12 e a
   locução tocava adiantada em relação à imagem e à legenda; nem o ouvido nem o blackdetect pegam isso).
Grava tudo em <saida>/qc.txt e a folha em <saida>/planos_*.png. Sai com 1 se achar problema.
A folha e as listas são para olhar, não substituem assistir no celular do começo ao fim.
"""
import argparse
import difflib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import alinha_palavras as al  # noqa: E402

FF = os.path.expanduser("~/bin/.ffmpeg-real") if os.path.exists(os.path.expanduser("~/bin/.ffmpeg-real")) else "ffmpeg"
CURTO = 1.0


def cortes(video):
    r = subprocess.run([FF, "-nostats", "-i", video, "-vf", "scale=240:-1,select='gt(scene,0.22)',showinfo", "-an", "-f", "null", "-"],
                       capture_output=True, text=True)
    return [float(x) for x in re.findall(r"pts_time:([0-9.]+)", r.stderr)]


def duracao(video):
    r = subprocess.run([FF, "-i", video], capture_output=True, text=True)
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr).groups()
    tam = re.search(r"Video: .*?(\d{3,4})x(\d{3,4})", r.stderr)
    return int(h) * 3600 + int(m) * 60 + float(s), (int(tam.group(1)), int(tam.group(2)))


def buracos_audio(video):
    """Saltos nos tempos dos quadros de áudio (amostras que faltam e o player pode tocar coladas)."""
    r = subprocess.run([FF, "-nostats", "-i", video, "-map", "0:a:0", "-af", "ashowinfo", "-f", "null", "-"],
                       capture_output=True, text=True)
    saida, ant = [], None
    for t, sr, n in re.findall(r"pts_time:([0-9.]+).*?rate:(\d+) nb_samples:(\d+)", r.stderr):
        t, n, sr = float(t), int(n), int(sr)
        if ant and t - ant[0] - ant[1] > 0.005:
            saida.append((ant[0], t - ant[0] - ant[1]))
        ant = (t, n / sr)
    return saida


def energia(wav):
    import wave
    import numpy as np
    w = wave.open(str(wav))
    x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float) / 32768
    if w.getnchannels() > 1:
        x = x[:: w.getnchannels()]
    h = int(w.getframerate() * 0.02)
    x = x[: len(x) // h * h].reshape(-1, h)
    return 20 * np.log10(np.sqrt((x ** 2).mean(1)) + 1e-6)


def inicio_voz(db, t, raio=0.8):
    """Começo de voz (3 quadros de 20 ms acima de pico - 15 dB, mínimo -28) mais perto de t."""
    import numpy as np
    i0, i1 = max(int((t - raio) / 0.02), 1), int((t + raio) / 0.02)
    trecho = db[i0:i1]
    if len(trecho) < 4:
        return None
    alto = trecho > max(trecho.max() - 15, -28)
    seguido = alto[1:-2] & alto[2:-1] & alto[3:] & ~alto[:-3]
    k = np.where(seguido)[0]
    if not len(k):
        return None
    ts_ = (i0 + 1 + k) * 0.02
    return ts_[np.argmin(np.abs(ts_ - t))]


FONTE = "'C\\:/Windows/Fonts/arial.ttf'" if os.name == "nt" else "/System/Library/Fonts/Helvetica.ttc"  # PC Windows: sem Helvetica


def folha(video, planos, saida):
    for i, (a, b) in enumerate(planos):
        t = a + min(0.4, (b - a) / 2)
        rot = f"{i:03d} {int(a // 60)}m{a % 60:04.1f} d{b - a:.1f}"
        subprocess.run([FF, "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1", "-vf",
                        f"scale=240:-1,drawtext=fontfile={FONTE}:text='{rot}':fontcolor=yellow:"
                        f"fontsize=18:box=1:boxcolor=black@0.7:x=4:y=4", str(saida / f"_q{i:03d}.png")], check=True)
    # sequência numerada, não glob: o ffmpeg do Windows não tem -pattern_type glob
    subprocess.run([FF, "-v", "error", "-y", "-start_number", "0", "-i", str(saida / "_q%03d.png"), "-vf", "tile=8x4",
                    str(saida / "planos_%02d.png")], check=True)
    for p in saida.glob("_q*.png"):
        p.unlink()


def transcreve(video, saida):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import transcricao_cache as tc       # a do checklist, se já rodou (16/11/2026)
    w = tc.ler(video)
    if w:
        w = [list(x) for x in w]; json.dump(w, open(saida / "palavras.json", "w")); return w
    wav = saida / "_audio16k.wav"
    subprocess.run([FF, "-v", "error", "-y", "-i", video, "-vn", "-ac", "1", "-ar", "16000", str(wav)], check=True)
    import checklist      # o mesmo Whisper do checklist (GPU no PC, vocabulário do job, tapa buraco pulado; 16/11/2026)
    w = [[x, round(a, 3), round(b, 3), round(p, 3)] for x, a, b, p in checklist.transcrever(str(wav), "en", tc.vocabulario(video))]
    json.dump(w, open(saida / "palavras.json", "w"))
    wav.unlink()
    tc.gravar(video, w, "en", "qc_export")
    return w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("legendas")
    ap.add_argument("--saida", default=os.path.join(os.environ.get("TMPDIR", "/tmp"), "qc_export"))
    ap.add_argument("--palavras")
    ap.add_argument("--voz")
    a = ap.parse_args()
    saida = Path(a.saida)
    saida.mkdir(parents=True, exist_ok=True)
    rel, problemas = [], 0

    total, (lw, lh) = duracao(a.video)
    if min(lw, lh) != 720:
        rel.append(f"FORMATO: {lw}x{lh}, fora do 720p")
        problemas += 1
    buracos = [(t, g) for t, g in buracos_audio(a.video) if t < total - 1]   # o último quadro pode sobrar
    if buracos:
        rel.append("ÁUDIO COM BURACO (a voz sai do lugar dali em diante): " + ", ".join(f"{t:.2f} s (+{g:.2f})" for t, g in buracos))
        problemas += 1
    else:
        rel.append("ÁUDIO: contínuo, sem buraco")
    c = [0.0] + cortes(a.video) + [total]
    planos = list(zip(c[:-1], c[1:]))
    folha(a.video, planos, saida)
    curtos = [(i, x, y) for i, (x, y) in enumerate(planos) if y - x < CURTO]
    rel.append(f"PLANOS: {len(planos)} em {total:.1f} s; {len(curtos)} com menos de {CURTO:.0f} s (olhar na folha se cada um diz algo):")
    rel += [f"  {i:03d} {int(x // 60)}:{x % 60:05.2f}  {y - x:.2f} s" for i, x, y in curtos]

    pal = json.load(open(a.palavras)) if a.palavras else transcreve(a.video, saida)
    leg = al.le_ass(a.legendas)
    alinhado = al.alinha([t for _, _, t in leg], pal)
    fora, conferidas = [], 0
    db_voz = energia(a.voz) if a.voz else None
    for (x, y, t), ws in zip(leg, alinhado):
        ouvidas = [w for w in ws if w[3]]
        if not ouvidas:
            msg = f"  {x:7.2f}  ninguém disse: {t}"
        else:
            da, dfim = x - ouvidas[0][1], y - ouvidas[-1][2]
            if abs(da) <= 0.25 and dfim >= -0.15:
                continue
            msg = f"  {x:7.2f}  entra {da:+.2f} s, sai {dfim:+.2f} s: {t}"
        if db_voz is not None:
            v = inicio_voz(db_voz, x + 0.05)
            if v is not None and abs(v - (x + 0.05)) <= 0.25:
                conferidas += 1
                continue
            msg += f"  [voz começa em {v:.2f}]" if v is not None else "  [sem começo de voz perto]"
        fora.append(msg)
    if db_voz is not None:
        rel.append(f"(pela energia da voz: {conferidas} legendas apontadas pela transcrição começam junto com a voz)")
    rel.append(f"LEGENDA × VOZ: {len(fora)} de {len(leg)} fora (a transcrição erra começo de palavra depois de pausa: conferir no vídeo):")
    rel += fora
    # palavras ouvidas sem legenda (repetição em emenda, fala a mais)
    roteiro = [tk for _, _, t in leg for tk in al.norma(t)]
    ouvido = [(tk, w[1]) for w in pal for tk in al.norma(w[0])]
    sm = difflib.SequenceMatcher(None, roteiro, [o[0] for o in ouvido], autojunk=False)
    extras = []
    for op, a0, a1, b0, b1 in sm.get_opcodes():
        if op == "insert" or (op == "replace" and b1 - b0 > a1 - a0):
            extras.append(f"  {ouvido[b0][1]:7.2f}  ouvido sem legenda: {' '.join(o[0] for o in ouvido[b0:b1])}"
                          + (f"  (legenda: {' '.join(roteiro[a0:a1])})" if op == "replace" else ""))
    rel.append(f"VOZ SEM LEGENDA: {len(extras)} trechos (palavra repetida ou trocada na voz, ou erro da transcrição: ouvir cada um):")
    rel += extras
    problemas += len(fora) + len(extras)
    (saida / "qc.txt").write_text("\n".join(rel) + "\n", encoding="utf-8")
    print("\n".join(rel))
    print(f"\nFolha de planos e qc.txt em {saida}")
    sys.exit(1 if problemas else 0)


if __name__ == "__main__":
    main()
