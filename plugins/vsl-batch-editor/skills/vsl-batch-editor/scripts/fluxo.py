#!/usr/bin/env python3
"""Fluxo do núcleo (@CLIENTES/_FLUXO): um fluxo.py para todos os clientes de edição de vídeo (09/11/2026).

O que muda de um cliente para outro vem da ficha dele (../clientes/<cliente>.json): nomes das pastas ("pastas"),
motor ("plano" ou "pastas") e checagens. O cliente vem de `--cliente ev|ts` (os atalhos já passam) ou da pasta do
job/batch (o caminho contém a `pasta` da ficha, ex. "@EMPIRE VISION"). Sem cliente identificável, o script recusa.

Dois motores:
  plano   (Empire Vision) tudo parte de <auto>/plano.json. Cada arquivo esperado tem dependências; um arquivo falta
          (não existe) ou está desatualizado (alguma dependência é mais nova). O `status` mostra isso por módulo e o
          `fazer` roda só as etapas LOCAIS que estão pendentes, em ordem (cortes -> prévias -> legendas -> ADs -> XML).
          Etapas que gastam crédito (falas, quadros, b-roll) nunca rodam aqui: o status só lista o que falta.
  pastas  (Trendscale e qualquer batch/job sem plano.json) o `status` mostra, por pasta do mapa, o que existe (config,
          roteiro, refs, brutos, áudio, exports) e quais exports estão desatualizados; o `fazer` roda <auto>/montar.py
          do job quando falta export ou há export desatualizado (`--teste` só mostra o que rodaria).

Subcomandos:
  status <batch>                         o que falta / está desatualizado, e o próximo passo
  fazer  <batch> [--ate cortes|previas|legendas|ads] [--so AD1_neurobella] [--forcar] [--aceitar-sem-voz] [--teste]
  montar <batch> <produto> <hook>        renderiza um AD final (09_export)        (motor plano)
  xml    <batch>                         timeline Premiere, só se o Fefo pedir (fora do fazer desde 10/11/2026)
  identificar <videos...> --quadros <pasta>   casa cada vídeo baixado com o quadro inicial (1º frame)   (motor plano)
  novo-plano <batch>                     gera um plano.json vazio a partir do roteiro.txt (para o Claude preencher)   (motor plano)
  checar <job_ou_batch> [videos...] [--so freeze,lascas,ritmo,quadros,qc] [--json]
                                         checagens da ficha em cada export (sem vídeos: os exports da pasta de export, sem _old)
  perfil                                 perfil de quem usa (contas, aprovador); sem perfil → módulo configurar
  instalar <raiz>                        (fluxo.py da pasta da skill) monta/atualiza <raiz>/_FLUXO_VSL e _BATCH_MODELO
  empacotar                              (só no _FLUXO_VSL do Fefo) gera o zip da skill; zips antigos vão para old/
  publicar "<mensagem>"                  (só no _FLUXO_VSL do Fefo) manda a skill para o GitHub (plugin com auto-update)
  renomear <batch>                       exports com o nome antigo (BATCH<n>_AD<k>_<p>) → nome do card, sem renderizar

O código está dividido por assunto em fluxo_partes/ (para a sessão ler só o trecho que vai mexer):
  skill.py     perfil, empacotar, publicar, instalar
  plano.py     plano.json e caminhos de arquivos
  status.py    grafo de dependências, status, fazer, bordas e ganho
  acoes.py     ações locais (o que o fazer executa)
  legenda.py   transcrição, alinhamento e SRT
  broll.py     posição do b-roll e segmentos
  montar.py    montagem final do AD
  xml.py       timeline do Premiere, identificar e novo-plano
  pastas.py    motor "pastas" (status e fazer) e o comando checar
Todas rodam no mesmo espaço de nomes, na ordem acima, como se fossem um arquivo só. Os nomes das pastas viram globais
da ficha: AUTO, EXPORT, CFG, ROTEIRO, REFS, AUDIO, ELEMENTOS, PROJETO, BRUTOS.

Os atalhos dos clientes (ex. @EMPIRE VISION/2026/_FLUXO_VSL/scripts/fluxo.py) definem CLIENTE_ID, FLUXO_CLIENTE (a pasta
do fluxo do cliente) e NUCLEO_DIR, e executam este arquivo no próprio espaço de nomes: `import fluxo` continua dando
as funções (F.carregar, F.L...). Cópia de antes: @CLIENTES/_FLUXO/old/antes_fluxo_2026-11-09/."""
import argparse, difflib, glob, json, os, re, shutil, subprocess, sys, tempfile

# ---------------------------------------------------------------- onde estamos
AQUI = globals().get("NUCLEO_DIR") or os.path.dirname(os.path.abspath(__file__))     # pasta scripts/ deste fluxo.py
NUCLEO_DIR_PAI = os.path.dirname(AQUI)                                                  # _FLUXO (ou a pasta da skill)
_AQUI_ARQ = os.path.dirname(os.path.abspath(globals().get("__file__") or AQUI))        # onde está o arquivo que roda (atalho ou este)
RAIZ_CLIENTES = os.path.dirname(NUCLEO_DIR_PAI)                                         # @CLIENTES (quando no núcleo)
for _d in (AQUI, _AQUI_ARQ):
    if _d not in sys.path: sys.path.insert(0, _d)
os.environ["PATH"] = os.path.expanduser("~/bin") + os.pathsep + os.environ.get("PATH", "")
FF = shutil.which("ffmpeg") or "ffmpeg"
# ffmpeg 7+ lê o filtro de arquivo com "-/filter_complex"; o 9 do PC recusa "-filter_complex_script" (BATCH#3831 V5, 11/11/2026)
try: _ffv = int(re.search(r"version n?(\d+)\.", subprocess.run([FF, "-version"], capture_output=True, text=True).stdout)[1])
except Exception: _ffv = 0
FCS = "-/filter_complex" if _ffv >= 7 else "-filter_complex_script"
def fpath(p):
    """Caminho de arquivo dentro de um filtro (subtitles=...): no Windows, '\\' e o ':' do drive quebram o parser; no Mac fica igual."""
    return "'" + p.replace("\\", "/").replace(":", "\\:") + "'" if os.name == "nt" else p


# ---------------------------------------------------------------- ficha do cliente
def _fichas():
    """Fichas de cliente: <núcleo>/clientes/*.json (ou scripts/clientes/ quando o script vai dentro de uma skill)."""
    for pasta in (os.path.join(AQUI, "..", "clientes"), os.path.join(AQUI, "clientes")):
        if not os.path.isdir(pasta): continue
        fichas = {}
        for nome in sorted(os.listdir(pasta)):
            if nome.endswith(".json"):
                f = json.load(open(os.path.join(pasta, nome), encoding="utf-8"))
                if f.get("id"): f["_arquivo"] = nome[:-5]; fichas[f["id"]] = f
        if fichas: return fichas
    sys.exit(f"Sem ficha de cliente em {os.path.normpath(os.path.join(AQUI, '..', 'clientes'))}")

FICHAS = _fichas()

def _tira_opcao(nome):
    """Tira `nome VALOR` do sys.argv e devolve VALOR."""
    if nome not in sys.argv: return None
    i = sys.argv.index(nome)
    if i + 1 >= len(sys.argv): sys.exit(f"{nome} pede um valor")
    valor = sys.argv[i + 1]; del sys.argv[i:i + 2]
    return valor

def _acha_cliente(nome):
    n = str(nome).strip().lower()
    for f in FICHAS.values():
        if n in (f["id"].lower(), f["_arquivo"].lower(), f.get("nome", "").lower()): return f["id"]
    sys.exit(f"Cliente {nome!r} sem ficha. Clientes: {', '.join(FICHAS)}")

def _cliente_do_caminho(caminho):
    """id do cliente dono da pasta onde o caminho está; None fora das pastas de cliente."""
    partes = os.path.abspath(caminho).split(os.sep)
    for f in FICHAS.values():
        if f.get("pasta") and f["pasta"] in partes: return f["id"]
    return None

def _nome_cliente(cid): return FICHAS[cid].get("nome", cid)

def _caminhos_do_pedido():
    """Argumentos da linha de comando que existem como arquivo ou pasta (para deduzir e conferir o cliente)."""
    return [x for x in sys.argv[1:] if not x.startswith("-") and os.path.exists(x)]

def _recusa(msg):
    print(msg, file=sys.stderr); sys.exit(2)      # recusa de cliente: código 2 (erro de uso)

def _define_cliente():
    """Cliente deste processo: preset do atalho, --cliente/FLUXO_CLIENTE_ID, ou a pasta dos argumentos. Recusa cruzar clientes."""
    rodando = globals().get("__name__") == "__main__"        # como módulo (import fluxo) o argv não é nosso
    preset = globals().get("CLIENTE_ID")
    pedido = _tira_opcao("--cliente") if rodando else None
    pedido = pedido or os.environ.get("FLUXO_CLIENTE_ID")
    ped = _acha_cliente(pedido) if pedido else None
    pre = _acha_cliente(preset) if preset else None
    if ped and pre and ped != pre:
        _recusa(f"RECUSADO: este atalho é só de {_nome_cliente(pre)}; o pedido é de {_nome_cliente(ped)}.")
    donos = {}
    if rodando:
        for c in _caminhos_do_pedido():
            d = _cliente_do_caminho(c)
            if d: donos.setdefault(d, c)
    if len(donos) > 1:
        _recusa("RECUSADO: o pedido mistura pastas de clientes diferentes: " + "; ".join(f"{_nome_cliente(d)} → {c}" for d, c in donos.items()))
    da_pasta = next(iter(donos), None)
    dito = pre or ped
    if dito and da_pasta and dito != da_pasta:
        _recusa(f"RECUSADO: o cliente pedido é {_nome_cliente(dito)}, mas a pasta é de {_nome_cliente(da_pasta)} ({donos[da_pasta]}).")
    cid = dito or da_pasta or _cliente_do_caminho(os.getcwd()) or (next(iter(FICHAS)) if len(FICHAS) == 1 else None)
    if not cid:
        _recusa(f"Diga o cliente: --cliente {'|'.join(FICHAS)} (o caminho não está em pasta de cliente).")
    return cid

CLIENTE = _define_cliente()
FICHA = FICHAS[CLIENTE]
MOTOR = FICHA.get("motor", "plano")
CHECAGENS = FICHA.get("checagens", [])
_P = FICHA.get("pastas", {})        # mapa de nomes de pasta; o padrão é o formato da batch da Empire Vision
CFG = _P.get("config", "batch.json"); AUTO = _P.get("auto", "08_auto"); EXPORT = _P.get("export", "09_export")
ROTEIRO = _P.get("roteiro", "00_roteiro"); REFS = _P.get("refs", "01_refs"); AUDIO = _P.get("audio", "02_audio")
ELEMENTOS = _P.get("elementos", "06_elementos"); PROJETO = _P.get("projeto", "07_premiere")
BRUTOS = _P.get("brutos", ["03_avatar", "04_broll_hold", "05_broll_hooks"])
if FICHA.get("scripts_cliente"):                                    # módulos auxiliares do cliente (vsl, umtake, cartao...)
    _sc = os.path.join(RAIZ_CLIENTES, FICHA["scripts_cliente"])
    if os.path.isdir(_sc) and _sc not in sys.path: sys.path.append(_sc)

_PARTES_DIR = os.path.join(AQUI, "fluxo_partes")
for _parte in ("skill.py", "plano.py", "status.py", "acoes.py", "legenda.py", "broll.py", "montar.py", "xml.py", "pastas.py"):
    _arq = os.path.join(_PARTES_DIR, _parte)
    exec(compile(open(_arq, encoding="utf-8").read(), _arq, "exec"), globals())
del _parte, _arq


# ---------------------------------------------------------------- escolha do motor
def motor_de(B):
    """'plano' quando a ficha é do motor plano e a batch tem <auto>/plano.json; senão 'pastas'."""
    return "plano" if MOTOR == "plano" and os.path.exists(f"{B}/{AUTO}/plano.json") else "pastas"

def _so_plano(B, cmd):
    if motor_de(B.rstrip("/")) != "plano":
        sys.exit(f"`{cmd}` é do motor plano (precisa de {AUTO}/plano.json); {_nome_cliente(CLIENTE)} usa o motor {MOTOR}"
                 + ("" if MOTOR == "pastas" else f" e esta pasta não tem {AUTO}/plano.json") + ".")

def _status(a):
    B = a.batch.rstrip("/")
    (cmd_status if motor_de(B) == "plano" else cmd_status_pastas)(a)

def _fazer(a):
    B = a.batch.rstrip("/")
    if motor_de(B) == "plano":
        if a.teste: print("--teste no motor plano: só o status (o `fazer` do plano não tem simulação)."); cmd_status(a); return
        cmd_fazer(a)
    else: cmd_fazer_pastas(a)

def _novo_plano(a):
    if MOTOR != "plano": sys.exit(f"`novo-plano` é do motor plano; {_nome_cliente(CLIENTE)} usa o motor {MOTOR}.")
    cmd_novo_plano(a)

def _identificar(a):
    if MOTOR != "plano": sys.exit(f"`identificar` é do motor plano; {_nome_cliente(CLIENTE)} usa o motor {MOTOR}.")
    cmd_identificar(a)


def _argumentos():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("status"); p.add_argument("batch"); p.set_defaults(fn=_status)
    p = sp.add_parser("fazer"); p.add_argument("batch"); p.add_argument("--ate", choices=ORDEM[2:]); p.add_argument("--so"); p.add_argument("--forcar", action="store_true"); p.add_argument("--aceitar-sem-voz", action="store_true"); p.add_argument("--teste", action="store_true"); p.set_defaults(fn=_fazer)
    p = sp.add_parser("montar"); p.add_argument("batch"); p.add_argument("produto"); p.add_argument("hook"); p.set_defaults(fn=lambda a: (_so_plano(a.batch, "montar"), montar(a.batch.rstrip("/"), a.produto, a.hook)))
    p = sp.add_parser("xml"); p.add_argument("batch"); p.set_defaults(fn=lambda a: (_so_plano(a.batch, "xml"), gerar_xml(a.batch.rstrip("/"))))
    p = sp.add_parser("identificar"); p.add_argument("videos", nargs="+"); p.add_argument("--quadros", required=True); p.set_defaults(fn=_identificar)
    p = sp.add_parser("novo-plano"); p.add_argument("batch"); p.set_defaults(fn=_novo_plano)
    p = sp.add_parser("checar"); p.add_argument("batch"); p.add_argument("videos", nargs="*"); p.add_argument("--so"); p.add_argument("--json", action="store_true"); p.set_defaults(fn=cmd_checar)
    p = sp.add_parser("perfil"); p.set_defaults(fn=cmd_perfil)
    p = sp.add_parser("instalar"); p.add_argument("raiz"); p.set_defaults(fn=cmd_instalar)
    p = sp.add_parser("empacotar"); p.set_defaults(fn=cmd_empacotar)
    p = sp.add_parser("publicar"); p.add_argument("mensagem"); p.add_argument("--teste", action="store_true"); p.set_defaults(fn=cmd_publicar)
    p = sp.add_parser("renomear"); p.add_argument("batch"); p.set_defaults(fn=lambda a: (_so_plano(a.batch, "renomear"), cmd_renomear(a)))
    return ap


if __name__ == "__main__":
    ap = _argumentos(); a, extra = ap.parse_known_args()
    if extra:                                  # `checar JOB --so freeze video.mp4`: vídeo depois de uma opção
        if a.cmd != "checar" or any(x.startswith("-") for x in extra): ap.error("argumentos não reconhecidos: " + " ".join(extra))
        a.videos += extra
    a.fn(a)
