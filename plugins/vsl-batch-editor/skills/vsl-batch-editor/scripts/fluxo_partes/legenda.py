# Parte do fluxo.py: transcrição, alinhamento e SRT. Roda no mesmo espaço de nomes do fluxo.py (não importar sozinho).
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

