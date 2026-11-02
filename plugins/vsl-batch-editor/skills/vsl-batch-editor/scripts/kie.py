#!/usr/bin/env python3
"""Kie.ai — saldo, upload e geração de vídeo com download (gerador das batches desde 02/11/2026).

Uso (--teste em qualquer geração mostra o pedido sem subir arquivo e sem gastar):
  python3 kie.py saldo
  python3 kie.py upload ARQ.png                         # devolve a URL (o Kie apaga em 24 h)
  python3 kie.py sunburst PROMPT.txt SAIDA.png [--ref A.png --ref B.png] [--res 2K] [--ratio 9:16]
        # GPT Image 2.5 Sunburst. Com --ref (até 16), edita ou usa referências; sem --ref, só texto.
  python3 kie.py nanopro PROMPT.txt SAIDA.png --ref QUADRO.png [--ref B.png] [--res 2K] [--ratio 9:16]
        # Nano Banana Pro (até 8 --ref). Avatar a partir de quadro real de UGC: ver modulos/03_personagens.md.
  python3 kie.py omni PROMPT.txt IMAGEM SAIDA.mp4 --dur 8 [--res 720p]
        # Gemini Omni com som. --dur só 4, 6, 8 ou 10. Liberado junto do Kling em 02/11/2026; custo ainda não medido.
  python3 kie.py kling3 PROMPT.txt IMAGEM SAIDA.mp4 --dur 5 [--mode std] [--sem-som] [--fim FIM.png]
        # IMAGEM = quadro inicial, ou "-" para só texto (sai 9:16).
  python3 kie.py kling4 PROMPT.txt SAIDA.mp4 --dur 5 [--video F01.mp4] [--imagem A.png] [--voz nome=AUDIO.mp3] [--res 720p]
        # Reference-to-video. No prompt: @video_1, @image_1, @nome. Toda menção precisa de arquivo. Sempre com som.
  python3 kie.py seedance PROMPT.txt SAIDA.mp4 --dur 8 [--imagem A.png] [--audio F01.mp3] [--res 720p] [--sem-som]
        # Só em Drama ad. Referências, sem quadro inicial: o Kie não aceita os dois juntos.
  python3 kie.py tts TEXTO.txt SAIDA.mp3 --voz ID [--speed 1]
        # ElevenLabs Multilingual v2. Só vozes prontas do catálogo, sem voz clonada.
  python3 kie.py espera TASK_ID SAIDA                   # retoma uma tarefa já criada, sem cobrar de novo

O taskId sai na tela e fica em SAIDA.task.json assim que a tarefa é criada: se cair a conexão, use `espera`,
não reenvie (cobra duas vezes). A mídia gerada some em 14 dias: baixar sempre.
A chave fica em ~/.vsl-batch-editor/kie_chave (fora do Drive e do zip; nunca em perfil.json, nota ou módulo).
"""
import json, mimetypes, os, secrets, sys, time, urllib.parse, urllib.request, urllib.error

API = 'https://api.kie.ai'
UPLOAD = 'https://kieai.redpandaai.co/api/file-stream-upload'   # host do exemplo dos docs
CHAVE = os.path.expanduser('~/.vsl-batch-editor/kie_chave')
UA = 'fefo-vsl/1.0'
ESPERA_MAX = 1200   # s
TESTE = '--teste' in sys.argv


def _chave():
    try:
        return open(CHAVE).read().strip()
    except FileNotFoundError:
        sys.exit(f'Sem chave em {CHAVE}')


def _pede(url, corpo=None, tipo='application/json'):
    req = urllib.request.Request(url, data=corpo, headers={
        'Authorization': f'Bearer {_chave()}', 'Content-Type': tipo, 'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f'HTTP {e.code}: {e.read().decode(errors="replace")[:400]}')
    if d.get('code') != 200:   # erro do Kie volta com HTTP 200 e o código no corpo
        sys.exit(f'Kie {d.get("code")}: {d.get("msg")}')
    return d['data']


def saldo():
    return _pede(f'{API}/api/v1/chat/credit')


def upload(caminho):
    limite = secrets.token_hex(16)
    nome = os.path.basename(caminho)
    tipo = mimetypes.guess_type(nome)[0] or 'application/octet-stream'
    corpo = b''.join([
        f'--{limite}\r\nContent-Disposition: form-data; name="uploadPath"\r\n\r\nvsl\r\n'.encode(),
        f'--{limite}\r\nContent-Disposition: form-data; name="file"; filename="{nome}"\r\n'
        f'Content-Type: {tipo}\r\n\r\n'.encode(),
        open(caminho, 'rb').read(),
        f'\r\n--{limite}--\r\n'.encode()])
    return _pede(UPLOAD, corpo, f'multipart/form-data; boundary={limite}')['downloadUrl']


def cria(modelo, entrada, saida):
    if TESTE:
        sys.exit(json.dumps({'model': modelo, 'input': entrada}, ensure_ascii=False, indent=1))
    corpo = json.dumps({'model': modelo, 'input': entrada}).encode()
    task = _pede(f'{API}/api/v1/jobs/createTask', corpo)['taskId']
    json.dump({'taskId': task, 'model': modelo, 'input': entrada},
              open(saida + '.task.json', 'w'), ensure_ascii=False, indent=1)
    print(f'taskId {task}', flush=True)
    return task


def espera(task, saida):
    fim = time.time() + ESPERA_MAX
    estado = None
    while time.time() < fim:
        d = _pede(f'{API}/api/v1/jobs/recordInfo?taskId={urllib.parse.quote(task)}')
        if d['state'] != estado:
            estado = d['state']
            print(estado, flush=True)
        if estado == 'fail':
            sys.exit(f'Falhou: {d.get("failCode")} {d.get("failMsg")}')
        if estado == 'success':
            url = json.loads(d['resultJson'])['resultUrls'][0]
            req = urllib.request.Request(url, headers={'User-Agent': UA})   # sem a chave: é outro host
            with urllib.request.urlopen(req, timeout=300) as r, open(saida, 'wb') as f:
                f.write(r.read())
            print(f'{saida} · {d.get("creditsConsumed")} cr · {d.get("costTime")} s')
            return d
        time.sleep(10)
    sys.exit(f'Sem resultado em {ESPERA_MAX} s. Retome com: python3 kie.py espera {task} {saida}')


def _opcao(args, nome, padrao=None):
    if nome in args:
        return args[args.index(nome) + 1]
    return padrao


def _opcoes(args, nome):
    return [args[i + 1] for i, x in enumerate(args) if x == nome]


def _sobe(caminho):
    return caminho if TESTE else upload(caminho)


def _texto(caminho):
    return open(caminho, encoding='utf-8').read().strip()


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] == 'saldo':
        print(saldo())
    elif a[0] == 'upload':
        print(upload(a[1]))
    elif a[0] == 'sunburst':
        prompt, saida = _texto(a[1]), a[2]
        refs = _opcoes(a, '--ref')
        entrada = {'prompt': prompt, 'aspect_ratio': _opcao(a, '--ratio', '9:16'), 'resolution': _opcao(a, '--res', '2K')}
        if refs:
            entrada['input_urls'] = [_sobe(r) for r in refs]
        tipo = 'image-to-image' if refs else 'text-to-image'
        espera(cria(f'gpt-image-2-5-sunburst-{tipo}', entrada, saida), saida)
    elif a[0] == 'nanopro':
        prompt, saida = _texto(a[1]), a[2]
        entrada = {'prompt': prompt, 'aspect_ratio': _opcao(a, '--ratio', '9:16'), 'resolution': _opcao(a, '--res', '2K'),
                   'output_format': 'png', 'image_input': [_sobe(r) for r in _opcoes(a, '--ref')]}
        espera(cria('nano-banana-pro', entrada, saida), saida)
    elif a[0] == 'omni':
        prompt, imagem, saida = _texto(a[1]), a[2], a[3]
        entrada = {'prompt': prompt, 'image_urls': [_sobe(imagem)], 'duration': _opcao(a, '--dur', '8'),
                   'aspect_ratio': '9:16', 'resolution': _opcao(a, '--res', '720p')}
        espera(cria('gemini-omni-video', entrada, saida), saida)
    elif a[0] == 'kling3':
        prompt, imagem, saida = _texto(a[1]), a[2], a[3]
        entrada = {'prompt': prompt, 'sound': '--sem-som' not in a, 'duration': _opcao(a, '--dur', '5'),
                   'mode': _opcao(a, '--mode', 'std'), 'multi_shots': False}
        if imagem == '-':
            entrada['aspect_ratio'] = '9:16'
        else:
            entrada['image_urls'] = [_sobe(imagem)] + [_sobe(f) for f in _opcoes(a, '--fim')]
        espera(cria('kling-3.0/video', entrada, saida), saida)
    elif a[0] == 'kling4':
        prompt, saida = _texto(a[1]), a[2]
        entrada = {'prompt': prompt, 'duration': int(_opcao(a, '--dur', '5')), 'resolution': _opcao(a, '--res', '720p'),
                   'aspect_ratio': '9:16'}
        if _opcoes(a, '--video'):
            entrada['video_urls'] = [_sobe(v) for v in _opcoes(a, '--video')]
        if _opcoes(a, '--imagem'):
            entrada['image_urls'] = [_sobe(i) for i in _opcoes(a, '--imagem')]
        if _opcoes(a, '--voz'):
            entrada['voices'] = [{'name': n, 'audio_url': _sobe(c)}
                                 for n, c in (v.split('=', 1) for v in _opcoes(a, '--voz'))]
        espera(cria('kling-4.0/reference-to-video', entrada, saida), saida)
    elif a[0] == 'seedance':
        prompt, saida = _texto(a[1]), a[2]
        entrada = {'prompt': prompt, 'duration': int(_opcao(a, '--dur', '5')), 'resolution': _opcao(a, '--res', '720p'),
                   'aspect_ratio': '9:16', 'generate_audio': '--sem-som' not in a}
        if _opcoes(a, '--imagem'):
            entrada['reference_image_urls'] = [_sobe(i) for i in _opcoes(a, '--imagem')]
        if _opcoes(a, '--audio'):
            entrada['reference_audio_urls'] = [_sobe(c) for c in _opcoes(a, '--audio')]
        espera(cria('bytedance/seedance-2-5', entrada, saida), saida)
    elif a[0] == 'tts':
        texto, saida = _texto(a[1]), a[2]
        voz = _opcao(a, '--voz') or sys.exit('tts pede --voz ID')
        entrada = {'text': texto, 'voice': voz, 'speed': float(_opcao(a, '--speed', '1'))}
        espera(cria('elevenlabs/text-to-speech-multilingual-v2', entrada, saida), saida)
    elif a[0] == 'espera':
        espera(a[1], a[2])
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
