#!/usr/bin/env python3
"""Molde HyperFrames do núcleo (Fefo, 19/11/2026: "Molde HyperFrames"). Serve à Empire Vision e à Trendscale.

A montagem fica num JSON (`<auto>/montagem_hf.json`); este script gera o projeto HyperFrames no TEMP, confere a linha do
tempo pela trava do núcleo e renderiza. Nenhuma batch precisa de script próprio para montar no HyperFrames.
Origem: o piloto da BATCH#4618 (`08_auto/scripts/hf_4618.py`), que reproduziu a 4619 V1 aprovada. Os achados dele estão
embutidos aqui: alfa em WebM, sobreposição de 2 ms entre clipes encostados, blur pela media-treatment, push-in por GSAP,
`hyperframes` chamado pelo node (o .cmd não passa JSON e o `fila` não acha), progresso do render em arquivo (pipe trava).

  py -X utf8 hf_molde.py trava    <job> [--marca p]                          # só a linha do tempo (sem render)
  py -X utf8 hf_molde.py preparar <job> [--marca p] [--formato f]            # projeto em %TEMP%/hf/<job>/<p>_<f>
  py -X utf8 hf_molde.py quadros  <job> --em 1,5,12 [--marca p] [--formato f] # PNGs para conferir antes do render
  PREVIA=1 fila py -X utf8 hf_molde.py render <job> [--marca p] [--formato f]  # prévia (NVENC) -> export + .PREVIA.txt
  fila --frente py -X utf8 hf_molde.py render <job> --final [...]             # final (libx264 crf 18), só depois do ok

<job> = pasta da batch ou do job. O JSON fica em <job>/08_auto (EV) ou <job>/06_auto (TS), ou passe --spec <arquivo>.

montagem_hf.json (caminhos relativos ao job; "{p}" = marca; um valor {"<marca>": x, ...} vale por marca):
{
  "fps": 30, "dur": 35.5,
  "marcas": {"neurobella": {"nome": "Neurobella"}, "visiovance": {"nome": "VisioVance"}},
  "saida": "09_export/{p}/{card} - {nome} - AD1{sufixo}.mp4",          # padrão EV; card vem do batch.json
  "audio": {"trilha": "02_audio/trilha/trilha_1.mp3", "lufs": -20, "tp": -1.5, "fade_out": 2.2, "de": 0},
  "aceitar_lasca": [{"t": "mm:ss", "motivo": "..."}],                   # escape da trava (com motivo)
  "formatos": {
    "9x16": {"tela": [720, 1280], "camadas": [ ... ]},
    "4x5":  {"de": "9x16", "corte": [0, 200, 720, 900], "sufixo": " - 720x900"}   # derivado: recorte do 9x16
  }
}
Camadas (a ordem da lista = ordem de pintura; a de baixo primeiro):
  {"tipo": "video", "src", "t0", "t1", "de": 0, "caixa": [x, y, w, h] (px da tela; padrão: tela cheia, cover),
   "velocidade": 1, "congela": true (segura o último quadro até t1), "loop": true (repete o clipe até t1),
   "chaves": [{"t": 7.3, "caixa": [...]}] (troca seca de posição e tamanho), "entra"/"sai": {"dissolve": 0.3},
   "push": 0.02 (zoom por segundo), "papel": "broll" (entra na trava) | "camada" (padrão)}
     Alfa (ProRes 4444, PNG em vídeo) vira WebM VP9 com alfa, no tamanho de uso e a 30 fps (cache no TEMP).
  {"tipo": "planos", "t0", "faixa": 0.675, "pena": 26, "entra": {"dissolve": 0.3},
   "itens": [{"src", "de", "q" (quadros), "reenquadra": [s, bx, by] ou [s, bx, by, 1], "velocidade", "push"}]}
     Cortes por quadro. reenquadra = escala s e o ponto (bx, by) da fonte no centro x e na `faixa` y; s < 1 ou o 4º
     valor 1 = fundo desfocado do próprio clipe com borda suave. Sempre entra na trava (papel broll).
  {"tipo": "imagem", "src", "t0", "t1", "caixa"}
  {"tipo": "texto", "estilo": "caixa"|"legenda"|"check", "texto" (quebra pelo pilula) ou "linhas": [...], "tam", "y"
   (topo, px da tela base 1080 de largura), "area": "plataforma" | [x0, y0, x1, y1] (px da tela base),
   "fonte": "hd"|"leg", "destaque": [{"linha": 3, "cor": "#FFD400"}], "icone": "2705", "t0", "t1"}
     Desenho só pelo pilula.py (manual do montador, seção 4): o PNG sai na tela base (1080 x proporção) e escala na tela.
Medidas de cada render (s, RAM de pico): <auto>/hf_render.jsonl.
"""
import argparse, hashlib, json, os, re, shutil, subprocess, sys, tempfile, threading, time

AQUI = os.path.dirname(os.path.abspath(__file__))
for _d in (AQUI, os.path.join(AQUI, "checagens")):
    if _d not in sys.path: sys.path.insert(0, _d)

HF_JS = os.path.join(os.environ.get("APPDATA", ""), "npm", "node_modules", "hyperframes", "bin", "hyperframes.mjs")
NODE = shutil.which("node") or "node"
GSAP = os.path.join(os.environ.get("APPDATA", ""), "npm", "node_modules", "hyperframes", "dist", "vendor", "npm", "gsap@3.15.0", "dist", "gsap.min.js")
TMP = os.path.join(tempfile.gettempdir(), "hf")
CACHE = os.path.join(TMP, "_cache")
EMOJI = os.path.normpath(os.path.join(AQUI, "..", "emoji_apple"))
SOBRA = 0.002                      # 2 ms: clipes encostados deixavam 1 quadro preto no corte (piloto 4618)
ENV = dict(os.environ, HYPERFRAMES_NO_TELEMETRY="1")


def run(cmd, log=None, **kw):
    cmd = [str(c) for c in cmd]
    if log:                                                     # o HF escreve muito progresso: pipe trava o render
        with open(log, "w", encoding="utf-8", errors="replace") as f:
            r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, env=ENV, **kw)
        if r.returncode: raise SystemExit(f"ERRO {' '.join(cmd)[:300]}\n" + open(log, encoding="utf-8", errors="replace").read()[-2000:])
        return r
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV, **kw)
    if r.returncode: raise SystemExit(f"ERRO {' '.join(cmd)[:300]}\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}")
    return r


def hf(*args, log=None): return run([NODE, HF_JS, *args], log=log)


# ---------------------------------------------------------------- job, spec, marca
def auto_de(job):
    for a in ("08_auto", "06_auto"):
        if os.path.isdir(os.path.join(job, a)): return os.path.join(job, a)
    return job


def ler_spec(job, arq=None):
    arq = arq or os.path.join(auto_de(job), "montagem_hf.json")
    if not os.path.exists(arq): raise SystemExit(f"hf_molde: falta o {arq} (formato no cabeçalho deste script)")
    return json.load(open(arq, encoding="utf-8")), arq


def card_de(job, spec):
    if spec.get("card"): return spec["card"]
    for nome in ("batch.json", "job.json"):
        a = os.path.join(job, nome)
        if os.path.exists(a):
            j = json.load(open(a, encoding="utf-8")); c = j.get("card") or j.get("titulo") or j.get("nome")
            if c: return c
    return os.path.basename(job.rstrip("/\\"))


def por_marca(v, p, marcas):
    """{"neurobella": x, "visiovance": y} -> o valor da marca; listas e dicts comuns: resolve por dentro."""
    if isinstance(v, dict):
        if v and marcas and set(v) <= set(marcas): return por_marca(v.get(p), p, marcas)
        return {k: por_marca(x, p, marcas) for k, x in v.items()}
    if isinstance(v, list): return [por_marca(x, p, marcas) for x in v]
    if isinstance(v, str): return v.replace("{p}", p)
    return v


def caminho(job, src): return src if os.path.isabs(src) else os.path.normpath(os.path.join(job, src))


# ---------------------------------------------------------------- mídia
def probe(arq):
    r = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name,pix_fmt,width,height,r_frame_rate:format=duration",
             "-of", "json", arq])
    j = json.loads(r.stdout); s = (j.get("streams") or [{}])[0]
    return {"pix": s.get("pix_fmt", ""), "w": s.get("width"), "h": s.get("height"), "dur": float(j.get("format", {}).get("duration", 0) or 0),
            "codec": s.get("codec_name", "")}


def tem_alfa(info): return any(k in info["pix"] for k in ("yuva", "rgba", "argb", "bgra", "gbrap", "ya"))


def chave(arq, *extra):
    st = os.stat(arq); return hashlib.sha1(f"{os.path.abspath(arq)}|{st.st_size}|{st.st_mtime}|{extra}".encode()).hexdigest()[:16]


def asset(job, src, proj, fps, larg_max=None):
    """Copia (ou converte) a mídia para <proj>/assets e devolve o nome. Alfa -> WebM VP9 com alfa, no tamanho de uso, a fps."""
    arq = caminho(job, src)
    if not os.path.exists(arq): raise SystemExit(f"hf_molde: arquivo não existe: {arq}")
    os.makedirs(os.path.join(proj, "assets"), exist_ok=True); ext = os.path.splitext(arq)[1].lower()
    if ext in (".mov", ".mp4", ".webm", ".mkv") and tem_alfa(probe(arq)):
        os.makedirs(CACHE, exist_ok=True); k = chave(arq, fps, larg_max); out = os.path.join(CACHE, f"alfa_{k}.webm")
        if not os.path.exists(out):
            esc = f",scale='min(iw,{int(larg_max)})':-2:flags=lanczos" if larg_max else ""
            run(["ffmpeg", "-v", "error", "-y", "-i", arq, "-an", "-vf", f"fps={fps}{esc},format=yuva420p", "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
                 "-b:v", 0, "-crf", 20, "-row-mt", 1, "-auto-alt-ref", 0, out + ".tmp.webm"])
            os.replace(out + ".tmp.webm", out)
        nome = f"alfa_{k}.webm"; src_local = out
    else:
        nome = f"{chave(arq)}{ext}"; src_local = arq
    dst = os.path.join(proj, "assets", nome)
    if not os.path.exists(dst): shutil.copyfile(src_local, dst)
    return f"assets/{nome}"


def ultimo_quadro(job, src, proj):
    arq = caminho(job, src); nome = f"fim_{chave(arq)}.png"; dst = os.path.join(proj, "assets", nome)
    if not os.path.exists(dst):
        run(["ffmpeg", "-v", "error", "-y", "-sseof", "-0.1", "-i", arq, "-frames:v", 1, "-update", 1, dst])
    return f"assets/{nome}"


# ---------------------------------------------------------------- texto (pilula.py)
def tela_base(tela): return 1080, round(1080 * tela[1] / tela[0])


def png_texto(c, tela, dst):
    import pilula
    from PIL import Image
    cw, ch = tela_base(tela); img = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    ar = c.get("area", "plataforma")
    if ar == "plataforma": ar = pilula.area_legenda((cw, ch), "4:5", "plataforma")
    ar = tuple(ar); estilo = c.get("estilo", "legenda"); tam = c.get("tam") or pilula.PADRAO["tamanho"]; y = c["y"]
    mw = ar[2] - ar[0] - 2 * tam * pilula.MARGEM
    linhas = c.get("linhas") or pilula.caber([c["texto"]], tam, mw)
    if estilo == "caixa":
        cor = {d["linha"] - 1: d["cor"] for d in c.get("destaque", [])}
        ls = []
        for i, t in enumerate(linhas):
            if i in cor:
                h = cor[i].lstrip("#"); ls.append((t, (255, 255, 255), (0, 0, 0), (0, len(t), tuple(int(h[k:k + 2], 16) for k in (0, 2, 4)))))
            else: ls.append((t, (255, 255, 255), (0, 0, 0)))
        for t, *_ in ls:
            if pilula._largura(t, tam) > mw: raise SystemExit(f"hf_molde: texto não cabe na área ({tam}px): {t}")
        fonte = pilula.FONTE_HD if c.get("fonte", "hd") == "hd" else pilula.FONTE_LEG
        kw = {"raio": 0.26, "vao": -1} if c.get("fonte", "hd") == "hd" else {}
        pilula._linhas(img, ls, y, tam, topo=True, area=ar, arq=fonte, **kw)
    else:
        lh = round(tam * pilula.PADRAO["entrelinha"]); st = max(1, round(tam * pilula.PADRAO["contorno"]))
        tx = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        pilula._legenda_nativa(tx, [(t, None, None) for t in linhas], y + (len(linhas) * lh + 2 * st) / 2, tam, ar)
        if estilo == "check":                               # emoji Apple à esquerda da 1ª linha; bloco recentrado
            bb = tx.getbbox(); lado = round(tam); gap = round(tam * 0.28)
            l1 = tx.crop((0, bb[1], cw, bb[1] + lh)).getbbox()
            larg = (bb[2] - bb[0]) + lado + gap; x0 = round((cw - larg) / 2); dx = x0 + lado + gap - bb[0]
            img.alpha_composite(tx, (dx, 0))
            ic = Image.open(os.path.join(EMOJI, f"{c.get('icone', '2705')}.png")).convert("RGBA").resize((lado, lado), Image.LANCZOS)
            img.alpha_composite(ic, (round(l1[0] + dx - lado - gap), bb[1] + (lh - lado) // 2 + 2))
        else: img = tx
    img.save(dst, compress_level=1)
    bb = img.getbbox() or (0, 0, 0, 0)
    return [round(v * tela[0] / 1080) for v in bb]


# ---------------------------------------------------------------- composição
class Comp:
    def __init__(self, job, proj, tela, fps, dur):
        self.job, self.proj, self.tela, self.fps, self.dur = job, proj, tela, fps, dur
        self.el, self.js, self.trava, self.textos, self.bg = [], [], [], [], False; self.z = 1; self.n = 0

    def q(self, t): return round(t * self.fps) / self.fps                     # tempo no quadro

    def novo_id(self, pre): self.n += 1; return f"{pre}{self.n}"

    def video(self, src, t0, d, de=0.0, caixa=None, vel=1.0, extra="", cls="clip", z=None, larg=None):
        W, H = self.tela; x, y, w, h = caixa or (0, 0, W, H); i = self.novo_id("v")
        a = asset(self.job, src, self.proj, self.fps, larg or w)
        rate = f' data-playback-rate="{vel:.5f}"' if abs(vel - 1) > 1e-6 else ""
        self.el.append(f'<video id="{i}" class="{cls}" src="{a}" muted playsinline data-start="{t0:.4f}" data-duration="{d + SOBRA:.4f}" '
                       f'data-media-start="{de:.4f}"{rate} style="position:absolute;left:{x}px;top:{y}px;width:{w}px;height:{h}px;'
                       f'object-fit:cover;{extra}z-index:{z or self.z}"></video>')
        if z is None: self.z += 1
        return i

    def abre(self, extra=""):
        i = self.novo_id("g"); self.el.append(f'<div id="{i}" style="position:absolute;inset:0;overflow:hidden;{extra}z-index:{self.z}">'); self.z += 1; return i

    def fecha(self): self.el.append("</div>")

    def dissolve(self, i, t, d, entra=True):
        a, b = (0, 1) if entra else (1, 0)
        self.js.append(f'tl.fromTo("#{i}", {{opacity:{a}}}, {{opacity:{b}, duration:{d}, ease:"none"}}, {t:.4f});')

    def push(self, i, t0, d, k):
        self.js.append(f'tl.fromTo("#{i}", {{scale:1}}, {{scale:{1 + k * d:.4f}, duration:{d:.4f}, ease:"none"}}, {t0:.4f});')

    # -- camadas
    def c_video(self, c):
        t0, t1 = self.q(c.get("t0", 0)), self.q(c.get("t1", self.dur)); de = c.get("de", 0.0); vel = c.get("velocidade", 1.0)
        arq = caminho(self.job, c["src"]); info = probe(arq); dmed = info["dur"]
        cortes = [t0] + [self.q(k["t"]) for k in c.get("chaves", [])] + [t1]
        caixas = [c.get("caixa")] + [k.get("caixa") for k in c.get("chaves", [])]
        larg = max((cx[2] for cx in caixas if cx), default=None)
        wrap = None
        if c.get("entra") or c.get("sai") or c.get("push"):
            wrap = self.abre("opacity:0;" if c.get("entra") else "")
            if c.get("push"): inner = self.abre(); self.push(inner, t0, t1 - t0, c["push"])
        for a, b, cx in zip(cortes, cortes[1:], caixas):
            pos_med = de + (a - t0) * vel
            if c.get("loop") and dmed:
                t = a
                while t < b - 1e-6:
                    m = (pos_med + (t - a) * vel) % dmed; d = min(b - t, (dmed - m) / vel); d = max(d, 1 / self.fps)
                    self.video(c["src"], t, d, m, cx, vel, larg=larg); t = self.q(t + d) if self.q(t + d) > t else t + d
            else:
                fim_med = pos_med + (b - a) * vel
                if c.get("congela") and dmed and fim_med > dmed - 0.05:
                    d_vid = self.q(max(1 / self.fps, (dmed - 0.05 - pos_med) / vel))
                    self.video(c["src"], a, d_vid, pos_med, cx, vel, larg=larg)
                    W, H = self.tela; x, y, w, h = cx or (0, 0, W, H); png = ultimo_quadro(self.job, c["src"], self.proj); i = self.novo_id("i")
                    self.el.append(f'<img id="{i}" class="clip" src="{png}" data-start="{a + d_vid:.4f}" data-duration="{b - a - d_vid + SOBRA:.4f}" '
                                   f'data-layout-ignore style="position:absolute;left:{x}px;top:{y}px;width:{w}px;height:{h}px;object-fit:cover;z-index:{self.z}" />')
                    self.z += 1
                else:
                    self.video(c["src"], a, b - a, pos_med, cx, vel, larg=larg)
        if wrap:
            if c.get("push"): self.fecha()
            self.fecha()
            if c.get("entra"): self.dissolve(wrap, t0, c["entra"]["dissolve"])
            else: self.js.append(f'tl.set("#{wrap}", {{opacity:1}}, {t0:.4f});')
            if c.get("sai"): self.dissolve(wrap, t1 - c["sai"]["dissolve"], c["sai"]["dissolve"], entra=False)
        if c.get("papel") == "broll":
            self.trava.append({"ini": t0, "fim": t1, "fonte": arq, "tipo": "broll", "src_ini": de, "src_fim": de + (t1 - t0) * vel,
                               "nome": os.path.basename(arq)})

    def c_planos(self, c):
        W, H = self.tela; f = round(c["t0"] * self.fps); faixa = c.get("faixa", 0.5); pena = c.get("pena", 26)
        g = self.abre("opacity:0;" if c.get("entra") else ""); t_ini = f / self.fps
        for it in c["itens"]:
            n = int(it["q"]); t0 = f / self.fps; d = n / self.fps; de = it.get("de", 0.0); vel = it.get("velocidade", 1.0)
            arq = caminho(self.job, it["src"])
            s_, bx, by, *forca = it.get("reenquadra", [1, 0.5, 0.5]); sw, sh = round(W * s_), round(H * s_)
            x0 = round(W / 2 - bx * sw); y0 = round(faixa * H - by * sh); fundo = not (s_ >= 1 and not forca)
            if not fundo: x0 = max(min(x0, 0), W - sw); y0 = max(min(y0, 0), H - sh)
            wrap = self.abre() if it.get("push") else None
            if wrap: self.push(wrap, t0, d, it["push"])
            if fundo:
                self.bg = True; mx, my = round(W * 0.075), round(H * 0.075)
                self.video(it["src"], t0, d, de, (-mx, -my, W + 2 * mx, H + 2 * my), vel, cls="clip bg", larg=W)
                mask = (f"-webkit-mask-image:linear-gradient(to right,transparent,#000 {pena}px,#000 calc(100% - {pena}px),transparent),"
                        f"linear-gradient(to bottom,transparent,#000 {pena}px,#000 calc(100% - {pena}px),transparent);"
                        "-webkit-mask-composite:source-in;mask-composite:intersect;")
            else: mask = ""
            self.video(it["src"], t0, d, de, (x0, y0, sw, sh), vel, extra=mask, larg=sw)
            if wrap: self.fecha()
            self.trava.append({"ini": t0, "fim": t0 + d, "fonte": arq, "tipo": "broll", "src_ini": de, "src_fim": de + d * vel, "nome": os.path.basename(arq)})
            f += n
        self.fecha()
        if c.get("entra"): self.dissolve(g, t_ini, c["entra"]["dissolve"])
        else: self.js.append(f'tl.set("#{g}", {{opacity:1}}, {t_ini:.4f});')

    def c_imagem(self, c, src_local=None):
        W, H = self.tela; x, y, w, h = c.get("caixa") or (0, 0, W, H); t0, t1 = self.q(c.get("t0", 0)), self.q(c.get("t1", self.dur))
        a = src_local or asset(self.job, c["src"], self.proj, self.fps); i = self.novo_id("i")
        self.el.append(f'<img id="{i}" class="clip" src="{a}" data-start="{t0:.4f}" data-duration="{t1 - t0:.4f}" data-layout-ignore '
                       f'style="position:absolute;left:{x}px;top:{y}px;width:{w}px;height:{h}px;z-index:{self.z}" />'); self.z += 1

    def c_texto(self, c):
        nome = f"t_{self.n + 1}_{hashlib.sha1(json.dumps(c, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:8]}.png"
        os.makedirs(os.path.join(self.proj, "assets"), exist_ok=True)
        bb = png_texto(c, self.tela, os.path.join(self.proj, "assets", nome))
        self.textos.append({"t0": c.get("t0", 0), "t1": c.get("t1", self.dur), "estilo": c.get("estilo", "legenda"),
                            "texto": " / ".join(c.get("linhas") or [c.get("texto", "")]), "bbox": bb,
                            "y": [round(bb[1] / self.tela[1], 3), round(bb[3] / self.tela[1], 3)]})
        self.c_imagem(c, src_local=f"assets/{nome}")

    def html(self, audio=None):
        W, H = self.tela; corpo = "\n    ".join(self.el)
        aud = (f'<audio id="trilha" class="clip" src="{audio}" data-start="0" data-duration="{self.dur}" data-volume="1"></audio>' if audio else "")
        return f"""<!doctype html>
<html lang="pt">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width={W}, height={H}" />
  <script src="gsap.min.js"></script>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    html, body {{ width: {W}px; height: {H}px; overflow: hidden; background: #000; }}
    #root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; }}
  </style>
</head>
<body>
  <div id="root" data-composition-id="main" data-start="0" data-duration="{self.dur}" data-width="{W}" data-height="{H}" data-fps="{self.fps}">
    {corpo}
    {aud}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    {chr(10).join("    " + j for j in self.js).strip()}
    tl.set({{}}, {{}}, {self.dur});
    window.__timelines = window.__timelines || {{}};
    window.__timelines["main"] = tl;
    tl.seek(0);
  </script>
</body>
</html>
"""


# ---------------------------------------------------------------- áudio (ffmpeg só mede e prepara: loudnorm em 2 passos)
def trilha(job, a, dur, proj):
    arq = caminho(job, a["trilha"]); lufs, tp = a.get("lufs", -20), a.get("tp", -1.5); fo = a.get("fade_out", 2.0); de = a.get("de", 0)
    k = chave(arq, lufs, tp, fo, de, dur); dst = os.path.join(proj, "assets", f"trilha_{k}.wav")
    if os.path.exists(dst): return f"assets/trilha_{k}.wav"
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    af = f"atrim={de}:{de + dur},asetpts=PTS-STARTPTS"
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", arq, "-af", f"{af},loudnorm=I={lufs}:TP={tp}:LRA=11:print_format=json", "-f", "null", "-"])
    j = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    ln = (f"loudnorm=I={lufs}:TP={tp}:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}"
          f":measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
    run(["ffmpeg", "-v", "error", "-y", "-i", arq, "-af", f"{af},{ln},afade=t=out:st={max(0, dur - fo)}:d={fo},apad=whole_dur={dur}", "-t", dur,
         "-ar", 48000, "-ac", 2, dst])
    return f"assets/trilha_{k}.wav"


# ---------------------------------------------------------------- montar o projeto
def preparar(job, spec, p, fmt, saida_log=True):
    marcas = list(spec.get("marcas", {})) or ["ad"]; F = por_marca(spec["formatos"][fmt], p, marcas)
    if "de" in F: raise SystemExit(f"hf_molde: o formato {fmt} é derivado de {F['de']} (recorte); não tem projeto próprio")
    fps = spec.get("fps", 30); dur = spec["dur"]; tela = F["tela"]
    proj = os.path.join(TMP, re.sub(r"[^\w.-]", "_", os.path.basename(job.rstrip("/\\"))), f"{p}_{fmt}")
    if os.path.isdir(proj):
        for x in os.listdir(proj):
            if x.endswith(".html") or x.endswith(".png") and x.startswith("snap"): os.remove(os.path.join(proj, x))
    os.makedirs(os.path.join(proj, "assets"), exist_ok=True)
    shutil.copyfile(GSAP, os.path.join(proj, "gsap.min.js"))
    json.dump({"id": f"{p}_{fmt}", "name": f"{p}_{fmt}"}, open(os.path.join(proj, "meta.json"), "w"))
    C = Comp(job, proj, tela, fps, dur)
    for c in F["camadas"]:
        getattr(C, "c_" + c["tipo"])(c)
    aud = trilha(job, por_marca(spec["audio"], p, marcas), dur, proj) if spec.get("audio") else None
    open(os.path.join(proj, "index.html"), "w", encoding="utf-8").write(C.html(aud))
    if C.bg:   # fundo desfocado: blur pela media-treatment (o HyperFrames não aceita blur por CSS)
        hf("media-treatment", "--project", proj, "--selector", "video.bg", "--grading", json.dumps({"effects": {"blur": 0.85}}), "--apply", "--json")
    json.dump({"textos": C.textos, "planos": C.trava}, open(os.path.join(proj, "linha.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if saida_log:
        for t in C.textos: print(f"   texto {t['estilo']:7s} {t['t0']:5.2f}-{t['t1']:5.2f} s  y {t['y'][0] * 100:.1f}-{t['y'][1] * 100:.1f}%  {t['texto'][:60]}")
    return proj, C


def conferir_trava(job, spec, p, fmt, C):
    import trava_timeline as TT
    ps = sorted((dict(x) for x in C.trava), key=lambda x: x["ini"])
    for a, b in zip(ps, ps[1:]):            # dissolve: os dois planos coexistem; para a trava o corte é o início do dissolve
        if b["ini"] < a["fim"]: a["src_fim"] = a["src_ini"] + (b["ini"] - a["ini"]) * ((a["src_fim"] - a["src_ini"]) / max(1e-6, a["fim"] - a["ini"])); a["fim"] = b["ini"]
    C.trava = ps
    TT.trava(C.trava,spec.get("fps", 30), f"{p} {fmt}", dur_total=spec["dur"], aceitas=spec.get("aceitar_lasca", ()), ad=p)
    print(f"   trava ok: {len(C.trava)} planos, {max(0, len(C.trava) - 1)} cortes")


# ---------------------------------------------------------------- render
def pico_ram(stop, out):
    try: import psutil
    except ImportError: return
    nomes = ("chrome", "ffmpeg", "node", "chrome-headless-shell")
    while not stop.is_set():
        tot = 0
        for pr in psutil.process_iter(["name", "memory_info"]):
            try:
                if any((pr.info["name"] or "").lower().startswith(n) for n in nomes): tot += pr.info["memory_info"].rss
            except Exception: pass
        out[0] = max(out[0], tot); time.sleep(0.5)


def destino(job, spec, p, sufixo=""):
    nome = (spec.get("marcas", {}).get(p) or {}).get("nome", p)
    modelo = spec.get("saida", "09_export/{p}/{card} - {nome} - AD1{sufixo}.mp4")
    return caminho(job, modelo.format(p=p, card=card_de(job, spec), nome=nome, sufixo=sufixo))


def guardar_velho(arq):
    """Versão anterior vai para <export>/_old/V<k>/<marca>/ (só se havia arquivo)."""
    pasta = os.path.dirname(arq)
    if not os.path.exists(arq): return
    raiz = os.path.dirname(pasta); k = 1
    while os.path.exists(os.path.join(raiz, "_old", f"V{k}", os.path.basename(pasta), os.path.basename(arq))): k += 1
    d = os.path.join(raiz, "_old", f"V{k}", os.path.basename(pasta)); os.makedirs(d, exist_ok=True)
    shutil.move(arq, os.path.join(d, os.path.basename(arq)))
    if os.path.exists(arq + ".PREVIA.txt"): shutil.move(arq + ".PREVIA.txt", os.path.join(d, os.path.basename(arq) + ".PREVIA.txt"))


def entregar_arquivo(src, dst, previa, nota):
    os.makedirs(os.path.dirname(dst), exist_ok=True); guardar_velho(dst); shutil.copyfile(src, dst)
    if previa: open(dst + ".PREVIA.txt", "w", encoding="utf-8").write(f"PREVIA HyperFrames ({nota}), não entregar.\n")
    elif os.path.exists(dst + ".PREVIA.txt"): os.remove(dst + ".PREVIA.txt")
    print("   saiu:", dst)


def render(job, spec, p, fmt, final):
    previa = not final and os.environ.get("PREVIA", "1") == "1"
    F = por_marca(spec["formatos"][fmt], p, list(spec.get("marcas", {})))
    if "de" in F:                                                  # derivado: recorte do formato-base já renderizado
        base = destino(job, spec, p, por_marca(spec["formatos"][F["de"]], p, list(spec.get("marcas", {}))).get("sufixo", ""))
        if not os.path.exists(base): raise SystemExit(f"hf_molde: renderize o {F['de']} antes do {fmt}")
        x, y, w, h = F["corte"]; out = os.path.join(TMP, f"_{p}_{fmt}.mp4")
        enc = ["-c:v", "h264_nvenc", "-preset", "p5", "-cq", 21, "-b:v", 0] if previa else ["-c:v", "libx264", "-crf", 18, "-preset", "medium"]
        run(["ffmpeg", "-v", "error", "-y", "-i", base, "-vf", f"crop={w}:{h}:{x}:{y},setsar=1", "-r", spec.get("fps", 30)] + enc +
            ["-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", out])
        entregar_arquivo(out, destino(job, spec, p, F.get("sufixo", f" - {w}x{h}")), previa, f"recorte do {F['de']}")
        return
    proj, C = preparar(job, spec, p, fmt)
    conferir_trava(job, spec, p, fmt, C)
    out = os.path.join(proj, "saida.mp4"); log = os.path.join(proj, "render.log")
    args = ["render", proj, "-o", out, "-f", spec.get("fps", 30)] + (["--gpu"] if previa else ["--crf", 18])
    stop = threading.Event(); pico = [0]; th = threading.Thread(target=pico_ram, args=(stop, pico), daemon=True); th.start()
    t0 = time.time(); hf(*args, log=log); dt = time.time() - t0; stop.set(); th.join()
    med = {"marca": p, "formato": fmt, "final": not previa, "segundos": round(dt, 1), "ram_pico_gb": round(pico[0] / 2 ** 30, 2),
           "dur_video": spec["dur"], "quando": time.strftime("%Y-%m-%d %H:%M")}
    print("   render:", json.dumps(med, ensure_ascii=False))
    with open(os.path.join(auto_de(job), "hf_render.jsonl"), "a", encoding="utf-8") as f: f.write(json.dumps(med, ensure_ascii=False) + "\n")
    entregar_arquivo(out, destino(job, spec, p, F.get("sufixo", "")), previa, "NVENC" if previa else "final")


def quadros(job, spec, p, fmt, em):
    proj, _ = preparar(job, spec, p, fmt, saida_log=False)
    d = os.path.join(proj, "quadros")
    hf("snapshot", proj, "-o", d, "--at", em, "--no-end", log=os.path.join(proj, "snapshot.log"))
    for s in sorted(os.listdir(d)):
        if s.lower().endswith((".png", ".jpg")): print("   quadro:", os.path.join(d, s))


def main():
    for s in (sys.stdout, sys.stderr):
        try: s.reconfigure(encoding="utf-8")
        except Exception: pass
    ap = argparse.ArgumentParser(description="Molde HyperFrames do núcleo.")
    ap.add_argument("acao", choices=("trava", "preparar", "quadros", "render")); ap.add_argument("job")
    ap.add_argument("--marca"); ap.add_argument("--formato"); ap.add_argument("--final", action="store_true")
    ap.add_argument("--em", default="1,5,10"); ap.add_argument("--spec")
    a = ap.parse_args(); job = os.path.abspath(a.job); spec, _ = ler_spec(job, a.spec)
    if not os.path.exists(HF_JS): raise SystemExit(f"hf_molde: HyperFrames não instalado ({HF_JS}). npm i -g hyperframes@0.9.17")
    marcas = [a.marca] if a.marca else (list(spec.get("marcas", {})) or ["ad"])
    fmts = [a.formato] if a.formato else list(spec["formatos"])
    for p in marcas:
        for fmt in fmts:
            print(f"-- {a.acao} {p} {fmt}")
            if a.acao == "render": render(job, spec, p, fmt, a.final)
            elif "de" in spec["formatos"][fmt]: print("   derivado (recorte): nada a preparar")
            elif a.acao == "preparar": print("   projeto:", preparar(job, spec, p, fmt)[0])
            elif a.acao == "trava": conferir_trava(job, spec, p, fmt, preparar(job, spec, p, fmt, saida_log=False)[1])
            else: quadros(job, spec, p, fmt, a.em)


if __name__ == "__main__":
    main()
