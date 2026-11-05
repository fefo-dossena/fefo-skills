#!/usr/bin/env python3
"""Acrescenta um aprendizado ao diário do mês (_FLUXO_VSL/CALIBRACAO/AAAA-MM.md) sem ler o arquivo.

Uso: python3 anotar.py "Título da entrada (ex.: BATCH#3831 V2, legenda)" "- item 1" "- item 2" ...
     ou: python3 anotar.py "Título" < texto.md
Motivo (05/11/2026): ler o diário inteiro para editar custava ~50 mil tokens por sessão.
Consulta: grep -rn -i "<tema>" CALIBRACAO/  (nunca abrir o mês inteiro)."""
import datetime, os, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
PASTA = os.path.join(os.path.dirname(AQUI), "CALIBRACAO")
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
         "setembro", "outubro", "novembro", "dezembro"]

if len(sys.argv) < 2: raise SystemExit(__doc__)
hoje = datetime.date.today()
titulo = sys.argv[1]
corpo = "\n".join(sys.argv[2:]) if len(sys.argv) > 2 else sys.stdin.read()
os.makedirs(PASTA, exist_ok=True)
arq = os.path.join(PASTA, f"{hoje:%Y-%m}.md")
novo = not os.path.exists(arq)
with open(arq, "a", encoding="utf-8") as f:
    if novo: f.write(f"# Calibração — {MESES[hoje.month - 1]} de {hoje.year}\n")
    f.write(f"\n## {hoje:%Y-%m-%d}: {titulo}\n{corpo.strip()}\n")
print(f"anotado em {arq}")
