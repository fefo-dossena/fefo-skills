#!/usr/bin/env python3
"""Qualidade antes de gerar (PDF do Lucas, 16/11/2026; regra em _FLUXO/QUALIDADE_DO_BATCH.md).

  py prompt_qa.py checar PROMPT.txt|PASTA [...] [--imagem]
        # estrutura fixa, 140+ palavras, @image com função, START = END do anterior, NEVER da cena, verbos vagos
        # + skills do Joey (18/11/2026): tempos dos shots, contagem, palavras/s, teto do modelo, lente em graus,
        #   ouvinte com ação, left/right rotulado, FORMAT sem texto de tela, SOUND com "no music", START FRAME contínuo
  py prompt_qa.py folha PASTA_DOS_PROMPTS [--lote PEDIDOS.json]
        # monta folha_logica.md + folha_logica.json (clipe | START | planos | END | NEVER | quadro inicial)
  py prompt_qa.py ok FOLHA.json CLIPE [CLIPE ...]|--todos --nota "1-6 ok: ..."
        # grava o ok de cada clipe com o hash do prompt (mudou o prompt = precisa de novo ok)
  py prompt_qa.py veredito CLIPE.mp4 ok|parcial|reroll [--faixa 2.0-6.5] [--motivo "..."]
        # veredito por clipe em vereditos.json; avisa quando o clipe já foi regerado 1 vez
  py prompt_qa.py metricas PASTA --master A.mp4 [--master B.mp4] [--cr 1234]
        # segundos gerados, crédito, refeitos, aproveitamento (meta 70%) e crédito por segundo final (meta <= 7)

MODO CURTO (17/11/2026, BATCH#4611): prompt de até 300 caracteres (OmniHuman e qualquer modelo com esse limite; o
prompt completo nunca cabe nisso) dispensa os 12 campos e as 140 palavras, mas precisa de uma trava curta: um NEVER
ou uma frase de restrição ("never", "do not", "must not", "stays identical/still/unchanged", "no ..."). A folha e o ok
continuam obrigatórios, com o mesmo hash.

A trava do kie.py usa exigir_ok(): clipe de vídeo só sai com ok na folha_logica.json da pasta do prompt
(ou de até 3 pastas acima) e com o mesmo texto do ok.
"""
import argparse, glob, hashlib, json, os, re, subprocess, sys, time

CAMPOS = [  # (nome, regex do início da linha), na ordem do PDF
    ('TITLE', r'TITLE\s*:'),
    ('FORMAT', r'FORMAT\s*:'),
    ('CHARACTERS', r'(CHARACTERS|CAST)\s*:'),
    ('REFERENCES', r'REFERENCES\s*:'),
    ('PLACE AND LIGHT', r'(PLACE AND LIGHT|LOCATION)\s*:'),
    ('POSITION', r'POSITION(\s*\(locked\))?\s*:'),
    ('STATE AT START', r'STATE AT START\s*:'),
    ('Shot 1', r'Shot\s*1\b'),
    ('SOUND', r'SOUND\s*:'),
    ('STYLE', r'STYLE\s*:'),
    ('STATE AT END', r'STATE AT END\s*:'),
    ('NEVER', r'NEVER\s*:'),
]
VAGOS = re.compile(r'\b(attacks?|attacking|fights?|fighting|moves?|moving around)\b', re.I)
CAMERAS = re.compile(r'\b(dolly|pan|pans|tilt|truck|zoom|push-in|push in|pull-back|pull back|orbit|arc|crane|handheld|whip)\b', re.I)
STOP = set('the a an and or of in on at to with from his her their its is are be stays stay every never nobody one two '
           'into onto over under behind front side left right frame shot scene this that'.split())
MIN_PALAVRAS = 140
LIMITE_CURTO = 300   # caracteres: até aqui o prompt é do modo curto (limite do OmniHuman 2.0 no Kie)
RESTRICAO = re.compile(r"\bnever\b|\bmust not\b|\bdo(?:es)? not\b|\bdon'?t\b|\bdoesn'?t\b|\bcannot\b|\bcan'?t\b|"
                       r"\bno (?!one\b)\w+|\bwithout\b|\b(?:stays?|remains?|keeps?|kept|held|holds?)\b[^.]{0,40}?"
                       r"\b(?:still|identical|unchanged|the same|fixed|steady|sharp|legible)\b", re.I)

# Checagens das skills do Joey (Fefo, 18/11/2026: "Aplica as 5"; regra em _FLUXO/feedback/2026-11-18_skills_joey/COMPARACAO.md).
# Valem só no modo completo; o modo curto (<= 300 caracteres) segue só com a trava curta.
FRASES_FIXAS = re.compile(r'already in motion at frame one;?\s*no static or posed hold\.?|'
                          r'continues directly from @\s*image\s*_?\s*\d+\s*:[^.]*\.?', re.I)  # não contam no START = END
NUM_PALAVRA = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10}
TEMPO_FAIXA = re.compile(r'Shot\s*(\d+)\s*\(\s*(?:Duration:\s*)?([\d.]+)\s*s?\s*[-–]\s*([\d.]+)\s*(?:s|sec|seconds?)?\s*\)', re.I)
TEMPO_DUR = re.compile(r'Shot\s*(\d+)\s*\(\s*(?:Duration:\s*)?([\d.]+)\s*(?:s|sec|seconds?)\s*\)', re.I)
FALA = re.compile(r':\s*["“]([^"”]+)["”]')   # fala = aspas logo depois de dois-pontos (NOME (tom): "...")
LADO = re.compile(r'\b(?:the|to|his|her|their|its|bottom|top|lower|upper|far)\s+(left|right)\b', re.I)  # direção, não "right now"
LADO_OK_ANTES = re.compile(r'(screen|frame|camera)[\s-]*$|\bown\s*$', re.I)
LADO_OK_DEPOIS = re.compile(r'^\s*(of\s+(the\s+)?(frame|screen)|-?\s*(frame|screen)\b|'
                            r'(hand|hands|arm|arms|eye|eyes|ear|ears|foot|feet|leg|legs|shoulder|cheek|knee|wrist|thumb|'
                            r'palm|elbow|hip|temple|eyebrow|brow|nostril)\b|[\w\'’]*\s*(eye|ear|hand)\'?s?\b)', re.I)
MM = re.compile(r'\b\d+(?:\.\d+)?\s?mm\b', re.I)


def _num(s):
    s = s.lower()
    return int(s) if s.isdigit() else NUM_PALAVRA.get(s)


def _dur_format(fmt):
    m = re.search(r'\b(\d+(?:\.\d+)?)\s*(?:s|sec|seconds?)\b', fmt or '', re.I)
    return float(m.group(1)) if m else None


def tempos_dos_shots(shots):
    """[(n, ini, fim) ou (n, None, dur)] pelo rótulo de cada shot; None se algum shot não tem tempo."""
    out = []
    for s in shots:
        cab = s.split('\n')[0]
        m = TEMPO_FAIXA.search(cab)
        if m:
            out.append((int(m.group(1)), float(m.group(2)), float(m.group(3))))
            continue
        m = TEMPO_DUR.search(cab)
        if m:
            out.append((int(m.group(1)), None, float(m.group(2))))
            continue
        return None
    return out


def falas_do_shot(s, nomes):
    """[(quem, texto)] das falas do shot; quem = último rótulo citado antes dos dois-pontos (ou '')."""
    out = []
    for m in FALA.finditer(s):
        antes = s[max(0, m.start() - 80):m.start()]
        quem = ''
        melhor = -1
        for n in nomes:
            for x in re.finditer(rf'\b{re.escape(n)}\b', antes, re.I):
                if x.start() > melhor:
                    melhor, quem = x.start(), n
        out.append((quem, m.group(1)))
    return out


def checar_joey(arq, t, b, nomes):
    """Checagens 1-9 e 12 do COMPARACAO.md. Devolve (erros, avisos)."""
    erros, avisos = [], []
    fmt = b.get('FORMAT', '')
    shots = b.get('Shots', [])
    dur = _dur_format(fmt)
    tempos = tempos_dos_shots(shots) if shots else None
    # 1. soma dos tempos (erro)
    if tempos and dur:
        if all(i is not None for _, i, _ in tempos):
            fura = []
            if abs(tempos[0][1]) > 0.05:
                fura.append(f'Shot {tempos[0][0]} começa em {tempos[0][1]:g} s, não em 0')
            for (n0, _, f0), (n1, i1, _) in zip(tempos, tempos[1:]):
                if abs(i1 - f0) > 0.05:
                    fura.append(f'Shot {n0} termina em {f0:g} s e Shot {n1} começa em {i1:g} s')
            if abs(tempos[-1][2] - dur) > 0.05:
                fura.append(f'último shot termina em {tempos[-1][2]:g} s e o FORMAT diz {dur:g} s')
            if fura:
                erros.append('tempos dos shots: ' + '; '.join(fura))
        elif all(i is None for _, i, _ in tempos):
            soma = sum(d for _, _, d in tempos)
            if abs(soma - dur) > 0.05:
                erros.append(f'tempos dos shots somam {soma:g} s e o FORMAT diz {dur:g} s')
    # 2. contagem declarada (erro)
    m = re.search(r'exactly\s+(\w+)\s+shots?\b', fmt, re.I)
    if m and _num(m.group(1)) is not None and _num(m.group(1)) != len(shots):
        erros.append(f'FORMAT diz exactly {m.group(1)} shots e o prompt tem {len(shots)}')
    falas = [(i, falas_do_shot(s, nomes)) for i, s in enumerate(shots)]
    m = re.search(r'exactly\s+(\w+)\s+spoken\s+lines?\b', fmt, re.I)
    total = sum(len(f) for _, f in falas)
    if m and _num(m.group(1)) is not None and _num(m.group(1)) != total:
        erros.append(f'FORMAT diz exactly {m.group(1)} spoken lines e os shots têm {total} falas entre aspas')
    # 3. fala por segundo (aviso > 3, erro > 3,5)
    if tempos:
        for (i, fs), (n, ini, fim) in zip(falas, tempos):
            seg = (fim - ini) if ini is not None else fim
            pal = sum(len(re.findall(r"[A-Za-z0-9'’-]+", x)) for _, x in fs)
            if not fs or seg <= 0:
                continue
            ps = pal / seg
            if ps > 3.5:
                erros.append(f'Shot {n}: {pal} palavras em {seg:g} s = {ps:.1f} palavras/s (máximo 3,5; fala nunca acelerada)')
            elif ps > 3.0:
                avisos.append(f'Shot {n}: {pal} palavras em {seg:g} s = {ps:.1f} palavras/s (acima de 3; confira o ritmo natural)')
    # 4. teto do modelo (erro)
    mod = fmt.lower()
    teto = None
    if 'kling' in mod:
        teto = (15, 'Kling')
    elif re.search(r'seedance\s*2\.5', mod):
        teto = (30, 'Seedance 2.5')
    elif re.search(r'seedance\s*2(?:\.0)?(?![.\d])', mod):
        teto = (15, 'Seedance 2.0')
        nrefs = len(set(re.findall(r'@\s*[Ii]mage\s*_?\s*(\d+)', b.get('REFERENCES', ''))))
        if nrefs > 9:
            erros.append(f'Seedance 2.0 aceita até 9 referências; o prompt tem {nrefs}')
    elif re.search(r'\bomni\b(?!\s*-?\s*human)', mod) and 'trendscale' in os.path.abspath(arq).lower():
        teto = (10, 'Omni da TS')
    if teto and dur and dur > teto[0]:
        erros.append(f'{dur:g} s passa do teto do {teto[1]} ({teto[0]} s por geração)')
    # 5. lente em mm sem graus (aviso)
    soltas = [x.group(0) for x in MM.finditer(t) if '°' not in t[max(0, x.start() - 14):x.start()]]
    if soltas:
        avisos.append('lente em mm sem graus: ' + ', '.join(sorted(set(soltas))) + ' (escreva "47° (50mm)")')
    # 6. ouvinte sem ação (aviso)
    for s, (_, fs) in zip(shots, falas):
        if not fs or len(nomes) < 2:
            continue
        falam = {q for q, _ in fs if q}
        for n in nomes:
            if n in falam or not re.search(rf'\b{re.escape(n)}\b', s, re.I):
                continue
            if not re.search(rf'\b{re.escape(n)}\b[^.]{{0,20}}\bsays nothing\b', s, re.I):
                avisos.append(f'{s.split(":")[0][:20]}: {n} está no shot e não fala; escreva "{n} says nothing in this shot: <ação concreta>."')
    # 7. left/right sem rótulo (aviso)
    soltos = []
    for x in LADO.finditer(t):
        if LADO_OK_ANTES.search(t[max(0, x.start(1) - 12):x.start(1)]) or LADO_OK_DEPOIS.match(t[x.end():x.end() + 30]):
            continue
        soltos.append(t[max(0, x.start() - 15):x.end()].replace('\n', ' ').strip())
    if soltos:
        avisos.append(f'{len(soltos)} left/right sem screen-/frame/camera-/own (ex.: "…{soltos[0]}"); '
                      'escreva screen-left/right ou "her own right"')
    # 8. FORMAT sem "no on-screen text" (aviso)
    if 'FORMAT' in b and not re.search(r'no on-screen text', fmt, re.I):
        avisos.append('FORMAT sem "No on-screen text of any kind: no captions, subtitles, titles, watermarks or logos; '
                      'only real printed text on physical objects."')
    # 9. SOUND sem "no music" (erro em clipe com som)
    som = b.get('SOUND', '')
    if som and not re.match(r'\s*(none|no sound|silent|silence only|sound off)\b', som, re.I) \
            and not re.search(r'\bno music\b', som, re.I):
        erros.append('SOUND sem "no music" (clipe com som): termine com "No music, no score, no soundtrack, no humming, '
                     'no ambient pad, no swell, no drone, no off-frame voices."')
    # 12. START FRAME sem "continues directly from" (aviso)
    if re.search(r'START FRAME|last frame', b.get('REFERENCES', ''), re.I) and not re.search(r'continues directly from', t, re.I):
        avisos.append('START FRAME sem a frase de continuidade: "Continues directly from @imageN: same people, wardrobe, '
                      'place, light; motion resumes within the first quarter second; no re-establish."')
    return erros, avisos


def curto(t):
    return len(t.strip()) <= LIMITE_CURTO


def checar_curto(t):
    """Modo curto: só a trava curta. Devolve (erros, avisos, blocos) como o checar_um; NEVER = as frases de restrição."""
    frases = [f.strip() for f in re.split(r'(?<=[.!?])\s+', t.strip()) if f.strip()]
    trava = [f for f in frases if RESTRICAO.search(f)]
    erros = [] if trava else ['modo curto (até %d caracteres) sem trava: escreva um NEVER ou uma frase de restrição '
                              '(ex.: "The bottles never move; labels stay identical to the reference.")' % LIMITE_CURTO]
    avisos = [] if len(frases) > 1 else ['modo curto com uma frase só: diga também o que deve acontecer']
    v = sorted({x.lower() for f in frases if f not in trava for x in VAGOS.findall(f)})   # "never move" é trava, não verbo vago
    if v:
        avisos.append('verbo vago: ' + ', '.join(v))
    return erros, avisos, {'NEVER': ' '.join(trava), 'modo': 'curto'}


def texto(p):
    return open(p, encoding='utf-8').read().strip()


def hash_de(t):
    return hashlib.sha1(t.strip().encode('utf-8')).hexdigest()[:16]


def natural(s):
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r'(\d+)', s)]


def blocos(t):
    """{campo: texto} pelo início de linha de cada campo (o bloco vai até o próximo campo)."""
    linhas = t.splitlines()
    marcas = []
    for i, l in enumerate(linhas):
        for nome, rx in CAMPOS:
            if re.match(r'\s*' + rx, l):
                marcas.append((i, nome))
                break
        else:
            if re.match(r'\s*Shot\s*\d+', l):
                marcas.append((i, 'Shot'))
    out, ordem = {}, []
    for k, (i, nome) in enumerate(marcas):
        fim = marcas[k + 1][0] if k + 1 < len(marcas) else len(linhas)
        corpo = '\n'.join(linhas[i:fim])
        corpo = re.sub(r'^\s*[^:]+:\s*', '', corpo, count=1) if nome not in ('Shot 1', 'Shot') else corpo
        if nome == 'Shot':
            out.setdefault('Shots', []).append(corpo.strip())
        else:
            if nome == 'Shot 1':
                out.setdefault('Shots', []).insert(0, corpo.strip())
            out.setdefault(nome, corpo.strip())
            ordem.append(nome)
    return out, ordem


def norm(s):
    return re.sub(r'[^a-z0-9]+', ' ', (s or '').lower()).strip()


def rotulos(chars):
    return sorted(set(re.findall(r'\b([A-Z][A-Z\-]{2,})\b', chars or '')) - {'CHARACTERS', 'CAST', 'NEVER', 'VOICE'})


def cena_de(b, arq):
    t = b.get('TITLE', '')
    partes = [p.strip() for p in re.split(r'·|\|', t) if p.strip()]
    if len(partes) >= 2:
        m = re.match(r'([A-Za-z]*\s*\d+)\s*([A-Za-z][\w-]*)?', partes[1])
        cena = (m.group(1) if m else partes[1]).replace(' ', '').upper()
        # Gêmeos de marca paralelos (BATCH#4607, 17/11/2026): "H1 Neurobella" e "H1 VisioVance" são cadeias
        # separadas, não um clipe depois do outro. A palavra depois do número entra na chave quando o arquivo a tem.
        if m and m.group(2) and m.group(2).lower() in os.path.basename(arq).lower():
            cena += '·' + m.group(2).upper()
        return cena
    m = re.search(r'(C|CENA|S|SC)(\d+)', os.path.basename(arq), re.I)
    return m.group(0).upper() if m else '?'


def checar_um(arq, anterior=None, imagem=False):
    """Devolve (erros, avisos, blocos). Prompt de até LIMITE_CURTO caracteres vai pelo modo curto."""
    t = texto(arq)
    if curto(t):
        return checar_curto(t)
    b, ordem = blocos(t)
    erros, avisos = [], []
    faltam = [n for n, _ in CAMPOS if n not in b]
    if faltam:
        erros.append('faltam campos: ' + ', '.join(faltam))
    pres = [n for n, _ in CAMPOS if n in ordem]
    if [n for n in ordem if n in pres] != pres:
        erros.append('campos fora da ordem fixa (TITLE … NEVER): ' + ' > '.join(ordem))
    npal = len(re.findall(r"[A-Za-z0-9'’-]+", t))
    if not imagem and npal < MIN_PALAVRAS:
        erros.append(f'prompt de vídeo com {npal} palavras (mínimo {MIN_PALAVRAS})')
    refs = b.get('REFERENCES', '')
    for m in re.finditer(r'@\s*[Ii]mage\s*_?\s*(\d+)([^@\n]*)', refs):
        funcao = m.group(2).split('=', 1)[1] if '=' in m.group(2) else ''
        if len(funcao.split()) < 3:
            erros.append(f'@image{m.group(1)} sem função escrita (ex.: "= MARY face, keep in every shot")')
    nomes = rotulos(b.get('CHARACTERS', ''))
    if 'CHARACTERS' in b and not nomes and not imagem:
        avisos.append('CHARACTERS sem rótulo em CAIXA ALTA')
    if len(nomes) > 2:
        avisos.append(f'{len(nomes)} personagens ({", ".join(nomes)}): no máximo 2 importantes por quadro')
    never = b.get('NEVER', '')
    start = b.get('STATE AT START', '')
    obj = {w for w in norm(start).split() if len(w) >= 4 and w not in STOP}
    if never and not (any(n in never for n in nomes) or obj & set(norm(never).split())):
        erros.append('NEVER só genérico: precisa de pelo menos uma linha desta cena (personagem ou objeto)')
    for s in b.get('Shots', []):
        cams = {c.lower() for c in CAMERAS.findall(s)}
        if len(cams) > 1:
            avisos.append(f'{s.split(":")[0][:20]}: mais de uma câmera ({", ".join(sorted(cams))}); movimento a mais vai pro próximo shot')
        for n in nomes:
            if re.search(rf'\b{n}\b[^.]*\b(enters|walks in|comes in|appears)\b', s) and n in start:
                erros.append(f'{n} já está no STATE AT START e "entra" de novo ({s.split(":")[0][:20]})')
    v = sorted({x.lower() for x in VAGOS.findall(t)})
    if v:
        avisos.append('verbo vago: ' + ', '.join(v) + ' (use snaps, lunges, pivots, sets down, grips)')
    if not imagem:
        e2, w2 = checar_joey(arq, t, b, nomes)
        erros += e2
        avisos += w2
    if anterior is not None:
        fim_ant = anterior.get('STATE AT END', '')
        if fim_ant and start and norm(FRASES_FIXAS.sub(' ', fim_ant)) != norm(FRASES_FIXAS.sub(' ', start)):
            erros.append('STATE AT START não é o STATE AT END do clipe anterior, palavra por palavra')
    return erros, avisos, b


def prompts_de(alvos):
    arqs = []
    for a in alvos:
        if os.path.isdir(a):
            arqs += [p for p in glob.glob(os.path.join(a, '*')) if p.lower().endswith(('.txt', '.md'))
                     and not os.path.basename(p).lower().startswith(('folha_logica', 'licoes', 'leia-me', 'readme'))]
        else:
            arqs.append(a)
    return sorted(arqs, key=lambda p: natural(os.path.basename(p)))


def analisar(arqs, imagem=False):
    res, ult = [], {}
    for a in arqs:
        b0, _ = blocos(texto(a))
        cena = cena_de(b0, a)
        e, w, b = checar_um(a, ult.get(cena), imagem)
        ult[cena] = b
        res.append({'arquivo': a, 'cena': cena, 'erros': e, 'avisos': w, 'b': b})
    return res


def cmd_checar(a):
    res = analisar(prompts_de(a.alvos), a.imagem)
    ruins = 0
    for r in res:
        st = 'FALHA' if r['erros'] else ('aviso' if r['avisos'] else 'ok')
        ruins += bool(r['erros'])
        print(f'{st:6} {r["cena"]:6} {os.path.basename(r["arquivo"])}' + ('  (modo curto)' if r['b'].get('modo') == 'curto' else ''))
        for x in r['erros']:
            print(f'         ✖ {x}')
        for x in r['avisos']:
            print(f'         · {x}')
    print(f'---\n{len(res) - ruins}/{len(res)} prompts sem falha')
    return 1 if ruins else 0


def _folha_path(pasta):
    return os.path.join(pasta, 'folha_logica.json')


def cmd_folha(a):
    pasta = os.path.abspath(a.pasta)
    res = analisar(prompts_de([pasta]))
    quadros = {}
    if a.lote:
        for p in json.load(open(a.lote, encoding='utf-8')):
            args = [str(x) for x in p.get('args', [])]
            if args and p.get('cmd') in ('omni', 'kling3'):
                quadros[os.path.abspath(args[0])] = args[1] if len(args) > 1 else ''
            elif args:
                im = [args[i + 1] for i, x in enumerate(args[:-1]) if x in ('--imagem', '--ref', '--video')]
                quadros[os.path.abspath(args[0])] = ', '.join(im)
    velho = {}
    if os.path.exists(_folha_path(pasta)):
        velho = {c['clipe']: c for c in json.load(open(_folha_path(pasta), encoding='utf-8'))['clipes']}
    clipes = []
    for r in res:
        rel = os.path.relpath(r['arquivo'], pasta).replace('\\', '/')
        h = hash_de(texto(r['arquivo']))
        v = velho.get(rel, {})
        ok = bool(v.get('ok')) and v.get('hash') == h
        b = r['b']
        clipes.append({'clipe': rel, 'cena': r['cena'], 'start': b.get('STATE AT START', ''),
                       'planos': [s.split('\n')[0][:90] for s in b.get('Shots', [])],
                       'end': b.get('STATE AT END', ''), 'never': b.get('NEVER', ''), 'modo': b.get('modo', 'completo'),
                       'quadro': quadros.get(os.path.abspath(r['arquivo']), v.get('quadro', '')),
                       'erros': r['erros'], 'avisos': r['avisos'], 'hash': h, 'ok': ok,
                       'nota': v.get('nota', '') if ok else '', 'ok_em': v.get('ok_em', '') if ok else ''})
    json.dump({'pasta': pasta, 'gerada_em': time.strftime('%Y-%m-%d %H:%M'), 'clipes': clipes},
              open(_folha_path(pasta), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    md = ['# Folha de lógica', '', f'Pasta: `{pasta}` · {time.strftime("%d/%m/%Y %H:%M")}', '',
          'Ler de cima a baixo, cena por cena. Para cada clipe: (1) START = END do anterior? (2) todo mundo já estava ou tem '
          'entrada com causa? (3) quem muda de lugar tem o caminho? (4) todo efeito tem a causa antes? (5) NEVER com linha '
          'desta cena? (6) quadro inicial certo, em tamanho grande? Só gera com "ok" (`prompt_qa.py ok`).', '',
          '| clipe | cena | START | planos | END | NEVER | quadro inicial | checagem | ok |', '|---|---|---|---|---|---|---|---|---|']
    cel = lambda s: (s or '').replace('|', '/').replace('\n', ' ')[:220]
    for c in clipes:
        chk = ('✖ ' + '; '.join(c['erros'])) if c['erros'] else ('· ' + '; '.join(c['avisos']) if c['avisos'] else 'ok')
        md.append(f"| {c['clipe']}{' (curto)' if c.get('modo') == 'curto' else ''} | {c['cena']} | {cel(c['start'])} | {cel(' / '.join(c['planos']))} | {cel(c['end'])} | "
                  f"{cel(c['never'])} | {cel(c['quadro'])} | {cel(chk)} | {'ok' if c['ok'] else ''} |")
    open(os.path.join(pasta, 'folha_logica.md'), 'w', encoding='utf-8').write('\n'.join(md) + '\n')
    falhas = sum(bool(c['erros']) for c in clipes)
    print(f'folha com {len(clipes)} clipes ({falhas} com falha, {sum(c["ok"] for c in clipes)} com ok): '
          f'{os.path.join(pasta, "folha_logica.md")}')
    return 1 if falhas else 0


def cmd_ok(a):
    f = a.folha if a.folha.endswith('.json') else _folha_path(a.folha)
    d = json.load(open(f, encoding='utf-8'))
    if not a.nota or len(a.nota.split()) < 3:
        sys.exit('ok pede --nota com a leitura das 6 perguntas (ex.: "1-6 ok: START bate, ninguém entra de novo")')
    pasta = d['pasta']
    alvo = None if a.todos else set(a.clipes)
    n = 0
    for c in d['clipes']:
        if alvo is not None and c['clipe'] not in alvo and os.path.basename(c['clipe']) not in alvo:
            continue
        arq = os.path.join(pasta, c['clipe'])
        e, _, _ = checar_um(arq, None)
        e = [x for x in e if 'STATE AT START não é' not in x]    # a cadeia foi conferida na folha inteira
        if e or c.get('erros'):
            print(f'RECUSADO {c["clipe"]}: ' + '; '.join(e or c['erros']))
            continue
        c.update(ok=True, hash=hash_de(texto(arq)), nota=a.nota, ok_em=time.strftime('%Y-%m-%d %H:%M'))
        n += 1
    json.dump(d, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{n} clipe(s) com ok em {f}')
    return 0 if n else 1


def achar_folha(prompt):
    d = os.path.dirname(os.path.abspath(prompt))
    for _ in range(4):
        f = _folha_path(d)
        if os.path.exists(f):
            return f
        d2 = os.path.dirname(d)
        if d2 == d:
            break
        d = d2
    return None


def exigir_ok(prompt):
    """None se pode gerar; senão o motivo. Usada pelo kie.py nos comandos de vídeo."""
    f = achar_folha(prompt)
    como = ('monte a folha (`py _FLUXO/scripts/checagens/prompt_qa.py folha <pasta dos prompts>`), leia as 6 perguntas '
            'e dê o ok (`prompt_qa.py ok ...`). Regra: _FLUXO/QUALIDADE_DO_BATCH.md, 1.4')
    if not f:
        return f'sem folha_logica.json na pasta do prompt ({os.path.dirname(os.path.abspath(prompt))}): ' + como
    d = json.load(open(f, encoding='utf-8'))
    ap = os.path.abspath(prompt)
    for c in d['clipes']:
        if os.path.abspath(os.path.join(d['pasta'], c['clipe'])) == ap:
            if not c.get('ok'):
                return f'{c["clipe"]} sem ok na folha de lógica ({f}): ' + como
            if c.get('hash') != hash_de(texto(prompt)):
                return f'{c["clipe"]} mudou depois do ok: rode a folha de novo e dê novo ok'
            return None
    return f'{os.path.basename(prompt)} não está na folha {f}: rode `prompt_qa.py folha` de novo'


def dur(mp4):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', mp4],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def cmd_veredito(a):
    clipe = os.path.abspath(a.clipe)
    f = os.path.join(os.path.dirname(clipe), 'vereditos.json')
    d = json.load(open(f, encoding='utf-8')) if os.path.exists(f) else {}
    raiz = re.sub(r'(_r\d+|_v\d+|_reroll\d*)$', '', os.path.splitext(os.path.basename(clipe))[0], flags=re.I)
    if a.tipo == 'reroll' and not a.motivo:
        sys.exit('reroll pede --motivo da lista fechada: identidade, roupa, texto, anatomia, fundo, ação/batida faltando')
    if a.tipo == 'parcial' and not a.faixa:
        sys.exit('parcial pede --faixa INI-FIM (o trecho que presta, em s)')
    rerolls = sum(1 for k, v in d.items() if v.get('raiz') == raiz and v.get('tipo') == 'reroll')
    d[os.path.basename(clipe)] = {'raiz': raiz, 'tipo': a.tipo, 'faixa': a.faixa or '', 'motivo': a.motivo or '',
                                  'em': time.strftime('%Y-%m-%d %H:%M')}
    json.dump(d, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{a.tipo} gravado em {f}')
    if a.tipo == 'reroll' and rerolls >= 1:
        print('ATENÇÃO: este clipe já foi regerado 1 vez. Não rode o mesmo de novo: mude a abordagem '
              '(outro quadro, plano mais curto, cortar antes do erro, uma exigência a menos).')
        return 2
    return 0


def cmd_metricas(a):
    pasta = os.path.abspath(a.pasta)
    ger = [p for p in glob.glob(os.path.join(pasta, '**', '*.mp4'), recursive=True) if os.path.exists(p + '.task.json')]
    seg = sum(dur(p) for p in ger)
    master = sum(dur(p) for p in (a.master or []))
    cr = a.cr
    if cr is None:
        cr = 0.0
        for t in glob.glob(os.path.join(pasta, '**', '*.resultado.tsv'), recursive=True):
            for l in open(t, encoding='utf-8').read().splitlines()[1:]:
                p = l.split('\t')
                if len(p) > 3 and re.match(r'^[\d.]+$', p[3] or ''):
                    cr += float(p[3])
    rerolls = 0
    for v in glob.glob(os.path.join(pasta, '**', 'vereditos.json'), recursive=True):
        rerolls += sum(1 for x in json.load(open(v, encoding='utf-8')).values() if x.get('tipo') == 'reroll')
    aprov = (master / seg) if seg else 0.0
    crs = (cr / master) if master else 0.0
    out = {'clipes_gerados': len(ger), 'segundos_gerados': round(seg, 1), 'credito': round(cr, 1),
           'clipes_refeitos': rerolls, 'segundos_master': round(master, 1),
           'aproveitamento': round(aprov, 3), 'meta_aproveitamento': 0.70,
           'credito_por_segundo_final': round(crs, 2), 'meta_credito_por_segundo': 7.0, 'em': time.strftime('%Y-%m-%d %H:%M')}
    json.dump(out, open(os.path.join(pasta, 'metricas_qualidade.json'), 'w', encoding='utf-8'), indent=1)
    print(f'{len(ger)} clipes · {seg:.0f} s gerados · {cr:g} cr · {rerolls} refeitos · master {master:.0f} s')
    print(f'aproveitamento {aprov:.0%} (meta 70%) · {crs:.2f} cr/s final (meta até 7)')
    return 0


def main():
    for st in (sys.stdout, sys.stderr):
        try: st.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError): pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = ap.add_subparsers(dest='cmd', required=True)
    c = s.add_parser('checar'); c.add_argument('alvos', nargs='+'); c.add_argument('--imagem', action='store_true')
    c = s.add_parser('folha'); c.add_argument('pasta'); c.add_argument('--lote')
    c = s.add_parser('ok'); c.add_argument('folha'); c.add_argument('clipes', nargs='*')
    c.add_argument('--todos', action='store_true'); c.add_argument('--nota', default='')
    c = s.add_parser('veredito'); c.add_argument('clipe'); c.add_argument('tipo', choices=['ok', 'parcial', 'reroll'])
    c.add_argument('--faixa'); c.add_argument('--motivo')
    c = s.add_parser('metricas'); c.add_argument('pasta'); c.add_argument('--master', action='append')
    c.add_argument('--cr', type=float)
    a = ap.parse_args()
    sys.exit({'checar': cmd_checar, 'folha': cmd_folha, 'ok': cmd_ok, 'veredito': cmd_veredito,
              'metricas': cmd_metricas}[a.cmd](a))


if __name__ == '__main__':
    main()
