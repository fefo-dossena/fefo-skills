# Parte do fluxo.py: grafo de dependências, status, fazer, bordas e ganho. Roda no mesmo espaço de nomes do fluxo.py (não importar sozinho).
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

