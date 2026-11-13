#!/usr/bin/env python3
"""Checklist da Louise (Frente 4, 13/11/2026): os 6 itens que a Empire Vision exige antes de TODA entrega, nova e
revisão. Dispensa do Fefo não vale para estes itens (decisão dele, 13/11/2026). Liga por cliente na ficha
(clientes/<cliente>.json -> "checklist": {"ativo": true, ...}); limites e área segura também vêm da ficha.

  1 texto_45      todo texto dentro da área segura (EV: 4:5 = y 285–1635 em 1920) em todo quadro, e o centro da
                  legenda até 0,65 da altura (margem do Daniel). OCR a 2 fps + camadas gravadas pelo montar.
  2 texto_estilo  legenda na lista fechada (pílula ou branca com contorno): sem 3D, sombra deslocada, degradê, cor.
  3 vo            Whisper no AD inteiro contra o roteiro: palavra trocada, faltando, repetida, fim cortado, marca,
                  pausa acima do limite (padrão 0,45 s).
  4 musica        trilha abaixo da voz nos trechos com fala (ok >= 15 dB, falha < 12 dB) e AD a -20 LUFS.
                  Mede pelos stems do montar (<auto>/mix_AD<n>_<p>.json); sem eles, estima pelo mix (pausas x fala).
  5 imagem        por plano: imagem parada (still), tremida ou borrada.
  6 notas         revisão: toda nota da versão anterior marcada [x] com prova (quadro da versão nova) em
                  <roteiro>/revisao_V<k>.md (10_revisao.md, passo 1b). V1 não tem nota: passa.

Uso (no Windows: py -X utf8; processo pesado pela fila):
  checklist.py <batch> [videos...] [--versao K] [--so 1,3] [--saida PASTA] [--debug]
      Roda os itens nos vídeos (sem vídeos: os exports atuais, fora do _old) e grava <auto>/checklist_V<K>.json.
      A versão sai da pasta (_old/V4 = V4; export atual = maior V do _old + 1) ou de --versao.
      --saida: grava o json noutra pasta (teste em batch já entregue: nada é escrito na batch).
      Código: 0 = tudo verde, 1 = algum item vermelho, 2 = erro de uso ou de execução.
  checklist.py entrega <batch> [videos...]
      Trava da entrega: cada vídeo precisa de checklist verde com a mesma impressão digital (sha1) e não pode ser
      prévia (.PREVIA.txt). 0 = pode entregar; 1 = não pode (diz o porquê).
  checklist.py estado <video>...
      JSON com o estado do checklist de cada arquivo (usado pela sala e pelo frameio.py).
"""
import argparse, datetime, difflib, glob, hashlib, json, os, re, shutil, subprocess, sys, tempfile, wave

AQUI = os.path.dirname(os.path.abspath(__file__))          # scripts/checagens
NUCLEO = os.path.dirname(AQUI)                              # scripts
if AQUI not in sys.path: sys.path.insert(0, AQUI)
os.environ["PATH"] = os.path.expanduser("~/bin") + os.pathsep + os.environ.get("PATH", "")
FF = shutil.which("ffmpeg") or "ffmpeg"
FP = shutil.which("ffprobe") or "ffprobe"

ITENS = {1: "texto_45", 2: "texto_estilo", 3: "vo", 4: "musica", 5: "imagem", 6: "notas"}
TITULO = {1: "texto na área segura", 2: "estilo da legenda", 3: "VO limpa", 4: "música abaixo da VO",
          5: "imagem firme e nítida", 6: "notas da revisão"}

# Padrão (sobrescrito pelo bloco "checklist" da ficha do cliente). Calibrado nas versões que voltaram com nota (13/11).
PADRAO = {
    "ativo": False,
    "itens": [1, 2, 3, 4, 5, 6],
    "area_segura": {"nome": "4:5", "y0": 285 / 1920, "y1": 1635 / 1920, "x0": 0.0, "x1": 1.0, "tolerancia": 0.006},
    "legenda_centro_max": 0.65,
    "estilos_legenda": ["pilula", "branca_contorno"],
    "ocr": {"fps": 2, "altura_min": 0.012, "persistencia_s": 1.0},
    "vo": {"pausa_max_s": 0.45, "pausa_tolerancia_mix_s": 0.10, "pausa_emenda_max_s": 0.8, "pausa_abaixo_db": 8.0, "prob_min": 0.6, "idioma": "en"},
    "musica": {"margem_ok_db": 15, "margem_min_db": 12, "lufs": -20.0, "lufs_tol": 1.0},
    "imagem": {"fps": 15, "parado_atividade_max": 3.0, "parado_resto_max": 9.5, "parado_clipe_max": 10.0, "parado_dur_min": 1.0, "tremor_max": 6.0, "nitidez_min": 6.0,
               "plano_min_s": 0.6},
}


# ---------------------------------------------------------------- ficha, batch, versão
def _fichas():
    for pasta in (os.path.join(NUCLEO, "..", "clientes"), os.path.join(NUCLEO, "clientes"), os.path.join(AQUI, "clientes")):   # núcleo ou skill
        if os.path.isdir(pasta):
            out = {}
            for n in sorted(os.listdir(pasta)):
                if n.endswith(".json"):
                    f = json.load(open(os.path.join(pasta, n), encoding="utf-8"))
                    if f.get("id"): out[f["id"]] = f
            if out: return out
    return {}


def _mescla(a, b):
    out = dict(a)
    for k, v in (b or {}).items():
        out[k] = _mescla(a[k], v) if isinstance(v, dict) and isinstance(a.get(k), dict) else v
    return out


def ficha_de(caminho):
    """Ficha do cliente dono da pasta; fora das pastas de cliente (cópia de teste no TEMP), a de FLUXO_CLIENTE_ID."""
    partes = os.path.abspath(caminho).split(os.sep)
    fs = _fichas()
    for f in fs.values():
        if f.get("pasta") and f["pasta"] in partes: return f
    return fs.get(os.environ.get("FLUXO_CLIENTE_ID", ""))


def config_de(ficha):
    c = _mescla(PADRAO, (ficha or {}).get("checklist", {}))
    if os.environ.get("FLUXO_CHECKLIST_FORCAR") == "1": c["ativo"] = True      # só teste (cópia no TEMP)
    return c


def pastas_de(ficha):
    p = (ficha or {}).get("pastas", {})
    return {"auto": p.get("auto", "08_auto"), "export": p.get("export", "09_export"), "roteiro": p.get("roteiro", "00_roteiro"),
            "config": p.get("config", "batch.json")}


def batch_de(video, ficha):
    """Pasta da batch/job que contém o vídeo: a primeira acima dele com a pasta auto ou o arquivo de config."""
    P = pastas_de(ficha); d = os.path.dirname(os.path.abspath(video))
    while d and os.path.dirname(d) != d:
        if os.path.isdir(os.path.join(d, P["auto"])) or os.path.exists(os.path.join(d, P["config"])): return d
        d = os.path.dirname(d)
    return None


def versao_de(B, video, P):
    """V<k> da pasta: _old/V4/... = V4 (_old/V5_r1 = V5_r1); <export>/V2/... = V2 (Trendscale); export solto (Empire
    Vision) = maior V inteiro do _old + 1."""
    ab = os.path.abspath(video)
    m = re.search(r"[\\/]_old[\\/](V\d+[^\\/]*)[\\/]", ab)
    if m: return m[1]
    m = re.search(re.escape(os.sep + P["export"] + os.sep) + r"(V\d+[^\\/]*)[\\/]", ab)
    if m: return m[1]
    m = re.search(r"[_ ]V(\d+)(?:[ ._-]|$)", os.path.splitext(os.path.basename(ab))[0] + " ")      # TS: M8WK4B18_Hook1_9x16_V8.mp4
    if m: return f"V{m[1]}"
    nums =[int(x[1]) for x in (re.fullmatch(r"V(\d+)", os.path.basename(d)) for d in glob.glob(os.path.join(glob.escape(B), P["export"], "_old", "V*"))) if x]
    return f"V{max(nums, default=0) + 1}"


def exports_atuais(B, P):
    """Exports da versão atual: fora do _old; com pastas V<k> no export (Trendscale), só a de maior número."""
    out = []
    for raiz, dirs, arqs in os.walk(os.path.join(B, P["export"])):
        dirs[:] = [d for d in dirs if not d.startswith(("_", "."))]          # _old, _previas, _antigos
        out += [os.path.join(raiz, a) for a in arqs if a.lower().endswith((".mp4", ".mov"))]
    def vnum(p):
        m = re.search(re.escape(os.sep + P["export"] + os.sep) + r"V(\d+)", os.path.abspath(p)); return int(m[1]) if m else None
    vs = [vnum(p) for p in out if vnum(p) is not None]
    if vs: out = [p for p in out if vnum(p) in (None, max(vs))]
    def vnome(p):        # TS: versão no nome (M2WK3B2_Hook1_9x16_V5.mp4 ao lado de "Hook 1 V3 celular.mp4")
        m = re.search(r"[_ ]V(\d+)(?:[ ._-]|$)", os.path.splitext(os.path.basename(p))[0] + " "); return int(m[1]) if m else None
    vn = [vnome(p) for p in out if vnome(p) is not None]
    if vn: out = [p for p in out if vnome(p) in (None, max(vn))]
    return sorted(out)


def area_do_video(A, w, h):
    """Área segura no quadro deste vídeo: "4:5" ou "1:1" central (do nome), ou y0/y1 da ficha (frações do 9:16)."""
    m = re.fullmatch(r"(\d+):(\d+)", str(A.get("nome", "")))
    if m and w and h:
        alt = w * int(m[2]) / int(m[1])
        y0 = max(0.0, (h - alt) / 2 / h)
        return dict(A, y0=y0, y1=1 - y0)
    return A


def digital(path):
    """Mesma conta do reviewroom.py e do revisor.py (sha1, 16 primeiros hex)."""
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()[:16]


def mmss(t): return f"{int(t // 60)}:{t % 60:05.2f}"


# ---------------------------------------------------------------- mídia
def duracao(mp4):
    r = subprocess.run([FP, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", mp4], capture_output=True, text=True)
    try: return float(r.stdout.strip())
    except ValueError: return 0.0


def tamanho(mp4):
    r = subprocess.run([FP, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", mp4],
                       capture_output=True, text=True)
    try: w, h = r.stdout.strip().split(",")[:2]; return int(w), int(h)
    except ValueError: return 720, 1280


def quadros(mp4, pasta, fps):
    os.makedirs(pasta, exist_ok=True)
    subprocess.run([FF, "-nostdin", "-v", "error", "-y", "-i", mp4, "-an", "-vf", f"fps={fps}", "-q:v", "2",
                    os.path.join(pasta, "q_%05d.jpg")], check=True)
    arqs = sorted(glob.glob(os.path.join(pasta, "q_*.jpg")))
    return [((int(os.path.basename(a)[2:7]) - 1) / fps, a) for a in arqs]


def audio16k(mp4, destino):
    subprocess.run([FF, "-nostdin", "-v", "error", "-y", "-i", mp4, "-vn", "-ac", "1", "-ar", "16000", destino], check=True)
    import numpy as np
    with wave.open(destino) as w:
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768.0


def lufs(mp4):
    r = subprocess.run([FF, "-nostdin", "-hide_banner", "-nostats", "-i", mp4, "-vn", "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True, errors="replace")
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(m[-1]) if m else None


# ---------------------------------------------------------------- whisper
_MODELO = None
def _cuda_ok():
    if os.name != "nt": return False
    import ctypes
    for b in glob.glob(os.path.join(os.environ.get("APPDATA", ""), "Python", "Python3*", "site-packages", "nvidia", "*", "bin")):
        try: os.add_dll_directory(b)
        except OSError: pass
        os.environ["PATH"] = b + os.pathsep + os.environ["PATH"]
    try: ctypes.WinDLL("cublas64_12.dll"); ctypes.WinDLL("cudnn64_9.dll"); return True
    except OSError: return False


def transcrever(wav, idioma="en"):
    """Palavras [(texto, ini, fim, prob)] do AD inteiro (Whisper medium; GPU no PC Windows, CPU no Mac)."""
    global _MODELO
    from faster_whisper import WhisperModel
    if _MODELO is None:
        _MODELO = (WhisperModel("medium", device="cuda", compute_type="float16") if _cuda_ok()
                   else WhisperModel("medium", device="cpu", compute_type="int8", cpu_threads=8))
    segs, _ = _MODELO.transcribe(wav, word_timestamps=True, vad_filter=False, language=idioma,
                                 condition_on_previous_text=False, beam_size=5)
    out = []
    for s in segs:
        for w in (s.words or []):
            out.append((w.word.strip(), float(w.start), float(w.end), float(w.probability)))
    return out


# ---------------------------------------------------------------- texto: normalização e roteiro
_UN = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
_DZ = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
def _num(n):
    n = int(n)
    if n < 20: return _UN[n]
    if n < 100: return _DZ[n // 10] + ("" if n % 10 == 0 else " " + _UN[n % 10])
    if n < 1000: return _UN[n // 100] + " hundred" + ("" if n % 100 == 0 else " " + _num(n % 100))
    if n < 1000000: return _num(n // 1000) + " thousand" + ("" if n % 1000 == 0 else " " + _num(n % 1000))
    return str(n)


def palavras(txt):
    """Texto -> lista de palavras normalizadas (minúsculas, sem pontuação, números por extenso)."""
    t = str(txt).lower().replace("’", "'").replace("%", " percent ").replace("&", " and ")
    t = re.sub(r"(\d),(\d{3})", r"\1\2", t)
    t = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", t)
    t = re.sub(r"\d+", lambda m: " " + _num(m[0]) + " ", t)
    t = re.sub(r"\b([ap])\s*\.?\s*m\b\.?", r"\1m", t)          # a.m. / a m / am (Whisper escreve de três jeitos)
    t = re.sub(r"[-/]", " ", t)
    ws = [w for w in (re.sub(r"[^a-z0-9]", "", x) for x in t.split()) if w]
    return [ABREV.get(w, w) for w in ws]


# abreviação = palavra falada por extenso (M8WK3B14 H3, 13/11/2026: o áudio diz "milligrams", o Whisper escreve "mg")
ABREV = {"mg": "milligrams", "mcg": "micrograms", "ml": "milliliters", "kg": "kilograms", "lb": "pounds", "lbs": "pounds",
         "oz": "ounces", "dr": "doctor", "mr": "mister", "mrs": "missus", "vs": "versus", "hrs": "hours", "hr": "hour",
         "approx": "approximately", "ok": "okay", "tv": "television"}


ROTEIRO_HOOK = [0, None]   # nº de palavras e fim (s, pelos cortes do plano) do hook do último roteiro lido


def roteiro_md(B, P, video):
    """Trendscale: <roteiro>/roteiro.md com seções "## H<n>" (hooks) e "## B01".. (corpo igual em todos)."""
    arq = os.path.join(B, P["roteiro"], "roteiro.md")
    m = re.search(r"hook\s*_?(\d+)", os.path.basename(video), re.I)
    if not os.path.exists(arq) or not m: return None, None
    secoes, atual = [], None
    for ln in open(arq, encoding="utf-8"):
        h = re.match(r"##\s+(\S+)", ln)
        if h: atual = [h[1].strip(), []]; secoes.append(atual)
        elif atual and ln.strip() and not ln.startswith("#"): atual[1].append(ln.strip())
    hook = [" ".join(t) for n, t in secoes if re.fullmatch(rf"H0?{m[1]}", n, re.I)]
    corpo = [" ".join(t) for n, t in secoes if re.fullmatch(r"B\d+\w*", n, re.I)]
    if not hook: return None, None
    ROTEIRO_HOOK[0] = len(palavras(" ".join(hook)))
    marca = None
    try: marca = json.load(open(os.path.join(B, P["config"]), encoding="utf-8")).get("marca")
    except (OSError, ValueError): pass
    return " ".join(hook + corpo), marca


def roteiro_do_ad(B, P, video):
    """(texto esperado do AD, marca) a partir do plano.json: hook n + hold, com {MARCA}. Sem plano: roteiro.md
    (Trendscale). None quando não dá."""
    pj = os.path.join(B, P["auto"], "plano.json")
    if not os.path.exists(pj): return roteiro_md(B, P, video)
    try: plano = json.load(open(pj, encoding="utf-8"))
    except ValueError: return None, None
    nome = os.path.basename(video).lower(); m = re.search(r"ad\s*(\d+)", nome)
    if not m: return None, None
    n = int(m[1]); mn = plano.get("marca_nome", {})
    prod = next((p for p in plano.get("produtos", []) if p.lower() in nome or str(mn.get(p, p)).lower() in nome), None)
    prod = prod or (plano.get("produtos") or [None])[0]
    marca = mn.get(prod, (prod or "").capitalize())
    falas = plano.get("falas") or []
    def vale(f): return not f.get("marca") or f.get("marca") is True or f.get("marca") == prod   # true = varia por marca (3858 F09)
    def texto(f): return f.get(f"texto_{prod}") or f["texto"]
    hook = [texto(f) for f in falas if f.get("tipo") == "hook" and str(f.get("hook")) == str(n) and vale(f)]
    hold = [texto(f) for f in falas if f.get("tipo") != "hook" and vale(f)]
    if not hook: hook = [plano.get("hooks", {}).get(str(n), "")]
    if not hold: hold = plano.get("hold") if isinstance(plano.get("hold"), list) else [plano.get("hold") or ""]
    txt = " ".join(hook + hold).replace("{MARCA}", marca or "")
    ROTEIRO_HOOK[0] = len(palavras(" ".join(hook).replace("{MARCA}", marca or "")))
    ROTEIRO_HOOK[1] = None
    hf = next((f for f in falas if f.get("tipo") == "hook" and str(f.get("hook")) == str(n) and vale(f)), None)
    for nome_c in ([f"{hf['id']}_{prod}", hf["id"]] if hf else []):
        for ext in (".manual.json", ".json"):
            cj = os.path.join(B, P["auto"], "cortes", nome_c + ext)
            if ROTEIRO_HOOK[1] is None and os.path.exists(cj):
                try: ROTEIRO_HOOK[1] = round(sum(b - a for a, b in json.load(open(cj, encoding="utf-8"))), 2)
                except (ValueError, TypeError): pass
    return (txt if txt.strip() else None), marca


# ---------------------------------------------------------------- item 3: VO
def junta_marca(ouvidas, marca):
    """Whisper escreve a marca em pedaços ("Neuro Bella"): junta pares/trios parecidos com a marca."""
    if not marca: return ouvidas
    alvo = re.sub(r"[^a-z]", "", marca.lower()); out = []; i = 0
    while i < len(ouvidas):
        feito = False
        for k in (3, 2):
            if i + k <= len(ouvidas):
                junto = "".join(w[0] for w in ouvidas[i:i + k])
                if difflib.SequenceMatcher(None, junto, alvo).ratio() >= 0.8:
                    out.append((alvo, ouvidas[i][1], ouvidas[i + k - 1][2], min(w[3] for w in ouvidas[i:i + k]))); i += k; feito = True; break
        if not feito:
            w = ouvidas[i]
            out.append((alvo, w[1], w[2], w[3]) if difflib.SequenceMatcher(None, w[0], alvo).ratio() >= 0.8 else w); i += 1
    return out


FRACAS = set("a an the to of in on at for with by from and or but so if as that it is are was be just this its".split())

def item_vo(words, roteiro, marca, cfg, dur, pausas=None, exata=False):
    """words = [(texto, ini, fim, prob)] do Whisper. Devolve (ok, resumo, ocorrências)."""
    c = cfg["vo"]; occ = []
    ouv = []
    for w, a, b, p in words:
        for x in palavras(w): ouv.append((x, a, b, p))
    ouv = junta_marca(ouv, marca)
    if not ouv:
        return False, "Whisper não ouviu voz nenhuma", [{"t": 0, "msg": "sem voz", "nivel": "erro"}]
    # pausas dentro da VO: medidas no áudio (pausas_audio / stems do montar), não no Whisper (borda erra ±0,2 s)
    # a emenda hook→hold tem limite próprio (o montar abaixa a trilha ali; o lint cuida do mínimo de 0,30 s)
    nh = ROTEIRO_HOOK[0] if roteiro else 0
    emenda = ROTEIRO_HOOK[1] if roteiro and ROTEIRO_HOOK[1] else (ouv[nh - 1][2] if 0 < nh <= len(ouv) else None)
    tol = 0.0 if exata else c.get("pausa_tolerancia_mix_s", 0.10)       # medida no mix erra ~±0,1 s; nos stems, não
    for t, d in (pausas or []):
        na_emenda = emenda is not None and t - 0.3 <= emenda <= t + d + 0.3      # a pausa cobre o fim do hook
        lim = c.get("pausa_emenda_max_s", 0.8) if na_emenda else c["pausa_max_s"]
        if d > lim + tol:
            occ.append({"t": t, "msg": f"pausa de {d:.2f} s na VO" + (" (emenda hook→hold)" if na_emenda else "") + f" (limite {lim:.2f} s)", "nivel": "erro", "regra": "pausa"})
        elif d > lim:
            occ.append({"t": t, "msg": f"pausa de {d:.2f} s na VO, no limite ({lim:.2f} s; medida no mix)", "nivel": "aviso", "regra": "pausa"})
    # repetição colada (a mesma palavra duas vezes seguidas, que o roteiro não tem)
    esp = palavras(roteiro) if roteiro else []
    pares_rot = set(zip(esp, esp[1:]))
    for (w1, a1, b1, p1), (w2, a2, b2, p2) in zip(ouv, ouv[1:]):
        if w1 == w2 and w1 not in FRACAS and (w1, w2) not in pares_rot and min(p1, p2) >= c["prob_min"]:
            occ.append({"t": round(a1, 2), "msg": f"palavra repetida: \"{w1} {w2}\"", "nivel": "erro", "regra": "repetida"})
    resumo_rot = "sem roteiro no plano: conferi só pausa, repetição e fim"
    if esp:
        ouvidas = [w[0] for w in ouv]
        sm = difflib.SequenceMatcher(None, esp, ouvidas, autojunk=False)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == "equal": continue
            e, o = esp[i1:i2], ouv[j1:j2]
            t = o[0][1] if o else (ouv[j1 - 1][2] if j1 > 0 else 0.0)
            je, jo = "".join(e), "".join(w[0] for w in o)
            if e and o and difflib.SequenceMatcher(None, je, jo).ratio() >= 0.75:
                continue                                    # grafia do Whisper ("cocoa"/"coco", "type two"/"type to")
            pmin = min((w[3] for w in o), default=1.0)
            if op == "replace":
                forte = pmin >= c["prob_min"] and not all(x in FRACAS for x in e)
                occ.append({"t": round(t, 2), "msg": f"palavra trocada: roteiro \"{' '.join(e)}\", ouvido \"{' '.join(w[0] for w in o)}\"",
                            "nivel": "erro" if forte else "aviso", "regra": "trocada"})
            elif op == "delete":
                fortes = [x for x in e if x not in FRACAS]
                fim = i2 == len(esp)
                nivel = "erro" if (fim and fortes) or len(fortes) >= 2 or (marca and re.sub(r"[^a-z]", "", marca.lower()) in e) else "aviso"
                occ.append({"t": round(t, 2), "msg": ("fim cortado: falta " if fim else "falta no áudio: ") + f"\"{' '.join(e)}\"",
                            "nivel": nivel, "regra": "faltando"})
            elif op == "insert":
                fortes = [w for w in o if w[0] not in FRACAS and w[3] >= c["prob_min"]]
                longo = len(o) >= 6                      # frase inteira a mais: o plano é que não tem a fala (3858: F09/F11)
                occ.append({"t": round(t, 2), "msg": (f"trecho fora do roteiro do plano ({len(o)} palavras): confira se o plano tem a fala: \"{' '.join(w[0] for w in o)[:90]}\""
                                                      if longo else f"a mais no áudio: \"{' '.join(w[0] for w in o)}\""),
                            "nivel": "erro" if len(fortes) >= 2 and not longo else "aviso", "regra": "a_mais"})
        resumo_rot = f"{len(ouv)} palavras ouvidas contra {len(esp)} do roteiro"
    # fim cortado no áudio: última palavra colada no fim do arquivo
    if ouv and dur - ouv[-1][2] < 0.04:
        occ.append({"t": round(ouv[-1][1], 2), "msg": f"última palavra (\"{ouv[-1][0]}\") encosta no fim do arquivo: corte?", "nivel": "aviso", "regra": "fim"})
    erros = [o for o in occ if o["nivel"] == "erro"]
    return (not erros), (f"{resumo_rot}; " + (f"{len(erros)} problema(s)" if erros else "nada errado") +
                         (f", {len(occ) - len(erros)} aviso(s)" if len(occ) > len(erros) else "")), occ


# ---------------------------------------------------------------- item 4: música x voz
def _db(x):
    import numpy as np
    return 10 * np.log10(np.maximum(x, 1e-12))


def niveis(a16, words, sr=16000):
    """(tempos, energia dB por 20 ms, máscara de fala, máscara da VO, S = mediana da fala, piso = 10º percentil na VO)."""
    import numpy as np
    if a16 is None or not words: return None
    jan = int(0.02 * sr); n = len(a16) // jan
    if n < 25: return None
    e = _db((a16[:n * jan].reshape(n, jan) ** 2).mean(1)); tj = (np.arange(n) + 0.5) * 0.02
    fala = np.zeros(n, bool)
    for w, a, b, p in words: fala |= (tj >= a + 0.03) & (tj <= b - 0.03)
    vo = (tj >= words[0][1]) & (tj <= words[-1][2])
    if fala.sum() < 50: return None
    return tj, e, fala, vo, float(np.median(e[fala])), float(np.percentile(e[vo], 10))


def pausas_audio(nv, abaixo=8.0, minimo=0.25):
    """Pausas dentro da VO: trechos >= minimo s em que a energia fica abaixo da fala (S - abaixo dB). Com trilha, a
    pausa fica no nível da trilha (o item 4 garante >= 12 dB abaixo da voz). Devolve [(início, duração)]."""
    if not nv: return []
    tj, e, fala, vo, S, piso = nv
    baixo = (e <= S - abaixo) & vo
    out, k, n = [], 0, len(e)
    while k < n:
        if baixo[k]:
            j = k
            while j + 1 < n and (baixo[j + 1] or (j + 2 < n and baixo[j + 2])): j += 1
            d = (j - k + 1) * 0.02
            if d >= minimo: out.append((round(float(tj[k]) - 0.01, 2), round(d, 2)))
            k = j + 1
        else:
            k += 1
    return out


def item_musica(a16, words, cfg, mix=None, lu=None):
    import numpy as np
    c = cfg["musica"]; occ = []; partes = []
    if lu is not None:
        partes.append(f"{lu:.1f} LUFS")
        if abs(lu - c["lufs"]) > c["lufs_tol"]:
            occ.append({"t": 0, "msg": f"loudness {lu:.1f} LUFS (alvo {c['lufs']:.0f} ± {c['lufs_tol']:.0f})", "nivel": "erro", "regra": "lufs"})
    else:
        occ.append({"t": 0, "msg": "não deu para medir o loudness (ebur128)", "nivel": "erro", "regra": "lufs"})
    extra = {}
    if mix and mix.get("margem_db") is not None:     # stems do montar: medida exata
        margem = mix.get("margem_db"); fonte = "stems do montar"
        piores = mix.get("piores", [])
    else:
        nv = niveis(a16, words)
        if not nv:
            return False, "fala curta demais para medir", [{"t": 0, "msg": "não deu para medir voz x trilha", "nivel": "erro"}], extra
        tj, e, fala, vo, S, Mf = nv
        # trilha = piso da VO (entre sílabas a voz cai 15-25 dB e a trilha fica). As pausas do Whisper trazem cauda de
        # voz e sala e subestimavam a margem (calibração de 13/11: 4083, 3855, 4206).
        if Mf < -60: margem = 40.0
        else: margem = float(10 * np.log10(max(10 ** (S / 10) - 10 ** (Mf / 10), 1e-12)) - Mf)
        extra = {"S": round(S, 1), "M_piso": round(Mf, 1), "margem_piso": round(margem, 1)}
        fonte = "estimado pelo mix (fala x piso da VO)"; piores = []
        partes.append(f"voz {S:.1f} dB, trilha {Mf:.1f} dB")
    partes.insert(0, f"trilha {margem:.1f} dB abaixo da voz ({fonte})")
    if margem < c["margem_min_db"]:
        occ.append({"t": (piores[0]["t"] if piores else 0), "msg": f"trilha só {margem:.1f} dB abaixo da voz (mínimo {c['margem_min_db']}, alvo {c['margem_ok_db']})",
                    "nivel": "erro", "regra": "margem"})
    elif margem < c["margem_ok_db"]:
        occ.append({"t": 0, "msg": f"trilha {margem:.1f} dB abaixo da voz: passa, mas abaixo do alvo de {c['margem_ok_db']} dB", "nivel": "aviso", "regra": "margem"})
    erros = [o for o in occ if o["nivel"] == "erro"]
    return (not erros), "; ".join(partes), occ, extra


# ---------------------------------------------------------------- itens 1 e 2: texto (OCR)
def _palavras_ocr(t): return [w for w in palavras(t) if len(w) >= 2]


def e_legenda(linha, t, words, pilula=None):
    """A linha do OCR é legenda quando as palavras dela estão sendo faladas perto daquele instante. Palavra solta só
    conta se o desenho for de legenda (pílula): o rótulo do frasco também diz a palavra falada (4083: "BERBERINE")."""
    ws = _palavras_ocr(linha["t"])
    if not ws or not words: return False
    perto = set()
    for w, a, b, p in words:
        if a <= t + 2.5 and b >= t - 2.5: perto.update(palavras(w))
    achadas = sum(1 for w in ws if w in perto or any(difflib.SequenceMatcher(None, w, x).ratio() >= 0.85 for x in perto if abs(len(x) - len(w)) <= 2))
    if len(ws) >= 2: return achadas / len(ws) >= 0.5
    return len(ws[0]) >= 4 and achadas == 1 and bool(pilula and pilula())


def vocab_cena(B, P):
    """Palavras que a própria cena mostra (rótulo, frasco, objeto), tiradas do plano: texto delas na imagem não é camada."""
    try: pl = json.load(open(os.path.join(B, P["auto"], "plano.json"), encoding="utf-8"))
    except (OSError, ValueError): return set()
    v = set()
    for c in pl.get("cenas", []) or []:
        for k in ("nome", "busca", "mostra", "visual"):
            if isinstance(c.get(k), str): v.update(palavras(c[k]))
    for m in (pl.get("marca_nome") or {}).values(): v.update(palavras(m))
    v.update(palavras(" ".join((pl.get("frascos") or {}).keys())))
    return {w for w in v if len(w) >= 4}


def _agrupa(ocorr, folga):
    """Junta ocorrências seguidas do mesmo tipo e texto parecido: uma linha por trecho (início, fim)."""
    out = []
    for o in sorted(ocorr, key=lambda x: x["t"]):
        u = out[-1] if out else None
        if u and u["chave"] == o["chave"] and o["t"] - u["t_fim"] <= folga:
            u["t_fim"] = o["t"]; u["n"] += 1
        else:
            out.append(dict(o, t_fim=o["t"], n=1))
    return out


_CLASSES = {}
def _classe(img, q, l):
    """Classe do desenho da linha (cache). Devolve None quando o vídeo é de pílula e a linha não é: aí é texto da cena."""
    k = (q, tuple(l["b"]))
    if k not in _CLASSES: _CLASSES[k] = estilo_crop(img(q), l["b"])[0]
    c = _CLASSES[k]
    if _CLASSES.get("_pilula_dominante") and c != "pilula": return None
    return c


def item_texto(qs, vis, words, cfg, camadas=None, tam=(720, 1280), img=None, vocab=frozenset()):
    """Item 1. qs = [(t, quadro)], vis = OCR de cada quadro, img(q) = quadro em RGB. Devolve (ok, resumo, ocorrências, legendas)."""
    import numpy as np
    A = area_do_video(cfg["area_segura"], *tam); tol = A.get("tolerancia", 0.006); hmin = cfg["ocr"]["altura_min"]
    vertical = tam[1] / max(tam[0], 1) > 1.6          # margem do centro da legenda só vale no 9:16
    passo = 1.0 / cfg["ocr"]["fps"]; occ = []; legendas = []; centros = []
    _CLASSES.clear()
    if img is not None:
        amostra = [(t, q, l) for t, q in qs[::4] for l in vis.get(q, {}).get("textos", []) if len(_palavras_ocr(l["t"])) >= 2 and e_legenda(l, t, words)][:60]
        cls = [estilo_crop(img(q), l["b"])[0] for t, q, l in amostra]
        _CLASSES["_pilula_dominante"] = len(cls) >= 6 and cls.count("pilula") / len(cls) >= 0.6
    for t, q in qs:
        linhas = [l for l in vis.get(q, {}).get("textos", []) if len(re.sub(r"[^A-Za-z0-9]", "", l["t"])) >= 2]
        cl = [c for c in (camadas or {}).get("camadas", []) if c.get("tipo") == "legenda" and c["t0"] - 0.1 <= t <= c["t1"] + 0.1]
        if (camadas or {}).get("camadas"):        # o montar disse onde desenhou a legenda: só é legenda o que cai nela
            leg = [l for l in linhas if any(c["y0"] - 0.01 <= l["b"][1] + l["b"][3] / 2 <= c["y1"] + 0.01 for c in cl)]
        else:                                     # palavra solta: pílula, centralizada e fora do vocabulário da cena (rótulo)
            leg = [l for l in linhas if e_legenda(l, t, words, (lambda l=l, q=q: img is not None and abs(l["b"][0] + l["b"][2] / 2 - 0.5) <= 0.06
                                                                and not all(w in vocab for w in _palavras_ocr(l["t"]))
                                                                and estilo_crop(img(q), l["b"])[0] == "pilula"))]
        if img is not None and leg and not (camadas or {}).get("camadas"):
            leg = [l for l in leg if _classe(img, q, l) is not None]
        for l in leg: legendas.append((t, l, q))
        pil_h = 57 / 1080 * tam[0] / tam[1]                # altura da pílula do PSD (57 px em 1080 de largura)
        for l in linhas:
            x, y, w, h = l["b"]
            if h < hmin and l not in leg: continue
            if l in leg and img is not None and _CLASSES.get((q, tuple(l["b"]))) == "pilula" or (l in leg and _CLASSES.get("_pilula_dominante")):
                c = y + h / 2; y, h = min(y, c - pil_h / 2), max(y + h, c + pil_h / 2) - min(y, c - pil_h / 2)   # mede a pílula, não só o texto
            fora = y < A["y0"] - tol or y + h > A["y1"] + tol or x < A["x0"] - tol or x + w > A["x1"] + tol
            if fora:
                tipo = "legenda" if l in leg else "texto"
                if tipo == "texto" and vocab and all(w in vocab for w in _palavras_ocr(l["t"])): continue   # rótulo/objeto da cena
                occ.append({"t": round(t, 2), "chave": f"fora:{tipo}:{round(y, 1)}", "tipo": tipo, "b": l["b"], "q": q,
                            "msg": f"{tipo} fora do {A['nome']} (y {y:.3f}–{y + h:.3f}; área {A['y0']:.3f}–{A['y1']:.3f}): \"{l['t'][:40]}\""})
        if leg:          # centro do bloco da legenda (linhas empilhadas no mesmo quadro)
            leg = sorted(leg, key=lambda l: l["b"][1]); blocos = [[leg[0]]]
            for l in leg[1:]:
                u = blocos[-1][-1]
                if l["b"][1] - (u["b"][1] + u["b"][3]) <= 1.3 * max(u["b"][3], l["b"][3]): blocos[-1].append(l)
                else: blocos.append([l])
            for bl in blocos:
                top = min(l["b"][1] for l in bl); base = max(l["b"][1] + l["b"][3] for l in bl); cy = (top + base) / 2
                centros.append(cy)
                if vertical and cy > cfg["legenda_centro_max"] + 0.01:
                    occ.append({"t": round(t, 2), "chave": "baixa", "tipo": "legenda",
                                "msg": f"legenda baixa: centro em y {cy:.2f} (máximo {cfg['legenda_centro_max']:.2f}): \"{' / '.join(l['t'][:30] for l in bl)}\""})
    agrupado = _agrupa(occ, passo * 1.6)
    final = []
    for o in agrupado:
        dur = o["t_fim"] - o["t"] + passo
        if o["tipo"] == "texto":
            if dur < cfg["ocr"]["persistencia_s"]: continue            # letra solta do b-roll some
            if img is not None and o.get("b"):                         # texto que muda com a imagem é da cena, não camada
                q1 = next((q for t, q in qs if abs(t - o["t_fim"]) < 1e-6), None)
                try:
                    H, W = img(o["q"]).shape[:2]; x, y, w, h = o["b"]
                    ys, xs = slice(int(y * H), int((y + h) * H) + 1), slice(int(x * W), int((x + w) * W) + 1)
                    a0 = img(o["q"]).astype(np.float32)[ys, xs].mean(-1); a1 = img(q1).astype(np.float32)[ys, xs].mean(-1)
                    if a0.size and float(np.abs(a0 - a1).mean()) > 12: continue
                except Exception: pass
        final.append({"t": o["t"], "t_fim": o["t_fim"], "msg": o["msg"] + (f" ({mmss(o['t'])}–{mmss(o['t_fim'])})" if o["t_fim"] > o["t"] else ""), "nivel": "erro",
                      "regra": "baixa" if o["chave"] == "baixa" else "fora"})
    for cm in (camadas or {}).get("camadas", []):     # camadas desenhadas pelo montar (posição exata, mesmo arquivo)
        y0, y1 = cm["y0"], cm["y1"]
        if y0 < A["y0"] - tol or y1 > A["y1"] + tol:
            final.append({"t": cm.get("t0", 0), "msg": f"{cm['tipo']} do montar fora do {A['nome']} (y {y0:.3f}–{y1:.3f})", "nivel": "erro", "regra": "fora"})
        if vertical and cm["tipo"] == "legenda" and (y0 + y1) / 2 > cfg["legenda_centro_max"] + 0.01:
            final.append({"t": cm.get("t0", 0), "msg": f"legenda do montar com centro em y {(y0 + y1) / 2:.2f} (máximo {cfg['legenda_centro_max']:.2f})", "nivel": "erro", "regra": "baixa"})
    final.sort(key=lambda o: o["t"])
    import statistics
    res = (f"{len(legendas)} linha(s) de legenda lidas" + (f", centro mediano y {statistics.median(centros):.2f}" if centros else "") +
           ("; " + f"{len(final)} trecho(s) com problema" if final else "; tudo dentro"))
    if not legendas and not any(vis.get(q, {}).get("textos") for _, q in qs):
        res = "nenhum texto lido no vídeo (OCR vazio)"
    return (not final), res, final, legendas


def estilo_crop(img, b):
    """Classifica a legenda numa caixa do OCR: pilula | contorno | sombra | cor | indefinido. Devolve (classe, medidas)."""
    import numpy as np
    from scipy import ndimage
    H, W = img.shape[:2]; x, y, w, h = b
    hp = max(h * H, 6)
    x0, x1 = int(max(0, x * W - 0.4 * hp)), int(min(W, (x + w) * W + 0.4 * hp))
    y0, y1 = int(max(0, y * H - 0.45 * hp)), int(min(H, (y + h) * H + 0.45 * hp))
    ty0, ty1 = int(y * H), int(min(H, (y + h) * H)); tx0, tx1 = int(x * W), int(min(W, (x + w) * W))
    if y1 - y0 < 6 or x1 - x0 < 6 or ty1 <= ty0 or tx1 <= tx0: return "indefinido", {}
    c = img[y0:y1, x0:x1].astype(np.float32)
    L = 0.299 * c[..., 0] + 0.587 * c[..., 1] + 0.114 * c[..., 2]
    mx = c.max(-1); mn = c.min(-1); sat = (mx - mn) / np.maximum(mx, 1)
    branco = (L > 205) & (sat < 0.18); escuro = L < 70
    # faixa logo acima e logo abaixo do texto (dentro da pílula, quando há pílula)
    a = int(ty0 - y0); bb = int(ty1 - y0); fx = max(2, int(0.12 * hp))
    faixa = np.concatenate([L[max(0, a - fx):a].ravel(), L[bb:bb + fx].ravel()]) if a > 0 else L[bb:bb + fx].ravel()
    m = {"branco": round(float(branco.mean()), 3), "escuro": round(float(escuro.mean()), 3),
         "faixa": round(float(np.median(faixa)) if faixa.size else 0, 1)}
    if faixa.size and m["faixa"] >= 200 and m["branco"] >= 0.45 and m["escuro"] >= 0.03:
        return "pilula", m
    tx = branco[a:bb, int(tx0 - x0):int(tx1 - x0)]
    m["glifo"] = round(float(tx.mean()) if tx.size else 0, 3)
    if tx.size == 0 or m["glifo"] < 0.06:
        cor = ((L > 140) & (sat > 0.35))[a:bb, int(tx0 - x0):int(tx1 - x0)]
        if cor.size and cor.mean() >= 0.08: return "cor", m
        return "indefinido", m
    r = max(1, int(round(hp * 0.07)))                    # espessura esperada do contorno (~7% da altura da linha)
    dil = ndimage.binary_dilation(branco, iterations=r)
    anel = dil & ~branco
    m["contorno"] = round(float(escuro[anel].mean()) if anel.any() else 0, 3)
    # sombra deslocada: escuro de um lado do glifo e não do outro (3855 V1: sombra para baixo e à direita)
    d = max(2, int(round(hp * 0.12))); dil2 = ndimage.binary_dilation(branco, iterations=max(1, r))
    def lado(dy, dx):
        s = np.zeros_like(branco); ys, xs = slice(max(0, dy), branco.shape[0] + min(0, dy)), slice(max(0, dx), branco.shape[1] + min(0, dx))
        yo, xo = slice(max(0, -dy), branco.shape[0] + min(0, -dy)), slice(max(0, -dx), branco.shape[1] + min(0, -dx))
        s[ys, xs] = branco[yo, xo]; s &= ~dil2
        return float(escuro[s].mean()) if s.any() else 0.0
    esc2 = L < 100                                     # sombra semitransparente (BackColour &H99) fica menos escura que o contorno
    def lado2(dy, dx):
        sh = np.zeros_like(branco)
        ys, xs = slice(max(0, dy), branco.shape[0] + min(0, dy)), slice(max(0, dx), branco.shape[1] + min(0, dx))
        yo, xo = slice(max(0, -dy), branco.shape[0] + min(0, -dy)), slice(max(0, -dx), branco.shape[1] + min(0, -dx))
        sh[ys, xs] = branco[yo, xo]; sh &= ~branco
        return float(esc2[sh].mean()) if sh.any() else 0.0
    assim = 0.0
    for k in range(max(2, r + 1), max(4, int(round(0.5 * hp))) + 1):     # além do contorno: só a sombra continua escura de um lado
        for dy, dx in ((1, 1), (1, 0), (0, 1), (1, -1)):
            p1, p2 = lado2(k * dy, k * dx), lado2(-k * dy, -k * dx)
            if max(p1, p2) >= 0.35: assim = max(assim, abs(p1 - p2))
    m["sombra"] = round(assim, 3)
    # borda pesada (3855 V1, "looks 3d"): de 0,12 a 0,20 da altura da linha em volta da letra, quase preto; o fundo mais
    # longe (0,32-0,38) é claro. Contorno fino (pílula/TikTok) quase some a essa distância. Calibrado em 13/11/2026.
    def anel(r0, r1):
        a0 = ndimage.binary_dilation(branco, iterations=max(1, int(round(r0 * hp))))
        a1 = ndimage.binary_dilation(branco, iterations=max(2, int(round(r1 * hp))))
        rr = a1 & ~a0
        return float(L[rr].mean()) if rr.any() else None
    LA, LB = anel(0.12, 0.20), anel(0.32, 0.38)
    m["borda"] = round(LA, 1) if LA is not None else None; m["fundo"] = round(LB, 1) if LB is not None else None
    if LA is not None and LB is not None and LB >= 45 and LA <= 0.6 * LB: return "sombra", m
    # degradê no preenchimento: o branco do glifo varia muito de cima para baixo
    gl = L[a:bb, int(tx0 - x0):int(tx1 - x0)][tx]
    m["preench_std"] = round(float(gl.std()) if gl.size else 0, 1)
    if m["sombra"] >= 0.45: return "sombra", m
    if m["contorno"] >= 0.35: return "contorno", m
    return "indefinido", m


# família de cada estilo de legenda do montar (lista da Louise: pílula ou branca com contorno, sem sombra/3D/cor)
FAMILIA_LEGENDA = {"pilula": "pilula", "branca_contorno": "contorno", "branca_limpa": "contorno", "branca_limpa_arial": "contorno",
                   "caixa_branca": "pilula", "caixa_branca_pequena": "pilula", "caixa_branca_compacta": "pilula", "caixa_branca_justa": "pilula",
                   "amarelo_contorno": "cor", "branca_legivel": "sombra", "branca_fina": "sombra", "branca_fina_caps": "sombra",
                   "palavra_brilho": "outro"}


def item_estilo(legendas, cfg, estilo_plano=None, pedido_brief=None):
    """Item 2. Classifica cada legenda lida (amostra) e decide pela maioria. Lista fechada: pílula ou branca com contorno."""
    from PIL import Image
    import numpy as np
    ok_cls = {"pilula", "contorno"}; cont = {}; amostra = []; occ = []
    cache = {}
    passo = max(1, len(legendas) // 120)                # até ~120 legendas por vídeo
    for t, l, q in legendas[::passo]:
        if q not in cache:
            cache.clear(); cache[q] = np.asarray(Image.open(q).convert("RGB"))
        cls, m = estilo_crop(cache[q], l["b"])
        cont[cls] = cont.get(cls, 0) + 1
        if cls in ("sombra", "cor"): amostra.append((t, cls, l["t"], m))
    julgadas = sum(v for k, v in cont.items() if k != "indefinido")
    ruins = cont.get("sombra", 0) + cont.get("cor", 0)
    fam = FAMILIA_LEGENDA.get(estilo_plano, "outro") if estilo_plano else None
    if fam and fam not in ok_cls and not pedido_brief:
        occ.append({"t": 0, "msg": f"plano.json pede a legenda \"{estilo_plano}\" ({fam}: fora de pílula ou branca com contorno) sem frase do brief",
                    "nivel": "erro", "regra": "plano"})
    if julgadas >= 3 and ruins / julgadas >= 0.25:
        nome = {"sombra": "sombra deslocada (3D)", "cor": "texto colorido (fora de branco/pílula)"}
        pior = max(("sombra", "cor"), key=lambda k: cont.get(k, 0))
        occ.append({"t": amostra[0][0] if amostra else 0, "nivel": "erro", "regra": pior,
                    "msg": f"legenda com {nome[pior]} em {ruins} de {julgadas} amostras (ex.: {', '.join(mmss(a[0]) for a in amostra[:4])})"})
    res = "legendas: " + (", ".join(f"{k} {v}" for k, v in sorted(cont.items(), key=lambda x: -x[1])) or "nenhuma lida")
    if julgadas < 3 and not occ: res += " (poucas amostras: confira na sala)"
    return (not occ), res, occ, {"contagem": cont, "amostra": [{"t": a[0], "cls": a[1], "texto": a[2], "medidas": a[3]} for a in amostra[:8]]}


# ---------------------------------------------------------------- item 5: imagem por plano
def movimento(mp4, fps, W=180, H=320):
    """Por par de quadros (fps baixo, cinza 180x320): corte, deslocamento global (fase), grade de diferença local (blocos
    de 12 px depois de compensar o deslocamento) e nitidez. A atividade é calculada depois, sem as faixas de texto."""
    import numpy as np
    from scipy import ndimage
    cmd = [FF, "-nostdin", "-v", "error", "-i", mp4, "-an", "-vf", f"fps={fps},scale={W}:{H}:flags=area,format=gray", "-f", "rawvideo", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    n = W * H; han = np.outer(np.hanning(H), np.hanning(W)).astype(np.float32); ant = None; out = []; i = 0; m = 16
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n: break
        f = np.frombuffer(buf, np.uint8).reshape(H, W).astype(np.float32)
        hist = np.histogram(f, 32, (0, 256))[0] / n
        F = np.fft.fft2((f - f.mean()) * han)
        lap = ndimage.laplace(ndimage.gaussian_filter(f, 0.6))
        blk = np.abs(lap[: H // 20 * 20, : W // 20 * 20]).reshape(H // 20, 20, W // 20, 20).mean((1, 3))
        r = {"t": i / fps, "nit": float(np.percentile(blk, 90))}
        if ant is not None:
            R = ant["F"] * np.conj(F); R /= np.abs(R) + 1e-6
            c = np.fft.ifft2(R).real; k = np.unravel_index(np.argmax(c), c.shape); pk = float(c[k])
            dy = k[0] if k[0] <= H // 2 else k[0] - H; dx = k[1] if k[1] <= W // 2 else k[1] - W
            def sub(a0, a1, a2):
                den = a0 - 2 * a1 + a2
                return 0.0 if abs(den) < 1e-9 else 0.5 * (a0 - a2) / den
            sy = sub(c[(k[0] - 1) % H, k[1]], c[k], c[(k[0] + 1) % H, k[1]]); sx = sub(c[k[0], (k[1] - 1) % W], c[k], c[k[0], (k[1] + 1) % W])
            dyi, dxi = (int(dy), int(dx)) if pk >= 0.08 and abs(dy) < m and abs(dx) < m else (0, 0)
            a = ant["f"][m:H - m, m:W - m]; bsh = f[m + dyi:H - m + dyi, m + dxi:W - m + dxi]
            d = np.abs(a - bsh); hh, ww = d.shape[0] // 12 * 12, d.shape[1] // 12 * 12
            r.update({"corte": float(np.abs(hist - ant["h"]).sum() / 2), "dx": dx + sx, "dy": dy + sy, "pico": pk,
                      "mad": float(np.abs(f - ant["f"]).mean()),
                      "grade": d[:hh, :ww].reshape(hh // 12, 12, ww // 12, 12).mean((1, 3)).astype(np.float16)})
        if i % 3 == 0: r["mini"] = ((f[0::2, 0::2] + f[1::2, 0::2] + f[0::2, 1::2] + f[1::2, 1::2]) / 4).astype(np.uint8)   # 90x160 a 5 fps
        out.append(r); ant = {"f": f, "F": F, "h": hist}; i += 1
    p.wait()
    return out


def planos(mov, fps, corte=0.25, minimo=0.6):
    """Divide nos cortes (mudança de histograma ou da imagem inteira) e devolve [(ini, fim, [quadros])]."""
    cortes = [0]
    for k, r in enumerate(mov):
        if k and (r.get("corte", 0) >= corte or r.get("mad", 0) >= 35): cortes.append(k)
    cortes.append(len(mov))
    return [(a / fps, b / fps, mov[a + 1:b]) for a, b in zip(cortes, cortes[1:]) if (b - a) / fps >= minimo]


def atividade(q, faixas, H=320, m=16, bloco=12):
    """Mudança local do quadro (98º percentil dos blocos), sem as linhas onde há texto (legenda trocando não é movimento)."""
    import numpy as np
    g = q.get("grade")
    if g is None: return None
    g = g.astype(np.float32); ok = np.ones(g.shape[0], bool)
    for y0, y1 in faixas:
        for i in range(g.shape[0]):
            a, b = (m + i * bloco) / H, (m + (i + 1) * bloco) / H
            if b > y0 - 0.03 and a < y1 + 0.03: ok[i] = False
    v = g[ok]
    return float(np.percentile(v, 98)) if v.size >= 24 else None


def residuo_zoom(mov, faixas, passo=2, escalas=None):
    """Imagem parada com zoom (4029 V3, S01: quadro com zoom lento) não é deslocamento: compara cada quadro (5 fps,
    90x160) com o de 0,4 s depois, desfazendo zoom e deslocamento; o que sobra (98º percentil dos blocos, sem as faixas
    de texto) é o movimento de verdade. Quadro parado com zoom: quase zero. Devolve [(t, resto)]."""
    import numpy as np
    from scipy import ndimage
    escalas = escalas or [1 + k * 0.004 for k in range(-8, 9)]
    minis = [(q["t"], q["mini"].astype(np.float32)) for q in mov if q.get("mini") is not None]
    out = []
    for (t0, f0), (t1, f1) in zip(minis, minis[passo:]):
        if t1 - t0 > 0.6: continue
        H, W = f0.shape; cy, cx = (H - 1) / 2, (W - 1) / 2; m = 10
        F0 = np.fft.fft2(f0 - f0.mean()); melhor = None
        for sc in escalas:
            g = ndimage.affine_transform(f1, [1 / sc, 1 / sc], offset=[cy - cy / sc, cx - cx / sc], order=1, mode="nearest")
            R = F0 * np.conj(np.fft.fft2(g - g.mean())); R /= np.abs(R) + 1e-6
            c = np.fft.ifft2(R).real; k = np.unravel_index(np.argmax(c), c.shape)
            dy = k[0] if k[0] <= H // 2 else k[0] - H; dx = k[1] if k[1] <= W // 2 else k[1] - W
            if abs(dy) >= m or abs(dx) >= m: continue
            d = np.abs(f0[m:H - m, m:W - m] - g[m - dy:H - m - dy, m - dx:W - m - dx])
            hh, ww = d.shape[0] // 7 * 7, d.shape[1] // 7 * 7
            bl = d[:hh, :ww].reshape(hh // 7, 7, ww // 7, 7).mean((1, 3)); ok = np.ones(bl.shape[0], bool)
            for y0, y1 in faixas(t0) + faixas(t1):
                for i in range(bl.shape[0]):
                    a, b = (m + i * 7) / H, (m + (i + 1) * 7) / H
                    if b > y0 - 0.03 and a < y1 + 0.03: ok[i] = False
            v = bl[ok]
            if v.size < 20: continue
            r = float(np.percentile(v, 98))
            if melhor is None or r < melhor: melhor = r
        if melhor is not None: out.append((round(t0, 2), round(melhor, 2)))
    return out


def parado_clipe(mp4, cfg, fps=5, W=180, H=320, pula=0.6):
    """Clipe cru (antes da montagem) feito de imagem parada, com ou sem zoom: desfeitos zoom e deslocamento entre quadros
    a 0,4 s, o que sobra é só ruído (resto p90 <= ~8; clipe de verdade >= ~14). Calibrado em 13/11/2026: 4029 S01 V3
    (quadro com zoom) 7,1 e 3858 S38 V4 7,8 contra 21-25 dos clipes que os trocaram. Devolve (parado, resto)."""
    import numpy as np
    from scipy import ndimage
    r = subprocess.run([FF, "-nostdin", "-v", "error", "-i", mp4, "-an", "-vf", f"fps={fps},scale={W}:{H}:flags=area,format=gray", "-f", "rawvideo", "-"],
                       capture_output=True)
    a = np.frombuffer(r.stdout, np.uint8); n = a.size // (W * H)
    fr = a[: n * W * H].reshape(n, H, W).astype(np.float32)[int(pula * fps):]
    restos = []
    for f0, f1 in zip(fr, fr[2:]):
        cy, cx = (H - 1) / 2, (W - 1) / 2; F0 = np.fft.fft2(f0 - f0.mean()); best = None; m = 16
        for sc in [1 + k * 0.002 for k in range(-15, 16)]:
            g = ndimage.affine_transform(f1, [1 / sc, 1 / sc], offset=[cy - cy / sc, cx - cx / sc], order=1, mode="nearest")
            R = F0 * np.conj(np.fft.fft2(g - g.mean())); R /= np.abs(R) + 1e-6; c = np.fft.ifft2(R).real
            k = np.unravel_index(np.argmax(c), c.shape)
            dy = k[0] if k[0] <= H // 2 else k[0] - H; dx = k[1] if k[1] <= W // 2 else k[1] - W
            if abs(dy) >= m or abs(dx) >= m: continue
            d = np.abs(f0[m:H - m, m:W - m] - g[m - dy:H - m - dy, m - dx:W - m - dx])
            bl = d[: d.shape[0] // 8 * 8, : d.shape[1] // 8 * 8].reshape(d.shape[0] // 8, 8, d.shape[1] // 8, 8).mean((1, 3))
            v = (float(np.median(bl)), float(np.percentile(bl, 90)))
            if best is None or v[0] < best[0]: best = v
        if best: restos.append(best[1])
    if len(restos) < 3: return False, None
    resto = float(np.median(restos))
    return resto <= cfg["imagem"].get("parado_clipe_max", 10.0), round(resto, 2)


def clipes_reprovados(B, P):
    """Clipes que a conferência da chegada reprovou (parado, tremido, borrado) e que continuam na pasta sem ter sido
    refeitos (o json da conferência é mais novo que o clipe). Vale para a versão atual."""
    out = []
    for j in glob.glob(os.path.join(glob.escape(os.path.join(B, P["auto"])), "conferencia", "assets", "*.json")):
        try: r = json.load(open(j, encoding="utf-8"))
        except ValueError: continue
        arq = r.get("arquivo", "")
        if not arq or not os.path.exists(arq) or "_antigos" in arq or "_rejeitadas" in arq or os.path.getmtime(j) < os.path.getmtime(arq): continue
        for a in r.get("achados", []):
            if a.get("nivel") == "erro" and a.get("regra") in ("parado", "tremido", "borrado"):
                out.append((os.path.relpath(arq, B), a["regra"], a.get("msg", "")))
    return out


def item_imagem(mov, cfg, fps, dur, faixas_t=None):
    """Item 5. faixas_t = [(t, [(y0, y1)...])] das caixas de texto do OCR (para não contar texto como movimento)."""
    import numpy as np
    c = cfg["imagem"]; occ = []; info = []
    ft = sorted(faixas_t or [])
    tempos = [x[0] for x in ft]
    import bisect
    def faixas(t):
        if not ft: return []
        j = bisect.bisect_left(tempos, t)
        cand = [k for k in (j - 1, j) if 0 <= k < len(ft)]
        k = min(cand, key=lambda k: abs(ft[k][0] - t))
        return ft[k][1] if abs(ft[k][0] - t) <= 0.6 else []
    at = [atividade(q, faixas(q["t"])) for q in mov]
    lim = c["parado_resto_max"]
    # imagem parada: trecho >= parado_dur_min s em que, desfeitos zoom e deslocamento, quase nada muda (tolera 1 ponto fora)
    rz = residuo_zoom(mov, faixas); baixos = []; k, n = 0, len(rz)
    while k < n:
        if rz[k][1] <= lim:
            j = k
            while j + 1 < n and (rz[j + 1][1] <= lim or (j + 2 < n and rz[j + 2][1] <= lim)) and rz[j + 1][0] - rz[j][0] <= 0.5: j += 1
            a, b = rz[k][0], rz[j][0] + 0.4
            med = float(np.median([x for _, x in rz[k:j + 1]]))
            baixos.append((round(a, 2), round(b - a, 2), round(med, 2)))
            if b - a >= c["parado_dur_min"]:
                occ.append({"t": round(a, 2), "t_fim": round(b, 2), "regra": "parado", "nivel": "aviso",
                            "msg": f"possível imagem parada {mmss(a)}–{mmss(b)}: resto {med:.1f}; confira (no export o zoom da montagem confunde; a trava é no clipe, na chegada)"})
            k = j + 1
        else:
            k += 1
    for a, b, qs in planos(mov, fps, minimo=c["plano_min_s"]):
        qs = [q for q in qs if "dx" in q]
        if len(qs) < 5: continue
        conf = [q for q in qs if q["pico"] >= 0.08 and abs(q["dx"]) <= 10 and abs(q["dy"]) <= 10]
        tremor = 0.0
        if len(conf) >= 0.7 * len(qs):
            v = np.array([[q["dx"], q["dy"]] for q in conf]) * (720 / 180)          # px de 720 por quadro
            alto = v - np.array([np.median(v[max(0, i - 2):i + 3], 0) for i in range(len(v))])
            tremor = float(1.4826 * np.median(np.hypot(alto[:, 0], alto[:, 1])))
        nit = float(np.median([q["nit"] for q in qs]))
        ids = {id(q) for q in qs}
        aa = [x for x, q in zip(at, mov) if id(q) in ids and x is not None]
        rr = [x for t, x in rz if a <= t < b]
        info.append({"ini": round(a, 2), "fim": round(b, 2), "resto": round(float(np.median(rr)), 2) if rr else None,
                     "ativ": round(float(np.median(aa)), 2) if aa else None,
                     "ativ_p10": round(float(np.percentile(aa, 10)), 2) if aa else None, "tremor": round(tremor, 2), "nit": round(nit, 2)})
        if tremor > c["tremor_max"]:
            occ.append({"t": round(a, 2), "t_fim": round(b, 2), "regra": "tremido", "nivel": "erro",
                        "msg": f"plano tremido {mmss(a)}–{mmss(b)}: tremor {tremor:.1f} px (máximo {c['tremor_max']})"})
        if c.get("nitidez_min") and nit < c["nitidez_min"]:
            occ.append({"t": round(a, 2), "t_fim": round(b, 2), "regra": "borrado", "nivel": "erro",
                        "msg": f"plano borrado {mmss(a)}–{mmss(b)}: nitidez {nit:.1f} (mínimo {c['nitidez_min']})"})
    occ.sort(key=lambda o: o["t"])
    if info: info.append({"trechos_baixos": sorted(baixos, key=lambda x: -x[1])[:8]})
    erros = [o for o in occ if o["nivel"] == "erro"]
    return (not erros), f"{len(info) - (1 if info else 0)} plano(s) medidos" + (f"; {len(erros)} problema(s)" if erros else "; nenhum tremido ou borrado") +         (f", {len(occ) - len(erros)} aviso(s)" if len(occ) > len(erros) else ""), occ, info


# ---------------------------------------------------------------- item 6: notas da revisão
def item_notas(B, P, versao, video):
    m = re.match(r"V(\d+)", versao or "")
    k = int(m[1]) if m else 1
    if k <= 1: return True, "V1: sem notas de revisão", []
    nome = os.path.basename(video); ad = re.search(r"(?:AD|Hook)\s*_?(\d+)", nome, re.I)
    cands = [os.path.join(B, d, f"revisao_V{k}.md") for d in (P["roteiro"], "00_briefing", "00_roteiro")]
    arq = next((x for x in cands if os.path.exists(x)), None)
    if not arq:
        return False, f"sem lista de notas ({P['roteiro']}/revisao_V{k}.md, 10_revisao.md passo 1b)", \
            [{"t": 0, "msg": f"falta {P['roteiro']}/revisao_V{k}.md (gere com frameio.py comentarios ... --revisao)", "nivel": "erro", "regra": "sem_lista"}]
    occ = []; tot = 0
    for ln in open(arq, encoding="utf-8"):
        mm = re.match(r"\s*[-*]\s*\[( |x|X)\]\s*(.+)", ln)
        if not mm: continue
        txt = mm[2].strip(); nad = re.search(r"\b(?:AD|Hook|H)\s*(\d+)\b", txt, re.I)
        if ad and nad and nad[1] != ad[1] and not re.search(r"todos|all ads|hold", txt, re.I): continue
        tot += 1
        if mm[1] == " ":
            occ.append({"t": 0, "msg": f"nota aberta: {txt[:120]}", "nivel": "erro", "regra": "aberta"}); continue
        pv = re.search(r"prova:\s*`?([^`·|]+?)`?\s*(?:$|·|\|)", txt)
        cam = pv[1].strip() if pv else ""
        if not cam or not (os.path.exists(cam) or os.path.exists(os.path.join(B, cam))):
            occ.append({"t": 0, "msg": f"nota marcada sem prova (quadro da versão nova): {txt[:100]}", "nivel": "erro", "regra": "sem_prova"})
    if tot == 0:
        return False, f"{os.path.relpath(arq, B)} sem nenhuma nota", [{"t": 0, "msg": "lista de notas vazia", "nivel": "erro", "regra": "vazia"}]
    return (not occ), f"{tot} nota(s) em {os.path.relpath(arq, B)}" + (f"; {len(occ)} sem [x] ou sem prova" if occ else "; todas feitas com prova"), occ


# ---------------------------------------------------------------- montar: arquivos com a medida exata
def lado_montar(B, P, video, prefixo, dg):
    """<auto>/<prefixo>_AD<n>_<p>.json gravado pelo montar para este arquivo (mesma impressão digital)."""
    for j in glob.glob(os.path.join(glob.escape(os.path.join(B, P["auto"])), prefixo + "_*.json")):
        try: d = json.load(open(j, encoding="utf-8"))
        except ValueError: continue
        if d.get("digital") == dg: return d
        if dg in d.get("por_digital", {}): return d["por_digital"][dg]
    return None


# ---------------------------------------------------------------- rodar
def rodar_video(B, ficha, cfg, video, versao, itens, tmp, debug=False):
    P = pastas_de(ficha); dur = duracao(video); dg = digital(video)
    res = {"caminho": os.path.abspath(video), "digital": dg, "duracao": round(dur, 2), "versao": versao, "itens": {}}
    def poe(n, ok, resumo, occ, extra=None):
        res["itens"][str(n)] = {"nome": ITENS[n], "ok": bool(ok), "resumo": resumo, "ocorrencias": occ, **({"extra": extra} if extra and debug else {})}
    d = os.path.join(tmp, re.sub(r"[^A-Za-z0-9]+", "_", os.path.basename(video))[:60]); os.makedirs(d, exist_ok=True)
    words = []; a16 = None; faixas_t = None
    precisa_fala = any(n in itens for n in (1, 2, 3, 4))
    if precisa_fala:
        wav = os.path.join(d, "a16k.wav"); a16 = audio16k(video, wav)
        import numpy as np
        wp = os.path.join(d, "a16k_pad.wav")          # 0,5 s de silêncio antes: o Whisper perdia palavra no quadro 0 (4029 "I gave")
        with wave.open(wp, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
            w.writeframes((np.concatenate([np.zeros(8000, np.float32), a16]) * 32767).clip(-32768, 32767).astype(np.int16).tobytes())
        try: words = [(w, max(0.0, a - 0.5), max(0.0, b - 0.5), p) for w, a, b, p in transcrever(wp, cfg["vo"].get("idioma", "en"))]
        except Exception as e:
            words = []; res["aviso_whisper"] = f"Whisper falhou: {e}"
    nv = niveis(a16, words) if precisa_fala else None
    if 3 in itens:
        rot, marca = roteiro_do_ad(B, P, video)
        mix3 = lado_montar(B, P, video, "mix", dg)
        stems = bool(mix3 and mix3.get("pausas") is not None)
        pz = mix3["pausas"] if stems else pausas_audio(nv, cfg["vo"].get("pausa_abaixo_db", 8.0))
        ok3, r3, o3 = item_vo(words, rot, marca, cfg, dur, pz, exata=stems)
        poe(3, ok3, r3, o3, {"pausas": sorted(pz, key=lambda x: -x[1])[:8], "fonte_pausas": "stems" if stems else "mix"})
    if 4 in itens:
        mix = lado_montar(B, P, video, "mix", dg)
        c4 = cfg
        try:      # alvo de loudness do job/batch (EV batch.json e TS job.json: audio.loudness_lufs) vence o da ficha
            alvo = json.load(open(os.path.join(B, P["config"]), encoding="utf-8")).get("audio", {}).get("loudness_lufs")
            if alvo is not None: c4 = _mescla(cfg, {"musica": {"lufs": float(alvo)}})
        except (OSError, ValueError, AttributeError): pass
        poe(4, *item_musica(a16, words, c4, mix=mix, lu=lufs(video)))
    if 1 in itens or 2 in itens or 5 in itens:          # o item 5 usa as caixas de texto do OCR (legenda trocando não é movimento)
        qs = quadros(video, os.path.join(d, "q"), cfg["ocr"]["fps"])
        vis = __import__("visao").ler([q for _, q in qs]) if qs else {}
        faixas_t = [(t, [(l["b"][1], l["b"][1] + l["b"][3]) for l in vis.get(q, {}).get("textos", [])]) for t, q in qs]
        _cache = {}
        def img(q):
            if q not in _cache:
                from PIL import Image
                import numpy as np
                if len(_cache) > 6: _cache.clear()
                _cache[q] = np.asarray(Image.open(q).convert("RGB"))
            return _cache[q]
        if qs and not vis:
            for n in (1, 2):
                if n in itens: poe(n, False, "OCR indisponível nesta máquina", [{"t": 0, "msg": "sem OCR: não deu para conferir o texto", "nivel": "erro"}])
        else:
            cam = lado_montar(B, P, video, "camadas", dg)
            ok1, r1, o1, legendas = item_texto(qs, vis, words, cfg, cam, tamanho(video), img, vocab_cena(B, P))
            if 1 in itens: poe(1, ok1, r1, o1)
            if 2 in itens:
                ep, pb = None, None
                if versao == versao_de(B, os.path.join(B, P["export"], "x.mp4"), P):      # plano.json vale só para a versão atual
                    try:
                        pl = json.load(open(os.path.join(B, P["auto"], "plano.json"), encoding="utf-8")).get("estilo", {}).get("legenda", {})
                        ep, pb = pl.get("estilo") or "pilula", pl.get("pedido_brief")
                    except (OSError, ValueError): pass
                if cam and cam.get("estilo_legenda"): ep = cam["estilo_legenda"]
                ok2, r2, o2, ex2 = item_estilo(legendas, cfg, ep, pb)
                poe(2, ok2, r2, o2, ex2)
    if 5 in itens:
        mov = movimento(video, cfg["imagem"]["fps"])
        ok5, r5, o5, info = item_imagem(mov, cfg, cfg["imagem"]["fps"], dur, faixas_t)
        if versao == versao_de(B, os.path.join(B, P["export"], "x.mp4"), P):      # clipes da versão atual reprovados na chegada
            rep = clipes_reprovados(B, P)
            for arq, regra, msg in rep:
                o5.append({"t": 0, "regra": regra, "nivel": "erro", "msg": f"clipe reprovado na chegada e ainda na batch: {arq} ({msg[:90]})"})
            if rep: ok5 = False; r5 += f"; {len(rep)} clipe(s) reprovado(s) na chegada"
        poe(5, ok5, r5, o5, info)
    if 6 in itens:
        poe(6, *item_notas(B, P, versao, video))
    res["verde"] = all(v["ok"] for v in res["itens"].values()) and set(map(str, itens)) <= set(res["itens"])
    shutil.rmtree(d, ignore_errors=True)
    return res


def grava(B, P, versao, cfg, ficha, resultados, saida=None):
    pasta = saida or os.path.join(B, P["auto"]); os.makedirs(pasta, exist_ok=True)
    arq = os.path.join(pasta, f"checklist_{versao}.json")
    try: atual = json.load(open(arq, encoding="utf-8"))
    except (OSError, ValueError): atual = {}
    vids = atual.get("videos", {})
    for r in resultados: vids[os.path.basename(r["caminho"])] = r
    out = {"versao": versao, "batch": os.path.basename(B), "cliente": (ficha or {}).get("id"), "itens": cfg["itens"],
           "atualizado": datetime.datetime.now().isoformat(timespec="seconds"), "videos": vids,
           "verde": all(v.get("verde") for v in vids.values())}
    tmpf = arq + ".tmp"; json.dump(out, open(tmpf, "w", encoding="utf-8"), ensure_ascii=False, indent=1); os.replace(tmpf, arq)
    return arq


def imprime(r, B):
    nome = os.path.relpath(r["caminho"], B) if r["caminho"].startswith(B) else r["caminho"]
    print(f"\n{nome}  [{r['versao']}]  {'VERDE' if r['verde'] else 'VERMELHO'}")
    for k in sorted(r["itens"], key=int):
        it = r["itens"][k]
        print(f"  {'✔' if it['ok'] else '✖'} {k} {TITULO[int(k)]:22s} {it['resumo']}")
        for o in [o for o in it["ocorrencias"] if o.get("nivel") == "erro"][:6]:
            print(f"      ✖ {mmss(o.get('t', 0))}  {o['msg']}")
        for o in [o for o in it["ocorrencias"] if o.get("nivel") == "aviso"][:3]:
            print(f"      ! {mmss(o.get('t', 0))}  {o['msg']}")
    if r.get("aviso_whisper"): print("  !", r["aviso_whisper"])


def cmd_rodar(a):
    B = os.path.abspath(a.batch.rstrip("/\\"))
    if not os.path.isdir(B): print(f"Pasta não existe: {B}", file=sys.stderr); return 2
    ficha = ficha_de(B) or (_fichas().get(a.cliente) if a.cliente else None); cfg = config_de(ficha); P = pastas_de(ficha)
    if not ficha: print(f"{B} não está numa pasta de cliente com ficha (teste fora dela: --cliente ev|ts).", file=sys.stderr); return 2
    if not cfg.get("ativo") and not (a.forcar or a.saida):      # --saida = teste: roda mesmo desligado
        print(f"checklist desligado na ficha de {ficha.get('nome')} (\"checklist\": {{\"ativo\": false}}): nada a fazer. "
              "Ligar só com ok do Fefo."); return 0
    videos = [os.path.abspath(v if os.path.exists(v) else os.path.join(B, v)) for v in a.videos] or exports_atuais(B, P)
    for v in videos:
        if not os.path.exists(v): print(f"Vídeo não existe: {v}", file=sys.stderr); return 2
    if not videos: print(f"Sem vídeos em {P['export']}/.", file=sys.stderr); return 2
    itens = [int(x) for x in a.so.split(",")] if a.so else [int(x) for x in cfg["itens"]]
    tmp = tempfile.mkdtemp(prefix="checklist_")
    porver = {}
    try:
        for v in videos:
            ver = a.versao and (a.versao if str(a.versao).upper().startswith("V") else f"V{a.versao}") or versao_de(B, v, P)
            try:
                r = rodar_video(B, ficha, cfg, v, ver, itens, tmp, a.debug)
            except subprocess.CalledProcessError as e:
                print(f"\n{v}\n  ! erro ao rodar: {e}", file=sys.stderr); return 2
            imprime(r, B); porver.setdefault(ver, []).append(r)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for ver, rs in porver.items():
        arq = grava(B, P, ver, cfg, ficha, rs, a.saida)
        print(f"\ngravei {arq}")
    todos = [r for rs in porver.values() for r in rs]
    verm = [r for r in todos if not r["verde"]]
    print(f"\nChecklist da Louise: {len(todos) - len(verm)} de {len(todos)} vídeo(s) verde(s)." +
          ("" if not verm else " Item vermelho bloqueia a sala e a entrega; dispensa do Fefo não vale para estes itens."))
    return 1 if verm else 0


# ---------------------------------------------------------------- estado e trava da entrega
def estado_de(video):
    """{'verde': bool|None, 'versao', 'itens': {n: ok}, 'arquivo': json} do checklist com a mesma impressão digital."""
    ficha = ficha_de(video); P = pastas_de(ficha); B = batch_de(video, ficha)
    cfg = config_de(ficha)
    if not cfg.get("ativo"): return {"ativo": False}
    if not B: return {"ativo": True, "verde": None, "motivo": "vídeo fora de uma batch"}
    dg = digital(video)
    for j in sorted(glob.glob(os.path.join(glob.escape(os.path.join(B, P["auto"])), "checklist_V*.json")), key=os.path.getmtime, reverse=True):
        try: d = json.load(open(j, encoding="utf-8"))
        except ValueError: continue
        for nome, r in d.get("videos", {}).items():
            if r.get("digital") == dg:
                falhas = {k: [o["msg"] for o in v["ocorrencias"] if o.get("nivel") == "erro"][:3] for k, v in r["itens"].items() if not v["ok"]}
                faltam = [str(n) for n in cfg["itens"] if str(n) not in r["itens"]]
                return {"ativo": True, "verde": bool(r.get("verde")) and not faltam, "versao": r.get("versao"), "arquivo": j,
                        "itens": {k: v["ok"] for k, v in r["itens"].items()}, "falhas": falhas, "faltam": faltam,
                        "resumos": {k: v["resumo"] for k, v in r["itens"].items()}}
    return {"ativo": True, "verde": None, "motivo": "checklist não rodou neste arquivo (rode fluxo.py checar)"}


def cmd_entrega(a):
    B = os.path.abspath(a.batch.rstrip("/\\")); ficha = ficha_de(B); P = pastas_de(ficha); cfg = config_de(ficha)
    if not cfg.get("ativo"): print("checklist desligado na ficha deste cliente: a trava não se aplica."); return 0
    videos = [os.path.abspath(v if os.path.exists(v) else os.path.join(B, v)) for v in a.videos] or exports_atuais(B, P)
    if not videos: print("sem vídeos para entregar"); return 1
    ruins = 0
    for v in videos:
        if os.path.exists(os.path.splitext(v)[0] + ".PREVIA.txt") or os.path.exists(v + ".PREVIA.txt"):
            print(f"✖ {os.path.basename(v)}: é PRÉVIA (.PREVIA.txt): renderize sem PREVIA e rode o checklist no final"); ruins += 1; continue
        e = estado_de(v)
        if e.get("verde"):
            print(f"✔ {os.path.basename(v)}: checklist {e['versao']} verde")
        else:
            ruins += 1
            print(f"✖ {os.path.basename(v)}: " + (e.get("motivo") or "checklist vermelho") )
            for k, ms in (e.get("falhas") or {}).items():
                print(f"    item {k} ({TITULO[int(k)]}): " + " | ".join(ms))
            if e.get("faltam"): print(f"    itens que não rodaram: {', '.join(e['faltam'])}")
    if ruins:
        print(f"\nENTREGA RECUSADA: {ruins} vídeo(s) sem checklist verde. Corrija e rode `fluxo.py checar <batch>`; "
              "dispensa do Fefo não vale para o checklist da Louise.")
    return 1 if ruins else 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "entrega":
        ap = argparse.ArgumentParser(prog="checklist.py entrega"); ap.add_argument("batch"); ap.add_argument("videos", nargs="*")
        return cmd_entrega(ap.parse_args(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == "estado":
        out = {v: estado_de(v) for v in sys.argv[2:]}
        print(json.dumps(out, ensure_ascii=False, indent=1)); return 0
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("batch"); ap.add_argument("videos", nargs="*"); ap.add_argument("--versao"); ap.add_argument("--so")
    ap.add_argument("--saida"); ap.add_argument("--debug", action="store_true"); ap.add_argument("--cliente")
    ap.add_argument("--forcar", action="store_true", help="roda mesmo com o checklist desligado na ficha (teste)")
    return cmd_rodar(ap.parse_args())


if __name__ == "__main__":
    sys.exit(main())
