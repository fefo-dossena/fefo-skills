#!/usr/bin/env python3
"""Teste do alerta de fala sem voz (fluxo.falas_sem_voz) com os clipes reais da BATCH#3378 V1. Monta uma batch de mentira
em $TMPDIR com symlinks: nada é gravado na 3378 e nada é renderizado.
  M1F03 (hold/, guia a −30 dB)  -> clipe quase mudo + corte vazio; o `fazer` para antes das prévias
  M1F02 (hold/)                 -> passa; com o corte trocado para [] acusa só o corte vazio
Sem esses clipes em 03_avatar/hold/, o teste diz que pulou."""
import json, os, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fluxo

hold = f"{os.path.dirname(fluxo.FLUXO)}/BATCH#3378/03_avatar/hold"
if not all(os.path.exists(f"{hold}/{c}.mp4") for c in ("M1F01", "M1F02", "M1F03")): sys.exit(f"pulei: faltam os clipes em {hold}")

B = tempfile.mkdtemp(prefix="teste_sem_voz_")
try:
    for d in ("03_avatar/hold", "03_avatar/hooks", "08_auto/cortes"): os.makedirs(f"{B}/{d}")
    os.symlink(f"{hold}/M1F01.mp4", f"{B}/03_avatar/hooks/H1.mp4")
    os.symlink(f"{hold}/M1F02.mp4", f"{B}/03_avatar/hold/F02.mp4")
    os.symlink(f"{hold}/M1F03.mp4", f"{B}/03_avatar/hold/F03.mp4")
    json.dump({"batch": "BATCH#3378", "produtos": ["neurobella"], "modelo_falas": "seedance_2_5", "estilo": {}, "hold": ["a", "b"],
               "cenas": [], "falas": [{"id": "H1", "tipo": "hook", "hook": 1, "texto": "x"}, {"id": "F02", "tipo": "hold", "texto": "a"},
                                      {"id": "F03", "tipo": "hold", "texto": "b"}]}, open(f"{B}/08_auto/plano.json", "w"))
    json.dump({"corte_silencio": {}}, open(f"{B}/batch.json", "w"))
    fx = [sys.executable, os.path.abspath(fluxo.__file__)]

    assert [r for r, _ in fluxo.falas_sem_voz(B)] == ["F03"], "antes dos cortes: só o clipe mudo"

    r = subprocess.run(fx + ["fazer", B], capture_output=True, text=True)
    assert r.returncode != 0 and "Parei antes das prévias" in r.stderr, "o fazer tinha de parar"
    assert json.load(open(fluxo.corte(B, "F03"))) == [], "F03 deveria dar corte vazio, como na V1"
    assert not os.path.exists(fluxo.previa(B, "neurobella")), "o fazer não pode chegar à prévia"
    assert [r for r, _ in fluxo.falas_sem_voz(B)] == ["F03"] and "corte vazio" in fluxo.falas_sem_voz(B)[0][1]

    json.dump([], open(fluxo.corte(B, "F02"), "w"))
    motivo = dict(fluxo.falas_sem_voz(B))["F02"]
    assert motivo.startswith("corte vazio") and "mudo" not in motivo, "F02 tem voz: só o corte vazio"

    r = subprocess.run(fx + ["status", B], capture_output=True, text=True, check=True)
    assert "✖ Fala sem voz: 2" in r.stdout and "Tudo pronto" not in r.stdout, "status tem de mostrar o alerta"

    r = subprocess.run(fx + ["fazer", B, "--ate", "cortes", "--aceitar-sem-voz"], capture_output=True, text=True)
    assert r.returncode == 0 and "✖ Fala sem voz" in r.stdout, "--aceitar-sem-voz avisa e segue"
    print("ok: alerta do status, parada do fazer e --aceitar-sem-voz")
finally:
    shutil.rmtree(B, ignore_errors=True)
