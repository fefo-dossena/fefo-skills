#!/usr/bin/env python3
"""Linha do tempo por segmentos (EV e TS): monta cada pedaço uma vez e junta no fim, como no Premiere (Fefo, 17/11/2026).

Pedido do Fefo: "trabalha uma vez no hold e nos hooks e no fim junta tudo; não remonta a cada ajuste; monta o final
só quando eu aprovo hold e hooks individualmente". Música: "um momento pro hook e um pra hold" (cada segmento leva o
próprio trecho da trilha; nada atravessa a emenda além do banner e do loudness).

Peças
  segmento   pedaço da linha do tempo (EV: hook<n> e hold_<marca>; TS: hook<n> e corpo), renderizado SOZINHO num
             intermediário de alta qualidade (MKV: H.264 crf 14 em 1080x1920 + PCM 48 kHz estéreo), com vídeo, voz,
             SFX, trilha (o momento dele), legenda e textos já aplicados. Sem loudnorm.
  hash       das entradas (dict `chave` + tamanho e data de cada arquivo de `fontes` + MOTOR). O mesmo hash = o mesmo
             arquivo (`cache/<papel>/<hash>.mkv`: uma pasta por hook e uma pela hold/corpo): nada é refeito. Hook igual nas duas marcas = um arquivo só.
  aprovado   o segmento que o Fefo aprovou na sala fica TRAVADO: o AD continua usando aquele arquivo mesmo que as entradas
             mudem; só volta a ser refeito com `reabrir` (pedido do Fefo).
  final      só roda com todos os segmentos do AD aprovados. Junta os pedaços e aplica só o que atravessa a emenda: banner
             (quem chama passa o filtro), loudnorm em 2 passadas, export 720p e o lado do checklist. Um encode só.
  sala       prévia de aprovação por segmento: hold sozinha; hook + 2 s da hold depois dele (NVENC, 720p, só para ver).

Estado: <pasta_auto>/segmentos.json (fora do plano.json de propósito: gravar no plano mudaria a data dele e o `fazer` da EV
acharia a batch inteira desatualizada). Formato:
  {"segmentos": {"<id>": {"papel", "hash", "arquivo", "dur", "feito_em", "aprovado": bool, "aprovado_em", "ads": [...]}},
   "ads": {"<AD>": ["<id do hook>", "<id da hold/corpo>"]}}

Linha de comando (a sessão da task roda; o Fefo aprova na sala):
  py linha_do_tempo.py <pasta_auto> status
  py linha_do_tempo.py <pasta_auto> aprovar <id|papel> [...]     papel = hook1, hold_neurobella, corpo... (a pasta do segmento)
  py linha_do_tempo.py <pasta_auto> reabrir <id|papel> [...]     destrava (só com pedido do Fefo)
  py linha_do_tempo.py <pasta_auto> limpar                       apaga do cache os .mkv que nenhum AD usa
"""
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading

MOTOR = "ldt-1"                    # muda quando o jeito de renderizar o segmento muda (invalida o cache, não o aprovado)
TIMEOUT = int(os.environ.get("TS_TIMEOUT_FF", "900"))
FPS = 30
SR = 48000
# Intermediário: H.264 crf 14 veryfast (perda invisível; o final recodifica uma vez só). LDT_INTER=nvenc usa a placa.
INTER_X264 = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-pix_fmt", "yuv420p"]
INTER_NVENC = ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "15", "-b:v", "0", "-pix_fmt", "yuv420p"]


def ff():
    return shutil.which("ffmpeg") or "ffmpeg"


def codec_intermediario():
    return INTER_NVENC if os.environ.get("LDT_INTER") == "nvenc" else INTER_X264


def audio_intermediario():
    return ["-c:a", "pcm_s16le", "-ar", str(SR), "-ac", "2"]


def agora():
    return datetime.datetime.now().strftime("%d/%m %H:%M")


def _assina(f):
    try:
        st = os.stat(f)
        return f"{st.st_size}:{int(st.st_mtime)}"
    except OSError:
        return "-"


_CODIGO = (".py", ".pyc", ".md", ".json.bak")


def hash_de(chave, fontes=(), formato=None):
    """Hash do segmento: SÓ entradas e parâmetros que mudam imagem e som (Central, 17/11/2026: na M1WK3B8 o corpo montou
    2x porque o código do montador entrou no cache). Script (.py) passado em `fontes` é ignorado com aviso; o código não
    entra. Mudou o jeito de renderizar e a saída muda: troque à mão `formato` (ex. "corpo-v2") ou o MOTOR daqui."""
    codigo = [f for f in fontes if f and str(f).lower().endswith(_CODIGO)]
    if codigo:
        print(f"   aviso: código fora do hash do segmento ({', '.join(os.path.basename(str(f)) for f in codigo)})")
    if isinstance(chave, dict) and any(k in chave for k in ("codigo", "script", "fonte_py")):
        print("   aviso: a chave do segmento tem código do montador; mudança no script que não muda a saída refaz o segmento")
    fontes = [f for f in fontes if f and f not in codigo]
    blob = json.dumps([MOTOR, formato, chave, sorted({os.path.normpath(f): _assina(f) for f in fontes}.items())],
                      sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha1(blob.encode()).hexdigest()[:10]


def dur(arq):
    err = subprocess.run([ff(), "-nostdin", "-hide_banner", "-i", arq], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]) if m else 0.0


class _TravaArquivo:
    """Trava entre processos no segmentos.json (Central, 17/11/2026: corpo e hook em faixas diferentes da fila
    sobrescreviam o estado um do outro). Arquivo <estado>.lock criado com O_EXCL; trava velha (> 10 min) é desfeita."""

    def __init__(self, alvo, espera=600, velha=600):
        self.arq, self.espera, self.velha = alvo + ".lock", espera, velha

    def __enter__(self):
        import time
        t0 = time.time()
        while True:
            try:
                fd = os.open(self.arq, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, f"{os.getpid()} {agora()}".encode()); os.close(fd)
                return self
            except FileExistsError:
                try:
                    if time.time() - os.path.getmtime(self.arq) > self.velha:
                        os.remove(self.arq); continue
                except OSError:
                    continue
                if time.time() - t0 > self.espera:
                    raise SystemExit(f"segmentos.json travado há mais de {self.espera} s por outro processo ({self.arq})")
                time.sleep(0.2)

    def __exit__(self, *a):
        try:
            os.remove(self.arq)
        except OSError:
            pass


class Linha:
    """Estado da linha do tempo de uma batch (EV) ou job (TS)."""

    def __init__(self, pasta_auto, cache=None):
        self.auto = pasta_auto
        self.arq = os.path.join(pasta_auto, "segmentos.json")
        # cache dos intermediários fora do Drive (MKV de alta qualidade é grande e o Drive trava leitura no meio do render)
        nome = re.sub(r"[^\w#.-]+", "_", os.path.basename(os.path.dirname(os.path.abspath(pasta_auto))))[:60]
        self.cache = cache or os.path.join(tempfile.gettempdir(), "linha_do_tempo", nome)
        os.makedirs(self.cache, exist_ok=True)
        self.trava = threading.Lock()      # segmentos renderizados ao mesmo tempo (hook e hold) mexem no mesmo estado
        try:
            self.st = json.load(open(self.arq, encoding="utf-8"))
        except (OSError, ValueError):
            self.st = {}
        self.st.setdefault("segmentos", {})
        self.st.setdefault("ads", {})

    def _ler(self):
        try:
            st = json.load(open(self.arq, encoding="utf-8"))
        except (OSError, ValueError):
            st = {}
        st.setdefault("segmentos", {}); st.setdefault("ads", {})
        return st

    def _gravar(self):
        tmp = f"{self.arq}.{os.getpid()}.tmp"           # escrita atômica: tmp + replace
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.st, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, self.arq)

    def mexe(self, fn):
        """Lê o estado do disco, aplica fn(st) e grava, tudo sob a trava entre processos (e entre threads)."""
        with self.trava, _TravaArquivo(self.arq):
            self.st = self._ler()
            r = fn(self.st)
            self._gravar()
            return r

    def salvar(self):
        self.mexe(lambda st: None)

    # ------------------------------------------------------------ segmentos
    def fresco(self):
        """Relê o estado do disco (outro processo pode ter mexido)."""
        with self.trava, _TravaArquivo(self.arq):
            self.st = self._ler()
        return self.st

    def segmento(self, papel, chave, fontes, render, ad=None, forcar=False, formato=None):
        """Devolve o caminho do intermediário do segmento `papel` para o AD `ad`.
        render(dst) grava o MKV em dst (só chamado se o hash é novo). Segmento já aprovado para este AD com outro hash:
        continua o aprovado (travado) e avisa."""
        h = hash_de(chave, fontes, formato)
        sid = f"{papel}_{h}"
        self.fresco()
        trav = self._travado(papel, sid, ad)
        if trav:
            return trav
        # uma pasta por segmento (Fefo, 17/11/2026: "uma pasta pra cada hook e uma pra hold"): <cache>/<papel>/<hash>.mkv
        os.makedirs(os.path.join(self.cache, papel), exist_ok=True)
        dst = os.path.join(self.cache, papel, h + ".mkv")
        novo = False
        if forcar or not (os.path.exists(dst) and os.path.getsize(dst) > 0):
            tmp = dst + ".part.mkv"
            t0 = datetime.datetime.now()
            render(tmp)
            os.replace(tmp, dst)
            print(f"   {papel}: renderizado {sid} em {(datetime.datetime.now() - t0).total_seconds():.0f} s")
            novo = True
        else:
            print(f"   {papel}: do cache ({sid})")
        return self.mexe(lambda st: self._registra(papel, h, sid, dst, ad, novo))

    def _travado(self, papel, sid, ad):
        seg = self.st["segmentos"]
        # trava: este AD já tem um segmento aprovado com o mesmo papel
        if ad and ad in self.st["ads"]:
            for antigo in self.st["ads"][ad]:
                s = seg.get(antigo)
                if s and s["papel"] == papel and s.get("aprovado") and antigo != sid:
                    if os.path.exists(s["arquivo"]):
                        print(f"   {papel}: aprovado e travado ({antigo}); entradas mudaram depois do OK. "
                              f"Para refazer, o Fefo pede e roda-se `reabrir {antigo}`.")
                        return antigo, s["arquivo"]
                    print(f"   ! {papel}: o aprovado {antigo} sumiu do cache; refazendo com as entradas atuais")
        return None

    def _registra(self, papel, h, sid, dst, ad, novo):
        seg = self.st["segmentos"]
        s = seg.setdefault(sid, {"papel": papel, "hash": h, "arquivo": dst, "aprovado": False, "ads": []})
        s["arquivo"] = dst
        if novo or "dur" not in s:
            s["dur"] = round(dur(dst), 3)
            s["feito_em"] = agora()
            if novo and s.get("aprovado"):      # refeito por forçar: perde o OK
                s["aprovado"] = False
        if ad and ad not in s["ads"]:
            s["ads"].append(ad)
        return sid, dst

    def liga_ad(self, ad, ids):
        self.mexe(lambda st: st["ads"].__setitem__(ad, list(ids)))

    def ids_de(self, alvo):
        seg = self.st["segmentos"]
        if alvo in seg:
            return [alvo]
        usados = {i for ids in self.st["ads"].values() for i in ids}
        return [i for i, s in seg.items() if s["papel"] == alvo and i in usados]

    def aprovar(self, alvo, sim=True):
        def fn(st):
            ids = self.ids_de(alvo)
            for i in ids:
                s = st["segmentos"][i]
                s["aprovado"] = sim
                s["aprovado_em" if sim else "reaberto_em"] = agora()
            return ids
        ids = self.mexe(fn)
        if not ids:
            raise SystemExit(f"segmento {alvo!r} não existe na linha do tempo ({self.arq})")
        return ids

    def faltam(self, ad):
        """Ids do AD que ainda não foram aprovados."""
        self.fresco()
        return [i for i in self.st["ads"].get(ad, []) if not self.st["segmentos"].get(i, {}).get("aprovado")]

    def limpar(self):
        return self.mexe(lambda st: self._limpar())

    def _limpar(self):
        usados = {self.st["segmentos"][i]["arquivo"] for ids in self.st["ads"].values() for i in ids if i in self.st["segmentos"]}
        usados |= {s["arquivo"] for s in self.st["segmentos"].values() if s.get("aprovado")}
        n = 0
        for raiz, _, arqs in os.walk(self.cache):
            for f in arqs:
                p = os.path.join(raiz, f)
                if f.endswith(".mkv") and p not in usados:
                    os.remove(p)
                    n += 1
        self.st["segmentos"] = {i: s for i, s in self.st["segmentos"].items() if s["arquivo"] in usados}
        return n

    def resumo(self):
        linhas = []
        for ad, ids in sorted(self.st["ads"].items()):
            partes = []
            for i in ids:
                s = self.st["segmentos"].get(i, {})
                partes.append(f"{i} ({s.get('dur', 0):.2f} s, {'APROVADO' if s.get('aprovado') else 'falta OK'})")
            linhas.append(f"{ad}: " + " + ".join(partes))
        return "\n".join(linhas) or "(linha do tempo vazia)"


# ---------------------------------------------------------------- sala e final
def sala(hook, depois, saida, seg_depois=2.0, lufs=-14):
    """Prévia de aprovação: `hook` + os primeiros `seg_depois` s de `depois` (None = o segmento sozinho). 720p NVENC
    (libx264 rápido fora do Windows), loudnorm de uma passada só para ouvir. Marcador .PREVIA.txt ao lado."""
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    ins = ["-i", hook] + (["-t", f"{seg_depois:.3f}", "-i", depois] if depois else [])
    n = 2 if depois else 1
    fc = "".join(f"[{i}:v][{i}:a]" for i in range(n)) + f"concat=n={n}:v=1:a=1[v0][a0];" \
         f"[v0]scale=720:1280:flags=lanczos,setsar=1[v];[a0]loudnorm=I={lufs}:TP=-1.5:LRA=11,aresample={SR},asetpts=N/SR/TB[a]"
    vc = ["-c:v", "h264_nvenc", "-b:v", "2500k", "-maxrate", "3500k", "-bufsize", "5M"] if sys.platform == "win32" else \
         ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23"]
    subprocess.run([ff(), "-nostdin", "-v", "error", "-y", *ins, "-filter_complex", fc, "-map", "[v]", "-map", "[a]", *vc,
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", saida],
                   check=True, timeout=TIMEOUT)
    open(saida + ".PREVIA.txt", "w", encoding="utf-8").write(
        "Sala por segmento (linha_do_tempo.py): não entregar. O final sai do `final` depois do OK de todos os segmentos.\n")
    return saida


def final(segs, saida, lufs=-14, tp=-1.5, w_out=720, h_out=1280, overlay=None, codec=None, tmp=None):
    """Junta os intermediários `segs` (na ordem) e exporta o AD. Um encode de vídeo só.
    overlay(ins_base) -> (ins_extra, filtros, rotulo_saida) aplica o que atravessa a emenda (banner) sobre "[vj]" (o vídeo
    já juntado, na tela de trabalho); None = nada por cima.
    Áudio: PCM juntado -> 1ª passada mede -> loudnorm LINEAR com os valores medidos num WAV à parte (mix e vídeo no mesmo
    comando já deu buraco no áudio, EV e TS) -> mux AAC. Depois, a 2ª passada do módulo loudnorm confere (não refaz se ok)."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import loudnorm
    tmp = tmp or tempfile.mkdtemp(prefix="ldt_final_")
    os.makedirs(tmp, exist_ok=True)
    n = len(segs)
    ins = sum([["-i", s] for s in segs], [])
    cru = os.path.join(tmp, "audio_cru.wav")
    # áudio completado até o fim do vídeo juntado: o -shortest do encode cortava 1-2 quadros do fim (prova 4382 VV, 17/11)
    tot_v = sum(_dur_video(x) for x in segs)
    subprocess.run([ff(), "-nostdin", "-v", "error", "-y", *ins, "-filter_complex",
                    "".join(f"[{i}:a]" for i in range(n)) + f"concat=n={n}:v=0:a=1,apad=whole_dur={tot_v:.6f}[a]", "-map", "[a]",
                    "-c:a", "pcm_s16le", "-ar", str(SR), cru], check=True, timeout=TIMEOUT)
    m = loudnorm.mede(cru, lufs, tp, ff())
    af = (f"loudnorm=I={lufs}:TP={tp}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,aresample={SR},asetpts=N/SR/TB")
    norm = os.path.join(tmp, "audio_norm.wav")
    subprocess.run([ff(), "-nostdin", "-v", "error", "-y", "-i", cru, "-af", af, "-c:a", "pcm_s16le", norm],
                   check=True, timeout=TIMEOUT)
    fc = ["".join(f"[{i}:v]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vj]"]
    ia = n
    ins_v = list(ins) + ["-i", norm]
    cur = "vj"
    if overlay:
        extra, filtros, cur = overlay(_conta_entradas(ins_v))
        ins_v += extra
        fc += filtros
    fc.append(f"[{cur}]scale={w_out}:{h_out}:flags=lanczos,setsar=1[vout]")
    sc = os.path.join(tmp, "final_fc.txt")
    open(sc, "w", encoding="utf-8").write(";".join(fc))
    local = os.path.join(tmp, os.path.basename(saida))
    fcs = "-/filter_complex" if _ff_versao() >= 7 else "-filter_complex_script"
    vc = codec or ["-c:v", "libx264", "-preset", "medium", "-crf", "20"]
    subprocess.run([ff(), "-nostdin", "-v", "error", "-y", *ins_v, fcs, sc, "-map", "[vout]", "-map", f"{ia}:a", *vc,
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", local],
                   check=True, timeout=TIMEOUT)
    r = loudnorm.duas_passadas(local, lufs, tp, 0.5, ff())
    os.makedirs(os.path.dirname(saida) or ".", exist_ok=True)
    if os.path.abspath(local) != os.path.abspath(saida):
        shutil.copyfile(local, saida)
    return saida, r


def _dur_video(arq):
    """Duração do vídeo pelo nº de quadros (FPS fixo do intermediário)."""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                        "stream=nb_read_packets", "-of", "csv=p=0", arq], capture_output=True, text=True)
    try:
        return int(r.stdout.strip().split(",")[0]) / FPS
    except ValueError:
        return dur(arq)


def _conta_entradas(ins):
    return sum(1 for x in ins if x == "-i")


_FFV = None


def _ff_versao():
    global _FFV
    if _FFV is None:
        try:
            _FFV = int(re.search(r"version n?(\d+)\.", subprocess.run([ff(), "-version"], capture_output=True, text=True).stdout)[1])
        except Exception:
            _FFV = 0
    return _FFV


def junta_wavs(wavs, saida):
    """Concatena WAVs (stems do checklist) na ordem; ignora os que não existem. Devolve saida ou None."""
    wavs = [w for w in wavs if w and os.path.exists(w)]
    if not wavs:
        return None
    ins = sum([["-i", w] for w in wavs], [])
    subprocess.run([ff(), "-nostdin", "-v", "error", "-y", *ins, "-filter_complex",
                    "".join(f"[{i}:a]" for i in range(len(wavs))) + f"concat=n={len(wavs)}:v=0:a=1[a]", "-map", "[a]",
                    "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", saida], check=True, timeout=TIMEOUT)
    return saida


# ---------------------------------------------------------------- linha de comando
if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    L = Linha(a[0])
    cmd, alvos = a[1], a[2:]
    if cmd == "status":
        print(L.resumo())
    elif cmd in ("aprovar", "reabrir"):
        for x in alvos:
            ids = L.aprovar(x, cmd == "aprovar")
            print(f"{'aprovado' if cmd == 'aprovar' else 'reaberto'}: {', '.join(ids)}")
        print(L.resumo())
    elif cmd == "limpar":
        print(f"{L.limpar()} intermediários sem uso apagados de {L.cache}")
    else:
        sys.exit(__doc__)
