#!/usr/bin/env python3
"""Ponte para o visao.swift (framework Vision do Mac): rostos, texto (OCR) e mãos de cada imagem.

  python3 visao.py <img> [...]          imprime o JSON de cada imagem
  import visao; visao.ler([imgs])       -> {caminho: {"rostos": [...], "textos": [...], "maos": n}}

O binário é compilado uma vez em ~/.cache/fluxo/visao (recompila quando o .swift muda). Sem swiftc, ler() devolve {}
e quem chamou trata como "não deu para ler" (aviso, nunca erro inventado).
No PC Windows (13/11/2026, Frente 4): OCR embutido do Windows por visao_win.ps1, só texto (rostos [] e maos 0).
Caixas em fração do quadro, origem no canto de cima à esquerda: [x, y, w, h].
"""
import json, os, subprocess, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
FONTE = os.path.join(AQUI, 'visao.swift')
BIN = os.path.expanduser('~/.cache/fluxo/visao')


def binario():
    try:
        if os.path.exists(BIN) and os.path.getmtime(BIN) >= os.path.getmtime(FONTE):
            return BIN
        os.makedirs(os.path.dirname(BIN), exist_ok=True)
        r = subprocess.run(['swiftc', '-O', FONTE, '-o', BIN], capture_output=True, text=True)
        return BIN if r.returncode == 0 else None
    except (OSError, FileNotFoundError):
        return None


def ler_windows(imgs, lote=200):
    """PC Windows: OCR embutido do Windows (visao_win.ps1, sem instalar nada). Só texto: rostos [] e maos 0."""
    import tempfile
    ps1 = os.path.join(AQUI, 'visao_win.ps1')
    out = {}
    for i in range(0, len(imgs), lote):
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write('\n'.join(os.path.abspath(x) for x in imgs[i:i + lote])); lista = f.name
        try:
            r = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ps1, lista],
                               capture_output=True, text=True, encoding='utf-8', errors='replace')
        finally:
            os.remove(lista)
        for ln in r.stdout.splitlines():
            try:
                d = json.loads(ln.lstrip('﻿'))
            except ValueError:
                continue
            d['textos'] = d.get('textos') or []
            if isinstance(d['textos'], dict): d['textos'] = [d['textos']]   # PowerShell 5.1: lista de 1 vira objeto
            arq = d.pop('arquivo')
            out[arq] = d
            for x in imgs[i:i + lote]:                                     # devolve na chave que quem chamou passou
                if os.path.abspath(x) == arq and x != arq: out[x] = out.pop(arq)
    return out


def disponivel():
    """True quando há OCR nesta máquina (Mac: visao.swift; Windows: OCR do sistema)."""
    return os.name == 'nt' or bool(binario())


def ler(imgs, lote=40):
    if os.name == 'nt' and imgs:
        return ler_windows(list(imgs))
    b = binario()
    if not b or not imgs:
        return {}
    out = {}
    for i in range(0, len(imgs), lote):
        r = subprocess.run([b] + list(imgs[i:i + lote]), capture_output=True, text=True)
        for ln in r.stdout.splitlines():
            try:
                d = json.loads(ln)
            except ValueError:
                continue
            out[d.pop('arquivo')] = d
    return out


def sobrepoe(a, b, folga=0.0):
    """Fração da caixa `a` que cai dentro de `b` (caixas [x, y, w, h])."""
    x0, y0 = max(a[0], b[0] - folga), max(a[1], b[1] - folga)
    x1, y1 = min(a[0] + a[2], b[0] + b[2] + folga), min(a[1] + a[3], b[1] + b[3] + folga)
    if x1 <= x0 or y1 <= y0 or a[2] * a[3] <= 0:
        return 0.0
    return (x1 - x0) * (y1 - y0) / (a[2] * a[3])


if __name__ == '__main__':
    for k, v in ler(sys.argv[1:]).items():
        print(json.dumps({'arquivo': k, **v}, ensure_ascii=False))
