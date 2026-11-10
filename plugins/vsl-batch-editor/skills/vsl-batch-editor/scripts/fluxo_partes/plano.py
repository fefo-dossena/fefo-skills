# Parte do fluxo.py: plano.json e caminhos de arquivos. Roda no mesmo espaço de nomes do fluxo.py (não importar sozinho).
# ---------------------------------------------------------------- plano e caminhos
def carregar(B):
    plano = json.load(open(f"{B}/{AUTO}/plano.json"))
    cfg = json.load(open(f"{B}/{CFG}")) if os.path.exists(f"{B}/{CFG}") else {}
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
    return fala_orig(B, f, p) if v == 1 else f"{B}/{AUTO}/rapido/{fala_stem(f, p)}_x{v:g}.mp4"

def corte(B, stem): return f"{B}/{AUTO}/cortes/{stem}.json"
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
    if c.get("dur_max"): d = min(d, float(c["dur_max"]) + 0.05)   # trecho limpo do clipe (antes de um pulo/objeto estranho)
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

def L(B, nome): return f"{B}/{AUTO}/legendas/{nome}"
def previa(B, p): return f"{B}/{AUTO}/preview_hold_{p}.mp4"
def punch(plano, i, fala=None):
    """Punch-in alternado a cada corte de silêncio dentro da fala (disfarça o pulo do rosto; Frame.io BATCH_2080).
    plano.estilo.avatar.punch_in = [1.0, 1.12] e crop_y (0 = topo, 0.5 = centro) para manter o rosto no quadro."""
    av = plano.get("estilo", {}).get("avatar", {}); zs = (fala or {}).get("punch_in") or av.get("punch_in") or [1.0]; z = zs[i % len(zs)]   # falas[i].punch_in vence o do estilo
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
    cfg = json.load(open(f"{B}/{CFG}")) if os.path.exists(f"{B}/{CFG}") else {}
    t = (cfg.get("card") or "").strip()
    if not t and (cfg.get("titulo") or "").strip() and not cfg["titulo"].startswith("Nome do Ad"):
        t = f"BATCH#{num(plano)} - {cfg['titulo'].strip()}"
    return re.sub(r'[\\/:*?"<>|]', "-", t)
def export_antigo(B, plano, p, n): return f"{B}/{EXPORT}/{p}/BATCH{num(plano)}_AD{n}_{p}.mp4"
def export(B, plano, p, n):
    """Nome do AD = título do card + marca + AD (regra do Fefo, 23/10/2026):
    "BATCH#3215 - Thinning Shield - Macular Degeneration - L2 - Problem Aware - Daniel - Neurobella - AD1.mp4".
    Sem título do card no batch.json, o nome antigo (BATCH<n>_AD<k>_<p>.mp4)."""
    c = card(B, plano)
    if not c: return export_antigo(B, plano, p, n)
    m = plano.get("marca_nome", {}).get(p) or {"neurobella": "Neurobella", "visiovance": "VisioVance"}.get(p, p.capitalize())
    return f"{B}/{EXPORT}/{p}/{c} - {m} - AD{n}.mp4"
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
def xmlpath(B, plano): return f"{B}/{AUTO}/BATCH{num(plano)}_premiere.xml"

