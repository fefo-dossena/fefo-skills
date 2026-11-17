#!/usr/bin/env python3
"""Abre um HTML local no Chrome headless (tela de carrinho, produto, card) e grava um PNG.

  py html_png.py PAGINA.html SAIDA.png [--largura 720] [--altura 1280] [--escala 1]
  py html_png.py --url PAGINA.html        # só imprime a URL file:/// certa (para outro uso)

Por que existe (BATCH#4607, 17/11/2026): a pasta da batch tem "#" (BATCH#4607). Em URL o "#" começa a âncora, e o
Chrome abria "file:///G:/.../BATCH" (não existe). A URL certa leva %23 no lugar do "#" (e %20 no espaço):
pathlib.Path.as_uri() faz isso. Use sempre esta função em vez de montar "file://" + caminho à mão.
"""
import argparse, os, pathlib, shutil, subprocess, sys, tempfile

for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

CANDIDATOS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def url_de_arquivo(caminho):
    """file:///G:/Meu%20Drive/.../BATCH%234607/... (o "#" vira %23)."""
    return pathlib.Path(os.path.abspath(caminho)).as_uri()


def chrome():
    for c in CANDIDATOS + [shutil.which("chrome") or "", shutil.which("google-chrome") or "", shutil.which("msedge") or ""]:
        if c and os.path.exists(c):
            return c
    sys.exit("não achei o Chrome nem o Edge")


def png(html, saida, largura=720, altura=1280, escala=1):
    saida = os.path.abspath(saida)
    with tempfile.TemporaryDirectory() as perfil:   # perfil limpo: não mexe no Chrome do Fefo
        tmp_png = os.path.join(perfil, "shot.png")   # grava fora da pasta com "#" e copia depois
        cmd = [chrome(), "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={perfil}",
               f"--window-size={largura},{altura}", f"--force-device-scale-factor={escala}",
               f"--screenshot={tmp_png}", url_de_arquivo(html)]
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        if not os.path.exists(tmp_png):
            sys.exit(f"o Chrome não gravou o PNG ({url_de_arquivo(html)})")
        os.makedirs(os.path.dirname(saida), exist_ok=True)
        shutil.copyfile(tmp_png, saida)
    return saida


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("html"); ap.add_argument("saida", nargs="?")
    ap.add_argument("--url", action="store_true"); ap.add_argument("--largura", type=int, default=720)
    ap.add_argument("--altura", type=int, default=1280); ap.add_argument("--escala", type=float, default=1)
    a = ap.parse_args()
    if a.url or not a.saida:
        print(url_de_arquivo(a.html)); sys.exit(0)
    print(png(a.html, a.saida, a.largura, a.altura, a.escala))
