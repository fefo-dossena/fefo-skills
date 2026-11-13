"""Layout "cartao" (ref Dr. Kegel, BATCH_2078): avatar colorido em quadro 4:5 com faixas pretas no 9:16,
b-roll em cartão grande centralizado ou inset quadrado com borda, legenda uma palavra por vez com brilho,
banner de caixas brancas no hook e tela final de CTA. Tudo lido de plano.json -> estilo.

Chamado pelo fluxo.py (montar / xml) quando estilo.broll.layout == "cartao".
"""
import json, os, re, shutil, subprocess

W, H = 1080, 1920
FONTES = "/System/Library/Fonts"
HN = f"{FONTES}/HelveticaNeue.ttc"          # 10 = Medium, 1 = Bold

PADRAO = {
    "avatar": {"quadro": [0, 285, 1080, 1350], "crop_y": 0.25, "punch_in": [1.0, 1.12], "vinheta": True},
    "broll": {"cartao": [43, 460, 994, 1000], "cartao_borda": 3, "inset": [551, 609, 454, 454], "inset_borda": 8},
    "legenda": {"y": 1335, "caixa_alta": False},     # pílula padrão (_FLUXO/scripts/pilula.py); y = centro em px
    "hook_banner": {"texto": "", "y": 1065, "tamanho": 44, "largura_max": 900},
    "cta": {"cena": None, "titulo": "", "rodape": ""},
}

def cfg_estilo(plano):
    e = plano.get("estilo", {}); out = {}
    for k, v in PADRAO.items():
        d = dict(v); d.update(e.get(k, {}) if isinstance(e.get(k), dict) else {}); out[k] = d
    return out

# ---------------------------------------------------------------- imagens (banner, CTA)
def _fonte(tam, bold=False):
    from PIL import ImageFont
    return ImageFont.truetype(HN, tam, index=1 if bold else 10)

def banner_png(texto, out, tam=44, largura_max=900):
    """Caixas brancas arredondadas por linha, texto preto; **palavra** = negrito (igual ao ref)."""
    from PIL import Image, ImageDraw
    runs = []                                     # "|" força quebra de linha
    for i, parte in enumerate(re.split(r"\*\*", texto)):
        for w in parte.replace("|", " | ").split(): runs.append((w, i % 2 == 1))
    fR, fB = _fonte(tam), _fonte(tam, True); esp = fR.getlength(" ")
    larg = lambda r: (fB if r[1] else fR).getlength(r[0])
    linhas, cur = [], []
    for r in runs:
        if r[0] == "|": linhas.append(cur); cur = []; continue
        if cur and sum(larg(x) for x in cur + [r]) + esp * len(cur) > largura_max: linhas.append(cur); cur = []
        cur.append(r)
    if cur: linhas.append(cur)
    ph, pv, lh = 18, 9, int(tam * 1.32)
    img = Image.new("RGBA", (W, lh * len(linhas) + 2 * pv + 4), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    for i, ln in enumerate(linhas):
        lw = sum(larg(x) for x in ln) + esp * (len(ln) - 1); x0 = (W - lw) / 2; y0 = i * lh + pv
        d.rounded_rectangle([x0 - ph, y0 - pv + 2, x0 + lw + ph, y0 + lh + pv - 2], radius=14, fill=(255, 255, 255, 255))
    for i, ln in enumerate(linhas):
        lw = sum(larg(x) for x in ln) + esp * (len(ln) - 1); x = (W - lw) / 2; y0 = i * lh + pv + (lh - tam) / 2 - 2
        for w, b in ln:
            d.text((x, y0), w, font=fB if b else fR, fill=(0, 0, 0, 255)); x += larg((w, b)) + esp
    img.save(out); return img.size

def cta_png(titulo, rodape, out, topo=1207):
    """Fundo da tela final: branco em cima (o vídeo do frasco entra por cima), faixa escura embaixo, seta vermelha."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (W, H), (255, 255, 255)); d = ImageDraw.Draw(img)
    d.rectangle([0, topo, W, H], fill=(24, 24, 27))
    f1, f2 = _fonte(58), _fonte(34, True)
    if titulo:
        tw = f1.getlength(titulo); d.text(((W - tw) / 2, topo - 150), titulo, font=f1, fill=(30, 30, 30))
    if rodape:
        t = rodape.upper(); tw = f2.getlength(t); d.text(((W - tw) / 2, topo + 120), t, font=f2, fill=(235, 235, 235))
    cx, cy = W / 2, topo + 330
    d.line([(cx - 26, cy - 13), (cx, cy + 13), (cx + 26, cy - 13)], fill=(225, 29, 72), width=9, joint="curve")
    img.save(out)

def cta_packshot_pngs(titulo, marca, rodape, foto, pre, topo=1290):
    """CTA limpo como o da ref (revisão Frame.io 2078: "this looks horrible"): fundo branco, título com a marca em
    negrito, faixa escura com selo de garantia; frasco = foto real (refs) recortada e seta separados para animar.
    Devolve (fundo, frasco, seta, (x, y, w, h) do frasco)."""
    from PIL import Image, ImageDraw, ImageChops, ImageFilter
    img = Image.new("RGB", (W, H), (255, 255, 255)); d = ImageDraw.Draw(img)
    d.rectangle([0, topo, W, H], fill=(24, 24, 27))
    # título: "Get your bottle of" + **Marca**
    fR, fB = _fonte(62), _fonte(62, True)
    a, b = (titulo.split(marca, 1) + [""])[:2] if marca in titulo else (titulo, "")
    partes = [(a, fR), (marca if marca in titulo else "", fB), (b, fR)]
    tw = sum(f.getlength(t) for t, f in partes); x = (W - tw) / 2; ty = topo - 170
    for t, f in partes:
        d.text((x, ty), t, font=f, fill=(24, 24, 27)); x += f.getlength(t)
    # selo de garantia: escudo com check + texto
    if rodape:
        f2 = _fonte(36, True); t = rodape.upper(); lw = f2.getlength(t); ic = 44; gap = 18
        x0 = (W - (ic + gap + lw)) / 2; cy = topo + 150
        sx, sy = x0, cy - ic / 2
        d.polygon([(sx, sy + 4), (sx + ic / 2, sy - 2), (sx + ic, sy + 4), (sx + ic, sy + ic * 0.5),
                   (sx + ic / 2, sy + ic + 4), (sx, sy + ic * 0.5)], fill=(225, 29, 72))
        d.line([(sx + 11, cy + 1), (sx + 19, cy + 10), (sx + 34, cy - 9)], fill=(255, 255, 255), width=6, joint="curve")
        d.text((x0 + ic + gap, cy - 23), t, font=f2, fill=(240, 240, 240))
    fundo = f"{pre}_fundo.png"; img.save(fundo)
    # frasco: recorta o branco em volta da foto e põe sombra suave embaixo
    fr = Image.open(foto).convert("RGB")
    bbox = ImageChops.difference(fr, Image.new("RGB", fr.size, (255, 255, 255))).point(lambda v: 255 if v > 12 else 0).getbbox()
    fr = fr.crop(bbox); alt = topo - 330 - 120; s = alt / fr.height
    if fr.width * s > 820: s = 820 / fr.width
    fr = fr.resize((int(fr.width * s), int(fr.height * s)), Image.LANCZOS)
    m = ImageChops.difference(fr, Image.new("RGB", fr.size, (255, 255, 255))).convert("L").point(lambda v: 255 if v > 6 else 0)
    m = m.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1.2))
    pad = 60; tela = Image.new("RGBA", (fr.width + 2 * pad, fr.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("L", tela.size, 0); ImageDraw.Draw(sh).ellipse([pad + fr.width * 0.12, pad + fr.height - 28, pad + fr.width * 0.88, pad + fr.height + 22], fill=70)
    tela.paste(Image.new("RGBA", tela.size, (0, 0, 0, 255)), (0, 0), sh.filter(ImageFilter.GaussianBlur(16)))
    fr = fr.convert("RGBA"); fr.putalpha(m); tela.alpha_composite(fr, (pad, pad))
    frasco = f"{pre}_frasco.png"; tela.save(frasco)
    caixa = (int((W - tela.width) / 2), int(110 + (alt - fr.height) / 2) - pad + 10, tela.width, tela.height)
    # seta vermelha (anima pulando)
    st = Image.new("RGBA", (120, 80), (0, 0, 0, 0))
    ImageDraw.Draw(st).line([(28, 22), (60, 54), (92, 22)], fill=(225, 29, 72), width=11, joint="curve")
    seta = f"{pre}_seta.png"; st.save(seta)
    return fundo, frasco, seta, caixa

# ---------------------------------------------------------------- legenda palavra por vez
def ass_palavras(palavras, out, est, fim=None):
    """palavras = [(texto, s, e)] já na linha do tempo do AD."""
    L = est["legenda"]; y, tam = L["y"], L.get("tamanho", 74)      # .ass só para o QC: o vídeo usa a pílula
    cab = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\n\n[V4+ Styles]\n"
           "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
           f"Style: G,Helvetica Neue Medium,{tam},&H00FFFFFF,&H00FFFFFF,&H00FFFFFF,&H00000000,0,0,0,0,100,100,0,0,1,5,0,5,0,0,0,1\n"
           f"Style: P,Helvetica Neue Medium,{tam},&H00FFFFFF,&H00FFFFFF,&H70000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,5,0,0,0,1\n\n"
           "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    t = lambda s: "%d:%02d:%02d.%02d" % (s // 3600, s % 3600 // 60, int(s % 60), int(round((s % 1) * 100)) % 100)
    ev = []
    for i, (w, s, e) in enumerate(palavras):
        if fim is not None and s >= fim: break
        nx = palavras[i + 1][1] if i + 1 < len(palavras) else e + 0.3
        z = nx if nx - e < 0.5 else e + 0.2
        if fim is not None: z = min(z, fim)
        if z - s < 0.06: continue
        txt = w.upper() if L.get("caixa_alta", True) else w
        txt = txt.replace("{", "(").replace("}", ")")
        ev.append(f"Dialogue: 0,{t(s)},{t(z)},G,,0,0,0,,{{\\pos(540,{y})\\blur9\\3a&HB4&}}{txt}")
        ev.append(f"Dialogue: 1,{t(s)},{t(z)},P,,0,0,0,,{{\\pos(540,{y})\\blur1.5}}{txt}")
    open(out, "w").write(cab + "\n".join(ev) + "\n")

# ---------------------------------------------------------------- montagem
def montar(F, B, p, n):
    plano, cfg = F.carregar(B); n = int(n); f = F.fala_hook(plano, n); est = cfg_estilo(plano)
    tmp = f"{B}/08_auto/_tmp_montar"; os.makedirs(tmp, exist_ok=True)
    ele = f"{B}/08_auto/elementos"; os.makedirs(ele, exist_ok=True)
    # hook cortado
    segs = json.load(open(F.corte(B, F.fala_stem(f)))); hook = f"{tmp}/hook{n}.mp4"
    fc = ";".join(f"[0:v]trim={s}:{e},setpts=PTS-STARTPTS,scale=720:1280,fps=30,setsar=1[v{i}];[0:a]atrim={s}:{e},asetpts=PTS-STARTPTS,aresample=44100,aformat=channel_layouts=stereo[a{i}]" for i, (s, e) in enumerate(segs))
    fc += ";" + "".join(f"[v{i}][a{i}]" for i in range(len(segs))) + f"concat=n={len(segs)}:v=1:a=1[v][a]"
    subprocess.run([F.FF, "-nostdin", "-v", "error", "-y", "-i", F.fala_mp4(B, f), "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-crf", "16", "-c:a", "aac", "-b:a", "192k", hook], check=True)
    plan, HD = F.segmentos(B, p, n)
    json.dump(plan, open(f"{B}/08_auto/broll_posicoes_AD{n}_{p}.json", "w"), indent=1)
    total = HD + F.duracao(F.previa(B, p))
    cenas = {c["id"]: c for c in plano["cenas"]}
    cta = next(((cid, a) for cid, a, b, fl in plan if cenas[cid].get("formato") == "cta_final"), None)
    fim_leg = cta[1] if cta else None

    # limites de cada clipe de fala (punch-in alternado, como o ref muda o enquadramento a cada corte)
    lim, t0 = [(0.0, HD)], HD
    for fl in F.falas_hold(plano):
        d = F.dur_corte(F.corte(B, F.fala_stem(fl, p))); lim.append((t0, t0 + d)); t0 += d
    lim[-1] = (lim[-1][0], total + 1)
    A = est["avatar"]; qx, qy, qw, qh = A["quadro"]; zs = A["punch_in"]
    ins = ["-i", hook, "-i", F.previa(B, p)]
    g = ["[0:v]scale=720:1280,fps=30,setsar=1[hv];[1:v]scale=720:1280,fps=30,setsar=1[pv];[hv][0:a][pv][1:a]concat=n=2:v=1:a=1[av][aa]",
         f"[av]split={len(lim)}" + "".join(f"[s{i}]" for i in range(len(lim)))]
    ar = qw / qh
    for i, (a, b) in enumerate(lim):
        z = zs[i % len(zs)]; cw = 720 / z; ch = cw / ar
        cy0 = (1280 - 720 / ar) * A["crop_y"]; cy = cy0 + (720 / ar - ch) * 0.3; cx = (720 - cw) / 2
        g.append(f"[s{i}]trim={a:.4f}:{b:.4f},setpts=PTS-STARTPTS,crop={cw:.1f}:{ch:.1f}:{cx:.1f}:{cy:.1f},scale={qw}:{qh},setsar=1[c{i}]")
    g.append("".join(f"[c{i}]" for i in range(len(lim))) + f"concat=n={len(lim)}:v=1:a=0[cc]")
    vin = ",vignette=angle=PI/4.5" if A.get("vinheta") else ""
    g.append(f"[cc]eq=saturation=0.95{vin},pad={W}:{H}:{qx}:{qy}:black[b0]")
    cur = "b0"; Bz = est["broll"]
    for k, (cid, a, b, fl) in enumerate(plan):
        c = cenas[cid]; fmt = c.get("formato", "tela_cheia"); j = ins.count("-i")
        if fmt == "cta_final" and est["cta"].get("poster"):
            # pôster ilustrado em tela cheia (estilo do vídeo, texto já na arte): fade + push-in lento 1,000→1,025
            poster = f"{B}/{est['cta']['poster'].replace('{p}', p)}"; d = total - a + 0.1
            ins += ["-loop", "1", "-t", f"{total:.3f}", "-i", poster]
            z = f"(1+0.025*t/{d:.3f})"   # título vai quase de borda a borda
            g.append(f"[{j}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30,trim=0:{d:.3f},setpts=PTS-STARTPTS,"
                     f"scale=w='trunc({W}*{z}/2)*2':h='trunc({H}*{z}/2)*2':eval=frame,crop={W}:{H},setsar=1,"
                     f"fade=in:st=0:d=0.25,setpts=PTS-STARTPTS+{a}/TB[x{k}]")
            g.append(f"[{cur}][x{k}]overlay=0:0:eof_action=pass:enable='gte(t,{a})'[o{k}]"); cur = f"o{k}"; continue
        if fmt == "cta_final" and est["cta"].get("packshot"):
            C = est["cta"]; marca = F.marca_nome(plano, p); topo = C.get("topo", 1290)
            foto = f"{B}/{C['packshot'].replace('{MARCA}', marca[:1].upper() + marca[1:].lower())}"
            fundo, frasco, seta, (fx, fy, fw, fh) = cta_packshot_pngs(C.get("titulo", "").replace("{MARCA}", marca), marca,
                                                                       C.get("rodape", ""), foto, f"{ele}/cta_{p}", topo)
            d = total - a + 0.1
            ins += ["-loop", "1", "-t", f"{total:.3f}", "-i", fundo, "-loop", "1", "-t", f"{total:.3f}", "-i", frasco,
                    "-loop", "1", "-t", f"{total:.3f}", "-i", seta]
            # frasco: entra subindo 40 px com fade (0,35 s) e faz push-in lento 1,00→1,05; seta pula a 1,6 Hz
            z = f"(1+0.05*t/{d:.3f})"
            g.append(f"[{j+1}:v]fps=30,format=rgba,trim=0:{d:.3f},setpts=PTS-STARTPTS,"
                     f"scale=w='trunc({fw}*{z}/2)*2':h='trunc({fh}*{z}/2)*2':eval=frame,fade=in:st=0:d=0.35:alpha=1[fr{k}]")
            g.append(f"[{j+2}:v]fps=30,format=rgba,trim=0:{d:.3f},setpts=PTS-STARTPTS[st{k}]")
            g.append(f"[{j}:v]fps=30,setsar=1,trim=0:{d:.3f},setpts=PTS-STARTPTS[bg{k}];"
                     f"[bg{k}][fr{k}]overlay=x='(W-w)/2':y='{fy}+({fh}-h)/2+40*max(0,1-t/0.35)':eval=frame[bf{k}];"
                     f"[bf{k}][st{k}]overlay=x={(W - 120) // 2}:y='{topo + 300}+14*abs(sin(PI*1.6*t))':eval=frame,"
                     f"fade=in:st=0:d=0.2,setpts=PTS-STARTPTS+{a}/TB[x{k}]")
            g.append(f"[{cur}][x{k}]overlay=0:0:eof_action=pass:enable='gte(t,{a})'[o{k}]"); cur = f"o{k}"; continue
        if fmt == "cta_final":
            png = f"{ele}/cta_{p}.png"; C = est["cta"]
            cta_png(C.get("titulo", "").replace("{MARCA}", F.marca_nome(plano, p)), C.get("rodape", ""), png)
            ins += ["-loop", "1", "-t", f"{total:.3f}", "-i", png, "-i", fl]
            g.append(f"[{j+1}:v]scale=900:900:force_original_aspect_ratio=increase,crop=900:900,fps=30,setsar=1,tpad=stop_mode=clone:stop_duration=30[pv{k}]")
            g.append(f"[{j}:v]fps=30,setsar=1[bg{k}];[bg{k}][pv{k}]overlay=90:70:shortest=0,trim=0:{total - a + 0.1:.3f},setpts=PTS-STARTPTS+{a}/TB[x{k}]")
            g.append(f"[{cur}][x{k}]overlay=0:0:eof_action=pass:enable='gte(t,{a})'[o{k}]"); cur = f"o{k}"; continue
        ins += ["-i", fl]
        if fmt == "inset": x, y, w, h = Bz["inset"]; bd = Bz["inset_borda"]
        elif fmt == "avatar": x, y, w, h = est["avatar"]["quadro"]; bd = 0
        else: x, y, w, h = Bz["cartao"]; bd = Bz["cartao_borda"]
        iw, ih = w - 2 * bd, h - 2 * bd
        g.append(f"[{j}:v]trim=0:{b-a:.3f},setpts=PTS-STARTPTS+{a}/TB,scale={iw}:{ih}:force_original_aspect_ratio=increase,"
                 f"crop={iw}:{ih},pad={w}:{h}:{bd}:{bd}:color=0x111111,fps=30,setsar=1" + (f",eq=saturation=0.95,vignette=angle=PI/4.5" if fmt == "avatar" else "") + f"[x{k}]")
        g.append(f"[{cur}][x{k}]overlay={x}:{y}:eof_action=pass:enable='between(t,{a},{b})'[o{k}]"); cur = f"o{k}"
    # banner do hook
    HB = est["hook_banner"]
    if HB.get("texto"):
        png = f"{ele}/banner_H{n}.png"; bw, bh = banner_png(HB["texto"], png, HB["tamanho"], HB["largura_max"])
        j = ins.count("-i"); ins += ["-loop", "1", "-t", f"{HD:.3f}", "-i", png]
        g.append(f"[{cur}][{j}:v]overlay=0:{HB['y'] - bh // 2}:eof_action=pass:enable='lt(t,{HD})'[ob]"); cur = "ob"
    # legenda palavra por vez (texto do roteiro, tempos do whisper)
    hk = F.alinhar(json.load(open(F.L(B, f"palavras_H{n}.json"))), f["texto"])
    hd = F.alinhar(json.load(open(F.L(B, f"palavras_hold_{p}.json"))), F.texto_hold(plano, p))
    pal = hk + [(w, s + HD, e + HD) for w, s, e in hd]
    ass = f"{tmp}/AD{n}_{p}.ass"; ass_palavras(pal, ass, est, fim_leg)      # o .ass fica para o QC (texto e tempos)
    shutil.copy(ass, f"{B}/08_auto/legendas/AD{n}_{p}.ass")
    # legenda SEMPRE pílula TikTok Sans Medium (regra do Fefo, 13/11/2026): frases curtas em pílula no lugar da palavra
    # por vez com brilho; altura do layout (estilo.legenda.y em px) continua valendo
    import pilula
    L = est["legenda"]; cx = (lambda t: t.upper()) if L.get("caixa_alta") else (lambda t: t)
    evs = [(a, b, cx(t)) for a, b, t in pilula.agrupar(pal, fim=fim_leg)]
    lista = pilula.gerar(evs, None, 0, total, f"{tmp}/pilula_{n}_{p}", {"estilo": {"legenda": {"y": L["y"]}}})
    j = ins.count("-i"); ins += ["-f", "concat", "-safe", "0", "-i", lista]
    g.append(f"[{j}:v]fps=30,format=rgba[cap];[{cur}][cap]overlay=0:0:eof_action=pass:format=auto[vout]")
    # áudio
    import glob
    trilha = sorted(glob.glob(f"{B}/02_audio/trilha/*.mp3") + glob.glob(f"{B}/02_audio/trilha/*.wav"))
    lufs = cfg.get("audio", {}).get("loudness_lufs", -20)
    if trilha:
        vol = cfg.get("audio", {}).get("trilha_volume_db", -22); j = ins.count("-i"); ins += ["-stream_loop", "-1", "-i", trilha[0]]
        g.append(f"[{j}:a]volume={vol}dB,aresample=44100,aformat=channel_layouts=stereo[tr];[aa][tr]amix=inputs=2:duration=first:normalize=0[mx]")
        g.append(f"[mx]loudnorm=I={lufs}:TP=-1.5:LRA=11,aresample=48000[aout]")
    else:
        g.append(f"[aa]loudnorm=I={lufs}:TP=-1.5:LRA=11,aresample=48000[aout]")
    g.append(F.SAIDA_720)
    sc = f"{tmp}/fc_AD{n}_{p}.txt"; open(sc, "w").write(";\n".join(g))
    out = F.export(B, plano, p, n); os.makedirs(os.path.dirname(out), exist_ok=True)
    subprocess.run([F.FF, "-nostdin", "-v", "error", "-y", *ins, "-filter_complex_script", sc, "-map", "[v720]", "-map", "[aout]",
                    "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out], check=True)
    shutil.rmtree(tmp, ignore_errors=True); F.tira_export_antigo(B, plano, p, n)
    print(f"   ok {os.path.basename(out)} (hook {HD:.2f}s, total {total:.1f}s, {len(plan)} b-rolls{', com trilha' if trilha else ''})")

# ---------------------------------------------------------------- XML: posição/escala do avatar e do b-roll
def motion_avatar(sw, sh, est, z=1.0):
    """Escala/crop/centro no Premiere para o avatar ficar no quadro 4:5 entre faixas pretas."""
    A = est["avatar"]; qx, qy, qw, qh = A["quadro"]; s = qw / sw * z
    jan = qh / (qw / sw)                                   # altura da janela 4:5 em px da fonte
    cy0 = (sh - jan) * A["crop_y"]                         # topo da janela visível
    top = 100 * cy0 / sh; bot = 100 * (sh - cy0 - jan) / sh
    cen_src = cy0 + jan / 2                                # centro da janela -> centro do quadro (y = qy + qh/2)
    vert = ((qy + qh / 2) - (cen_src * s + (H - sh * s) / 2)) / H
    return 100 * s, 0.0, vert, top, bot

def motion_broll(sw, sh, est, fmt):
    Bz = est["broll"]
    x, y, w, h = Bz["inset"] if fmt == "inset" else est["avatar"]["quadro"] if fmt == "avatar" else Bz["cartao"]
    s = max(w / sw, h / sh)
    return 100 * s, (x + w / 2 - W / 2) / W, (y + h / 2 - H / 2) / H
