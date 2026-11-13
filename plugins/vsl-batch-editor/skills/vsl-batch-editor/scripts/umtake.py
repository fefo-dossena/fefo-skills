"""Modo ONE TAKE (plano.json -> "one_take": true). Ref: BATCH#2827 (KittySpout Halloween).

O AD inteiro é UMA fala contínua por marca (fala tipo "take", ex. T1_neurobella.mp4), sem b-roll e sem cortes no meio:
  corte    = só o silêncio do início e do fim
  legenda  = transcrição do take -> AD<n>_<p>.srt (grafia do roteiro)
  montagem = take em tela cheia + título fixo no topo (PNG) + legenda em pílula (PNG por bloco) + loudnorm (+ trilha)
Estilo em plano.json -> estilo.titulo; legenda SEMPRE pílula TikTok Sans Medium (_FLUXO/scripts/pilula.py, regra do Fefo
13/11/2026; era "caixa_laranja"), estilo.legenda.y muda só a altura.
"""
import glob, json, os, shutil, subprocess

FN = "/System/Library/Fonts/HelveticaNeue.ttc"; FN_BOLD = 1
FL = "/System/Library/Fonts/Avenir Next.ttc"; FL_DEMI = 2
EMOJI = "/System/Library/Fonts/Apple Color Emoji.ttc"
W, H = 1080, 1920

def takes(plano): return [f for f in plano["falas"] if f["tipo"] == "take"]

def itens(F, B, plano):
    P = plano["produtos"]; PL = f"{B}/08_auto/plano.json"; out = []
    for f in takes(plano):
        n = int(f.get("hook", 1))
        for p in (P if f.get("marca") else [None]):
            st = F.fala_stem(f, p); mp4 = F.fala_mp4(B, f, p); m = f"{B}/08_auto/cortes/{st}.manual.json"
            out.append(("falas", mp4, [], None, st))
            out.append(("cortes", F.corte(B, st), [mp4] + ([m] if os.path.exists(m) else []), ("corte_take", mp4, st), st))
            for pp in ([p] if p else P):
                pal = F.L(B, f"palavras_{st}.json"); srt = F.L(B, f"AD{n}_{pp}.srt")
                out.append(("legendas", pal, [F.corte(B, st)], ("transcrever_take", mp4, st), f"palavras {st}"))
                out.append(("legendas", srt, [pal, PL], ("srt_take", st, pp, n), f"legenda AD{n} {pp}"))
                dep = [mp4, F.corte(B, st), srt, PL, f"{B}/batch.json"] + trilhas(B)
                out.append(("ads", F.export(B, plano, pp, n), dep, ("montar_take", pp, n), f"AD{n}_{pp}"))
    dx = [F.corte(B, F.fala_stem(f, p)) for f in takes(plano) for p in (P if f.get("marca") else [None])]
    out.append(("xml", F.xmlpath(B, plano), dx + [PL], ("xml",), "XML Premiere"))
    return out

def trilhas(B): return sorted(glob.glob(f"{B}/02_audio/trilha/*.mp3") + glob.glob(f"{B}/02_audio/trilha/*.wav"))

def take_de(plano, p, n):
    return next(f for f in takes(plano) if int(f.get("hook", 1)) == int(n))

def executar(F, B, acao):
    plano, cfg = F.carregar(B); k = acao[0]
    if k == "corte_take":
        _, mp4, st = acao; man = f"{B}/08_auto/cortes/{st}.manual.json"
        if os.path.exists(man): shutil.copy(man, F.corte(B, st)); print(f"   (corte manual mantido: {st})"); return
        import vsl
        c = vsl.load_cfg(f"{B}/batch.json"); segs = vsl.keep_segments(vsl.envelope(mp4), c["limiar_db"], c["silencio_min_s"],
                                                                       c["folga_antes_s"], c["folga_depois_s"])
        dur = F.duracao(mp4); a = max(0, segs[0][0] - 0.1) if segs else 0; b = min(dur, segs[-1][1] + 0.25) if segs else dur
        json.dump([[round(a, 3), round(b, 3)]], open(F.corte(B, st), "w"))
    elif k == "transcrever_take":
        _, mp4, st = acao; (a, b), = json.load(open(F.corte(B, st))); wav = F.L(B, f"_{st}.wav")
        subprocess.run([F.FF, "-nostdin", "-v", "error", "-y", "-ss", str(a), "-to", str(b), "-i", mp4, "-vn", "-ac", "1",
                        "-ar", "16000", wav], check=True)
        F.transcrever(wav, F.L(B, f"palavras_{st}.json")); os.remove(wav)
    elif k == "srt_take":
        _, st, p, n = acao; f = take_de(plano, p, n); est = plano.get("estilo", {}).get("legenda", {})
        c2 = dict(cfg); c2["legenda"] = dict(cfg.get("legenda", {}), max_caracteres=est.get("max_caracteres", 34))
        txt = f.get("texto_por_marca", {}).get(p, f["texto"])   # oferta diferente por marca (ex. 2827: VisioVance 71%)
        F.srt(F.L(B, f"palavras_{st}.json"), txt.replace("{MARCA}", F.marca_nome(plano, p)),
              F.L(B, f"AD{n}_{p}.srt"), c2)
    elif k == "montar_take": montar(F, B, acao[1], acao[2])

# ---------------------------------------------------------------- PNGs (título e legendas)
def _font(path, size, idx=0):
    from PIL import ImageFont; return ImageFont.truetype(path, size, index=idx)

def _emoji_row(txt, alto):
    """Emojis coloridos (Apple Color Emoji só renderiza em 160 px) -> uma imagem RGBA com altura `alto`."""
    from PIL import Image, ImageDraw, ImageFont, features
    fe = _font(EMOJI, 160); peças = []
    for e in _emoji_split(txt):
        im = Image.new("RGBA", (480, 320), (0, 0, 0, 0)); ImageDraw.Draw(im).text((40, 40), e, font=fe, embedded_color=True, layout_engine=ImageFont.Layout.RAQM if features.check("raqm") else ImageFont.Layout.BASIC)
        bb = im.getbbox()
        if bb: peças.append(im.crop(bb))
    if not peças: return None
    sc = alto / max(p.height for p in peças); peças = [p.resize((max(1, int(p.width * sc)), max(1, int(p.height * sc)))) for p in peças]
    gap = int(alto * 0.08); row = Image.new("RGBA", (sum(p.width for p in peças) + gap * (len(peças) - 1), alto), (0, 0, 0, 0)); x = 0
    for p in peças: row.alpha_composite(p, (x, (alto - p.height) // 2)); x += p.width + gap
    return row

def _emoji_split(txt):
    out = []
    for ch in txt:
        if out and (ch in "‍️" or out[-1].endswith("‍")): out[-1] += ch
        else: out.append(ch)
    return out

def titulo_png(plano, p, out):
    from PIL import Image, ImageDraw
    t = plano["estilo"]["titulo"]; marca = F_marca(plano, p)
    l1 = t.get("linha1", "{MARCA_UP}").replace("{MARCA_UP}", marca.upper()).replace("{MARCA}", marca); l2 = t.get("linha2", "")
    im = Image.new("RGBA", (W, 420), (0, 0, 0, 0)); d = ImageDraw.Draw(im); y = 0
    for txt, tam, sw in ((l1, 128, 7), (l2, 64, 5)):
        if not txt: continue
        f = _font(FN, tam, FN_BOLD)
        while d.textlength(txt, font=f) > W - 80: tam -= 4; f = _font(FN, tam, FN_BOLD)
        bb = d.textbbox((0, 0), txt, font=f, stroke_width=sw)
        d.text(((W - (bb[2] - bb[0])) // 2 - bb[0], y - bb[1]), txt, font=f, fill="black", stroke_width=sw, stroke_fill="white")
        y += bb[3] - bb[1] + 6
    row = _emoji_row(t.get("emojis", ""), 62)
    if row: im.alpha_composite(row, ((W - row.width) // 2, y + 4)); y += 70
    im.crop((0, 0, W, y + 10)).save(out)

def F_marca(plano, p): return plano.get("marca_nome", {}).get(p, p.capitalize())

def legenda_png(txt, out, y=None):
    """Legenda SEMPRE pílula TikTok Sans Medium (regra do Fefo, 13/11/2026; era a caixa laranja do ref): PNG do tamanho
    da tela, sobreposto em 0:0. y = centro do bloco (fração da altura ou px); sem y, a altura do PSD de referência."""
    import pilula
    pilula.quadro(txt, cfg_leg={} if y is None else {"y": y}, tela=(W, H)).save(out)

# ---------------------------------------------------------------- montagem
def montar(F, B, p, n):
    plano, cfg = F.carregar(B); n = int(n); f = take_de(plano, p, n)
    st = F.fala_stem(f, p if f.get("marca") else None); mp4 = F.fala_mp4(B, f, p if f.get("marca") else None)
    (a, b), = json.load(open(F.corte(B, st)))
    tmp = F.tmp_montar(B, f"_tmp_take_{p}"); os.makedirs(tmp, exist_ok=True)
    titulo_png(plano, p, f"{tmp}/titulo.png")
    blocos = F.ler_srt(F.L(B, f"AD{n}_{p}.srt"))
    ins = ["-ss", str(a), "-to", str(b), "-i", mp4, "-loop", "1", "-i", f"{tmp}/titulo.png"]
    g = [f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30,setsar=1[v0]",
         "[1:v]format=rgba[tt]", "[v0][tt]overlay=0:150:shortest=1[c0]"]
    cur = "c0"; yleg = plano.get("estilo", {}).get("legenda", {}).get("y")     # centro da pílula; sem campo, o do PSD
    for k, (s, e, txt) in enumerate(blocos):
        png = f"{tmp}/leg{k:02d}.png"; legenda_png(txt, png, yleg); ins += ["-i", png]; j = k + 2
        g.append(f"[{cur}][{j}:v]overlay=0:0:enable='between(t,{s:.3f},{e:.3f})'[c{k+1}]"); cur = f"c{k+1}"
    g.append(f"[{cur}]format=yuv420p[vout]")
    lufs = cfg.get("audio", {}).get("loudness_lufs", -20); tr = trilhas(B)
    if tr:
        vol = cfg.get("audio", {}).get("trilha_volume_db", -22); ins += ["-stream_loop", "-1", "-i", tr[0]]; jt = len(blocos) + 2
        g.append(f"[{jt}:a]volume={vol}dB,aresample=44100,aformat=channel_layouts=stereo[tr];[0:a]aresample=44100,aformat=channel_layouts=stereo[vz];"
                 f"[vz][tr]amix=inputs=2:duration=first:normalize=0[mx];[mx]loudnorm=I={lufs}:TP=-1.5:LRA=11,aresample=48000[aout]")
    else:
        g.append(f"[0:a]loudnorm=I={lufs}:TP=-1.5:LRA=11,aresample=48000[aout]")
    g.append(F.SAIDA_720)
    sc = f"{tmp}/fc.txt"; open(sc, "w").write(";".join(g))
    out = F.export(B, plano, p, n); os.makedirs(os.path.dirname(out), exist_ok=True)
    subprocess.run([F.FF, "-nostdin", "-v", "error", "-y", *ins, "-filter_complex_script", sc, "-map", "[v720]", "-map", "[aout]",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                    "-t", f"{b - a:.3f}", out], check=True)
    shutil.copy(f"{tmp}/titulo.png", f"{B}/06_elementos/titulo_{p}.png")
    shutil.rmtree(tmp, ignore_errors=True); F.tira_export_antigo(B, plano, p, n)
    print(f"   ok {os.path.basename(out)} (one take {b - a:.2f}s, {len(blocos)} legendas{', com trilha' if tr else ''})")

# ---------------------------------------------------------------- XML: uma sequência por marca, take em V1
def gerar_xml(F, B):
    import urllib.parse
    from xml.sax.saxutils import escape
    plano, _ = F.carregar(B); FPS = 30; fr = lambda t: int(round(t * FPS)); seqs = []
    rate = f"<rate><timebase>{FPS}</timebase><ntsc>FALSE</ntsc></rate>"
    for p in plano["produtos"]:
        for f in takes(plano):
            n = int(f.get("hook", 1)); pp = p if f.get("marca") else None; mp4 = F.fala_mp4(B, f, pp)
            if not os.path.exists(mp4): continue
            (a, b), = json.load(open(F.corte(B, F.fala_stem(f, pp)))); d = F.duracao(mp4); dd = fr(b) - fr(a)
            fil = (f'<file id="file-{p}{n}"><name>{escape(os.path.basename(mp4))}</name><pathurl>file://{urllib.parse.quote(mp4)}</pathurl>'
                   f'{rate}<duration>{fr(d)}</duration><media><video/><audio><channelcount>2</channelcount></audio></media></file>')
            com = (f'<name>{escape(os.path.basename(mp4))}</name><enabled>TRUE</enabled><duration>{fr(d)}</duration>{rate}'
                   f'<start>0</start><end>{dd}</end><in>{fr(a)}</in><out>{fr(a) + dd}</out>')
            seqs.append(f'<sequence id="AD{n}-{p}"><name>AD{n}_{p}</name><duration>{dd}</duration>{rate}<media><video><format>'
                        f'<samplecharacteristics>{rate}<width>{W}</width><height>{H}</height><pixelaspectratio>square</pixelaspectratio>'
                        f'</samplecharacteristics></format><track><clipitem id="v{p}{n}">{com}{fil}</clipitem></track></video>'
                        f'<audio><track><clipitem id="a{p}{n}">{com}<file id="file-{p}{n}"/></clipitem></track></audio></media></sequence>')
    out = F.xmlpath(B, plano)
    open(out, "w").write('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n<xmeml version="4"><project><name>'
                         f'BATCH{F.num(plano)}</name><children>{"".join(seqs)}</children></project></xmeml>')
    print(f"   ok {os.path.basename(out)} ({len(seqs)} sequências)")
