#!/usr/bin/env python3
"""Lista de notas da revisão (item 6 do checklist da Louise; Frente 4, 13/11/2026). Serve aos dois clientes.

  notas_revisao.py gerar <batch> --versao K --comentarios <arquivo.json> [--fps 30] [--forcar]
      Escreve <roteiro>/revisao_V<K>.md (EV: 00_roteiro; TS: 00_briefing), uma linha por nota:
        - [ ] AD1 0:07.07 · "deadspace" · vou mudar: ... · prova:
      <arquivo.json> = lista de {"arquivo": nome do vídeo no Frame.io, "t": segundos | "quadro": n, "texto": ..., "autor": ...}.
      Empire Vision: `frameio.py comentarios <pasta> --revisao <batch>` gera o json e chama este comando.
      Trendscale: ler os comentários pelo conector FrameTS (read_comments), gravar o json no $TMPDIR e rodar este comando.
      Nota que já apareceu antes (preferências do revisor do cliente) sai marcada: na 2ª vez vira checagem ou regra.
      Sem --forcar, não sobrescreve um revisao_V<K>.md que já existe (acrescenta só as notas novas).
  notas_revisao.py respostas <batch> --versao K
      Texto da resposta de cada nota (em inglês, para o Frame.io), a partir do "mudei:" de cada linha marcada [x].
      Grava <roteiro>/revisao_V<K>_respostas.md. Postar no Frame.io só com ok do Fefo.

Antes de mandar a versão nova ao Fefo, cada linha precisa de [x] e de "prova: <quadro da versão nova>"; o checklist
(item 6) fica vermelho até lá, e a sala e a entrega travam.
"""
import argparse, datetime, json, os, re, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import checklist as CK  # noqa: E402


def mmss(t): return f"{int(t // 60)}:{t % 60:05.2f}"


def preferencias(ficha):
    """[(palavras-chave, linha)] do arquivo de preferências do revisor do cliente (ficha checklist.preferencias)."""
    rel = (ficha or {}).get("checklist", {}).get("preferencias")
    if not rel: return []
    arq = os.path.join(os.path.dirname(os.path.dirname(CK.NUCLEO)), rel)
    if not os.path.exists(arq): return []
    out = []
    for ln in open(arq, encoding="utf-8"):
        m = re.match(r"\s*-\s*`([^`]+)`\s*·\s*(.+)", ln)
        if m: out.append(([k.strip().lower() for k in m[1].split(",") if k.strip()], m[2].strip()))
    return out


def ja_apareceu(texto, prefs):
    t = texto.lower()
    return [linha for chaves, linha in prefs if any(k in t for k in chaves)]


def ad_de(nome):
    m = re.search(r"(?:AD|Hook)\s*_?(\d+)", nome or "", re.I)
    return f"AD{m[1]}" if m and re.search(r"AD", nome, re.I) else (f"Hook{m[1]}" if m else "todos")


def arquivo_notas(B, P, k): return os.path.join(B, P["roteiro"], f"revisao_V{k}.md")


def gerar(a):
    B = os.path.abspath(a.batch); ficha = CK.ficha_de(B) or (CK._fichas().get(a.cliente) if a.cliente else None); P = CK.pastas_de(ficha)
    k = int(str(a.versao).lstrip("Vv")); arq = arquivo_notas(B, P, k)
    coms = json.load(open(a.comentarios, encoding="utf-8"))
    prefs = preferencias(ficha)
    linhas = []
    for c in sorted(coms, key=lambda c: (ad_de(c.get("arquivo")), c.get("t") or (c.get("quadro") or 0) / a.fps)):
        t = c.get("t")
        if t is None and c.get("quadro") is not None: t = float(c["quadro"]) / a.fps
        txt = re.sub(r"\s+", " ", str(c.get("texto", ""))).strip()
        if not txt: continue
        rep = ja_apareceu(txt, prefs)
        marca = (" · JÁ APARECEU (" + re.sub(r"[`·|]", "", rep[0])[:70] + "): vira checagem ou regra") if rep else ""
        linhas.append(f"- [ ] {ad_de(c.get('arquivo'))} {mmss(t or 0)} · \"{txt}\"{' (' + c['autor'] + ')' if c.get('autor') else ''}{marca} · "
                      f"vou mudar: ? · mudei: ? · prova:")
    existentes = open(arq, encoding="utf-8").read() if os.path.exists(arq) and not a.forcar else ""
    novas = [l for l in linhas if l.split(" · JÁ APARECEU")[0].split(" · vou mudar")[0].split("] ", 1)[1] not in existentes]
    os.makedirs(os.path.dirname(arq), exist_ok=True)
    if existentes:
        open(arq, "a", encoding="utf-8").write(("\n" + "\n".join(novas) + "\n") if novas else "")
    else:
        cab = [f"# Notas da revisão V{k} · {os.path.basename(B)} ({datetime.date.today():%d/%m/%Y})", "",
               "Uma linha por nota do revisor (Frame.io e card). Nota vaga (\"still\", \"deadspace\"): escreva a leitura em \"vou mudar\".",
               "Antes de mandar ao Fefo: confira cada nota NA VERSÃO NOVA exportada, troque [ ] por [x], diga o que mudou em",
               "\"mudei:\" (vira a resposta no Frame.io) e ponha em \"prova:\" o caminho do quadro da versão nova (relativo à batch).",
               "Linha sem [x] ou sem prova deixa o checklist (item 6) vermelho: a sala e a entrega travam.", ""]
        open(arq, "w", encoding="utf-8").write("\n".join(cab + linhas) + "\n")
    print(f"{'acrescentei' if existentes else 'gravei'} {arq} ({len(novas) if existentes else len(linhas)} nota(s))")
    rep = [l for l in linhas if "JÁ APARECEU" in l]
    if rep:
        print(f"{len(rep)} nota(s) já apareceram antes: pela regra, cada uma vira checagem ou regra fixa (preferências do revisor).")
    return 0


def respostas(a):
    B = os.path.abspath(a.batch); ficha = CK.ficha_de(B) or (CK._fichas().get(a.cliente) if a.cliente else None); P = CK.pastas_de(ficha)
    k = int(str(a.versao).lstrip("Vv")); arq = arquivo_notas(B, P, k)
    if not os.path.exists(arq): print(f"não existe {arq}", file=sys.stderr); return 2
    out, falta = [], []
    for ln in open(arq, encoding="utf-8"):
        m = re.match(r"\s*[-*]\s*\[( |x|X)\]\s*(\S+)\s+([\d:.]+)\s*·\s*\"(.*?)\"", ln)
        if not m: continue
        mud = re.search(r"mudei:\s*(.+?)\s*(?:·|$)", ln)
        mud = mud[1].strip() if mud and mud[1].strip() not in ("?", "") else None
        if m[1] == " " or not mud:
            falta.append(f"{m[2]} {m[3]} \"{m[4]}\""); continue
        out.append(f"- {m[2]} {m[3]} · nota: \"{m[4]}\"\n  Resposta: Fixed in V{k}: {mud}")
    dst = os.path.join(os.path.dirname(arq), f"revisao_V{k}_respostas.md")
    open(dst, "w", encoding="utf-8").write(f"# Respostas para o Frame.io · V{k} (postar só com ok do Fefo)\n\n" + "\n".join(out) + "\n")
    print(f"gravei {dst} ({len(out)} resposta(s))")
    if falta:
        print(f"{len(falta)} nota(s) sem [x] ou sem \"mudei:\": " + "; ".join(falta[:6]))
        return 1
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    g = sp.add_parser("gerar"); g.add_argument("batch"); g.add_argument("--versao", required=True)
    g.add_argument("--comentarios", required=True); g.add_argument("--fps", type=float, default=30.0); g.add_argument("--forcar", action="store_true"); g.add_argument("--cliente")
    r = sp.add_parser("respostas"); r.add_argument("batch"); r.add_argument("--versao", required=True); r.add_argument("--cliente")
    a = ap.parse_args()
    return gerar(a) if a.cmd == "gerar" else respostas(a)


if __name__ == "__main__":
    sys.exit(main())
