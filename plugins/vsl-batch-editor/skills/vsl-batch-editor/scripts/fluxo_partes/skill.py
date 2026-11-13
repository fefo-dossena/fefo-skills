# Parte do fluxo.py: perfil, empacotar, publicar, instalar. Roda no mesmo espaço de nomes do fluxo.py (não importar sozinho).
# ---------------------------------------------------------------- perfil de quem usa (modulos/00_configurar.md)
# <raiz>/_FLUXO_VSL (ou a pasta da skill). O atalho do cliente passa a pasta dele em FLUXO_CLIENTE; na skill empacotada o
# fluxo.py fica em <skill>/scripts/ e a pasta da skill sai de __file__.
FLUXO = globals().get("FLUXO_CLIENTE") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERFIL = f"{FLUXO}/perfil.json"
QUEM = os.path.expanduser("~/.vsl-batch-editor/raiz")                    # raiz das batches neste Mac
REPO_SKILL = os.path.expanduser("~/repos/fefo-skills")                   # repositório do plugin, fora do Drive
REPO_SKILL_URL = "https://github.com/fefo-dossena/fefo-skills.git"     # sem REPO_SKILL, o publicar clona em pasta temporária

def carregar_perfil():
    return json.load(open(PERFIL)) if os.path.exists(PERFIL) else None

def cmd_perfil(a):
    pf = carregar_perfil()
    if pf: print(f"raiz: {os.path.dirname(FLUXO)}\nperfil: {PERFIL}\n" + json.dumps(pf, indent=1, ensure_ascii=False)); return
    print(f"Sem perfil em {PERFIL} — rodar o módulo configurar (modulos/00_configurar.md) antes de tudo.")

# o que vem da skill; o resto de _FLUXO_VSL (perfil.json, CALIBRACAO.md, dia.json, old/) é de quem usa
DA_SKILL = ("SKILL.md", "modulos", "scripts")
MONITOR_NA_SKILL = ("milanote_briefing.js", "notion_cards_fefo.js", "notion_cards.js")   # o resto do monitor/ é do Fefo
PASTAS_BATCH = ("00_roteiro", "01_refs", "02_audio/trilha", "02_audio/neurobella", "02_audio/visiovance", "03_avatar/hooks",
                "03_avatar/hold", "04_broll_hold/geral", "04_broll_hold/neurobella", "04_broll_hold/visiovance",
                "05_broll_hooks/hook1", "05_broll_hooks/hook2", "05_broll_hooks/hook3", "06_elementos", "07_premiere",
                "08_auto", "09_export/neurobella", "09_export/visiovance")

def arvore(base):
    # caminhos sempre com "/": no Windows o os.walk devolve "\" e os filtros de itens_da_skill (monitor/, troca dos
    # atalhos pelo núcleo, fluxo_partes/) falhavam, mandando dados do monitor e atalhos quebrados ao GitHub (13/11/2026)
    base = base.replace("\\", "/")
    if os.path.isfile(base): yield base; return
    for raiz, dirs, arqs in os.walk(base):
        dirs[:] = [x for x in dirs if x != "__pycache__"]
        for f in arqs:
            if f not in (".DS_Store", "desktop.ini"): yield os.path.join(raiz, f).replace("\\", "/")

def itens_da_skill():
    """(origem, caminho na skill) de tudo que sai com a skill, no zip e no plugin."""
    F = FLUXO.replace("\\", "/"); R = os.path.dirname(F)                   # "/" também no Windows (ver arvore)
    rel = lambda p, b: os.path.relpath(p, b).replace("\\", "/")
    itens = [(s, rel(s, F)) for item in DA_SKILL for s in arvore(f"{F}/{item}")
             if not s.startswith(f"{F}/scripts/monitor/") or os.path.basename(s) in MONITOR_NA_SKILL]
    # Núcleo comum (@CLIENTES/_FLUXO, 09/11/2026): scripts/kie.py, scripts/fluxo.py, scripts/lascas.py e scripts/ritmo.py
    # daqui são só atalhos. Na skill vão os do núcleo (kie.py, fluxo.py + fluxo_partes/, checagens) com a ficha deste cliente
    # ao lado (scripts/clientes/), para funcionar sozinho na pasta de outra pessoa.
    nucleo = NUCLEO_DIR_PAI if os.path.exists(f"{NUCLEO_DIR_PAI}/scripts/kie.py") else os.path.join(os.path.dirname(os.path.dirname(R)), "_FLUXO")
    if os.path.exists(f"{nucleo}/scripts/kie.py"):
        troca = {"scripts/kie.py": f"{nucleo}/scripts/kie.py", "scripts/fluxo.py": f"{nucleo}/scripts/fluxo.py",
                 "scripts/lascas.py": f"{nucleo}/scripts/checagens/lascas.py", "scripts/ritmo.py": f"{nucleo}/scripts/checagens/ritmo.py",
                 "scripts/pilula.py": f"{nucleo}/scripts/pilula.py"}       # legenda padrão EV/TS (13/11/2026)
        itens = [(troca.get(rel, s), rel) for s, rel in itens if not rel.startswith("scripts/fluxo_partes/")]
        itens += [(s, "scripts/fluxo_partes/" + rel(s, f"{nucleo}/scripts/fluxo_partes")) for s in arvore(f"{nucleo}/scripts/fluxo_partes")]
        # fonte da legenda (TikTok Sans Medium, corte 36) ao lado de scripts/, onde o pilula.py procura (../fontes)
        itens += [(f"{nucleo}/fontes/{a}", f"fontes/{a}") for a in ("TikTokSans-Legenda-Medium.ttf", "TikTokSans_OFL.txt")
                  if os.path.exists(f"{nucleo}/fontes/{a}")]
        itens.append((f"{nucleo}/clientes/empire-vision.json", "scripts/clientes/empire-vision.json"))
        # checklist da Louise (Frente 4, 13/11/2026): o checar o roda quando a ficha o liga; vai em scripts/ (onde o checar procura)
        itens += [(f"{nucleo}/scripts/checagens/{a}", f"scripts/{a}") for a in
                  ("checklist.py", "notas_revisao.py", "visao.py", "visao_win.ps1", "visao.swift") if os.path.exists(f"{nucleo}/scripts/checagens/{a}")]
    return itens + [(s, "modelo/_BATCH_MODELO/" + rel(s, f"{R}/_BATCH_MODELO")) for s in arvore(f"{R}/_BATCH_MODELO")
                    if s.endswith((".md", ".txt", ".json"))]

def cmd_empacotar(a):
    """Zip da skill (claude.ai / outra pessoa), só no _FLUXO_VSL fonte da skill. Do monitor/ vão só os scripts do
    navegador que os módulos usam; o _BATCH_MODELO da raiz vai em modelo/ só com os textos. Zips anteriores vão para old/."""
    import datetime, zipfile
    if not (carregar_perfil() or {}).get("fonte_da_skill"):
        raise SystemExit("Só empacoto no _FLUXO_VSL fonte da skill (perfil com fonte_da_skill).")
    base = f"vsl-batch-editor_{datetime.date.today()}"
    os.makedirs(f"{FLUXO}/old", exist_ok=True)
    for z in glob.glob(f"{FLUXO}/*.zip"): shutil.move(z, f"{FLUXO}/old/{os.path.basename(z)}")
    nome = next(f"{base}{l}.zip" for l in ("",) + tuple("bcdefghij") if not os.path.exists(f"{FLUXO}/old/{base}{l}.zip"))
    itens = itens_da_skill()
    with zipfile.ZipFile(f"{FLUXO}/{nome}", "w", zipfile.ZIP_DEFLATED) as z:
        for s, rel in sorted(itens, key=lambda x: x[1]): z.write(s, f"vsl-batch-editor/{rel}")
    print(f"ok {FLUXO}/{nome} ({len(itens)} arquivos)")

def cmd_publicar(a):
    """Copia a skill para o repositório do plugin (~/repos/fefo-skills, fora do Drive), faz commit e push. Só no _FLUXO_VSL
    fonte da skill; leva os mesmos arquivos do zip. Quem tem o plugin com auto-update recebe depois que uma sessão abre."""
    if not (carregar_perfil() or {}).get("fonte_da_skill"):
        raise SystemExit("Só publico no _FLUXO_VSL fonte da skill (perfil com fonte_da_skill).")
    # Sem ~/repos/fefo-skills (PC Windows, 13/11/2026): clona numa pasta temporária, publica e apaga no fim, para não
    # deixar uma segunda cópia fixa do repositório na máquina. Nunca usar a cópia do marketplace do Claude.
    repo, temp = REPO_SKILL, None
    if not os.path.isdir(f"{repo}/.git"):
        temp = tempfile.mkdtemp(prefix="fefo-skills_"); repo = f"{temp}/fefo-skills"
        subprocess.run(["git", "clone", "-q", REPO_SKILL_URL, repo], check=True)
    try:
        itens = itens_da_skill()                                         # lista antes de apagar o destino
        dst = f"{repo}/plugins/vsl-batch-editor/skills/vsl-batch-editor"
        shutil.rmtree(dst, ignore_errors=True)
        for s, rel in itens:
            os.makedirs(os.path.dirname(f"{dst}/{rel}"), exist_ok=True); shutil.copy2(s, f"{dst}/{rel}")
        quem = []                                                        # PC sem identidade do git: a mesma dos commits do Mac
        if not subprocess.run(["git", "-C", repo, "config", "user.email"], capture_output=True, text=True).stdout.strip():
            quem = ["-c", "user.name=Fefo", "-c", "user.email=133016163+fefo-dossena@users.noreply.github.com"]
        def git(*x):
            r = subprocess.run(["git", "-C", repo, "-c", "core.autocrlf=input", *quem, *x], capture_output=True, text=True)
            if r.returncode: raise SystemExit(f"git {x[0]} falhou: {r.stderr.strip() or r.stdout.strip()}")
            return r.stdout.strip()
        git("add", "-A")
        if not git("status", "--porcelain"): print("ok nada mudou desde a última publicação"); return
        if getattr(a, "teste", False):
            print(git("diff", "--cached", "--stat")); print("--teste: não fiz commit nem push."); return
        git("commit", "-m", a.mensagem)
        if not git("remote"): print(f"ok commit {git('rev-parse', '--short', 'HEAD')} (sem remoto, não enviei)"); return
        git("push")
        print(f"ok publicado {git('rev-parse', '--short', 'HEAD')} ({len(itens)} arquivos)")
    finally:
        if temp: shutil.rmtree(temp, onerror=lambda f, p, e: (os.chmod(p, 0o700), f(p)))   # .git do Windows vem só-leitura

def cmd_instalar(a):
    """Monta ou atualiza <raiz>/_FLUXO_VSL e <raiz>/_BATCH_MODELO a partir da pasta da skill (rodar o fluxo.py DA SKILL).
    Copia só o que falta ou está mais velho que o da skill; arquivo mais novo aqui fica. Nunca mexe em perfil.json,
    CALIBRACAO.md, dia.json nem nas batches; do _BATCH_MODELO só acrescenta o que falta."""
    R = os.path.abspath(os.path.expanduser(a.raiz)); dst = f"{R}/_FLUXO_VSL"
    if os.path.realpath(FLUXO) == os.path.realpath(dst):
        raise SystemExit("Este fluxo.py já é o do _FLUXO_VSL da raiz: rode o fluxo.py da pasta da skill.")
    pf = f"{dst}/perfil.json"
    if os.path.exists(pf) and json.load(open(pf)).get("fonte_da_skill"):
        raise SystemExit(f"{dst} é a fonte da skill (perfil com fonte_da_skill): não atualizo a partir do zip.")
    cont = {"novo": 0, "atualizado": 0, "mantido": []}
    def copiar(s, d, sobrescrever=True):
        if os.path.exists(d):
            dt = os.path.getmtime(d) - os.path.getmtime(s)        # o Drive guarda o horário só em segundos
            if not sobrescrever or abs(dt) < 2: return
            if dt > 0: cont["mantido"].append(os.path.relpath(d, R)); return
            cont["atualizado"] += 1
        else: cont["novo"] += 1
        os.makedirs(os.path.dirname(d), exist_ok=True); shutil.copy2(s, d)
    for item in DA_SKILL:
        for s in arvore(f"{FLUXO}/{item}"): copiar(s, f"{dst}/{os.path.relpath(s, FLUXO)}")
    modelo = f"{FLUXO}/modelo/_BATCH_MODELO"
    for s in arvore(modelo) if os.path.isdir(modelo) else ():
        copiar(s, f"{R}/_BATCH_MODELO/{os.path.relpath(s, modelo)}", sobrescrever=False)
    for p in PASTAS_BATCH: os.makedirs(f"{R}/_BATCH_MODELO/{p}", exist_ok=True)
    cal = f"{dst}/CALIBRACAO.md"
    if not os.path.exists(cal): open(cal, "w").write("# Calibração (diário)\nAprendizados de cada batch, do mais novo para o mais antigo.\n")
    os.makedirs(os.path.dirname(QUEM), exist_ok=True); open(QUEM, "w").write(R + "\n")
    print(f"ok {R}: {cont['novo']} novos, {cont['atualizado']} atualizados da skill")
    for m in cont["mantido"]: print(f"  mantive (mais novo aqui que na skill): {m}")
    if not os.path.exists(pf): print(f"Falta o perfil: {pf} (módulo configurar).")

