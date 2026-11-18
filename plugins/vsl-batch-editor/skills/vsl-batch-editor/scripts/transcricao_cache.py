"""Uma transcrição por vídeo, usada por todos (Fefo, 16/11/2026: fluxo mais rápido).

O checklist da Louise, o qc_export da TS e o prepara.py do revisor transcreviam o mesmo arquivo cada um (até 3 Whisper
medium por vídeo). Agora o primeiro grava as palavras e os outros leem. Chave = conteúdo do arquivo (tamanho + 1 MB do
começo e do fim), então a cópia local do Drive e o original batem. Palavras no tempo do vídeo: [palavra, ini, fim, prob].
Cópia idêntica em ~/.claude/skills/sala-de-revisao/revisor/transcricao_cache.py (o revisor importa a de lá).
"""
import hashlib, json, os, tempfile

# DLLs CUDA do Whisper na GPU (Central, 17/11/2026; M1WK4B2: "cublas64_12.dll not found"). O cuda_dlls.py fica na
# mesma pasta (copia do revisor) ou em _FLUXO/scripts (copia do nucleo, um nivel acima de checagens/).
try:
    import sys as _sys
    _aqui = os.path.dirname(os.path.abspath(__file__))
    for _d in (_aqui, os.path.dirname(_aqui)):
        if os.path.exists(os.path.join(_d, "cuda_dlls.py")) and _d not in _sys.path:
            _sys.path.insert(0, _d)
    import cuda_dlls
except ImportError:
    cuda_dlls = None


def gpu():
    """True se a GPU serve para o Whisper (liga as DLLs CUDA antes). Toda transcricao chama isto antes do WhisperModel."""
    return bool(cuda_dlls and cuda_dlls.liga())

PASTA = os.path.join(os.environ.get("TEMP") or os.environ.get("TMPDIR") or tempfile.gettempdir(), "fluxo_transcricao")


def chave(video):
    t = os.path.getsize(video); h = hashlib.sha1(str(t).encode())
    with open(video, "rb") as f:
        h.update(f.read(1 << 20))
        if t > 2 << 20:
            f.seek(-(1 << 20), 2); h.update(f.read(1 << 20))
    return h.hexdigest()[:20]


def ler(video, idioma="en"):
    try:
        d = json.load(open(os.path.join(PASTA, f"{chave(video)}_{idioma}.json"), encoding="utf-8"))
        return [tuple(w) for w in d["palavras"]]
    except (OSError, ValueError, KeyError):
        return None


def gravar(video, palavras, idioma="en", origem=""):
    try:
        os.makedirs(PASTA, exist_ok=True)
        json.dump({"video": os.path.basename(video), "origem": origem,
                   "palavras": [[w, round(a, 3), round(b, 3), round(p, 3)] for w, a, b, p in palavras]},
                  open(os.path.join(PASTA, f"{chave(video)}_{idioma}.json"), "w", encoding="utf-8"), ensure_ascii=False)
    except OSError:
        pass


def vocabulario(video):
    """Palavras raras do job para o Whisper (hotwords): job.json/batch.json "vocabulario", na pasta acima
    do vídeo. Sem isso o medium ouvia "Leydig" como "lytic" (M1WK4B2 V6, 16/11/2026). None = sem vocabulário."""
    d = os.path.dirname(os.path.abspath(video))
    for _ in range(6):
        for nome in ("job.json", "batch.json"):
            try:
                j = json.load(open(os.path.join(d, nome), encoding="utf-8"))
            except (OSError, ValueError):
                continue
            v = [str(x) for x in (j.get("vocabulario") or [])]   # sem a marca: com "Testolite" o Whisper inventava
                                                                  # a marca no lugar de "every penny" (M1WK4B2 V6 H3)
            return " ".join(dict.fromkeys(v)) or None
        d = os.path.dirname(d)
    return None


def idioma(video, padrao="en"):
    """Idioma da fala para o Whisper. Ordem: job.json/batch.json "idioma" na pasta acima do vídeo → plano.json da
    batch ("idioma", na pasta ou numa subpasta como 08_auto) → padrao (o da ficha do cliente). Antes todos usavam o
    "en" da ficha: na 4611 ("es") o Whisper ouvia "Insta" no lugar de "Esta" e o L3 travava (17/11/2026)."""
    d = os.path.dirname(os.path.abspath(video))
    for _ in range(6):
        for nome in ("job.json", "batch.json"):
            try:
                j = json.load(open(os.path.join(d, nome), encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if str(j.get("idioma") or "").strip():
                return str(j["idioma"]).strip().lower()
            planos = [os.path.join(d, "plano.json")] + sorted(
                os.path.join(d, s, "plano.json") for s in os.listdir(d) if os.path.isdir(os.path.join(d, s)))
            for pl in planos:
                try:
                    i = str(json.load(open(pl, encoding="utf-8")).get("idioma") or "").strip()
                except (OSError, ValueError, AttributeError):
                    continue
                if i:
                    return i.lower()
            return padrao or "en"
        d = os.path.dirname(d)
    return padrao or "en"
