#!/usr/bin/env python3
"""Relógio do job e chamada do Fefo (Fefo, 18/11/2026). Serve à Empire Vision e à Trendscale.

Meta: no máximo 2 h de TRABALHO por sessão em tarefa de vídeo. O relógio PARA enquanto a sessão espera o Fefo
("sim, o relogio para enquanto me espera"). Toda espera vira uma chamada numa lista que o MacBook dele vigia, porque a
notificação das sessões do PC não chega lá.

  py relogio.py passo  <pasta do job> "<nome do passo>" [--min N]   # começa um passo (fecha o anterior); N = orçamento em minutos
  py relogio.py espera <pasta do job> "<o que preciso do Fefo>" [--tipo plano|elenco|previa|entrega|credito|duvida|travou]
                                                                    # para o relógio e abre a chamada; imprime a linha do push
  py relogio.py voltou <pasta do job>                               # o Fefo respondeu: fecha a chamada e o relógio volta a andar
  py relogio.py fim    <pasta do job>                               # sessão fechou (entrega feita ou etapa fechada)
  py relogio.py status [<pasta do job>] [--orcamento 120]           # trabalho, espera e cada passo contra o orçamento
  py relogio.py abertas                                             # quem espera o Fefo agora, e há quanto tempo

Onde grava:
  <job>/<auto>/tempo.jsonl          uma linha por evento (auto = 08_auto na EV, 06_auto na TS; sem elas, a pasta do job)
  _FLUXO/chamadas/abertas.json      chamadas abertas (todas as sessões)
  _FLUXO/chamadas/abertas.tsv       a mesma lista em texto simples: é o que o vigia do Mac lê (chamadas/vigia_mac.sh)
  _FLUXO/chamadas/ABERTAS.md        a mesma lista para ler no Drive, no celular ou no Mac
A pasta chamadas/ fica no Drive, então chega ao MacBook pela sincronização (em geral menos de 1 min).

Depois do `espera`, a sessão também manda um PushNotification com a linha impressa (celular) e segue com o que não
depende do Fefo. Não é para avisar progresso de rotina: chamada = a sessão parou e precisa dele.
"""
import argparse, datetime, json, os, sys, time

AQUI = os.path.dirname(os.path.abspath(__file__))
CHAMADAS = os.environ.get("CHAMADAS_DIR") or os.path.normpath(os.path.join(AQUI, "..", "chamadas"))
ORCAMENTO = 120
TIPOS = ("plano", "elenco", "previa", "entrega", "credito", "duvida", "travou")


def agora(): return datetime.datetime.now().replace(microsecond=0)


def nome_job(job): return os.path.basename(os.path.abspath(job).rstrip("/\\")).split(" - ")[0]


def arq_tempo(job):
    job = os.path.abspath(job)
    for a in ("08_auto", "06_auto"):
        if os.path.isdir(os.path.join(job, a)): return os.path.join(job, a, "tempo.jsonl")
    return os.path.join(job, "tempo.jsonl")


def eventos(job):
    arq = arq_tempo(job)
    if not os.path.exists(arq): return []
    out = []
    for ln in open(arq, encoding="utf-8"):
        try: out.append(json.loads(ln))
        except ValueError: pass
    return out


def grava(job, ev, **kw):
    if not os.path.isdir(os.path.abspath(job)):
        sys.exit(f"relogio: a pasta do job não existe: {job}")
    reg = dict({"t": agora().isoformat(), "ev": ev}, **kw)
    with open(arq_tempo(job), "a", encoding="utf-8") as f: f.write(json.dumps(reg, ensure_ascii=False) + "\n")
    return reg


def conta(evs, ate=None):
    """Soma o trabalho e a espera. Devolve (trabalho_s, espera_s, passos [(nome, s, orçamento_min)], estado, passo atual)."""
    ate = ate or agora()
    trab = esp = 0.0; passos = []; estado = "parado"; ult = None; atual = None
    def anda(t):
        nonlocal trab, esp
        if ult is None: return
        d = max(0.0, (t - ult).total_seconds())
        if estado == "andando":
            trab += d
            if passos: passos[-1][1] += d
        elif estado == "esperando": esp += d
    for e in evs:
        t = datetime.datetime.fromisoformat(e["t"]); anda(t); ult = t
        if e["ev"] == "passo":
            atual = e.get("passo"); passos.append([atual, 0.0, e.get("min")]); estado = "andando"
        elif e["ev"] == "espera": estado = "esperando"
        elif e["ev"] == "voltou": estado = "andando" if atual else "parado"
        elif e["ev"] == "fim": estado = "fechado"
    if estado in ("andando", "esperando"): anda(ate)
    return trab, esp, [tuple(p) for p in passos], estado, atual


def hm(s):
    m = int(round(s / 60)); return f"{m // 60}h{m % 60:02d}" if m >= 60 else f"{m} min"


# ---------------------------------------------------------------- chamadas (lista única, no Drive)
class Trava:
    def __init__(self): self.arq = os.path.join(CHAMADAS, ".trava")
    def __enter__(self):
        os.makedirs(CHAMADAS, exist_ok=True); t0 = time.time()
        while True:
            try:
                os.close(os.open(self.arq, os.O_CREAT | os.O_EXCL | os.O_WRONLY)); return self
            except FileExistsError:
                if time.time() - t0 > 20 or (os.path.exists(self.arq) and time.time() - os.path.getmtime(self.arq) > 60):
                    try: os.remove(self.arq)
                    except OSError: pass
                time.sleep(0.2)
    def __exit__(self, *a):
        try: os.remove(self.arq)
        except OSError: pass


def le_abertas():
    try: return json.load(open(os.path.join(CHAMADAS, "abertas.json"), encoding="utf-8"))
    except (OSError, ValueError): return {}


def grava_abertas(ab):
    def troca(nome, txt):
        tmp = os.path.join(CHAMADAS, nome + ".tmp")
        with open(tmp, "w", encoding="utf-8", newline="\n") as f: f.write(txt)
        os.replace(tmp, os.path.join(CHAMADAS, nome))
    itens = sorted(ab.items(), key=lambda kv: kv[1]["desde"])
    troca("abertas.json", json.dumps(ab, ensure_ascii=False, indent=1))
    limpa = lambda s: " ".join(str(s).replace("\t", " ").split())
    troca("abertas.tsv", "".join(f"{k}\t{v['desde'][11:16]}\t{limpa(v['job'])}\t{limpa(v['tipo'])}\t{limpa(v['texto'])}\n" for k, v in itens))
    md = ["# Quem espera o Fefo agora", "", f"Atualizado em {agora():%d/%m %H:%M}. Gerado por `_FLUXO/scripts/relogio.py`; não edite à mão.", ""]
    md += [f"- **{v['job']}** · {v['tipo']} · desde {v['desde'][11:16]} · {v['texto']}" for k, v in itens] or ["Ninguém espera."]
    troca("ABERTAS.md", "\n".join(md) + "\n")


def cmd_passo(a):
    grava(a.job, "passo", passo=a.texto, **({"min": a.min} if a.min else {}))
    print(f"relogio: {nome_job(a.job)} · passo \"{a.texto}\"" + (f" · orçamento {a.min} min" if a.min else ""))
    return cmd_status(a, curto=True)


def cmd_espera(a):
    j = nome_job(a.job); evs = eventos(a.job)
    if conta(evs)[3] != "esperando": grava(a.job, "espera", texto=a.texto, tipo=a.tipo)
    with Trava():
        ab = le_abertas()
        velha = next((k for k, v in ab.items() if v["job"] == j), None)
        k = velha or f"{j}_{agora():%Y%m%d%H%M%S}"
        ab[k] = {"job": j, "tipo": a.tipo, "texto": a.texto, "desde": (ab[velha]["desde"] if velha else agora().isoformat()), "pasta": os.path.abspath(a.job)}
        if velha:      # texto novo = chamada nova para o vigia (ele avisa de novo)
            ab[f"{j}_{agora():%Y%m%d%H%M%S}"] = ab.pop(k)
        grava_abertas(ab)
    print(f"relogio: {j} esperando o Fefo; relógio parado. Chamada aberta em {CHAMADAS}.")
    print(f"PUSH: {j}: {a.texto}"[:206])
    return 0


def cmd_voltou(a):
    j = nome_job(a.job)
    if conta(eventos(a.job))[3] == "esperando": grava(a.job, "voltou")
    with Trava():
        ab = le_abertas(); n = len(ab); ab = {k: v for k, v in ab.items() if v["job"] != j}
        if len(ab) != n: grava_abertas(ab)
    print(f"relogio: {j} · o Fefo respondeu; relógio andando.")
    return cmd_status(a, curto=True)


def cmd_fim(a):
    j = nome_job(a.job); grava(a.job, "fim")
    with Trava():
        ab = le_abertas(); n = len(ab); ab = {k: v for k, v in ab.items() if v["job"] != j}
        if len(ab) != n: grava_abertas(ab)
    return cmd_status(a)


def cmd_status(a, curto=False):
    if not getattr(a, "job", None): return cmd_abertas(a)
    evs = eventos(a.job); orc = getattr(a, "orcamento", None) or ORCAMENTO
    if not evs:
        print(f"relogio: {nome_job(a.job)} sem registro. Comece com: relogio.py passo \"<pasta>\" \"<passo>\""); return 0
    trab, esp, passos, estado, atual = conta(evs)
    sobra = orc * 60 - trab
    linha = f"relogio: {nome_job(a.job)} · trabalho {hm(trab)} de {hm(orc * 60)} · espera do Fefo {hm(esp)} · {estado}" + (f" em \"{atual}\"" if estado == "andando" and atual else "")
    print(linha)
    if not curto:
        for nome, s, m in passos:
            print(f"   {nome}: {hm(s)}" + (f" (orçamento {m} min{', PASSOU' if s > m * 60 else ''})" if m else ""))
    if sobra < 0:
        print(f"   PASSOU do orçamento em {hm(-sobra)}: pare, diga numa linha onde travou e chame o Fefo (relogio.py espera ... --tipo travou).")
    elif sobra < 20 * 60:
        print(f"   faltam {hm(sobra)}: feche o que está em curso ou chame o Fefo.")
    if passos and passos[-1][2] and estado == "andando" and passos[-1][1] > passos[-1][2] * 60:
        print(f"   o passo \"{passos[-1][0]}\" passou do orçamento dele ({passos[-1][2]} min).")
    return 0


def cmd_abertas(a):
    ab = le_abertas()
    if not ab: print("Ninguém espera o Fefo."); return 0
    for k, v in sorted(ab.items(), key=lambda kv: kv[1]["desde"]):
        d = (agora() - datetime.datetime.fromisoformat(v["desde"])).total_seconds()
        print(f"{v['job']:12} {v['tipo']:8} há {hm(d):>7} · {v['texto']}")
    return 0


def main():
    for s in (sys.stdout, sys.stderr):
        try: s.reconfigure(encoding="utf-8")
        except Exception: pass
    ap = argparse.ArgumentParser(description="Relógio do job e chamada do Fefo."); sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("passo"); p.add_argument("job"); p.add_argument("texto"); p.add_argument("--min", type=int); p.set_defaults(fn=cmd_passo)
    p = sp.add_parser("espera"); p.add_argument("job"); p.add_argument("texto"); p.add_argument("--tipo", choices=TIPOS, default="duvida"); p.set_defaults(fn=cmd_espera)
    p = sp.add_parser("voltou"); p.add_argument("job"); p.set_defaults(fn=cmd_voltou)
    p = sp.add_parser("fim"); p.add_argument("job"); p.set_defaults(fn=cmd_fim)
    p = sp.add_parser("status"); p.add_argument("job", nargs="?"); p.add_argument("--orcamento", type=int); p.set_defaults(fn=cmd_status)
    p = sp.add_parser("abertas"); p.set_defaults(fn=cmd_abertas)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
