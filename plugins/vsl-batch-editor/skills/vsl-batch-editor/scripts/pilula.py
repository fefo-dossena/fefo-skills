#!/usr/bin/env python3
"""Legenda padrão da Empire Vision e da Trendscale (regra do Fefo, 13/11/2026): SEMPRE TikTok Sans Medium, texto preto
numa pílula branca de ponta toda redonda, nas proporções do PSD de referência (_FLUXO/legenda/EXEMPLO LEGENDA.psd).
Toda legenda dos dois clientes passa por aqui: montar.py (EV), cartao.py e umtake.py (EV) e montagem_base.exportar (TS).

Medidas do PSD (tela 1080x1920; tudo escala pelo lado menor da tela / 1080):
  fonte    TikTok Sans Medium no corte óptico 36 (instância estática _FLUXO/fontes/TikTokSans-Legenda-Medium.ttf;
           o TikTokSans-Medium.ttf estático do zip é o corte 12, 8% mais largo que o do PSD), corpo 42,5 px, preto
  pílula   branca, altura 57 px (1,342 x corpo), raio = metade da altura, 18,7 px de folga de cada lado (0,44 x corpo)
  texto    linha de base 12,2 px abaixo do centro da pílula (0,287 x corpo), centralizado na horizontal
  2 linhas cada linha na sua pílula, uma em cima da outra, 6 px de vão (0,14 x corpo); quebra em ~30 caracteres
  altura   NÃO vem do PSD (lá a pílula está a 80,6%, abaixo do limite da EV). Segue a regra de cada cliente: EV y = 0,63 e
           nunca abaixo de 0,65 (SKILL.md, checklist da Louise); TS dentro do 1:1 central (legenda.y_rel do job.json).
           Sem y no plano, o padrão é 0,63, que serve aos dois.
  4:5      SEMPRE dentro do 4:5 central, nunca fora (Fefo, 13/11/2026), legenda e header: o bloco é empurrado para
           dentro (folga de 0,3 x corpo) e a linha que passaria da largura é re-quebrada. Avisa quando mexe.
           9:16 1080x1920 = y 285-1635 (190-1090 em 720p).
           Trendscale: estilo.legenda.area = "1:1" (o montagem_base passa) prende no 1:1 central (y 420-1500). Do PSD
           vem só o estilo; a posição é a da regra de cada cliente (Fefo, 13/11/2026).

O que o plano pode mudar (plano.json -> estilo.legenda): "y" (centro do bloco: fração da altura ou px), "quebra"
(caracteres por linha) e "destaque" = {"palavras": [...], "cor": "#FFD400"} (marca-texto atrás da 1ª expressão achada,
texto continua preto). Corpo, cores, fonte e desenho da pílula NÃO mudam: "tamanho", "cor_texto" e "cor_caixa" no
plano são ignorados com aviso. Exceção só com ok do Fefo, anotada no plano.
Header do hook (estilo.header_pilula: {"y": 190, "tamanho": 52, "cor_destaque": "#5A2A20"}): mesmo desenho, linhas em
pílula branca com texto preto e a parte entre parênteses numa pílula da cor da marca com texto branco.

Saída: PNGs transparentes do tamanho da tela (header + legenda já compostos) e uma lista do concat demuxer do ffmpeg,
sobreposta como uma entrada só (-f concat -safe 0 -i lista; overlay=0:0)."""
import hashlib, os, re, sys
from PIL import Image, ImageDraw, ImageFont
try:
    import elementos_hook as EH                     # emoji colorido no header (só na Empire Vision)
except Exception:
    EH = None

AQUI = os.path.dirname(os.path.abspath(__file__))
FONTE = os.path.normpath(os.path.join(AQUI, "..", "fontes", "TikTokSans-Legenda-Medium.ttf"))
W, H, FPS = 1080, 1920, 30
PADRAO = {"tamanho": 42.5, "altura": 1.342, "folga": 0.44, "base": 0.287, "vao": 0.14,
          "y": 0.63, "quebra": 30, "cor_caixa": "#FFFFFF", "cor_texto": "#000000"}
FIXOS = ("tamanho", "cor_caixa", "cor_texto")       # o plano não muda (regra do Fefo, 13/11/2026)
FRACAS = set("a an the to of in on at for with by from and or but so if as that than i my your his her our their its "
             "is are was were be just de da do das dos e o a os as em no na um uma que para com por".split())
_avisado = set()

def _rgb(h): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def _fonte(tam):
    if not os.path.exists(FONTE):
        raise SystemExit(f"Fonte da legenda não encontrada: {FONTE}. A legenda é SEMPRE TikTok Sans Medium "
                         "(regra do Fefo, 13/11/2026): não troque por outra fonte, recupere o arquivo.")
    return ImageFont.truetype(FONTE, tam)

def escala(tela=(W, H)): return min(tela) / 1080

def _avisar_fixos(cfg):
    for k in FIXOS:
        if k in cfg and cfg[k] != PADRAO[k] and k not in _avisado:
            _avisado.add(k)
            print(f"   aviso pilula: estilo.legenda.{k} = {cfg[k]!r} ignorado (legenda padrão TikTok Sans Medium em pílula, "
                  "regra do Fefo 13/11/2026)", file=sys.stderr)

def quebrar(txt, maxc):
    """1 linha se couber; senão 2 linhas equilibradas, sem terminar a 1ª em palavra fraca."""
    if len(txt) <= maxc: return [txt]
    p = txt.split(); melhor = None
    for k in range(1, len(p)):
        a, b = " ".join(p[:k]), " ".join(p[k:])
        c = max(len(a), len(b)) + (8 if p[k - 1].lower().strip(",.") in FRACAS else 0) + (0 if len(a) >= len(b) else 1)
        if melhor is None or c < melhor[0]: melhor = (c, [a, b])
    return melhor[1] if melhor else [txt]

def geometria(tam):
    """(altura da pílula, folga lateral, raio, linha de base abaixo do centro, vão entre pílulas) para um corpo."""
    P = PADRAO; bh = round(tam * P["altura"])
    return bh, tam * P["folga"], bh / 2, tam * P["base"], tam * P["vao"]

SS = 4                                               # cada linha é desenhada 4x maior e reduzida: borda lisa e
                                                     # largura do texto fracionada (o Pillow sem raqm arredonda cada letra)
MARGEM = 0.3                                         # folga mínima entre a pílula e a borda do 4:5 (x corpo)

def area_45(tela=(W, H)):
    """(x0, y0, x1, y1) do maior 4:5 no centro da tela. Legenda e header NUNCA saem dele (regra do Fefo, 13/11/2026).
    9:16 1080x1920 -> (0, 285, 1080, 1635); 1:1 1080x1080 -> (108, 0, 972, 1080)."""
    w, h = tela
    if w * 5 <= h * 4: a = w * 5 / 4; return 0, (h - a) / 2, w, (h + a) / 2
    a = h * 4 / 5; return (w - a) / 2, 0, (w + a) / 2, h

def area_central(tela=(W, H), prop="4:5"):
    """(x0, y0, x1, y1) do maior retângulo `prop` ("4:5" ou "1:1") no centro da tela. EV: 4:5; TS: 1:1 (regra do Dan;
    Fefo, 13/11/2026: "a posição tem que ser DENTRO do 4x5 pra ev e DENTRO do 1x1 em ts")."""
    if str(prop) in ("4:5", "4x5", "", "None"): return area_45(tela)
    a_, b_ = (float(x) for x in str(prop).replace("x", ":").split(":"))
    w, h = tela
    if w * b_ <= h * a_: a = w * b_ / a_; return 0, (h - a) / 2, w, (h + a) / 2
    a = h * a_ / b_; return (w - a) / 2, 0, (w + a) / 2, h

def _largura(txt, tam):
    """Largura da pílula (texto + folgas) de uma linha."""
    bh, px, *_ = geometria(tam)
    if EH is not None and any(EH._e_emoji(ch) for ch in txt):
        f1 = _fonte(tam); dd = ImageDraw.Draw(Image.new("L", (1, 1))); lado, esp = round(f1.size * 1.12), round(f1.size * 0.06)
        return sum(dd.textlength(t, font=f1) if not e else lado + 2 * esp for t, e in EH._pedacos(txt)) + 2 * px
    return ImageDraw.Draw(Image.new("L", (1, 1))).textlength(txt, font=_fonte(tam * SS)) / SS + 2 * px

def caber(linhas, tam, maxw):
    """Re-quebra pela largura quando alguma pílula passaria da largura do 4:5 (tela 1:1, 16:9 ou frase longa)."""
    if all(_largura(t, tam) <= maxw for t in linhas): return linhas
    out, cur = [], ""
    for w in " ".join(linhas).split():
        if cur and _largura(cur + " " + w, tam) > maxw: out.append(cur); cur = w
        else: cur = (cur + " " + w).strip()
    return out + [cur]

def _linhas(img, linhas, cy, tam, topo=False, area=None):
    """Desenha linhas [(texto, cor_caixa, cor_texto[, (ini, fim, cor)])] centralizadas, cada uma na sua pílula.
    cy = centro do bloco (ou topo do bloco se topo=True). area = (x0, y0, x1, y1): o bloco é empurrado para dentro dela
    (padrão: o 4:5 da tela). Devolve o y de baixo do bloco."""
    larg = img.width; bh, px, r, base, vao = geometria(tam)
    f4 = _fonte(tam * SS); d4 = ImageDraw.Draw(Image.new("L", (1, 1)))
    total = len(linhas) * bh + (len(linhas) - 1) * round(vao)
    y = round(cy if topo else cy - total / 2)
    ax0, ay0, ax1, ay1 = area or area_45(img.size); m = tam * MARGEM
    y2 = min(max(y, ay0 + m), ay1 - m - total)           # nunca fora do 4:5
    if round(y2) != y and ("y", y) not in _avisado:
        _avisado.add(("y", y))
        print(f"   aviso pilula: bloco em y {y}-{y + total} px sairia da área segura ({ay0:.0f}-{ay1:.0f}); foi para "
              f"{round(y2)}-{round(y2) + total} (regra do Fefo, 13/11/2026: EV dentro do 4:5, TS dentro do 1:1)", file=sys.stderr)
    y = round(y2)
    for txt, cx, ct, *hl in linhas:
        emo = EH is not None and any(EH._e_emoji(ch) for ch in txt)
        if emo:
            f1 = _fonte(tam); dd = ImageDraw.Draw(img); lado, esp = round(f1.size * 1.12), round(f1.size * 0.06)
            w = sum(dd.textlength(t, font=f1) if not e else lado + 2 * esp for t, e in EH._pedacos(txt))
        else: w = d4.textlength(txt, font=f4) / SS
        lw = w + 2 * px; x0 = round((larg - lw) / 2)
        lay = Image.new("RGBA", (round(lw * SS) + SS, bh * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        d.rounded_rectangle([0, 0, round(lw * SS), bh * SS - 1], radius=round(r * SS), fill=cx + (255,))
        if hl and hl[0]:                                 # marca-texto da palavra-chave: (início, fim, cor) na linha
            a, b, cor = hl[0]; xa = px * SS + d.textlength(txt[:a], font=f4); xb = xa + d.textlength(txt[a:b], font=f4)
            d.rounded_rectangle([xa - tam * 0.12 * SS, bh * 0.14 * SS, xb + tam * 0.12 * SS, bh * 0.86 * SS],
                                radius=round(bh * 0.36 * SS), fill=cor + (255,))
        if not emo: d.text((lw * SS / 2, (bh / 2 + base) * SS), txt, font=f4, fill=ct + (255,), anchor="ms")
        img.alpha_composite(lay.resize((lay.width // SS, bh), Image.LANCZOS), (x0, y))
        if emo: EH._texto_emoji(img, txt, larg / 2, y + bh / 2, f1, ct)
        y += bh + round(vao)
    return y - round(vao)

def _y_px(y, alt): return y if y > 1 else alt * y

def quadro(legenda, header=None, cfg_leg=None, cfg_hd=None, tela=(W, H)):
    """Imagem RGBA do tamanho da tela com o header (topo) e a legenda (pílula) já desenhados."""
    cfg_leg, cfg_hd = cfg_leg or {}, cfg_hd or {}; k = escala(tela)
    img = Image.new("RGBA", tuple(tela), (0, 0, 0, 0))
    ar = area_central(tela, cfg_leg.get("area", "4:5"))      # TS: estilo.legenda.area = "1:1"
    if header:
        tam = cfg_hd.get("tamanho", 52) * k; dest = _rgb(cfg_hd.get("cor_destaque", "#5A2A20")); mw = ar[2] - ar[0] - 2 * tam * MARGEM
        princ, _, par = header.partition("(")
        ls = [(t, (255, 255, 255), (0, 0, 0)) for t in caber(quebrar(princ.strip(), cfg_hd.get("quebra", 22)), tam, mw)]
        if par: ls.append(("(" + par.strip(), dest, (255, 255, 255)))
        _linhas(img, ls, cfg_hd.get("y", 190) * k, tam, topo=True, area=ar)
    if legenda:
        _avisar_fixos(cfg_leg)
        cx, ct = _rgb(PADRAO["cor_caixa"]), _rgb(PADRAO["cor_texto"]); tam = PADRAO["tamanho"] * k
        lin = caber(quebrar(legenda, cfg_leg.get("quebra", PADRAO["quebra"])), tam, ar[2] - ar[0] - 2 * tam * MARGEM)
        ls = [(t, cx, ct) for t in lin]
        de = cfg_leg.get("destaque")
        if isinstance(de, dict) and de.get("palavras"):
            low = legenda.lower(); ach = [(low.find(p.lower()), p) for p in de["palavras"] if p.lower() in low]
            if ach:
                i0, p = max(ach, key=lambda x: len(x[1])); i1 = i0 + len(p); cor = _rgb(de.get("cor", "#FFD400")); o = 0
                for n, t in enumerate(lin):
                    a, b = max(i0 - o, 0), min(i1 - o, len(t))
                    if a < b: ls[n] = (t, cx, ct, (a, b, cor))
                    o += len(t) + 1
        _linhas(img, ls, _y_px(cfg_leg.get("y", PADRAO["y"]), tela[1]), tam, area=ar)
    return img

def gerar(eventos, header, HD, total, pasta, plano, alturas=(), tela=(W, H), fps=FPS):
    """eventos = [(ini, fim, texto)] ou [(ini, fim, texto, y)] da legenda; header só em [0, HD). alturas = [(ini, fim, y)]:
    trechos em que a legenda muda de altura (cenas com "legenda_y", y_trechos). y: fração da altura ou px.
    Devolve a lista do concat demuxer (PNGs com a duração de cada trecho)."""
    e = (plano or {}).get("estilo", {}); cl, ch = e.get("legenda", {}), e.get("header_pilula", {})
    os.makedirs(pasta, exist_ok=True)
    fr = lambda t: int(round(t * fps))
    evs = [(ev[0], ev[1], ev[2], ev[3] if len(ev) > 3 else None) for ev in eventos]
    marcas = sorted({0, fr(total)} | ({fr(HD)} if header else set()) | {fr(a) for a, *_ in evs} | {fr(b) for _, b, *_ in evs})
    marcas = [m for m in marcas if 0 <= m <= fr(total)]
    feitos, ls = {}, []
    for a, b in zip(marcas, marcas[1:]):
        if b <= a: continue
        t = (a + b) / 2 / fps
        ev = next((x for x in evs if fr(x[0]) <= a and b <= fr(x[1])), None)
        leg = ev[2] if ev else None
        hd = header if header and t < HD else None
        ini = ev[0] if ev else t
        y = ev[3] if ev and ev[3] is not None else next((yy for s, f, yy in alturas if s - 0.05 <= ini < f), cl.get("y", PADRAO["y"]))
        k = hashlib.md5(f"{leg}|{hd}|{y}|{tela}".encode()).hexdigest()[:10]
        if k not in feitos:
            p = os.path.abspath(f"{pasta}/q_{k}.png"); quadro(leg, hd, dict(cl, y=y), ch, tela).save(p); feitos[k] = p
        ls.append((feitos[k], (b - a) / fps))
    if not ls:                                          # sem legenda nem header: um quadro vazio
        p = os.path.abspath(f"{pasta}/q_vazio.png"); Image.new("RGBA", tuple(tela), (0, 0, 0, 0)).save(p)
        ls = [(p, max(total, 1 / fps))]
    lista = f"{pasta}/pilula.txt"
    with open(lista, "w", encoding="utf-8") as o:
        for p, d in ls: o.write(f"file '{p.replace(os.sep, '/')}'\nduration {d:.6f}\n")
        o.write(f"file '{ls[-1][0].replace(os.sep, '/')}'\n")
    return lista

def agrupar(palavras, quebra=PADRAO["quebra"] * 2, pausa=0.45, fim=None):
    """[(palavra, ini, fim)] -> [(ini, fim, frase)]: junta palavras em blocos de até `quebra` caracteres (até 2 linhas),
    cortando em pontuação final, em pausa maior que `pausa` s ou quando o bloco enche. O bloco fica até a próxima fala
    (se ela vier em menos de 0,5 s) ou 0,2 s depois da última palavra."""
    blocos, cur = [], []
    for i, (w, s, e) in enumerate(palavras):
        if fim is not None and s >= fim: break
        if cur and (len(" ".join(x[0] for x in cur + [(w, s, e)])) > quebra or s - cur[-1][2] > pausa):
            blocos.append(cur); cur = []
        cur.append((w, s, e))
        if re.search(r"[.!?…]$", w): blocos.append(cur); cur = []
    if cur: blocos.append(cur)
    out = []
    for i, bl in enumerate(blocos):
        s, e = bl[0][1], bl[-1][2]; nx = blocos[i + 1][0][1] if i + 1 < len(blocos) else e + 0.3
        z = nx if nx - e < 0.5 else e + 0.2
        if fim is not None: z = min(z, fim)
        if z - s >= 0.06: out.append((s, z, " ".join(x[0] for x in bl)))
    return out

_TAG = re.compile(r"\{[^}]*\}")
def ler_ass(caminho, estilos=("Leg",)):
    """Eventos [(ini, fim, texto, y_px | None)] das linhas Dialogue dos `estilos` de um .ass (tags tiradas; y do \\pos)."""
    def t(x): h, m, s = x.split(":"); return int(h) * 3600 + int(m) * 60 + float(s)
    out = []
    for ln in open(caminho, encoding="utf-8-sig"):
        if not ln.startswith("Dialogue:"): continue
        c = ln.rstrip("\n").split(",", 9)
        if len(c) < 10 or c[3].strip() not in estilos: continue
        pos = re.search(r"\\pos\(\s*[-\d.]+\s*,\s*([-\d.]+)\s*\)", c[9])
        txt = _TAG.sub("", c[9]).replace("\\N", " ").replace("\\n", " ").replace("\\h", " ").strip()
        if txt: out.append((t(c[1]), t(c[2]), " ".join(txt.split()), float(pos[1]) if pos else None))
    return out

if __name__ == "__main__":
    # prova: py pilula.py "texto da legenda" saida.png [fundo.png]
    txt, out = sys.argv[1], sys.argv[2]
    q = quadro(txt)
    if len(sys.argv) > 3: q = Image.alpha_composite(Image.open(sys.argv[3]).convert("RGBA").resize(q.size), q)
    q.save(out); print("ok", out)
