#!/usr/bin/env python3
"""Legenda 'pilula' (ref Paleovalley, BATCH#2824): estilo do texto do Instagram — cada linha numa caixa de cantos
arredondados, centralizada, 1 ou 2 linhas por bloco. O header do hook usa o mesmo desenho: linhas em caixa branca
com texto preto e a parte entre parênteses numa caixa da cor da marca com texto branco.

Gera PNGs transparentes 1080x1920 (header + legenda já compostos) e uma lista do concat demuxer do ffmpeg;
o fluxo.montar sobrepõe essa lista como uma entrada só (em vez do filtro subtitles).

Configuração em plano.json -> estilo.legenda (todos opcionais):
  "estilo": "pilula", "y": 0.30 (centro do bloco, fração da altura), "tamanho": 46, "quebra": 22 (caracteres por linha),
  "cor_texto": "#111111", "cor_caixa": "#FFFFFF"
e plano.json -> estilo.header_pilula: {"y": 190, "tamanho": 52, "cor_destaque": "#5A2A20"}
Palavra-chave destacada (BATCH#3467, "captions with the key word highlighted"): estilo.legenda.destaque =
  {"palavras": ["morning wood", "cold extraction", ...], "cor": "#FFD400"} -> marca-texto atrás da 1ª expressão da lista
  achada no bloco (a mais longa ganha), texto continua preto; pode atravessar as 2 linhas."""
import hashlib, os
from PIL import Image, ImageDraw, ImageFont
import elementos_hook as EH

FONTE = ("/System/Library/Fonts/HelveticaNeue.ttc", 1)      # Helvetica Neue Bold
W, H, FPS = 1080, 1920, 30
FRACAS = set("a an the to of in on at for with by from and or but so if as that than i my your his her our their its "
             "is are was were be just".split())

def _rgb(h): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def _fonte(tam): return ImageFont.truetype(FONTE[0], tam, index=FONTE[1])

def quebrar(txt, maxc):
    """1 linha se couber; senão 2 linhas equilibradas, sem terminar a 1ª em palavra fraca."""
    if len(txt) <= maxc: return [txt]
    p = txt.split(); melhor = None
    for k in range(1, len(p)):
        a, b = " ".join(p[:k]), " ".join(p[k:])
        c = max(len(a), len(b)) + (8 if p[k - 1].lower().strip(",.") in FRACAS else 0) + (0 if len(a) >= len(b) else 1)
        if melhor is None or c < melhor[0]: melhor = (c, [a, b])
    return melhor[1]

def _linhas(img, linhas, cy, tam, topo=False):
    """Desenha linhas [(texto, cor_caixa, cor_texto)] centralizadas. cy = centro do bloco (ou topo se topo=True)."""
    d = ImageDraw.Draw(img); f = _fonte(tam)
    capH = f.getbbox("H")[3] - f.getbbox("H")[1]
    px, bh, r, sob = round(tam * 0.42), round(tam * 1.42), round(tam * 0.32), round(tam * 0.10)
    total = len(linhas) * bh - (len(linhas) - 1) * sob
    y = cy if topo else cy - total / 2
    for txt, cx, ct, *hl in linhas:
        # emoji colorido (header do Milanote com 😩, BATCH#3215): desenhado pelo elementos_hook, do tamanho da letra
        emo = any(EH._e_emoji(ch) for ch in txt)
        if emo:
            lado, esp = round(f.size * 1.12), round(f.size * 0.06)
            w = sum(d.textlength(t, font=f) if not e else lado + 2 * esp for t, e in EH._pedacos(txt))
        else: w = d.textlength(txt, font=f)
        x0 = (W - w) / 2 - px
        d.rounded_rectangle([x0, y, x0 + w + 2 * px, y + bh], radius=r, fill=cx + (255,))
        if hl and hl[0]:                                 # marca-texto da palavra-chave: (início, fim, cor) na linha
            a, b, cor = hl[0]; xa = x0 + px + d.textlength(txt[:a], font=f); xb = xa + d.textlength(txt[a:b], font=f)
            d.rounded_rectangle([xa - tam * 0.12, y + bh * 0.14, xb + tam * 0.12, y + bh * 0.86], radius=round(r * 0.6), fill=cor + (255,))
        if emo: EH._texto_emoji(img, txt, W / 2, y + bh / 2, f, ct)
        else: d.text((W / 2, y + bh / 2 + capH / 2), txt, font=f, fill=ct + (255,), anchor="ms")
        y += bh - sob
    return y

def quadro(legenda, header, cfg_leg, cfg_hd):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if header:
        tam = cfg_hd.get("tamanho", 52); dest = _rgb(cfg_hd.get("cor_destaque", "#5A2A20"))
        princ, _, par = header.partition("(")
        ls = [(t, (255, 255, 255), (17, 17, 17)) for t in quebrar(princ.strip(), cfg_hd.get("quebra", 22))]
        if par: ls.append(("(" + par.strip(), dest, (255, 255, 255)))
        _linhas(img, ls, cfg_hd.get("y", 190), tam, topo=True)
    if legenda:
        cx, ct = _rgb(cfg_leg.get("cor_caixa", "#FFFFFF")), _rgb(cfg_leg.get("cor_texto", "#111111"))
        lin = quebrar(legenda, cfg_leg.get("quebra", 22)); ls = [(t, cx, ct) for t in lin]
        de = cfg_leg.get("destaque")
        if isinstance(de, dict) and de.get("palavras"):
            low = legenda.lower(); ach = [(low.find(k.lower()), k) for k in de["palavras"] if k.lower() in low]
            if ach:
                i0, k = max(ach, key=lambda x: len(x[1])); i1 = i0 + len(k); cor = _rgb(de.get("cor", "#FFD400")); o = 0
                for n, t in enumerate(lin):
                    a, b = max(i0 - o, 0), min(i1 - o, len(t))
                    if a < b: ls[n] = (t, cx, ct, (a, b, cor))
                    o += len(t) + 1
        _linhas(img, ls, H * cfg_leg.get("y", 0.30), cfg_leg.get("tamanho", 46))
    return img

def gerar(eventos, header, HD, total, pasta, plano, alturas=()):
    """eventos = [(ini, fim, texto)] da legenda do AD; header só em [0, HD). alturas = [(ini, fim, y)]: trechos (cenas
    com "legenda_y" no plano) em que a legenda muda de altura, p.ex. para não cobrir o nome no rótulo. Devolve a lista do concat."""
    e = plano.get("estilo", {}); cl, ch = e.get("legenda", {}), e.get("header_pilula", {})
    os.makedirs(pasta, exist_ok=True)
    fr = lambda t: int(round(t * FPS))
    marcas = sorted({0, fr(total)} | ({fr(HD)} if header else set()) | {fr(a) for a, _, _ in eventos} | {fr(b) for _, b, _ in eventos})
    marcas = [m for m in marcas if 0 <= m <= fr(total)]
    feitos, ls = {}, []
    for a, b in zip(marcas, marcas[1:]):
        if b <= a: continue
        t = (a + b) / 2 / FPS
        leg = next((x for s, f, x in eventos if fr(s) <= a and b <= fr(f)), None)
        hd = header if header and t < HD else None
        ini = next((s for s, f, x in eventos if fr(s) <= a and b <= fr(f)), t)
        y = next((yy for s, f, yy in alturas if s - 0.05 <= ini < f), cl.get("y", 0.30))
        k = hashlib.md5(f"{leg}|{hd}|{y}".encode()).hexdigest()[:10]
        if k not in feitos:
            p = os.path.abspath(f"{pasta}/q_{k}.png"); quadro(leg, hd, dict(cl, y=y), ch).save(p); feitos[k] = p
        ls.append((feitos[k], (b - a) / FPS))
    lista = f"{pasta}/pilula.txt"
    with open(lista, "w") as o:
        for p, d in ls: o.write(f"file '{p}'\nduration {d:.6f}\n")
        o.write(f"file '{ls[-1][0]}'\n")
    return lista
