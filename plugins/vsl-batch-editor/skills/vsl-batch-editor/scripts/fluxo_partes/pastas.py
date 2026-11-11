# Parte do fluxo.py: motor "pastas" (status e fazer de job sem plano.json) e o comando checar. Roda no mesmo espaço de
# nomes do fluxo.py (não importar sozinho). Usa os globais da ficha: AUTO, EXPORT, CFG, ROTEIRO, REFS, AUDIO, ELEMENTOS,
# PROJETO, BRUTOS, CHECAGENS. Nomes com prefixo pj_ para não esbarrar nos do motor plano.
# ---------------------------------------------------------------- motor "pastas"
PJ_VIDEO = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi"}
PJ_IMAGEM = {".png", ".jpg", ".jpeg", ".webp", ".heic", ".gif"}
PJ_AUDIO = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".aif", ".aiff"}
PJ_IGNORA_DIR = {"__pycache__", ".git"}
PJ_IGNORA_ARQ = {".DS_Store", "checagens.json"}

def pj_arquivos(base):
    """Todos os arquivos de uma pasta (recursivo), sem lixo do sistema. Pasta que não existe = lista vazia."""
    out = []
    if os.path.isfile(base): return [base]
    for raiz, dirs, arqs in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in PJ_IGNORA_DIR)
        out += [os.path.join(raiz, f) for f in sorted(arqs) if f not in PJ_IGNORA_ARQ and not f.endswith(".pyc") and not f.startswith("._")]
    return out

def pj_pastas_de(B, nomes): return [f"{B}/{n}" for n in ([nomes] if isinstance(nomes, str) else nomes)]

def pj_exports(B):
    """(exports, antigos): MP4 de <export>/ (qualquer subpasta, menos _old*) e os arquivos de _old*/."""
    base = f"{B}/{EXPORT}"; atuais, antigos = [], []
    for arq in pj_arquivos(base):
        rel = os.path.relpath(arq, base).split(os.sep)
        if any(x.startswith("_old") for x in rel[:-1]): antigos.append(arq)
        elif arq.lower().endswith(".mp4"): atuais.append(arq)
    return atuais, antigos

def pj_insumos(B):
    """Arquivos dos quais o export depende: brutos, áudio, elementos e auto."""
    out = []
    for nome in list(BRUTOS) + [AUDIO, ELEMENTOS, AUTO]: out += pj_arquivos(f"{B}/{nome}")
    return out

def pj_desatualizado(B, mp4, insumos=None):
    """(True, arquivo_mais_novo) se algum insumo é mais novo que o export (1 s de folga, como o estado() do motor plano)."""
    t = os.path.getmtime(mp4); novo = None
    for d in (insumos if insumos is not None else pj_insumos(B)):
        m = os.path.getmtime(d)
        if m > t + 1 and (novo is None or m > os.path.getmtime(novo)): novo = d
    return (novo is not None), novo

def pj_config(B):
    arq = f"{B}/{CFG}"
    try: return json.load(open(arq, encoding="utf-8")) if os.path.exists(arq) else None
    except ValueError as e: return {"_erro": str(e)}

def pj_conta(arqs):
    v = sum(1 for x in arqs if os.path.splitext(x)[1].lower() in PJ_VIDEO)
    i = sum(1 for x in arqs if os.path.splitext(x)[1].lower() in PJ_IMAGEM)
    au = sum(1 for x in arqs if os.path.splitext(x)[1].lower() in PJ_AUDIO)
    return v, i, au

def pj_hooks_esperados(cfg):
    h = (cfg or {}).get("hooks")
    return h if isinstance(h, int) else None

def cmd_status_pastas(a):
    B = a.batch.rstrip("/")
    if not os.path.isdir(B): raise SystemExit(f"Pasta não existe: {B}")
    print(f"== {os.path.basename(B)}  ({_nome_cliente(CLIENTE)}, motor pastas)")
    prox = None
    cfg = pj_config(B)
    if cfg is None: print(f"• Config ({CFG}): falta"); prox = f"criar {CFG}"
    elif "_erro" in cfg: print(f"✖ Config ({CFG}): JSON inválido ({cfg['_erro']})"); prox = f"corrigir {CFG}"
    else:
        fm = ", ".join(f"{f.get('nome', '?')} {f.get('largura', '?')}x{f.get('altura', '?')}@{f.get('fps', '?')}" for f in cfg.get("formatos", []) if isinstance(f, dict))
        print(f"✔ Config ({CFG}): job {cfg.get('job', '?')} · marca {cfg.get('marca', '?')} · hooks {cfg.get('hooks', '?')} · formatos {fm or '?'}")
    etapas = [("Roteiro/briefing", ROTEIRO, "roteiro"), ("Refs", REFS, "refs")]
    for nome, pasta, _ in etapas:
        n = len(pj_arquivos(f"{B}/{pasta}")); print(f"{'✔' if n else '•'} {nome} ({pasta}): {n} arquivo(s)")
        if not n and not prox: prox = f"preencher {pasta}"
    brutos = [x for d in pj_pastas_de(B, BRUTOS) for x in pj_arquivos(d)]; v, i, _ = pj_conta(brutos)
    print(f"{'✔' if brutos else '•'} Brutos ({', '.join(BRUTOS)}): {v} vídeo(s), {i} imagem(ns), {len(brutos)} arquivo(s) no total")
    if not brutos and not prox: prox = "gerar ou baixar os brutos (módulos de falas e b-roll; gasta crédito: pedir ok)"
    au = pj_arquivos(f"{B}/{AUDIO}"); print(f"{'✔' if au else '•'} Áudio ({AUDIO}): {len(au)} arquivo(s)")
    if not au and not prox: prox = f"pôr o áudio em {AUDIO}"
    for nome, pasta in (("Elementos", ELEMENTOS), ("Projeto", PROJETO)):
        n = len(pj_arquivos(f"{B}/{pasta}")); print(f"{'✔' if n else '•'} {nome} ({pasta}): {n} arquivo(s)")
    mont = f"{B}/{AUTO}/montar.py"; na = len(pj_arquivos(f"{B}/{AUTO}"))
    print(f"{'✔' if os.path.exists(mont) else '•'} Auto ({AUTO}): {na} arquivo(s); montar.py {'presente' if os.path.exists(mont) else 'ausente'}")
    atuais, antigos = pj_exports(B); insumos = pj_insumos(B); velhos = 0
    print(f"{'✔' if atuais else '•'} Exports ({EXPORT}): {len(atuais)} arquivo(s)")
    for e in atuais:
        velho, novo = pj_desatualizado(B, e, insumos); velhos += velho
        print(f"     {'desatualizado' if velho else 'ok':13s} {os.path.relpath(e, f'{B}/{EXPORT}')}" + (f"   (mais novo: {os.path.relpath(novo, B)})" if velho else ""))
    if antigos: print(f"     em _old: {len(antigos)} arquivo(s)")
    esp = pj_hooks_esperados(cfg); faltam = max(0, esp - len(atuais)) if esp else 0
    if faltam: print(f"     faltam {faltam} export(s): o config pede {esp} hook(s)")
    if not prox:
        if not atuais or faltam or velhos:
            prox = (f'python3 fluxo.py fazer "{B}"  (roda {AUTO}/montar.py)' if os.path.exists(mont)
                    else f"montar à mão ({AUTO}/montar.py não existe)")
        else: prox = f'python3 fluxo.py checar "{B}"  (checagens antes de mandar ao Fefo)'
    print(f"\nPróximo: {prox}")

def cmd_fazer_pastas(a):
    B = a.batch.rstrip("/"); mont = f"{B}/{AUTO}/montar.py"
    if not os.path.isdir(B): raise SystemExit(f"Pasta não existe: {B}")
    if not os.path.exists(mont): print(f"Sem {AUTO}/montar.py neste job: nada que o `fazer` possa rodar."); return
    atuais, _ = pj_exports(B); insumos = pj_insumos(B)
    velhos = [e for e in atuais if pj_desatualizado(B, e, insumos)[0]]
    esp = pj_hooks_esperados(pj_config(B)); faltam = max(0, esp - len(atuais)) if esp else 0
    if not (atuais and not velhos and not faltam) or a.forcar:
        motivo = "sem export" if not atuais else (f"{len(velhos)} export(s) desatualizado(s)" if velhos else f"faltam {faltam} export(s)" if faltam else "forçado")
        cmd = ["python3", mont]
        print(f"→ montar ({motivo}): {' '.join(cmd)}   (cwd {B})")
        if a.teste: print("  --teste: não rodei."); return
        r = subprocess.run(cmd, cwd=B)
        if r.returncode: raise SystemExit(f"montar.py saiu com código {r.returncode}")
    else: print("Nada a fazer: todos os exports estão atualizados.")


# ---------------------------------------------------------------- checar
PJ_TODAS = ["freeze", "lascas", "ritmo", "quadros", "qc", "lint"]

def pj_uso(msg):
    """Erro de uso ou de execução do checar: mensagem no stderr e código 2 (0 = passou, 1 = checagem falhou)."""
    print(msg, file=sys.stderr); sys.exit(2)

def pj_lint(B):
    """lint_plano.py <batch>, uma vez por batch (script de outra thread; se não existir, pula e avisa)."""
    s = os.path.join(AQUI, "lint_plano.py")
    if not os.path.exists(s): return None, f"lint_plano.py não existe em {AQUI}; pulado"
    rc, saida = pj_roda([sys.executable, s, B]); linhas = [l.strip() for l in saida.strip().splitlines() if l.strip()]
    if rc not in (0, 1): return "erro", "lint_plano.py falhou (código %s): %s" % (rc, linhas[-1][:120] if linhas else "sem saída")
    return rc == 0, (linhas[-1][:200] if linhas else ("sem problemas" if rc == 0 else "lint achou problema"))

def pj_script_checagem(nome):
    """Script de checagem: scripts/checagens/<nome>.py no núcleo, ou scripts/<nome>.py na skill empacotada."""
    for d in (os.path.join(AQUI, "checagens"), AQUI):
        p = os.path.join(d, nome + ".py")
        if os.path.exists(p): return p
    return None

def pj_env():
    """Ambiente dos scripts de checagem: o PYTHONPATH enxerga os módulos do cliente (ex. alinha_palavras da Trendscale)."""
    env = dict(os.environ); extra = [p for p in sys.path if os.path.isdir(p)]
    env["PYTHONPATH"] = os.pathsep.join(extra + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    return env

def pj_roda(cmd, timeout=None):
    r = subprocess.run(cmd, capture_output=True, text=True, env=pj_env(), timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")

def pj_freeze(mp4):
    r = subprocess.run([FF, "-nostdin", "-hide_banner", "-nostats", "-i", mp4, "-an", "-vf", "freezedetect=n=0.008:d=0.4", "-f", "null", "-"],
                       capture_output=True, text=True)
    ini = re.findall(r"freeze_start: ([\d.]+)", r.stderr); dur = re.findall(r"freeze_duration: ([\d.]+)", r.stderr)
    if r.returncode and not ini: return "erro", f"ffmpeg falhou (código {r.returncode})", []
    trechos = [f"{float(s):.2f}s por {float(d):.2f}s" for s, d in zip(ini, dur)]
    if len(ini) > len(dur): trechos.append(f"{float(ini[-1]):.2f}s até o fim")      # congelou até o fim: sem freeze_duration
    return (not trechos), (f"{len(trechos)} trecho(s) congelado(s): " + "; ".join(trechos[:6]) if trechos else "nenhum quadro congelado"), trechos

def pj_posicoes(B, mp4):
    """Json de posições do b-roll do AD (motor plano: <auto>/broll_posicoes_AD<n>_<marca>.json), se existir."""
    nome = os.path.basename(mp4); m = re.search(r"AD(\d+)", nome)
    if not m or not os.path.exists(f"{B}/{AUTO}/plano.json"): return None
    try: plano = json.load(open(f"{B}/{AUTO}/plano.json"))
    except ValueError: return None
    for p in plano.get("produtos", []):
        if p.lower() in nome.lower() or marca_nome(plano, p).lower() in nome.lower():
            arq = f"{B}/{AUTO}/broll_posicoes_AD{m[1]}_{p}.json"
            if os.path.exists(arq): return arq
    return None

def pj_lascas(B, mp4, loc):
    s = pj_script_checagem("lascas")
    if not s: return "erro", "lascas.py não encontrado"
    pos = pj_posicoes(B, mp4); cmd = [sys.executable, s, loc] + ([pos] if pos else [])
    rc, saida = pj_roda(cmd); m = re.search(r"(\d+) plano\(s\) com até (\d+) quadros", saida)
    if not m: return "erro", "saída inesperada do lascas.py: " + (saida.strip().splitlines() or ["(vazia)"])[-1][:120]
    n = int(m[1]); linhas = [l.strip() for l in saida.splitlines() if "quadros" in l and "plano(s)" not in l]
    return n == 0, (f"{n} plano(s) de até {m[2]} quadros" + (": " + "; ".join(re.sub(r"\s+", " ", l.split("(antes")[0]).strip() for l in linhas[:4]) if linhas else "")
                    + (" (com posições do b-roll)" if pos and n == 0 else ""))

def pj_ritmo(B, mp4, loc):
    s = pj_script_checagem("ritmo")
    if not s: return "erro", "ritmo.py não encontrado"
    rc, saida = pj_roda([sys.executable, s, loc, "--limite", "3.0"])
    linhas = [l.strip() for l in saida.strip().splitlines()]
    if rc not in (0, 1): return "erro", "ritmo.py falhou: " + (linhas[-1][:120] if linhas else "sem saída")
    return rc == 0, (linhas[0].split(": ", 1)[-1] if linhas else "sem saída") + ("" if rc == 0 else " — " + "; ".join(linhas[1:4]))

def pj_quadros(B, mp4, loc):
    s = pj_script_checagem("conferir_quadros")
    if not s: return "erro", "conferir_quadros.py não encontrado"
    rc, saida = pj_roda([sys.executable, s, loc]); linhas = [l.strip() for l in saida.strip().splitlines() if l.strip()]
    if rc not in (0, 1): return "erro", "conferir_quadros.py falhou: " + (linhas[-1][:120] if linhas else "sem saída")
    if rc == 0: return True, "sem tela preta, plano curto, piscada nem resolução fora de 720"
    ocorr = [l for l in linhas if l.startswith(("PRETO", "CURTO", "PISCADA"))]; conta = {k: sum(1 for l in ocorr if l.startswith(k)) for k in ("PRETO", "CURTO", "PISCADA")}
    resol = next((l.replace("tem que ser 720 no lado menor", "(deve ser 720 no lado menor)") for l in linhas if l.startswith("RESOLUCAO")), None)
    partes = ([resol] if resol else []) + [f"{n} {k}" for k, n in conta.items() if n] + ([f"primeiro em {re.sub(chr(32) + '+', chr(32), ocorr[0])}"] if ocorr else [])
    return False, "; ".join(partes) or linhas[-1][:160]

def pj_acha_ass(B, mp4):
    """Legenda .ass do export: mesmo nome do vídeo (sem espaços, caixa baixa) em <auto>, <export> ou ao lado do vídeo."""
    chave = lambda p: re.sub(r"[^a-z0-9]", "", os.path.splitext(os.path.basename(p))[0].lower())
    alvo = chave(mp4)
    for base in (os.path.dirname(mp4), f"{B}/{AUTO}", f"{B}/{EXPORT}"):
        for arq in pj_arquivos(base):
            if arq.lower().endswith(".ass") and chave(arq) == alvo: return arq
    return None

def pj_qc(B, mp4, loc):
    s = pj_script_checagem("qc_export")
    if not s: return "erro", "qc_export.py não encontrado"
    ass = pj_acha_ass(B, mp4)
    if not ass: return None, f"sem .ass do export em {AUTO}/ nem ao lado do vídeo (qc_export precisa da legenda)"
    saida = os.path.join(tempfile.gettempdir(), "qc_" + re.sub(r"[^A-Za-z0-9]+", "_", os.path.splitext(os.path.basename(mp4))[0]))
    fila = os.path.expanduser("~/bin/fila.py" if os.name == "nt" else "~/bin/fila")     # no PC Windows a fila é um .py
    cmd = (([sys.executable] if os.name == "nt" else []) + [fila] if os.path.exists(fila) else []) + [sys.executable, s, loc, ass, "--saida", saida]
    voz = os.path.join(os.path.dirname(ass), "dialogo16k.wav")
    if os.path.exists(voz): cmd += ["--voz", voz]
    rc, texto = pj_roda(cmd); linhas = [l.strip() for l in texto.strip().splitlines() if l.strip()]
    if rc not in (0, 1): return "erro", "qc_export.py falhou: " + (linhas[-1][:120] if linhas else "sem saída")
    cab = [re.sub(r"\s+", " ", l.split(":")[0] + ":" + l.split(":", 1)[1].split(" (")[0])[:80] for l in texto.splitlines()
           if l and not l[0].isspace() and ":" in l and not l.startswith("Folha")]        # uma linha por seção do qc.txt
    return rc == 0, (f"qc ok (detalhes em {saida}/qc.txt)" if rc == 0 else "; ".join(cab) + f" (ver {saida}/qc.txt)")

def pj_local(mp4, pasta):
    """Cópia local do vídeo para as checagens (o Drive em streaming é lento para o ffmpeg ler quatro vezes). Mesmo nome de arquivo."""
    if "CloudStorage" not in os.path.abspath(mp4): return mp4
    os.makedirs(pasta, exist_ok=True); dst = os.path.join(pasta, os.path.basename(mp4))
    if not os.path.exists(dst) or os.path.getsize(dst) != os.path.getsize(mp4): shutil.copyfile(mp4, dst)
    return dst

PJ_FN = {"lascas": pj_lascas, "ritmo": pj_ritmo, "quadros": pj_quadros, "qc": pj_qc}

def cmd_checar(a):
    B = a.batch.rstrip("/")
    if not os.path.isdir(B): pj_uso(f"Pasta não existe: {B}")
    ficha = list(CHECAGENS) or ["freeze"]
    so = [x.strip() for x in a.so.split(",") if x.strip()] if a.so else None
    if so:
        ruim = [x for x in so if x not in PJ_TODAS]
        if ruim: pj_uso(f"Checagem desconhecida: {', '.join(ruim)}. Disponíveis: {', '.join(PJ_TODAS)}")
        fora = [x for x in so if x not in ficha]
        if fora: print(f"(aviso: {', '.join(fora)} não está na ficha de {_nome_cliente(CLIENTE)}; rodo mesmo assim)")
        ficha = so
    so_lint = ficha == ["lint"]
    if so_lint: videos = []
    elif a.videos:
        videos = []
        for v in a.videos:
            p = v if os.path.exists(v) else f"{B}/{v}"
            if not os.path.exists(p): pj_uso(f"Vídeo não existe: {v}")
            videos.append(os.path.abspath(p))
    else: videos, _ = pj_exports(B)
    if not videos and not so_lint: pj_uso(f"Sem vídeos: {EXPORT}/ não tem MP4 (fora do _old). Passe os vídeos na linha de comando.")
    print(f"== checar {os.path.basename(B)}  ({_nome_cliente(CLIENTE)}: {', '.join(ficha)})")
    resultado = []; falhas = 0; puladas = 0; erros = 0; tmp = tempfile.mkdtemp(prefix="checar_"); lint = None
    def conta(ok):
        nonlocal falhas, puladas, erros
        if ok == "erro": erros += 1
        elif ok is False: falhas += 1
        elif ok is None: puladas += 1
    def marca(ok): return "!" if ok == "erro" else "-" if ok is None else ("✔" if ok else "✖")
    if "lint" in ficha:
        ok, motivo = pj_lint(B); print(f"\nbatch\n  {marca(ok)} {'lint':8s} {motivo}", flush=True)
        lint = {"ok": ok, "motivo": motivo}; conta(ok)
    for v in videos:
        nome = os.path.relpath(v, B) if v.startswith(B + os.sep) else v
        print(f"\n{nome}", flush=True); linha = {}; loc = pj_local(v, tmp)
        for c in [x for x in ficha if x != "lint"]:
            ok, motivo = (pj_freeze(loc)[:2] if c == "freeze" else PJ_FN[c](B, v, loc))
            print(f"  {marca(ok)} {c:8s} {motivo}", flush=True)
            linha[c] = {"ok": ok, "motivo": motivo}; conta(ok)
        resultado.append({"video": v, "checagens": linha})
        if loc != v: os.remove(loc)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nResumo: {len(videos)} vídeo(s), {falhas} falha(s)" + (f", {erros} erro(s) de execução (!)" if erros else "") + (f", {puladas} checagem(ns) puladas (-)" if puladas else "")
          + (". Tudo certo; assistir no celular do começo ao fim ainda é do Fefo/revisor." if not (falhas or erros) else ""))
    if a.json:
        os.makedirs(f"{B}/{AUTO}", exist_ok=True)
        json.dump({"cliente": CLIENTE, "checagens": ficha, "lint": lint, "resultado": resultado}, open(f"{B}/{AUTO}/checagens.json", "w"), indent=1, ensure_ascii=False)
        print(f"gravei {AUTO}/checagens.json")
    sys.exit(2 if erros else 1 if falhas else 0)
