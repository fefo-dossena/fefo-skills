# Parte do fluxo.py: timeline do Premiere, identificar e novo-plano. Roda no mesmo espaço de nomes do fluxo.py (não importar sozinho).
# ---------------------------------------------------------------- XML (V1 falas, V2 b-roll)
def gerar_xml(B):
    import urllib.parse
    from xml.sax.saxutils import escape
    plano, _ = carregar(B); FPS, W, H = 30, 1080, 1920; fr = lambda t: int(round(t * FPS))
    if plano.get("one_take"):
        import umtake; return umtake.gerar_xml(sys.modules[__name__], B)
    info, fid = {}, {}
    def media(p):
        if p not in info:
            o = subprocess.run([FF, "-i", p], capture_output=True, text=True).stderr
            v = re.search(r"Video:.*?, (\d+)x(\d+)", o); r = re.search(r"(\d+(?:\.\d+)?) fps", o)
            info[p] = (duracao(p), int(v[1]), int(v[2]), float(r[1])); fid[p] = f"file-{len(fid)+1}"
        return info[p]
    def fe(p, vistos):
        d, sw, sh, sf = media(p)
        if fid[p] in vistos: return f'<file id="{fid[p]}"/>'
        vistos.add(fid[p])
        return (f'<file id="{fid[p]}"><name>{escape(os.path.basename(p))}</name><pathurl>file://{urllib.parse.quote(p)}</pathurl>'
                f'<rate><timebase>{round(sf)}</timebase><ntsc>FALSE</ntsc></rate><duration>{int(round(d*sf))}</duration><media><video>'
                f'<samplecharacteristics><width>{sw}</width><height>{sh}</height></samplecharacteristics></video>'
                f'<audio><channelcount>2</channelcount></audio></media></file>')
    rate = f"<rate><timebase>{FPS}</timebase><ntsc>FALSE</ntsc></rate>"
    def motion(sw, sh, vert=0.0, crop=None):
        s = 100 * max(W / sw, (H if crop is None else H / 2) / sh) if crop is None else 100 * W / sw
        e = (f'<filter><effect><name>Basic Motion</name><effectid>basic</effectid><effectcategory>motion</effectcategory><effecttype>motion</effecttype>'
             f'<mediatype>video</mediatype><parameter><parameterid>scale</parameterid><name>Scale</name><valuemin>0</valuemin><valuemax>1000</valuemax>'
             f'<value>{s:.2f}</value></parameter><parameter><parameterid>center</parameterid><name>Center</name><value><horiz>0</horiz><vert>{vert}</vert></value></parameter></effect></filter>')
        if crop:
            e += (f'<filter><effect><name>Crop</name><effectid>crop</effectid><effectcategory>motion</effectcategory><effecttype>motion</effecttype><mediatype>video</mediatype>'
                  f'<parameter><parameterid>top</parameterid><name>top</name><value>{crop}</value></parameter>'
                  f'<parameter><parameterid>bottom</parameterid><name>bottom</name><value>{crop}</value></parameter></effect></filter>')
        return e
    def motion_xy(s, hz, vt, top=None, bot=None):
        e = (f'<filter><effect><name>Basic Motion</name><effectid>basic</effectid><effectcategory>motion</effectcategory><effecttype>motion</effecttype>'
             f'<mediatype>video</mediatype><parameter><parameterid>scale</parameterid><name>Scale</name><valuemin>0</valuemin><valuemax>1000</valuemax>'
             f'<value>{s:.2f}</value></parameter><parameter><parameterid>center</parameterid><name>Center</name><value><horiz>{hz:.4f}</horiz><vert>{vt:.4f}</vert></value></parameter></effect></filter>')
        if top is not None:
            e += (f'<filter><effect><name>Crop</name><effectid>crop</effectid><effectcategory>motion</effectcategory><effecttype>motion</effecttype><mediatype>video</mediatype>'
                  f'<parameter><parameterid>top</parameterid><name>top</name><value>{top:.2f}</value></parameter>'
                  f'<parameter><parameterid>bottom</parameterid><name>bottom</name><value>{bot:.2f}</value></parameter></effect></filter>')
        return e
    def motion_meia(sw, sh, lado, baixo=False):
        """Metade da tela dividida (split): lado -1 esquerda, +1 direita; cobre 540 x (1920 ou 960) e corta o excesso."""
        hh = H / 2 if baixo else H; s = 100 * max(W / 2 / sw, hh / sh)
        cl = round(100 * (1 - (W / 2) / (sw * s / 100)) / 2, 2); ct = round(100 * (1 - hh / (sh * s / 100)) / 2, 2)
        e = motion_xy(s, 0.25 * lado, 0.25 if baixo else 0, ct, ct)
        return e.replace('<parameter><parameterid>bottom</parameterid>',
                         f'<parameter><parameterid>left</parameterid><name>left</name><value>{cl:.2f}</value></parameter>'
                         f'<parameter><parameterid>right</parameterid><name>right</name><value>{cl:.2f}</value></parameter>'
                         '<parameter><parameterid>bottom</parameterid>')
    CART = plano.get("estilo", {}).get("broll", {}).get("layout") == "cartao"; CENS = {c["id"]: c for c in plano["cenas"]}
    if CART:
        import cartao; EST = cartao.cfg_estilo(plano); CEN = {c["id"]: c for c in plano["cenas"]}
    seqs = []
    for p in plano["produtos"]:
        for n in hooks(plano):
            vistos, V1, A1, V2, V3, t = set(), [], [], [], [], 0
            fl = [fala_hook(plano, n)] + falas_hold(plano)
            for fi, f in enumerate(fl):
                mp4 = fala_mp4(B, f, p if f.get("marca") else None); d, sw, sh, _ = media(mp4)
                if CART:
                    zz = EST["avatar"]["punch_in"]; mav = motion_xy(*cartao.motion_avatar(sw, sh, EST, zz[fi % len(zz)]))
                else: mav = motion(sw, sh)
                for s, e in json.load(open(corte(B, fala_stem(f, p if f.get("marca") else None)))):
                    a, b = fr(s), fr(e); dd = b - a
                    if dd <= 0: continue
                    cid = f"AD{n}{p}-{len(V1)}"; com = (f'<name>{escape(os.path.basename(mp4))}</name><enabled>TRUE</enabled><duration>{fr(d)}</duration>'
                                                       f'{rate}<start>{t}</start><end>{t+dd}</end><in>{a}</in><out>{b}</out>')
                    lk = f'<link><linkclipref>{cid}v</linkclipref><mediatype>video</mediatype></link><link><linkclipref>{cid}a</linkclipref><mediatype>audio</mediatype></link>'
                    V1.append(f'<clipitem id="{cid}v">{com}{fe(mp4, vistos)}{mav}{lk}</clipitem>')
                    A1.append(f'<clipitem id="{cid}a">{com}<file id="{fid[mp4]}"/><sourcetrack><mediatype>audio</mediatype><trackindex>1</trackindex></sourcetrack>{lk}</clipitem>')
                    t += dd
            if os.path.exists(L(B, f"palavras_hold_{p}.json")) and os.path.exists(L(B, f"palavras_{hook_marca(plano, n, p)[2]}.json")):
                plan, _ = segmentos(B, p, n)
                for k, (c, a, b, fl2) in enumerate(plan):
                    d, sw, sh, _ = media(fl2); dd = fr(b) - fr(a)
                    if dd <= 0: continue
                    if CART:
                        fm = CEN[c]["formato"] if c in CEN else "tela_cheia"
                        mo = motion_xy(100 * 900 / sw, 0, (70 + 450 - H / 2) / H) if fm == "cta_final" else motion_xy(*cartao.motion_broll(sw, sh, EST, fm))
                    elif plano.get("estilo", {}).get("broll", {}).get("layout") == "metade_baixo":
                        mo = motion(sw, sh, 0.25, round(100 * (1 - (H / 2) / (sh * W / sw)) / 2, 2))
                    else: mo = motion(sw, sh)
                    rd = None if CART else clipe_direita(B, CENS.get(c, {}), p)
                    baixo = plano.get("estilo", {}).get("broll", {}).get("layout") == "metade_baixo"
                    if rd: mo = motion_meia(sw, sh, -1, baixo)      # split: esta metade à esquerda, o produto em V3
                    i0 = fr(cena_inicio(CENS.get(c, {})))
                    V2.append(f'<clipitem id="AD{n}{p}-b{k}"><name>{escape(os.path.basename(fl2))}</name><enabled>TRUE</enabled><duration>{fr(d)}</duration>'
                              f'{rate}<start>{fr(a)}</start><end>{fr(a)+dd}</end><in>{i0}</in><out>{i0+dd}</out>{fe(fl2, vistos)}{mo}</clipitem>')
                    if rd:
                        d3, sw3, sh3, _ = media(rd); i3 = fr(float(CENS[c].get("inicio_direita", 0)))
                        V3.append(f'<clipitem id="AD{n}{p}-d{k}"><name>{escape(os.path.basename(rd))}</name><enabled>TRUE</enabled><duration>{fr(d3)}</duration>'
                                  f'{rate}<start>{fr(a)}</start><end>{fr(a)+dd}</end><in>{i3}</in><out>{i3+dd}</out>{fe(rd, vistos)}{motion_meia(sw3, sh3, 1, baixo)}</clipitem>')
            v3 = f'<track>{"".join(V3)}</track>' if V3 else ""
            seqs.append(f'<sequence id="AD{n}-{p}"><name>AD{n}_{p}</name><duration>{t}</duration>{rate}<media><video><format><samplecharacteristics>{rate}'
                        f'<width>{W}</width><height>{H}</height><pixelaspectratio>square</pixelaspectratio></samplecharacteristics></format>'
                        f'<track>{"".join(V1)}</track><track>{"".join(V2)}</track>{v3}</video><audio><track>{"".join(A1)}</track></audio></media></sequence>')
    out = xmlpath(B, plano)
    open(out, "w").write('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n<xmeml version="4"><project><name>'
                         f'BATCH{num(plano)}</name><children>{"".join(seqs)}</children></project></xmeml>')
    print(f"   ok {os.path.basename(out)} ({len(seqs)} sequências)")

# ---------------------------------------------------------------- identificar vídeos baixados
def cmd_identificar(a):
    import numpy as np
    def fp(p, video):
        args = [FF, "-nostdin", "-v", "quiet", "-i", p, "-vf", "scale=32:56,format=gray", "-frames:v", "1", "-f", "rawvideo", "-"]
        return np.frombuffer(subprocess.run(args, capture_output=True).stdout, np.uint8).astype(float)
    Q = {os.path.splitext(os.path.basename(q))[0]: fp(q, False) for q in glob.glob(f"{a.quadros}/*.png") + glob.glob(f"{a.quadros}/*.jpg")}
    for v in a.videos:
        x = fp(v, True); d = sorted((np.abs(x - q).mean(), k) for k, q in Q.items() if len(q) == len(x))
        tag = "OK" if d and d[0][0] < 5 and (len(d) < 2 or d[1][0] - d[0][0] > 5) else "CONFERIR"
        print(f"{os.path.basename(v)}\t{d[0][1] if d else '-'}\t{d[0][0]:.1f}\t{tag}")

def cmd_novo_plano(a):
    B = a.batch.rstrip("/"); r = open(f"{B}/{ROTEIRO}/roteiro.txt").read()
    hold = [re.sub(r"^\d+\.\s*", "", l).strip() for l in r.split("HOLD", 1)[1].strip().splitlines() if re.match(r"^\d+\.", l)]
    hk = {int(m[0]): m[1].strip() for m in re.findall(r"HOOK (\d+)\s*\n([^\n]+)", r)}
    plano = {"batch": os.path.basename(B).split(" ")[0], "produtos": ["neurobella", "visiovance"],
             "marca_nome": {"neurobella": "Neurobella", "visiovance": "VisioVance"},
             "hold": [l.replace("Neurobella", "{MARCA}") for l in hold], "hooks": {str(k): v for k, v in hk.items()},
             "personagens": {}, "frascos": {}, "falas": [], "cenas": []}
    out = f"{B}/{AUTO}/plano.json"
    if os.path.exists(out): raise SystemExit("plano.json já existe; não sobrescrevo.")
    json.dump(plano, open(out, "w"), indent=1, ensure_ascii=False); print("ok", out)

