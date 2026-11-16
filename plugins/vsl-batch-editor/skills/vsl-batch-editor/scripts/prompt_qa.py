#!/usr/bin/env python3
"""Qualidade antes de gerar (PDF do Lucas, 16/11/2026; regra em _FLUXO/QUALIDADE_DO_BATCH.md).

  py prompt_qa.py checar PROMPT.txt|PASTA [...] [--imagem]
        # estrutura fixa, 140+ palavras, @image com função, START = END do anterior, NEVER da cena, verbos vagos
  py prompt_qa.py folha PASTA_DOS_PROMPTS [--lote PEDIDOS.json]
        # monta folha_logica.md + folha_logica.json (clipe | START | planos | END | NEVER | quadro inicial)
  py prompt_qa.py ok FOLHA.json CLIPE [CLIPE ...]|--todos --nota "1-6 ok: ..."
        # grava o ok de cada clipe com o hash do prompt (mudou o prompt = precisa de novo ok)
  py prompt_qa.py veredito CLIPE.mp4 ok|parcial|reroll [--faixa 2.0-6.5] [--motivo "..."]
        # veredito por clipe em vereditos.json; avisa quando o clipe já foi regerado 1 vez
  py prompt_qa.py metricas PASTA --master A.mp4 [--master B.mp4] [--cr 1234]
        # segundos gerados, crédito, refeitos, aproveitamento (meta 70%) e crédito por segundo final (meta <= 7)

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
        m = re.match(r'([A-Za-z]*\s*\d+)', partes[1])
        return (m.group(1) if m else partes[1]).replace(' ', '').upper()
    m = re.search(r'(C|CENA|S|SC)(\d+)', os.path.basename(arq), re.I)
    return m.group(0).upper() if m else '?'


def checar_um(arq, anterior=None, imagem=False):
    """Devolve (erros, avisos, blocos)."""
    t = texto(arq)
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
    if anterior is not None:
        fim_ant = anterior.get('STATE AT END', '')
        if fim_ant and start and norm(fim_ant) != norm(start):
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
        print(f'{st:6} {r["cena"]:6} {os.path.basename(r["arquivo"])}')
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
                       'end': b.get('STATE AT END', ''), 'never': b.get('NEVER', ''),
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
        md.append(f"| {c['clipe']} | {c['cena']} | {cel(c['start'])} | {cel(' / '.join(c['planos']))} | {cel(c['end'])} | "
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
