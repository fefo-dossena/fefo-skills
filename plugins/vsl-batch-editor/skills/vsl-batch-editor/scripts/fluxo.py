#!/usr/bin/env python3
"""Fluxo modular da batch (Neurobella / VisioVance).

Tudo parte de 08_auto/plano.json. Cada arquivo esperado tem dependências; um arquivo
falta (não existe) ou está desatualizado (alguma dependência é mais nova). O `status`
mostra isso por módulo e o `fazer` roda só as etapas LOCAIS que estão pendentes, em
ordem (cortes -> prévias -> legendas -> ADs -> XML). Etapas que gastam crédito
(falas, quadros, b-roll) nunca rodam aqui: o status só lista o que falta.

Subcomandos:
  status <batch>                         o que falta / está desatualizado, e o próximo passo
  fazer  <batch> [--ate cortes|previas|legendas|ads|xml] [--so AD1_neurobella] [--forcar] [--aceitar-sem-voz]
  montar <batch> <produto> <hook>        renderiza um AD final (09_export)
  xml    <batch>                         timeline Premiere (falas em V1, b-roll em V2)
  identificar <videos...> --quadros <pasta>   casa cada vídeo baixado com o quadro inicial (1º frame)
  novo-plano <batch>                     gera um plano.json vazio a partir do roteiro.txt (para o Claude preencher)
  perfil                                 perfil de quem usa (contas, aprovador); sem perfil → módulo configurar
  instalar <raiz>                        (fluxo.py da pasta da skill) monta/atualiza <raiz>/_FLUXO_VSL e _BATCH_MODELO
  empacotar                              (só no _FLUXO_VSL do Fefo) gera o zip da skill; zips antigos vão para old/
  publicar "<mensagem>"                  (só no _FLUXO_VSL do Fefo) manda a skill para o GitHub (plugin com auto-update)
  renomear <batch>                       exports com o nome antigo (BATCH<n>_AD<k>_<p>) → nome do card, sem renderizar

O código está dividido por assunto em fluxo_partes/ (05/11/2026, para a sessão ler só o trecho que vai mexer):
  skill.py     perfil, empacotar, publicar, instalar
  plano.py     plano.json e caminhos de arquivos
  status.py    grafo de dependências, status, fazer, bordas e ganho
  acoes.py     ações locais (o que o fazer executa)
  legenda.py   transcrição, alinhamento e SRT
  broll.py     posição do b-roll e segmentos
  montar.py    montagem final do AD
  xml.py       timeline do Premiere, identificar e novo-plano
Todas rodam no mesmo espaço de nomes, na ordem abaixo, como se fossem um arquivo só."""
import argparse, difflib, glob, json, os, re, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["PATH"] = os.path.expanduser("~/bin") + os.pathsep + os.environ.get("PATH", "")
FF = shutil.which("ffmpeg") or "ffmpeg"


_PARTES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fluxo_partes")
for _parte in ('skill.py', 'plano.py', 'status.py', 'acoes.py', 'legenda.py', 'broll.py', 'montar.py', 'xml.py'):
    _arq = os.path.join(_PARTES_DIR, _parte)
    exec(compile(open(_arq, encoding="utf-8").read(), _arq, "exec"), globals())
del _parte, _arq

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("status"); p.add_argument("batch"); p.set_defaults(fn=cmd_status)
    p = sp.add_parser("fazer"); p.add_argument("batch"); p.add_argument("--ate", choices=ORDEM[2:]); p.add_argument("--so"); p.add_argument("--forcar", action="store_true"); p.add_argument("--aceitar-sem-voz", action="store_true"); p.set_defaults(fn=cmd_fazer)
    p = sp.add_parser("montar"); p.add_argument("batch"); p.add_argument("produto"); p.add_argument("hook"); p.set_defaults(fn=lambda a: montar(a.batch.rstrip("/"), a.produto, a.hook))
    p = sp.add_parser("xml"); p.add_argument("batch"); p.set_defaults(fn=lambda a: gerar_xml(a.batch.rstrip("/")))
    p = sp.add_parser("identificar"); p.add_argument("videos", nargs="+"); p.add_argument("--quadros", required=True); p.set_defaults(fn=cmd_identificar)
    p = sp.add_parser("novo-plano"); p.add_argument("batch"); p.set_defaults(fn=cmd_novo_plano)
    p = sp.add_parser("perfil"); p.set_defaults(fn=cmd_perfil)
    p = sp.add_parser("instalar"); p.add_argument("raiz"); p.set_defaults(fn=cmd_instalar)
    p = sp.add_parser("empacotar"); p.set_defaults(fn=cmd_empacotar)
    p = sp.add_parser("publicar"); p.add_argument("mensagem"); p.set_defaults(fn=cmd_publicar)
    p = sp.add_parser("renomear"); p.add_argument("batch"); p.set_defaults(fn=cmd_renomear)
    a = ap.parse_args(); a.fn(a)
