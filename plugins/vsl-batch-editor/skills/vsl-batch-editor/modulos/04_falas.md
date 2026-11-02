# Módulo: falas do avatar (gasta crédito: Kling; Seedance só em Drama ad; custo em `modulos/kie.md`)
**Geração pelo Kie desde 02/11/2026:** `kie.py kling3`, `kling4` e `seedance`. Os ids `kling3_0`, `kling4_0` e `seedance_2_5`, os `start_image` e os créditos por segundo abaixo são do Higgsfield; os comandos estão em `modulos/kie.md`.

**Seed Audio não existe no Kie.** A rota de guia Seed Audio descrita abaixo acabou: não gere guia novo. Marca ou termo técnico errado: refaça a fala no Kling 4.0 com o vídeo da F01 aprovado (`--video`) ou a voz em `--voz`, grafia fonética dentro da fala, e confira no Whisper e de ouvido. Rota ainda não testada no Kie. Não resolveu: avise o Fefo. VO sobre b-roll sem avatar depende de voz nova: pergunte ao Fefo antes de gerar.
Áudio NATIVO do modelo — sem lipsync colado depois. Use o áudio do próprio clipe.

## Qual modelo: Kling; Seedance só em Drama ad
**Ordem do cliente (30/10/2026):** não usar mais Seedance, que é caro demais e desnecessário em ad curto e em ad que não
é drama. Só Kling, em falas, b-roll e revisão. Seedance só em **Drama ad**: o que o card ou o briefing chama assim; na
dúvida, Kling e pergunte ao Fefo.
| Caso | Modelo |
|---|---|
| Padrão: clipes de fala de 3–15 s, poucas falas, orçamento curto | **Kling 3.0** (`kling3_0`), `mode: std`, 9:16, `sound: on`, `start_image` = avatar aprovado (1,75/s) |
| A voz precisa ser **igual em todas as falas** (narrador, muitas falas); refazer uma fala com a mesma voz | **Kling 4.0** (`kling4_0`), 720p, reference-to-video com a 1ª fala aprovada como vídeo de referência (1,5/s). Passou na 3217; na 3219, image-to-video sem referência, a voz variou e 5 de 11 falas trocaram palavras |
| One take > 15 s; marca/número que o Kling erra; revisão de batch antiga feita no Seedance | Kling: quebre o take em clipes, use a grafia fonética, refaça a fala no Kling 4.0 e confira a voz. Não resolveu: pergunte ao Fefo antes de gastar Seedance |
| **Drama ad** | **Seedance 2.5** (`seedance_2_5`), `mode: omni_reference`, **720p**, `generate_audio: true`, `start_image` = avatar aprovado + `audio_references` (7/s) |

As notas de Seedance abaixo valem para Drama ad e para entender batch antiga. O que pesa entre os dois (BATCH#1977 no
Kling × BATCH#1980 no Seedance, 15/10/2026):
| | Kling 3.0 std | Seedance 2.5 720p |
|---|---|---|
| Custo real | 15 falas = 359 cr em 23 gerações (7 refeitas) | 91 s de fala = 637 cr |
| Voz | muda um pouco entre takes (o Kling não aceita áudio de referência) | igual em todos os takes com `audio_references` (F0 170–180 Hz nos 16 takes) |
| Mãos | levanta a mão em ~metade dos takes, mesmo com trava | estável |
| Começo | começa a falar entre 0 e 4 s | fala logo |
| Defeitos típicos | mão deformada subindo; última palavra embolada se a fala vai até o fim do clipe | repete palavra ("is, is"); **estalo ~50 ms antes do fim de todo clipe**; mostra o celular se o prompt citar |
| Marca | grafia fonética dentro da fala acerta | "VisioVance" pode exigir a rota Seed Audio (abaixo) |

- **480p** (3/s) só para teste de voz/ritmo antes do lote; nunca em take com frasco/rótulo legível. 1080p existe (mais caro) e
  ainda não foi necessário.
- Pelo MCP o Seedance sai **com áudio** e não barrou "strong erections" (pelo site saía mudo e barrava).
- `start_image` no Seedance vira referência: o enquadramento sai um pouco mais aberto que o quadro.
- Kling e Seedance sugerem o preset "IN THE DARK" (ou um com o nome da cena) em quase todo pedido com `start_image`,
  até de dia: mande já com `declined_preset_id` (não cobra).

## Prompt (Kling e Seedance): estrutura de 14 blocos de `prompts.md`
Personagem, cenário e enquadramento vêm do ad em `01_refs/` (`plano.json` → `estilo`) e da imagem aprovada. Modelo:
```
SCENE CONTEXT: <NOME>, <idade/aparência>, talks to camera <onde>, <hora do dia>, <por que está falando>.
ACTIVE REFERENCES: start frame = <NOME> as approved [; audio reference = <NOME>'s voice — use it ONLY for voice identity].
LOCATION MAP: <primeiro plano / meio / fundo do cenário>; camera <posição no espaço>.
FIRST FRAME: framed exactly as the start frame, <enquadramento>, already mid-conversation.
FORMAT MODE: single continuous shot, no cuts.
OPTICS: ~<70>° horizontal FOV, <distância>.
CAMERA: <operador e intenção, ex.: handheld selfie at arm's length, small natural sway>.
ACTION: <beats com tempo; mãos baixas, longe da câmera>.
PERFORMANCE: <estado interno: para quem fala, objetivo, emoção — contida>.
PHYSICS: <contato/peso relevante, ex.: phone held steady, shirt fabric moves with breathing>.
LIGHTING: <fonte real>, catchlight in the eyes, shadows motivated by it, same as the start frame.
AUDIO: <NOME>'s voice: <timbre, sotaque, ritmo>. <NOME> says, word for word, in English: "<FALA>". Only <NOME>'s voice and room tone, no music.
STYLE: <look do ref, ex.: UGC smartphone footage>, 9:16 vertical, natural grain, real-time speed.
POSITIVE LOCKS: face, hair, outfit and setting stay exactly as in the start frame; accurate lip sync with the mouth fully visible; the frame stays clean with no on-screen text; one person only.
```
- Exemplo antigo (formato corrido, BATCH_2080): `BATCH_2080/00_roteiro/falas.md`.
- Gestual: mãos longe da câmera (mão/relógio em primeiro plano deforma — "AI avatar is terrible").
- **Trava de mãos no Kling** (1977): "hands stay low" não basta. Funcionou: "both hands rest still on her lap below the
  steering wheel for the entire clip and never rise into the frame; no hand gestures" + lock "the lower part of the
  frame shows only her sweatshirt and the top of the steering wheel"; "both hands tucked between her knees" também.
  No Seedance, médico na mesa (3215, 25 takes sem uma mão subindo): "hands loosely clasped beside the eye model… never
  rise toward the camera".
- **Setup "celular na mesa" (selfie sem mão)**: não cite o celular no LOCATION MAP — com "phone on the side table in the
  foreground" o Seedance mostrou o celular em pé na frente (1980). Descreva só a câmera: "camera at chest height, about
  one meter in front of her". Nem em outro bloco: "phone camera on a small tripod" pôs um celular deitado na borda de
  baixo da F10 da 3214 (faixa escura em 18/18 quadros) — o prompt da mesa vai sem "phone".
- Pronúncia da marca: ver "Marca e números" abaixo.

## Duração (errar aqui estraga o ritmo)
- **Kling 4.0** (`kling4_0`, 3217): `ceil(palavras/3,3 + 1,5)`. Com `round(pal/3,3 + 0,7)` ele cortou a última palavra em 4
  de 22 falas (voz a −15/−22 dB no último quadro; o Whisper não acusa). Confira a folga: voz terminando ≥ 0,15 s antes do
  fim do clipe (nível dos últimos 0,15 s < −35 dB); fala lenta se acerta com `velocidade` na montagem.
- **Kling**: duração ≥ fala estimada + ~1,5 s; conferir no Whisper se a última palavra termina antes do fim do clipe.
  Fala que vai até o fim (folga < 0,3 s) embola a última palavra ("windshield"): dê 1 s a mais.
- **Seedance**: duração ≈ palavras ÷ 3,3 + 0,5 s (mín. 4 s), ou a duração do áudio de referência arredondada para cima.
  Sobra > 1 s = fala lenta e picotada (microsilêncios entre palavras); curta demais comprime palavras ("compsulas").
  Linha curta (8–10 palavras) no mínimo de 4 s sai a 2,5–2,8 pal/s; o corte de silêncio sobe para ~3,2.
  Arredonde para o inteiro mais próximo, não para cima: `round(palavras/3,3 + 0,6)` deu 2,9–3,3 pal/s cru nas 25 falas da
  3215, o `ceil` deixou as mais lentas a 2,8. Palavra longa (meso-zeaxanthin) +1 s. O Seedance **enche a duração pedida**:
  segundo a mais = fala mais lenta, não folga (a folga antes do estalo vem do corte; H1 da 3214 com 7 s = 2,7 pal/s).
  Hook de selfie andando (6 s) sai a 2,7–2,9 pal/s → `velocidade` 1,08–1,15; a hold sentada (11–13 s) já sai a 3,0–3,3.

## Voz igual em todos os clipes (Seedance)
- Rota que deu certo (1980): gere a **F01 com a voz nativa** do Seedance (sem áudio de referência), aprove a voz com o
  Fefo e use o áudio da F01 (~6 s, sem marca nem número) como `audio_references` de todas as outras falas.
- `audio_references` = trecho de ~6 s de **outra** fala aprovada da mesma voz, **sem** a frase que muda, sem números,
  oferta ou marca — com o take inteiro/a própria fala antiga ele repete as palavras da referência ("74%" em vez de 71).
- No prompt: "use the audio reference ONLY for voice identity; do NOT repeat its words".
- Alternativa: gerar a fala inteira no Seed Audio (`seed_audio`, voz clonada de um trecho sem a marca) e passar esse áudio
  como `audio_references` — o Seedance segue palavra por palavra com lip-sync ("follow its timing and pronunciation").
- Entrega: "fast, fluent, one single breath, no pauses between words, no stretched words"; frase longa que não pode cair
  o tom: "'…molecule that won the Nobel Prize…' is ONE continuous phrase, no falling tone after 'molecule'".

## Marca e números
- **Kling: a grafia fonética vai DENTRO da fala**, não numa nota no fim do AUDIO. Nota "Pronunciation: zeaxanthin is
  zee-uh-ZAN-thin" saiu "zaxanthin"; "zee-uh-zanthin" dentro da fala (+1 s de duração) saiu certo. "dee-generation" na
  fala acertou 4 de 5; a nota "dih-JEN-er-AY-shun" voltou "degemination".
  - Neurobella: `Pronunciation: "Neurobella" is said "NOOR-oh-BELL-uh".` funcionou.
  - VisioVance: "Vizzy-oh Vance" na fala + nota "a crisp, clear 'Vance' that rhymes with 'dance'" → certo de primeira.
- **Seedance**: grafia fonética **dentro** da fala — "Neuro-Bella". VisioVance é instável: "Vizzy-oh Vance" + "VIZ-ee-oh
  VANCE, NOT 'vivo'" deu certo na 2822 e saiu "VizioVaints" na 1980; "Vizio Vance" direto sai "Vivo Vance";
  "Visio-Vance" sai "Vage/Vade". Nota "pronunciation guide, not spoken" foi FALADA — não use.
  **Pronúncia aprovada pelo Fefo (2480, "pronúncia 6"): Seed Audio com a grafia "Visio Vance", speech_rate 5** → guia
  do Seedance. "Vizio Vance" (abaixo, rota antiga da 1980) foi reprovada na 3214: não usar.
  **Rota Seed Audio para a marca** (1980): `seed_audio` com `audio_references` = F01 (voz, sem marca), texto com
  "Vizio Vance", speech_rate 10 (lento, marca nítida; com 40 a marca embola) → aparar e acelerar ×1,35 no ffmpeg →
  `audio_references` do Seedance 720p ("follow its timing and pronunciation"). ~1 cr por teste de Seed Audio.
  **Termos técnicos no Seedance** (macula, lutein, degeneration, fovea, meso-zeaxanthin): a grafia fonética falhou em
  ~40% das falas da 3214 ("deterioration", "demesia", "Luton", "maxilla"). Fala com termo técnico vai pelo guia Seed
  Audio (texto escrito normal, mesma voz) como `audio_references`; F03 e F10 da 3214 acertaram de primeira assim.
  Guia lento: não acelere a fala inteira no ffmpeg (embola); mande o guia original e use `velocidade` na montagem.
  Tom do guia: com `audio_references` = 6,5 s da F01, o Seed Audio sai a 106–136 Hz conforme o texto e o rate (F01 = 121).
  Se destoar da voz, corrija no ffmpeg (`asetrate=44100*r,aresample=44100,atempo=1/r`, r = F0 alvo ÷ F0 do guia; o
  Whisper continua ouvindo certo). `pitch_rate −2` com "Vizio Vance" embolou a marca ("VZO Vance"); com "Visio Vance"
  rate 5 passou (F16/F19 da 3215, com a dica "crisp, clear 'Vance' with a sharp 'nce' sound" no prompt do Seedance).
- "ED" sai como palavra: escreva "E.D.".
- **Não remendar** a marca/número colando voz clonada: refazer a fala inteira.
- Conferir no Whisper **medium sem dica de vocabulário E large-v3** a marca e todo número da oferta. O large-v3
  "corrige" pronúncia errada (ouviu "degeneration" onde o take dizia "degemination"): se QUALQUER modelo ouvir diferente
  da copy, é suspeito — peça ao Fefo para ouvir. Suspeito não é reprovado: "macula" saiu "maxilla"/"mesela" nos dois
  modelos e o Fefo ouviu e aprovou (3215). **Mas o cliente reprovou** na 3214 V1 ("VO says macula wrong", "lutein is
  said wrong", "says trials wrong") as falas que o Whisper marcava ("maculus", "maxilla", "Lutitin", "tries") e o Fefo
  tinha deixado passar: termo técnico suspeito → refazer pelo guia Seed Audio antes da entrega. "lutein" não se confere
  pelo Whisper (ele escreve certo onde o cliente ouviu errado). **VisioVance não se confere pelo texto do Whisper**: o large-v3 escreve
  "VizioVans" até no guia aprovado e nos takes certos (3214). Compare de ouvido guia × take (vídeo com os dois em
  sequência) e mande ao Fefo antes de montar.

## Depois de gerar
- Faça 2–3 clipes primeiro e peça ao Fefo para ouvir (voz igual?). Depois **um pedido por vez** (~10–15 s de intervalo).
- **Prancha de quadros de TODO take** procurando texto/legenda inventada pelo modelo e mão deformada — refazer se houver.
  Mão na faixa de baixo (y > 78%) dá para achar com um detector simples de pele.
- Kling com mão subindo: só refaça se cai em trecho em que o avatar aparece (confira no plano o que o b-roll cobre);
  hook coberto 100% por b-roll e fala inteira sob b-roll aceitam.
- **Seedance: estalo no fim do clipe.** Todo clipe do Seedance 2.5 tem um estalo de ~20 ms (−30 dB, 15–20 dB acima do
  ruído) uns 40–60 ms antes do fim do arquivo. O corte da fala tem de terminar ANTES dele: corte que vai até o fim do
  clipe = "weird sound whenever there is a new scene", e o estalo ainda impede o corte do silêncio final (sobra ~0,5 s
  parado entre falas = "deadspace"). Confira o envelope dos últimos 100 ms de cada clipe.
  O estalo fica 35–55 ms antes do fim do **áudio** (21 de 25 takes da 3215), e o áudio do clipe às vezes é mais curto que
  o vídeo: o teto do `fluxo.py` (duração do vídeo − 0,08 s) passou do estalo em 7 dos 25. Em toda fala do Seedance, depois
  do `fazer --ate cortes`: `python3 scripts/estalo.py "<batch>" F01 F02 … H1 …` (só mostra) e, conferido,
  `--gravar` (grava `<clipe>.manual.json` terminando 8 ms antes do estalo; não mexe em manual que já existe).
- **Seedance repete palavra** ("is, is"): ouça/Whisper em todo take; o corte manual que tira a repetição não pode cair
  dentro da palavra vizinha (na 1980 caiu dentro de "happening" = "VO wrong").
- **Kling demora a falar** (até 4 s): confira o início de cada corte antes da prévia.
- **Nível**: fala refeita/acelerada pode sair mais baixa que as vizinhas (F11 da 1980, −3,7 dB = "VO weird"): compare o
  LUFS de cada fala cortada com as vizinhas e iguale.
- **Ritmo**: palavras ÷ duração cortada ≈ 3,3 pal/s. Lento → campo `velocidade` na fala do plano (número ou
  {marca: número}, até ×1,2 continua natural; boca e voz juntas em `08_auto/rapido/`). Cru < 3 pal/s = refazer, não acelerar.
- Salve como o plano manda (`03_avatar/hold/F01.mp4`…) e anote IDs em `08_auto/falas_ids.tsv`. Antigos vão para
  `03_avatar/_antigos/`.
- Depois: `fluxo.py fazer` (cortes → prévias → legendas → ADs). Peça ao Fefo para ouvir a prévia; ajuste de corte
  vai em `08_auto/cortes/<clipe>.manual.json` (ex.: `[[0, 3.32]]`; em fala com `velocidade`, no tempo da cópia acelerada).
