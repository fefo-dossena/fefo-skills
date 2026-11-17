"""Alinha o texto revisado das legendas com as palavras da transcrição (faster-whisper, tempo por palavra).

O texto vem sempre do roteiro revisado; da transcrição só sai o tempo de cada palavra.
Uso como módulo: alinha(frases, palavras) → para cada frase, a lista de (palavra, início, fim).
Uso direto: python3 alinha_palavras.py <legendas.ass> <palavras.json>  → mede o atraso de cada legenda.
"""
import difflib
import json
import re
import sys

UNID = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
DEZ = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
IGUAIS = {"deck": "dick", "d***": "dick", "ball": "balls", "lentil": "leydig", "eva": "emma", "wood": "wood"}


def extenso(n):
    if n < 20:
        return [UNID[n]]
    if n < 100:
        return [DEZ[n // 10]] + ([UNID[n % 10]] if n % 10 else [])
    if n >= 1000:  # "1,206" e "30,000" (M2WK2B3, 04/11/2026)
        m, r = divmod(n, 1000)
        return extenso(m) + ["thousand"] + (extenso(r) if r else [])
    c, r = divmod(n, 100)
    return [UNID[c], "hundred"] + (extenso(r) if r else [])


def norma(texto):
    """Palavra do texto → tokens comparáveis ("90-day" → ninety day, "d***" → dick)."""
    t = texto.lower().replace("d***", "dick").replace("’", "'")
    t = re.sub(r"[-–—/]", " ", t)
    saida = []
    for p in t.split():
        p = re.sub(r"[^a-z0-9']", "", p).strip("'")
        if not p:
            continue
        if p.isdigit():
            saida += extenso(int(p))
        elif re.fullmatch(r"\d*[2-9]0s", p):        # "70s" = seventies (M1WK4B2 V6, 16/11/2026)
            e = extenso(int(p[:-1])); saida += e[:-1] + [e[-1][:-1] + "ies"]
        else:
            saida.append(IGUAIS.get(p, p))
    return saida


def alinha(frases, palavras):
    """frases: lista de textos; palavras: [[texto, início, fim, prob], ...] da transcrição."""
    roteiro = []                         # (frase, nº da palavra, palavra original, token)
    for i, f in enumerate(frases):
        for n, w in enumerate(f.split()):
            for tk in norma(w) or [""]:
                roteiro.append((i, n, w, tk))
    ouvido = []                          # (token, início, fim)
    for w, a, b, _ in palavras:
        toks = norma(w) or [""]
        passo = (b - a) / len(toks)
        for j, tk in enumerate(toks):
            ouvido.append((tk, a + j * passo, a + (j + 1) * passo))
    sm = difflib.SequenceMatcher(None, [r[3] for r in roteiro], [o[0] for o in ouvido], autojunk=False)
    tempo = [None] * len(roteiro)
    for op, a0, a1, b0, b1 in sm.get_opcodes():
        if op == "equal" or (op == "replace" and a1 - a0 == b1 - b0):
            for k in range(a1 - a0):
                tempo[a0 + k] = (ouvido[b0 + k][1], ouvido[b0 + k][2], op == "equal")
        elif op == "replace" and b1 > b0:  # tamanhos diferentes: reparte o trecho ouvido
            ini, fim = ouvido[b0][1], ouvido[b1 - 1][2]
            n = a1 - a0
            for k in range(n):
                tempo[a0 + k] = (ini + (fim - ini) * k / n, ini + (fim - ini) * (k + 1) / n, False)
    # palavra que a transcrição não ouviu: entre as vizinhas
    for k, t in enumerate(tempo):
        if t is None:
            ant = next((tempo[j][1] for j in range(k - 1, -1, -1) if tempo[j]), 0.0)
            pro = next((tempo[j][0] for j in range(k + 1, len(tempo)) if tempo[j]), ant + 0.3)
            tempo[k] = (ant, min(pro, ant + 0.3), False)
    saida, ultimo = [[] for _ in frases], None
    for k, (i, n, w, _) in enumerate(roteiro):
        if ultimo == (i, n):  # vários tokens da mesma palavra ("90-day" → ninety day): uma palavra só
            p = saida[i][-1]
            saida[i][-1] = (w, p[1], tempo[k][1], p[3] and tempo[k][2])
        else:
            saida[i].append((w, tempo[k][0], tempo[k][1], tempo[k][2]))
        ultimo = (i, n)
    return saida


def le_ass(caminho):
    def seg(t):
        h, m, s = t.split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)
    leg = []
    for linha in open(caminho, encoding="utf-8"):
        if linha.startswith("Dialogue:"):
            c = linha.rstrip("\n").split(",", 9)
            leg.append((seg(c[1]), seg(c[2]), re.sub(r"\{[^}]*\}", "", c[9]).replace(r"\N", " ")))
    return leg


if __name__ == "__main__":
    leg = le_ass(sys.argv[1])
    pal = json.load(open(sys.argv[2]))
    al = alinha([t for _, _, t in leg], pal)
    ruins = 0
    for (a, b, t), ws in zip(leg, al):
        da, db = a - ws[0][1], b - ws[-1][2]
        ok = sum(w[3] for w in ws) / len(ws)
        marca = "  <<" if abs(da) > 0.25 or db < -0.15 else ""
        ruins += bool(marca)
        print(f"{a:7.2f} ini {da:+.2f} fim {db:+.2f} ouvido {ok:.0%}  {t}{marca}")
    print(f"{ruins} de {len(leg)} legendas fora (início > 0,25 s ou somem antes do fim da fala)")
