# Parte do fluxo.py: ações locais (o que o fazer executa). Roda no mesmo espaço de nomes do fluxo.py (não importar sozinho).
# ---------------------------------------------------------------- ações locais
def executar(B, acao):
    plano, cfg = carregar(B); k = acao[0]
    os.makedirs(f"{B}/08_auto/cortes", exist_ok=True); os.makedirs(f"{B}/08_auto/legendas", exist_ok=True)
    if k.endswith("_take"):
        import umtake; return umtake.executar(sys.modules[__name__], B, acao)
    if k == "rapido":
        _, src, dst, v = acao; os.makedirs(os.path.dirname(dst), exist_ok=True)
        subprocess.run([FF, "-nostdin", "-v", "error", "-y", "-i", src, "-filter_complex",
                        f"[0:v]setpts=PTS/{v}[v];[0:a]atempo={v}[a]", "-map", "[v]", "-map", "[a]",
                        "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-c:a", "aac", "-b:a", "192k", dst], check=True)
        return
    if k == "corte":
        _, mp4, stem = acao; man = f"{B}/08_auto/cortes/{stem}.manual.json"
        import vsl
        c = vsl.load_cfg(f"{B}/batch.json")
        exato = False
        if os.path.exists(man):
            segs = json.load(open(man)); print(f"   (corte manual mantido: {stem})")
            # {"segs": [...], "exato": true} = bordas como estão: o chiado tipo "s" do Seedance depois de "macula" (−45 a −50 dB)
            # não conta como silêncio e a borda andava até depois dele ("maculus", BATCH#3214 F04)
            if isinstance(segs, dict): exato, segs = bool(segs.get("exato")), segs["segs"]
        else:
            db = vsl.envelope(mp4)
            segs = vsl.keep_segments(db, c["limiar_db"], c["silencio_min_s"], c["folga_antes_s"], c["folga_depois_s"])
        if not exato: segs = bordas_no_silencio(mp4, segs, rel=c.get("borda_relativa_db"))
        if eh_seedance(plano, stem):
            # todo clipe do Seedance tem um estalo ~50 ms antes do fim do arquivo (04_falas.md): nenhum trecho vai até lá
            fim = duracao(mp4) - 0.08; segs = [[s, min(e, fim)] for s, e in segs if s < fim - 0.05]
        if segs and falas_hold(plano) and stem.split("_")[0] == falas_hold(plano)[0]["id"]:
            # 1ª fala da hold logo depois do hook: ~0,1 s a mais de respiro antes da 1ª palavra (o hook às vezes termina colado na
            # última palavra; ~0,05 s de silêncio = "corte estranho na voz", Fefo, BATCH#2822). Antes começava no 0 do
            # clipe, mas o Kling pode demorar ~2 s para falar = avatar congelado depois do hook (Fefo, BATCH#1977).
            segs[0][0] = round(max(0.0, segs[0][0] - 0.1), 3)
        if re.match(r"H\d", stem) and segs:
            # hook termina e a hold começa logo: sem respiro entre as frases soa como "corte na voz" (Fefo, BATCH#2822).
            # Mantém ~0,3 s do silêncio do próprio clipe depois da última palavra do hook. `respiro_hook_s` (batch.json,
            # opcional): com a borda relativa as folgas já são justas e 0,2 s a mais deixava ~0,5 s de "deadspace" (1977).
            # No Seedance o respiro não passa do limite do estalo (sem isso voltava a "duração − 0,02", BATCH#3214 H1).
            teto = duracao(mp4) - (0.08 if eh_seedance(plano, stem) else 0.02)
            segs[-1][1] = round(min(teto, segs[-1][1] + float(c.get("respiro_hook_s", 0.2))), 3)
        json.dump(segs, open(corte(B, stem), "w"))
    elif k == "previa":
        p = acao[1]; ins, fc, n = [], [], 0
        for f in falas_hold(plano):
            segs = g30(json.load(open(corte(B, fala_stem(f, p))))); i = len(ins) // 2; ins += ["-i", fala_mp4(B, f, p)]
            for q, (s, e) in enumerate(segs):
                fc.append(f"[{i}:v]{vtrim(s, e)[0]},scale=720:1280{punch(plano, q)},fps=30{push(f, segs, q)}{vtrim(s, e)[1]},setsar=1[v{n}];"
                          f"[{i}:a]atrim={s}:{e},asetpts=PTS-STARTPTS{afade(e - s)}{ganho(f, p)},aresample=44100,aformat=channel_layouts=stereo[a{n}]"); n += 1
        fc.append("".join(f"[v{j}][a{j}]" for j in range(n)) + f"concat=n={n}:v=1:a=1[v][a]")
        sc = previa(B, p) + ".fc.txt"; open(sc, "w").write(";".join(fc))
        subprocess.run([FF, "-nostdin", "-v", "error", "-y", *ins, "-filter_complex_script", sc, "-map", "[v]", "-map", "[a]",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac", "-b:a", "160k", previa(B, p)], check=True)
        os.remove(sc)
    elif k == "transcrever_hold":
        transcrever(previa(B, acao[1]), L(B, f"palavras_hold_{acao[1]}.json"))
    elif k == "transcrever_hook":
        n = acao[1]; f, pm, hs = hook_marca(plano, n, acao[2] if len(acao) > 2 else None)
        wav = f"{B}/08_auto/legendas/_{hs}_cortado.wav"
        segs = json.load(open(corte(B, fala_stem(f, pm)))); sel = "+".join(f"between(t,{s},{e})" for s, e in segs)
        subprocess.run([FF, "-nostdin", "-v", "error", "-y", "-i", fala_mp4(B, f, pm), "-vn", "-ac", "1", "-ar", "16000",
                        "-af", f"aselect='{sel}',asetpts=N/SR/TB", wav], check=True)
        transcrever(wav, L(B, f"palavras_{hs}.json")); os.remove(wav)
    elif k == "srt_hold":
        p = acao[1]; srt(L(B, f"palavras_hold_{p}.json"), texto_hold(plano, p), L(B, f"HOLD_{p}.srt"), cfg,
                         plano.get("estilo", {}).get("legenda", {}).get("inteiras", []),
                         plano.get("estilo", {}).get("legenda", {}).get("separar", []))
    elif k == "srt_hook":
        n = acao[1]; f, pm, hs = hook_marca(plano, n, acao[2] if len(acao) > 2 else None)
        srt(L(B, f"palavras_{hs}.json"), texto_hook(plano, n, pm), L(B, f"{hs}.srt"), cfg,
            plano.get("estilo", {}).get("legenda", {}).get("inteiras", []),
            plano.get("estilo", {}).get("legenda", {}).get("separar", []))
    elif k == "srt_ad":
        _, p, n = acao; f, pm, hs = hook_marca(plano, n, p); off = dur_corte(corte(B, fala_stem(f, pm)))
        # hook com texto fixo no topo: sem legenda embaixo, a não ser com estilo.legenda_no_hook ("text is not following the
        # voice" no hook só com o banner, BATCH#3214 V1)
        so_banner = str(n) in plano.get("hook_header", {}) and not plano.get("estilo", {}).get("legenda_no_hook")
        hk = [] if so_banner else ler_srt(L(B, f"{hs}.srt"))
        pl = pulo_hold(B, plano, p, n)
        bl = hk + [(max(a - pl, 0) + off, b - pl + off, t) for a, b, t in ler_srt(L(B, f"HOLD_{p}.srt")) if b - pl > 0.05]
        escrever_srt(bl, L(B, f"AD{n}_{p}.srt"))
    elif k == "montar": montar(B, acao[1], acao[2])
    elif k == "xml": gerar_xml(B)

