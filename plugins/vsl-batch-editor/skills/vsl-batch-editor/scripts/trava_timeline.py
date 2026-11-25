"""Trava da linha do tempo (Fefo, "Põe a trava", 18/11/2026; MANUAL_DO_MONTADOR.md seção 2).

Confere a LINHA DO TEMPO (o plano da montagem, não o vídeo) antes de qualquer render e recusa o render se houver lasca.
Os três motores chamam `conferir` antes do ffmpeg: EV `fluxo.py fazer/montar` (montar.py), `linha_do_tempo.py`
(segmento e final), `take_unico.py`; TS `montagem_base.montar_por_segmentos`.

  conferir(planos, fps, dur_total=None, aceitas=(), saltos=True) -> [erros]

planos = lista de dicts (ou tuplas (ini, fim, fonte, tipo)) no tempo da SAÍDA:
  ini, fim (s), fonte (id do clipe; arquivo no b-roll), tipo "avatar" | "broll" | "camada",
  opcionais: src_ini, src_fim (s no clipe de origem), dur_min (s, da cena), nome (cena), emenda (bool: corte do avatar).
Erros (cada um com tempo mm:ss, fonte e correção sugerida):
  curto       plano com menos de 12 quadros a 30 (escala pelo fps), exceto cena com dur_min explícito >= o tamanho
  A-B-A       plano curto entre dois da mesma fonte
  corte duplo dois cortes a menos de 12 quadros, um do b-roll e outro da emenda de fala
  avatar 0    avatar a menos de 0,5 s do início antes de um insert
  buraco / sobreposição entre planos
  repetida    mesmo trecho de fonte usado 2x
  salto       trecho que contém um salto interno do clipe de origem (saltos_da_fonte, cache por hash)
Escape: `aceitar_lasca` no plano (EV plano.json, TS job.json): [{"t": "mm:ss" | "<segmento>@mm:ss", "ad": opcional,
"motivo": "..."}]. Grave com: py trava_timeline.py aceitar <plano.json|job.json> <mm:ss> "<motivo>" [--ad AD1_neurobella]

CLI: py trava_timeline.py saltos <clipe.mp4> ... (registra os saltos; a trava também registra sozinha no 1º uso)
     py trava_timeline.py json <planos.json> [--fps 30]   (teste)
Sem render pelo motor: EV e take único `fluxo.py trava <batch> [--so AD1_x]`; TS `TRAVA_SO=1 py 06_auto/montar.py`.
Desligar (só para diagnóstico, nunca para entregar): TRAVA_TIMELINE=0. TRAVA_VER=1|2 lista os planos.
"""
import hashlib, json, os, subprocess, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
CACHE_SALTOS = os.path.join(os.path.dirname(os.path.dirname(AQUI)), "cache", "saltos_fonte")   # _FLUXO/cache/saltos_fonte
VIS = ("avatar", "broll")
VERSAO_SALTOS = 2           # muda quando o detector muda (refaz o cache)


def mmss(t):
    t = max(0.0, t); m = int(t // 60); return f"{m:02d}:{t - 60 * m:04.1f}"


def _norm(p):
    if isinstance(p, dict): return dict(p)
    ini, fim, fonte, tipo = p[:4]; return {"ini": ini, "fim": fim, "fonte": fonte, "tipo": tipo}


def _nome(p):
    f = p.get("nome") or os.path.basename(str(p.get("fonte", "?")))
    return f


# ---------------------------------------------------------------- saltos internos do clipe de origem
def _hash_arq(arq):
    h = hashlib.sha1(); st = os.stat(arq); h.update(str(st.st_size).encode())
    with open(arq, "rb") as f:
        h.update(f.read(1 << 20))
        if st.st_size > 2 << 20: f.seek(-(1 << 20), 2); h.update(f.read(1 << 20))
    return h.hexdigest()[:20]


HOOK_ATE = float(os.environ.get("TRAVA_HOOK_ATE", "6.0"))   # hook = até 6 s (manual 7b, regra 1); 0 desliga
PARADO_MIN = 0.5                                              # trecho parado que recusa
CACHE_PARADOS = os.path.join(os.path.dirname(CACHE_SALTOS), "parados_fonte")


def parados_da_fonte(arq):
    """(duração, [(ini, fim)]) dos trechos sem movimento (freezedetect, ruído 0,003, >= 0,5 s) do clipe de origem.
    Cache por hash do conteúdo em _FLUXO/cache/parados_fonte."""
    if not arq or not os.path.isfile(arq): return 0.0, []
    try: h = _hash_arq(arq)
    except OSError: return 0.0, []
    cj = os.path.join(CACHE_PARADOS, h + ".json")
    if os.path.exists(cj):
        try:
            c = json.load(open(cj, encoding="utf8")); return c["dur"], [tuple(x) for x in c["parados"]]
        except (ValueError, KeyError): pass
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", arq], capture_output=True, text=True)
    try: dur = float(r.stdout.strip())
    except ValueError: dur = 0.0
    r = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-nostats", "-i", arq, "-an", "-vf", f"scale=180:-2,freezedetect=n=0.003:d={PARADO_MIN}",
                        "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    ini, par = None, []
    for ln in r.stderr.splitlines():
        if "freeze_start:" in ln: ini = float(ln.rsplit("freeze_start:", 1)[1].split()[0])
        elif "freeze_end:" in ln and ini is not None: par.append((round(ini, 3), round(float(ln.rsplit("freeze_end:", 1)[1].split()[0]), 3))); ini = None
    if ini is not None: par.append((round(ini, 3), round(dur, 3)))
    os.makedirs(CACHE_PARADOS, exist_ok=True)
    json.dump({"arquivo": os.path.basename(arq), "dur": dur, "parados": par}, open(cj, "w", encoding="utf8"))
    return dur, par


def saltos_da_fonte(arq):
    """Saltos internos (corte, pulo de cena) de um clipe de origem, em s. Mesmo detector do lascas.py (diferença entre
    quadros > 12 e > 3x a mediana de ±0,5 s), sem a faixa da legenda. Cache por hash do conteúdo em _FLUXO/cache/saltos_fonte."""
    if not arq or not os.path.isfile(arq) or arq.lower().endswith((".png", ".jpg", ".jpeg", ".webp")): return []
    try: h = _hash_arq(arq)
    except OSError: return []
    cj = os.path.join(CACHE_SALTOS, h + ".json")
    if os.path.exists(cj):
        try:
            c = json.load(open(cj, encoding="utf8"))
            if c.get("v") == VERSAO_SALTOS: return c["saltos"]
        except (ValueError, KeyError): pass
    import numpy as np
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                        "-of", "csv=p=0", arq], capture_output=True, text=True)
    try: a, _, b = r.stdout.strip().split(",")[0].partition("/"); fps = float(a) / float(b or 1)
    except (ValueError, ZeroDivisionError): fps = 30.0
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", arq, "-an", "-vf", "scale=90:160,format=gray",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    sal = []
    if len(raw) >= 2 * 90 * 160:
        fr = np.frombuffer(raw[: len(raw) // 14400 * 14400], np.uint8).reshape(-1, 160, 90).astype(np.float32)
        d = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2)); J = max(3, int(round(fps / 2)))
        pico = [d[i] > 12 and d[i] > 3 * np.median(d[max(0, i - J):i + J]) for i in range(len(d))]
        # salto = pico ISOLADO (1 quadro) longe das bordas. Pico em 2+ quadros seguidos é movimento rápido (rolagem,
        # chicote; 4607 V6 S02/S03 aprovados, falsos_positivos_V6.md), não corte.
        for i in range(2, len(d) - 2):
            if pico[i] and not pico[i - 1] and not pico[i + 1] and d[i - 1] < 0.5 * d[i] and d[i + 1] < 0.5 * d[i]:
                sal.append(round((i + 1) / fps, 3))
    os.makedirs(CACHE_SALTOS, exist_ok=True)
    json.dump({"v": VERSAO_SALTOS, "arquivo": os.path.basename(arq), "fps": fps, "saltos": sal}, open(cj, "w", encoding="utf8"))
    return sal


# ---------------------------------------------------------------- aceitas
def _seg(t):
    """'mm:ss' ou 'mm:ss.d' -> (s, tolerância)."""
    m, _, s = str(t).rpartition(":"); v = float(m or 0) * 60 + float(s)
    return v, (0.15 if "." in s else 1.0)


def _aceita(e, aceitas, papel=None, ad=None):
    for a in aceitas or ():
        if a.get("ad") and ad and a["ad"] != ad: continue
        t = str(a.get("t", ""))
        if "@" in t:
            pp, _, t = t.partition("@")
            if pp != papel: continue
        elif papel and e.get("_seg_rel"): continue          # mm:ss solto vale para o AD inteiro (final), não para o segmento
        v, tol = _seg(t)
        if v - 1e-6 <= e["t"] < v + tol or abs(e["t"] - v) <= 0.15: return a
    return None


# ---------------------------------------------------------------- a trava
def conferir(planos, fps, dur_total=None, aceitas=(), saltos=True, papel=None, ad=None):
    fps = float(fps); K = fps / 30; MIN = int(round(12 * K)); q = lambda t: int(round(t * fps))
    ps = [_norm(p) for p in planos]
    vis = sorted([p for p in ps if p.get("tipo", "broll") in VIS], key=lambda p: (q(p["ini"]), q(p["fim"])))
    erros = []

    def err(kind, t, p, msg, fix):
        erros.append({"tipo": kind, "t": round(t, 3), "mmss": mmss(t), "fonte": _nome(p) if p else "-", "msg": msg, "correcao": fix})

    # buraco e sobreposição
    pos = 0
    for p in vis:
        a, b = q(p["ini"]), q(p["fim"])
        if a > pos: err("buraco", pos / fps, p, f"buraco de {a - pos} quadro(s) antes de {_nome(p)}", "estique a cena anterior ou comece esta antes")
        elif a < pos: err("sobreposição", a / fps, p, f"{_nome(p)} começa {pos - a} quadro(s) antes do fim do plano anterior", "comece no fim da anterior")
        pos = max(pos, b)
    # 1 quadro no fim é arredondamento do áudio (encurta_pausas; M2WK2B3 V3, 19/11/2026): o montar estica o último quadro
    # (tpad clone). Só 2+ quadros sem plano são buraco.
    if dur_total is not None and vis and q(dur_total) - pos > 1:
        err("buraco", pos / fps, vis[-1], f"{q(dur_total) - pos} quadro(s) sem plano no fim", "estique o último plano até o fim")
    # curto / A-B-A / corte duplo
    for i, p in enumerate(vis):
        n = q(p["fim"]) - q(p["ini"])
        if n <= 0 or n >= MIN: continue
        dm = p.get("dur_min")
        if dm is not None and float(dm) >= n / fps - 1e-6: continue
        ant = vis[i - 1] if i else None; dep = vis[i + 1] if i + 1 < len(vis) else None
        if ant and dep and ant["fonte"] == dep["fonte"]:
            err("A-B-A", p["ini"], p, f"{n} quadros de {_nome(p)} entre dois planos de {_nome(ant)}",
                f"a {_nome(ant)} cobre o trecho (ou {_nome(p)} ganha {MIN - n} quadros)")
        elif p.get("tipo") == "avatar" and ant and dep and (ant.get("tipo") == "broll") != (dep.get("tipo") == "broll"):
            err("corte duplo", p["ini"], p, f"corte do b-roll a {n} quadros da emenda da fala ({_nome(p)})",
                "o corte do b-roll vai para a emenda (estique ou encurte o b-roll até ela)")
        else:
            err("curto", p["ini"], p, f"plano de {n} quadros (< {MIN})", "tome tempo das vizinhas ou junte com a anterior")
    # avatar no início
    if len(vis) > 1 and vis[0].get("tipo") == "avatar" and vis[1].get("tipo") == "broll":
        n = q(vis[0]["fim"]) - q(vis[0]["ini"])
        if 0 < n < q(0.5) and n >= MIN:
            err("avatar 0", 0.0, vis[0], f"{n} quadros de avatar antes do 1º insert", f"{_nome(vis[1])} começa em 0")
    # fonte repetida (mesmo trecho 2x) e salto do clipe de origem
    usados = {}
    for p in vis:
        if p.get("tipo") != "broll" or p.get("src_ini") is None: continue
        s0 = float(p["src_ini"]); s1 = float(p.get("src_fim", s0 + p["fim"] - p["ini"]))
        for (o0, o1, op) in usados.get(p["fonte"], []):
            ov = min(s1, o1) - max(s0, o0)
            if ov > 1.5 / fps:
                err("repetida", p["ini"], p, f"{ov:.2f} s do clipe {_nome(p)} já usados em {mmss(op['ini'])}",
                    "desacelere até ~0,6x ou use outro clipe/trecho")
        usados.setdefault(p["fonte"], []).append((s0, s1, p))
        if saltos:
            for t in saltos_da_fonte(p["fonte"]) if isinstance(p["fonte"], str) else []:
                if s0 + 1.0 / fps < t < s1 - 1.0 / fps:
                    err("salto", p["ini"] + (t - s0), p, f"o trecho {s0:.2f}-{s1:.2f} s de {_nome(p)} passa pelo salto do clipe em {t:.2f} s",
                        "use o trecho antes ou depois do salto (inicio/dur_max) ou aceite com motivo")
    # hook parado (Fefo, 19/11/2026: "Os hooks tem que ter movimento"): mede a FONTE de cada b-roll dos primeiros HOOK_ATE s
    if HOOK_ATE > 0 and (not papel or str(papel).lower().startswith("hook")):
        for p in vis:
            if p.get("tipo") != "broll" or p["ini"] >= HOOK_ATE or not isinstance(p.get("fonte"), str): continue
            # zoom só quando o ref faz (Fefo, 19/11/2026: "zoom só quando o ref faz"): plano com zoom declarado passa se
            # a trava do ref marcou REF_ZOOM=1 (trava_ref.marca_zoom); sem isso, punch-in não conta como movimento
            if (p.get("zoom") or p.get("movimento")) and os.environ.get("REF_ZOOM") == "1": continue
            if p.get("kenburns"): continue           # imagem com Ken Burns (TS): o motor sempre move a imagem
            ini, fim = float(p["ini"]), min(float(p["fim"]), HOOK_ATE)
            if p.get("src_ini") is None:
                if str(p["fonte"]).lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    err("hook parado", ini, p, f"imagem parada no hook ({_nome(p)})", "troque por vídeo com movimento (punch-in não vale: extinto em 19/11/2026)")
                continue
            s0 = float(p["src_ini"]); s1t = float(p.get("src_fim", s0 + p["fim"] - p["ini"]))
            vel = (s1t - s0) / max(1e-6, float(p["fim"]) - float(p["ini"])); s1 = s0 + (fim - ini) * vel
            dur, para = parados_da_fonte(p["fonte"])
            if dur and s1 > dur + PARADO_MIN:
                err("hook parado", ini + (dur - s0) / max(vel, 1e-6), p, f"o plano pede {s1 - dur:.2f} s além do fim de {_nome(p)} (o resto fica congelado)",
                    "corte o plano no fim da fonte, desacelere o clipe ou use outro clipe")
            for a, b in para:
                ov = min(s1, b) - max(s0, a)
                if ov >= PARADO_MIN:
                    err("hook parado", ini + (max(s0, a) - s0) / max(vel, 1e-6), p, f"{ov:.2f} s sem movimento em {_nome(p)} (fonte {max(s0, a):.2f}-{min(s1, b):.2f} s)",
                        "use outro trecho do clipe ou outra cena (punch-in não vale: extinto em 19/11/2026)")
    if papel:
        for e in erros: e["_seg_rel"] = True
    fica, ok = [], []
    for e in erros:
        a = _aceita(e, aceitas, papel, ad)
        (ok if a else fica).append((e, a))
    for e, a in ok: print(f"   trava: aceito {e['mmss']} {e['tipo']} ({a.get('motivo', '')})")
    return [e for e, _ in fica]


def recusar(erros, onde):
    """Imprime e sai com código 3 se houver erro."""
    if not erros: return
    print(f"\nTRAVA DA LINHA DO TEMPO: {onde} não renderiza ({len(erros)} erro(s))")
    for e in erros:
        print(f"  {e['mmss']}  {e['tipo']:12s} {e['fonte']}: {e['msg']}\n             correção: {e['correcao']}")
    print("  Escape (só com motivo): py \"G:/Meu Drive/@CLIENTES/_FLUXO/scripts/checagens/trava_timeline.py\" aceitar "
          "<plano.json|job.json> <mm:ss|segmento@mm:ss> \"<motivo>\" [--ad <AD>]")
    raise SystemExit(3)


def trava(planos, fps, onde, dur_total=None, aceitas=(), papel=None, ad=None):
    if os.environ.get("TRAVA_TIMELINE") == "0":
        print("   trava da linha do tempo DESLIGADA (TRAVA_TIMELINE=0)"); return []
    if os.environ.get("TRAVA_VER"):
        vis = [p for p in map(_norm, planos) if p.get("tipo", "broll") in VIS]
        print(f"   trava {onde}: {len(vis)} planos, {len(vis) - 1} cortes, {dur_total or 0:.2f} s")
        if os.environ["TRAVA_VER"] == "2":
            for p in vis: print(f"      {mmss(p['ini'])}-{mmss(p['fim'])} {round((p['fim'] - p['ini']) * fps):4d}q {p['tipo']:6s} {_nome(p)}")
    e = conferir(planos, fps, dur_total, aceitas, papel=papel, ad=ad); recusar(e, onde); return e


def deslocar(planos, ofs):
    out = []
    for p in planos:
        p = _norm(p); p["ini"] += ofs; p["fim"] += ofs; out.append(p)
    return out


def de_quadros(lab, fps):
    """Lista por quadro [(fonte, tipo, src_ini_do_quadro, extra)] -> planos (run-length)."""
    out = []
    for k, x in enumerate(lab):
        if x is None: continue
        f, t, s, ex = x
        if out and out[-1]["_k"] == k and out[-1]["fonte"] == f and out[-1]["tipo"] == t and out[-1].get("_id") == ex.get("_id"):
            out[-1]["fim"] = (k + 1) / fps; out[-1]["src_fim"] = None if s is None else s + 1 / fps; out[-1]["_k"] = k + 1; continue
        out.append({"ini": k / fps, "fim": (k + 1) / fps, "fonte": f, "tipo": t, "src_ini": s,
                    "src_fim": None if s is None else s + 1 / fps, "_k": k + 1, **ex})
    for p in out: p.pop("_k", None)
    return out


# ---------------------------------------------------------------- CLI
def _aceitar(arq, t, motivo, ad=None):
    d = json.load(open(arq, encoding="utf8")); alvo = d
    lst = alvo.setdefault("aceitar_lasca", [])
    lst.append({"t": t, "motivo": motivo, **({"ad": ad} if ad else {})})
    json.dump(d, open(arq, "w", encoding="utf8"), ensure_ascii=False, indent=1)
    print(f"aceito {t} em {arq}: {motivo}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: print(__doc__); sys.exit(0)
    if a[0] == "aceitar":
        ad = a[a.index("--ad") + 1] if "--ad" in a else None
        _aceitar(a[1], a[2], a[3], ad); sys.exit(0)
    if a[0] == "saltos":      # registra os saltos internos de clipes (REUSE do banco ou geração); cache por hash
        for f in a[1:]: print(f"{os.path.basename(f)}: saltos {saltos_da_fonte(f)}")
        sys.exit(0)
    if a[0] == "json":
        fps = float(a[a.index("--fps") + 1]) if "--fps" in a else 30
        e = conferir(json.load(open(a[1], encoding="utf8")), fps)
        for x in e: print(x)
        sys.exit(3 if e else 0)
    print("ev/ts/tu: rode pelo motor (fluxo.py trava <batch> | montagem_base.trava_job | take_unico) ou veja o cabeçalho")
