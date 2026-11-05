# Parte do fluxo.py: posição do b-roll e segmentos. Roda no mesmo espaço de nomes do fluxo.py (não importar sozinho).
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
    # PiP (cena "formato": "inset") com o avatar falando atrás: borda do PiP a até 0,3 s de uma emenda do avatar =
    # dois cortes seguidos (lascas.py: 1-3 quadros, BATCH#3375; 7 quadros no S12 da 3375 V4 com 0,15). A borda vai para a emenda.
    if out and not sem_avatar and any(cen[c].get("formato") == "inset" for c, _, _, _ in out):
        em = emendas_avatar(B, plano, p, n, HD)
        perto = lambda t: min(em, key=lambda x: abs(x - t)) if em else t
        for k in range(len(out)):
            cid, a, b, f = out[k]
            if cen[cid].get("formato") != "inset": continue
            ea, eb = perto(a), perto(b)
            ea, eb = round(ea * 30) / 30 - 1 / 60, round(eb * 30) / 30 - 1 / 60     # meio quadro antes: o quadro da emenda já é do PiP novo
            a2 = ea if abs(ea - a) <= 0.3 and (k == 0 or ea >= out[k - 1][2] - 1e-3) else a
            b2 = eb if abs(eb - b) <= 0.3 and eb - a2 >= 1.0 and eb <= a2 + dur_util(B, cen[cid], f, p) - 0.05 else b
            if k + 1 < len(out): b2 = min(b2, out[k + 1][1]) if out[k + 1][1] >= a2 else b2
            out[k] = (cid, round(a2, 3), round(b2, 3), f)
        for k in range(len(out) - 1):          # PiPs encostados: o seguinte começa onde o anterior acaba
            if 0 < out[k + 1][1] - out[k][2] < 0.15: out[k + 1] = (out[k + 1][0], out[k][2], out[k + 1][2], out[k + 1][3])
    return out, HD

def dur_corte_hold(B, plano, p):
    return sum(dur_corte(corte(B, fala_stem(f, p if f.get("marca") else None))) for f in falas_hold(plano))

