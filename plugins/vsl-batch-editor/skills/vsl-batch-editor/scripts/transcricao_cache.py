"""Uma transcrição por vídeo, usada por todos (Fefo, 16/11/2026: fluxo mais rápido).

O checklist da Louise, o qc_export da TS e o prepara.py do revisor transcreviam o mesmo arquivo cada um (até 3 Whisper
medium por vídeo). Agora o primeiro grava as palavras e os outros leem. Chave = conteúdo do arquivo (tamanho + 1 MB do
começo e do fim), então a cópia local do Drive e o original batem. Palavras no tempo do vídeo: [palavra, ini, fim, prob].
Cópia idêntica em ~/.claude/skills/sala-de-revisao/revisor/transcricao_cache.py (o revisor importa a de lá).
"""
import hashlib, json, os, tempfile

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
