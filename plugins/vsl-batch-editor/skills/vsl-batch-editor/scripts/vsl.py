#!/usr/bin/env python3
"""Ferramentas de edição VSL (Neurobella / VisioVance).

Subcomandos:
  cut      <video> <cuts.json> [--cfg batch.json]          detecta silêncios e grava os trechos mantidos
  xml      <cuts.json> <src_device_path> <src_dur> <nome> <out.xml> [--fps 30] [--src-w 720 --src-h 1280]
  preview  <video> <cuts.json> <out.mp4>                   renderiza a hold cortada (conferência rápida)
  calibrate <video> <prproj_parse.json> <sequencia>        compara o corte automático com um corte real
  revisar  <saida.jpg> <video1> [video2 ...] [--quadros 8] tira de quadros de cada vídeo (conferir b-roll gerado)
  prancha  <saida.jpg> <img1> [img2 ...] [--colunas 4]     prancha das imagens iniciais para aprovação
  transcrever <audio_ou_video> <palavras.json> [--lang en]  tempo de cada palavra (faster-whisper; roda no Mac/Claude Code)
  srt      <palavras.json> <saida.srt> [--max 22]           legenda de 1 linha com até N caracteres
"""
import sys, json, subprocess, argparse, urllib.parse
import numpy as np
from xml.sax.saxutils import escape

DEF = {"limiar_db": -34, "silencio_min_s": 0.45, "folga_antes_s": 0.05, "folga_depois_s": 0.12}
HOP = 0.01

def envelope(video, sr=16000):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", video, "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.int16).astype(float) / 32768
    h = int(sr * HOP); n = len(x) // h
    return 20 * np.log10(np.sqrt((x[:n*h].reshape(n, h) ** 2).mean(1) + 1e-12))

def keep_segments(db, thr, min_sil, pad_in, pad_out, min_keep=0.15):
    voiced = db > thr; n = len(voiced); sil = []; i = 0
    k = 0
    while k < n and voiced[k]: k += 1
    if k * HOP < 0.25: voiced[:k] = False   # clique do Kling no 1º décimo: vira silêncio e o início é sempre aparado
    while i < n:
        if not voiced[i]:
            j = i
            while j < n and not voiced[j]: j += 1
            if (j - i) * HOP >= min_sil or i == 0 or j == n: sil.append((i * HOP, j * HOP))
            i = j
        else: i += 1
    dur = n * HOP; t = 0; keep = []
    for a, b in sil:
        if a + pad_out - t > 0: keep.append([t, a + pad_out])
        t = max(b - pad_in, a + pad_out)
    if dur - t > 0: keep.append([t, dur])
    keep = [[max(0, s), min(dur, e)] for s, e in keep if e - s >= min_keep]
    m = []
    for s, e in keep:
        if m and s <= m[-1][1]: m[-1][1] = max(m[-1][1], e)
        else: m.append([s, e])
    # sobra curta antes da 1ª pausa = o avatar "pisca" num enquadramento diferente (comentário Frame.io, BATCH_2080)
    if len(m) > 1 and m[0][1] - m[0][0] < 0.4: m = m[1:]
    return [[round(s, 3), round(e, 3)] for s, e in m]

def load_cfg(path):
    c = dict(DEF)
    if path:
        c.update(json.load(open(path)).get("corte_silencio", {}))
    return c

def cmd_cut(a):
    c = load_cfg(a.cfg); db = envelope(a.video)
    k = keep_segments(db, c["limiar_db"], c["silencio_min_s"], c["folga_antes_s"], c["folga_depois_s"])
    json.dump(k, open(a.out, "w"))
    print(f"{len(k)} trechos, {sum(e-s for s,e in k):.1f}s de {len(db)*HOP:.1f}s")

def fcp_xml(segs, src_path, src_dur, seq_name, fps=30, w=1080, h=1920, sw=720, sh=1280):
    name = src_path.split("/")[-1]; url = "file://" + urllib.parse.quote(src_path)
    f = lambda t: int(round(t * fps))
    rate = f"<rate><timebase>{fps}</timebase><ntsc>FALSE</ntsc></rate>"
    V, A, t = [], [], 0
    for i, (s, e) in enumerate(segs):
        a, b = f(s), f(e); d = b - a
        if d <= 0: continue
        fe = (f'<file id="file-1"><name>{escape(name)}</name><pathurl>{url}</pathurl>{rate}<duration>{f(src_dur)}</duration>'
              f'<media><video><samplecharacteristics><width>{sw}</width><height>{sh}</height></samplecharacteristics></video>'
              f'<audio><channelcount>1</channelcount></audio></media></file>') if not V else '<file id="file-1"/>'
        links = f'<link><linkclipref>v{i}</linkclipref><mediatype>video</mediatype></link><link><linkclipref>a{i}</linkclipref><mediatype>audio</mediatype></link>'
        common = f'<name>{escape(name)}</name><enabled>TRUE</enabled><duration>{f(src_dur)}</duration>{rate}<start>{t}</start><end>{t+d}</end><in>{a}</in><out>{b}</out>'
        V.append(f'<clipitem id="v{i}">{common}{fe}<filter><effect><name>Basic Motion</name><effectid>basic</effectid><effectcategory>motion</effectcategory>'
                 f'<effecttype>motion</effecttype><mediatype>video</mediatype><parameter><parameterid>scale</parameterid><name>Scale</name>'
                 f'<valuemin>0</valuemin><valuemax>1000</valuemax><value>{100*h/sh:.2f}</value></parameter></effect></filter>{links}</clipitem>')
        A.append(f'<clipitem id="a{i}">{common}<file id="file-1"/><sourcetrack><mediatype>audio</mediatype><trackindex>1</trackindex></sourcetrack>{links}</clipitem>')
        t += d
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n<xmeml version="4"><sequence id="seq-1"><name>{escape(seq_name)}</name>'
            f'<duration>{t}</duration>{rate}<media><video><format><samplecharacteristics>{rate}<width>{w}</width><height>{h}</height>'
            f'<pixelaspectratio>square</pixelaspectratio></samplecharacteristics></format><track>{"".join(V)}</track></video>'
            f'<audio><track>{"".join(A)}</track></audio></media></sequence></xmeml>')

def cmd_xml(a):
    segs = json.load(open(a.cuts))
    open(a.out, "w").write(fcp_xml(segs, a.src, a.dur, a.name, a.fps, sw=a.src_w, sh=a.src_h))
    print("ok", a.out)

def cmd_preview(a):
    segs = json.load(open(a.cuts)); p = []
    for i, (s, e) in enumerate(segs):
        p.append(f"[0:v]trim={s}:{e},setpts=PTS-STARTPTS[v{i}];[0:a]atrim={s}:{e},asetpts=PTS-STARTPTS[a{i}]")
    p.append("".join(f"[v{i}][a{i}]" for i in range(len(segs))) + f"concat=n={len(segs)}:v=1:a=1[v][a]")
    fc = a.out + ".fc.txt"; open(fc, "w").write(";".join(p))
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", a.video, "-filter_complex_script", fc, "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-crf", "26", "-preset", "veryfast", "-c:a", "aac", "-b:a", "128k", "-y", a.out], check=True)
    print("ok", a.out)

def cmd_calibrate(a):
    gt = [(x["inp"], x["outp"]) for x in json.load(open(a.parsed))
          if x["seq"] == a.seq and x["track"] == "VideoClipTrack0" and x["inp"] is not None]
    db = envelope(a.video); N = len(db)
    def mask(segs):
        m = np.zeros(N, bool)
        for s, e in segs: m[int(s/HOP):int(e/HOP)] = 1
        return m
    G = mask(gt); res = []
    for thr in range(-44, -27, 2):
        for ms in [0.3, 0.35, 0.4, 0.45, 0.5, 0.6]:
            for pi in [0.03, 0.05, 0.08]:
                for po in [0.08, 0.12, 0.15, 0.2]:
                    k = keep_segments(db, thr, ms, pi, po)
                    res.append(((mask(k) == G).mean(), thr, ms, pi, po, len(k)))
    res.sort(reverse=True)
    print(f"corte real: {len(gt)} trechos, {G.sum()*HOP:.1f}s")
    for r in res[:5]: print("acerto %.3f | limiar %d dB, silencio_min %.2f, folga_antes %.2f, folga_depois %.2f -> %d trechos" % r)

def _dur(f):
    return float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",f],capture_output=True,text=True).stdout.strip())

def _label(path):
    import os; return os.path.basename(path).replace("'", "").replace(":", "")[:40]

def cmd_revisar(a):
    import tempfile, os
    tmp = tempfile.mkdtemp(); linhas = []
    for vi, v in enumerate(a.videos):
        d = _dur(v); fr = []
        for k in range(a.quadros):
            t = d * (k + 0.5) / a.quadros; o = f"{tmp}/{vi}_{k}.jpg"
            txt = f"{_label(v)}  {t:.1f}s" if k == 0 else f"{t:.1f}s"
            subprocess.run(["ffmpeg","-nostdin","-v","error","-ss",f"{t:.2f}","-i",v,"-frames:v","1","-vf",
                f"scale=-2:360,drawtext=text='{txt}':fontcolor=yellow:fontsize=16:x=6:y=6:box=1:boxcolor=black@0.7","-y",o],check=True)
            fr.append(o)
        lo = f"{tmp}/l{vi}.jpg"
        subprocess.run(["ffmpeg","-nostdin","-v","error",*sum([["-i",f] for f in fr],[]),"-filter_complex",
            "".join(f"[{i}]" for i in range(len(fr)))+f"hstack={len(fr)}","-y",lo],check=True); linhas.append(lo)
    if len(linhas) == 1: os.replace(linhas[0], a.out)
    else:
        subprocess.run(["ffmpeg","-nostdin","-v","error",*sum([["-i",f] for f in linhas],[]),"-filter_complex",
            "".join(f"[{i}]" for i in range(len(linhas)))+f"vstack={len(linhas)}","-y",a.out],check=True)
    print("ok", a.out)

def cmd_prancha(a):
    from PIL import Image, ImageDraw
    W = 360; ims = []
    for f in a.imgs:
        im = Image.open(f).convert("RGB"); im = im.resize((W, int(im.height * W / im.width)))
        ImageDraw.Draw(im).rectangle([0, 0, W, 24], fill=(0, 0, 0)); ImageDraw.Draw(im).text((6, 5), _label(f), fill=(255, 220, 0))
        ims.append(im)
    H = max(i.height for i in ims); c = a.colunas; r = (len(ims) + c - 1) // c
    sheet = Image.new("RGB", (c * W, r * H), (20, 20, 20))
    for i, im in enumerate(ims): sheet.paste(im, ((i % c) * W, (i // c) * H))
    sheet.save(a.out, quality=88); print("ok", a.out)

def _cuda_ok():
    # PC Windows do Fefo (RTX 3060 Ti, 11/11/2026): as DLLs CUDA vêm do pip (nvidia-cublas-cu12, nvidia-cudnn-cu12).
    # Põe as pastas no caminho e confere se carregam. No Mac não há CUDA: fica na CPU como antes.
    import os, glob, ctypes
    if os.name != "nt": return False
    for b in glob.glob(os.path.join(os.environ.get("APPDATA", ""), "Python", "Python3*", "site-packages", "nvidia", "*", "bin")):
        os.add_dll_directory(b); os.environ["PATH"] = b + os.pathsep + os.environ["PATH"]
    try: ctypes.WinDLL("cublas64_12.dll"); ctypes.WinDLL("cudnn64_9.dll"); return True
    except OSError: return False

def cmd_transcrever(a):
    from faster_whisper import WhisperModel
    m = WhisperModel(a.modelo, device="cuda", compute_type="float16") if _cuda_ok() else WhisperModel(a.modelo, device="cpu", compute_type="int8")
    segs, _ = m.transcribe(a.midia, language=a.lang, word_timestamps=True, vad_filter=True)
    w = [{"w": x.word.strip(), "s": round(x.start, 3), "e": round(x.end, 3)} for sg in segs for x in (sg.words or [])]
    json.dump(w, open(a.out, "w"), ensure_ascii=False); print(len(w), "palavras ->", a.out)

def chunk_words(words, maxc=22):
    blocos, cur = [], []
    for x in words:
        t = " ".join(y["w"] for y in cur + [x])
        if cur and (len(t) > maxc or x["s"] - cur[-1]["e"] > 0.6):
            blocos.append(cur); cur = [x]
        else: cur.append(x)
    if cur: blocos.append(cur)
    return [{"s": b[0]["s"], "e": b[-1]["e"], "t": " ".join(y["w"] for y in b)} for b in blocos]

def cmd_srt(a):
    ts = lambda t: "%02d:%02d:%02d,%03d" % (t // 3600, t % 3600 // 60, t % 60, round((t % 1) * 1000) % 1000)
    bl = chunk_words(json.load(open(a.palavras)), a.max)
    for i in range(len(bl) - 1):  # sem buracos curtos entre blocos
        if bl[i + 1]["s"] - bl[i]["e"] < 0.3: bl[i]["e"] = bl[i + 1]["s"]
    open(a.out, "w").write("\n".join(f"{i+1}\n{ts(b['s'])} --> {ts(b['e'])}\n{b['t']}\n" for i, b in enumerate(bl)))
    print(len(bl), "legendas ->", a.out)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("cut"); p.add_argument("video"); p.add_argument("out"); p.add_argument("--cfg"); p.set_defaults(fn=cmd_cut)
    p = sp.add_parser("xml"); p.add_argument("cuts"); p.add_argument("src"); p.add_argument("dur", type=float); p.add_argument("name"); p.add_argument("out")
    p.add_argument("--fps", type=int, default=30); p.add_argument("--src-w", type=int, default=720); p.add_argument("--src-h", type=int, default=1280); p.set_defaults(fn=cmd_xml)
    p = sp.add_parser("preview"); p.add_argument("video"); p.add_argument("cuts"); p.add_argument("out"); p.set_defaults(fn=cmd_preview)
    p = sp.add_parser("calibrate"); p.add_argument("video"); p.add_argument("parsed"); p.add_argument("seq"); p.set_defaults(fn=cmd_calibrate)
    p = sp.add_parser("revisar"); p.add_argument("out"); p.add_argument("videos", nargs="+"); p.add_argument("--quadros", type=int, default=8); p.set_defaults(fn=cmd_revisar)
    p = sp.add_parser("prancha"); p.add_argument("out"); p.add_argument("imgs", nargs="+"); p.add_argument("--colunas", type=int, default=4); p.set_defaults(fn=cmd_prancha)
    p = sp.add_parser("transcrever"); p.add_argument("midia"); p.add_argument("out"); p.add_argument("--lang", default="en"); p.add_argument("--modelo", default="small"); p.set_defaults(fn=cmd_transcrever)
    p = sp.add_parser("srt"); p.add_argument("palavras"); p.add_argument("out"); p.add_argument("--max", type=int, default=22); p.set_defaults(fn=cmd_srt)
    a = ap.parse_args(); a.fn(a)
