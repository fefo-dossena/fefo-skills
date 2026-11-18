#!/usr/bin/env python3
"""Revisão expressa (Fefo, 18/11/2026): liga cada nota da revisão ao segmento, ao plano e à legenda, e diz o caminho.

  notas_segmento.py <batch|job> --versao K [--todas] [--sem-gravar]

Lê <roteiro>/revisao_V<K>.md (gerado pelo notas_revisao.py gerar) e a linha do tempo que a montagem já gravou:
  Empire Vision: <auto>/broll_posicoes_AD<n>_<marca>.json + plano.json (cenas), ou linha_do_tempo_<marca>.json (por segmentos);
                 legenda de <auto>/legendas/AD<n>_<marca>.srt.
  Trendscale:    <auto>/planos_Hook<n>.json (ou planos_h<n>.json) + segmentos.json (duração de cada hook).
Para cada nota diz: segmento (hook<n>, hold/corpo ou vídeo inteiro), plano no tempo da nota (id, início–fim, arquivo),
legenda na tela e a classe: MECÂNICO (pausa, volume, posição ou digitação da legenda: sai sem sala, regra
"Ajuste mecânico sai sem sala" de REGRAS_DA_SESSAO.md), SALA (troca de clipe, regeração, roteiro, estilo) ou
VER (não reconheci: na dúvida, sala). No fim: segmentos a remontar, vídeos a exportar e o caminho da versão.
Grava <auto>/notas_segmento_V<K>.md e .json. Não muda o revisao_V<K>.md, não monta e não escreve no cliente.
A classe é uma sugestão por palavra-chave: quem decide é a sessão, lendo a nota.
Sem --todas, o resumo conta só as notas abertas ([ ]); se não há nota aberta, conta todas.
"""
import argparse, glob, json, os, re, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import checklist as CK  # noqa: E402

MECANICO = [r"\bpauses?\b", r"dead ?space", r"too slow", r"speed (it )?up", r"lower (the )?music", r"music (is )?too loud",
            r"\blouder\b", r"\bvolume\b", r"4:5", r"\b1:1\b", r"(put|move|shift) (the )?(text|caption|sub)", r"shift them",
            r"over (his|her|the) (face|eyes)", r"captions? (are|is) over", r"\btypo\b", r"spell", r"match the subs",
            r"subs? with the vo", r"not following the vo", r"\bsync", r"file ?name", r"\brename\b"]
SALA = [r"\bstills?\b", r"\bai\b", r"terrible", r"b[- ]?rolls?", r"\breplace\b", r"\bredo\b", r"\bvoice\b", r"\bvo\b.*(quality|bad|real|redo|robot|messed)", r"(quality|bad|redo).*\bvo\b",
        r"glitch", r"weird", r"quality", r"\bscript\b", r"\bblood\b", r"\bshow\b", r"\bscenes?\b", r"\bproduct\b", r"pixar",
        r"natural", r"repeat", r"\blazy\b", r"\bcolou?r\b", r"emotion", r"\bangle\b", r"add (bg |background )?music",
        r"text looks", r"\bfake\b", r"\bfiller\b", r"doesn'?t make (much )?sense", r"\bhook\b", r"accent"]


def classe(texto):
    t = texto.lower()
    s = [p for p in SALA if re.search(p, t)]
    m = [p for p in MECANICO if re.search(p, t)]
    if s: return "SALA", s[0]
    if m: return "MECÂNICO", m[0]
    return "VER", ""


def seg_t(s):
    m = re.match(r"(?:(\d+):)?(\d+(?:\.\d+)?)$", s.strip())
    return (int(m[1] or 0) * 60 + float(m[2])) if m else 0.0


def mmss(t): return f"{int(t // 60)}:{t % 60:05.2f}"


def ler_json(p):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return None


def ler_srt(p):
    out = []
    try: txt = open(p, encoding="utf-8-sig").read()
    except Exception: return out
    for b in re.split(r"\r?\n\r?\n", txt):
        m = re.search(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)\s*\r?\n(.+)", b, re.S)
        if m:
            g = [int(x) for x in m.groups()[:8]]
            out.append((g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000, g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000,
                        " ".join(m[9].split())))
    return out


def linha_ev(B, auto, n):
    """Linha do tempo de um AD da Empire Vision: (planos [(id, t0, t1, fonte, papel)], fim do hook, legendas, origem)."""
    A = os.path.join(B, auto); plano = ler_json(os.path.join(A, "plano.json")) or {}
    cenas = {c.get("id"): c for c in plano.get("cenas", []) if isinstance(c, dict)}
    pos = sorted(glob.glob(os.path.join(A, f"broll_posicoes_AD{n}_*.json")))
    planos, fim_hook, origem = [], None, None
    if pos:
        origem = os.path.basename(pos[0])
        for it in ler_json(pos[0]) or []:
            cid, t0, t1 = it[0], float(it[1]), float(it[2]); c = cenas.get(cid) or cenas.get(str(cid).split("-")[0] + "-01") or {}
            papel = "hook" if (c.get("tipo") == "hook" or re.match(r"H\d", str(cid))) else "hold"
            planos.append((cid, t0, t1, it[3] if len(it) > 3 else "", papel))
        hold = [p[1] for p in planos if p[4] == "hold"]
        fim_hook = min(hold) if hold else None
    else:
        ldt = sorted(glob.glob(os.path.join(A, "linha_do_tempo_*.json")))
        d = ler_json(ldt[0]) if ldt else None
        if d:
            origem = os.path.basename(ldt[0]); fim_hook = float(d.get("hook_dur") or 0)
            cs = d.get("cenas") or []
            for (cid, t0), (_, t1) in zip(cs, cs[1:]):
                planos.append((cid, fim_hook + float(t0), fim_hook + float(t1), "", "hold"))
    marca = re.search(r"_AD\d+_(.+)\.json$", pos[0])[1] if pos else None
    leg = ler_srt(os.path.join(A, "legendas", f"AD{n}_{marca}.srt")) if marca else []
    if not leg:
        ldt = sorted(glob.glob(os.path.join(A, "linha_do_tempo_*.json")))
        d = ler_json(ldt[0]) if ldt else None
        leg = [(float(a), float(b), c) for a, b, c in (d or {}).get("legenda", [])]
    return planos, fim_hook, leg, origem


def linha_ts(B, auto, n):
    A = os.path.join(B, auto)
    arq = next((p for p in (os.path.join(A, f"planos_Hook{n}.json"), os.path.join(A, f"planos_h{n}.json")) if os.path.exists(p)), None)
    planos = []
    for it in (ler_json(arq) or []) if arq else []:
        if isinstance(it, dict) and "start" in it:
            planos.append((it.get("nome") or it.get("arq") or str(it.get("n", "")), float(it["start"]), float(it["end"]),
                           it.get("fonte") or it.get("arq") or "", "?"))
    seg = (ler_json(os.path.join(A, "segmentos.json")) or {}).get("segmentos", {})
    fim_hook = next((float(s["dur"]) for s in seg.values() if s.get("papel") == f"hook{n}" and s.get("dur")), None)
    return planos, fim_hook, [], (os.path.basename(arq) if arq else None)


def videos_do_job(B, P, ev):
    """Nomes curtos dos vídeos do job (AD1.. ou Hook1..), para saber quem divide a hold ou o corpo."""
    A = os.path.join(B, P["auto"])
    if ev:
        ns = sorted({int(m[1]) for p in glob.glob(os.path.join(A, "broll_posicoes_AD*_*.json")) for m in [re.search(r"AD(\d+)_", p)] if m})
        if not ns:
            hooks = (ler_json(os.path.join(A, "plano.json")) or {}).get("hooks") or {}
            ns = sorted(int(k) for k in hooks if str(k).isdigit())
        return [f"AD{n}" for n in ns]
    ns = sorted({int(m[1]) for p in glob.glob(os.path.join(A, "planos_*.json")) for m in [re.search(r"planos_(?:Hook|h)(\d+)\.json$", p)] if m})
    return [f"Hook{n}" for n in ns]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("batch"); ap.add_argument("--versao", required=True); ap.add_argument("--todas", action="store_true")
    ap.add_argument("--sem-gravar", action="store_true", help="só mostra (teste em job entregue)")
    a = ap.parse_args()
    B = os.path.abspath(a.batch); P = CK.pastas_de(CK.ficha_de(B)); k = int(str(a.versao).lstrip("Vv"))
    ev = P["auto"] == "08_auto"; corpo = "hold" if ev else "corpo"
    arq = os.path.join(B, P["roteiro"], f"revisao_V{k}.md")
    if not os.path.exists(arq):
        print(f"não existe {arq}: rode antes o notas_revisao.py gerar", file=sys.stderr); return 2
    todos = videos_do_job(B, P, ev); cache, notas = {}, []
    for ln in open(arq, encoding="utf-8"):
        m = re.match(r"\s*[-*]\s*\[( |x|X)\]\s*(\S+)\s+([\d:.]+)\s*·\s*(.*)", ln)
        if not m: continue
        partes = m[4].split(" · "); texto = partes[0].strip()
        vid, t = m[2], seg_t(m[3]); num = re.search(r"(\d+)$", vid)
        n = int(num[1]) if num else None
        if n is not None and n not in cache: cache[n] = (linha_ev if ev else linha_ts)(B, P["auto"], n)
        planos, fim_hook, leg, origem = cache.get(n, ([], None, [], None))
        cl, por = classe(texto)
        geral = n is None or (t == 0 and cl != "VER" and re.search(r"too slow|pauses?|music|voice|\bvo\b|overall|whole", texto.lower()))
        if geral: seg = "vídeo inteiro"
        elif fim_hook is None: seg = f"hook{n} ou {corpo} (sem linha do tempo: conferir)"
        else: seg = f"hook{n}" if t < fim_hook - 1e-3 else corpo
        pl = next((p for p in planos if p[1] - 1e-3 <= t < p[2]), None) if not geral else None
        if pl: plano_txt = f"{pl[0]} {mmss(pl[1])}–{mmss(pl[2])}" + (f" · {os.path.basename(str(pl[3]))}" if pl[3] else "")
        elif geral: plano_txt = "todos"
        elif planos and ev: plano_txt = "avatar (fala), sem b-roll por cima"
        else: plano_txt = "não achei"
        lg = next((c for a0, b0, c in leg if a0 - 1e-3 <= t < b0), "") if not geral else ""
        if seg == "vídeo inteiro": alcance = todos or [vid]
        elif seg == corpo: alcance = todos or [vid]
        else: alcance = [vid]
        notas.append({"aberta": m[1] == " ", "video": vid, "t": round(t, 2), "nota": texto, "segmento": seg, "plano": plano_txt,
                      "legenda": lg, "classe": cl, "por": por, "exportar": alcance, "linha_do_tempo": origem})
    if not notas:
        print(f"nenhuma nota em {arq}"); return 1
    conta = [x for x in notas if x["aberta"]] if not a.todas else notas
    quais = "abertas"
    if not conta: conta, quais = notas, "todas (nenhuma aberta)"
    elif a.todas: quais = "todas"
    segs = sorted({(f"{corpo}" if x["segmento"] == corpo else x["segmento"]) for x in conta})
    exportar = sorted({v for x in conta for v in x["exportar"]})
    classes = {x["classe"] for x in conta}
    if classes == {"MECÂNICO"}: caminho = "SEM SALA: só ajuste mecânico. Remonte os segmentos, mande o antes e depois ao Fefo e peça o ok da entrega."
    elif "SALA" in classes: caminho = "SALA: há nota que muda clipe, voz, roteiro ou estilo."
    else: caminho = "SALA (na dúvida): há nota que não reconheci. Leia e decida."
    L = [f"# Notas por segmento · V{k} · {os.path.basename(B)}", "",
         f"Fonte: `{os.path.relpath(arq, B).replace(os.sep, '/')}`. A classe é sugestão por palavra-chave; leia a nota antes de seguir.", "",
         "| Nota | Vídeo e tempo | Segmento | Plano no tempo da nota | Legenda na tela | Classe | Estado |", "|---|---|---|---|---|---|---|"]
    for x in notas:
        L.append(f"| {x['nota'].replace('|', '/')} | {x['video']} {mmss(x['t'])} | {x['segmento']} | {x['plano'].replace('|', '/')} | "
                 f"{x['legenda'].replace('|', '/') or '—'} | {x['classe']} | {'aberta' if x['aberta'] else 'feita'} |")
    L += ["", f"## Resumo (notas {quais}: {len(conta)})", f"- Remontar: {', '.join(segs)}", f"- Exportar: {', '.join(exportar)}"
          + (" (cada marca)" if ev else ""), f"- Caminho: {caminho}", ""]
    print("\n".join(L))
    if a.sem_gravar: return 0
    saida = os.path.join(B, P["auto"], f"notas_segmento_V{k}")
    open(saida + ".md", "w", encoding="utf-8").write("\n".join(L))
    json.dump({"versao": k, "notas": notas, "remontar": segs, "exportar": exportar, "caminho": caminho.split(":")[0]},
              open(saida + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"gravei {saida}.md e .json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
