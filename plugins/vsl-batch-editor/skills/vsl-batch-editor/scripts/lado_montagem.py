#!/usr/bin/env python3
"""O que a montagem grava para o checklist da Louise (Frente 4, 13/11/2026), igual nos dois clientes:
  <auto>/mix_<nome>.json      voz x trilha medidas nos stems (antes do loudnorm) e as pausas da VO no stem limpo
  <auto>/camadas_<nome>.json  onde o pilula.py desenhou cada bloco de texto (legenda/header), em fração da altura
Os dois guardam {"por_digital": {<sha1 16 do vídeo final>: {...}}}: o checklist só usa a medida do mesmo arquivo.
Usado por fluxo_partes/montar.py (Empire Vision) e por montagem_base.py (Trendscale)."""
import datetime, hashlib, json, os, wave


def digital(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()[:16]


def grava(pasta_auto, nome, dg, dados):
    """<auto>/<nome>.json = {"por_digital": {dg: dados}} (últimos 6: prévia e final convivem)."""
    os.makedirs(pasta_auto, exist_ok=True)
    arq = os.path.join(pasta_auto, nome + ".json")
    try: d = json.load(open(arq, encoding="utf-8"))
    except (OSError, ValueError): d = {}
    pd = d.get("por_digital", {}); pd[dg] = dict(dados, gravado=datetime.datetime.now().isoformat(timespec="seconds"))
    json.dump({"por_digital": dict(list(pd.items())[-6:])}, open(arq, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return arq


def _ler(a):
    import numpy as np
    with wave.open(a) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768.0
        sr = w.getframerate(); ch = w.getnchannels()
    if ch > 1: x = x.reshape(-1, ch).mean(1)
    return x, sr


def mede_mix(voz, trilha, jan=0.05):
    """Voz x trilha nos trechos com fala (stems antes do loudnorm: o ganho final é o mesmo nos dois) e pausas da VO."""
    import numpy as np
    v, sr = _ler(voz); n = int(sr * jan); k = len(v) // n
    dv = 10 * np.log10(np.maximum((v[:k * n].reshape(k, n) ** 2).mean(1), 1e-12))
    fala = dv > np.percentile(dv, 95) - 25
    n2 = int(sr * 0.02); k2 = len(v) // n2; d2 = 10 * np.log10(np.maximum((v[:k2 * n2].reshape(k2, n2) ** 2).mean(1), 1e-12))
    ativo = d2 > np.percentile(d2, 95) - 30; idx = np.where(ativo)[0]; pausas = []
    if idx.size:
        i, fim = idx[0], idx[-1]
        while i <= fim:
            if not ativo[i]:
                j = i
                while j + 1 <= fim and not ativo[j + 1]: j += 1
                if (j - i + 1) * 0.02 >= 0.25: pausas.append((round(i * 0.02, 2), round((j - i + 1) * 0.02, 2)))
                i = j + 1
            else: i += 1
    if not trilha or not os.path.exists(trilha):
        return {"margem_db": 40.0, "trilha": False, "piores": [], "pausas": pausas}
    t, _ = _ler(trilha); t = t[:k * n]; t = np.pad(t, (0, k * n - len(t)))
    dt = 10 * np.log10(np.maximum((t.reshape(k, n) ** 2).mean(1), 1e-12))
    m = (dv - dt)[fala]
    if not m.size: return {"margem_db": None, "trilha": True, "piores": [], "pausas": pausas}
    ii = np.where(fala)[0][np.argsort(m)[:5]]
    return {"margem_db": round(float(np.median(m)), 1), "p10_db": round(float(np.percentile(m, 10)), 1), "trilha": True, "pausas": pausas,
            "piores": [{"t": round(float(i * jan), 2), "margem_db": round(float(dv[i] - dt[i]), 1)} for i in ii]}


def camadas_pilula(lista, y_legs=(0.63,)):
    """Blocos de texto desenhados pelo pilula.py (alfa dos PNGs da lista do concat): [{tipo, t0, t1, y0, y1}] em fração
    da altura. "legenda" = bloco perto de uma das alturas de legenda (y_legs, fração ou px de 1920); o resto, "header"."""
    from PIL import Image
    import numpy as np
    out, t, cache = [], 0.0, {}
    linhas = open(lista, encoding="utf-8").read().splitlines(); itens = []
    for i, l in enumerate(linhas):
        if l.startswith("file ") and i + 1 < len(linhas) and linhas[i + 1].startswith("duration "):
            itens.append((l[6:-1], float(linhas[i + 1].split()[1])))
    ys = [y if y <= 1 else y / 1920 for y in y_legs]
    for png, d in itens:
        if png not in cache:
            al = np.asarray(Image.open(png).getchannel("A")); H = al.shape[0]; rows = np.where(al.max(1) > 0)[0]; blocos = []
            if rows.size:
                ini = rows[0]
                for a, b in zip(rows, rows[1:]):
                    if b - a > 12: blocos.append((ini, a)); ini = b
                blocos.append((ini, rows[-1]))
            cache[png] = [(y0 / H, (y1 + 1) / H) for y0, y1 in blocos]
        for y0, y1 in cache[png]:
            c = (y0 + y1) / 2
            out.append({"tipo": "legenda" if any(abs(c - yy) <= 0.12 for yy in ys) else "header",
                        "t0": round(t, 2), "t1": round(t + d, 2), "y0": round(y0, 4), "y1": round(y1, 4)})
        t += d
    junto = []
    for c in out:
        u = junto[-1] if junto else None
        if u and u["tipo"] == c["tipo"] and abs(u["y0"] - c["y0"]) < 0.002 and abs(u["y1"] - c["y1"]) < 0.002 and abs(u["t1"] - c["t0"]) < 0.05: u["t1"] = c["t1"]
        else: junto.append(dict(c))
    return junto


def pasta_auto(video):
    """Pasta auto do job/batch do vídeo (pela ficha do cliente), ou None."""
    import sys
    aqui = os.path.dirname(os.path.abspath(__file__))
    if aqui not in sys.path: sys.path.insert(0, aqui)
    import checklist as CK
    f = CK.ficha_de(video); B = CK.batch_de(video, f)
    return os.path.join(B, CK.pastas_de(f)["auto"]) if B else None
