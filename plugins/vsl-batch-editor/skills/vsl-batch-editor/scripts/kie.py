#!/usr/bin/env python3
"""Kie.ai — saldo, upload e geração com download. Um script só para todos os clientes (núcleo, 09/11/2026).

CLIENTE E CONTA: cada cliente tem a sua conta do Kie e a sua chave. A ficha do cliente (../clientes/<cliente>.json)
diz onde está a chave, a pasta dele e o que não pode. O script define o cliente assim:
  1. `--cliente ev|ts` (ou KIE_CLIENTE). Os kie.py das pastas dos clientes são atalhos que já passam isso.
  2. Sem isso, pela pasta da SAIDA (@EMPIRE VISION → ev, @TRENDSCALE → ts).
E recusa o cruzamento: saída na pasta de um cliente com a conta de outro não roda. Também recusa quando duas
contas têm a mesma chave, quando a chave de um cliente é a registrada para outro, e quando a chave mudou sem
`registrar-chave`. Toda geração imprime a conta que pagou e grava o cliente no SAIDA.task.json.
  python3 kie.py contas [--saldo]                       # clientes, chave presente, impressão conferida (não gasta)
  python3 kie.py --cliente ts registrar-chave           # depois de trocar a chave de um cliente (confirmar com o Fefo)

Uso (--teste em qualquer geração mostra o pedido sem subir arquivo e sem gastar):
  python3 kie.py saldo
  python3 kie.py upload ARQ.png                         # devolve a URL (o Kie apaga em 24 h)
  python3 kie.py sunburst PROMPT.txt SAIDA.png [--ref A.png --ref B.png] [--res 2K] [--ratio 9:16]
        # GPT Image 2.5 Sunburst. Com --ref (até 16), edita ou usa referências; sem --ref, só texto.
  python3 kie.py seedream PROMPT.txt SAIDA.png [--ref A.png ...] [--res 1K] [--ratio 9:16]
        # Seedream 5.5 (ByteDance, 09/11/2026), 3,6 cr em 1K. Com --ref (até 10), image-to-image. Imagem, não é o Seedance.
  python3 kie.py nanopro PROMPT.txt SAIDA.png --ref QUADRO.png [--ref B.png] [--res 2K] [--ratio 9:16]
        # Nano Banana Pro (até 8 --ref). Avatar a partir de quadro real de UGC: ver modulos/03_personagens.md.
  python3 kie.py omni PROMPT.txt IMAGEM SAIDA.mp4 --dur 8 [--res 720p]
        # Gemini Omni com som. --dur só 4, 6, 8 ou 10. Liberado junto do Kling em 02/11/2026; custo ainda não medido.
  python3 kie.py kling3 PROMPT.txt IMAGEM SAIDA.mp4 --dur 5 [--mode std] [--sem-som] [--fim FIM.png]
        # IMAGEM = quadro inicial, ou "-" para só texto (sai 9:16).
  python3 kie.py kling4 PROMPT.txt SAIDA.mp4 --dur 5 [--video F01.mp4] [--imagem A.png] [--voz nome=AUDIO.mp3] [--res 720p]
        # Reference-to-video. No prompt: @video_1, @image_1, @nome. Toda menção precisa de arquivo. Sempre com som.
  python3 kie.py seedance PROMPT.txt SAIDA.mp4 --dur 8 [--imagem A.png] [--audio F01.mp3] [--res 720p] [--sem-som]
        # Só em Drama ad. Referências, sem quadro inicial: o Kie não aceita os dois juntos.
  python3 kie.py tts TEXTO.txt SAIDA.mp3 --voz ID [--speed 1]
        # ElevenLabs Multilingual v2. Só vozes prontas do catálogo, sem voz clonada.
  python3 kie.py suno ESTILO.txt SAIDA.mp3 --titulo "Nome" [--letra LETRA.txt] [--instrumental] [--voz m|f]
        [--dur 120] [--modelo V5_5] [--persona ID] [--sem-estilo "edm, autotune"] [--peso-estilo 0.6] [--peso-audio 0.75]
        # Música pela API da Suno no Kie. Sai mais de uma faixa por pedido: SAIDA_1.mp3, SAIDA_2.mp3...
        # --dur só vale em V5_5/V6. Sem --letra e sem --instrumental, a Suno escreve a letra.
  python3 kie.py suno-ref REFERENCIA.mp3 ESTILO.txt SAIDA.mp3 --titulo "Nome" [--letra LETRA.txt] [--voz m|f]
        [--peso-audio 0.75] [--dur 120] [--persona ID] [--modelo V6] [--instrumental] [--sem-estilo ...]
        # Upload and Cover (12 cr): sobe a música de referência e a Suno canta a letra por cima dela.
        # Método do Dan (Trendscale): letra com a emoção escrita no fim, ESTILO vazio ("-"), peso-audio 0.75.
  python3 kie.py suno-persona SAIDA.mp3.task.json NUM_FAIXA "Nome" "Descrição da voz" [--de 10 --ate 40]
        # Fixa a voz de uma faixa já gerada (suno ou suno-ref) num persona_id, para todos os hooks
        # cantarem com a mesma voz. Use o persona_id com --persona em suno e suno-ref.
  python3 kie.py espera TASK_ID SAIDA                   # retoma uma tarefa já criada, sem cobrar de novo
  python3 kie.py lote PEDIDOS.json [--teste] [--intervalo 0.6]
        # Várias gerações num comando só (depois do ok de crédito). PEDIDOS.json = lista de
        # {"cmd": "kling4", "args": ["P.txt", "S.mp4", "--dur", "5", "--imagem", "A.png"]}: args na mesma ordem
        # do subcomando (posicionais primeiro). Opcional "saida" quando o script não acha sozinho.
        # Dispara um kie.py por pedido, em paralelo (0,6 s entre disparos; o Kie aceita 20 a cada 10 s), espera
        # todos e imprime uma linha por pedido
        # (saída, status ok/erro/barrado, taskId, cr). Resumo em PEDIDOS.resultado.tsv, logs em PEDIDOS.logs/.
        # Pedido com SAIDA.task.json já existente vira `espera` (não cobra de novo). --teste repassa --teste.

O taskId sai na tela e fica em SAIDA.task.json assim que a tarefa é criada: se cair a conexão, use `espera`,
não reenvie (cobra duas vezes). A mídia gerada some em 14 dias: baixar sempre.
As chaves e a impressão (12 caracteres do SHA-256) moram em @CLIENTES/_CHAVES/ (Fefo, 11/11/2026); o script lê
~/.vsl-batch-editor/, que tem atalhos para lá (_CHAVES/ligar_chaves.sh). Nunca no zip, perfil.json, ficha, nota ou módulo.
"""
import hashlib, json, mimetypes, re, os, secrets, sys, time, urllib.parse, urllib.request, urllib.error

API = 'https://api.kie.ai'
UPLOAD = 'https://kieai.redpandaai.co/api/file-stream-upload'   # host do exemplo dos docs
UA = 'fefo-vsl/1.0'
ESPERA_MAX = 1200   # s
TESTE = '--teste' in sys.argv


AQUI = os.path.dirname(os.path.abspath(__file__))
IMPRESSOES = os.path.expanduser('~/.vsl-batch-editor/kie_impressoes.json')   # atalho para @CLIENTES/_CHAVES/

if '--conta' in sys.argv:
    sys.exit('Sem --conta. A conta vem do cliente: --cliente ev|ts, ou o kie.py da pasta do cliente.')


def _fichas():
    """Fichas de cliente: <núcleo>/clientes/*.json (ou scripts/clientes/ quando o script vai dentro de uma skill)."""
    for pasta in (os.path.join(AQUI, '..', 'clientes'), os.path.join(AQUI, 'clientes')):
        if not os.path.isdir(pasta):
            continue
        fichas = {}
        for nome in sorted(os.listdir(pasta)):
            if nome.endswith('.json'):
                f = json.load(open(os.path.join(pasta, nome), encoding='utf-8'))
                if f.get('id') and (f.get('kie') or {}).get('chave'):
                    f['_arquivo'] = nome[:-5]
                    fichas[f['id']] = f
        if fichas:
            return fichas
    sys.exit(f'Sem ficha de cliente em {os.path.normpath(os.path.join(AQUI, "..", "clientes"))}')


def _tira_opcao(nome):
    """Tira `nome VALOR` do sys.argv e devolve VALOR."""
    if nome not in sys.argv:
        return None
    i = sys.argv.index(nome)
    if i + 1 >= len(sys.argv):
        sys.exit(f'{nome} pede um valor')
    valor = sys.argv[i + 1]
    del sys.argv[i:i + 2]
    return valor


FICHAS = _fichas()
PEDIDO = _tira_opcao('--cliente') or os.environ.get('KIE_CLIENTE')   # cliente dito por quem chamou
CONTA = FICHA = CHAVE = None                                          # definidos em _trava_cliente()
_CHAVE_OK = None


def _acha_cliente(nome):
    n = nome.strip().lower()
    for f in FICHAS.values():
        if n in (f['id'].lower(), f['_arquivo'].lower(), f.get('nome', '').lower()):
            return f['id']
    sys.exit(f'Cliente {nome!r} sem ficha. Clientes: {", ".join(FICHAS)}')


def _cliente_do_caminho(caminho):
    """id do cliente dono da pasta onde o caminho está; None fora das pastas de cliente."""
    partes = os.path.abspath(caminho).split(os.sep)
    for f in FICHAS.values():
        if f.get('pasta') and f['pasta'] in partes:
            return f['id']
    return None


def _nome(cid):
    return FICHAS[cid].get('nome', cid)


def _trava_cliente(caminhos=()):
    """Define o cliente (CONTA, FICHA, CHAVE) e recusa cruzar a conta de um cliente com a pasta de outro."""
    global CONTA, FICHA, CHAVE
    donos = {}
    for c in caminhos:
        dono = _cliente_do_caminho(c)
        if dono:
            donos.setdefault(dono, c)
    if len(donos) > 1:
        sys.exit('RECUSADO: o pedido mistura pastas de clientes diferentes: '
                 + '; '.join(f'{_nome(d)} → {c}' for d, c in donos.items()))
    da_pasta = next(iter(donos), None)
    pedido = _acha_cliente(PEDIDO) if PEDIDO else None
    if pedido and da_pasta and pedido != da_pasta:
        sys.exit(f'RECUSADO: a conta pedida é a de {_nome(pedido)}, mas a saída fica na pasta de {_nome(da_pasta)} '
                 f'({donos[da_pasta]}). Cada cliente paga na sua conta do Kie: use o kie.py da pasta de '
                 f'{_nome(da_pasta)} ou --cliente {da_pasta}.')
    if CONTA and (pedido or da_pasta) and (pedido or da_pasta) != CONTA:
        sys.exit(f'RECUSADO: este processo já está na conta de {_nome(CONTA)}; saída de outro cliente.')
    if not CONTA:
        CONTA = (pedido or da_pasta or (next(iter(FICHAS)) if len(FICHAS) == 1 else None)
                 or _cliente_do_caminho(os.getcwd()))
    if not CONTA:
        sys.exit(f'Diga o cliente: --cliente {"|".join(FICHAS)} (a saída está fora das pastas de cliente).')
    FICHA = FICHAS[CONTA]
    CHAVE = os.path.expanduser(FICHA['kie']['chave'])


def _le_chave(cid):
    try:
        return open(os.path.expanduser(FICHAS[cid]['kie']['chave'])).read().strip()
    except OSError:
        return ''


def _impressao(chave):
    return hashlib.sha256(chave.encode()).hexdigest()[:12]


def _impressoes():
    try:
        return json.load(open(IMPRESSOES))
    except (OSError, ValueError):
        return {}


def _grava_impressao(cid, imp):
    reg = _impressoes()
    reg[cid] = imp
    os.makedirs(os.path.dirname(IMPRESSOES), exist_ok=True)
    json.dump(reg, open(IMPRESSOES, 'w'), indent=1)
    try:
        os.chmod(IMPRESSOES, 0o600)
    except OSError:
        pass


def _confere_chave(cid, registrar=False):
    """Devolve a chave do cliente, depois de conferir que ela é dele e só dele."""
    chave = _le_chave(cid)
    arq = FICHAS[cid]['kie']['chave']
    if not chave:
        sys.exit(f'Sem chave do Kie de {_nome(cid)} em {arq}. Não use a chave de outro cliente: avise o Fefo.')
    imp, reg = _impressao(chave), _impressoes()
    for outro in FICHAS:
        if outro == cid:
            continue
        if _le_chave(outro) == chave:
            sys.exit(f'RECUSADO: a chave em {arq} ({_nome(cid)}) é igual à de {_nome(outro)}. '
                     'Duas contas com a mesma chave: uma delas está errada. Avise o Fefo.')
        if reg.get(outro) == imp:
            sys.exit(f'RECUSADO: a chave em {arq} ({_nome(cid)}) é a que está registrada para {_nome(outro)}. '
                     'Arquivos de chave trocados? Avise o Fefo.')
    if registrar or cid not in reg:
        _grava_impressao(cid, imp)
        print(f'Chave de {_nome(cid)} registrada (impressão {imp}).', file=sys.stderr, flush=True)
    elif reg[cid] != imp:
        sys.exit(f'RECUSADO: a chave de {_nome(cid)} em {arq} mudou (registrada {reg[cid]}, agora {imp}). '
                 f'Se o Fefo trocou a chave dessa conta, confirme com ele e rode: kie.py --cliente {cid} registrar-chave')
    return chave


def _chave():
    global _CHAVE_OK
    if not CONTA:
        _trava_cliente()
    if _CHAVE_OK is None:
        _CHAVE_OK = _confere_chave(CONTA)
    return _CHAVE_OK


RES_IMAGEM = {'1K': 1, '2K': 2, '4K': 3}
RES_VIDEO = {'480p': 1, '720p': 2, '1080p': 3, '2K': 4, '4K': 5}


def _res(a, tipo):
    """--res do pedido, com o padrão e o teto da ficha do cliente (tipo = 'imagem' ou 'video')."""
    k = FICHA['kie']
    escala = RES_IMAGEM if tipo == 'imagem' else RES_VIDEO
    res = _opcao(a, '--res', k.get(f'{tipo}_res_padrao', '2K' if tipo == 'imagem' else '720p'))
    teto = k.get(f'{tipo}_res_max')
    if teto and escala.get(res, 0) > escala.get(teto, 99):
        sys.exit(f'RECUSADO: --res {res} passa do teto de {FICHA["nome"]} ({tipo}: {teto}).')
    return res


def contas(com_saldo=False):
    """Lista os clientes e confere as chaves, sem gastar."""
    global CONTA, FICHA, CHAVE, _CHAVE_OK
    reg = _impressoes()
    for cid, f in FICHAS.items():
        chave = _le_chave(cid)
        if not chave:
            estado = 'SEM CHAVE'
        else:
            imp = _impressao(chave)
            iguais = [_nome(o) for o in FICHAS if o != cid and _le_chave(o) == chave]
            trocada = [_nome(o) for o in FICHAS if o != cid and reg.get(o) == imp]
            if iguais:
                estado = f'ERRO: mesma chave de {", ".join(iguais)}'
            elif trocada:
                estado = f'ERRO: chave registrada para {", ".join(trocada)}'
            elif cid not in reg:
                estado = f'sem registro (impressão {imp}; registra no primeiro uso)'
            elif reg[cid] != imp:
                estado = f'MUDOU (registrada {reg[cid]}, agora {imp}): registrar-chave depois de confirmar'
            else:
                estado = f'ok (impressão {imp})'
        linha = f'{cid:4} {f.get("nome", ""):15} pasta {f.get("pasta", "-"):16} chave {f["kie"]["chave"]} · {estado}'
        if com_saldo and estado.startswith('ok'):
            CONTA, FICHA, CHAVE, _CHAVE_OK = cid, f, os.path.expanduser(f['kie']['chave']), None
            linha += f' · saldo {saldo()}'
        print(linha)


def _pede(url, corpo=None, tipo='application/json'):
    req = urllib.request.Request(url, data=corpo, headers={
        'Authorization': f'Bearer {_chave()}', 'Content-Type': tipo, 'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f'HTTP {e.code}: {e.read().decode(errors="replace")[:400]}')
    if d.get('code') != 200:   # erro do Kie volta com HTTP 200 e o código no corpo
        sys.exit(f'Kie {d.get("code")}: {d.get("msg")}')
    return d['data']


def saldo():
    return _pede(f'{API}/api/v1/chat/credit')


def upload(caminho):
    limite = secrets.token_hex(16)
    nome = os.path.basename(caminho)
    tipo = mimetypes.guess_type(nome)[0] or 'application/octet-stream'
    corpo = b''.join([
        f'--{limite}\r\nContent-Disposition: form-data; name="uploadPath"\r\n\r\nvsl\r\n'.encode(),
        f'--{limite}\r\nContent-Disposition: form-data; name="file"; filename="{nome}"\r\n'
        f'Content-Type: {tipo}\r\n\r\n'.encode(),
        open(caminho, 'rb').read(),
        f'\r\n--{limite}--\r\n'.encode()])
    return _pede(UPLOAD, corpo, f'multipart/form-data; boundary={limite}')['downloadUrl']


def cria(modelo, entrada, saida):
    if TESTE:
        sys.exit(json.dumps({'model': modelo, 'input': entrada}, ensure_ascii=False, indent=1))
    corpo = json.dumps({'model': modelo, 'input': entrada}).encode()
    task = _pede(f'{API}/api/v1/jobs/createTask', corpo)['taskId']
    json.dump({'taskId': task, 'cliente': CONTA, 'model': modelo, 'input': entrada},
              open(saida + '.task.json', 'w'), ensure_ascii=False, indent=1)
    print(f'taskId {task}', flush=True)
    return task


def _confere_tarefa(saida):
    """A tarefa guardada em SAIDA.task.json é de outro cliente? Então não é desta conta."""
    try:
        dono = json.load(open(saida + '.task.json')).get('cliente')
    except (OSError, ValueError):
        return
    if dono and dono != CONTA:
        sys.exit(f'RECUSADO: {saida}.task.json é uma tarefa da conta de {_nome(dono) if dono in FICHAS else dono}, '
                 f'e este pedido está na conta de {_nome(CONTA)}.')


def espera(task, saida):
    _confere_tarefa(saida)
    fim = time.time() + ESPERA_MAX
    estado = None
    while time.time() < fim:
        d = _pede(f'{API}/api/v1/jobs/recordInfo?taskId={urllib.parse.quote(task)}')
        if d['state'] != estado:
            estado = d['state']
            print(estado, flush=True)
        if estado == 'fail':
            sys.exit(f'Falhou: {d.get("failCode")} {d.get("failMsg")}')
        if estado == 'success':
            urls = _urls(d)
            if len(urls) == 1:
                saidas = [saida]
            else:   # Suno: várias faixas
                base, ext = os.path.splitext(saida)
                saidas = [f'{base}_{i}{ext}' for i in range(1, len(urls) + 1)]
            for url, arq in zip(urls, saidas):
                req = urllib.request.Request(url, headers={'User-Agent': UA})   # sem a chave: é outro host
                with urllib.request.urlopen(req, timeout=300) as r, open(arq, 'wb') as f:
                    f.write(r.read())
            ids = _ids_faixas(d)
            if ids:   # Suno: guarda os ids das faixas (para suno-persona)
                json.dump({'taskId': task, 'faixas': [{'arquivo': a, 'audio_id': i} for a, i in zip(saidas, ids)]},
                          open(saida + '.faixas.json', 'w'), ensure_ascii=False, indent=1)
            print(f'{", ".join(saidas)} · {d.get("creditsConsumed")} cr · {d.get("costTime")} s · conta {CONTA} ({FICHA["nome"]})')
            return d
        time.sleep(10)
    sys.exit(f'Sem resultado em {ESPERA_MAX} s. Retome com: python3 kie.py espera {task} {saida}')


def _urls(d):
    """URLs do resultado: resultJson.resultUrls (imagem, vídeo, tts) ou response.data[].audio_url (Suno)."""
    try:
        r = json.loads(d.get('resultJson') or '{}')
    except ValueError:
        r = {}
    if r.get('resultUrls'):
        return r['resultUrls']
    faixas = (d.get('response') or r.get('response') or {}).get('data') or r.get('data') or []
    urls = [f.get('audio_url') or f.get('audioUrl') for f in faixas if isinstance(f, dict)]
    urls = [u for u in urls if u]
    if not urls:
        sys.exit('Sucesso sem URL reconhecida. Resposta: ' + json.dumps(d, ensure_ascii=False)[:800])
    return urls


def _ids_faixas(d):
    try:
        r = json.loads(d.get('resultJson') or '{}')
    except ValueError:
        r = {}
    faixas = (d.get('response') or r.get('response') or {}).get('data') or r.get('data') or []
    return [f.get('id') for f in faixas if isinstance(f, dict) and (f.get('audio_url') or f.get('audioUrl'))]


def _suno_extras(a, entrada):
    for opc, campo, conv in (('--voz', 'vocal_gender', str), ('--dur', 'duration', int),
                             ('--sem-estilo', 'negative_tags', str), ('--peso-estilo', 'style_weight', float),
                             ('--peso-audio', 'audio_weight', float)):
        if _opcao(a, opc) is not None:
            entrada[campo] = conv(_opcao(a, opc))
    if _opcao(a, '--persona'):
        entrada['persona_id'] = _opcao(a, '--persona')
        entrada['persona_model'] = 'style_persona'


def _modelo_suno():
    return FICHA['kie'].get('suno_modelo', 'V5_5')   # Trendscale no V6 (05/11/2026)


def _opcao(args, nome, padrao=None):
    if nome in args:
        return args[args.index(nome) + 1]
    return padrao


def _opcoes(args, nome):
    return [args[i + 1] for i, x in enumerate(args) if x == nome]


def _sobe(caminho):
    return caminho if TESTE else upload(caminho)


def _texto(caminho):
    return open(caminho, encoding='utf-8').read().strip()


# Posição da SAIDA entre os args de cada subcomando (args = o que vem depois do nome do subcomando).
POS_SAIDA = {'sunburst': 1, 'nanopro': 1, 'seedream': 1, 'omni': 2, 'kling3': 2, 'kling4': 1, 'seedance': 1, 'tts': 1,
             'suno': 1, 'suno-ref': 2, 'espera': 1}
BARRADO = re.compile(r'sensitive|moderat|policy|nsfw|inappropriate|prohibit|violat|safety|copyright|'
                     r'celebrit|public figure', re.I)


def _excecao(cmd, saidas):
    """Exceção por job a um modelo proibido (ficha: kie.excecoes.<cmd>.pastas). Toda saída precisa estar numa pasta liberada."""
    ex = (FICHA['kie'].get('excecoes') or {}).get(cmd) or {}
    pastas = ex.get('pastas') or []
    return bool(saidas) and all(any(p in os.path.abspath(s) for p in pastas) for s in saidas)


def lote(caminho, intervalo=0.6):
    """Dispara cada pedido como um kie.py próprio (subprocesso), em paralelo, e resume no fim."""
    import subprocess
    pedidos = json.load(open(caminho, encoding='utf-8'))
    if not isinstance(pedidos, list) or not pedidos:
        sys.exit('lote: o JSON precisa ser uma lista de pedidos')
    proibidos = FICHA['kie'].get('proibidos') or {}
    base = os.path.splitext(caminho)[0]
    logs = base + '.logs'
    os.makedirs(logs, exist_ok=True)
    script = os.path.abspath(__file__)
    itens, vistas = [], set()
    for n, p in enumerate(pedidos, 1):
        cmd, args = p.get('cmd'), [str(x) for x in p.get('args', [])]
        if cmd not in POS_SAIDA or cmd == 'espera':
            sys.exit(f'lote: pedido {n} com cmd inválido: {cmd!r} (use {", ".join(k for k in POS_SAIDA if k != "espera")})')
        saida = p.get('saida') or (args[POS_SAIDA[cmd]] if len(args) > POS_SAIDA[cmd] else None)
        if not saida:
            sys.exit(f'lote: pedido {n} sem saída')
        if saida in vistas:
            sys.exit(f'lote: saída repetida {saida} (pedido {n})')
        vistas.add(saida)
        if cmd in proibidos and not _excecao(cmd, [saida]):
            sys.exit(f'RECUSADO: pedido {n}: {cmd} não roda em {FICHA["nome"]}: {proibidos[cmd]}')
        _trava_cliente([saida])     # todas as saídas na pasta do mesmo cliente da conta
        _confere_tarefa(saida)
        if not TESTE and os.path.exists(saida + '.task.json'):   # já criada: só espera e baixa, sem cobrar
            task = json.load(open(saida + '.task.json')).get('taskId')
            cmd, args = 'espera', [task, saida]
        if TESTE:
            args = args + ['--teste']
        itens.append({'n': n, 'cmd': cmd, 'args': args, 'saida': saida,
                      'log': os.path.join(logs, f'{n:02d}_{os.path.basename(saida)}.log')})
    if not TESTE:
        _chave()                    # confere a chave uma vez, antes de disparar
    print(f'{len(itens)} pedidos na conta {CONTA} ({FICHA["nome"]})'
          + (' (teste, nada é enviado)' if TESTE else f', ~{intervalo:g} s entre disparos'), flush=True)
    for i, it in enumerate(itens):
        if i and not TESTE:
            time.sleep(intervalo)
        it['arq'] = open(it['log'], 'w')
        it['proc'] = subprocess.Popen([sys.executable, script, it['cmd']] + it['args'],
                                      stdout=it['arq'], stderr=subprocess.STDOUT,
                                      env={**os.environ, 'KIE_LOTE': '1', 'KIE_CLIENTE': CONTA})
        print(f'  {it["n"]:02d} {it["cmd"]} → {it["saida"]}', flush=True)
    linhas = []
    for it in itens:
        cod = it['proc'].wait()
        it['arq'].close()
        txt = open(it['log'], encoding='utf-8', errors='replace').read()
        task = re.search(r'taskId (\S+)', txt)
        task = task.group(1) if task else (it['args'][0] if it['cmd'] == 'espera' else '')
        cr = re.search(r'· (\S+) cr ·', txt)
        cr = cr.group(1) if cr else ''
        ultima = (txt.strip().splitlines() or [''])[-1][:200]
        if TESTE:
            status = 'teste' if '"model"' in txt else 'erro'
            ultima = '' if status == 'teste' else ultima
        elif cod == 0:
            status, ultima = 'ok', ''
        else:
            status = 'barrado' if BARRADO.search(ultima) else 'erro'
        linhas.append((it['saida'], status, task, cr, ultima))
    with open(base + '.resultado.tsv', 'w', encoding='utf-8') as f:
        f.write('saida\tstatus\ttaskId\tcr\tmotivo\n')
        for l in linhas:
            f.write('\t'.join(l) + '\n')
    print('---')
    for s, st, t, c, m in linhas:
        print(f'{st:8} {s} · {t or "-"} · {c + " cr" if c else "-"}' + (f' · {m}' if m else ''))
    total = sum(float(c) for *_, c, _ in linhas if c.replace('.', '', 1).isdigit())
    ok = sum(1 for l in linhas if l[1] in ('ok', 'teste'))
    print(f'{ok}/{len(linhas)} ok · {total:g} cr · conta {CONTA} ({FICHA["nome"]}) · resumo em {base}.resultado.tsv · logs em {logs}/')
    if TESTE:
        print(f'O pedido montado de cada um está no log ({logs}/).')


def _aviso_fora_do_lote(cmd):
    """Geração avulsa (fora do `lote`): se já houve outra nos últimos 2 min, avisa para usar o lote (Fefo, 09/11/2026)."""
    if TESTE or os.environ.get('KIE_LOTE') or cmd in ('lote', 'saldo', 'upload', 'espera', 'suno-persona'):
        return
    reg = os.path.expanduser(f'~/.vsl-batch-editor/kie_avulsos_{CONTA}.log')
    agora = time.time()
    try:
        antes = [float(x) for x in open(reg).read().split() if agora - float(x) < 120]
    except (OSError, ValueError):
        antes = []
    try:
        open(reg, 'w').write(' '.join(str(x) for x in antes + [agora]))
    except OSError:
        pass
    if antes:
        print(f'AVISO: {len(antes) + 1} gerações avulsas em 2 min. Regra do Fefo: tudo em paralelo pelo '
              '`kie.py lote PEDIDOS.json` (até 20 pedidos por 10 s), nunca um a um.', file=sys.stderr, flush=True)


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] == 'contas':
        return contas('--saldo' in a)
    if a[0] == 'registrar-chave':
        if not PEDIDO:
            sys.exit('registrar-chave pede o cliente: kie.py --cliente ev|ts registrar-chave')
        _trava_cliente()
        return _confere_chave(CONTA, registrar=True) and None
    # caminhos que dizem de quem é o pedido: a saída de cada subcomando, o PEDIDOS.json do lote, o arquivo do upload
    pos = {'upload': 1, 'suno-persona': 1}.get(a[0], POS_SAIDA.get(a[0], -1) + 1)
    caminhos = [a[pos]] if 0 < pos < len(a) and not a[pos].startswith('--') else []
    if a[0] == 'lote':
        caminhos = [x for x in a[1:] if not x.startswith('--') and x != _opcao(a, '--intervalo')][:1]
        try:   # as saídas de dentro do PEDIDOS.json também dizem de quem é o lote
            for p in json.load(open(caminhos[0], encoding='utf-8')):
                args, i = [str(x) for x in p.get('args', [])], POS_SAIDA.get(p.get('cmd'), 99)
                caminhos.append(p.get('saida') or (args[i] if len(args) > i else caminhos[0]))
        except (IndexError, OSError, ValueError, AttributeError):
            pass
    _trava_cliente(caminhos)
    if a[0] in (FICHA['kie'].get('proibidos') or {}) and not _excecao(a[0], [a[POS_SAIDA[a[0]]+1]] if len(a) > POS_SAIDA.get(a[0], 99)+1 else []):
        sys.exit(f'RECUSADO: {a[0]} não roda em {FICHA["nome"]}: {FICHA["kie"]["proibidos"][a[0]]}')
    _aviso_fora_do_lote(a[0])
    if a[0] == 'lote':
        arq = next((x for x in a[1:] if not x.startswith('--') and x != _opcao(a, '--intervalo')), None)
        if not arq:
            sys.exit('lote pede PEDIDOS.json')
        lote(arq, float(_opcao(a, '--intervalo', '0.6')))
    elif a[0] == 'saldo':
        print(saldo(), f'· conta {CONTA} ({FICHA["nome"]})')
    elif a[0] == 'upload':
        print(upload(a[1]))
    elif a[0] == 'sunburst':
        prompt, saida = _texto(a[1]), a[2]
        refs = _opcoes(a, '--ref')
        entrada = {'prompt': prompt, 'aspect_ratio': _opcao(a, '--ratio', '9:16'), 'resolution': _res(a, 'imagem')}
        if refs:
            entrada['input_urls'] = [_sobe(r) for r in refs]
        tipo = 'image-to-image' if refs else 'text-to-image'
        espera(cria(f'gpt-image-2-5-sunburst-{tipo}', entrada, saida), saida)
    elif a[0] == 'seedream':
        prompt, saida = _texto(a[1]), a[2]
        refs = _opcoes(a, '--ref')
        entrada = {'prompt': prompt, 'aspect_ratio': _opcao(a, '--ratio', '9:16'), 'size': _res(a, 'imagem'),
                   'output_format': 'png'}
        if refs:
            entrada['image_urls'] = [_sobe(r) for r in refs]
        tipo = 'image-to-image' if refs else 'text-to-image'
        espera(cria(f'seedream/5-5-{tipo}', entrada, saida), saida)
    elif a[0] == 'nanopro':
        prompt, saida = _texto(a[1]), a[2]
        entrada = {'prompt': prompt, 'aspect_ratio': _opcao(a, '--ratio', '9:16'), 'resolution': _res(a, 'imagem'),
                   'output_format': 'png', 'image_input': [_sobe(r) for r in _opcoes(a, '--ref')]}
        espera(cria('nano-banana-pro', entrada, saida), saida)
    elif a[0] == 'omni':
        prompt, imagem, saida = _texto(a[1]), a[2], a[3]
        entrada = {'prompt': prompt, 'image_urls': [_sobe(imagem)], 'duration': _opcao(a, '--dur', '8'),
                   'aspect_ratio': '9:16', 'resolution': _res(a, 'video')}
        espera(cria('gemini-omni-video', entrada, saida), saida)
    elif a[0] == 'kling3':
        prompt, imagem, saida = _texto(a[1]), a[2], a[3]
        entrada = {'prompt': prompt, 'sound': '--sem-som' not in a, 'duration': _opcao(a, '--dur', '5'),
                   'mode': _opcao(a, '--mode', 'std'), 'multi_shots': False}
        if imagem == '-':
            entrada['aspect_ratio'] = '9:16'
        else:
            entrada['image_urls'] = [_sobe(imagem)] + [_sobe(f) for f in _opcoes(a, '--fim')]
        espera(cria('kling-3.0/video', entrada, saida), saida)
    elif a[0] == 'kling4':
        prompt, saida = _texto(a[1]), a[2]
        entrada = {'prompt': prompt, 'duration': int(_opcao(a, '--dur', '5')), 'resolution': _res(a, 'video'),
                   'aspect_ratio': '9:16'}
        if _opcoes(a, '--video'):
            entrada['video_urls'] = [_sobe(v) for v in _opcoes(a, '--video')]
        if _opcoes(a, '--imagem'):
            entrada['image_urls'] = [_sobe(i) for i in _opcoes(a, '--imagem')]
        if _opcoes(a, '--voz'):
            entrada['voices'] = [{'name': n, 'audio_url': _sobe(c)}
                                 for n, c in (v.split('=', 1) for v in _opcoes(a, '--voz'))]
        espera(cria('kling-4.0/reference-to-video', entrada, saida), saida)
    elif a[0] == 'seedance':
        prompt, saida = _texto(a[1]), a[2]
        entrada = {'prompt': prompt, 'duration': int(_opcao(a, '--dur', '5')), 'resolution': _res(a, 'video'),
                   'aspect_ratio': '9:16', 'generate_audio': '--sem-som' not in a}
        if _opcoes(a, '--imagem'):
            entrada['reference_image_urls'] = [_sobe(i) for i in _opcoes(a, '--imagem')]
        if _opcoes(a, '--audio'):
            entrada['reference_audio_urls'] = [_sobe(c) for c in _opcoes(a, '--audio')]
        espera(cria('bytedance/seedance-2-5', entrada, saida), saida)
    elif a[0] == 'tts':
        texto, saida = _texto(a[1]), a[2]
        voz = _opcao(a, '--voz') or sys.exit('tts pede --voz ID')
        tag = re.search(r'\[[^\[\]\n]{1,40}\]', texto)
        if tag:   # Multilingual v2 não entende tag de áudio e lê em voz alta (13/11/2026)
            sys.exit(f'RECUSADO: o tts do Kie é o Multilingual v2, que leria {tag.group(0)} em voz alta. '
                     'Tire as tags ou gere no v3/v4 (Trendscale: elevenlabs.py).')
        entrada = {'text': texto, 'voice': voz, 'speed': float(_opcao(a, '--speed', '1'))}
        espera(cria('elevenlabs/text-to-speech-multilingual-v2', entrada, saida), saida)
    elif a[0] == 'suno':
        estilo, saida = _texto(a[1]), a[2]
        titulo = _opcao(a, '--titulo') or sys.exit('suno pede --titulo')
        entrada = {'custom_mode': True, 'instrumental': '--instrumental' in a,
                   'model': _opcao(a, '--modelo', _modelo_suno()), 'title': titulo[:80], 'style': estilo}
        if _opcao(a, '--letra'):
            entrada['prompt'] = _texto(_opcao(a, '--letra'))
        _suno_extras(a, entrada)
        espera(cria('ai-music-api/generate', entrada, saida), saida)
    elif a[0] == 'suno-ref':
        ref, estilo, saida = a[1], a[2], a[3]
        titulo = _opcao(a, '--titulo') or sys.exit('suno-ref pede --titulo')
        entrada = {'upload_url': _sobe(ref), 'instrumental': '--instrumental' in a,
                   'model': _opcao(a, '--modelo', _modelo_suno()), 'title': titulo[:80]}
        if estilo != '-':
            entrada['style'] = _texto(estilo)
        if _opcao(a, '--letra'):
            entrada['lyrics'] = _texto(_opcao(a, '--letra'))
        _suno_extras(a, entrada)
        espera(cria('ai-music-api/upload-and-cover-audio', entrada, saida), saida)
    elif a[0] == 'suno-persona':
        info = json.load(open(a[1].replace('.task.json', '') + '.faixas.json'))
        faixa = info['faixas'][int(a[2]) - 1]
        entrada = {'task_id': info['taskId'], 'audio_id': faixa['audio_id'], 'name': a[3], 'description': a[4]}
        if _opcao(a, '--de') is not None:
            entrada['vocal_start'] = float(_opcao(a, '--de'))
            entrada['vocal_end'] = float(_opcao(a, '--ate'))
        saida = a[1].replace('.task.json', '') + '.persona'
        task = cria('ai-music-api/generate-persona', entrada, saida)
        for _ in range(ESPERA_MAX // 5):   # persona não tem arquivo para baixar: só o id
            d = _pede(f'{API}/api/v1/jobs/recordInfo?taskId={urllib.parse.quote(task)}')
            if d['state'] == 'fail':
                sys.exit(f'Falhou: {d.get("failCode")} {d.get("failMsg")}')
            if d['state'] == 'success':
                pid = re.search(r'"persona_?[iI]d"\s*:\s*"([^"]+)"', json.dumps(d))
                pid = pid.group(1) if pid else None
                open(saida + '.json', 'w').write(json.dumps({'persona_id': pid, 'nome': a[3], 'resposta': d},
                                                             ensure_ascii=False, indent=1))
                print(f'persona_id {pid} · {d.get("creditsConsumed")} cr · salvo em {saida}.json')
                break
            time.sleep(5)
    elif a[0] == 'espera':
        espera(a[1], a[2])
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
