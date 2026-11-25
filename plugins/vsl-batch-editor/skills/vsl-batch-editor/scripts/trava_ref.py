#!/usr/bin/env python3
"""Trava da referência (Fefo, 19/11/2026: "a ideia da referencia tem que ser uma trava, se nao estruturar que nem a
referencia, tu nao pode seguir em diante"). Regra: _FLUXO/LEIA-ME.md, seção "Ref no briefing".

O job só gera vídeo (kie.py) e só monta (EV fluxo.py, TS montagem_base) com `<auto>/ref_estrutura.json` certo:
  {"ref": {"arquivo": "01_refs/REF.mp4", "dur": 34.9, "quadros": "08_auto/ref_quadros",
           "truque": {"texto": "o que faz este ref funcionar", "quadros": ["hook_0012.jpg", "meio_s_0009.jpg"]}},
   "planos": [{"n": 1, "de": 0.0, "ate": 2.4, "enquadramento": "...", "camera": "...", "acao": "...",
               "personagem": "...", "texto": "...", "som": "..."}],            # decupagem: uma linha por plano do ref
   "nosso":  [{"cena": "H1-01", "ref": 1, "dur": 2.4, "movimento": "push-in lento"}],   # cada cena e o plano que refaz
   "audio": {"ref":   {"musica": "piano tenso, entra no 0 s", "bpm": 92, "voz": "mulher 50+, calma", "genero": "f", "pps": 3.1},
             "nosso": {"musica": "mesma do ref | <a mais próxima, qual>", "bpm": 90, "voz": "...", "genero": "f", "pps": 3.0}},
   "excecoes": [{"de": "ref 7" | "cena S12" | "audio" | "audio.musica" | "audio.voz" | "audio.genero" | "audio.pps", "motivo": "...", "fefo": "<palavras do Fefo>"}]}
   Ref sem música: "musica": "nenhuma ..." (ou "sem ...") ou "bpm": 0; aí a trilha do nosso não é conferida.
Plano do ref com zoom na pessoa (punch-in): "zoom": true no plano; a cena que o refaz leva "zoom": true também.
Vários refs no mesmo job: {"refs": [ {ref, planos, nosso, excecoes}, ... ]}.
Job sem ref: {"sem_ref": {"motivo": "...", "fefo": "<palavras do Fefo>"}}.
Cena que repete o padrão do ref porque o script é mais longo: "repete": true (não entra na conta da ordem).

O que a trava recusa (código 3):
  1. sem ref_estrutura.json, ou ref que não existe no disco, ou duração que não bate com o arquivo (não olhou o ref);
  2. sem os quadros do ref no disco (hook inteiro e 1 a cada 0,5 s: `trava_ref.py quadros <job>`);
  3. decupagem com buraco, que não cobre o ref inteiro, ou plano sem enquadramento, câmera ou ação;
  4. plano do ref que nenhuma cena refaz; cena que não aponta plano do ref;
  5. ordem das cenas diferente da ordem do ref;
  6. tempo de cena fora do tempo do plano do ref (na proporção das durações; folga de 30% ou 0,4 s);
  7. cena do hook (plano do ref que começa antes de 3 s) sem movimento;
  8. zoom onde o ref não faz, ou plano do ref com zoom refeito sem zoom (Fefo, 19/11/2026: "zoom só quando o ref faz");
  10. sem ref.truque: o truque que o ref usa, escrito, com os quadros que provam (método Katana do Lucas, 19/11/2026);
  11. sem <auto>/PLANO.md com as 4 partes: brief, regras do cliente, erros passados e ordem do trabalho (plano primeiro).
  9. sem "audio", ref com música e o nosso sem, BPM fora de 10%, voz de outro gênero ou ritmo de fala fora de 15%
     (call da EV, 19/11/2026: o remake leva a mesma VO e a mesma música).
Escape: só `excecoes`, um por item, com motivo e as palavras do Fefo.

Vale para job criado desde 19/11/2026. Job mais antigo sem o arquivo: só aviso. Com o arquivo, confere sempre.

CLI: py trava_ref.py conferir <job|batch>          (0 = ok, 3 = recusado)
     py trava_ref.py quadros  <job|batch> [ref.mp4] (tira os quadros do ref; rode com `fila --leve`)
     py trava_ref.py modelo   <job|batch> [ref.mp4] (grava um ref_estrutura.json vazio, com a duração do ref)
"""
import glob, json, os, subprocess, sys

DESDE = 1795057200      # 19/11/2026 00:00 (Brasília; Fefo, 19/11: "Vale já")
ARQ = 'ref_estrutura.json'
VIDEOS = ('.mp4', '.mov', '.webm', '.mkv', '.m4v')
PARADO = ('', 'parado', 'parada', 'estatico', 'estático', 'static', 'still', 'nenhum', 'fixo', 'sem movimento', 'none')
COMO = ('faça a decupagem quadro a quadro do ref e grave ref_estrutura.json (formato no cabeçalho de '
        '_FLUXO/scripts/checagens/trava_ref.py; regra em _FLUXO/LEIA-ME.md, seção "Ref no briefing")')
_cache = {}


def _fichas():
    aqui = os.path.dirname(os.path.abspath(__file__))
    out = []
    for d in (os.path.join(aqui, '..', '..', 'clientes'), os.path.join(aqui, '..', 'clientes'), os.path.join(aqui, 'clientes')):
        for f in glob.glob(os.path.join(d, '*.json')):
            try:
                p = json.load(open(f, encoding='utf-8')).get('pastas')
            except (OSError, ValueError):
                continue
            if isinstance(p, dict) and p.get('config') and p.get('auto'):
                out.append(p)
    return out


def achar_job(caminho):
    """Sobe do caminho até a pasta do job (a que tem o batch.json ou o job.json da ficha). (raiz, pastas) ou (None, None)."""
    fichas = _fichas()
    d = os.path.abspath(caminho)
    if not os.path.isdir(d):
        d = os.path.dirname(d)
    while True:
        for p in fichas:
            if os.path.isfile(os.path.join(d, p['config'])):
                return d, p
        pai = os.path.dirname(d)
        if pai == d:
            return None, None
        d = pai


def criada_em(B):
    st = os.stat(B)
    return getattr(st, 'st_birthtime', None) or (st.st_ctime if os.name == 'nt' else st.st_mtime)


def _dur(mp4):
    try:
        r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', mp4],
                           capture_output=True, text=True, timeout=60)
        return float(r.stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


SEM = ('nenhuma', 'nenhum', 'sem', 'none', 'sem musica', 'sem música', 'sem voz', 'sem vo')


def _sem(x, bpm=None):
    """Texto que diz que não há música/voz ("nenhuma música audível...", "sem trilha", "none") ou BPM 0
    (M1WK4B2 Naturva LFS, 19/11/2026: o ref do Vine não tem música)."""
    x = str(x or '').strip().lower()
    return (not x and bpm == 0) or x in SEM or x.startswith(('nenhum', 'sem ', 'none', 'no music', 'no voice')) or bpm == 0


def _audio(a, rot, erros, exc):
    """Mesma música e mesma VO do ref (call da EV de 19/11/2026; Fefo: "pode por os 4")."""
    if 'audio' in exc:
        return
    if not isinstance(a, dict) or not isinstance(a.get('ref'), dict) or not isinstance(a.get('nosso'), dict):
        erros.append(f'{rot}sem "audio": descreva a música e a voz do ref e as nossas '
                     '("audio": {"ref": {"musica", "bpm", "voz", "genero", "pps"}, "nosso": {...}}; sem música ou sem voz: "nenhuma")')
        return
    r, n = a['ref'], a['nosso']
    for lado, d in (('ref', r), ('nosso', n)):
        falta = [c for c in ('musica', 'voz') if not str(d.get(c, '')).strip()]
        if falta:
            erros.append(f'{rot}audio.{lado} sem {", ".join(falta)} (sem nada: "nenhuma")')
    rm, nm = str(r.get('musica', '')).strip().lower(), str(n.get('musica', '')).strip().lower()
    rb, nb = _num(r.get('bpm')), _num(n.get('bpm'))
    ref_com_musica = bool(rm) and not _sem(rm, rb) and 'audio.musica' not in exc   # exceção por item (19/11/2026)
    if ref_com_musica and _sem(nm, nb):
        erros.append(f'{rot}o ref tem música ("{rm[:50]}") e o nosso não: mesma música do ref, ou a mais próxima')
    if ref_com_musica:
        if rb is None or nb is None:
            erros.append(f'{rot}audio sem "bpm" no ref ou no nosso: meça o BPM da trilha do ref e da nossa')
        elif abs(nb - rb) > 0.1 * rb:
            erros.append(f'{rot}trilha a {nb:g} BPM; a do ref tem {rb:g} (folga de 10%)')
    rv, nv = str(r.get('voz', '')).strip().lower(), str(n.get('voz', '')).strip().lower()
    if rv and not _sem(rv) and 'audio.voz' not in exc:
        if _sem(nv):
            erros.append(f'{rot}o ref tem voz ("{rv[:50]}") e o nosso não')
        rg, ng = str(r.get('genero', '')).strip().lower()[:1], str(n.get('genero', '')).strip().lower()[:1]
        if 'audio.genero' in exc:
            pass
        elif not rg or not ng:
            erros.append(f'{rot}audio sem "genero" da voz (f ou m) no ref ou no nosso')
        elif rg != ng:
            erros.append(f'{rot}voz de gênero diferente do ref (ref {rg}, nosso {ng})')
        rp, np_ = _num(r.get('pps')), _num(n.get('pps'))
        if 'audio.pps' in exc:
            pass
        elif rp is None or np_ is None:
            erros.append(f'{rot}audio sem "pps" (palavras por segundo da fala) no ref ou no nosso')
        elif abs(np_ - rp) > 0.15 * rp:
            erros.append(f'{rot}fala a {np_:g} palavras/s; a do ref tem {rp:g} (folga de 15%)')


_zoom = {}


def marca_zoom(caminho):
    """REF_ZOOM=1 no ambiente quando algum plano do ref tem "zoom": true. O código de montagem só aceita punch-in assim
    (Fefo, 19/11/2026: "zoom só quando o ref faz")."""
    k = os.path.abspath(caminho)
    if k not in _zoom:
        z = False
        raiz, pastas = achar_job(caminho)
        if raiz:
            try:
                d = json.load(open(os.path.join(raiz, pastas['auto'], ARQ), encoding='utf-8'))
                blocos = d['refs'] if isinstance(d.get('refs'), list) and d['refs'] else [d]
                z = any(p.get('zoom') for b in blocos if isinstance(b, dict)
                        for p in (b.get('planos') or []) if isinstance(p, dict))
            except (OSError, ValueError, AttributeError):
                z = False
        _zoom[k] = z
    os.environ['REF_ZOOM'] = '1' if _zoom[k] else '0'
    return _zoom[k]


def _bloco(raiz, b, rot, erros, avisos):
    r = b.get('ref') or {}
    arq = os.path.join(raiz, str(r.get('arquivo') or ''))
    if not r.get('arquivo') or not os.path.isfile(arq):
        erros.append(f'{rot}ref.arquivo não existe no job ({r.get("arquivo")!r}): baixe o ref e assista antes de planejar')
        return
    dur, real = _num(r.get('dur')), _dur(arq)
    if real is None:
        avisos.append(f'{rot}sem ffprobe: a duração do ref não foi conferida')
    elif dur is None or abs(real - dur) > 0.5:
        erros.append(f'{rot}ref.dur = {r.get("dur")!r}, mas o arquivo tem {real:.2f} s: meça o ref de verdade')
    D = real or dur or 0.0
    q = os.path.join(raiz, str(r.get('quadros') or ''))
    nq = len([f for f in os.listdir(q) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]) if r.get('quadros') and os.path.isdir(q) else 0
    preciso = int(D * 2 * 0.8)
    if nq < preciso:
        erros.append(f'{rot}{nq} quadros do ref em {r.get("quadros")!r}; a decupagem pede pelo menos {preciso} '
                     f'(hook inteiro e 1 a cada 0,5 s): rode `fila --leve py trava_ref.py quadros <job>` e olhe os quadros')

    tq = r.get('truque')
    if not isinstance(tq, dict) or len(str(tq.get('texto', '')).strip()) < 30:
        erros.append(f'{rot}sem ref.truque.texto: escreva o truque que o ref usa (o que faz ele funcionar), em pelo menos uma frase')
    else:
        qs = [x for x in (tq.get('quadros') or []) if isinstance(x, str)]
        fora = [x for x in qs if not os.path.isfile(os.path.join(q, x))]
        if len(qs) < 2:
            erros.append(f'{rot}ref.truque.quadros pede pelo menos 2 quadros do ref que provam o truque (nomes em {r.get("quadros")!r})')
        elif fora:
            erros.append(f'{rot}quadro do truque fora do disco: {", ".join(fora[:3])}')
    exc = set()
    for e in b.get('excecoes') or []:
        if not isinstance(e, dict) or not str(e.get('motivo', '')).strip() or not str(e.get('fefo', '')).strip():
            erros.append(f'{rot}exceção sem "motivo" ou sem "fefo" (as palavras dele): {str(e)[:80]}')
        else:
            exc.add(' '.join(str(e.get('de', '')).lower().split()))

    planos = [p for p in (b.get('planos') or []) if isinstance(p, dict)]
    if not planos:
        erros.append(f'{rot}sem "planos": a decupagem tem uma linha por plano do ref')
        return
    ids, t, zoom_ref, zoom_nosso = {}, 0.0, set(), set()
    for p in planos:
        n, a, f = p.get('n'), _num(p.get('de')), _num(p.get('ate'))
        if n is None or a is None or f is None or f <= a:
            erros.append(f'{rot}plano do ref ilegível (n, de, ate): {str(p)[:80]}')
            continue
        if n in ids:
            erros.append(f'{rot}plano {n} do ref repetido na decupagem')
        if abs(a - t) > 0.1:
            erros.append(f'{rot}decupagem com buraco ou sobreposição antes do plano {n}: {t:.2f} s → {a:.2f} s')
        falta = [c for c in ('enquadramento', 'camera', 'acao') if not str(p.get(c, '')).strip()]
        falta += [c for c in ('personagem', 'texto', 'som') if c not in p]
        if falta:
            erros.append(f'{rot}plano {n} do ref sem {", ".join(falta)} (sem nada: escreva "nenhum")')
        ids[n] = (a, f)
        if p.get('zoom'):
            zoom_ref.add(n)
        t = f
    if D and abs(t - D) > 0.5:
        erros.append(f'{rot}a decupagem acaba em {t:.2f} s e o ref tem {D:.2f} s: falta plano')

    nosso = [c for c in (b.get('nosso') or []) if isinstance(c, dict)]
    if not nosso:
        erros.append(f'{rot}sem "nosso": cada cena do plano aponta o plano do ref que ela refaz')
        return
    usados, grupos, ordem = set(), {}, []
    for c in nosso:
        cid = str(c.get('cena', '?'))
        livre = f'cena {cid}'.lower() in exc
        n, d = c.get('ref'), _num(c.get('dur'))
        if n not in ids:
            if not livre:
                erros.append(f'{rot}cena {cid} não aponta plano do ref (ref = {n!r}): toda cena refaz um plano do ref')
            continue
        usados.add(n)
        if c.get('zoom'):
            zoom_nosso.add(n)
            if n not in zoom_ref and not livre:
                erros.append(f'{rot}cena {cid} tem zoom e o plano {n} do ref não: zoom só quando o ref faz; fora disso, outra cena')
        if d is None or d <= 0:
            erros.append(f'{rot}cena {cid} sem "dur" (segundos)')
            continue
        if ids[n][0] < 3.0 or c.get('hook'):
            if str(c.get('movimento', '')).strip().lower() in PARADO:
                erros.append(f'{rot}cena {cid} é do hook e está sem movimento: hook sempre com movimento (câmera, gesto ou objeto)')
        if c.get('repete'):
            grupos.setdefault((n, cid), [0.0, [cid], livre])[0] += d
        else:
            g = grupos.setdefault((n, None), [0.0, [], False])
            g[0] += d; g[1].append(cid); g[2] = g[2] or livre
            ordem.append((n, cid, livre))
    for n in ids:
        if n not in usados and f'ref {n}' not in exc:
            erros.append(f'{rot}o plano {n} do ref ({ids[n][0]:.2f}–{ids[n][1]:.2f} s) não é refeito por nenhuma cena')
    for n in sorted(zoom_ref - zoom_nosso, key=str):
        if n in usados and f'ref {n}' not in exc:
            erros.append(f'{rot}o plano {n} do ref tem zoom e a cena que o refaz não ("zoom": true na cena)')
    _audio(b.get('audio'), rot, erros, exc)
    pos = {n: i for i, n in enumerate(ids)}
    for (n0, c0, _), (n1, c1, l1) in zip(ordem, ordem[1:]):
        if pos[n1] < pos[n0] and not l1:
            erros.append(f'{rot}ordem diferente do ref: a cena {c1} (plano {n1} do ref) vem depois da cena {c0} (plano {n0})')
    tot_n = sum(g[0] for g in grupos.values())
    tot_r = sum(ids[n][1] - ids[n][0] for (n, _) in grupos)
    if tot_r > 0 and tot_n > 0:
        esc = tot_n / tot_r
        if not 0.5 <= esc <= 2.0:
            avisos.append(f'{rot}o ad tem {esc:.2f}x o tempo do ref: diga ao Fefo o que foi esticado ou cortado')
        for (n, _), (d, cenas, livre) in grupos.items():
            alvo = (ids[n][1] - ids[n][0]) * esc
            if abs(d - alvo) > max(0.4, 0.3 * alvo) and not livre and f'ref {n}' not in exc:
                erros.append(f'{rot}tempo fora do ref: {", ".join(cenas)} somam {d:.2f} s; o plano {n} do ref pede ~{alvo:.2f} s '
                             f'(ref {ids[n][1] - ids[n][0]:.2f} s x {esc:.2f})')


PARTES_PLANO = ('brief', 'regras do cliente', 'erros passados', 'ordem do trabalho')
MODELO_PLANO = """# Plano do job (plano primeiro; processo do Lucas, 19/11/2026)
Escreva antes de gerar. Cada etapa acrescenta a sua linha na última parte.

## Brief
(o brief e o card lidos inteiros: o que pedem, o script do CS, o ref)

## Regras do cliente
(as regras da ficha e das preferências que valem para este job)

## Erros passados
(as notas que já voltaram e as entradas do APRENDIZADOS.md que valem aqui)

## Ordem do trabalho
(os passos, na ordem, com quem faz cada um)

## O que cada etapa acrescentou
- geração:
- edição:
- efeitos:
- design:
"""


def _plano_escrito(raiz, pastas, erros):
    """Plano primeiro (processo do Lucas): <auto>/PLANO.md com as 4 partes preenchidas."""
    arq = os.path.join(raiz, pastas['auto'], 'PLANO.md')
    if not os.path.isfile(arq):
        erros.append(f'sem {pastas["auto"]}/PLANO.md: escreva o plano antes de gerar (brief, regras do cliente, erros passados, '
                     'ordem do trabalho); `trava_ref.py modelo <job>` grava o modelo')
        return
    try:
        t = open(arq, encoding='utf-8').read()
    except OSError as e:
        erros.append(f'PLANO.md ilegível: {e}'); return
    baixo = t.lower()
    falta = [p for p in PARTES_PLANO if '## ' + p not in baixo]
    if falta:
        erros.append(f'PLANO.md sem a parte: {", ".join(falta)}')
    elif len(t) - len(MODELO_PLANO) < 200:
        erros.append('PLANO.md ainda é o modelo vazio: preencha as 4 partes')


def conferir(raiz, pastas):
    """(erros, avisos) do ref_estrutura.json do job."""
    erros, avisos = [], []
    arq = os.path.join(raiz, pastas['auto'], ARQ)
    if not os.path.isfile(arq):
        return [f'sem {pastas["auto"]}/{ARQ}: {COMO}'], avisos
    _plano_escrito(raiz, pastas, erros)
    try:
        d = json.load(open(arq, encoding='utf-8'))
    except (OSError, ValueError) as e:
        return [f'{ARQ} ilegível: {e}'], avisos
    sr = d.get('sem_ref')
    if sr:
        if not isinstance(sr, dict) or not str(sr.get('motivo', '')).strip() or not str(sr.get('fefo', '')).strip():
            erros.append('"sem_ref" pede "motivo" e "fefo" (as palavras dele)')
        refs = os.path.join(raiz, str(pastas.get('refs') or ''))
        vids = [f for f in os.listdir(refs) if f.lower().endswith(VIDEOS)] if pastas.get('refs') and os.path.isdir(refs) else []
        if vids:
            erros.append(f'"sem_ref", mas há vídeo em {pastas["refs"]}/ ({", ".join(vids[:3])}): decupe o ref')
        return erros, avisos
    blocos = d['refs'] if isinstance(d.get('refs'), list) and d['refs'] else [d]
    for i, b in enumerate(blocos):
        _bloco(raiz, b if isinstance(b, dict) else {}, f'ref {i + 1}: ' if len(blocos) > 1 else '', erros, avisos)
    return erros, avisos


def exigir(caminho):
    """None se pode seguir; senão o motivo (texto). Usada pelo kie.py e pela montagem."""
    raiz, pastas = achar_job(caminho)
    if not raiz:
        return None
    marca_zoom(caminho)
    if raiz in _cache:
        return _cache[raiz]
    tem = os.path.isfile(os.path.join(raiz, pastas['auto'], ARQ))
    desde = float(os.environ.get('TRAVA_REF_DESDE') or DESDE)
    if not tem and criada_em(raiz) < desde:
        print(f'AVISO (trava do ref): {os.path.basename(raiz)} é de antes de 19/11/2026 e não tem {ARQ}. '
              'Job novo e revisão nova: sem ele, não gera nem monta.', file=sys.stderr, flush=True)
        _cache[raiz] = None
        return None
    erros, avisos = conferir(raiz, pastas)
    for a in avisos:
        print(f'AVISO (trava do ref): {a}', file=sys.stderr, flush=True)
    m = None
    if erros:
        m = (f'TRAVA DO REF: {os.path.basename(raiz)} não está estruturado como a referência ({len(erros)} erro(s)):\n  - '
             + '\n  - '.join(erros) + '\n  Escape só com exceção escrita (motivo + palavras do Fefo) em ' + ARQ + '.')
    _cache[raiz] = m
    return m


def trava(caminho, onde=''):
    """Recusa (código 3) se o job não está estruturado como o ref."""
    m = exigir(caminho)
    if m:
        print(f'{m}\n  Recusado: {onde or caminho}', file=sys.stderr, flush=True)
        raise SystemExit(3)


def _ref_do_job(raiz, pastas, arg=None):
    if arg:
        return os.path.abspath(arg)
    refs = os.path.join(raiz, str(pastas.get('refs') or ''))
    vids = sorted(f for f in os.listdir(refs) if f.lower().endswith(VIDEOS)) if os.path.isdir(refs) else []
    if len(vids) != 1:
        sys.exit(f'{len(vids)} vídeos em {refs}: diga qual é o ref (py trava_ref.py <comando> <job> <ref.mp4>)')
    return os.path.join(refs, vids[0])


def quadros(raiz, pastas, ref):
    """Hook (0 a 3 s): todos os quadros. Resto: 1 a cada 0,5 s. Em <auto>/ref_quadros/, nome com o tempo."""
    out = os.path.join(raiz, pastas['auto'], 'ref_quadros')
    os.makedirs(out, exist_ok=True)
    base = ['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', ref]
    subprocess.run(base + ['-t', '3', '-vf', 'scale=-2:960', '-q:v', '3', '-frame_pts', '0',
                           os.path.join(out, 'hook_%04d.jpg')], check=True)
    subprocess.run(base + ['-vf', 'fps=2,scale=-2:960', '-q:v', '3', os.path.join(out, 'meio_s_%04d.jpg')], check=True)
    n = len(os.listdir(out))
    print(f'{n} quadros em {out}\n  hook_NNNN.jpg = quadro NNNN dos 3 primeiros segundos; meio_s_NNNN.jpg = (NNNN - 1) x 0,5 s.\n'
          '  Corte fora da grade: tire o quadro de antes e o de depois com `ffmpeg -ss <t> -frames:v 1`.')
    return os.path.relpath(out, raiz).replace('\\', '/')


def modelo(raiz, pastas, ref):
    pl = os.path.join(raiz, pastas['auto'], 'PLANO.md')
    if not os.path.exists(pl):
        open(pl, 'w', encoding='utf-8').write(MODELO_PLANO); print(f'gravado: {pl}')
    arq = os.path.join(raiz, pastas['auto'], ARQ)
    if os.path.exists(arq):
        sys.exit(f'já existe: {arq}')
    d = _dur(ref)
    json.dump({'ref': {'arquivo': os.path.relpath(ref, raiz).replace('\\', '/'), 'dur': round(d, 2) if d else None,
                       'quadros': f'{pastas["auto"]}/ref_quadros', 'truque': {'texto': '', 'quadros': []}},
               'planos': [{'n': 1, 'de': 0.0, 'ate': 0.0, 'enquadramento': '', 'camera': '', 'acao': '',
                           'personagem': '', 'texto': '', 'som': ''}],
               'nosso': [{'cena': '', 'ref': 1, 'dur': 0.0, 'movimento': ''}],
               'audio': {'ref': {'musica': '', 'bpm': None, 'voz': '', 'genero': '', 'pps': None},
                         'nosso': {'musica': '', 'bpm': None, 'voz': '', 'genero': '', 'pps': None}},
               'excecoes': []}, open(arq, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'gravado: {arq}')


def main():
    a = sys.argv[1:]
    if len(a) < 2 or a[0] not in ('conferir', 'quadros', 'modelo'):
        sys.exit(__doc__)
    raiz, pastas = achar_job(a[1])
    if not raiz:
        print(f'não achei o job (batch.json / job.json) a partir de {a[1]}', file=sys.stderr); sys.exit(2)
    if a[0] == 'quadros':
        return quadros(raiz, pastas, _ref_do_job(raiz, pastas, a[2] if len(a) > 2 else None))
    if a[0] == 'modelo':
        return modelo(raiz, pastas, _ref_do_job(raiz, pastas, a[2] if len(a) > 2 else None))
    erros, avisos = conferir(raiz, pastas)
    for x in avisos:
        print(f'AVISO: {x}')
    if erros:
        print(f'TRAVA DO REF: {os.path.basename(raiz)} não está estruturado como a referência ({len(erros)} erro(s)):')
        for x in erros:
            print(f'  - {x}')
        sys.exit(3)
    print(f'{os.path.basename(raiz)}: estrutura igual à do ref. Pode seguir.')


if __name__ == '__main__':
    main()
