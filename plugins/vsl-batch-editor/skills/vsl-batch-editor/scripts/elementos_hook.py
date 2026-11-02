#!/usr/bin/env python3
"""Elementos de hook do guia modulos/hooks.md que o fluxo.montar desenha por cima do vídeo (PNG do Pillow + overlay do
ffmpeg, como o pilula.py). Todos opcionais, ligados por plano.json -> estilo; o ref da batch decide se entram.

- barra_tempo (tipo A, ref NoMore): pílula no topo com os marcos ("1 min · Day 1 · Week 1 · Week 3 · Week 4"); o marco
  atual fica verde e avança quando a legenda do AD chega no texto do gatilho; os já passados ficam com texto verde.
  estilo.barra_tempo = {"marcos": [...], "gatilhos": ["<texto da legenda>", ...] (um por marco), "de": "<texto>" (opcional:
  a barra aparece antes do 1º gatilho, sem marco aceso), "ate": "fim" | "<texto>", "y": 110 (topo, px de 1920, ou
  fração se <= 1), "tamanho": 38, "pop": true, "hooks": [1, 2], cores: "cor_fundo", "opacidade", "cor_texto",
  "cor_ativo", "cor_texto_ativo", "cor_passado"}
- tag_nativa (tipo F, ref Pureskin): legenda "nativa" estilo Snapchat nos primeiros segundos do hook: faixa preta
  translúcida de ponta a ponta, texto branco pequeno centralizado + emojis.
  estilo.tag_nativa = {"texto": "what are these dudes doing 🤯🤯", "y": 0.42 (centro da faixa; fração ou px), "de": 0,
  "ate": 2.2 (s, ou "hook" = o hook inteiro), "tamanho": 40, "opacidade": 0.6, "hooks": [1]}
- split (tipo B, ref 8 Sheep): cena com "formato": "split" = dois clipes lado a lado (esquerda o clipe da cena = resultado;
  direita "clipe_direita" = produto). O filtro é montado no fluxo.montar (split_filtro).
- inset (antes/depois sobre a selfie, BATCH#3223): cena com "formato": "inset" = o clipe entra num cartão quadrado de
  cantos arredondados, com borda branca e sombra, por cima do avatar (que continua falando por cima do cartão); rótulo
  opcional na cena ("rotulo": "2 MONTHS AGO" / "NOW") numa pílula branca no canto do cartão. Na cena: "inset_cy" (0 = topo
  do clipe, 1 = base; qual faixa do 9:16 vira o quadrado, padrão 0.4) e "inset_filtro" (filtro ffmpeg extra no clipe, ex.
  "hue=s=0.35" para o "antes" dessaturado). Geometria em estilo.inset = {"x": 150, "y": 870, "lado": 780, "raio": 36,
  "borda": 8, "tamanho": 46} (px de 1080x1920; o padrão deixa o rosto da selfie livre em cima e a legenda pílula em 0,66 cai
  dentro do cartão). Só no layout tela_cheia."""
import os
from PIL import Image, ImageDraw, ImageFont

FONTE = ("/System/Library/Fonts/HelveticaNeue.ttc", 1)      # Helvetica Neue Bold (igual ao pilula.py)
NATIVA = ("/System/Library/Fonts/HelveticaNeue.ttc", 0)     # Helvetica Neue regular: a legenda do Snapchat é fina
EMOJI = "/System/Library/Fonts/Apple Color Emoji.ttc"       # bitmap: só renderiza em 160 px; reduz depois
W, H, FPS = 1080, 1920, 30

def _rgb(h): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
def _px(y, ref=H): return round(y * ref) if y <= 1 else round(y)
def _fonte(f, tam): return ImageFont.truetype(f[0], tam, index=f[1])

def vale(cfg, n):
    """O elemento entra neste hook? ("hooks": [1, 3] limita; sem a chave, entra em todos)."""
    return bool(cfg) and (not cfg.get("hooks") or int(n) in [int(h) for h in cfg["hooks"]])

# ---------------------------------------------------------------- texto com emoji
def _e_emoji(ch):
    o = ord(ch)
    return o >= 0x1F000 or 0x2600 <= o <= 0x27BF or 0x2B00 <= o <= 0x2BFF or 0x2190 <= o <= 0x21FF

def _pedacos(txt):
    """[(texto, é_emoji)]. Sem libraqm o Pillow não junta ZWJ/tom de pele: esses modificadores saem (emoji simples)."""
    out = []
    for ch in txt:
        if ch in "‍️" or 0x1F3FB <= ord(ch) <= 0x1F3FF: continue
        e = _e_emoji(ch)
        if out and out[-1][1] == e and not e: out[-1] = (out[-1][0] + ch, False)
        else: out.append((ch, e))
    return out

_cache_emoji = {}
def _emoji(ch, lado):
    if (ch, lado) not in _cache_emoji:
        im = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((0, 0), ch, font=ImageFont.truetype(EMOJI, 160), embedded_color=True)
        im = im.crop((0, 0, 160, 160)).resize((lado, lado), Image.LANCZOS)
        _cache_emoji[(ch, lado)] = im
    return _cache_emoji[(ch, lado)]

def _texto_emoji(img, txt, cx, cy, fonte, cor):
    """Texto centralizado em (cx, cy) com emoji colorido do tamanho da letra."""
    d = ImageDraw.Draw(img); ps = _pedacos(txt)
    lado = round(fonte.size * 1.12); esp = round(fonte.size * 0.06)
    larg = sum(d.textlength(t, font=fonte) if not e else lado + 2 * esp for t, e in ps)
    capH = fonte.getbbox("H")[3] - fonte.getbbox("H")[1]
    x = cx - larg / 2
    for t, e in ps:
        if e:
            img.alpha_composite(_emoji(t, lado), (round(x + esp), round(cy - lado / 2)))
            x += lado + 2 * esp
        else:
            d.text((x, cy + capH / 2), t, font=fonte, fill=cor + (255,), anchor="ls"); x += d.textlength(t, font=fonte)
    return larg

# ---------------------------------------------------------------- tag nativa (Snapchat)
def tag_nativa(cfg, pasta):
    """PNG 1080 x altura da faixa. Devolve (png, y_topo) para o overlay."""
    tam = cfg.get("tamanho", 40); f = _fonte(NATIVA, tam); hf = round(tam * 1.95)
    img = Image.new("RGBA", (W, hf), (0, 0, 0, round(255 * cfg.get("opacidade", 0.6))))
    _texto_emoji(img, cfg["texto"], W / 2, hf / 2, f, _rgb(cfg.get("cor_texto", "#FFFFFF")))
    os.makedirs(pasta, exist_ok=True); p = os.path.abspath(f"{pasta}/tag_nativa.png"); img.save(p)
    return p, _px(cfg.get("y", 0.42)) - hf // 2

def janela_tag(cfg, HD):
    a = float(cfg.get("de", 0)); b = HD if cfg.get("ate") == "hook" else min(HD, float(cfg.get("ate", 2.2)))
    return a, b

# ---------------------------------------------------------------- barra de progresso
def _tam_barra(cfg):
    """Tamanho da letra que cabe na largura (marcos demais: diminui)."""
    tam = cfg.get("tamanho", 38); d = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    while tam > 18:
        f = _fonte(FONTE, tam); pad = round(tam * 0.55)
        larg = sum(d.textlength(m, font=f) + 2 * pad for m in cfg["marcos"]) + d.textlength(" · ", font=f) * (len(cfg["marcos"]) - 1)
        if larg <= W - 60: break
        tam -= 2
    return tam

def _canvas(tam): hb = round(tam * 1.9); return (W, 3 * hb), hb      # faixa com margem de 1 altura em cima e embaixo (pop)

def _barra(cfg, ativo, escala, tam):
    """Quadro da barra com o marco `ativo` aceso (-1 = barra sem marco aceso)."""
    marcos = cfg["marcos"]; f = _fonte(FONTE, tam); (cw, ch), hb = _canvas(tam)
    pad = round(tam * 0.55); sep = " · "; mg = hb
    img = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    lw = [d.textlength(m, font=f) for m in marcos]; sw = d.textlength(sep, font=f)
    larg = sum(lw) + sw * (len(marcos) - 1) + 2 * pad * len(marcos)
    fundo = _rgb(cfg.get("cor_fundo", "#FFFFFF")) + (round(255 * cfg.get("opacidade", 0.92)),)
    x0 = (W - larg) / 2 - pad * 0.4; y0 = mg
    d.rounded_rectangle([x0, y0, x0 + larg + pad * 0.8, y0 + hb], radius=hb / 2, fill=fundo)
    capH = f.getbbox("H")[3] - f.getbbox("H")[1]; x = x0 + pad * 0.4
    cor_t, cor_a = _rgb(cfg.get("cor_texto", "#2A2A2A")), _rgb(cfg.get("cor_ativo", "#22C55E"))
    cor_ta, cor_p = _rgb(cfg.get("cor_texto_ativo", "#FFFFFF")), _rgb(cfg.get("cor_passado", "#16A34A"))
    for k, (m, w) in enumerate(zip(marcos, lw)):
        cx = x + pad + w / 2; cy = y0 + hb / 2
        if k == ativo:
            bw, bh = (w + 1.5 * pad) * escala, (hb - 10) * escala       # folga até o "·" vizinho
            d.rounded_rectangle([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2], radius=bh / 2, fill=cor_a + (255,))
            fa = _fonte(FONTE, max(8, round(tam * escala)))
            d.text((cx, cy + (capH * escala) / 2), m, font=fa, fill=cor_ta + (255,), anchor="ms")
        else:
            d.text((cx, cy + capH / 2), m, font=f, fill=(cor_p if 0 <= ativo and k < ativo else cor_t) + (255,), anchor="ms")
        x += w + 2 * pad
        if k + 1 < len(marcos):
            d.text((x + sw / 2, cy + capH / 2), sep.strip(), font=f, fill=(150, 150, 150, 255), anchor="ms"); x += sw
    return img

def barra_tempo(cfg, evs, total, pasta):
    """Lista do concat demuxer (PNGs com duração) cobrindo [0, total] e o y do overlay.
    evs = legenda do AD [(ini, fim, texto)]; cada gatilho vale no ponto da legenda em que o texto aparece."""
    import re
    nt = lambda s: re.sub(r"[^a-z0-9% ]", "", s.lower())
    def achar(txt, i0):
        alvo = nt(txt).strip()
        for k in range(i0, len(evs)):
            t = nt(evs[k][2]); j = t.find(alvo)
            if j >= 0: s, e = evs[k][0], evs[k][1]; return k, s + (e - s) * j / max(1, len(t))
        raise SystemExit(f"barra_tempo: não achei {txt!r} na legenda do AD (gatilhos/de/ate procuram na legenda da hold, "
                         f"e na do hook quando ele não tem hook_header)")
    marcos, gat = cfg["marcos"], cfg["gatilhos"]
    if len(gat) != len(marcos): raise SystemExit("barra_tempo: um gatilho por marco")
    tg, i = [], 0
    for g in gat: i, t = achar(g, i); tg.append(t)
    ini = achar(cfg["de"], 0)[1] if cfg.get("de") else tg[0]
    if cfg.get("ate", "fim") == "fim": fim = total
    else: k, _ = achar(cfg["ate"], i); fim = evs[k][1]
    fr = lambda t: int(round(t * FPS))
    # (quadro_inicial, marco_ativo) em ordem; o pop é uma escala 1,18 -> 1 nos 6 quadros depois de cada troca
    trocas = [(fr(ini), -1)] + [(fr(t), k) for k, t in enumerate(tg)] + [(fr(fim), None)]
    trocas = sorted({q: a for q, a in trocas}.items())
    tam = _tam_barra(cfg); (cw, ch), hb = _canvas(tam)
    os.makedirs(pasta, exist_ok=True); feitos, ls = {}, []
    def png(ativo, esc=1.0):                       # ativo None = barra escondida
        key = (ativo, round(esc, 3))
        if key not in feitos:
            p = os.path.abspath(f"{pasta}/barra_{'x' if ativo is None else ativo}_{round(esc * 1000)}.png")
            (Image.new("RGBA", (cw, ch), (0, 0, 0, 0)) if ativo is None else _barra(cfg, ativo, esc, tam)).save(p)
            feitos[key] = p
        return feitos[key]
    q0 = trocas[0][0]
    if q0 > 0: ls.append((png(None), q0 / FPS))
    pop = cfg.get("pop", True)
    for (qa, at), (qb, _) in zip(trocas, trocas[1:]):
        if qb <= qa: continue
        n_pop = min(6, qb - qa) if pop and at is not None and at >= 0 else 0
        for j in range(n_pop):
            u = (j + 1) / 6; ls.append((png(at, 1 + 0.18 * (1 - u) ** 2), 1 / FPS))
        if qb - qa - n_pop > 0: ls.append((png(at, 1), (qb - qa - n_pop) / FPS))
    qf = trocas[-1][0]
    if qf < fr(total): ls.append((png(None), (fr(total) - qf) / FPS))
    lista = f"{pasta}/barra.txt"
    with open(lista, "w") as o:
        for p, d in ls: o.write(f"file '{p}'\nduration {d:.6f}\n")
        o.write(f"file '{ls[-1][0]}'\n")
    return lista, _px(cfg.get("y", 110)) - hb          # o PNG tem margem de hb em cima (espaço do pop)

# ---------------------------------------------------------------- tela dividida
def split_filtro(j, jr, i0, i0r, dur, a, k, geo_h, divisoria=0, cor="white"):
    """Filtro da cena 'split': entrada j (esquerda, resultado) e jr (direita, produto), cada uma cobrindo meia largura.
    Gera o rótulo [x{k}] já com a largura cheia (1080 x geo_h), como as outras cenas."""
    m = W // 2
    lado = lambda e, s, r: (f"[{e}:v]trim={s:.3f}:{s + dur:.3f},setpts=PTS-STARTPTS+{a}/TB,"
                            f"scale={m}:{geo_h}:force_original_aspect_ratio=increase,crop={m}:{geo_h},fps=30,setsar=1[{r}{k}]")
    f = f"{lado(j, i0, 'xl')};{lado(jr, i0r, 'xr')};[xl{k}][xr{k}]hstack=inputs=2"
    if divisoria: f += f",drawbox=x={m - divisoria // 2}:y=0:w={divisoria}:h=ih:color={cor}:t=fill"
    return f + f"[x{k}]"

# ---------------------------------------------------------------- inset (antes/depois sobre o avatar)
def _geo_inset(cfg):
    c = {"x": 150, "y": 870, "lado": 780, "raio": 36, "borda": 8, "tamanho": 46}; c.update(cfg or {}); return c

def inset_pngs(cfg, rotulo, pasta, nome):
    """Máscara do cartão (cinza, lado x lado) e moldura 1080x1920 (sombra + borda branca + pílula do rótulo).
    Devolve (máscara, moldura, (x, y, lado))."""
    from PIL import ImageFilter
    g = _geo_inset(cfg); x, y, L, r, bd = g["x"], g["y"], g["lado"], g["raio"], g["borda"]
    os.makedirs(pasta, exist_ok=True)
    mk = Image.new("L", (L, L), 0); ImageDraw.Draw(mk).rounded_rectangle((0, 0, L - 1, L - 1), r, fill=255)
    fm = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sb = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sb).rounded_rectangle((x - bd + 6, y - bd + 14, x + L + bd + 6, y + L + bd + 14), r + bd, fill=(0, 0, 0, 110))
    fm = Image.alpha_composite(fm, sb.filter(ImageFilter.GaussianBlur(14)))
    d = ImageDraw.Draw(fm)
    d.rounded_rectangle((x - bd, y - bd, x + L + bd - 1, y + L + bd - 1), r + bd, outline=(255, 255, 255, 255), width=bd)
    if rotulo:
        f = _fonte(FONTE, g["tamanho"]); tw = d.textlength(rotulo, font=f); ph = round(g["tamanho"] * 1.55); pw = round(tw + ph * 0.9)
        px, py = x + 26, y - ph // 2
        d.rounded_rectangle((px, py, px + pw, py + ph), ph // 2, fill=(255, 255, 255, 255))
        d.text((px + pw / 2, py + ph / 2), rotulo, font=f, fill=(15, 15, 15, 255), anchor="mm")
    m, o = f"{pasta}/{nome}_mascara.png", f"{pasta}/{nome}_moldura.png"
    mk.save(m); fm.save(o); return m, o, (x, y, L)

def inset_filtro(j, jm, i0, dur, a, k, L, cy=0.4, extra=""):
    """Clipe j recortado no quadrado L x L (faixa vertical cy) com a máscara jm de cantos arredondados; sai [x{k}] com alfa,
    já no tempo do AD (como as outras cenas). O overlay e a moldura ficam no fluxo.montar."""
    ex = f"{extra}," if extra else ""
    return (f"[{j}:v]trim={i0:.3f}:{i0 + dur:.3f},setpts=PTS-STARTPTS,scale={L}:{L}:force_original_aspect_ratio=increase,"
            f"crop={L}:{L}:(iw-{L})/2:(ih-{L})*{cy},{ex}fps=30,setsar=1,format=rgba[xi{k}];"
            f"[{jm}:v]scale={L}:{L},format=gray,fps=30[mk{k}];[xi{k}][mk{k}]alphamerge,settb=1/90000,"
            f"setpts=PTS+{round(a * 30) / 30 - 1 / 60:.6f}/TB[x{k}]")


# ---------------------------------------------------------------- card do hook (caixa branca por linha, emoji colorido)
def hook_card(linhas, cfg, out):
    """Card de abertura em PNG 1080x1920 (ref Atria da BATCH#3375: caixa branca, texto preto em negrito, ⚠️ colorido).
    cfg = estilo.hook_card {"x": 30 (esquerda; None = centralizado), "y": 300 (topo), "tamanho": 40, "raio": 14}."""
    tam = int(cfg.get("tamanho", 40)); f = _fonte(FONTE, tam); pad_x, pad_y = round(tam * 0.45), round(tam * 0.28)
    lado = round(tam * 1.12); esp = round(tam * 0.06); hl = round(tam * 1.32) + 2 * pad_y
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img); y = int(cfg.get("y", 300))
    for ln in linhas:
        larg = sum(d.textlength(t, font=f) if not e else lado + 2 * esp for t, e in _pedacos(ln))
        x0 = int(cfg["x"]) if cfg.get("x") is not None else round(W / 2 - larg / 2 - pad_x)
        d.rounded_rectangle((x0, y, x0 + larg + 2 * pad_x, y + hl), int(cfg.get("raio", 14)), fill=(255, 255, 255, 255))
        _texto_emoji(img, ln, x0 + pad_x + larg / 2, y + hl / 2, f, (10, 10, 10)); y += hl - 2
    img.save(out); return out
