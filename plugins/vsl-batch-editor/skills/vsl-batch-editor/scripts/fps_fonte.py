#!/usr/bin/env python3
"""Clipe de origem no fps do export, sem cadência travada (EV em 60 fps desde 18/11/2026).

Pedido do Daniel (Loom de 18/11/2026): "every video should be in 60 frames per second"; vídeos "laggy", parecendo
20-30 fps. Os clipes gerados (Kling, Seedance, Omni) vêm a 24 fps. Só `fps=60` repete os quadros em 2-3-2-3: o
movimento continua a 24 e a cadência fica irregular (47-51% de quadros repetidos no teste). A interpolação por
movimento do ffmpeg (minterpolate mci) cria os quadros do meio sem imagem dupla; a mistura (framerate) deixa fantasma
na mão e na árvore (teste no H1-01 e no F07 da 4382, 18/11/2026).

O mci é lento (~26x o tempo do clipe, 1 núcleo só). Por isso:
  - cada clipe é interpolado UMA vez e fica no cache (%TEMP%/fps_fonte/<hash>.mp4; hash = caminho, tamanho, data,
    fps e versão do filtro): prévia, segmentos e final usam o mesmo arquivo;
  - o clipe é cortado em pedaços de 2 s (múltiplo de 0,5 s: cai na grade de 24, 25, 30 e 60 fps) com 0,25 s de sobra,
    e os pedaços de todos os clipes rodam em paralelo (FPS_PARALELO, padrão 8);
  - o áudio do clipe vai junto, copiado sem recodificar (o corte de silêncio e a voz usam o mesmo arquivo).

Modo (ficha do cliente, "fps_interp"): "mci" interpola; "dup" (padrão) só repete quadros no montador.
FPS_INTERP=dup no ambiente desliga a interpolação numa rodada (teste rápido).

  py fps_fonte.py <clipe.mp4> [...] [--fps 60]      # interpola e imprime o caminho no cache
"""
import hashlib, json, os, shutil, subprocess, sys, tempfile, threading
from concurrent.futures import ThreadPoolExecutor

VERSAO = "mci-1"
FILTRO = "minterpolate=fps={fps}:mi_mode=mci"      # obmc/bilat/epzs padrão: o mais rápido dos 3 testados e sem artefato visto
PEDACO = 2.0
SOBRA = 0.25
CACHE = os.path.join(tempfile.gettempdir(), "fps_fonte")
_travas = {}; _trava_mapa = threading.Lock(); _fps_cache = {}


def ff(): return shutil.which("ffmpeg") or "ffmpeg"
def fp(): return shutil.which("ffprobe") or "ffprobe"


def fps_de(arq):
    """fps do vídeo (r_frame_rate). 0 quando não lê (imagem, áudio)."""
    k = (os.path.abspath(arq), os.path.getmtime(arq) if os.path.exists(arq) else 0)
    if k in _fps_cache: return _fps_cache[k]
    r = subprocess.run([fp(), "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                        "-of", "csv=p=0", arq], capture_output=True, text=True)
    try:
        a, _, b = r.stdout.strip().split(",")[0].partition("/"); v = float(a) / float(b or 1)
    except (ValueError, ZeroDivisionError): v = 0.0
    _fps_cache[k] = v
    return v


def dur_video(arq):
    r = subprocess.run([fp(), "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=duration",
                        "-of", "csv=p=0", arq], capture_output=True, text=True)
    try: return float(r.stdout.strip().split(",")[0])
    except ValueError:
        r = subprocess.run([fp(), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", arq], capture_output=True, text=True)
        return float(r.stdout.strip() or 0)


def precisa(arq, fps, modo):
    if modo != "mci" or os.environ.get("FPS_INTERP") == "dup": return False
    if not arq or not os.path.isfile(arq) or not arq.lower().endswith((".mp4", ".mov", ".mkv", ".webm")): return False
    v = fps_de(arq)
    return 1 < v < fps - 0.5


def destino(arq, fps):
    st = os.stat(arq)
    h = hashlib.sha1(json.dumps([VERSAO, FILTRO, fps, os.path.normcase(os.path.abspath(arq)), st.st_size, int(st.st_mtime)]).encode()).hexdigest()[:12]
    return os.path.join(CACHE, f"{os.path.splitext(os.path.basename(arq))[0][:40]}_{fps}_{h}.mp4")


def _pedacos(arq, fps):
    d = dur_video(arq); n = max(1, int(-(-d // PEDACO)))
    out = []
    for i in range(n):
        a = i * PEDACO; b = min(d, a + PEDACO)
        k = round(b * fps) - round(a * fps)
        if k > 0: out.append((i, a, k))
    return out


def _um_pedaco(arq, fps, pasta, i, a, k):
    dst = os.path.join(pasta, f"p{i:04d}.mp4")
    vf = f"tpad=stop_mode=clone:stop=4,{FILTRO.format(fps=fps)},trim=end_frame={k},setpts=PTS-STARTPTS"
    subprocess.run([ff(), "-nostdin", "-v", "error", "-y", "-ss", f"{a:.6f}", "-t", f"{PEDACO + SOBRA:.3f}", "-i", arq, "-an",
                    "-vf", vf, "-fps_mode", "cfr", "-r", str(fps), "-c:v", "libx264", "-preset", "veryfast", "-crf", "14",
                    "-pix_fmt", "yuv420p", "-threads", "2", dst], check=True)
    return dst


def _junta(arq, fps, partes, dst):
    lista = os.path.join(os.path.dirname(partes[0]), "lista.txt")
    with open(lista, "w", encoding="utf-8") as f:
        for p in partes: f.write(f"file '{p.replace(os.sep, '/')}'\n")
    tmp = dst + ".part.mp4"
    subprocess.run([ff(), "-nostdin", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-r", str(fps), "-i", lista, "-i", arq,
                    "-map", "0:v", "-map", "1:a?", "-c", "copy", "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, dst)


def prepara(arqs, fps, modo="mci", paralelo=None, avisa=True):
    """Interpola (em paralelo, por pedaços) os clipes de `arqs` que estão abaixo de `fps`. Devolve {original: caminho}."""
    arqs = list(dict.fromkeys(a for a in arqs if a))
    mapa = {a: a for a in arqs}
    falta = []
    for a in arqs:
        if not precisa(a, fps, modo): continue
        dst = destino(a, fps); mapa[a] = dst
        if not os.path.exists(dst): falta.append((a, dst))
    if not falta: return mapa
    os.makedirs(CACHE, exist_ok=True)
    paralelo = paralelo or int(os.environ.get("FPS_PARALELO", "8"))
    trabalhos, grupos = [], {}
    for a, dst in falta:
        with _trava_mapa: tv = _travas.setdefault(dst, threading.Lock())
        if not tv.acquire(blocking=False):          # outra thread (hook x hold) já está fazendo: espera ela
            grupos[dst] = None; continue
        pasta = tempfile.mkdtemp(prefix="fpsf_", dir=CACHE)
        grupos[dst] = (a, pasta, tv, [])
        for i, ini, k in _pedacos(a, fps): trabalhos.append((dst, a, pasta, i, ini, k))
    import time; t0 = time.time()
    if avisa and trabalhos:
        print(f"   fps {fps}: interpolando {sum(1 for g in grupos.values() if g)} clipe(s) em {len(trabalhos)} pedaço(s) de "
              f"{PEDACO:g} s, {paralelo} em paralelo (mci, cache em {CACHE})", flush=True)
    try:
        with ThreadPoolExecutor(paralelo) as ex:
            fut = {(dst, i): ex.submit(_um_pedaco, a, fps, pasta, i, ini, k) for dst, a, pasta, i, ini, k in trabalhos}
            for (dst, i), f in sorted(fut.items()): grupos[dst][3].append(f.result())
        for dst, g in grupos.items():
            if g: _junta(g[0], fps, g[3], dst)
    finally:
        for dst, g in grupos.items():
            if g: shutil.rmtree(g[1], ignore_errors=True); g[2].release()
    for dst, g in grupos.items():                    # os que outra thread fazia: espera a trava soltar
        if g is None:
            with _travas[dst]: pass
    if avisa and trabalhos: print(f"   fps {fps}: interpolação pronta em {time.time() - t0:.0f} s", flush=True)
    return mapa


def fonte(arq, fps, modo="mci"):
    """Caminho do clipe no fps do export (interpola se precisar; usa o cache)."""
    return prepara([arq], fps, modo).get(arq, arq)


if __name__ == "__main__":
    args = sys.argv[1:]; fps = 60
    if "--fps" in args: i = args.index("--fps"); fps = int(args[i + 1]); del args[i:i + 2]
    for k, v in prepara(args, fps).items(): print(f"{k} -> {v}")
