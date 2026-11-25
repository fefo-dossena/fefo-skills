#!/usr/bin/env python3
"""lint_plano: trava antes do revisor (proposta A, Frente 1, 09/11/2026). Lê a linha do tempo de cada AD e acha o que o
revisor sempre bloqueava na 1ª rodada, antes de exportar os ADs (ou num export pronto).

  python3 lint_plano.py <batch> [--ad AD1_neurobella] [--json] [--sem-visao]
      Modo plano: a linha do tempo sai do plano.json + cortes + palavras (a mesma conta da montagem, sem render).
      Roda depois do `fazer --ate legendas` e antes do `fazer` final.
  python3 lint_plano.py <batch> --export <AD.mp4> [...]
      Modo export: a linha do tempo sai do vídeo (cada trecho casado com o clipe de origem da batch). Serve para
      versão já exportada e para conferir uma V antiga.

Erros (código de saída 1):
  3d_seguido   dois planos 3D seguidos (sem avatar ou plano real de >= 0,5 s entre eles)
  3d_longo     plano 3D acima de 2,5 s
  hook_hold    pausa entre o fim do hook e a 1ª palavra da hold abaixo de 0,30 s
  trilha       AD do Daniel sem trilha em <audio>/trilha/
  parado       trecho previsto sem mudança acima de 3 s (b-roll longo, ou avatar sem corte)
  rosto        legenda ou header em cima do rosto (lido pela visão do Mac)
  rotulo       legenda ou header em cima do rótulo do frasco (lido pela visão do Mac)
Avisos (não travam): o que não dá para ler (sem visão, cena sem clipe, copy não achada, posição de texto só prevista).
Código 2: erro de uso ou de leitura (sem plano.json, batch inexistente).

Grava <auto>/lint_plano.json (com --json ou sempre que roda pelo `fluxo.py checar`): achados e o fim do hook de cada AD
(usado pelo revisor.py para mostrar a hold uma vez e cada hook separado).
Regras e números: PADRAO.md do revisor (§1) e a nota "Levantamento dos fluxos das batches".
"""
import argparse, contextlib, glob, importlib.util, io, json, os, re, subprocess, sys, tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, 'checagens'))

LIM_3D = 2.5          # Daniel 3215 / 2084: 3D no máximo ~2,5 s
GAP_REAL = 0.5        # menos que isso entre dois 3D = seguidos
LIM_PAUSA = 0.30      # meta do montar.py (2822: < 0,2 s soa corte estranho)
LIM_PARADO = 3.0      # SOP do Daniel: algo muda a cada 1 a 3 s
RE_3D = re.compile(r'(^|[^a-z0-9])3d([^a-z0-9]|$)|animation|anima[cç][aã]o|render', re.I)
FF = os.path.expanduser('~/bin/ffmpeg') if os.path.exists(os.path.expanduser('~/bin/ffmpeg')) else 'ffmpeg'


# ------------------------------------------------------------------ fluxo (só leitura: segmentos, cortes, palavras)
def carregar_fluxo(B):
    """Importa o fluxo.py do núcleo preso ao cliente da pasta da batch (sem rodar comando nenhum)."""
    old = os.getcwd(); os.chdir(B)
    try:
        spec = importlib.util.spec_from_file_location('fluxo_lint', os.path.join(AQUI, 'fluxo.py'))
        m = importlib.util.module_from_spec(spec)
        argv = sys.argv; sys.argv = [argv[0]]
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                spec.loader.exec_module(m)
        finally:
            sys.argv = argv
        return m
    finally:
        os.chdir(old)


def eh_3d(c=None, arquivo=''):
    txt = ' '.join([arquivo or ''] + ([c.get('id', ''), c.get('nome', ''), c.get('busca', ''), c.get('mostra', ''),
                                       c.get('visual', '') if isinstance(c.get('visual'), str) else ''] if c else []))
    return bool((c or {}).get('3d')) or bool(RE_3D.search(os.path.basename(arquivo or '')) or RE_3D.search(txt))


def eh_daniel(B, plano, cfg):
    txt = ' '.join(str(x) for x in (cfg.get('card', ''), cfg.get('titulo', ''), plano.get('batch', ''), os.path.basename(B)))
    return 'daniel' in txt.lower() or bool(plano.get('trilha_obrigatoria'))


def quadro(mp4, t, out):
    subprocess.run([FF, '-nostdin', '-v', 'error', '-y', '-ss', f'{max(t, 0):.3f}', '-i', mp4, '-frames:v', '1',
                    '-vf', 'scale=720:-2', out], capture_output=True)
    return out if os.path.exists(out) else None


def duracao(mp4):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', mp4],
                       capture_output=True, text=True)
    try: return float(r.stdout.strip())
    except ValueError: return 0.0


# ------------------------------------------------------------------ zonas (visão do Mac)
def rotulo_zona(textos, marcas):
    """Caixa do rótulo: o nome da marca e as linhas de texto logo em volta (mesma coluna, até ~3 alturas)."""
    nomes = [re.sub(r'[^a-z]', '', m.lower()) for m in marcas if m]
    base = [t for t in textos if any(n and n[:6] in re.sub(r'[^a-z]', '', t['t'].lower()) for n in nomes)]
    if not base:
        return None
    x, y, w, h = base[0]['b']
    x0, y0, x1, y1 = x, y, x + w, y + h
    for t in textos:
        tx, ty, tw, th = t['b']
        cx = tx + tw / 2
        if x0 - w * 0.6 <= cx <= x1 + w * 0.6 and y0 - 4 * h <= ty <= y1 + 12 * h and tw < w * 2.2:
            x0, y0, x1, y1 = min(x0, tx), min(y0, ty), max(x1, tx + tw), max(y1, ty + th)
    return [x0, y0, x1 - x0, y1 - y0]


def sobre(a, b):
    import visao
    return visao.sobrepoe(a, b)


def testar_zonas(texto_caixas, rostos, rotulo):
    """[(tipo, texto, fração)] para cada caixa de legenda/header que cai no rosto ou no rótulo."""
    out = []
    for nome, cx in texto_caixas:
        for r in rostos:
            # só a parte de cima do rosto (testa, olhos, boca); queixo encostado não conta
            zona = [r[0] + r[2] * 0.1, r[1], r[2] * 0.8, r[3] * 0.85]
            f = sobre(cx, zona)
            if f >= 0.15:
                out.append(('rosto', nome, f)); break
        if rotulo:
            z = [rotulo[0] - 0.01, rotulo[1] - 0.01, rotulo[2] + 0.02, rotulo[3] + 0.02]
            f = sobre(cx, z)
            if f >= 0.08:
                out.append(('rotulo', nome, f))
    return out


# ------------------------------------------------------------------ modo plano
def caixa_legenda(y, linhas=2, tam=42.5):
    # pílula padrão (pilula.py, regra do Fefo 13/11/2026): cada linha 1,342 x corpo de altura, 0,14 x corpo de vão
    if y > 1: y = y / 1920
    h = (linhas * 1.342 + (linhas - 1) * 0.14) * tam / 1920
    m = 0.3 * tam / 1920                      # o pilula.py empurra o bloco para dentro da margem da legenda
    y = min(max(y, 0.139 + m + h / 2), 0.649 - m - h / 2)   # (Fefo, 16/11/2026: y 267-1246 em 1920)
    return [0.18, y - h / 2, 0.64, h]


def linha_do_tempo_plano(F, B, plano, cfg, p, n):
    """Planos do AD na ordem: [{'ini','fim','tipo': broll|avatar, 'cena', 'arq', 'off'}] e o fim do hook."""
    f, pm, hs = F.hook_marca(plano, n, p)
    HD = F.dur_corte(F.corte(B, F.fala_stem(f, pm)))
    segs, _ = F.segmentos(B, p, n)
    PL = F.pulo_hold(B, plano, p, n)
    T = HD + F.dur_corte_hold(B, plano, p) - PL
    cen = {c['id']: c for c in plano['cenas']}
    sem_avatar = plano.get('estilo', {}).get('avatar', {}).get('enquadramento') in ('nenhum', 'pip')
    # emendas do avatar pela conta dos cortes (cada trecho do corte troca o punch-in)
    q = getattr(F, 'FPS', 30)     # fps do cliente (EV 60 desde 18/11/2026)
    d = lambda s, e: (round(e * q) - round(s * q)) / q
    em, t = [], 0.0
    for s, e in json.load(open(F.corte(B, F.fala_stem(f, pm)), encoding='utf-8')):
        t += d(s, e); em.append(t)
    t = 0.0
    for fa in F.falas_hold(plano):
        for s, e in json.load(open(F.corte(B, F.fala_stem(fa, p if fa.get('marca') else None)), encoding='utf-8')):
            t += d(s, e)
            if t - PL > 1e-3: em.append(HD + t - PL)
    out, cur = [], 0.0
    for cid, a, b, arq in segs:
        if a - cur > 0.05:
            out.append({'ini': cur, 'fim': a, 'tipo': 'avatar' if not sem_avatar else 'vazio'})
        c = cen.get(cid, {})
        out.append({'ini': a, 'fim': b, 'tipo': 'broll', 'cena': cid, 'arq': arq, 'off': F.cena_inicio(c), 'c': c})
        cur = b
    if T - cur > 0.05:
        out.append({'ini': cur, 'fim': T, 'tipo': 'avatar' if not sem_avatar else 'vazio'})
    return out, HD, em, PL


def pausa_hook_hold_plano(F, B, plano, p, n, HD, PL):
    f, pm, hs = F.hook_marca(plano, n, p)
    try:
        hk = json.load(open(F.L(B, f'palavras_{hs}.json'), encoding='utf-8'))
        hd = json.load(open(F.L(B, f'palavras_hold_{p}.json'), encoding='utf-8'))
    except (OSError, ValueError):
        return None
    fim_hook = max(w['e'] for w in hk) if hk else HD
    prim = [w for w in hd if w['s'] >= PL - 0.01]
    if not prim:
        return None
    return round((HD - fim_hook) + (prim[0]['s'] - PL), 3)


# ------------------------------------------------------------------ modo export
def miniaturas(mp4, fps, ini=0.0, dur=None, W=32, H=56):
    import numpy as np
    cmd = [FF, '-nostdin', '-v', 'error']
    if ini: cmd += ['-ss', f'{ini:.3f}']
    if dur: cmd += ['-t', f'{dur:.3f}']
    cmd += ['-i', mp4, '-vf', f'fps={fps},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},format=gray',
            '-f', 'rawvideo', '-']
    raw = subprocess.run(cmd, capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, H * W).astype(np.float32)
    fr = fr[:, : H * W]
    m = fr.mean(1, keepdims=True); s = fr.std(1, keepdims=True) + 8
    return (fr - m) / s


def linha_do_tempo_export(B, mp4, F, sem_avatar=False):
    """Casa cada 1/6 s do export com o quadro mais parecido dos clipes da batch (avatar ou b-roll)."""
    import numpy as np
    pastas = getattr(F, 'BRUTOS', ['03_avatar', '04_broll_hold', '05_broll_hooks'])
    clipes = sorted({x for p in pastas for x in glob.glob(os.path.join(glob.escape(B), p, '**', '*.mp4'), recursive=True)
                     if '/_old/' not in x and '/personagens/' not in x and not (sem_avatar and '/03_avatar/' in x)})
    rapido = [] if sem_avatar else sorted(glob.glob(os.path.join(glob.escape(B), getattr(F, 'AUTO', '08_auto'), 'rapido', '*.mp4')))
    clipes += rapido
    # clipes que saíram da batch depois (ex.: 08_auto/_kling_nao_usado/): a V antiga pode ter usado
    clipes += sorted(x for x in glob.glob(os.path.join(glob.escape(B), getattr(F, 'AUTO', '08_auto'), '**', '*.mp4'), recursive=True)
                     if not re.search(r'preview_|/rapido/|/tmp|/_montar|/cortes/', x) and x not in clipes)
    FPS_C = 6
    banco, dono, tempo = [], [], []
    for c in clipes:
        m = miniaturas(c, FPS_C)
        if not len(m): continue
        banco.append(m); dono += [c] * len(m); tempo += [i / FPS_C for i in range(len(m))]
    if not banco:
        return [], 'sem clipes na batch para casar'
    banco = np.concatenate(banco)
    FPS_E = 6
    ex = miniaturas(mp4, FPS_E)
    # parte de cima e de baixo do quadro têm legenda/header: compara só a faixa do meio
    H, W = 56, 32
    faixa = np.zeros((H, W), bool); faixa[int(H * 0.08):int(H * 0.62)] = True; faixa = faixa.ravel()
    bb = banco[:, faixa]; ee = ex[:, faixa]
    dist = ((ee[:, None, :] - bb[None, :, :]) ** 2).mean(2) if len(ee) * len(bb) < 4e7 else None
    if dist is None:
        idx = []; dmin = []
        for v in ee:
            dd = ((bb - v) ** 2).mean(1); k = int(dd.argmin()); idx.append(k); dmin.append(float(dd[k]))
    else:
        idx = list(dist.argmin(1)); dmin = [float(dist[i, k]) for i, k in enumerate(idx)]
    amostras = []
    for i, (k, dm) in enumerate(zip(idx, dmin)):
        arq = dono[k] if dm < 0.9 else None
        amostras.append((i / FPS_E, arq, tempo[k]))
    # suaviza amostra isolada (1 em 6 que cai noutro clipe parecido)
    for i in range(1, len(amostras) - 1):
        if amostras[i - 1][1] == amostras[i + 1][1] != amostras[i][1]:
            amostras[i] = (amostras[i][0], amostras[i - 1][1], amostras[i][2])
    planos = []
    for t, arq, tc in amostras:
        tipo = 'avatar' if arq and '03_avatar' in arq or (arq and '/rapido/' in arq) else ('broll' if arq else '?')
        chave = arq if tipo == 'broll' else tipo
        if planos and planos[-1]['_k'] == chave:
            planos[-1]['fim'] = t + 1 / FPS_E
        else:
            planos.append({'_k': chave, 'ini': t, 'fim': t + 1 / FPS_E, 'tipo': tipo, 'arq': arq, 'off': tc})
    # trecho curto (< 0,4 s) entre dois pedaços do mesmo clipe = engano do casamento: junta
    k = 1
    while k < len(planos) - 1:
        q = planos[k]
        if q['fim'] - q['ini'] < 0.4 and planos[k - 1]['_k'] == planos[k + 1]['_k']:
            planos[k - 1]['fim'] = planos[k + 1]['fim']; del planos[k:k + 2]; continue
        k += 1
    k = 1
    while k < len(planos):
        if planos[k]['fim'] - planos[k]['ini'] < 0.2:
            planos[k - 1]['fim'] = planos[k]['fim']; del planos[k]; continue
        k += 1
    return planos, None


def transcrever_inicio(mp4, ate):
    """Palavras do começo do export (faster-whisper, com tempo por palavra)."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None
    tmp = tempfile.mkdtemp(prefix='lint_')
    wav = os.path.join(tmp, 'a.wav')
    subprocess.run([FF, '-nostdin', '-v', 'error', '-y', '-i', mp4, '-t', f'{ate:.2f}', '-ac', '1', '-ar', '16000', wav])
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import cuda_dlls                                            # GPU (cuda/float16), CPU só se falhar (Central, 17/11/2026)
    m = cuda_dlls.whisper('small')                              # small de propósito: só os 16 s do começo
    try:
        import transcricao_cache as tc; idi = tc.idioma(mp4)      # batch.json/job.json → plano → "en" (17/11/2026)
    except Exception:
        idi = 'en'
    seg, _ = m.transcribe(wav, language=idi, word_timestamps=True, vad_filter=False)
    return [{'w': w.word.strip(), 's': w.start, 'e': w.end} for s in seg for w in s.words]


def norm(w): return re.sub(r'[^a-z0-9]', '', w.lower())


def silencio_voz(mp4, a, b):
    """Maior trecho sem voz entre a e b (s): energia na faixa da voz (300-3400 Hz) 18 dB abaixo da fala em volta.
    A trilha fica por baixo; o whisper sozinho erra o fim da palavra em até 0,3 s."""
    import numpy as np
    ini = max(a - 1.0, 0)
    raw = subprocess.run([FF, '-nostdin', '-v', 'error', '-ss', f'{ini:.3f}', '-t', f'{b - ini + 1.0:.3f}', '-i', mp4,
                          '-af', 'highpass=f=300,lowpass=f=3400', '-ac', '1', '-ar', '16000', '-f', 's16le', '-'],
                         capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32)
    if not len(x): return None
    q = 160                                                   # 10 ms
    n = len(x) // q
    db = 20 * np.log10(np.sqrt((x[:n * q].reshape(n, q) ** 2).mean(1)) + 1e-3)
    fala = np.percentile(db, 85)
    baixo = db < fala - 18
    i0, i1 = int((a - ini) * 100), int((b - ini) * 100)
    melhor = cur = 0
    for v in baixo[i0:i1]:
        cur = cur + 1 if v else 0; melhor = max(melhor, cur)
    return melhor / 100


def pausa_hook_hold_export(mp4, texto_hook, texto_hold):
    alvo_fim = [norm(x) for x in texto_hook.split() if norm(x)][-2:]
    alvo_ini = [norm(x) for x in texto_hold.split() if norm(x)][:2]
    ws = transcrever_inicio(mp4, 16)
    if not ws:
        return None, None
    tk = [norm(w['w']) for w in ws]
    k = None
    for i in range(len(tk) - 3):
        if tk[i:i + 2] == alvo_fim and tk[i + 2:i + 4] == alvo_ini:
            k = i + 2; break
    if k is None:
        k = next((i for i in range(1, len(tk) - 1) if tk[i:i + 2] == alvo_ini), None)
    if k is None:
        return None, None
    # janela: do meio da última palavra do hook ao meio da 1ª da hold
    a = (ws[k - 1]['s'] + ws[k - 1]['e']) / 2; b = (ws[k]['s'] + ws[k]['e']) / 2
    sil = silencio_voz(mp4, a, b)
    return (round(sil, 3) if sil is not None else round(ws[k]['s'] - ws[k - 1]['e'], 3)), ws[k - 1]['e']


def vocab_legenda(B, F, plano):
    """Palavras que podem aparecer como legenda/header: SRTs da batch, falas, header e textos do plano."""
    txt = ' '.join(plano.get('hold', []) + [f.get('texto', '') for f in plano.get('falas', [])])
    for k in ('header', 'hook_header', 'titulo_hook', 'tag_hook'):
        txt += ' ' + json.dumps(plano.get(k, ''), ensure_ascii=False)
    txt += ' ' + ' '.join(c.get(k, '') for c in plano.get('cenas', []) for k in ('callout', 'destaque') if isinstance(c.get(k), str))
    for srt in glob.glob(os.path.join(glob.escape(B), getattr(F, 'AUTO', '08_auto'), 'legendas', '*.srt')):
        txt += ' ' + open(srt, encoding='utf-8', errors='ignore').read()
    txt = txt.replace('{MARCA}', ' '.join(F.marca_nome(plano, p) for p in plano.get('produtos', [])))
    return {norm(w) for w in txt.split() if len(norm(w)) >= 2}


def caixas_texto_export(textos, marcas, vocab):
    """Caixas de legenda/header do export: texto que bate com a legenda/header da batch e não é do rótulo."""
    rz = rotulo_zona(textos, marcas)
    out = []
    for t in textos:
        if rz and sobre(t['b'], rz) > 0.5: continue
        ws = [norm(w) for w in t['t'].split() if len(norm(w)) >= 2]
        if not ws or t['b'][3] < 0.015: continue
        if sum(w in vocab for w in ws) / len(ws) < 0.6: continue    # texto da cena (rótulo, tela), não legenda
        if len(ws) == 1 and any(norm(m) == ws[0] for m in marcas) and rz: continue   # nome no rótulo
        out.append((t['t'], t['b']))
    return out


# ------------------------------------------------------------------ regras
def achado(lista, nivel, regra, ini, fim, msg):
    lista.append({'nivel': nivel, 'regra': regra, 'ini': round(ini, 2), 'fim': round(fim, 2), 'msg': msg})


def regras_tempo(planos, em, achados, cen=None):
    reais = [p for p in planos if p['fim'] - p['ini'] > 0.04]
    # 3D
    for k, p in enumerate(reais):
        c = p.get('c') or (cen or {}).get(p.get('cena'))
        p['3d'] = p['tipo'] == 'broll' and eh_3d(c, p.get('arq') or '')
    for k, p in enumerate(reais):
        if not p['3d']: continue
        d = p['fim'] - p['ini']
        nome = p.get('cena') or os.path.basename(p.get('arq') or '?')
        if d > LIM_3D + 0.05:
            achado(achados, 'erro', '3d_longo', p['ini'], p['fim'], f'3D {nome} com {d:.2f} s (máx. {LIM_3D} s)')
        # próximo 3D sem plano real de >= 0,5 s no meio
        for q in reais[k + 1:]:
            if q['3d']:
                if (q.get('arq') or q.get('cena')) != (p.get('arq') or p.get('cena')) or True:
                    nq = q.get('cena') or os.path.basename(q.get('arq') or '?')
                    achado(achados, 'erro', '3d_seguido', p['ini'], q['fim'], f'3D seguido: {nome} → {nq}')
                break
            if q['fim'] - q['ini'] >= GAP_REAL:
                break
    # parado
    for p in reais:
        d = p['fim'] - p['ini']
        if d <= LIM_PARADO + 0.05: continue
        if p['tipo'] == 'broll':
            c = p.get('c') or {}
            if c.get('push_in') or c.get('zoom'):
                achado(achados, 'aviso', 'parado', p['ini'], p['fim'], f"b-roll {p.get('cena') or os.path.basename(p['arq'])} com {d:.1f} s (tem push-in; confira o movimento)")
            else:
                achado(achados, 'erro', 'parado', p['ini'], p['fim'], f"b-roll {p.get('cena') or os.path.basename(p['arq'])} com {d:.1f} s sem troca (máx. {LIM_PARADO:g} s)")
        elif p['tipo'] in ('avatar', 'vazio'):
            cortes = [e for e in (em or []) if p['ini'] + 0.05 < e < p['fim'] - 0.05]
            marcas = [p['ini']] + cortes + [p['fim']]
            maior = max(b - a for a, b in zip(marcas, marcas[1:]))
            if maior > LIM_PARADO + 0.05:
                achado(achados, 'erro', 'parado', p['ini'], p['fim'], f"{p['tipo']} {maior:.1f} s sem corte (máx. {LIM_PARADO:g} s)")


def lint_ad(F, B, plano, cfg, p, n, export=None, usar_visao=True, tmp=None):
    achados, info = [], {}
    cen = {c['id']: c for c in plano['cenas']}
    marcas = [F.marca_nome(plano, x) for x in plano.get('produtos', [])]
    if export:
        sem_av = plano.get('estilo', {}).get('avatar', {}).get('enquadramento') in ('nenhum', 'pip')
        planos, err = linha_do_tempo_export(B, export, F, sem_av)
        if err: achado(achados, 'aviso', 'leitura', 0, 0, err)
        # liga cada clipe à cena do plano pelo id no nome (S12_... → S12)
        for q in planos:
            if q.get('arq'):
                cid = os.path.basename(q['arq']).split('_')[0]
                if cid in cen: q['cena'] = cid; q['c'] = cen[cid]
        em = []
        desconhecido = sum(q['fim'] - q['ini'] for q in planos if q['tipo'] == '?')
        if desconhecido > 2:
            achado(achados, 'aviso', 'leitura', 0, 0, f'{desconhecido:.1f} s do export não casaram com clipe nenhum da batch')
        # avatar no export: corte = troca de enquadramento (ritmo.py mede); aqui usa o ritmo para os trechos parados
        try:
            import ritmo
            tempos, _ = ritmo.mudancas(export, 0.3)
            em = tempos
        except Exception as e:
            achado(achados, 'aviso', 'leitura', 0, 0, f'ritmo.py não rodou: {e}')
        pausa, fim_hook = pausa_hook_hold_export(export, F.texto_hook(plano, n, F.hook_marca(plano, n, p)[1]),
                                                 F.texto_hold(plano, p))
        info['hook_fim'] = fim_hook
        if pausa is None:
            achado(achados, 'aviso', 'hook_hold', 0, 0, 'não achei a emenda hook → hold na transcrição do export')
    else:
        try:
            planos, HD, em, PL = linha_do_tempo_plano(F, B, plano, cfg, p, n)
        except SystemExit as e:
            achado(achados, 'aviso', 'leitura', 0, 0, f'não montei a linha do tempo do plano: {e}')
            return achados, info
        except (OSError, ValueError, KeyError) as e:
            achado(achados, 'aviso', 'leitura', 0, 0, f'falta insumo para a linha do tempo ({e}); rode `fluxo.py fazer --ate legendas`')
            return achados, info
        info['hook_fim'] = HD
        pausa = pausa_hook_hold_plano(F, B, plano, p, n, HD, PL)
        fim_hook = HD
        if pausa is None:
            achado(achados, 'aviso', 'hook_hold', HD, HD, 'sem palavras do hook ou da hold para medir a pausa')
    if pausa is not None:
        info['pausa_hook_hold'] = pausa
        if pausa < LIM_PAUSA:
            achado(achados, 'erro', 'hook_hold', fim_hook or 0, (fim_hook or 0) + max(pausa, 0),
                   f'pausa hook → hold de {pausa:.2f} s (mín. {LIM_PAUSA:.2f} s; abrir com respiro_hook_s_H{n})')
    regras_tempo(planos, em, achados, cen)
    # trilha
    if eh_daniel(B, plano, cfg):
        tr = glob.glob(os.path.join(glob.escape(B), getattr(F, 'AUDIO', '02_audio'), 'trilha', '*.mp3')) + \
             glob.glob(os.path.join(glob.escape(B), getattr(F, 'AUDIO', '02_audio'), 'trilha', '*.wav'))
        if not tr:
            achado(achados, 'erro', 'trilha', 0, 0, 'AD do Daniel sem trilha (02_audio/trilha/ vazia): gerar no Kie (kie.py suno)')
    # texto em cima de rosto ou rótulo
    if usar_visao:
        zonas_texto(F, B, plano, planos, p, n, export, marcas, achados, tmp, info)
    else:
        achado(achados, 'aviso', 'rosto', 0, 0, 'visão desligada: legenda/header × rosto e rótulo não conferidos')
    info['planos'] = [{k: (round(v, 2) if isinstance(v, float) else v) for k, v in q.items() if k in ('ini', 'fim', 'tipo', 'cena', '3d')}
                      for q in planos]
    return achados, info


def zonas_texto(F, B, plano, planos, p, n, export, marcas, achados, tmp, info):
    import visao
    est = plano.get('estilo', {}); leg = est.get('legenda', {})
    # legenda SEMPRE pílula (pilula.py): corpo fixo de 42,5 px; o plano só muda a altura (padrão 0.63, regra da EV)
    y0 = float(leg.get('y', 0.63)); tam = 42.5; lin = int(leg.get('linhas', 2) or 2)
    # Legenda prevista só onde ela existe (BATCH#4607, 17/11/2026: com hook_card o hook não tem legenda e o lint
    # acusava "rótulo" falso). Com o SRT do AD: vale o SRT. Sem SRT: no hook com card, sem legenda; no resto, com.
    legs = None
    try:
        srt = F.L(B, f'AD{n}_{p}.srt')
        if os.path.exists(srt): legs = [(a, b) for a, b, _ in F.ler_srt(srt)]
    except Exception:
        legs = None
    card = bool((plano.get('hook_card') or {}).get(str(n)))
    def tem_legenda(t):
        if legs is not None: return any(a - 0.05 <= t <= b + 0.05 for a, b in legs)
        return not (card and t < (info.get('hook_fim') or 0))
    pedidos = []      # (plano, t_no_ad, img_origem, img_export)
    for k, q in enumerate(planos):
        if q['fim'] - q['ini'] < 0.3 or q['tipo'] == '?': continue
        meio = (q['ini'] + q['fim']) / 2
        for j, t in enumerate(sorted({q['ini'] + 0.15, meio})):
            src = None
            if q['tipo'] == 'broll' and q.get('arq'):
                src = quadro(q['arq'], q['off'] + (t - q['ini']), os.path.join(tmp, f'o_{n}_{k}_{j}.jpg'))
            ex = quadro(export, t, os.path.join(tmp, f'e_{n}_{k}_{j}.jpg')) if export else None
            if not export and q['tipo'] == 'avatar':
                f, pm, hs = F.hook_marca(plano, n, p)
                src = quadro(F.fala_mp4(B, f, pm), 1.0, os.path.join(tmp, f'a_{n}_{k}_{j}.jpg')) if t < (info.get('hook_fim') or 0) else None
            pedidos.append((q, t, src, ex))
    imgs = [x for _, _, s, e in pedidos for x in (s, e) if x]
    vis = visao.ler(imgs)
    if imgs and not vis:
        achado(achados, 'aviso', 'rosto', 0, 0, 'visão do Mac indisponível (swiftc): legenda/header × rosto e rótulo não conferidos')
        return
    vistos = set()
    vocab = vocab_legenda(B, F, plano) if export else set()
    for q, t, src, ex in pedidos:
        vs = vis.get(src, {}) if src else {}
        ve = vis.get(ex, {}) if ex else {}
        rostos = ve.get('rostos') or vs.get('rostos') or []
        rot = rotulo_zona(vs.get('textos', []), marcas) if vs else None
        if not rot and ve: rot = rotulo_zona(ve.get('textos', []), marcas)
        if export:
            caixas = caixas_texto_export(ve.get('textos', []), marcas, vocab)
        else:
            c = q.get('c') or {}
            y = float(c.get('legenda_y', y0))
            caixas = [('legenda (prevista)', caixa_legenda(y, lin, tam))] if tem_legenda(t) else []
            if t < (info.get('hook_fim') or 0):
                hp = est.get('header_pilula') or {}
                hy = (hp.get('y_hook', {}) or {}).get(str(n), hp.get('y')) if (plano.get('header') or hp) else None
                if plano.get('header') and hy:
                    caixas.append(('header (previsto)', [0.1, float(hy) / 1920, 0.8, 2 * float(hp.get('tamanho', 52)) * 1.35 / 1920]))
        for tipo, nome, f in testar_zonas([(nm, cx) for nm, cx in caixas], rostos, rot):
            chave = (tipo, q.get('cena') or q.get('arq') or q['tipo'], norm(nome))
            if chave in vistos: continue
            vistos.add(chave)
            onde = q.get('cena') or (os.path.basename(q['arq']) if q.get('arq') else q['tipo'])
            alvo = 'o rosto' if tipo == 'rosto' else 'o rótulo do frasco'
            nivel = 'erro' if export or tipo == 'rotulo' or q['tipo'] == 'broll' else 'aviso'
            achado(achados, nivel, tipo, q['ini'], q['fim'], f'"{nome}" em cima de {alvo} ({onde}, {int(f * 100)}% da caixa)')


# ------------------------------------------------------------------ saída
def mmss(t): return f'{int(t // 60)}:{t % 60:05.2f}'


BRIEF_DESDE = 1794538800   # 13/11/2026 00:00 (Brasília): batches criadas a partir daqui precisam do brief_regras


def criada_em(B):
    st = os.stat(B)
    return getattr(st, 'st_birthtime', None) or (st.st_ctime if os.name == 'nt' else st.st_mtime)


def lint_brief(B, plano, F):
    """Brief antes do ref (Louise, 13/11/2026; Frente 4 H): o 02_referencia grava no plano as instruções escritas do
    brief/card ("brief_regras") e os conflitos com o ref ("brief_conflitos", cada um com a decisão do Fefo). Batch nova
    sem isso, ou conflito sem decisão, é erro. Batch de antes de 13/11 sem o campo: só aviso."""
    ach = []
    nova = criada_em(B) >= BRIEF_DESDE and not os.path.isdir(os.path.join(B, F.EXPORT, '_old'))
    if 'brief_regras' not in plano:
        ach.append({'nivel': 'erro' if nova else 'aviso', 'regra': 'brief', 'ini': 0, 'fim': 0,
                    'msg': 'plano.json sem "brief_regras": leia o brief e o card antes do ref (modulos/02_referencia.md, passo 0b). '
                           'Sem instrução escrita: "brief_regras": [] e "brief_lido": "<onde leu>".'})
    for c in plano.get('brief_conflitos', []) or []:
        if isinstance(c, str):   # forma curta (BATCH#4607, 17/11/2026): "brief x ref -> decisão do Fefo: ..."
            if 'fefo' not in c.lower():
                ach.append({'nivel': 'erro', 'regra': 'brief', 'ini': 0, 'fim': 0,
                            'msg': f'conflito brief x ref sem decisão do Fefo: "{c[:120]}" (escreva "decisão do Fefo: ..." no texto)'})
            continue
        if not isinstance(c, dict):
            ach.append({'nivel': 'erro', 'regra': 'brief', 'ini': 0, 'fim': 0,
                        'msg': f'brief_conflitos: item ilegível ({type(c).__name__}); use texto ou {{"brief", "ref", "decisao_fefo"}}'})
            continue
        if not str(c.get('decisao_fefo', '')).strip():
            ach.append({'nivel': 'erro', 'regra': 'brief', 'ini': 0, 'fim': 0,
                        'msg': f"conflito brief x ref sem decisão do Fefo: brief \"{str(c.get('brief', ''))[:60]}\" x ref \"{str(c.get('ref', ''))[:60]}\""})
    return ach


MIX_DESDE = 1794970800     # 18/11/2026 00:00 (Brasília): trava de real x IA (Umut 17/11 + skill do Matthew, Fefo 18/11)
WPS = 2.2                  # palavras por segundo da VO destes ADs (medido pelo Matthew: ~181 wpm)
MECANISMO = ('mecanismo', 'mechanism', 'macula', 'mácula', 'retina', 'retin', 'barreira', 'barrier', 'vaso', 'vessel',
             'fotorrecept', 'photorecept', 'pigmento', 'pigment', 'dentro do olho', 'inside', 'celula', 'célula', 'cell',
             'sangue', 'blood', 'nervo', 'nerve', 'proteina', 'proteína', 'protein', 'cristalino', 'lens', '3d')

def origem_cena(c):
    """real | ia | avatar | camada. Campo "origem" do plano manda; sem ele, lê o texto de "fonte"/"banco"."""
    o = str(c.get('origem', '')).strip().lower()
    if o in ('real', 'ia', 'avatar', 'camada', 'packshot'): return 'real' if o == 'packshot' else o
    t = ' '.join(str(c.get(k, '')) for k in ('fonte', 'banco', 'tipo')).lower()
    if 'camada' in t or 'local (camada' in t: return 'camada'
    if 'avatar' in t or 'omni' in t: return 'avatar'
    if any(k in t for k in ('real', 'stock', 'packshot', 'reuse banco', 'banco ev', 'criador', 'ugc')): return 'real'
    if any(k in t for k in ('ia', 'new', 'kling', 'seedance', '3d', 'gerad', 'ai')): return 'ia'
    return '?'

def dur_cena(c):
    if isinstance(c.get('dur'), (int, float)) and c['dur'] > 0: return float(c['dur'])
    return len(str(c.get('copy', '')).split()) / WPS

def lint_mix(B, plano):
    """Real x IA em SEGUNDOS de tela (Umut 17/11/2026: 70% b-roll real, IA só no mecanismo; skill do Matthew, Fefo
    18/11/2026: "Aplica as duas"). Conta só b-roll (avatar e camada ficam fora). Batch criada a partir de 18/11: erro.
    Antes: aviso. Também avisa cena com mais de 3 s sem 2+ planos ("planos" no plano) e IA fora do mecanismo."""
    nova = criada_em(B) >= MIX_DESDE
    nv = 'erro' if nova else 'aviso'
    ach, soma, sem = [], {'real': 0.0, 'ia': 0.0, 'avatar': 0.0, 'camada': 0.0, '?': 0.0}, []
    mae = {}                              # gêmea (ex. 4615 ES): a origem do b-roll vem do plano da mãe (ex. 4614)
    try:
        for irma in os.listdir(os.path.dirname(B)):
            pm = os.path.join(os.path.dirname(B), irma, '08_auto', 'plano.json')
            if irma != os.path.basename(B) and os.path.exists(pm):
                dm = json.load(open(pm, encoding='utf-8'))
                if str((dm.get('gemea') or {}).get('batch', '')) == os.path.basename(B):
                    mae = {c.get('id'): c for c in dm.get('cenas', []) if isinstance(c, dict)}; break
    except (OSError, ValueError):
        pass
    for c in plano.get('cenas', []) or []:
        if not isinstance(c, dict): continue
        o, d = origem_cena(c), dur_cena(c)
        if o == '?' and c.get('id') in mae:
            o = origem_cena(mae[c.get('id')])
        soma[o] += d
        if o == '?': sem.append(c.get('id'))
        if o == 'ia':
            txt = ' '.join(str(c.get(k, '')) for k in ('nome', 'mostra', 'copy', 'fonte', 'tipo')).lower()
            if not any(k in txt for k in MECANISMO):
                ach.append({'nivel': nv, 'regra': 'mix', 'ini': 0, 'fim': 0,
                            'msg': f"{c.get('id')}: IA fora do mecanismo (\"{str(c.get('mostra') or c.get('copy'))[:70]}\"). "
                                   "Busque vídeo real no banco (real=1) ou marque o porquê em \"origem_motivo\"."})
        # teto de 2,5 s por plano (Fefo, 20/11/2026; antes 3 s, Umut/Daniel); 0.05 de folga para arredondamento
        if o in ('real', 'ia') and d > 2.55 and int(c.get('planos', 1) or 1) < -(-d // 2.5) and not c.get('origem_motivo'):
            ach.append({'nivel': 'aviso', 'regra': 'mix', 'ini': 0, 'fim': 0,
                        'msg': f"{c.get('id')}: ~{d:.1f} s num plano só; nada passa de 2,5 s (Fefo, 20/11): divida ou ponha \"planos\": {int(-(-d // 2.5))}"})
    br = soma['real'] + soma['ia']
    if br > 0:
        pr = soma['real'] / br
        msg = (f"b-roll real {soma['real']:.1f} s / {br:.1f} s = {pr:.0%} (mínimo 70%); IA {soma['ia']:.1f} s; "
               f"avatar {soma['avatar']:.1f} s (fora da conta)")
        if pr < 0.70:
            ach.append({'nivel': nv, 'regra': 'mix', 'ini': 0, 'fim': 0, 'msg': msg + ". Troque cenas de IA por vídeo real do banco (real=1)."})
        else:
            print(f"mix: {msg}")
    if sem:
        ach.append({'nivel': 'aviso', 'regra': 'mix', 'ini': 0, 'fim': 0,
                    'msg': f"sem origem clara: {', '.join(map(str, sem))}. Ponha \"origem\": real|ia|avatar|camada em cada cena."})
    return ach


def main():
    try:                                  # console do Windows (cp1252) não imprime ✖ (18/11/2026)
        sys.stdout.reconfigure(encoding='utf-8', errors='replace'); sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('batch'); ap.add_argument('--ad', action='append', help='ex.: AD1_neurobella (padrão: todos)')
    ap.add_argument('--export', action='append', help='MP4 exportado (nome com ADn e a marca)')
    ap.add_argument('--json', action='store_true'); ap.add_argument('--sem-visao', action='store_true')
    a = ap.parse_args()
    B = os.path.abspath(a.batch.rstrip('/'))
    if not os.path.isdir(B):
        print(f'não achei a batch: {B}', file=sys.stderr); sys.exit(2)
    try:
        F = carregar_fluxo(B)
    except SystemExit as e:
        print(f'fluxo.py recusou a pasta: {e}', file=sys.stderr); sys.exit(2)
    if not os.path.exists(os.path.join(B, F.AUTO, 'plano.json')):
        print(f'sem {F.AUTO}/plano.json: o lint é do motor plano (Empire Vision). Pulado.'); sys.exit(0)
    plano, cfg = F.carregar(B)
    alvos = []
    if a.export:
        for mp4 in a.export:
            nome = os.path.basename(mp4)
            m = re.search(r'AD(\d+)', nome)
            p = next((x for x in plano['produtos'] if x.lower() in nome.lower()), plano['produtos'][0])
            if not m:
                print(f'não sei o AD de {nome} (falta "AD<n>" no nome)', file=sys.stderr); sys.exit(2)
            alvos.append((p, int(m[1]), os.path.abspath(mp4)))
    else:
        for p in plano['produtos']:
            for n in F.hooks(plano):
                if a.ad and f'AD{n}_{p}' not in a.ad: continue
                alvos.append((p, n, None))
    tmp = tempfile.mkdtemp(prefix='lint_plano_')
    res, erros = {}, 0
    ab = lint_brief(B, plano, F) + lint_mix(B, plano)
    if ab:
        res['brief'] = {'achados': ab}; erros += sum(1 for x in ab if x['nivel'] == 'erro')
        print(f"brief: {sum(1 for x in ab if x['nivel'] == 'erro')} erro(s), {sum(1 for x in ab if x['nivel'] != 'erro')} aviso(s)")
        for x in ab: print(f"  {'✖' if x['nivel'] == 'erro' else '!'} {x['regra']:<10} {x['msg']}")
    for p, n, mp4 in alvos:
        chave = f'AD{n}_{p}'
        ach, info = lint_ad(F, B, plano, cfg, p, n, mp4, not a.sem_visao, tmp)
        res[chave] = {'export': mp4, **info, 'achados': ach}
        ne = sum(1 for x in ach if x['nivel'] == 'erro'); erros += ne
        print(f"{chave}{' (export)' if mp4 else ' (plano)'}: {ne} erro(s), {len(ach) - ne} aviso(s)"
              + (f", hook acaba em {info['hook_fim']:.2f} s" if info.get('hook_fim') else '')
              + (f", pausa hook→hold {info['pausa_hook_hold']:.2f} s" if info.get('pausa_hook_hold') is not None else ''))
        for x in sorted(ach, key=lambda x: (x['nivel'] != 'erro', x['ini'])):
            print(f"  {'✖' if x['nivel'] == 'erro' else '!'} {x['regra']:<10} {mmss(x['ini'])}–{mmss(x['fim'])}  {x['msg']}")
    if a.json or os.environ.get('FLUXO_CHECAR'):
        out = os.path.join(B, F.AUTO, 'lint_plano.json' if not a.export else 'lint_export.json')
        json.dump({'batch': os.path.basename(B), 'modo': 'export' if a.export else 'plano', 'erros': erros, 'ads': res},
                  open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'gravado {out}')
    print(f"lint_plano: {'TRAVA' if erros else 'ok'} ({erros} erro(s) em {len(res)} AD(s))")
    sys.exit(1 if erros else 0)


if __name__ == '__main__':
    main()
