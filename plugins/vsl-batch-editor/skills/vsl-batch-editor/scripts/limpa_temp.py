#!/usr/bin/env python3
"""Apaga do %TEMP% as pastas de trabalho de um job entregue (Fefo, 24/11/2026).

As montagens gravam no TEMP e nada apagava no fim: em 24/11 o TEMP chegou a 165 GB (só a M2WK3B1 deixou 115 GB)
e o C: ficou com 9,6 GB livres. Os exports, segmentos e estados ficam no Drive; o TEMP é só cache e se refaz.

Uso:
  limpa_temp.py <pasta do job | ID>   [--ver]     apaga (ou só lista, com --ver) as pastas do job
O `checklist.py entrega` chama sozinho quando a entrega passa. Para pular: FLUXO_SEM_LIMPEZA=1.

O que conta como pasta do job (ID = BATCH#4453 ou M2WK2B3, tirado do nome da pasta do job):
  - dentro de linha_do_tempo, ts_montar, hf, vsl_montar: subpasta cujo nome começa pelo ID
    (BATCH#4453, BATCH_4453, M2WK2B3_-_True_Clean_Home...);
  - no TEMP direto: pasta com o ID no nome (m2wk2b3, tb_m2wk3b2_v6) ou, em batch da EV, com o número
    (b4453, qa4453, c4453, b4453_ref). Número e ID valem só inteiros: 4453 não pega 44530, M2WK3B1 não pega M2WK3B10.
Arquivo solto, pasta de outro job e cache comum (_overlays, _cache, fluxo_refs, claude...) ficam.
"""
import os, re, sys, shutil, stat, tempfile

PAIS = ("linha_do_tempo", "ts_montar", "hf", "vsl_montar")


def id_do_job(alvo):
    nome = os.path.basename(os.path.abspath(alvo).rstrip("/\\")) if os.path.sep in alvo or os.path.exists(alvo) else alvo
    m = re.search(r"BATCH\s*[#_ ]?\s*(\d+)", nome, re.I)
    if m: return ("ev", m.group(1))
    m = re.search(r"M\d+WK\d+B\d+", nome, re.I)
    if m: return ("ts", m.group(0).lower())
    return None


def _norm(s): return re.sub(r"[^a-z0-9]", "", s.lower())


def _bate_inicio(nome, tipo, chave):
    n = _norm(nome)
    pre = ("batch" + chave) if tipo == "ev" else chave
    return n.startswith(pre) and not n[len(pre):len(pre) + 1].isdigit()


def _bate_solto(nome, tipo, chave):
    n = nome.lower()
    if tipo == "ev": return re.search(rf"(?<![0-9]){chave}(?![0-9])", n) is not None
    return re.search(rf"{chave}(?![0-9])", _norm(n)) is not None


def pastas_do_job(tipo, chave, tmp=None):
    tmp = tmp or tempfile.gettempdir(); achadas = []
    for pai in PAIS:
        P = os.path.join(tmp, pai)
        if not os.path.isdir(P): continue
        for n in os.listdir(P):
            p = os.path.join(P, n)
            if os.path.isdir(p) and not n.startswith("_") and _bate_inicio(n, tipo, chave): achadas.append(p)
    for n in os.listdir(tmp):
        p = os.path.join(tmp, n)
        if n in PAIS or n.startswith("_") or not os.path.isdir(p): continue
        if _bate_solto(n, tipo, chave): achadas.append(p)
    return achadas


def _tamanho(p):
    t = 0
    for r, _, fs in os.walk(p):
        for f in fs:
            try: t += os.path.getsize(os.path.join(r, f))
            except OSError: pass
    return t


def _forca(func, path, _):
    try: os.chmod(path, stat.S_IWRITE); func(path)
    except OSError: pass


def limpar(alvo, ver=False, tmp=None):
    j = id_do_job(alvo)
    if not j: print(f"limpeza do TEMP: não achei ID de job em '{alvo}'; nada apagado."); return 0
    pastas = pastas_do_job(*j, tmp=tmp); total = 0
    if not pastas: print(f"limpeza do TEMP ({j[1]}): nada a apagar."); return 0
    for p in pastas:
        t = _tamanho(p); total += t
        if ver: print(f"  apagaria {t/1e9:6.2f} GB  {p}"); continue
        shutil.rmtree(p, onerror=_forca)
        print(f"  {'apagada' if not os.path.exists(p) else 'FICOU (arquivo em uso?)'} {t/1e9:6.2f} GB  {p}")
    print(f"limpeza do TEMP ({j[1]}): {'apagaria' if ver else 'liberados'} {total/1e9:.1f} GB em {len(pastas)} pasta(s).")
    return 0


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if not a: print(__doc__); sys.exit(1)
    sys.exit(limpar(a[0], ver="--ver" in sys.argv))
