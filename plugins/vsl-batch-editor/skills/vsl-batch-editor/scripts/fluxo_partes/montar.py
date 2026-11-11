# Parte do fluxo.py: montagem final do AD. Roda no mesmo espaço de nomes do fluxo.py (não importar sozinho).
# ---------------------------------------------------------------- montagem final
# Regra do Fefo (02/11/2026): export sempre em 720p. A composição continua em 1080x1920 (posições em px de 1920)
# e só a saída desce; usado também em cartao.py e umtake.py.

# Prévia rápida (Fefo, 11/11/2026): com PREVIA=1 o encode final usa o chip de vídeo (h264_videotoolbox no Mac,
# h264_nvenc da RTX 3060 Ti no PC Windows; ~2,5 Mbps), que sai em segundos e quase não ocupa o processador. Serve para a
# sala e para o revisor julgarem corte, ritmo, legenda e som.
# O arquivo ganha um marcador "<saída>.PREVIA.txt" ao lado: enquanto ele existir, o vídeo NÃO é de entrega. O render
# normal (sem PREVIA) apaga o marcador. Entrega só de arquivo sem marcador.
def _codec_final(normal):
    if os.environ.get("PREVIA") == "1":
        chip = ["-c:v", "h264_nvenc", "-preset", "p4"] if os.name == "nt" else ["-c:v", "h264_videotoolbox"]
        return chip + ["-b:v", "2500k", "-maxrate", "3500k", "-bufsize", "5M"]
    return normal

def _marca_previa(saida):
    m = saida + ".PREVIA.txt"
    if os.environ.get("PREVIA") == "1":
        open(m, "w").write("Prévia rápida (PREVIA=1): não entregar. Rode o render sem PREVIA depois do aprovado.\n")
    elif os.path.exists(m):
        os.remove(m)

def _silencio_real(mp4, ini=0.0, dur=None, db=-42):
    """[(inicio, fim|None)] dos silêncios do áudio (silencedetect), no tempo do trecho lido."""
    cmd = [FF, "-nostats", "-hide_banner"] + (["-ss", f"{ini:.3f}"] if ini else []) + (["-t", f"{dur:.3f}"] if dur else []) + ["-i", mp4, "-af", f"silencedetect=n={db}dB:d=0.05", "-vn", "-f", "null", "-"]
    err = subprocess.run(cmd, capture_output=True, text=True).stderr
    out, aberto = [], None
    for m in re.finditer(r"silence_(start|end): (-?[\d.]+)", err):
        if m.group(1) == "start": aberto = max(0.0, float(m.group(2)))
        else: out.append((aberto if aberto is not None else 0.0, float(m.group(2)))); aberto = None
    if aberto is not None: out.append((aberto, None))
    return out
SAIDA_720 = "[vout]scale=720:1280:flags=lanczos,setsar=1[v720]"
# O estilo vem SEMPRE de plano.json -> "estilo", definido a partir de 01_refs/ da batch (módulo referencia).
ESTILOS = {
    "amarelo_contorno": "FontName=Arial Black,FontSize=16,PrimaryColour=&H0000E6FF,OutlineColour=&H00000000,BorderStyle=1,Outline=2.2,Shadow=0",
    "caixa_branca":     "FontName=Arial Black,FontSize=15,PrimaryColour=&H00000000,OutlineColour=&H00FFFFFF,BackColour=&H00FFFFFF,BorderStyle=3,Outline=6,Shadow=0",
    "caixa_branca_pequena": "FontName=Arial Black,FontSize=10,PrimaryColour=&H00000000,OutlineColour=&H00FFFFFF,BackColour=&H00FFFFFF,BorderStyle=3,Outline=4,Shadow=0",
    # caixa_branca 25% menor e caixa com metade da altura (pedido do Fefo, BATCH#2820)
    "caixa_branca_compacta": "FontName=Arial Black,FontSize=11,PrimaryColour=&H00000000,OutlineColour=&H00FFFFFF,BackColour=&H00FFFFFF,BorderStyle=3,Outline=1.5,Shadow=0",
    # caixa_branca 40% menor e caixa justa, quase do tamanho da fonte (pedido do Fefo, BATCH#2822)
    "caixa_branca_justa": "FontName=Arial Black,FontSize=9,PrimaryColour=&H00000000,OutlineColour=&H00FFFFFF,BackColour=&H00FFFFFF,BorderStyle=3,Outline=1,Shadow=0",
    "branca_contorno":  "FontName=Arial Black,FontSize=16,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2.2,Shadow=0",
    # branca sem caixa, sans meio-negrito, contorno preto fino + sombra leve; usar com estilo.legenda.caixa_alta (ref
    # mini-filme "I lied" da Resilia, BATCH#2480: 1-2 linhas curtas na altura do peito). A Montserrat variável do Mac
    # sai fina/vazada no libass: usar Avenir Next Demi Bold.
    "branca_fina_caps": "FontName=Avenir Next Demi Bold,Bold=0,FontSize=11,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H99000000,BorderStyle=1,Outline=0.5,Shadow=0.3,Spacing=0.2",
    # branca regular, caixa normal, contorno preto fino + sombra leve, frase inteira em 1-2 linhas (ref cartoon da Resilia,
    # BATCH#2481): "Somebody called about a" ocupa ~60% da largura como no ref; usar com posicao peito_alto (~67% da altura)
    "branca_fina":      "FontName=Helvetica Neue,FontSize=10,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H80000000,BorderStyle=1,Outline=0.4,Shadow=0.25",
    # branca_fina legível: negrito, 30% maior, contorno preto grosso + sombra; mesma posição, sem caixa, linha longa
    # quebra sozinha em 2 ("hard to read" na branca_fina sobre fundo cartoon vermelho, Zane, BATCH#2481 V2)
    "branca_legivel":   "FontName=Helvetica Neue,Bold=1,FontSize=13,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H99000000,BorderStyle=1,Outline=1.8,Shadow=0.9",
    # branca_legivel sem a sombra deslocada (a sombra semitransparente "sujava" a letra: Daniel, BATCH#3831 V2, 06/11/2026):
    # mesma fonte e tamanho, só contorno preto
    "branca_limpa":     "FontName=Helvetica Neue,Bold=1,FontSize=13,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=1.5,Shadow=0",
    # palavra por vez, caixa alta, branca com brilho (ref Dr. Kegel, BATCH_2078). No layout "cartao" vira ASS próprio.
    "palavra_brilho":   "FontName=Helvetica Neue Medium,FontSize=14,PrimaryColour=&H00FFFFFF,OutlineColour=&H60000000,BorderStyle=1,Outline=1,Shadow=0",
    # caixa arredondada por linha, 1-2 linhas, estilo texto do Instagram (ref Paleovalley, BATCH#2824). Desenhada em PNG
    # por pilula.py (o header do hook vai junto, no mesmo estilo); não usa o filtro subtitles.
    "pilula":           None,
}
POSICOES = {"divisao": "Alignment=2,MarginV=150", "centro_baixo": "Alignment=2,MarginV=100", "centro": "Alignment=10,MarginV=0",   # 10 = meio (numeração antiga); 5 caía no topo (BATCH#3378)
            "meio_alto": "Alignment=6,MarginV=65",
            "peito_alto": "Alignment=2,MarginV=96",     # linha centrada em ~64% da altura (ref BATCH#2480)
            "peito": "Alignment=2,MarginV=55"}      # ~78% da altura, abaixo do rosto nas selfies (BATCH#2824)   # ~30% do topo (ref Paleovalley, BATCH#2824). force_style no .srt usa a
                                                     # numeração antiga do SSA: 1-3 base, +4 topo, +8 meio (6 = topo centralizado)

def ass_textos(B, plano, plan, HD, out, n=None, sem_header=False):
    """Textos fixos por cima do vídeo, lidos do plano: 'header' (topo, só durante o hook), 'hook_header' (um por hook:
    [1ª metade em faixa branca, 2ª metade em caixa vermelha], ref Smdge, BATCH#2820), 'titulo_hook' (um por hook, caixa azul
    na altura do peito, estilo.titulo_hook_y), 'callout' de cena
    (texto grande no meio; continua nas cenas seguintes que reaproveitam o mesmo clipe) e 'destaque' (pílula menor).
    Devolve False se não houver nada para escrever."""
    cen = {c["id"]: c for c in plano["cenas"]}; ev = []
    t = lambda x: "%d:%02d:%05.2f" % (x // 3600, x % 3600 // 60, x % 60)
    esc = lambda x: x.replace("{", "(").replace("}", ")")
    if plano.get("header") and not sem_header:
        ev.append(f"Dialogue: 0,{t(0)},{t(HD)},Header,,0,0,0,,{esc(plano['header'])}")
    tg = plano.get("tag_hook")      # tag curta no topo durante o hook, sem esconder a legenda (ref Smdge "WE LIED", BATCH#2822)
    if tg and (not tg.get("hooks") or n in tg["hooks"]):
        fim = HD
        if tg.get("so_broll"):    # some quando o avatar aparece (não cobre o rosto)
            fim = max([bb for cid, aa, bb, _ in plan if cen.get(cid, {}).get("tipo") == "hook"] or [HD])
        ev.append(f"Dialogue: 2,{t(0)},{t(min(fim, tg.get('dur', HD)))},Tag,,0,0,{tg.get('y', 360)},,{esc(tg['texto'])}")
    hh = plano.get("hook_header", {}).get(str(n)) if n is not None else None
    if hh and plano.get("hook_card", {}).get(str(n)): hh = None      # card em PNG no lugar (montar, BATCH#3375)
    if hh:
        import textwrap
        y = plano.get("estilo", {}).get("hook_header_y", 120)   # topo do bloco (px de 1920); 2820: terço inferior
        for k, parte in enumerate(hh):
            ln = textwrap.wrap(esc(parte), plano.get("estilo", {}).get("hook_header_quebra", 24))   # 3214: 32 (24 deixava "vision" sozinha)
            txt = "\\N".join(ln)
            hdur = plano.get("estilo", {}).get("hook_header_dur")   # header só nos primeiros N s (ref: "banner first 5 s", 3855)
            ev.append(f"Dialogue: 0,{t(0)},{t(min(HD, hdur) if hdur else HD)},{'HookBranco' if k == 0 else 'HookVermelho'},,0,0,{y},,{txt}")
            y += 74 * len(ln) + 6
    th = plano.get("titulo_hook", {}).get(str(n)) if n is not None else None   # título que muda por hook (BATCH#3214: "Eye doctor")
    if th:
        ev.append(f"Dialogue: 0,{t(0)},{t(HD)},TituloHook,,0,0,{plano.get('estilo', {}).get('titulo_hook_y', 1240)},,{esc(th)}")
    for k, (cid, a, b, fl) in enumerate(plan):
        c = cen.get(cid, {})
        if c.get("callout"):
            b2 = b
            for cid2, a2, bb, _ in plan[k + 1:]:
                if cen.get(cid2, {}).get("usa") == cid: b2 = bb
                else: break
            txt = esc(c["callout"]).replace(" GET", "\\NGET")
            if c.get("callout_y"):   # topo do texto em px de 1920 (no meio cobria o nome no rótulo do frasco, BATCH#3222)
                txt = f"{{\\an8\\pos(540,{int(c['callout_y'])})}}" + txt
            ev.append(f"Dialogue: 1,{t(a)},{t(b2)},{'CalloutTopo' if c.get('formato') == 'cta_final' else 'Callout'},,0,0,0,,{txt}")
        if c.get("destaque"):
            b2, j = b, k
            for cid2, a2, bb, _ in plan[k + 1:]:
                if cen.get(cid2, {}).get("usa") == cid: b2, j = bb, j + 1
                else: break
            # avatar logo depois: o b-roll fica 0,1 s a mais na tela (montar) e o destaque sumia 3 quadros antes do corte
            # (BATCH#3215 V2, S37 -> médico; lascas.py acusava 3 quadros)
            if j + 1 < len(plan) and plan[j + 1][1] - b2 > 0.05: b2 += 0.1
            dy = plano.get("estilo", {}).get("destaque_y")   # centro em px de 1920 (no meio batia na legenda; BATCH#3217)
            pos = "{\\an5\\pos(540,%d)}" % int(dy) if dy else ""
            ev.append(f"Dialogue: 1,{t(a)},{t(b2)},Destaque,,0,0,0,,{pos}{esc(c['destaque'])}")
    if not ev: return False
    open(out, "w").write(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 0\n\n[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Header,Arial Black,56,&H00000000,&H00000000,&H00FFFFFF,&H00000000,0,0,0,0,100,100,0,0,1,5,0,8,70,70,190,1\n"
        "Style: HookBranco,Arial Black,62,&H00000000,&H00000000,&H00FFFFFF,&H00FFFFFF,0,0,0,0,100,100,0,0,3,8,0,8,60,60,210,1\n"
        "Style: HookVermelho,Arial Black,62,&H00FFFFFF,&H00FFFFFF,&H001E1ED8,&H001E1ED8,0,0,0,0,100,100,0,0,3,8,0,8,60,60,210,1\n"
        "Style: Callout,Arial Black,112,&H00FFFFFF,&H00FFFFFF,&H00193A6B,&H00000000,0,0,0,0,100,100,0,0,1,9,0,5,60,60,0,1\n"
        "Style: CalloutTopo,Arial Black,112,&H00FFFFFF,&H00FFFFFF,&H00193A6B,&H00000000,0,0,0,0,100,100,0,0,1,9,0,8,60,60,170,1\n"
        "Style: TituloHook,Arial Black,54,&H00FFFFFF,&H00FFFFFF,&H00512A1A,&H00512A1A,0,0,0,0,100,100,1,0,3,12,0,8,60,60,1240,1\n"
        "Style: Tag,Arial Black,66,&H00FFFFFF,&H00FFFFFF,&H002B1BE0,&H002B1BE0,0,0,0,0,100,100,1,0,3,16,0,8,60,60,360,1\n"
        "Style: Destaque,Arial Black,64,&H00FFFFFF,&H00FFFFFF,&H001E7BE0,&H001E7BE0,0,0,0,0,100,100,0,0,3,14,0,5,60,60,0,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n" + "\n".join(ev) + "\n")
    return True

def estilo_do_plano(plano, cfg):
    e = plano.get("estilo")
    if not e:
        raise SystemExit("plano.json não tem 'estilo'. Rode o módulo referencia (analisa 01_refs/ desta batch) antes de montar.")
    leg = e.get("legenda", {})
    nome = leg.get("estilo") or cfg.get("legenda", {}).get("estilo", "amarelo_contorno")
    if nome not in ESTILOS: raise SystemExit(f"Estilo de legenda '{nome}' ainda não existe em ESTILOS (fluxo.py): implemente antes.")
    av = e.get("avatar", {})
    return {"pb": bool(av.get("pb", False)),
            "pip": av.get("pip") if av.get("enquadramento") == "pip" else None,
            "layout": e.get("broll", {}).get("layout", "tela_cheia"),
            "pilula": nome == "pilula",
            "sub": (ESTILOS[nome] or "") + "," + POSICOES.get(leg.get("posicao", "centro_baixo"), POSICOES["centro_baixo"])}

def pip_pngs(w, h, raio, borda, pasta, s=12):
    """Máscara de cantos arredondados (w x h) e moldura da janela do picture-in-picture: borda branca de `borda` px e sombra
    leve de `s` px em volta (BATCH#3217). Devolve (máscara, moldura, s); a moldura vai em (x - borda - s, y - borda - s)."""
    from PIL import Image, ImageDraw, ImageFilter
    os.makedirs(pasta, exist_ok=True)
    mk = Image.new("L", (w, h), 0); ImageDraw.Draw(mk).rounded_rectangle([0, 0, w - 1, h - 1], raio, fill=255)
    W, H = w + 2 * (borda + s), h + 2 * (borda + s)
    sombra = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sombra).rounded_rectangle([s, s + 4, W - s - 1, H - s + 3], raio + borda, fill=110)
    fr = Image.new("RGBA", (W, H), (0, 0, 0, 0)); fr.putalpha(sombra.filter(ImageFilter.GaussianBlur(7)))
    ImageDraw.Draw(fr).rounded_rectangle([s, s, W - s - 1, H - s - 1], raio + borda, fill=(255, 255, 255, 255))
    mk.save(f"{pasta}/pip_mascara.png"); fr.save(f"{pasta}/pip_moldura.png")
    return f"{pasta}/pip_mascara.png", f"{pasta}/pip_moldura.png", s

def montar(B, p, n):
    if carregar(B)[0].get("one_take"):
        import umtake; return umtake.montar(sys.modules[__name__], B, p, n)
    plano, cfg = carregar(B); n = int(n); f, pm, hs = hook_marca(plano, n, p); est = estilo_do_plano(plano, cfg)
    if est["layout"] == "cartao":
        import cartao; return cartao.montar(sys.modules[__name__], B, p, n)
    tmp = tmp_montar(B); os.makedirs(tmp, exist_ok=True)
    segs = g30(json.load(open(corte(B, fala_stem(f, pm))))); hook = f"{tmp}/hook{n}.mp4"
    fc = ";".join(f"[0:v]{vtrim(s, e)[0]},scale=720:1280{punch(plano, i)},fps=30{vtrim(s, e)[1]},setsar=1[v{i}];[0:a]atrim={s}:{e},asetpts=PTS-STARTPTS{afade(e - s)}{ganho(f, pm)},aresample=44100,aformat=channel_layouts=stereo[a{i}]" for i, (s, e) in enumerate(segs))
    fc += ";" + "".join(f"[v{i}][a{i}]" for i in range(len(segs))) + f"concat=n={len(segs)}:v=1:a=1[v][a]"
    subprocess.run([FF, "-nostdin", "-v", "error", "-y", "-i", fala_mp4(B, f, pm), "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-crf", "18", "-c:a", "aac", "-b:a", "192k", hook], check=True)
    plan, HD = segmentos(B, p, n)
    json.dump(plan, open(f"{B}/{AUTO}/broll_posicoes_AD{n}_{p}.json", "w"), indent=1)
    sub = f"{tmp}/AD{n}_{p}.srt"; shutil.copy(L(B, f"AD{n}_{p}.srt"), sub)
    if plano.get("estilo", {}).get("legenda", {}).get("caixa_alta"):      # legenda em caixa alta (ref BATCH#2480)
        escrever_srt([(a, b, t.upper()) for a, b, t in ler_srt(sub)], sub)
    cen = {c["id"]: c for c in plano["cenas"]}
    PL = pulo_hold(B, plano, p, n); DP = duracao(previa(B, p)) - PL     # hold sem a(s) fala(s) pulada(s) neste AD
    ext = max([b for cid, a, b, fl in plan if pos_fala(cen[cid])] + [0]) - (HD + DP)   # tela final depois da fala
    pad = f",tpad=stop_mode=clone:stop_duration={ext:.3f}" if ext > 0 else ""; apad = f",apad=pad_dur={ext:.3f}" if ext > 0 else ""
    ins = ["-i", hook, "-i", previa(B, p)]
    # o AAC do hook completa o último pacote (1024 amostras): o áudio saía até 23 ms mais longo que o vídeo, o concat
    # começava a hold depois dele e o AD pulava 2 quadros na emenda hook -> hold (hooks 1 e 3, BATCH#3215)
    hq = sum(int((e - s) * 30 + 1e-6) for s, e in segs) / 30
    # Silêncio REAL entre o fim da fala do hook e a 1ª palavra da hold (o ruído do clipe do Kling, -38 a -45 dB, enchia a pausa e o
    # envelope mostrava ~0,1 s, V2 da 4083): o áudio do hook cai a zero 40 ms depois da última palavra e a hold só entra 30 ms antes da
    # 1ª palavra. Total medido impresso abaixo; meta >= 0,30 s (`respiro_hook_s_<hook>` no batch.json aumenta o fim do hook).
    sh = _silencio_real(hook); ts = sh[-1][0] if sh and (sh[-1][1] is None or sh[-1][1] >= hq - 0.12) else hq
    ts = min(ts, hq)
    sp = _silencio_real(previa(B, p), PL, 1.5); tl = next((e for a0, e in sp if a0 < 0.05 and e is not None), 0.0)
    sil = (hq - ts - 0.04) + max(tl - 0.03, 0)
    print(f"   hook {n}: silêncio real hook→hold {sil:.2f} s (fala do hook acaba em {ts:.2f}, hold entra em {tl:.2f})" + ("  AVISO < 0,30 s" if sil < 0.30 else ""))
    g = [f"[0:v]scale=720:1280,fps=30,setsar=1[hv];[0:a]atrim=end={hq:.6f},afade=t=out:st={ts:.3f}:d=0.04[ha];[1:v]trim=start={PL:.6f},setpts=PTS-STARTPTS,scale=720:1280,fps=30,setsar=1[pv];[1:a]atrim=start={PL:.6f},asetpts=PTS-STARTPTS,afade=t=in:st={max(tl - 0.03, 0):.3f}:d=0.03[pa];[hv][ha][pv][pa]concat=n=2:v=1:a=1[av0][aa0]",
         f"[av0]null{pad}[av];[aa0]anull{apad}" + (",asplit=2[aa][voz]" if os.environ.get("DUMP_VOZ") else "[aa]")]
    if est["pip"]: g.append("[av]split[avb][avp]")      # avp = o médico na janela (picture-in-picture, BATCH#3217)
    g.append(f"[{'avb' if est['pip'] else 'av'}]scale=1080:1920" + (",hue=s=0,eq=contrast=1.08" if est["pb"] else "") + "[b0]")
    if est["layout"] == "metade_baixo": geo, oy = "scale=1080:-2,crop=1080:960:0:(ih-960)/2", 960
    else: geo, oy = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920", 0
    cur = "b0"
    import elementos_hook as EH
    for k, (cid, a, b, fl) in enumerate(plan):
        c = cen.get(cid, {}); j = ins.count("-i"); ins += ["-i", fl]
        i0 = cena_inicio(c)
        # cada cena passa 3 quadros do fim por baixo da seguinte: sem isso o 1º quadro do clipe novo cai depois
        # do corte e aparece 1 quadro do fundo (preto quando não tem avatar)
        b2 = b + 0.1 if k + 1 < len(plan) else b
        # PiP (inset) seguido de avatar: os 3 quadros a mais ficavam à vista depois do corte (lascas, BATCH#3375)
        if c.get("formato") == "inset" and (k + 1 == len(plan) or plan[k + 1][1] - b > 0.02): b2 = b
        if c.get("formato") == "inset" and oy == 0:
            # antes/depois num cartão por cima do avatar, que continua falando (BATCH#3223; elementos_hook.inset_*)
            mk, mo, (ix, iy, il) = EH.inset_pngs(plano.get("estilo", {}).get("inset"), c.get("rotulo"), f"{tmp}/inset", cid)
            jm = ins.count("-i"); ins += ["-loop", "1", "-framerate", "30", "-t", f"{b2 - a + 0.3:.3f}", "-i", mk]
            jf = ins.count("-i"); ins += ["-loop", "1", "-framerate", "30", "-t", f"{b2 + 0.3:.3f}", "-i", mo]
            g.append(EH.inset_filtro(j, jm, i0, b2 - a, a, k, il, float(c.get("inset_cy", 0.4)), c.get("inset_filtro", "")))
            g.append(f"[{cur}][x{k}]overlay={ix}:{iy}:eof_action=pass:format=auto:enable='between(t,{a},{b2})'[oi{k}]")
            g.append(f"[{jf}:v]format=rgba[fm{k}];[oi{k}][fm{k}]overlay=0:0:eof_action=pass:format=auto:"
                     f"enable='between(t,{a},{b2})'[o{k}]"); cur = f"o{k}"
            continue
        if clipe_direita(B, c, p):       # tela dividida (tipo B de hooks.md): esquerda = resultado, direita = produto
            jr = ins.count("-i"); ins += ["-i", clipe_direita(B, c, p)]
            g.append(EH.split_filtro(j, jr, i0, float(c.get("inicio_direita", 0)), b2 - a, a, k, 1920 - oy, int(c.get("divisoria", 0))))
        else:
            # quadros do b-roll meio quadro antes da grade de 30 fps: com a hold começando exatamente na grade (emenda AAC,
            # 3215) o overlay empatava por microssegundos com o quadro principal e pulava/triplicava quadros (BATCH#3214 AD2)
            # cena com "push_in" (zoom por segundo): b-roll com trecho parado ou clipe mais curto que a cena; o último
            # quadro se repete e o zoom continua, em subpixel (BATCH#3825: freezedetect em 9 cenas do Kling)
            r = float(c.get("push_in") or 0); z0 = float(c.get("zoom") or 0)   # "zoom": 0.18 = enquadramento 1,18x fixo (corte em punch-in no 2º corte do mesmo clipe)
            zp = ""
            if (r or z0) and oy == 0:
                kz = f"({z0}+{r}*in/30)"
                x0, y0, w, h = f"540*{kz}/(1+{kz})", f"960*{kz}/(1+{kz})", f"1080/(1+{kz})", f"1920/(1+{kz})"
                zp = (f",tpad=stop_mode=clone:stop_duration=3,trim=end_frame={int((b2 - a) * 30) + 2},"
                      f"perspective=x0='{x0}':y0='{y0}':x1='{x0}+{w}':y1='{y0}':x2='{x0}':y2='{y0}+{h}':"
                      f"x3='{x0}+{w}':y3='{y0}+{h}':interpolation=cubic:eval=frame")
            rc = c.get("recorte")    # [x, y, w, h] em fração do clipe: recorte antes do enquadramento (ex.: organizador sem o frasco)
            rec = f"crop=trunc(iw*{rc[2]}/2)*2:trunc(ih*{rc[3]}/2)*2:iw*{rc[0]}:ih*{rc[1]}," if rc else ""
            g.append(f"[{j}:v]trim={i0:.3f}:{i0+b2-a:.3f},setpts=PTS-STARTPTS,{rec}{geo},fps=30{zp},settb=1/90000,"
                     f"setpts=PTS+{round(a * 30) / 30 - 1 / 60:.6f}/TB,setsar=1[x{k}]")
        g.append(f"[{cur}][x{k}]overlay=0:{oy}:eof_action=repeat:enable='between(t,{a},{b2})'[o{k}]"); cur = f"o{k}"
    evs = ler_srt(sub); nt = lambda s: re.sub(r"[^a-z0-9% ]", "", s.lower())
    total = HD + DP + max(ext, 0)
    if est["pip"]:
        # médico em picture-in-picture (BATCH#3217): recorte do avatar 720x1280 numa janela de cantos arredondados, com
        # borda branca e sombra leve, por cima do b-roll e por baixo da legenda. estilo.avatar.pip = {x, y, w, h, raio,
        # borda, recorte: [x, y, w, h] no quadro 720x1280 do avatar}
        pp = est["pip"]; x, y, w, h = (int(pp[k]) for k in ("x", "y", "w", "h")); bd = int(pp.get("borda", 6))
        rx, ry, rw, rh = pp.get("recorte", [0, 40, 720, 960])
        mk, fr, s = pip_pngs(w, h, int(pp.get("raio", 28)), bd, f"{tmp}/pip")
        jm = ins.count("-i"); ins += ["-loop", "1", "-framerate", "30", "-t", f"{total + 1:.3f}", "-i", mk]
        jf = ins.count("-i"); ins += ["-loop", "1", "-framerate", "30", "-t", f"{total + 1:.3f}", "-i", fr]
        # cena com "pip": false (frasco em close, rótulo no canto da janela): a janela some só durante a cena
        fora = [(a, b) for cid, a, b, _ in plan if cen.get(cid, {}).get("pip") is False]
        en = (":enable='not(" + "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in fora) + ")'") if fora else ""
        g.append(f"[avp]crop={rw}:{rh}:{rx}:{ry},scale={w}:{h},setsar=1,format=rgba[pv];[{jm}:v]format=gray[pm];[pv][pm]alphamerge[pa]")
        g.append(f"[{cur}][{jf}:v]overlay={x - bd - s}:{y - bd - s}:eof_action=pass:format=auto{en}[pf];"
                 f"[pf][pa]overlay={x}:{y}:eof_action=pass:format=auto{en}[pip]"); cur = "pip"
    # banner/sticker com alfa (.mov 1080x1920, em loop) por cima do vídeo, em trechos do AD (BATCH#2822: Halloween 71% OFF):
    # estilo.overlays = [{"arquivo": "06_elementos/x.mov", "trechos": [{"cena": "S14"}, {"de": "<legenda>", "ate": "fim"}]}]
    jan = {cid: (a, b) for cid, a, b, _ in plan}
    fim_v = max([total] + [b for _, _, b, _ in plan])     # a última cena pode passar uns quadros do fim da fala
    for q, ov in enumerate(plano.get("estilo", {}).get("overlays", [])):
        fd = float(ov.get("fade", 0.12))
        for r, t in enumerate(ov["trechos"]):
            if "cena" in t:
                if t["cena"] not in jan: continue                      # cena que não entra neste AD
                a, b = jan[t["cena"]]
            else:
                # "de": "inicio" = desde o quadro 0 do AD, hook incluído (faixa de BF "o vídeo todo", BATCH#3467)
                ini0 = t["de"] == "inicio"
                i = 0 if ini0 else next((k for k, e in enumerate(evs) if nt(t["de"]) in nt(e[2])), None)
                fim = t.get("ate", "fim")
                j = None if i is None or fim == "fim" else next((k for k in range(i, len(evs)) if nt(fim) in nt(evs[k][2])), None)
                if i is None or (fim != "fim" and j is None): raise SystemExit(f"overlays: não achei {t} na legenda AD{n}_{p}")
                a, b = (0.0 if ini0 else evs[i][0]), (fim_v + 0.5 if fim == "fim" else evs[j][1])
            jo = ins.count("-i"); ins += ["-stream_loop", "-1", "-i", f"{B}/{ov['arquivo']}"]
            sai = f",fade=out:st={b - fd:.3f}:d={fd}:alpha=1" if b < fim_v - 0.05 else ""
            g.append(f"[{jo}:v]trim=0:{b - a:.3f},setpts=PTS-STARTPTS+{a:.3f}/TB,fps=30,format=rgba,"
                     f"fade=in:st={a:.3f}:d={fd}:alpha=1{sai}[ov{q}_{r}]")
            # "y": desloca o .mov em px de 1920 (faixa BF de cima para dentro do 4:5, 285–1635: "text wont fit within 4:5", 3465 V1)
            g.append(f"[{cur}][ov{q}_{r}]overlay=0:{int(ov.get('y', 0))}:eof_action=pass:format=auto:enable='between(t,{a:.3f},{b:.3f})'[ovo{q}_{r}]")
            cur = f"ovo{q}_{r}"
    # card de abertura do hook em PNG (caixa branca, emoji colorido, BATCH#3375): plano.hook_card = {"<n>": {"linhas":
    # [...], "png": "06_elementos/card_H<n>.png"}}, geometria em estilo.hook_card; fica do quadro 0 ao fim do hook
    hc = plano.get("hook_card", {}).get(str(n))
    if hc:
        import elementos_hook as EH2
        png = f"{B}/{hc['png']}".replace("{p}", p)     # "{p}" = card por marca (BATCH#3846)
        if not os.path.exists(png): EH2.hook_card(hc["linhas"], plano.get("estilo", {}).get("hook_card", {}), png)
        jc = ins.count("-i"); ins += ["-loop", "1", "-framerate", "30", "-t", f"{HD:.3f}", "-i", png]
        g.append(f"[{cur}][{jc}:v]overlay=0:0:eof_action=pass:format=auto:enable='between(t,0,{HD:.3f})'[hcard]"); cur = "hcard"
    # elementos de hook (modulos/hooks.md, scripts/elementos_hook.py), por baixo da legenda:
    # estilo.barra_tempo = barra de progresso dos marcos no topo (tipo A, ref NoMore), troca pelo texto da legenda;
    # estilo.tag_nativa = legenda "nativa" estilo Snapchat nos primeiros segundos do hook (tipo F, ref Pureskin)
    es = plano.get("estilo", {})
    if EH.vale(es.get("barra_tempo"), n):
        lb, yb = EH.barra_tempo(es["barra_tempo"], evs, fim_v, f"{tmp}/barra")
        jb = ins.count("-i"); ins += ["-f", "concat", "-safe", "0", "-i", lb]
        g.append(f"[{jb}:v]fps=30,format=rgba[bt];[{cur}][bt]overlay=0:{yb}:eof_action=pass:format=auto[bto]"); cur = "bto"
    if EH.vale(es.get("tag_nativa"), n):
        tn, yt = EH.tag_nativa(es["tag_nativa"], tmp); ta, tb = EH.janela_tag(es["tag_nativa"], HD)
        jt = ins.count("-i"); ins += ["-loop", "1", "-t", f"{tb + 0.2:.3f}", "-i", tn]
        g.append(f"[{jt}:v]fps=30,format=rgba[tn];[{cur}][tn]overlay=0:{yt}:eof_action=pass:format=auto:"
                 f"enable='between(t,{ta:.3f},{tb:.3f})'[tno]"); cur = "tno"
    ass = f"{tmp}/textos_AD{n}_{p}.ass"
    if est["pilula"]:
        import pilula
        alt = [(a, b, cen[cid]["legenda_y"]) for cid, a, b, _ in plan if "legenda_y" in cen.get(cid, {})]
        # trecho de fala (sem cena de b-roll) com a legenda em outra altura, achado pelo texto da legenda:
        # estilo.legenda.y_trechos = [{"de": "...", "ate": "...", "y": 0.8}] (BATCH#2822: placa "68% OFF" na mão do avatar)
        for t in plano.get("estilo", {}).get("legenda", {}).get("y_trechos", []):
            i = next((k for k, e in enumerate(evs) if nt(t["de"]) in nt(e[2])), None)
            j = next((k for k in range(i or 0, len(evs)) if nt(t.get("ate", t["de"])) in nt(evs[k][2])), None)
            if i is None or j is None: raise SystemExit(f"y_trechos: não achei {t} na legenda AD{n}_{p}")
            alt.insert(0, (evs[i][0], evs[j][1], t["y"]))
        # header_pilula.y_hook = {"3": 960}: outra altura do header num hook (BATCH#3465: no topo cobria o rosto do H3-01)
        hp = plano.get("estilo", {}).get("header_pilula", {}); hy = hp.get("y_hook", {}).get(str(n))
        pl = plano if hy is None else {**plano, "estilo": {**plano["estilo"], "header_pilula": {**hp, "y": hy}}}
        lista = pilula.gerar(evs, plano.get("header"), HD, total, f"{tmp}/pilula", pl, alt)
        jc = ins.count("-i"); ins += ["-f", "concat", "-safe", "0", "-i", lista]
        g.append(f"[{jc}:v]fps=30,format=rgba[cap];[{cur}][cap]overlay=0:0:eof_action=pass:format=auto[pl]")
        g.append(f"[pl]subtitles={ass}[vout]" if ass_textos(B, plano, plan, HD, ass, n, sem_header=True) else "[pl]null[vout]")
    elif ass_textos(B, plano, plan, HD, ass, n):
        g.append(f"[{cur}]subtitles={sub}:force_style='{est['sub']}'[vs];[vs]subtitles={ass}[vout]")
    else:
        g.append(f"[{cur}]subtitles={sub}:force_style='{est['sub']}'[vout]")
    trilha = sorted(glob.glob(f"{B}/{AUDIO}/trilha/*.mp3") + glob.glob(f"{B}/{AUDIO}/trilha/*.wav"))
    lufs = cfg.get("audio", {}).get("loudness_lufs", -20)
    if trilha:
        vol = cfg.get("audio", {}).get("trilha_volume_db", -22); it = ins.count("-i"); ins += ["-stream_loop", "-1", "-i", trilha[0]]
        fim_db = plano.get("estilo", {}).get("trilha_final_db")      # trilha sobe quando a voz acaba (tela final)
        if fim_db is not None and ext > 0:
            T, v1, v2 = HD + DP, 10 ** (vol / 20), 10 ** (fim_db / 20)
            gv = f"volume='{v1:.5f}+({v2 - v1:.5f})*clip((t-{T:.3f})/0.5,0,1)':eval=frame"
        else: gv = f"volume={vol}dB"
        gv += f",volume=0.25:enable='between(t,{ts + 0.04:.3f},{hq + max(tl - 0.03, 0):.3f})'"   # trilha cai ~12 dB no silêncio hook -> hold (a pausa aparece no mix)
        g.append(f"[{it}:a]{gv},aresample=44100,aformat=channel_layouts=stereo[tr];[aa][tr]amix=inputs=2:duration=first:normalize=0[mx]")
        g.append(f"[mx]loudnorm=I={lufs}:TP=-1.5:LRA=11,aresample=48000[aout]")
    else:
        g.append(f"[aa]loudnorm=I={lufs}:TP=-1.5:LRA=11,aresample=48000[aout]")
    g.append(SAIDA_720)
    sc = f"{tmp}/fc_AD{n}_{p}.txt"; open(sc, "w").write(";".join(g))
    out = export(B, plano, p, n); os.makedirs(os.path.dirname(out), exist_ok=True)
    vz = os.environ.get("DUMP_VOZ")     # pasta: grava a trilha de VOZ isolada (antes da música/loudnorm) para medir pausas
    extra = ["-map", "[voz]", "-c:a", "pcm_s16le", f"{vz}/voz_AD{n}_{p}.wav"] if vz else []
    subprocess.run([FF, "-nostdin", "-v", "error", "-y", *ins, "-filter_complex_script", sc, *extra, "-map", "[v720]", "-map", "[aout]",
                    *_codec_final(["-c:v", "libx264", "-preset", "medium", "-crf", "20"]), "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", out], check=True)
    _marca_previa(out)
    shutil.rmtree(tmp, ignore_errors=True); tira_export_antigo(B, plano, p, n)
    print(f"   ok {os.path.basename(out)} (hook {HD:.2f}s, {len(plan)} b-rolls{', com trilha' if trilha else ''})")

