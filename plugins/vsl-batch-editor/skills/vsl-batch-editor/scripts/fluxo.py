#!/usr/bin/env python3
"""Fluxo modular da batch (Neurobella / VisioVance).

Tudo parte de 08_auto/plano.json. Cada arquivo esperado tem dependências; um arquivo
falta (não existe) ou está desatualizado (alguma dependência é mais nova). O `status`
mostra isso por módulo e o `fazer` roda só as etapas LOCAIS que estão pendentes, em
ordem (cortes -> prévias -> legendas -> ADs -> XML). Etapas que gastam crédito
(falas, quadros, b-roll) nunca rodam aqui: o status só lista o que falta.

Subcomandos:
  status <batch>                         o que falta / está desatualizado, e o próximo passo
  fazer  <batch> [--ate cortes|previas|legendas|ads|xml] [--so AD1_neurobella] [--forcar] [--aceitar-sem-voz]
  montar <batch> <produto> <hook>        renderiza um AD final (09_export)
  xml    <batch>                         timeline Premiere (falas em V1, b-roll em V2)
  identificar <videos...> --quadros <pasta>   casa cada vídeo baixado com o quadro inicial (1º frame)
  novo-plano <batch>                     gera um plano.json vazio a partir do roteiro.txt (para o Claude preencher)
  perfil                                 perfil de quem usa (contas, aprovador); sem perfil → módulo configurar
  instalar <raiz>                        (fluxo.py da pasta da skill) monta/atualiza <raiz>/_FLUXO_VSL e _BATCH_MODELO
  empacotar                              (só no _FLUXO_VSL do Fefo) gera o zip da skill; zips antigos vão para old/
  publicar "<mensagem>"                  (só no _FLUXO_VSL do Fefo) manda a skill para o GitHub (plugin com auto-update)
  renomear <batch>                       exports com o nome antigo (BATCH<n>_AD<k>_<p>) → nome do card, sem renderizar
"""
import argparse, difflib, glob, json, os, re, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["PATH"] = os.path.expanduser("~/bin") + os.pathsep + os.environ.get("PATH", "")
FF = shutil.which("ffmpeg") or "ffmpeg"

# ---------------------------------------------------------------- perfil de quem usa (modulos/00_configurar.md)
FLUXO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # <raiz>/_FLUXO_VSL (ou a pasta da skill)
PERFIL = f"{FLUXO}/perfil.json"
QUEM = os.path.expanduser("~/.vsl-batch-editor/raiz")                    # raiz das batches neste Mac
REPO_SKILL = os.path.expanduser("~/repos/fefo-skills")                   # repositório do plugin, fora do Drive

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
    if os.path.isfile(base): yield base; return
    for raiz, dirs, arqs in os.walk(base):
        dirs[:] = [x for x in dirs if x != "__pycache__"]
        for f in arqs:
            if f != ".DS_Store": yield os.path.join(raiz, f)

def itens_da_skill():
    """(origem, caminho na skill) de tudo que sai com a skill, no zip e no plugin."""
    R = os.path.dirname(FLUXO)
    itens = [(s, os.path.relpath(s, FLUXO)) for item in DA_SKILL for s in arvore(f"{FLUXO}/{item}")
             if not s.startswith(f"{FLUXO}/scripts/monitor/") or os.path.basename(s) in MONITOR_NA_SKILL]
    return itens + [(s, "modelo/_BATCH_MODELO/" + os.path.relpath(s, f"{R}/_BATCH_MODELO")) for s in arvore(f"{R}/_BATCH_MODELO")
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
    if not os.path.isdir(f"{REPO_SKILL}/.git"): raise SystemExit(f"Sem repositório em {REPO_SKILL}.")
    itens = itens_da_skill()                                             # lista antes de apagar o destino
    dst = f"{REPO_SKILL}/plugins/vsl-batch-editor/skills/vsl-batch-editor"
    shutil.rmtree(dst, ignore_errors=True)
    for s, rel in itens:
        os.makedirs(os.path.dirname(f"{dst}/{rel}"), exist_ok=True); shutil.copy2(s, f"{dst}/{rel}")
    git = lambda *x: subprocess.run(["git", "-C", REPO_SKILL, *x], check=True, capture_output=True, text=True).stdout.strip()
    git("add", "-A")
    if not git("status", "--porcelain"): print("ok nada mudou desde a última publicação"); return
    git("commit", "-m", a.mensagem)
    if not git("remote"): print(f"ok commit {git('rev-parse', '--short', 'HEAD')} (sem remoto, não enviei)"); return
    git("push")
    print(f"ok publicado {git('rev-parse', '--short', 'HEAD')} ({len(itens)} arquivos)")

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

# ---------------------------------------------------------------- plano e caminhos
def carregar(B):
    plano = json.load(open(f"{B}/08_auto/plano.json"))
    cfg = json.load(open(f"{B}/batch.json")) if os.path.exists(f"{B}/batch.json") else {}
    return plano, cfg

def marca_nome(plano, p): return plano.get("marca_nome", {}).get(p, p.capitalize())
def num(plano): return str(plano["batch"]).replace("BATCH_", "").replace("BATCH#", "")

def fala_stem(f, p=None):
    return f"{f['id']}_{p}" if f.get("marca") else f["id"]

def fala_orig(B, f, p=None):
    pasta = "hooks" if f["tipo"] == "hook" else "hold"
    return f"{B}/03_avatar/{pasta}/{fala_stem(f, p)}.mp4"

def fala_vel(f, p=None):
    """'velocidade' na fala do plano (número, ou {marca: número}) acelera voz + boca juntas (Fefo, BATCH#2822:
    "ela tá falando muito pausada no início"). Meta ~3,3 palavras/s."""
    v = f.get("velocidade", 1)
    if isinstance(v, dict): v = v.get(p or "", 1)
    return float(v)

def fala_mp4(B, f, p=None):
    """Clipe usado na montagem: o original, ou a cópia acelerada em 08_auto/rapido/ quando a fala tem 'velocidade'."""
    v = fala_vel(f, p)
    return fala_orig(B, f, p) if v == 1 else f"{B}/08_auto/rapido/{fala_stem(f, p)}_x{v:g}.mp4"

def corte(B, stem): return f"{B}/08_auto/cortes/{stem}.json"
def falas_hold(plano): return [f for f in plano["falas"] if f["tipo"] == "hold"]
def eh_seedance(plano, stem):
    """Clipe do Seedance (estalo no fim): pelo `modelo_clip` da fala (texto, ou {marca: texto}) quando a batch mistura
    modelos (BATCH#3219: Kling 4.0 + Seedance); sem ele, pelo `plano.modelo_falas`."""
    fid, _, p = stem.partition("_")
    f = next((x for x in plano["falas"] if x["id"] == fid), {})
    mc = f.get("modelo_clip")
    if isinstance(mc, dict): mc = mc.get(p)
    return str(mc or plano.get("modelo_falas", "")).startswith("seedance")
def fala_hook(plano, n): return next(f for f in plano["falas"] if f["tipo"] == "hook" and int(f["hook"]) == int(n))
def hooks(plano): return sorted({int(f["hook"]) for f in plano["falas"] if f["tipo"] == "hook"})

def tem_marca(c): return c["tipo"] == "produto" or bool(c.get("produto"))

def cena_mp4(B, c, p=None):
    """'usa': <id> = mesmo clipe de outra cena (2º corte do clipe ou hook repetido); hook com 'produto' = um por marca."""
    cid = c.get("usa", c["id"])
    if c["tipo"] == "hook":
        h = re.match(r"H(\d+)", cid); pasta = f"05_broll_hooks/hook{h[1] if h else c['hook']}"
        return f"{B}/{pasta}/{cid}_{c['nome']}" + (f"_{p}" if c.get("produto") and p else "") + ".mp4"
    pasta = f"04_broll_hold/{p}" if c["tipo"] == "produto" else "04_broll_hold/geral"
    return f"{B}/{pasta}/{cid}_{c['nome']}.mp4"

def cena_inicio(c):
    """Segundo de onde o corte começa dentro do clipe ('parte' b = 2º corte do mesmo clipe)."""
    return float(c.get("inicio", 2.5 if c.get("parte") == "b" else 0))

def clipe_direita(B, c, p=None):
    """Cena "formato": "split" (tela dividida, tipo B de modulos/hooks.md): clipe da metade direita (produto), caminho
    relativo à batch; "{p}" vira a marca (ex.: "05_broll_hooks/hook1/H1-01d_pote_{p}.mp4"). None se a cena não tem."""
    d = c.get("clipe_direita") if c.get("formato") == "split" else None
    return f"{B}/{d.replace('{p}', p or '')}" if d else None

def dur_util(B, c, f, p=None):
    """Segundos usáveis da cena a partir do 'inicio' (split: o mais curto dos dois clipes, sem congelar nenhum lado)."""
    d = duracao(f) - cena_inicio(c); r = clipe_direita(B, c, p)
    return min(d, duracao(r) - float(c.get("inicio_direita", 0))) if r else d

def pos_fala(c): return c.get("copy", "").startswith("(")    # ex.: "(tela final)" entra depois da última fala

def texto_hold(plano, p):
    return " ".join(plano["hold"]).replace("{MARCA}", marca_nome(plano, p))

def hook_marca(plano, n, p):
    """(fala, marca_ou_None, stem) do hook n; hook que cita a marca tem clipe/legenda por produto (H1_neurobella)."""
    f = fala_hook(plano, n); pm = p if f.get("marca") else None
    return f, pm, f"H{n}" + (f"_{pm}" if pm else "")
def hook_stems(plano, n):
    f = fala_hook(plano, n); return [(p, f"H{n}_{p}") for p in plano["produtos"]] if f.get("marca") else [(None, f"H{n}")]
def texto_hook(plano, n, p):
    return fala_hook(plano, n)["texto"].replace("{MARCA}", marca_nome(plano, p) if p else "")

def L(B, nome): return f"{B}/08_auto/legendas/{nome}"
def previa(B, p): return f"{B}/08_auto/preview_hold_{p}.mp4"
def punch(plano, i):
    """Punch-in alternado a cada corte de silêncio dentro da fala (disfarça o pulo do rosto; Frame.io BATCH_2080).
    plano.estilo.avatar.punch_in = [1.0, 1.12] e crop_y (0 = topo, 0.5 = centro) para manter o rosto no quadro."""
    av = plano.get("estilo", {}).get("avatar", {}); zs = av.get("punch_in") or [1.0]; z = zs[i % len(zs)]
    if z == 1: return ""
    return f",crop=iw/{z}:ih/{z}:(iw-iw/{z})/2:(ih-ih/{z})*{av.get('crop_y', 0.3)},scale=720:1280"
def vtrim(s, e):
    """Trecho de vídeo do clipe de 24 fps com a duração exata do atrim: pega 0,1 s a mais e corta já em 30 fps no nº de
    quadros. Só com trim={s}:{e} o vídeo acabava ~0,1 s antes do áudio e o concat deixava o último quadro do hook parado
    0,2 s na emenda hook -> hold (6 quadros; BATCH#2480). Devolve (antes, depois) do scale/fps.
    Corte a menos de 0,1 s do fim do clipe (Seedance: teto = duração - 0,08) não tem essa sobra: o trecho saía 2 quadros
    mais curto que o áudio e o AD pulava 0,1 s na emenda hook -> hold (BATCH#3215). O tpad repete o último quadro
    (no máximo os que faltam) antes do corte por quadros."""
    return (f"trim={s}:{e + 0.1:.3f},setpts=PTS-STARTPTS",
            f",tpad=stop_mode=clone:stop_duration=0.15,trim=end_frame={int((e - s) * 30 + 1e-6)}")
def g30(segs):
    """Bordas do corte na grade de 30 fps (como dur_corte e emendas_avatar já contam): atrim e trim=end_frame ficam com a
    mesma duração em todo trecho. Com s/e soltos o vídeo perdia até 1 quadro por trecho e a prévia da hold saía ~1,3 s
    mais curta que o áudio (46 falas, BATCH#2481)."""
    return [(round(s * 30) / 30, round(e * 30) / 30) for s, e in segs if round(e * 30) > round(s * 30)]
def push(f, segs, q, cy=0.3):
    """Push-in contínuo na fala com pouco movimento (plano aberto do casal: freezedetect acusava 0,4-1,4 s; BATCH#2480).
    falas[i].push_in = zoom por segundo (0.02 = 2%/s, como o end card), contínuo de um corte de silêncio para o outro.
    Zoom em subpixel (perspective com interpolação cúbica, depois do fps=30: t = in/30). O scale eval=frame + crop
    andava em pixel inteiro: a médica ficava parada ~10 quadros e pulava 3 px ("why are the doctor videos shaking",
    BATCH#3214 V1)."""
    r = float(f.get("push_in") or 0)
    if not r: return ""
    k = f"{r}*({sum(e - s for s, e in segs[:q]):.3f}+in/30)"
    x0, y0, w, h = f"360*{k}/(1+{k})", f"1280*{k}*{cy}/(1+{k})", f"720/(1+{k})", f"1280/(1+{k})"
    return (f",perspective=x0='{x0}':y0='{y0}':x1='{x0}+{w}':y1='{y0}':x2='{x0}':y2='{y0}+{h}':"
            f"x3='{x0}+{w}':y3='{y0}+{h}':interpolation=cubic:eval=frame")
def card(B, plano):
    """Título exato do card no Notion: batch.json → "card"; sem ele, "BATCH#<n> - <titulo>" (é o card nas batches novas).
    Só troca o que não pode em nome de arquivo (/ : * ? " < > | \\) por "-"."""
    cfg = json.load(open(f"{B}/batch.json")) if os.path.exists(f"{B}/batch.json") else {}
    t = (cfg.get("card") or "").strip()
    if not t and (cfg.get("titulo") or "").strip() and not cfg["titulo"].startswith("Nome do Ad"):
        t = f"BATCH#{num(plano)} - {cfg['titulo'].strip()}"
    return re.sub(r'[\\/:*?"<>|]', "-", t)
def export_antigo(B, plano, p, n): return f"{B}/09_export/{p}/BATCH{num(plano)}_AD{n}_{p}.mp4"
def export(B, plano, p, n):
    """Nome do AD = título do card + marca + AD (regra do Fefo, 23/10/2026):
    "BATCH#3215 - Thinning Shield - Macular Degeneration - L2 - Problem Aware - Daniel - Neurobella - AD1.mp4".
    Sem título do card no batch.json, o nome antigo (BATCH<n>_AD<k>_<p>.mp4)."""
    c = card(B, plano)
    if not c: return export_antigo(B, plano, p, n)
    m = plano.get("marca_nome", {}).get(p) or {"neurobella": "Neurobella", "visiovance": "VisioVance"}.get(p, p.capitalize())
    return f"{B}/09_export/{p}/{c} - {m} - AD{n}.mp4"
def tira_export_antigo(B, plano, p, n):
    """Depois de renderizar com o nome do card, o arquivo do nome antigo é o mesmo AD desatualizado: sai, para não subir
    duplicado no Frame.io (a versão anterior de uma revisão já foi guardada em 09_export/_old/V<k>/)."""
    a = export_antigo(B, plano, p, n)
    if a != export(B, plano, p, n) and os.path.exists(a): os.remove(a); print(f"   saiu o nome antigo {os.path.basename(a)}")
def cmd_renomear(a):
    """Exports já renderizados com o nome antigo → nome do card, sem renderizar de novo (só 09_export/<p>/, não o _old/)."""
    B = a.batch.rstrip("/"); plano, _ = carregar(B)
    if not card(B, plano): raise SystemExit('Sem o título do card: ponha "card" no batch.json (copiado do Notion).')
    for p in plano["produtos"]:
        for n in range(1, 10):
            de, para = export_antigo(B, plano, p, n), export(B, plano, p, n)
            if os.path.exists(de) and not os.path.exists(para): os.rename(de, para); print(f"ok {os.path.basename(para)}")
def xmlpath(B, plano): return f"{B}/08_auto/BATCH{num(plano)}_premiere.xml"

# ---------------------------------------------------------------- grafo de dependências
def itens(B):
    """Lista de (etapa, alvo, deps, acao, rotulo). acao=None -> etapa que gasta crédito (só listar)."""
    plano, cfg = carregar(B); P = plano["produtos"]; PL = f"{B}/08_auto/plano.json"; out = []
    if plano.get("one_take"):                              # AD = um take contínuo por marca (umtake.py)
        import umtake; return umtake.itens(sys.modules[__name__], B, plano)
    for f in plano["falas"]:
        for p in (P if f.get("marca") else [None]):
            out.append(("falas", fala_orig(B, f, p), [], None, fala_stem(f, p)))
            if fala_vel(f, p) != 1:
                out.append(("cortes", fala_mp4(B, f, p), [fala_orig(B, f, p)],
                            ("rapido", fala_orig(B, f, p), fala_mp4(B, f, p), fala_vel(f, p)), fala_stem(f, p) + " acelerada"))
            m = f"{B}/08_auto/cortes/{fala_stem(f, p)}.manual.json"
            out.append(("cortes", corte(B, fala_stem(f, p)), [fala_mp4(B, f, p)] + ([m] if os.path.exists(m) else []),
                        ("corte", fala_mp4(B, f, p), fala_stem(f, p)), fala_stem(f, p)))
    for c in plano["cenas"]:
        if c.get("usa"): continue
        for p in (P if tem_marca(c) else [None]):
            out.append(("broll", cena_mp4(B, c, p), [], None, c["id"] + (f" {p}" if p else "")))
    dirs = {}                                              # metade direita das cenas "split"
    for c in plano["cenas"]:
        for p in P:
            r = clipe_direita(B, c, p)
            if r: dirs.setdefault(r, f"{c['id']} direita" + (f" {p}" if "{p}" in c["clipe_direita"] else ""))
    out += [("broll", r, [], None, rot) for r, rot in dirs.items()]
    for p in P:
        hc = [corte(B, fala_stem(f, p)) for f in falas_hold(plano)]
        out.append(("previas", previa(B, p), hc, ("previa", p), f"hold {p}"))
        out.append(("legendas", L(B, f"palavras_hold_{p}.json"), [previa(B, p)], ("transcrever_hold", p), f"palavras hold {p}"))
        out.append(("legendas", L(B, f"HOLD_{p}.srt"), [L(B, f"palavras_hold_{p}.json"), PL], ("srt_hold", p), f"legenda hold {p}"))
    for n in hooks(plano):
        f = fala_hook(plano, n)
        for pm, hs in hook_stems(plano, n):
            rot = f"hook {n}" + (f" {pm}" if pm else "")
            out.append(("legendas", L(B, f"palavras_{hs}.json"), [corte(B, fala_stem(f, pm))], ("transcrever_hook", n, pm), f"palavras {rot}"))
            out.append(("legendas", L(B, f"{hs}.srt"), [L(B, f"palavras_{hs}.json"), PL], ("srt_hook", n, pm), f"legenda {rot}"))
    for p in P:
        for n in hooks(plano):
            f, pm, hs = hook_marca(plano, n, p)
            out.append(("legendas", L(B, f"AD{n}_{p}.srt"), [L(B, f"HOLD_{p}.srt"), L(B, f"{hs}.srt"), corte(B, fala_stem(f, pm))],
                        ("srt_ad", p, n), f"legenda AD{n} {p}"))
            dep = [previa(B, p), L(B, f"AD{n}_{p}.srt"), L(B, f"palavras_hold_{p}.json"), L(B, f"palavras_{hs}.json"),
                   fala_mp4(B, f, pm), corte(B, fala_stem(f, pm)), PL, f"{B}/batch.json"]
            dep += sorted({cena_mp4(B, c, p if tem_marca(c) else None) for c in plano["cenas"]
                           if c["tipo"] != "hook" or int(c["hook"]) == n})
            dep += sorted({clipe_direita(B, c, p) for c in plano["cenas"] if clipe_direita(B, c, p)
                           and (c["tipo"] != "hook" or int(c["hook"]) == n)})
            dep += sorted(glob.glob(f"{B}/02_audio/trilha/*.mp3") + glob.glob(f"{B}/02_audio/trilha/*.wav"))
            out.append(("ads", export(B, plano, p, n), dep, ("montar", p, n), f"AD{n}_{p}"))
    dx = [corte(B, fala_stem(f, p)) for f in plano["falas"] for p in (P if f.get("marca") else [None])]
    out.append(("xml", xmlpath(B, plano), dx + [PL], ("xml",), "XML Premiere"))
    return out

def estado(alvo, deps):
    if not os.path.exists(alvo): return "bloqueado" if any(not os.path.exists(d) for d in deps) else "falta"
    t = os.path.getmtime(alvo)
    for d in deps:
        if not os.path.exists(d): return "bloqueado"
        if os.path.getmtime(d) > t + 1: return "desatualizado"
    return "ok"

ORDEM = ["falas", "broll", "cortes", "previas", "legendas", "ads", "xml"]
NOMES = {"falas": "Falas do avatar (Kling, gasta crédito)", "broll": "B-roll (quadros + Kling, gasta crédito)",
         "cortes": "Cortes de silêncio", "previas": "Prévias da hold", "legendas": "Transcrição e legendas",
         "ads": "ADs finais (09_export)", "xml": "XML para o Premiere"}

PICO_MIN_DB = -20

def pico_voz(mp4):
    """Pico do áudio do clipe em dB, sem os 0,25 s iniciais (clique do Kling) e os 0,1 s finais (estalo do Seedance), que
    disfarçariam um clipe mudo. −99 = sem áudio. Cache fora do Drive por caminho, data e tamanho: o status passa por
    todos os clipes e reler cada um dali leva segundos."""
    import numpy as np
    st = os.stat(mp4); chave = f"{os.path.realpath(mp4)}|{st.st_mtime}|{st.st_size}"
    cache = os.path.join(tempfile.gettempdir(), "vsl_picos.json")
    try: picos = json.load(open(cache))
    except (OSError, ValueError): picos = {}
    if chave in picos: return picos[chave]
    raw = subprocess.run([FF, "-nostdin", "-v", "error", "-i", mp4, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True).stdout
    a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768; x = a[4000:-1600]
    if not len(x): x = a
    picos[chave] = round(float(20 * np.log10(np.abs(x).max() + 1e-9)), 1) if len(x) else -99.0
    tmp = f"{cache}.{os.getpid()}"; json.dump(picos, open(tmp, "w")); os.replace(tmp, cache)
    return picos[chave]

def falas_sem_voz(B):
    """[(fala, motivo)] de cada fala que sumiria do AD sem nenhum erro: corte vazio ou clipe quase mudo. BATCH#3378 V1:
    guia de voz a −30 dB, clipe do Seedance com pico de −28 dB, corte [] e "Cocoa? Like hot chocolate?" fora dos 6 ADs."""
    out = []
    for et, alvo, deps, acao, rot in itens(B):
        if et != "cortes" or not acao or acao[0] not in ("corte", "corte_take"): continue
        motivos = []
        if os.path.exists(acao[1]):
            pk = pico_voz(acao[1])
            if pk < PICO_MIN_DB: motivos.append(f"clipe quase mudo (pico {pk:g} dB, mínimo {PICO_MIN_DB})")
        if os.path.exists(alvo):
            d = json.load(open(alvo))
            if not (d.get("segs") if isinstance(d, dict) else d): motivos.append(f"corte vazio ({os.path.basename(alvo)} = [])")
        if motivos: out.append((rot, "; ".join(motivos)))
    return out

def avisar_sem_voz(mudas):
    print(f"\n✖ Fala sem voz: {len(mudas)} (sairia do AD sem aviso)")
    for rot, motivo in mudas: print(f"     {rot}: {motivo}")

def cmd_status(a):
    B = a.batch.rstrip("/"); its = itens(B); grupos = {}
    for et, alvo, deps, acao, rot in its: grupos.setdefault(et, []).append((estado(alvo, deps), rot, deps))
    print(f"== {os.path.basename(B)}")
    prox = None
    pf = carregar_perfil()
    if pf: print(f"✔ Perfil: {pf.get('nome', '?')} (OK dos exports: {pf.get('aprovador', '?')})")
    else: print("• Perfil: falta — rodar o módulo configurar"); prox = "configurar"
    plano, _ = carregar(B); e = plano.get("estilo")
    if e: print(f"✔ Estilo do ad (de {e.get('fonte', '01_refs')}): avatar {'P&B' if e.get('avatar', {}).get('pb') else 'colorido'}, "
                f"b-roll {e.get('broll', {}).get('layout', '?')}, legenda {e.get('legenda', {}).get('estilo', '?')}")
    else: print("• Estilo do ad: falta — rodar o módulo referencia (analisa 01_refs/ desta batch)"); prox = prox or "referencia"
    for et in ORDEM:
        g = grupos.get(et, []); ok = sum(1 for s, *_ in g if s == "ok")
        pend = [(s, r) for s, r, _ in g if s != "ok"]
        print(f"{'✔' if not pend else '•'} {NOMES[et]}: {ok}/{len(g)}")
        for s, r in pend[:12]: print(f"     {s:13s} {r}")
        if len(pend) > 12: print(f"     … e mais {len(pend)-12}")
        if pend and not prox: prox = et
    mudas = falas_sem_voz(B)
    if mudas: avisar_sem_voz(mudas); print("\nPróximo: refazer essas falas (conferir a guia de voz) antes de montar; o `fazer` para nos cortes até lá.")
    elif not prox: print("\nTudo pronto e atualizado.")
    elif prox == "configurar": print("\nPróximo: módulo 'configurar' (modulos/00_configurar.md) — perguntas de início desta pessoa, antes de qualquer outro.")
    elif prox == "referencia": print("\nPróximo: módulo 'referencia' — definir o estilo a partir de 01_refs/ antes de planejar cenas ou montar.")
    elif prox in ("falas", "broll"): print(f"\nPróximo: módulo '{prox}' (gera no Kie; pedir ok de crédito antes).")
    else: print(f"\nPróximo: python3 fluxo.py fazer \"{B}\"  (roda {prox} e o que vier depois, só o necessário)")

def cmd_fazer(a):
    B = a.batch.rstrip("/"); ate = ORDEM.index(a.ate) if a.ate else len(ORDEM) - 1
    for et in ORDEM[2:ate + 1]:
        for e2, alvo, deps, acao, rot in itens(B):        # recalcula a cada etapa (mtimes mudam)
            if e2 != et or acao is None: continue
            if a.so and a.so not in (rot.replace(" ", "_"), os.path.basename(alvo)) and et == "ads": continue
            s = estado(alvo, deps)
            if s == "bloqueado": print(f"  pulei {rot}: falta insumo"); continue
            if s == "ok" and not a.forcar: continue
            print(f"→ {et}: {rot} ({s})"); executar(B, acao)
        mudas = falas_sem_voz(B) if et == "cortes" else None
        if mudas:
            avisar_sem_voz(mudas)
            if not a.aceitar_sem_voz: raise SystemExit("\nParei antes das prévias: refazer essas falas (ou --aceitar-sem-voz, se for de propósito).")

def bordas_no_silencio(mp4, segs, alto=-50, quieto=-52, busca=0.25, rel=None):
    """Emenda que cai em cima da voz soa como corte ("cortes na voz", Fefo, BATCH#2822): cada início recua e cada fim
    avança até o ponto silencioso mais próximo (janela de 20 ms abaixo de `quieto` dB), no máximo `busca` s, sem
    invadir o trecho vizinho. Vale para corte automático e manual.
    `rel` (batch.json corte_silencio.borda_relativa_db, opcional): silêncio = piso de ruído do clipe + `rel` dB, e não
    −52 fixo. Kling no carro (BATCH#1977) tem piso de −39 a −45 dB: com −52 toda borda andava os 0,25 s inteiros e as
    pausas viravam ~0,65 s ("deadspace", Frame.io 16/10)."""
    import numpy as np
    raw = subprocess.run([FF, "-nostdin", "-v", "error", "-i", mp4, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True).stdout
    a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768; sr, w = 16000, 320
    dur = len(a) / sr
    if rel is not None:
        n = len(a) // w; env = 20 * np.log10(np.sqrt((a[:n * w].reshape(n, w) ** 2).mean(1)) + 1e-9)
        piso = float(np.percentile(env, 10)); quieto, alto = piso + rel, piso + rel + 5
    def nivel(t, lado):            # lado -1: janela antes de t; +1: janela depois de t
        i = int(t * sr); x = a[max(0, i - w):i] if lado < 0 else a[i:i + w]
        return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9) if len(x) else -99
    out = []
    for k, (s, e) in enumerate(segs):
        lim_s = out[-1][1] if out else 0.0
        lim_e = segs[k + 1][0] if k + 1 < len(segs) else dur
        if nivel(s, 1) > alto:
            t = s
            while t - 0.01 >= max(lim_s, s - busca) and nivel(t, 1) > quieto: t -= 0.01
            s = t
        if nivel(e, -1) > alto:
            t = e
            while t + 0.01 <= min(lim_e, e + busca) and nivel(t, -1) > quieto: t += 0.01
            e = t
        out.append([round(s, 3), round(e, 3)])
    return out

def ganho(f, p=None):
    """`ganho_db` na fala do plano (número, ou {marca: número}): só ganho, sem EQ, para igualar o loudness das falas
    (BATCH#3219: Kling 4.0 a −13/−15 LUFS e Seedance a −19/−21 na mesma hold = "o volume da loc muda da metade da hold
    em diante", Fefo). Nada de highshelf: soou distorcido na 2822 (memória do Fefo)."""
    g = f.get("ganho_db", 0)
    if isinstance(g, dict): g = g.get(p or "", 0)
    return f",volume={float(g):.2f}dB" if g else ""

def afade(d):
    """Fade de 8 ms nas pontas de cada trecho de fala: emenda sem clique."""
    f = 0.008
    return f",afade=t=in:d={f},afade=t=out:st={max(0, d - f):.3f}:d={f}"

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

def transcrever(midia, out):
    import vsl
    class A: pass
    a = A(); a.midia, a.out, a.lang, a.modelo = midia, out, "en", "small"; vsl.cmd_transcrever(a)

norm1 = lambda w: re.sub(r"[^a-z0-9']", "", w.lower().replace("’", "'"))

def alinhar(palavras, texto):
    """Tempos da transcrição + grafia do roteiro. Retorna [(token_roteiro, s, e)]."""
    toks = texto.split(); A = [norm1(t) for t in toks]; Bw = [norm1(p["w"]) for p in palavras]
    tempos = [None] * len(toks); sm = difflib.SequenceMatcher(None, A, Bw, autojunk=False)
    for op, a1, a2, b1, b2 in sm.get_opcodes():
        if op == "equal" or (op == "replace" and a2 - a1 == b2 - b1):
            for k in range(a2 - a1): tempos[a1 + k] = (palavras[b1 + k]["s"], palavras[b1 + k]["e"])
        elif op == "replace" and b2 > b1:   # tamanhos diferentes: distribui o intervalo
            s0, e0 = palavras[b1]["s"], palavras[b2 - 1]["e"]; d = (e0 - s0) / (a2 - a1)
            for k in range(a2 - a1): tempos[a1 + k] = (s0 + k * d, s0 + (k + 1) * d)
    for i in range(len(tempos)):          # palavras do roteiro sem tempo: encosta na vizinha
        if tempos[i] is None:
            prev = next((tempos[j] for j in range(i - 1, -1, -1) if tempos[j]), (0, 0))
            tempos[i] = (prev[1], prev[1] + 0.2)
    return [(t, s, e) for t, (s, e) in zip(toks, tempos)]

# Palavras que não devem terminar um bloco de legenda (puxam a próxima): artigos, preposições, conectivos, pronomes.
FRACAS = set("a an the to of in on at for with by from and or but so if as that than then i i'm i've you you're your "
             "my his her our their its it's is are was were be been get got gonna going will can just up plus about into like "
             "because".split())
# Palavras que não devem ABRIR um bloco (pertencem à anterior): partículas, advérbios de lugar, objetos curtos.
PRESAS = set("off below above back out up down over away again too it them me him us percent prize".split())
# Quebrar ANTES destas é natural (início de expressão): ganha bônus.
ABREM = set("to with so and but or because that which who when if plus for from like until".split())

def srt(palavras_json, texto, out, cfg, inteiras=(), separar=()):
    """Legenda por EXPRESSÕES completas (regra fixa, todas as batches):
    - corta primeiro em fim de frase, vírgula e pausa (>0,6 s); dentro de cada trecho escolhe as quebras mais
      equilibradas (programação dinâmica), sem terminar bloco em palavra fraca ("a", "the", "to"...);
    - max_caracteres é a meta, não um teto: pode passar até ~1,5x para manter a expressão inteira;
    - max_palavras (padrão 7, SOP do Daniel) é teto: só uma expressão de `inteiras` passa dele;
    - bloco de 1 palavra ou muito curto (<0,8 s ou <=8 caracteres) é juntado ao vizinho;
    - inteiras = expressões que nunca se quebram, nem em fim de frase (plano.estilo.legenda.inteiras: "National Eye
      Institute", "Lutein. 7 out of 10", BATCH#3214);
    - separar = lista que sai um bloco por item, quebrando em cada " | " e no fim, sem juntar ao vizinho
      (plano.estilo.legenda.separar: "Years of sunlight, | screens, | headlights | and reading,", Frame.io "split
      sunlight and screens", BATCH#3215)."""
    maxc = cfg.get("legenda", {}).get("max_caracteres", 22); teto = round(maxc * 1.5)
    maxp = cfg.get("legenda", {}).get("max_palavras", 7)
    W = [{"t": re.sub(r"[.,!;:]+$", "", t), "fim": bool(re.search(r"[.?!]$", t)), "virg": bool(re.search(r"[,;:]$", t)), "dp": t.endswith(":"),
          "s": s, "e": e} for t, s, e in alinhar(json.load(open(palavras_json)), texto)]
    txt = lambda b: " ".join(y["t"] for y in b)
    for x in inteiras:                                      # "liga" = não quebrar depois desta palavra
        q = [norm1(y) for y in x.split()]
        for k in range(len(W) - len(q) + 1):
            if [norm1(y["t"]) for y in W[k:k + len(q)]] == q:
                for y in W[k:k + len(q) - 1]: y["liga"] = True
    for x in separar:                                       # "sep" = sempre quebra depois desta palavra e não junta
        partes = [[norm1(y) for y in p.split()] for p in x.split("|")]; q = sum(partes, [])
        fins = [sum(len(p) for p in partes[:j + 1]) - 1 for j in range(len(partes))]
        for k in range(len(W) - len(q) + 1):
            if [norm1(y["t"]) for y in W[k:k + len(q)]] == q:
                for f in fins: W[k + f]["sep"] = True
    trechos, cur = [], []
    for k, x in enumerate(W):
        cur.append(x); nx = W[k + 1] if k + 1 < len(W) else None
        if nx is None or ((x["fim"] or x["virg"] or x.get("sep") or nx["s"] - x["e"] > 0.6) and not x.get("liga")):
            trechos.append(cur); cur = []
    def custo(b):
        L = len(txt(b))
        if b[-1].get("liga"): return 1e9
        if len(b) > maxp: return 1e7 * (len(b) - maxp)
        if L > teto and len(b) > 1: return 1e6 * (L - teto)     # só vence quando uma expressão inteira passa do teto
        c = 40 + 2 * max(0, L - maxc) ** 2 + 0.3 * max(0, maxc - L) ** 2
        if len(b) == 1: c += 2000
        if norm1(b[-1]["t"]) in FRACAS and not (b[-1]["fim"] or b[-1]["virg"]): c += 400
        return c
    bl = []
    for t in trechos:
        if len(txt(t)) <= maxc * 1.25 and len(t) <= maxp: bl.append(t); continue
        m = len(t); dp = [0] + [1e18] * m; de = [0] * (m + 1)
        for a in range(1, m + 1):
            for b0 in range(max(0, a - 12), a):
                v = dp[b0] + custo(t[b0:a]) + (300 if a < m and norm1(t[a]["t"]) in PRESAS else 0) \
                    - (80 if a < m and norm1(t[a]["t"]) in ABREM else 0)
                if v < dp[a]: dp[a], de[a] = v, b0
        cortes, a = [], m
        while a > 0: cortes.append((de[a], a)); a = de[a]
        bl += [t[x:y] for x, y in reversed(cortes)]
    curto = lambda b: len(b) == 1 or b[-1]["e"] - b[0]["s"] < 0.8 or len(txt(b)) <= 8
    mudou = True
    while mudou and len(bl) > 1:                            # junta blocos curtos ao vizinho que couber melhor
        mudou = False
        for i, b in enumerate(bl):
            if not curto(b): continue
            # (fim de frase, cruza vírgula, tamanho, índice): entre os dois vizinhos, prefere o que NÃO junta por cima de
            # vírgula ("If the page blurs when you read," e não "when you read if headlights", BATCH#3215)
            opc = []
            if i > 0: opc.append((bl[i - 1][-1]["fim"], bl[i - 1][-1]["virg"], len(txt(bl[i - 1] + b)), i - 1))
            if i + 1 < len(bl): opc.append((b[-1]["fim"], b[-1]["virg"], len(txt(b + bl[i + 1])), i))
            # sobra miúda (<= 8 caracteres, "for you") cabe até 4 caracteres além do teto (BATCH#3215)
            lim = teto + (4 if len(txt(b)) <= 8 else 0)
            opc = [o for o in opc if o[2] <= lim and not o[0]]    # nunca junta por cima de fim de frase (BATCH#2820)
            opc = [o for o in opc if len(bl[o[3]]) + len(bl[o[3] + 1]) <= maxp]
            # nem por cima de dois-pontos ("...in 1998: nitric oxide" = 2 blocos, Frame.io "split", BATCH#2822)
            # nem por cima de item do `separar` (BATCH#3215)
            opc = [o for o in opc if not bl[o[3]][-1].get("dp") and not bl[o[3]][-1].get("sep")]
            if not opc: continue
            k = min(opc)[3]; bl[k:k + 2] = [bl[k] + bl[k + 1]]; mudou = True; break
    B2 = [[b[0]["s"], b[-1]["e"], txt(b)] for b in bl]
    for i in range(len(B2) - 1):
        if B2[i + 1][0] - B2[i][1] < 0.3: B2[i][1] = B2[i + 1][0]
    # fala de uma palavra que não pode juntar ao vizinho (fim de frase: "Yeah?", "Right?", troca de quem fala no diálogo,
    # BATCH#2480) piscava 0,2 s: fica no mínimo 0,7 s na tela, sem invadir o bloco seguinte
    for i in range(len(B2)):
        if B2[i][1] - B2[i][0] < 0.7:
            B2[i][1] = round(min(B2[i][0] + 0.7, B2[i + 1][0] if i + 1 < len(B2) else B2[i][0] + 0.7), 3)
    escrever_srt(B2, out)

def ts(t): return "%02d:%02d:%02d,%03d" % (t // 3600, t % 3600 // 60, t % 60, round((t % 1) * 1000) % 1000)
def escrever_srt(bl, out): open(out, "w").write("\n".join(f"{i+1}\n{ts(a)} --> {ts(b)}\n{t}\n" for i, (a, b, t) in enumerate(bl)))
def ler_srt(p):
    out = []
    for b in open(p).read().strip().split("\n\n"):
        ln = b.splitlines(); a, z = ln[1].split(" --> ")
        f = lambda s: int(s[:2]) * 3600 + int(s[3:5]) * 60 + int(s[6:8]) + int(s[9:]) / 1000
        out.append((f(a), f(z), " ".join(ln[2:])))
    return out
def tmp_montar(B, nome="_tmp_montar"):
    """Intermediários da montagem fora do Drive (não sincroniza, não dá timeout entre sessões); apagados no fim do AD."""
    return os.path.join(tempfile.gettempdir(), "vsl_montar", re.sub(r"[^\w-]", "_", os.path.basename(B.rstrip("/"))), nome)
def dur_corte(p): return sum(round(e * 30) - round(s * 30) for s, e in json.load(open(p))) / 30
def duracao(p):
    o = subprocess.run([FF, "-i", p], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", o); return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])

# ---------------------------------------------------------------- posição do b-roll
def emendas_reais(mp4, aprox):
    """Onde cada emenda prevista (s, relativo ao mp4) cai de fato no grid de 30 fps: o quadro de maior diferença a ±4
    quadros do previsto. Trecho de clipe de 24 fps vira 30 fps arredondando para um lado ou outro e o erro acumula
    (até 2 quadros na BATCH#1977). Sem o vídeo, fica a previsão."""
    import numpy as np
    if not aprox or not os.path.exists(mp4): return list(aprox)
    raw = subprocess.run([FF, "-nostdin", "-v", "error", "-i", mp4, "-vf", "fps=30,scale=90:160,format=gray", "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, 160, 90); out = []
    for t in aprox:
        k = int(round(t * 30)); lo, hi = max(1, k - 4), min(len(fr) - 1, k + 4)
        if hi < lo: out.append(t); continue
        d = [np.abs(fr[j].astype(np.int16) - fr[j - 1]).mean() for j in range(lo, hi + 1)]
        out.append(round((lo + int(np.argmax(d))) / 30, 3))
    return out

def pulo_hold(B, plano, p, n):
    """Segundos do começo da hold que o AD<n> pula: falas com `pular_hooks` contendo n, só no começo da hold (BATCH#3375:
    a F01 'He started taking...' sai nos hooks 2 e 3, que já dizem que ele começou a tomar)."""
    if n is None: return 0.0
    d = lambda s, e: (round(e * 30) - round(s * 30)) / 30; t = 0.0
    for fa in falas_hold(plano):
        if int(n) not in [int(x) for x in fa.get("pular_hooks", [])]: break
        t += sum(d(s, e) for s, e in json.load(open(corte(B, fala_stem(fa, p if fa.get("marca") else None)))))
    return round(t, 6)

def emendas_avatar(B, plano, p, n, HD):
    """Emendas do avatar na linha do tempo do AD: cortes do hook, hook -> hold, cortes e trocas de fala da hold."""
    f, pm, _ = hook_marca(plano, n, p)
    d = lambda s, e: (round(e * 30) - round(s * 30)) / 30
    hs = json.load(open(corte(B, fala_stem(f, pm)))); hk = [sum(d(s, e) for s, e in hs[:i]) for i in range(1, len(hs))]
    hd, t = [], 0.0
    for fa in falas_hold(plano):
        for s, e in json.load(open(corte(B, fala_stem(fa, p if fa.get("marca") else None)))): t += d(s, e); hd.append(t)
    pl = pulo_hold(B, plano, p, n)
    return (emendas_reais(f"{tmp_montar(B)}/hook{n}.mp4", hk) + [HD]
            + [HD + x - pl for x in emendas_reais(previa(B, p), hd[:-1]) if x - pl > 1e-3])

def segmentos(B, p, n):
    """[(cena, inicio, fim, arquivo)] na linha do tempo do AD (hook + hold)."""
    plano, _ = carregar(B); f, pm, hs = hook_marca(plano, n, p)
    hk = alinhar(json.load(open(L(B, f"palavras_{hs}.json"))), texto_hook(plano, n, p))
    hd = alinhar(json.load(open(L(B, f"palavras_hold_{p}.json"))), texto_hold(plano, p))
    HD = dur_corte(corte(B, fala_stem(f, pm)))
    def achar(tl, copy, i0):
        alvo = [norm1(w) for w in copy.replace("{MARCA}", marca_nome(plano, p)).split() if norm1(w)]
        toks = [norm1(t) for t, _, _ in tl]
        for k in range(i0, len(toks) - len(alvo) + 1):
            if toks[k:k + len(alvo)] == alvo: return tl[k][1], tl[k + len(alvo) - 1][2], k + len(alvo)
        m = difflib.SequenceMatcher(None, toks[i0:], alvo, autojunk=False).find_longest_match(0, len(toks) - i0, 0, len(alvo))
        if m.size >= max(2, len(alvo) // 2):
            k = i0 + m.a - m.b; k = max(i0, k); kk = min(len(tl) - 1, k + len(alvo) - 1); return tl[k][1], tl[kk][2], kk + 1
        raise SystemExit(f"Não achei a copy da cena na fala: {copy!r}")
    raw, i0 = [], 0
    for c in plano["cenas"]:
        if c["tipo"] == "hook" and int(c["hook"]) == int(n):
            s, e, i0 = achar(hk, c["copy"], i0); raw.append((c, s, e))
    PL = pulo_hold(B, plano, p, n)
    i0 = 0; fim = HD + (dur_corte_hold(B, plano, p) - PL if any(pos_fala(c) for c in plano["cenas"]) else 0)
    for c in plano["cenas"]:
        if c["tipo"] != "hook":
            if pos_fala(c): raw.append((c, fim, fim + float(c.get("dur", 3.5)))); fim += float(c.get("dur", 3.5)); continue
            s, e, i0 = achar(hd, c["copy"], i0)
            if e - PL <= 0.05: continue        # cena da fala pulada neste AD (pular_hooks)
            raw.append((c, max(s - PL, 0) + HD, e - PL + HD))
    out = []
    for k, (c, s, e) in enumerate(raw):
        a = max(0, s - 0.08) if not pos_fala(c) else s; b = e + float(c.get("fim_extra", 0.25)) if not pos_fala(c) else e   # fim_extra 0 = avatar entra na palavra seguinte (BATCH#2822)
        if b - a < 1.4: b = a + 1.4
        if k + 1 < len(raw): b = min(b, raw[k + 1][1] - (0.08 if not pos_fala(raw[k + 1][0]) else 0))
        if k > 0 and not pos_fala(c): a = max(a, out[-1][2])      # sem sobreposição com a cena anterior
        f = cena_mp4(B, c, p if tem_marca(c) else None)
        b = min(b, a + dur_util(B, c, f, p) - 0.05); out.append((c["id"], round(a, 3), round(b, 3), f))
    # 1ª cena a menos de 0,5 s do início = lasca de avatar no quadro 0 do AD (BATCH#2480 AD3: 4-7 quadros antes do insert
    # do hook 3, que achava a copy na 1ª palavra a 0,22 s): a cena começa no 0
    if out and 0 < out[0][1] < 0.5 and not pos_fala(raw[0][0]):
        cid, a, b, f = out[0]; out[0] = (cid, 0.0, round(min(b, dur_util(B, raw[0][0], f, p) - 0.05), 3), f)
    # buraco curto entre duas cenas = o avatar "pisca" 1-2 quadros (Fefo, BATCH#2822: "frame muito rápido dela falando
    # depois do b-roll do cacau"). < 0,5 s: a cena anterior estica até a seguinte (ou a seguinte começa antes, se o clipe
    # anterior não tiver duração). Buraco maior é momento de avatar de propósito e fica.
    cen = {c["id"]: c for c in plano["cenas"]}
    def fechar_buracos():
        for k in range(len(out) - 1):
            cid, a, b, f = out[k]; nid, na, nb, nf = out[k + 1]
            if pos_fala(cen[cid]) or pos_fala(cen[nid]) or not 0 < na - b < 0.5: continue
            b2 = round(min(na, a + dur_util(B, cen[cid], f, p) - 0.05), 3)
            out[k] = (cid, a, b2, f)
            if na > b2: out[k + 1] = (nid, b2, nb, nf)
    fechar_buracos()
    # lasca de avatar (Fefo, BATCH#1977: "frames estranhos aparecendo por poucos frames"): dentro do buraco entre duas
    # cenas, cada emenda do avatar (corte de silêncio com punch-in, troca de fala, hook -> hold) é um corte. Pedaço < 0,5 s
    # entre a cena e a emenda = 2-9 quadros de outro enquadramento: a cena anterior estica até 1 quadro depois da emenda e
    # a seguinte começa 1 quadro antes dela. O fim do AD conta como emenda (avatar logo depois da última cena).
    enq = plano.get("estilo", {}).get("avatar", {}).get("enquadramento")
    sem_avatar = enq in ("nenhum", "pip")     # pip: o avatar fica numa janela e o b-roll cobre a tela o AD inteiro
    if out and not sem_avatar and not any(pos_fala(c) for c in plano["cenas"]):
        T = HD + dur_corte_hold(B, plano, p) - PL; em = emendas_avatar(B, plano, p, n, HD); q = 1 / 30
        lim = lambda c, a, f: a + dur_util(B, cen[c], f, p) - 0.05
        # 1ª cena logo depois de uma emenda (troca de fala): o laço abaixo só olha o buraco ENTRE cenas, e o avatar novo
        # piscava 1 quadro antes da 1ª cena (BATCH#2481: F03 -> F04 em 19,50 s e S01 em 19,52 s). Começa 1 quadro antes dela.
        pre = [s for s in em if out[0][1] - 0.5 < s < out[0][1] + 0.04]
        if pre:
            cid, a, b, f = out[0]; a = round(pre[0] - q, 3); out[0] = (cid, a, round(min(b, lim(cid, a, f)), 3), f)
        for k in range(len(out)):
            cid, a, b, f = out[k]; ult = k + 1 == len(out)
            ve = b if ult else b + 0.1                      # a cena passa 0,1 s por baixo da seguinte (montar)
            fim = T if ult else out[k + 1][1]
            if fim - ve < 0.02: continue
            pts = [s for s in em if ve + 0.02 < s < fim - 0.02]
            s1 = pts[0] if pts else (T if ult else None)
            if s1 is not None and s1 - ve < 0.5:
                out[k] = (cid, a, round(max(b, min(s1 + q - (0 if ult else 0.1), lim(cid, a, f))), 3), f)
            # emenda rente ao início da seguinte (−0,02 a +0,04 s): o b-roll de 24 fps entra até 1 quadro depois de `a`,
            # então sobrava 1 quadro do outro enquadramento do avatar (BATCH#1977 V2, lascas.py: AD1 NB 6,37 s antes do S01)
            rente = [s for s in em if fim - 0.02 <= s < fim + 0.04] if not ult else []
            if not ult and pts and fim - pts[-1] < 0.5:
                nid, na, nb, nf = out[k + 1]; na = round(pts[-1] - q, 3)
                out[k + 1] = (nid, na, round(min(nb, lim(nid, na, nf)), 3), nf)
            elif rente:
                nid, na, nb, nf = out[k + 1]; na = round(min(na, rente[0] - q), 3)
                out[k + 1] = (nid, na, round(min(nb, lim(nid, na, nf)), 3), nf)
            for x, y in zip(pts, pts[1:] + ([T] if ult else [])):
                if y - x < 0.5: print(f"   AVISO AD{n} {p}: trecho de avatar de {(y - x) * 30:.0f} quadros em {x:.2f} s (corte curto demais)")
        fechar_buracos()        # cena que começou antes pode terminar antes (fim do clipe) e abrir buraco com a seguinte
    if enq == "pip" and out:
        # médico em picture-in-picture sobre b-roll (BATCH#3217, build da 3213): nenhum quadro do avatar em tela cheia.
        # Cada cena começa onde a anterior acaba e termina antes do fim do clipe; a 1ª cobre o quadro 0 e a última vai
        # até o fim da fala (se o clipe acabar antes, o overlay segura o último quadro).
        T = HD + dur_corte_hold(B, plano, p) - PL
        for k in range(len(out)):
            cid, a, b, f = out[k]
            a = 0.0 if k == 0 else out[k - 1][2]
            if k + 1 < len(out): b = min(max(b, a + 0.3), a + dur_util(B, cen[cid], f, p) - 0.05)
            else: b = max(b, T)
            out[k] = (cid, round(a, 3), round(b, 3), f)
        # emenda do médico na janela (corte de silêncio, troca de fala, hook -> hold) a menos de 0,4 s de um corte de b-roll
        # = dois cortes seguidos (lascas.py: 1-3 quadros no AD1 da 3217): o corte do b-roll vai para a emenda
        em = emendas_avatar(B, plano, p, n, HD)
        for k in range(len(out) - 1):
            cid, a, b, f = out[k]; nid, na, nb, nf = out[k + 1]
            perto = [s for s in em if abs(s - b) < 0.4 and a + 0.45 < s < nb - 0.45 and s <= a + dur_util(B, cen[cid], f, p) - 0.05]
            if perto:
                # meio quadro antes da emenda: na emenda exata o b-roll entrava 1 quadro depois da virada da janela e com 1 quadro
                # antes entrava 1 quadro antes (lascas.py, 3217); com o enable começando meio quadro antes, os dois caem juntos
                s = round(min(perto, key=lambda x: abs(x - b)) - 1 / 60, 3); out[k] = (cid, a, s, f); out[k + 1] = (nid, s, nb, nf)
        # cena curta demais (< 0,45 s, ex.: "headlights" numa lista de uma cena por item) = lasca: pega tempo das vizinhas
        for k in range(1, len(out) - 1):
            cid, a, b, f = out[k]; falta = 0.45 - (b - a)
            if falta <= 0: continue
            pid, pa, pb, pf = out[k - 1]; nid, na, nb, nf = out[k + 1]
            a2 = max(pa + 0.45, a - falta / 2); b2 = min(nb - 0.45, b + falta - (a - a2))
            out[k - 1] = (pid, pa, round(a2, 3), pf); out[k] = (cid, round(a2, 3), round(b2, 3), f); out[k + 1] = (nid, round(b2, 3), nb, nf)
    elif sem_avatar:
        # sem avatar por baixo, buraco entre cenas = tela preta: a cena seguinte começa onde a anterior termina
        for k in range(1, len(out)):
            if out[k][1] > out[k - 1][2]: out[k] = (out[k][0], out[k - 1][2], out[k][2], out[k][3])
    # PiP (cena "formato": "inset") com o avatar falando atrás: borda do PiP a até 0,15 s de uma emenda do avatar =
    # dois cortes seguidos (lascas.py: 1-3 quadros, BATCH#3375). A borda vai para a emenda.
    if out and not sem_avatar and any(cen[c].get("formato") == "inset" for c, _, _, _ in out):
        em = emendas_avatar(B, plano, p, n, HD)
        perto = lambda t: min(em, key=lambda x: abs(x - t)) if em else t
        for k in range(len(out)):
            cid, a, b, f = out[k]
            if cen[cid].get("formato") != "inset": continue
            ea, eb = perto(a), perto(b)
            ea, eb = round(ea * 30) / 30 - 1 / 60, round(eb * 30) / 30 - 1 / 60     # meio quadro antes: o quadro da emenda já é do PiP novo
            a2 = ea if abs(ea - a) <= 0.15 and (k == 0 or ea >= out[k - 1][2] - 1e-3) else a
            b2 = eb if abs(eb - b) <= 0.15 and eb - a2 >= 1.0 and eb <= a2 + dur_util(B, cen[cid], f, p) - 0.05 else b
            if k + 1 < len(out): b2 = min(b2, out[k + 1][1]) if out[k + 1][1] >= a2 else b2
            out[k] = (cid, round(a2, 3), round(b2, 3), f)
        for k in range(len(out) - 1):          # PiPs encostados: o seguinte começa onde o anterior acaba
            if 0 < out[k + 1][1] - out[k][2] < 0.15: out[k + 1] = (out[k + 1][0], out[k][2], out[k + 1][2], out[k + 1][3])
    return out, HD

def dur_corte_hold(B, plano, p):
    return sum(dur_corte(corte(B, fala_stem(f, p if f.get("marca") else None))) for f in falas_hold(plano))

# ---------------------------------------------------------------- montagem final
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
            ev.append(f"Dialogue: 0,{t(0)},{t(HD)},{'HookBranco' if k == 0 else 'HookVermelho'},,0,0,{y},,{txt}")
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
    json.dump(plan, open(f"{B}/08_auto/broll_posicoes_AD{n}_{p}.json", "w"), indent=1)
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
    g = [f"[0:v]scale=720:1280,fps=30,setsar=1[hv];[0:a]atrim=end={hq:.6f}[ha];[1:v]trim=start={PL:.6f},setpts=PTS-STARTPTS,scale=720:1280,fps=30,setsar=1[pv];[1:a]atrim=start={PL:.6f},asetpts=PTS-STARTPTS[pa];[hv][ha][pv][pa]concat=n=2:v=1:a=1[av0][aa0]",
         f"[av0]null{pad}[av];[aa0]anull{apad}[aa]"]
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
            g.append(f"[{j}:v]trim={i0:.3f}:{i0+b2-a:.3f},setpts=PTS-STARTPTS,{geo},fps=30,settb=1/90000,"
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
        png = f"{B}/{hc['png']}"
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
    trilha = sorted(glob.glob(f"{B}/02_audio/trilha/*.mp3") + glob.glob(f"{B}/02_audio/trilha/*.wav"))
    lufs = cfg.get("audio", {}).get("loudness_lufs", -20)
    if trilha:
        vol = cfg.get("audio", {}).get("trilha_volume_db", -22); it = ins.count("-i"); ins += ["-stream_loop", "-1", "-i", trilha[0]]
        fim_db = plano.get("estilo", {}).get("trilha_final_db")      # trilha sobe quando a voz acaba (tela final)
        if fim_db is not None and ext > 0:
            T, v1, v2 = HD + DP, 10 ** (vol / 20), 10 ** (fim_db / 20)
            gv = f"volume='{v1:.5f}+({v2 - v1:.5f})*clip((t-{T:.3f})/0.5,0,1)':eval=frame"
        else: gv = f"volume={vol}dB"
        g.append(f"[{it}:a]{gv},aresample=44100,aformat=channel_layouts=stereo[tr];[aa][tr]amix=inputs=2:duration=first:normalize=0[mx]")
        g.append(f"[mx]loudnorm=I={lufs}:TP=-1.5:LRA=11,aresample=48000[aout]")
    else:
        g.append(f"[aa]loudnorm=I={lufs}:TP=-1.5:LRA=11,aresample=48000[aout]")
    sc = f"{tmp}/fc_AD{n}_{p}.txt"; open(sc, "w").write(";".join(g))
    out = export(B, plano, p, n); os.makedirs(os.path.dirname(out), exist_ok=True)
    subprocess.run([FF, "-nostdin", "-v", "error", "-y", *ins, "-filter_complex_script", sc, "-map", "[vout]", "-map", "[aout]",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", out], check=True)
    shutil.rmtree(tmp, ignore_errors=True); tira_export_antigo(B, plano, p, n)
    print(f"   ok {os.path.basename(out)} (hook {HD:.2f}s, {len(plan)} b-rolls{', com trilha' if trilha else ''})")

# ---------------------------------------------------------------- XML (V1 falas, V2 b-roll)
def gerar_xml(B):
    import urllib.parse
    from xml.sax.saxutils import escape
    plano, _ = carregar(B); FPS, W, H = 30, 1080, 1920; fr = lambda t: int(round(t * FPS))
    if plano.get("one_take"):
        import umtake; return umtake.gerar_xml(sys.modules[__name__], B)
    info, fid = {}, {}
    def media(p):
        if p not in info:
            o = subprocess.run([FF, "-i", p], capture_output=True, text=True).stderr
            v = re.search(r"Video:.*?, (\d+)x(\d+)", o); r = re.search(r"(\d+(?:\.\d+)?) fps", o)
            info[p] = (duracao(p), int(v[1]), int(v[2]), float(r[1])); fid[p] = f"file-{len(fid)+1}"
        return info[p]
    def fe(p, vistos):
        d, sw, sh, sf = media(p)
        if fid[p] in vistos: return f'<file id="{fid[p]}"/>'
        vistos.add(fid[p])
        return (f'<file id="{fid[p]}"><name>{escape(os.path.basename(p))}</name><pathurl>file://{urllib.parse.quote(p)}</pathurl>'
                f'<rate><timebase>{round(sf)}</timebase><ntsc>FALSE</ntsc></rate><duration>{int(round(d*sf))}</duration><media><video>'
                f'<samplecharacteristics><width>{sw}</width><height>{sh}</height></samplecharacteristics></video>'
                f'<audio><channelcount>2</channelcount></audio></media></file>')
    rate = f"<rate><timebase>{FPS}</timebase><ntsc>FALSE</ntsc></rate>"
    def motion(sw, sh, vert=0.0, crop=None):
        s = 100 * max(W / sw, (H if crop is None else H / 2) / sh) if crop is None else 100 * W / sw
        e = (f'<filter><effect><name>Basic Motion</name><effectid>basic</effectid><effectcategory>motion</effectcategory><effecttype>motion</effecttype>'
             f'<mediatype>video</mediatype><parameter><parameterid>scale</parameterid><name>Scale</name><valuemin>0</valuemin><valuemax>1000</valuemax>'
             f'<value>{s:.2f}</value></parameter><parameter><parameterid>center</parameterid><name>Center</name><value><horiz>0</horiz><vert>{vert}</vert></value></parameter></effect></filter>')
        if crop:
            e += (f'<filter><effect><name>Crop</name><effectid>crop</effectid><effectcategory>motion</effectcategory><effecttype>motion</effecttype><mediatype>video</mediatype>'
                  f'<parameter><parameterid>top</parameterid><name>top</name><value>{crop}</value></parameter>'
                  f'<parameter><parameterid>bottom</parameterid><name>bottom</name><value>{crop}</value></parameter></effect></filter>')
        return e
    def motion_xy(s, hz, vt, top=None, bot=None):
        e = (f'<filter><effect><name>Basic Motion</name><effectid>basic</effectid><effectcategory>motion</effectcategory><effecttype>motion</effecttype>'
             f'<mediatype>video</mediatype><parameter><parameterid>scale</parameterid><name>Scale</name><valuemin>0</valuemin><valuemax>1000</valuemax>'
             f'<value>{s:.2f}</value></parameter><parameter><parameterid>center</parameterid><name>Center</name><value><horiz>{hz:.4f}</horiz><vert>{vt:.4f}</vert></value></parameter></effect></filter>')
        if top is not None:
            e += (f'<filter><effect><name>Crop</name><effectid>crop</effectid><effectcategory>motion</effectcategory><effecttype>motion</effecttype><mediatype>video</mediatype>'
                  f'<parameter><parameterid>top</parameterid><name>top</name><value>{top:.2f}</value></parameter>'
                  f'<parameter><parameterid>bottom</parameterid><name>bottom</name><value>{bot:.2f}</value></parameter></effect></filter>')
        return e
    def motion_meia(sw, sh, lado, baixo=False):
        """Metade da tela dividida (split): lado -1 esquerda, +1 direita; cobre 540 x (1920 ou 960) e corta o excesso."""
        hh = H / 2 if baixo else H; s = 100 * max(W / 2 / sw, hh / sh)
        cl = round(100 * (1 - (W / 2) / (sw * s / 100)) / 2, 2); ct = round(100 * (1 - hh / (sh * s / 100)) / 2, 2)
        e = motion_xy(s, 0.25 * lado, 0.25 if baixo else 0, ct, ct)
        return e.replace('<parameter><parameterid>bottom</parameterid>',
                         f'<parameter><parameterid>left</parameterid><name>left</name><value>{cl:.2f}</value></parameter>'
                         f'<parameter><parameterid>right</parameterid><name>right</name><value>{cl:.2f}</value></parameter>'
                         '<parameter><parameterid>bottom</parameterid>')
    CART = plano.get("estilo", {}).get("broll", {}).get("layout") == "cartao"; CENS = {c["id"]: c for c in plano["cenas"]}
    if CART:
        import cartao; EST = cartao.cfg_estilo(plano); CEN = {c["id"]: c for c in plano["cenas"]}
    seqs = []
    for p in plano["produtos"]:
        for n in hooks(plano):
            vistos, V1, A1, V2, V3, t = set(), [], [], [], [], 0
            fl = [fala_hook(plano, n)] + falas_hold(plano)
            for fi, f in enumerate(fl):
                mp4 = fala_mp4(B, f, p if f.get("marca") else None); d, sw, sh, _ = media(mp4)
                if CART:
                    zz = EST["avatar"]["punch_in"]; mav = motion_xy(*cartao.motion_avatar(sw, sh, EST, zz[fi % len(zz)]))
                else: mav = motion(sw, sh)
                for s, e in json.load(open(corte(B, fala_stem(f, p if f.get("marca") else None)))):
                    a, b = fr(s), fr(e); dd = b - a
                    if dd <= 0: continue
                    cid = f"AD{n}{p}-{len(V1)}"; com = (f'<name>{escape(os.path.basename(mp4))}</name><enabled>TRUE</enabled><duration>{fr(d)}</duration>'
                                                       f'{rate}<start>{t}</start><end>{t+dd}</end><in>{a}</in><out>{b}</out>')
                    lk = f'<link><linkclipref>{cid}v</linkclipref><mediatype>video</mediatype></link><link><linkclipref>{cid}a</linkclipref><mediatype>audio</mediatype></link>'
                    V1.append(f'<clipitem id="{cid}v">{com}{fe(mp4, vistos)}{mav}{lk}</clipitem>')
                    A1.append(f'<clipitem id="{cid}a">{com}<file id="{fid[mp4]}"/><sourcetrack><mediatype>audio</mediatype><trackindex>1</trackindex></sourcetrack>{lk}</clipitem>')
                    t += dd
            if os.path.exists(L(B, f"palavras_hold_{p}.json")) and os.path.exists(L(B, f"palavras_{hook_marca(plano, n, p)[2]}.json")):
                plan, _ = segmentos(B, p, n)
                for k, (c, a, b, fl2) in enumerate(plan):
                    d, sw, sh, _ = media(fl2); dd = fr(b) - fr(a)
                    if dd <= 0: continue
                    if CART:
                        fm = CEN[c]["formato"] if c in CEN else "tela_cheia"
                        mo = motion_xy(100 * 900 / sw, 0, (70 + 450 - H / 2) / H) if fm == "cta_final" else motion_xy(*cartao.motion_broll(sw, sh, EST, fm))
                    elif plano.get("estilo", {}).get("broll", {}).get("layout") == "metade_baixo":
                        mo = motion(sw, sh, 0.25, round(100 * (1 - (H / 2) / (sh * W / sw)) / 2, 2))
                    else: mo = motion(sw, sh)
                    rd = None if CART else clipe_direita(B, CENS.get(c, {}), p)
                    baixo = plano.get("estilo", {}).get("broll", {}).get("layout") == "metade_baixo"
                    if rd: mo = motion_meia(sw, sh, -1, baixo)      # split: esta metade à esquerda, o produto em V3
                    i0 = fr(cena_inicio(CENS.get(c, {})))
                    V2.append(f'<clipitem id="AD{n}{p}-b{k}"><name>{escape(os.path.basename(fl2))}</name><enabled>TRUE</enabled><duration>{fr(d)}</duration>'
                              f'{rate}<start>{fr(a)}</start><end>{fr(a)+dd}</end><in>{i0}</in><out>{i0+dd}</out>{fe(fl2, vistos)}{mo}</clipitem>')
                    if rd:
                        d3, sw3, sh3, _ = media(rd); i3 = fr(float(CENS[c].get("inicio_direita", 0)))
                        V3.append(f'<clipitem id="AD{n}{p}-d{k}"><name>{escape(os.path.basename(rd))}</name><enabled>TRUE</enabled><duration>{fr(d3)}</duration>'
                                  f'{rate}<start>{fr(a)}</start><end>{fr(a)+dd}</end><in>{i3}</in><out>{i3+dd}</out>{fe(rd, vistos)}{motion_meia(sw3, sh3, 1, baixo)}</clipitem>')
            v3 = f'<track>{"".join(V3)}</track>' if V3 else ""
            seqs.append(f'<sequence id="AD{n}-{p}"><name>AD{n}_{p}</name><duration>{t}</duration>{rate}<media><video><format><samplecharacteristics>{rate}'
                        f'<width>{W}</width><height>{H}</height><pixelaspectratio>square</pixelaspectratio></samplecharacteristics></format>'
                        f'<track>{"".join(V1)}</track><track>{"".join(V2)}</track>{v3}</video><audio><track>{"".join(A1)}</track></audio></media></sequence>')
    out = xmlpath(B, plano)
    open(out, "w").write('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n<xmeml version="4"><project><name>'
                         f'BATCH{num(plano)}</name><children>{"".join(seqs)}</children></project></xmeml>')
    print(f"   ok {os.path.basename(out)} ({len(seqs)} sequências)")

# ---------------------------------------------------------------- identificar vídeos baixados
def cmd_identificar(a):
    import numpy as np
    def fp(p, video):
        args = [FF, "-nostdin", "-v", "quiet", "-i", p, "-vf", "scale=32:56,format=gray", "-frames:v", "1", "-f", "rawvideo", "-"]
        return np.frombuffer(subprocess.run(args, capture_output=True).stdout, np.uint8).astype(float)
    Q = {os.path.splitext(os.path.basename(q))[0]: fp(q, False) for q in glob.glob(f"{a.quadros}/*.png") + glob.glob(f"{a.quadros}/*.jpg")}
    for v in a.videos:
        x = fp(v, True); d = sorted((np.abs(x - q).mean(), k) for k, q in Q.items() if len(q) == len(x))
        tag = "OK" if d and d[0][0] < 5 and (len(d) < 2 or d[1][0] - d[0][0] > 5) else "CONFERIR"
        print(f"{os.path.basename(v)}\t{d[0][1] if d else '-'}\t{d[0][0]:.1f}\t{tag}")

def cmd_novo_plano(a):
    B = a.batch.rstrip("/"); r = open(f"{B}/00_roteiro/roteiro.txt").read()
    hold = [re.sub(r"^\d+\.\s*", "", l).strip() for l in r.split("HOLD", 1)[1].strip().splitlines() if re.match(r"^\d+\.", l)]
    hk = {int(m[0]): m[1].strip() for m in re.findall(r"HOOK (\d+)\s*\n([^\n]+)", r)}
    plano = {"batch": os.path.basename(B).split(" ")[0], "produtos": ["neurobella", "visiovance"],
             "marca_nome": {"neurobella": "Neurobella", "visiovance": "VisioVance"},
             "hold": [l.replace("Neurobella", "{MARCA}") for l in hold], "hooks": {str(k): v for k, v in hk.items()},
             "personagens": {}, "frascos": {}, "falas": [], "cenas": []}
    out = f"{B}/08_auto/plano.json"
    if os.path.exists(out): raise SystemExit("plano.json já existe; não sobrescrevo.")
    json.dump(plano, open(out, "w"), indent=1, ensure_ascii=False); print("ok", out)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("status"); p.add_argument("batch"); p.set_defaults(fn=cmd_status)
    p = sp.add_parser("fazer"); p.add_argument("batch"); p.add_argument("--ate", choices=ORDEM[2:]); p.add_argument("--so"); p.add_argument("--forcar", action="store_true"); p.add_argument("--aceitar-sem-voz", action="store_true"); p.set_defaults(fn=cmd_fazer)
    p = sp.add_parser("montar"); p.add_argument("batch"); p.add_argument("produto"); p.add_argument("hook"); p.set_defaults(fn=lambda a: montar(a.batch.rstrip("/"), a.produto, a.hook))
    p = sp.add_parser("xml"); p.add_argument("batch"); p.set_defaults(fn=lambda a: gerar_xml(a.batch.rstrip("/")))
    p = sp.add_parser("identificar"); p.add_argument("videos", nargs="+"); p.add_argument("--quadros", required=True); p.set_defaults(fn=cmd_identificar)
    p = sp.add_parser("novo-plano"); p.add_argument("batch"); p.set_defaults(fn=cmd_novo_plano)
    p = sp.add_parser("perfil"); p.set_defaults(fn=cmd_perfil)
    p = sp.add_parser("instalar"); p.add_argument("raiz"); p.set_defaults(fn=cmd_instalar)
    p = sp.add_parser("empacotar"); p.set_defaults(fn=cmd_empacotar)
    p = sp.add_parser("publicar"); p.add_argument("mensagem"); p.set_defaults(fn=cmd_publicar)
    p = sp.add_parser("renomear"); p.add_argument("batch"); p.set_defaults(fn=cmd_renomear)
    a = ap.parse_args(); a.fn(a)
