#!/usr/bin/env python3
"""Review Room da batch: monta o review.json a partir de plano.json e 09_export e roda o build do reviewroom.py.
Cada marca vira um vídeo e cada AD vira um hook; a versão atual vem de 09_export/_old/V<k>. Rodar de novo depois de
uma revisão acrescenta a versão nova e aponta as anteriores para _old/. Nada fica na batch: cópias de revisão, page e
estado ficam em ~/.vsl-batch-editor/salas/<batch>/.

  python3 sala.py "<batch>" [--nota "o que mudou"] [--4x5] [--pasta <outra pasta>]
"""
import argparse, datetime, glob, json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fluxo as F

def versao_atual(B):
    v = [int(m[1]) for d in glob.glob(f"{B}/09_export/_old/V*") if (m := re.search(r"V(\d+)$", d))]
    return max(v, default=0) + 1

def timeline(B, plano, p, n, mp4, dest):
    """Trechos hook/body e legendas do AD, para as notas 'all hooks' caírem no mesmo ponto da hold."""
    srt_ad = F.L(B, f"AD{n}_{p}.srt")
    if not os.path.exists(srt_ad): return
    ad, dur = F.ler_srt(srt_ad), F.duracao(mp4)
    hs = F.hook_marca(plano, n, p)[2]; srt_h = F.L(B, f"{hs}.srt")
    hk = F.ler_srt(srt_h) if os.path.exists(srt_h) else []
    tl = {"duration": round(dur, 3), "segments": [],
          "text": [{"type": "caption", "text": t, "start": round(a, 3), "end": round(b, 3)} for a, b, t in ad]}
    if hk and len(ad) > len(hk) and [x[2].lower() for x in ad[:len(hk)]] == [x[2].lower() for x in hk]:
        c = round(ad[len(hk)][0], 3)
        tl["segments"] = [{"seg": "hook", "start": 0, "end": c}, {"seg": "body", "start": c, "end": round(dur, 3)}]
    os.makedirs(os.path.dirname(dest), exist_ok=True); json.dump(tl, open(dest, "w"), ensure_ascii=False)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("batch"); ap.add_argument("--nota", default="")
    ap.add_argument("--4x5", dest="q45", action="store_true"); ap.add_argument("--pasta")
    a = ap.parse_args(); B = os.path.abspath(a.batch); plano, cfg = F.carregar(B); nome = os.path.basename(B)
    base = a.pasta or os.path.expanduser(f"~/.vsl-batch-editor/salas/{nome}"); os.makedirs(base, exist_ok=True)
    rj = f"{base}/review.json"
    r = json.load(open(rj)) if os.path.exists(rj) else {"title": cfg.get("card") or nome, "id": re.sub(r"\W+", "-", nome).strip("-").lower(),
                                                        "client": "Empire Vision", "url": None, "videos": []}
    k = versao_atual(B); hoje = str(datetime.date.today()); faltam = []
    for p in plano["produtos"]:
        vd = next((x for x in r["videos"] if x["id"] == p), None)
        if vd is None:
            vd = {"id": p, "concept": F.marca_nome(plano, p), "hooks": [], "versions": []}; r["videos"].append(vd)
        for ver in vd["versions"]:                          # versão anterior foi para _old/V<v>/<p>/
            if ver["v"] == k: continue
            for rs in ver["renders"].values():
                for q, c in rs.items():
                    novo = c.replace(f"/09_export/{p}/", f"/09_export/_old/V{ver['v']}/{p}/")
                    if os.path.exists(novo): rs[q] = novo
        rend = {}
        for n in sorted(int(x) for x in plano["hooks"]):
            mp4 = F.export(B, plano, p, n)
            if not os.path.exists(mp4): faltam.append(mp4); continue
            ad_name = os.path.basename(mp4)[:-4]; rend[str(n)] = {"9x16": mp4}
            if not any(h["n"] == n for h in vd["hooks"]): vd["hooks"].append({"n": n, "label": f"AD{n}", "ad_name": ad_name})
            if a.q45:
                q = glob.glob(f"{glob.escape(os.path.dirname(mp4))}/4x5/*AD{n}*.mp4")
                if q: rend[str(n)]["4x5"] = q[0]
            timeline(B, plano, p, n, mp4, f"{base}/timelines/v{k}_{ad_name}.timeline.json")
        vd["versions"] = [x for x in vd["versions"] if x["v"] != k] + [{"v": k, "date": hoje, "note": a.nota or f"V{k}", "renders": rend}]
    json.dump(r, open(rj, "w"), ensure_ascii=False, indent=1)
    for f in faltam: print("  ! falta o export:", f)
    print(f"V{k} em {rj}")
    # O kit vive na skill sala-de-revisao (design do Fefo + montagem ao vivo); a cópia daqui fica de reserva.
    kit = os.path.expanduser("~/.claude/skills/sala-de-revisao/scripts/reviewroom.py")
    if not os.path.exists(kit): kit = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reviewroom.py")
    subprocess.run([sys.executable, kit, "build", rj], check=True)

if __name__ == "__main__": main()
