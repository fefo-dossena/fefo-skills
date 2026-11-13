#!/usr/bin/env python3
"""Frame.io V4 do Fefo — login, listar pasta, subir vídeo como nova versão, ler comentários.

Uso:
  python3 frameio.py login                              # 1x: abre o login da Adobe (rodar no SEU terminal)
  python3 frameio.py eu                                 # confere quem está logado e as contas
  python3 frameio.py ls "Hike Balance Brand/FEFO"       # lista a pasta (projeto/pasta/subpasta…)
  python3 frameio.py versao "Hike Balance Brand/FEFO" ARQ1.mp4 ARQ2.mp4 …
        # sobe cada arquivo e empilha como versão nova do item com o MESMO nome na pasta
        # (procura também nas subpastas). Sem item com esse nome → só sobe. --teste = só mostra o plano.
  python3 frameio.py nova "Hike Balance Brand/FEFO/BATCH_1970" ARQ1.mp4 …  [--teste]
        # padrão de pastas: o que está solto na pasta da batch vai para V<n> e os novos entram na raiz
  python3 frameio.py links "Hike Balance Brand/FEFO/BATCH_1971"   # 1 link f.io público por marca (vídeos da raiz)
  python3 frameio.py comentarios "Hike Balance Brand/FEFO" [filtro_nome]
  python3 frameio.py comentarios "Hike Balance Brand/FEFO/BATCH_3858" --revisao <pasta da batch> [--versao 5]
        # notas dos vídeos atuais -> <batch>/00_roteiro/revisao_V<k>.md (item 6 do checklist da Louise)

Trava (Frente 4, 13/11/2026): `versao` e `nova` recusam vídeo sem checklist da Louise verde para aquele arquivo
(<auto>/checklist_V<k>.json, mesma impressão digital) e vídeo de prévia (.PREVIA.txt). Dispensa do Fefo não vale.

O acesso fica em ~/.frameio/tokens.json (só no seu Mac) e é renovado sozinho.
"""
import base64, hashlib, json, os, re, secrets, sys, time, urllib.parse, urllib.request, urllib.error, webbrowser

CLIENT_ID = '5eabeba7800e46eda63ad4b4a14ba79f'       # credencial "OAuth Single-Page App" (não é segredo)
REDIRECT = 'https://localhost/callback'
SCOPES = 'openid email profile offline_access additional_info.roles'
IMS = 'https://ims-na1.adobelogin.com/ims'
API = 'https://api.frame.io/v4'
TOK = os.path.expanduser('~/.frameio/tokens.json')
UA = 'fefo-frameio/1.0'   # o firewall do Frame.io barra o User-Agent padrão do Python (403)


# ---------- autenticação (PKCE, sem client secret) ----------
def _post_form(url, data):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(),
                                 headers={'Content-Type': 'application/x-www-form-urlencoded', 'User-Agent': UA})
    with urllib.request.urlopen(req) as r:
        return json.load(r)

def _salva(t):
    t['expira_em'] = time.time() + int(t.get('expires_in', 3600)) - 120
    os.makedirs(os.path.dirname(TOK), exist_ok=True)
    with open(TOK, 'w') as f:
        json.dump(t, f)
    os.chmod(TOK, 0o600)

def login():
    ver = base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b'=').decode()
    chal = base64.urlsafe_b64encode(hashlib.sha256(ver.encode()).digest()).rstrip(b'=').decode()
    st = secrets.token_urlsafe(16)
    url = f'{IMS}/authorize/v2?' + urllib.parse.urlencode({
        'client_id': CLIENT_ID, 'redirect_uri': REDIRECT, 'scope': SCOPES, 'response_type': 'code',
        'code_challenge': chal, 'code_challenge_method': 'S256', 'state': st})
    print('\n1) Vai abrir o login da Adobe no navegador. Entre e autorize.')
    print('2) No fim aparece uma página de erro em "localhost" — é normal.')
    print('3) Clique na barra de endereço e COPIE a URL (Cmd+L, Cmd+C). Não precisa colar aqui:')
    print('   o script lê da área de transferência (a URL passa do limite de uma linha do terminal).\n')
    print(url, '\n')
    webbrowser.open(url)
    print('Esperando você copiar a URL do localhost…', flush=True)
    import subprocess
    while True:   # lê a área de transferência até aparecer a URL de volta deste login
        volta = subprocess.run(['pbpaste'], capture_output=True, text=True).stdout.strip()
        if 'localhost/callback' in volta and st in volta:
            break
        time.sleep(1)
    q = urllib.parse.parse_qs(urllib.parse.urlparse(volta if '://' in volta else 'https://' + volta).query)
    if q.get('state', [''])[0] != st:
        sys.exit('A URL não corresponde a este login (state diferente). Rode "login" de novo.')
    if 'code' not in q:
        sys.exit('Não achei o código na URL: ' + json.dumps(q))
    t = _post_form(f'{IMS}/token/v3', {'grant_type': 'authorization_code', 'client_id': CLIENT_ID,
                                       'code': q['code'][0], 'code_verifier': ver, 'redirect_uri': REDIRECT})
    _salva(t)
    print('\nLogin ok. Acesso salvo em', TOK)

def token():
    if not os.path.exists(TOK):
        sys.exit('Sem login. Rode no seu terminal:  python3 frameio.py login')
    t = json.load(open(TOK))
    if time.time() > t.get('expira_em', 0):
        try:
            n = _post_form(f'{IMS}/token/v3', {'grant_type': 'refresh_token', 'client_id': CLIENT_ID,
                                               'refresh_token': t['refresh_token']})
        except urllib.error.HTTPError as e:
            sys.exit('Login expirou (' + e.read().decode()[:200] + '). Rode: python3 frameio.py login')
        n.setdefault('refresh_token', t['refresh_token'])
        _salva(n); t = n
    return t['access_token']


# ---------- API ----------
def api(met, path, corpo=None, experimental=False):
    h = {'Authorization': 'Bearer ' + token(), 'Content-Type': 'application/json', 'User-Agent': UA}
    if experimental:
        h['api-version'] = 'experimental'
    url = path if path.startswith('http') else API + path
    for tent in range(5):
        req = urllib.request.Request(url, method=met, headers=h,
                                     data=json.dumps(corpo).encode() if corpo is not None else None)
        try:
            with urllib.request.urlopen(req) as r:
                txt = r.read()
                return json.loads(txt) if txt else {}
        except urllib.error.HTTPError as e:
            if e.code == 429 and tent < 4:
                time.sleep(15 * (tent + 1)); continue
            sys.exit(f'Erro {e.code} em {met} {path}: {e.read().decode()[:400]}')

def paginado(path, experimental=False):
    out, url = [], path
    while url:
        r = api('GET', url, experimental=experimental)
        out += r.get('data', [])
        nxt = (r.get('links') or {}).get('next')
        url = (API.rsplit('/v4', 1)[0] + nxt) if nxt and nxt.startswith('/') else nxt
    return out

def conta():
    contas = api('GET', '/accounts')['data']
    for c in contas:
        vistos = set()
        for w in paginado(f"/accounts/{c['id']}/workspaces"):
            for p in paginado(f"/accounts/{c['id']}/workspaces/{w['id']}/projects"):
                vistos.add(p['id']); yield c, w, p
        # projetos em que você foi convidado sem ser do workspace (caso da Umut's Account)
        for p in paginado(f"/accounts/{c['id']}/invited_projects", experimental=True):
            if p['id'] not in vistos:
                vistos.add(p['id']); yield c, {'name': '(convidado)'}, p

def resolve(caminho):
    """'Projeto/pasta/subpasta' → (account_id, folder_id)."""
    partes = [p for p in caminho.split('/') if p]
    for c, w, p in conta():
        if p['name'].strip().lower() == partes[0].strip().lower():
            aid, fid = c['id'], p['root_folder_id']
            for nome in partes[1:]:
                filhos = paginado(f'/accounts/{aid}/folders/{fid}/children')
                ach = [f for f in filhos if f['type'] == 'folder' and f['name'].strip().lower() == nome.strip().lower()]
                if not ach:
                    sys.exit(f'Pasta "{nome}" não encontrada. Existem: ' + ', '.join(f['name'] for f in filhos if f['type'] == 'folder'))
                fid = ach[0]['id']
            return aid, fid
    sys.exit(f'Projeto "{partes[0]}" não encontrado nas contas que você acessa.')

def arvore(aid, fid, prefixo=''):
    for f in paginado(f'/accounts/{aid}/folders/{fid}/children'):
        yield prefixo, fid, f
        if f['type'] == 'folder':
            yield from arvore(aid, f['id'], prefixo + f['name'] + '/')


# ---------- upload ----------
def sobe(aid, fid, arq, nome=None):
    nome = nome or os.path.basename(arq)
    tam = os.path.getsize(arq)
    r = api('POST', f'/accounts/{aid}/folders/{fid}/files/local_upload', {'data': {'name': nome, 'file_size': tam}})['data']
    urls, mt = r['upload_urls'], r.get('media_type') or 'video/mp4'
    pos = 0
    with open(arq, 'rb') as f:
        for k, u in enumerate(urls, 1):
            f.seek(pos); pedaco = f.read(u['size']); pos += u['size']
            for tent in range(4):
                try:
                    req = urllib.request.Request(u['url'], data=pedaco, method='PUT',
                                                 headers={'Content-Type': mt, 'x-amz-acl': 'private', 'User-Agent': UA})
                    urllib.request.urlopen(req).read(); break
                except Exception as e:
                    if tent == 3: sys.exit(f'Falhou a parte {k}/{len(urls)} de {nome}: {e}')
                    time.sleep(5 * (tent + 1))
            print(f'   {nome[-40:]}: parte {k}/{len(urls)}', end='\r', flush=True)
    print(f'   {nome[-40:]}: enviado ({tam/1e6:.0f} MB, {len(urls)} partes)      ')
    return r


# ---------- comandos ----------
def cmd_eu():
    print(json.dumps(api('GET', '/me')['data'], indent=1, ensure_ascii=False)[:800])
    for c, w, p in conta():
        print(f"conta {c.get('display_name') or c['id']} | workspace {w['name']} | projeto {p['name']}")

def cmd_ls(caminho):
    aid, fid = resolve(caminho)
    for pre, _, f in arvore(aid, fid):
        print(f"{f['type']:<13} {pre}{f['name']}")

def _checklist():
    """checklist.py do núcleo (@CLIENTES/_FLUXO/scripts/checagens); None fora da pasta do Fefo (skill dos colegas)."""
    aqui = os.path.dirname(os.path.abspath(__file__))
    for c in (os.path.join(aqui, '..', '..', '..', '..', '_FLUXO', 'scripts', 'checagens'), os.path.join(aqui, 'checagens')):
        if os.path.exists(os.path.join(c, 'checklist.py')):
            import importlib.util as iu
            spec = iu.spec_from_file_location('checklist_fio', os.path.join(c, 'checklist.py'))
            m = iu.module_from_spec(spec); spec.loader.exec_module(m); return m
    return None


def trava_checklist(arqs):
    """Checklist da Louise (Frente 4, 13/11/2026): não sobe vídeo sem checklist verde para aquele arquivo, nem prévia.
    Dispensa do Fefo não vale. Cliente com o checklist desligado na ficha: passa."""
    ck = _checklist()
    if not ck:
        return
    ruins = []
    for a in arqs:
        if os.path.exists(os.path.splitext(a)[0] + '.PREVIA.txt') or os.path.exists(a + '.PREVIA.txt'):
            ruins.append(f'{os.path.basename(a)}: é PRÉVIA; renderize o final e rode o checklist nele'); continue
        e = ck.estado_de(a)
        if not e.get('ativo') or e.get('verde'):
            continue
        falhas = '; '.join(f"item {k}: {' | '.join(v)}" for k, v in (e.get('falhas') or {}).items())
        ruins.append(f"{os.path.basename(a)}: {e.get('motivo') or 'checklist vermelho'}" + (f' ({falhas[:300]})' if falhas else ''))
    if ruins:
        sys.exit('ENTREGA RECUSADA pelo checklist da Louise (sem dispensa):\n  ' + '\n  '.join(ruins) +
                 '\nCorrija e rode `fluxo.py checar <batch>` no arquivo final (ou `checklist.py entrega <batch>`).')


def cmd_versao(caminho, arqs, teste):
    trava_checklist(arqs)
    aid, fid = resolve(caminho)
    idx = {}
    for pre, pai, f in arvore(aid, fid):
        if f['type'] in ('file', 'version_stack'):
            idx.setdefault(f['name'].strip(), []).append((pre, pai, f))
    plano = []
    for a in arqs:
        nome = os.path.basename(a)
        alvo = idx.get(nome.strip(), [])
        if len(alvo) > 1:
            sys.exit(f'Mais de um item chamado "{nome}" na pasta — resolva à mão: ' + ', '.join(p + f['name'] for p, _, f in alvo))
        plano.append((a, nome, alvo[0] if alvo else None))
        print(('VERSÃO NOVA de ' + alvo[0][0] + alvo[0][2]['name'] + f" ({alvo[0][2]['type']})") if alvo else f'SÓ SOBE (sem item igual): {nome}')
    if teste:
        return
    for a, nome, alvo in plano:
        pai = alvo[1] if alvo else fid
        novo = sobe(aid, pai, a, nome)
        if not alvo:
            continue
        ant = alvo[2]
        if ant['type'] == 'file':
            pilha = api('POST', f'/accounts/{aid}/folders/{pai}/version_stacks',
                        {'data': {'file_ids': [ant['id'], novo['id']]}}, experimental=True)['data']
        else:   # já é pilha de versões: move o arquivo novo para dentro dela
            api('PATCH', f"/accounts/{aid}/files/{novo['id']}/move", {'data': {'parent_id': ant['id']}})
            pilha = ant
        print(f"   empilhado → {pilha.get('view_url', '')}")
        time.sleep(7)   # limite de 10 pilhas/min

def cmd_nova(caminho, arqs, teste):
    """Padrão do Fefo: os arquivos soltos na pasta da batch vão para V<n> (próximo número) e os novos entram na raiz."""
    import re
    trava_checklist(arqs)
    aid, fid = resolve(caminho)
    filhos = paginado(f'/accounts/{aid}/folders/{fid}/children')
    nums = [int(m.group(1)) for f in filhos if f['type'] == 'folder' for m in [re.fullmatch(r'V(\d+)', f['name'].strip(), re.I)] if m]
    atuais = [f for f in filhos if f['type'] in ('file', 'version_stack')]
    vn = f'V{max(nums, default=0) + 1}'
    print(f'{len(atuais)} arquivo(s) atuais → {caminho}/{vn}/')
    for f in atuais: print('   ', f['name'])
    print(f'{len(arqs)} arquivo(s) novos → {caminho}/ (raiz)')
    for a in arqs: print(f'    {os.path.basename(a)}  ({os.path.getsize(a)/1e6:.0f} MB)')
    if teste:
        return
    if atuais:
        pasta = api('POST', f'/accounts/{aid}/folders/{fid}/folders', {'data': {'name': vn}})['data']
        for f in atuais:
            api('PATCH', f"/accounts/{aid}/files/{f['id']}/move", {'data': {'parent_id': pasta['id']}})
        print(f'movidos para {vn}')
    for a in arqs:
        sobe(aid, fid, a)
    print('pronto.')

def cmd_links(caminho):
    """1 share público (download liberado) por marca com os vídeos atuais (raiz) da pasta da batch → short_url."""
    aid, fid = resolve(caminho)
    proj = next(p for c, w, p in conta() if p['name'].strip().lower() == caminho.split('/')[0].strip().lower())
    atuais = [f for f in paginado(f'/accounts/{aid}/folders/{fid}/children') if f['type'] in ('file', 'version_stack')]
    batch = caminho.rstrip('/').split('/')[-1].replace('BATCH_', 'BATCH#')
    links = {}
    def marca_de(nome):   # a última marca do nome: o título do card pode citar outra antes ("… Daniel (VisioVance) - Neurobella - AD1")
        n = nome.lower(); pos = {m: n.rfind(m) for m in ('visiovance', 'neurobella')}
        m = max(pos, key=pos.get); return m if pos[m] >= 0 else None
    for marca in ('Visiovance', 'Neurobella'):
        ids = [f['id'] for f in sorted(atuais, key=lambda f: f['name']) if marca_de(f['name']) == marca.lower()]
        if not ids:
            print(f'{marca}: nenhum vídeo na raiz de {caminho}'); continue
        s = api('POST', f"/accounts/{aid}/projects/{proj['id']}/shares", {'data': {
            'type': 'asset', 'access': 'public', 'name': f'{batch} - {marca}',
            'asset_ids': ids, 'downloading_enabled': True}})['data']
        links[marca] = s['short_url']
        print(f"{marca}: {s['short_url']}  ({len(ids)} vídeos)")
        time.sleep(7)   # limite de 10 shares/min
    return links

def cmd_comentarios(caminho, filtro='', batch=None, versao=None):
    """Lista os comentários. Com --revisao <batch>: só os vídeos atuais (raiz da pasta da batch, sem V<n>/) e grava a
    lista de notas <roteiro>/revisao_V<k>.md (item 6 do checklist da Louise) pelo notas_revisao.py do núcleo."""
    aid, fid = resolve(caminho)
    coms = []
    for pre, _, f in arvore(aid, fid):
        if f['type'] != 'file' or filtro.lower() not in f['name'].lower():
            continue
        if batch and re.match(r'V\d+/', pre):          # versão antiga já respondida
            continue
        cs = paginado(f"/accounts/{aid}/files/{f['id']}/comments")
        if cs:
            print(f"\n== {pre}{f['name']}")
            for c in cs:
                print(f"  [{c.get('timestamp')}] {c.get('text')}")
                coms.append({'arquivo': f['name'], 'quadro': c.get('timestamp'), 'texto': c.get('text') or '',
                             'autor': (c.get('owner') or {}).get('name') if isinstance(c.get('owner'), dict) else None})
    if batch:
        import subprocess, tempfile
        ck = _checklist()
        if not ck:
            sys.exit('notas_revisao.py do núcleo não encontrado')
        if not versao:
            P = ck.pastas_de(ck.ficha_de(batch))
            versao = ck.versao_de(batch, os.path.join(batch, P['export'], 'x.mp4'), P)
        j = os.path.join(tempfile.gettempdir(), 'comentarios_frameio.json')
        json.dump(coms, open(j, 'w', encoding='utf-8'), ensure_ascii=False)
        subprocess.run([sys.executable, '-X', 'utf8', os.path.join(os.path.dirname(ck.__file__), 'notas_revisao.py'), 'gerar',
                        batch, '--versao', str(versao), '--comentarios', j], check=False)
        os.remove(j)


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a: sys.exit(__doc__)
    if a[0] == 'login': login()
    elif a[0] == 'eu': cmd_eu()
    elif a[0] == 'ls': cmd_ls(a[1])
    elif a[0] == 'versao': cmd_versao(a[1], [x for x in a[2:] if x != '--teste'], '--teste' in a)
    elif a[0] == 'nova': cmd_nova(a[1], [x for x in a[2:] if x != '--teste'], '--teste' in a)
    elif a[0] == 'links': cmd_links(a[1])
    elif a[0] == 'comentarios':
        import re
        rv = a[a.index('--revisao') + 1] if '--revisao' in a else None
        vs = a[a.index('--versao') + 1] if '--versao' in a else None
        resto = [x for i, x in enumerate(a[1:], 1) if x not in ('--revisao', '--versao') and a[i - 1] not in ('--revisao', '--versao')]
        cmd_comentarios(resto[0], resto[1] if len(resto) > 1 else '', rv, vs)
    else: sys.exit(__doc__)
