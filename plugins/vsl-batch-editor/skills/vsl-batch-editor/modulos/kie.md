# Kie
**Toda geração das batches sai pelo Kie desde 02/11/2026** (decisão do Fefo), por `scripts/kie.py`. A chave fica em
`~/.vsl-batch-editor/kie_chave`, fora do Drive e do zip; nunca em `perfil.json`, nota ou módulo. Não existe MCP nem
workspace: a chave é da conta inteira, e cada cliente tem a sua. Sem chave, pare e avise. O Higgsfield só entra com
pedido do Fefo (`modulos/higgsfield.md`).

## Comandos
`--teste` mostra o pedido sem subir arquivo e sem gastar. Rode antes do 1º pedido de cada lote.
| Uso | Comando | Modelo no Kie |
|---|---|---|
| Quadro, personagem, frasco | `kie.py sunburst P.txt S.png --ref A.png --ref B.png --res 2K` | `gpt-image-2-5-sunburst-image-to-image` (sem `--ref`, `-text-to-image`) |
| Avatar a partir de quadro real de UGC | `kie.py nanopro P.txt S.png --ref QUADRO.png --res 2K` | `nano-banana-pro` (até 8 `--ref`; regra em `03_personagens.md`) |
| Fala no Gemini Omni, junto do Kling (liberado em 02/11) | `kie.py omni P.txt A.png S.mp4 --dur 8` | `gemini-omni-video` (`--dur` 4, 6, 8 ou 10; ver `04_falas.md`) |
| B-roll e fala padrão | `kie.py kling3 P.txt QUADRO.png S.mp4 --dur 5 --sem-som [--fim FIM.png]` | `kling-3.0/video` (`-` no lugar do quadro = só texto) |
| Voz igual entre falas | `kie.py kling4 P.txt S.mp4 --dur 6 --video F01.mp4 [--imagem A.png] [--voz Nome=A.mp3]` | `kling-4.0/reference-to-video` |
| Só Drama ad | `kie.py seedance P.txt S.mp4 --dur 8 --imagem A.png --audio F01.mp3` | `bytedance/seedance-2-5` |
| Voz pronta do catálogo | `kie.py tts T.txt S.mp3 --voz ID` | `elevenlabs/text-to-speech-multilingual-v2` |
| VO quando o ElevenLabs falha (03/11) | `python3 BATCH#3826/08_auto/gemini_tts.py T.txt S.wav VOZ` | `google/gemini-2-5-pro-tts` (~0,8 cr/11 s) |

- Kling 4.0: toda menção no prompt (`@video_1`, `@image_1`, `@Nome`) precisa de arquivo no pedido, senão falha. O nome
  da voz leva só letras, dígitos e `_`. Sem vídeo de referência, sempre sai com som. Não há `mode`.
- Seedance: quadro inicial e referências não andam juntos no mesmo pedido; o `kie.py` usa referências.
- ElevenLabs: só as 67 vozes prontas (por ID; Matilda/Sarah/Rachel não existem lá), sem voz clonada e sem áudio de referência. Em 03/11 ficou fora o dia todo (500 timeout); o Gemini TTS fez a VO.
- **Seed Audio não existe no Kie** (docs conferidas em 02/11/2026). Ver `04_falas.md`.
- Existem e não foram testados: Kling 3.0 Omni, Kling 3.0 Turbo, Kling 4.0 Keyframe, Seedance 2.5 Draft, Seedream 5.0 Pro.

## Regras
- **Crédito só com ok.** `kie.py saldo` antes de cada lote. Falha não cobra.
- Custo real: `creditsConsumed` no fim de cada geração, anotado em `08_auto/*_ids.tsv`. 1 cr ≈ US$ 0,005. O crédito do
  Kie não é o do Higgsfield: Kling 3.0 std 5 s com som = 100 cr (3217, 31/10). Kling 4.0 720p com som: 34 cr/s (3222). GPT Image 2.5 Sunburst 2K (texto ou com --ref): 10 cr. Kling 3.0 std 5 s sem som: 70 cr (14 cr/s), sai 716x1280 24 fps (3825, 03/11). Os
  demais, medir no 1º uso. Os números de crédito antigos dos módulos e do `CALIBRACAO.md` são do Higgsfield.
- Em paralelo (Fefo, 04/11/2026): um `kie.py` em segundo plano por geração, ~10–15 s entre disparos, cada um com o seu log; nada de fila única. O limite do Kie é 20 pedidos novos por 10 s.
- Caiu a conexão: `kie.py espera <taskId> <saída>` (o id fica em `<saída>.task.json`). **Não reenvie: cobra de novo.**
- O `kie.py` baixa o resultado na hora. A mídia gerada some em 14 dias e o upload em 24 h: o arquivo que vale é o local,
  e o script sobe de novo a cada pedido.
- Erro volta com HTTP 200: o script já lê o `code` do corpo.
- O callback do banco de conteúdo com o Kie ainda não está combinado com o Daniel.
