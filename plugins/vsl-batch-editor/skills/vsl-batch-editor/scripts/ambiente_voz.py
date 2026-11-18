#!/usr/bin/env python3
"""Ambienta uma voz seca (TTS da ElevenLabs, do Kie ou locução de estúdio) no cômodo da cena. Fefo, 18/11/2026.

Por quê: voz de estúdio sobre cena de celular denuncia a IA (regra "Fala de UGC" em _FLUXO/QUALIDADE_DO_BATCH.md).
Três camadas, nesta ordem:
  1. microfone de celular: corta grave e agudo extremo e comprime de leve;
  2. reverb do cômodo: resposta ao impulso SINTÉTICA do preset (ruído com queda exponencial + primeiras reflexões),
     gerada aqui mesmo, sempre igual (semente fixa); não é gravação de um cômodo real;
  3. room tone: ruído de fundo baixo e contínuo, do primeiro ao último segundo.

Uso:
  py ambiente_voz.py ENTRADA.(wav|mp3|m4a) SAIDA.wav --ambiente banheiro|cozinha|quarto|carro [--dose 0.18]
                     [--ruido -52] [--sem-ruido] [--sem-celular]
  py ambiente_voz.py --lista                    # presets e o que cada um faz

NA MONTAGEM (18/11/2026): EV plano.json estilo.voz_ambiente e TS job.json voz_ambiente ligam config() + cadeia() dentro do
grafo da mixagem (fluxo_partes/montar.py e montagem_base.mixar). Sem a chave, a montagem não muda.

ORDEM NO JOB: o lip-sync (Omni, OmniHuman, Kling) recebe a voz SECA. A ambientação entra na mixagem, depois do
lip-sync e antes da trilha. A saída sai em 48 kHz mono, com o mesmo tempo da entrada (a cauda do reverb é cortada
no fim com fade de 0,15 s para não mudar a duração).
DOSE: fração do reverb somada à voz. 0,18 é o padrão, de propósito baixo: a fala continua clara e o checklist
(item 3, VO contra o roteiro; item 4, voz contra trilha) continua valendo. Acima de 0,35 o script avisa.
Não substitui a geração com som: clipe do Omni ou do Kling que já vem com o ambiente não passa por aqui.
"""
import argparse, os, struct, subprocess, sys, tempfile, wave

SR = 48000
# rt60 = tempo de queda do reverb (s); brilho = corte de agudo da cauda (Hz); pre = atraso até a 1ª reflexão (ms);
# refl = (atraso em ms, ganho) das primeiras reflexões; tom = cor do ruído de fundo e corte (Hz)
PRESETS = {
    'banheiro': {'rt60': 0.55, 'brilho': 6500, 'pre': 6, 'refl': [(7, 0.55), (13, 0.40), (21, 0.30), (34, 0.20)],
                 'ruido': ('white', 3500), 'desc': 'azulejo: cauda curta e clara, reflexões fortes'},
    'cozinha':  {'rt60': 0.40, 'brilho': 5000, 'pre': 9, 'refl': [(11, 0.40), (19, 0.28), (31, 0.18)],
                 'ruido': ('pink', 1200), 'desc': 'cômodo duro médio, zumbido de geladeira no fundo'},
    'quarto':   {'rt60': 0.25, 'brilho': 3200, 'pre': 12, 'refl': [(14, 0.25), (27, 0.14)],
                 'ruido': ('brown', 900), 'desc': 'cômodo com cama e cortina: quase seco, cauda abafada'},
    'carro':    {'rt60': 0.10, 'brilho': 2800, 'pre': 2, 'refl': [(3, 0.50), (5, 0.35), (8, 0.20)],
                 'ruido': ('brown', 400), 'desc': 'cabine pequena: sem cauda, reflexões coladas, ronco grave'},
}


def impulso(nome):
    """Resposta ao impulso sintética do preset, gravada num wav temporário (cache por preset). Devolve o caminho."""
    import numpy as np
    p = PRESETS[nome]
    arq = os.path.join(tempfile.gettempdir(), f'ambiente_voz_ir_{nome}_v1.wav')
    if os.path.exists(arq):
        return arq
    rng = np.random.default_rng(20261118)
    n = int(SR * (p['rt60'] * 1.6 + 0.05))
    t = np.arange(n) / SR
    cauda = rng.standard_normal(n) * np.exp(-6.91 * t / p['rt60'])           # -60 dB em rt60
    k = np.exp(-2 * np.pi * p['brilho'] / SR)                                 # passa-baixa de 1 polo na cauda
    y = np.zeros(n); a = 0.0
    for i in range(n):
        a = (1 - k) * cauda[i] + k * a; y[i] = a
    ini = int(SR * p['pre'] / 1000)
    ir = np.zeros(n + ini); ir[ini:] = y * 0.35
    for ms, g in p['refl']:
        ir[int(SR * ms / 1000)] += g
    ir /= np.sqrt((ir ** 2).sum())                                            # energia 1: a dose manda no nível
    pcm = (np.clip(ir, -1, 1) * 32767).astype('<i2').tobytes()
    with wave.open(arq, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm)
    return arq


def config(valor):
    """Normaliza a chave do plano/job. Aceita "banheiro" ou {"ambiente": "banheiro", "dose": 0.18, "ruido_db": -52,
    "celular": true}. Devolve o dict completo, ou None quando não há ambiente (montagem segue como sempre)."""
    if not valor:
        return None
    c = {'ambiente': valor} if isinstance(valor, str) else dict(valor)
    if c.get('ambiente') not in PRESETS:
        raise SystemExit(f"voz_ambiente: ambiente {c.get('ambiente')!r} não existe (use {', '.join(sorted(PRESETS))})")
    c = {'ambiente': c['ambiente'], 'dose': float(c.get('dose', 0.18)), 'ruido_db': c.get('ruido_db', -52.0),
         'celular': bool(c.get('celular', True))}
    if not 0 <= c['dose'] <= 0.5:
        raise SystemExit(f"voz_ambiente: dose {c['dose']:g} fora de 0 a 0,5")
    return c


def cadeia(cfg, ent, sai, sr=48000, canais='stereo', pref='amb'):
    """Trecho de filter_complex que recebe [ent] (a voz seca) e entrega [sai] (a voz no cômodo), sem entrada nova no
    ffmpeg: o impulso entra por amovie e o room tone por anoisesrc. cfg = config(...). O stem de voz do checklist deve
    sair ANTES desta cadeia (pausas e voz x trilha são medidas na voz seca)."""
    p = PRESETS[cfg['ambiente']]
    ir = impulso(cfg['ambiente']).replace('\\', '/').replace(':', '\\:')
    mic = ('highpass=f=110,lowpass=f=9500,acompressor=threshold=-18dB:ratio=2.5:attack=8:release=120:makeup=1'
           if cfg['celular'] else 'anull')
    f = [f"[{ent}]aresample={SR},aformat=channel_layouts=mono,{mic},asplit[{pref}d][{pref}w]",
         f"amovie='{ir}',aresample={SR}[{pref}i]",
         f"[{pref}w][{pref}i]afir=irnorm=-1:gtype=none[{pref}m]"]
    fim = f"aresample={sr},aformat=channel_layouts={canais}[{sai}]"
    if cfg['ruido_db'] is None:
        f.append(f"[{pref}d][{pref}m]amix=inputs=2:weights='1 {cfg['dose']:.3f}':normalize=0,{fim}")
    else:
        cor, corte = p['ruido']
        f += [f"[{pref}d][{pref}m]amix=inputs=2:weights='1 {cfg['dose']:.3f}':normalize=0[{pref}v]",
              f"anoisesrc=color={cor}:amplitude={10 ** (float(cfg['ruido_db']) / 20):.6f}:sample_rate={SR}:seed=7,"
              f"lowpass=f={corte},highpass=f=60[{pref}n]",
              f"[{pref}v][{pref}n]amix=inputs=2:duration=first:normalize=0,{fim}"]
    return ';'.join(f)


def duracao(arq):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', arq],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def ambientar(entrada, saida, ambiente, dose=0.18, ruido_db=-52.0, com_ruido=True, celular=True):
    p = PRESETS[ambiente]; d = duracao(entrada); ir = impulso(ambiente)
    mic = 'highpass=f=110,lowpass=f=9500,acompressor=threshold=-18dB:ratio=2.5:attack=8:release=120:makeup=1' if celular else 'anull'
    f = [f'[0:a]aresample={SR},aformat=channel_layouts=mono,{mic},asplit[seco][w0]',
         f'[1:a]aresample={SR}[ir]',
         # irnorm=-1 e gtype=none: o impulso já sai com energia 1; o padrão do afir derrubava o reverb em ~32 dB
         '[w0][ir]afir=irnorm=-1:gtype=none[molhado]',
         f"[seco][molhado]amix=inputs=2:weights='1 {dose:.3f}':normalize=0[voz]"]
    ult = 'voz'
    if com_ruido:
        cor, corte = p['ruido']
        amp = 10 ** (ruido_db / 20)
        f += [f'anoisesrc=color={cor}:amplitude={amp:.6f}:sample_rate={SR}:duration={d + 0.5:.3f}:seed=7,lowpass=f={corte},highpass=f=60[rt]',
              '[voz][rt]amix=inputs=2:duration=first:normalize=0[mix]']
        ult = 'mix'
    f.append(f'[{ult}]atrim=0:{d:.3f},afade=t=out:st={max(0, d - 0.15):.3f}:d=0.15,alimiter=limit=0.891[out]')
    cmd = ['ffmpeg', '-v', 'error', '-y', '-i', entrada, '-i', ir, '-filter_complex', ';'.join(f), '-map', '[out]',
           '-ar', str(SR), '-ac', '1', '-c:a', 'pcm_s16le', saida]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit('ffmpeg falhou: ' + r.stderr.strip()[-600:])
    return d


def main():
    for s in (sys.stdout, sys.stderr):
        try: s.reconfigure(encoding='utf-8')
        except Exception: pass
    ap = argparse.ArgumentParser(description='Ambienta uma voz seca no cômodo da cena.')
    ap.add_argument('entrada', nargs='?'); ap.add_argument('saida', nargs='?')
    ap.add_argument('--ambiente', choices=sorted(PRESETS)); ap.add_argument('--dose', type=float, default=0.18)
    ap.add_argument('--ruido', type=float, default=-52.0, help='nível do room tone em dBFS (padrão -52)')
    ap.add_argument('--sem-ruido', action='store_true'); ap.add_argument('--sem-celular', action='store_true')
    ap.add_argument('--lista', action='store_true')
    a = ap.parse_args()
    if a.lista:
        for n, p in PRESETS.items():
            print(f"{n:9} rt60 {p['rt60']:.2f} s · {p['desc']}")
        return 0
    if not (a.entrada and a.saida and a.ambiente):
        ap.error('faltou ENTRADA, SAIDA ou --ambiente')
    if not 0 <= a.dose <= 1:
        ap.error('--dose vai de 0 a 1')
    if os.path.abspath(a.entrada) == os.path.abspath(a.saida):
        sys.exit('RECUSADO: a saída não pode ser o arquivo de entrada (a voz seca fica para o lip-sync).')
    if a.dose > 0.35:
        print(f'aviso: dose {a.dose:g} acima de 0,35: confira a transcrição (checklist item 3) antes de usar', file=sys.stderr)
    d = ambientar(a.entrada, a.saida, a.ambiente, a.dose, a.ruido, not a.sem_ruido, not a.sem_celular)
    print(f'ok {a.saida} · {a.ambiente} · dose {a.dose:g} · room tone {"não" if a.sem_ruido else f"{a.ruido:g} dBFS"} · {d:.2f} s')
    return 0


if __name__ == '__main__':
    sys.exit(main())
