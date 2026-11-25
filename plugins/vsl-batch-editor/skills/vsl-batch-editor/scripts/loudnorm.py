#!/usr/bin/env python3
"""Loudnorm em 2 passadas: módulo ÚNICO do núcleo (Central, 17/11/2026). EV e TS chamam este arquivo.
  EV: fluxo_partes/montar.py (_loudnorm_2p) · TS: @TRENDSCALE/2026/_FLUXO/montagem_base.py (loudnorm_2p / exportar(lufs=))
Conserto de loudness vai aqui, uma vez só.

Por quê (defeito achado na M1WK4B2 V6): o loudnorm de uma passada dentro do filter_complex deixa o export ~2 LU abaixo
do alvo (TS -14 saía em -16) e o item 4 do checklist reprova. Depois do encode: mede o áudio do arquivo (1ª passada) e
reaplica o loudnorm LINEAR com os valores medidos (2ª), só no áudio; o vídeo é copiado. TP -1.5 deixa folga para o AAC:
o checklist pede no máximo -1 dBTP. Já no alvo (±tol LU e pico ≤ -1 dBTP): não refaz.

Uso no código:  import loudnorm; loudnorm.duas_passadas(mp4, lufs=-14)      -> (LUFS, dBTP) ou None
Linha de comando: py loudnorm.py ARQ.mp4 [-14] [--tp -1.5] [--so-medir]
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

TIMEOUT = int(os.environ.get("TS_TIMEOUT_FF", "900"))    # 15 min por chamada de ffmpeg


def _ff(ff=None):
    return ff or shutil.which("ffmpeg") or "ffmpeg"


def mede(arq, lufs=-14, tp=-1.5, ff=None):
    """1ª passada: dict do loudnorm (input_i, input_tp, input_lra, input_thresh, target_offset) ou None."""
    err = subprocess.run([_ff(ff), "-nostdin", "-hide_banner", "-nostats", "-i", arq, "-vn", "-af",
                          f"loudnorm=I={lufs}:TP={tp}:LRA=11:print_format=json", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=TIMEOUT).stderr
    blocos = re.findall(r"\{[^{}]*\}", err)
    return json.loads(blocos[-1]) if blocos else None


def duas_passadas(mp4, lufs=-14, tp=-1.5, tol=0.5, ff=None):
    """Leva o áudio de `mp4` ao alvo (no lugar). Devolve (LUFS, dBTP) do arquivo final, ou None se não mediu."""
    ff = _ff(ff)
    m = mede(mp4, lufs, tp, ff)
    if not m or m["input_i"] in ("-inf", "inf"):
        print(f"   aviso: não medi o loudness de {os.path.basename(mp4)}; ficou o da 1ª passada")
        return None
    ent_i, ent_tp = float(m["input_i"]), float(m["input_tp"])
    if abs(ent_i - lufs) <= tol and ent_tp <= min(tp + 0.5, -1.0):
        print(f"   loudness ok na 1ª passada: {ent_i:.1f} LUFS, {ent_tp:.1f} dBTP")
        return ent_i, ent_tp
    af = (f"loudnorm=I={lufs}:TP={tp}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,aresample=48000"
          # limitador depois do ganho linear: o linear sozinho deixava o pico em -0,6 dBTP (M2WK2B3 H5 V3, 19/11/2026).
          # Teto da amostra 0,5 dB abaixo do TP alvo: folga para o pico entre amostras e para o AAC.
          f",alimiter=limit={10 ** ((tp - 0.5) / 20):.4f}:attack=1:release=50:level=disabled")
    pasta = tempfile.mkdtemp(prefix="ln2p_")
    wav, tmp = os.path.join(pasta, "a.wav"), os.path.join(pasta, os.path.basename(mp4))
    try:
        subprocess.run([ff, "-nostdin", "-v", "error", "-y", "-i", mp4, "-vn", "-af", af, "-c:a", "pcm_s16le", wav],
                       check=True, timeout=TIMEOUT)
        subprocess.run([ff, "-nostdin", "-v", "error", "-y", "-i", mp4, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", tmp], check=True, timeout=TIMEOUT)
        shutil.copyfile(tmp, mp4)
    finally:
        shutil.rmtree(pasta, ignore_errors=True)
    f = mede(mp4, lufs, tp, ff)
    if not f:
        print(f"   loudnorm 2ª passada aplicada (entrada {ent_i:.1f} LUFS)")
        return None
    print(f"   loudnorm 2ª passada: {ent_i:.1f} -> {float(f['input_i']):.1f} LUFS (alvo {lufs}), pico {float(f['input_tp']):.1f} dBTP")
    return float(f["input_i"]), float(f["input_tp"])


if __name__ == "__main__":
    a = [x for x in sys.argv[1:]]
    if not a:
        sys.exit(__doc__)
    tp = float(a[a.index("--tp") + 1]) if "--tp" in a else -1.5
    pos = [x for i, x in enumerate(a) if not x.startswith("--") and (i == 0 or a[i - 1] != "--tp")]
    alvo = float(pos[1]) if len(pos) > 1 else -14
    if "--so-medir" in a:
        r = mede(pos[0], alvo, tp)
        print(f"{float(r['input_i']):.1f} LUFS, pico {float(r['input_tp']):.1f} dBTP" if r else "não medi")
    else:
        duas_passadas(pos[0], alvo, tp)
