# Parte do fluxo.py: pedidos de geração a partir do plano.json (motor plano). Roda no mesmo espaço de nomes do fluxo.py.
# ---------------------------------------------------------------- pedidos (Central, 17/11/2026)
# Substitui os scripts copiados nas batches desde 01/11 (gerar_quadros.py, gerar_clipes.py, gerar_vo.py, monta_lote.py,
# gemini_tts.py): o plano.json já diz tudo; aqui só se escreve o PEDIDOS.json do `kie.py lote`. Nada é gerado nem
# gasto por este comando: o lote roda depois do ok de crédito do Fefo, com as travas do kie.py (conta, pasta, folha de
# prompt_qa para vídeo, task.json contra cobrança dupla).
#   fluxo.py pedidos <batch> quadros [--so S01,S02] [--modelo sunburst] [--res 2K] [--ratio 9:16] [--traco pula|quadro]
#        ref "-": padrão "pula" (sem quadro, o clipe sai só de texto, como a 4377); "quadro" = quadro sem referência (3826)
#   fluxo.py pedidos <batch> clipes  [--so ...] [--dur 5]          (kling3 sem som; quadro da cena, ou só texto se ref "-")
#   fluxo.py pedidos <batch> vo --voz Sulafat [--estilo Firm] [--ritmo Natural] [--cena/--contexto/--perfil ...]
#   fluxo.py vo-clipes <batch>    clipe 720x1280 preto com a voz de cada fala (03_avatar/hooks|hold) para o montador
# Campos do plano: cenas[].frame / .motion / .ref (letras ou lista: código de personagens[].codigo, B = frasco da
# marca, C = cápsula, "-" = sem referência), .usa / .reuso (pula); falas[].texto, .marca, .reuso. {MARCA} vira o nome.

def _refs_plano(B, plano):
    R = {v["codigo"]: v["imagem"].split(" (")[0].strip() for v in plano.get("personagens", {}).values() if v.get("codigo") and v.get("imagem")}
    for k in ("W", "N", "D"):
        if k not in R:
            achado = sorted(glob.glob(f"{B}/03_avatar/personagens/{k}.png") + glob.glob(f"{B}/03_avatar/personagens/{k}_*.png"))
            if achado: R[k] = os.path.relpath(achado[0], B)
    return R


def _refs_cena(B, plano, c, p, R):
    ref = c.get("ref", "")
    if ref in ("-", None): return []
    out = []
    for k in (ref if isinstance(ref, list) else list(ref)):
        if k == "B": arq = plano.get("frascos", {}).get(p or (plano.get("produtos") or ["neurobella"])[0])
        elif k == "C": arq = plano.get("frascos", {}).get("capsula")
        else: arq = R.get(k)
        if arq and f"{B}/{arq}" not in out: out.append(f"{B}/{arq}")
    return out


def _quadro(B, c, p, plano=None):
    """Quadro da cena; sufixo da marca só quando a batch tem mais de um produto (3826: um produto, sem sufixo; 4377: dois)."""
    suf = f"_{p}" if p and len((plano or {}).get("produtos") or [p, p]) > 1 else ""
    return f"{B}/{AUTO}/quadros/{c['id']}{suf}.png"


def cmd_pedidos(a):
    B = a.batch.rstrip("/\\"); plano, _ = carregar(B)
    so = set(a.so.split(",")) if a.so else None
    prods = plano.get("produtos") or [None]
    nome = lambda p: marca_nome(plano, p or prods[0]) if (p or prods[0]) else ""
    os.makedirs(f"{B}/{AUTO}/prompts", exist_ok=True); os.makedirs(f"{B}/{AUTO}/quadros", exist_ok=True)
    ped, pulei = [], []
    if a.tipo in ("quadros", "clipes"):
        R = _refs_plano(B, plano)
        for c in plano["cenas"]:
            if c.get("usa") or c.get("reuso") or (so and c["id"] not in so): continue
            campo = "frame" if a.tipo == "quadros" else "motion"
            if campo not in c: continue
            for p in (plano.get("produtos") if tem_marca(c) else [None]):
                suf = f"_{p}" if p and len(plano.get("produtos") or []) > 1 else ""
                pt = f"{B}/{AUTO}/prompts/{c['id']}{suf}_{campo}.txt"
                if a.tipo == "quadros":
                    out = _quadro(B, c, p, plano)
                    if os.path.exists(out) and os.path.getsize(out) > 0: continue
                    if c.get("ref") == "-" and a.traco != "quadro": continue   # 4377: ref "-" = sem quadro (vídeo só de texto); 3826: --traco quadro
                    arg = [pt, out] + sum([["--ref", r] for r in _refs_cena(B, plano, c, p, R)], [])
                    arg += ["--ratio", a.ratio] + (["--res", a.res] if a.res else [])
                    cmd = a.modelo or "sunburst"
                else:
                    out = cena_mp4(B, c, p)
                    if os.path.exists(out) and os.path.getsize(out) > 0: continue
                    q = _quadro(B, c, p, plano)
                    if not os.path.exists(q) and c.get("ref") == "-": q = "-"   # sem quadro: kling só de texto
                    elif not os.path.exists(q): pulei.append(f"{c['id']}{suf} (sem quadro)"); continue
                    os.makedirs(os.path.dirname(out), exist_ok=True)
                    arg, cmd = [pt, q, out, "--dur", str(c.get("dur", a.dur)), "--sem-som"], a.modelo or "kling3"
                open(pt, "w", encoding="utf-8").write(c[campo].replace("{MARCA}", nome(p)))
                ped.append({"cmd": cmd, "args": arg})
    elif a.tipo == "vo":
        if not a.voz: sys.exit("pedidos vo pede --voz (ex.: Sulafat)")
        os.makedirs(f"{B}/02_audio/vo", exist_ok=True)
        for f in plano["falas"]:
            if f.get("reuso") or (so and f["id"] not in so): continue
            for p in (plano.get("produtos") if f.get("marca") else [None]):   # mesmo nome do montador (fala_stem)
                stem = fala_stem(f, p)
                out = f"{B}/02_audio/vo/{stem}.wav"
                if os.path.exists(out) and os.path.getsize(out) > 0: continue
                pt = f"{B}/{AUTO}/prompts/{stem}_vo.txt"
                open(pt, "w", encoding="utf-8").write(f["texto"].replace("{MARCA}", nome(p)))
                arg = [pt, out, "--voz", a.voz]
                for op in ("estilo", "ritmo", "cena", "contexto", "perfil"):
                    if getattr(a, op): arg += [f"--{op}", getattr(a, op)]
                ped.append({"cmd": "gemini-tts", "args": arg})
    saida = f"{B}/{AUTO}/pedidos_{a.tipo}.json"
    json.dump(ped, open(saida, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(ped)} pedido(s) -> {saida}")
    for x in pulei: print("  pulei:", x)
    if ped:
        print(f"Depois do ok de crédito do Fefo: python3 {os.path.join(FLUXO_CLIENTE if 'FLUXO_CLIENTE' in globals() else AQUI, 'kie.py')} lote \"{saida}\""
              " (antes: --teste)")


def cmd_vo_clipes(a):
    """Clipe preto 720x1280 com a voz de cada fala gerada (02_audio/vo/<stem>.wav -> 03_avatar/hooks|hold/<stem>.mp4)."""
    B = a.batch.rstrip("/\\"); plano, _ = carregar(B); n = 0
    for f in plano["falas"]:
        for p in (plano.get("produtos") if f.get("marca") else [None]):
            stem = fala_stem(f, p)
            wav, mp4 = f"{B}/02_audio/vo/{stem}.wav", fala_orig(B, f, p)
            if not os.path.exists(wav) or os.path.exists(mp4): continue
            os.makedirs(os.path.dirname(mp4), exist_ok=True)
            subprocess.run([FF, "-nostdin", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=black:s=720x1280:r=30",
                            "-i", wav, "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100",
                            "-ac", "2", "-b:a", "192k", mp4], check=True, timeout=900)
            n += 1; print("  ", os.path.relpath(mp4, B))
    print(f"{n} clipe(s) de voz criados")
