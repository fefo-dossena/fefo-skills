"""Prancha para conferir se a imagem bate com a fala em cada trecho de um AD (regra do Fefo, 30/10/2026).

Uso: python3 imagem_fala.py <AD.mp4> [--srt <ADn_p.srt>] [--pos <broll_posicoes_ADn_p.json>] [--hook] [--passo 2] [--saida <pasta>]

Divide o AD nos blocos da legenda e nas trocas de cena, tira o quadro do meio de cada trecho e grava em <saida>
as pranchas numeradas (prancha_01.jpg...) e a tabela.md (nº, tempo, cena, legenda, status em branco para preencher).
--hook para na primeira cena da hold (S..): serve para os ADs que só mudam no hook. Sem --srt nem --pos (vídeo de outro
editor), usa um quadro a cada --passo s e a tabela vem sem legenda. Quadros são cópia de trabalho: saída padrão em
$TMPDIR/vsl_conferencia/<AD>/, nunca na batch. Passo da checagem final: modulos/07_montagem.md."""
import glob, json, os, re, shutil, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont

FF = "ffmpeg"; COLS, LINHAS, W = 8, 2, 216; MIN = 0.15   # trecho menor que isso não vira quadro próprio

def opt(nome, padrao=None):
    return sys.argv[sys.argv.index(nome) + 1] if nome in sys.argv else padrao

args = []; pula = False
for a in sys.argv[1:]:
    if pula: pula = False
    elif a in ("--srt", "--pos", "--passo", "--saida"): pula = True
    elif not a.startswith("--"): args.append(a)
mp4 = args[0]; srt = opt("--srt"); pos = json.load(open(opt("--pos"))) if opt("--pos") else []
passo = float(opt("--passo", 2)); so_hook = "--hook" in sys.argv
saida = opt("--saida") or f"{tempfile.gettempdir()}/vsl_conferencia/{os.path.splitext(os.path.basename(mp4))[0]}"

def ler_srt(p):
    seg = lambda t: sum(float(x) * m for x, m in zip(t.replace(",", ".").split(":"), (3600, 60, 1)))
    out = []
    for bl in re.split(r"\n\s*\n", open(p, encoding="utf-8").read().strip()):
        ls = bl.splitlines()
        if len(ls) >= 3: out.append((*map(seg, ls[1].split(" --> ")), " ".join(ls[2:])))
    return out

dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", mp4],
                           capture_output=True, text=True).stdout)
if so_hook:
    corte = next((a for c, a, b, _ in pos if c.startswith("S")), None)
    if corte is None: raise SystemExit("--hook precisa do --pos com alguma cena S.")
    dur = min(dur, corte)
blocos = ler_srt(srt) if srt else []
if blocos or pos:
    pts = sorted({0.0, dur} | {t for a, b, _ in blocos for t in (a, b)} | {t for _, a, b, _ in pos for t in (a, b)})
else:
    pts = [i * passo for i in range(int(dur / passo) + 1)] + [dur]
pts = [t for t in pts if t <= dur]
trechos = []
for a, b in zip(pts, pts[1:]):
    if b - a < MIN and trechos: trechos[-1][1] = b
    elif b - a > 0: trechos.append([a, b])

def cena(t):
    return next((c for c, a, b, _ in pos if a - 0.02 <= t < b), "avatar" if pos else "")

def legenda(t):
    return next((x for a, b, x in blocos if a - 0.02 <= t < b), "")

# pausa sem legenda na mesma cena não pede quadro próprio
juntos = []
for a, b in trechos:
    t = (a + b) / 2
    if blocos and juntos and not legenda(t) and cena(t) == cena(juntos[-1][0]): juntos[-1][1] = b
    else: juntos.append([a, b])
trechos = juntos

# um processo só do ffmpeg: passa o vídeo uma vez e separa os quadros (o ~/bin/ffmpeg entra na fila)
tmp = tempfile.mkdtemp(prefix="imagem_fala_")
ns = [int((a + b) / 2 * 30) for a, b in trechos]
sel = "+".join(f"eq(n,{n})" for n in ns)
subprocess.run([FF, "-nostdin", "-v", "error", "-i", mp4, "-vf", f"fps=30,select='{sel}',scale={W}:-2",
                "-fps_mode", "passthrough", "-q:v", "3", f"{tmp}/q_%04d.jpg"], check=True)
quadros = sorted(glob.glob(f"{tmp}/q_*.jpg"))
if len(quadros) != len(trechos): print(f"aviso: {len(quadros)} quadros para {len(trechos)} trechos")

shutil.rmtree(saida, ignore_errors=True); os.makedirs(saida)
fonte = ImageFont.load_default(size=15); H = Image.open(quadros[0]).height + 22; n_cel = COLS * LINHAS
pranchas = 0
for i in range(0, len(quadros), n_cel):
    parte = quadros[i:i + n_cel]; pranchas += 1
    pr = Image.new("RGB", (COLS * W, H * ((len(parte) + COLS - 1) // COLS)), "black"); d = ImageDraw.Draw(pr)
    for j, q in enumerate(parte):
        x, y = j % COLS * W, j // COLS * H; a = trechos[i + j][0]
        pr.paste(Image.open(q), (x, y + 22))
        d.text((x + 4, y + 3), f"#{i + j + 1} {int(a // 60)}:{a % 60:04.1f} {cena(a)}", fill="yellow", font=fonte)
    pr.save(f"{saida}/prancha_{pranchas:02d}.jpg", quality=85)
shutil.rmtree(tmp)

with open(f"{saida}/tabela.md", "w", encoding="utf-8") as f:
    f.write(f"# {os.path.basename(mp4)}\n\n| # | tempo | cena | legenda | status |\n|---|---|---|---|---|\n")
    for i, (a, b) in enumerate(trechos, 1):
        t = (a + b) / 2
        f.write(f"| {i} | {a:.2f}-{b:.2f} | {cena(t)} | {legenda(t).replace('|', '/')} | |\n")
print(f"{saida}: {len(trechos)} trechos em {pranchas} prancha(s), {dur:.1f} s")
