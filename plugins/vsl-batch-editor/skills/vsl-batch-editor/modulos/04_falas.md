# Módulo: falas do avatar (gasta crédito: Kling; Seedance só em Drama ad; custo em `modulos/kie.md`)
**Geração pelo Kie desde 02/11/2026:** `kie.py kling3`, `kling4` e `seedance`. Os ids `kling3_0`, `kling4_0` e `seedance_2_5`, os `start_image` e os créditos por segundo abaixo são do Higgsfield; os comandos estão em `modulos/kie.md`.

**Seed Audio não existe no Kie.** A rota de guia Seed Audio descrita abaixo acabou: não gere guia novo. Marca ou termo técnico errado: refaça a fala no Kling 4.0 com o vídeo da F01 aprovado (`--video`) ou a voz em `--voz`, grafia fonética dentro da fala, e confira no Whisper e de ouvido. Rota ainda não testada no Kie. Não resolveu: avise o Fefo. VO sobre b-roll sem avatar depende de voz nova: pergunte ao Fefo antes de gerar.
Áudio NATIVO do modelo — sem lipsync colado depois. Use o áudio do próprio clipe.
**Drama ad no Seedance, batch antiga feita no Seedance ou rota Seed Audio:** `modulos/04b_seedance.md` (não abrir fora desses casos).

## Qual modelo: Kling e Omni; Seedance só em Drama ad
**Ordem do cliente (30/10/2026):** não usar mais Seedance, que é caro demais e desnecessário em ad curto e em ad que não
é drama. Falas, b-roll e revisão vão no Kling e, desde 02/11/2026, também no Gemini Omni (seção própria abaixo; validado
pelo Fefo com o Umut). Seedance só em **Drama ad**: o que o card ou o briefing chama assim; na dúvida, Kling e pergunte
ao Fefo.
| Caso | Modelo |
|---|---|
| Padrão: clipes de fala de 3–15 s, poucas falas, orçamento curto | **Kling 3.0** (`kling3_0`), `mode: std`, 9:16, `sound: on`, `start_image` = avatar aprovado (1,75/s) |
| A voz precisa ser **igual em todas as falas** (narrador, muitas falas); refazer uma fala com a mesma voz | **Kling 4.0** (`kling4_0`), 720p, reference-to-video com a 1ª fala aprovada como vídeo de referência (1,5/s). Passou na 3217; na 3219, image-to-video sem referência, a voz variou e 5 de 11 falas trocaram palavras |
| One take > 15 s; marca/número que o Kling erra; revisão de batch antiga feita no Seedance | Kling: quebre o take em clipes, use a grafia fonética, refaça a fala no Kling 4.0 e confira a voz. Não resolveu: pergunte ao Fefo antes de gastar Seedance |
| **Drama ad** | **Seedance 2.5** (`seedance_2_5`), `mode: omni_reference`, **720p**, `generate_audio: true`, `start_image` = avatar aprovado + `audio_references` (7/s) |

- **480p** só para teste de voz/ritmo antes do lote, nunca em take com frasco/rótulo legível. Vídeo final sempre 720p.

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

## Travar o prompt numa fala só (desde 02/11/2026)
Vale para Kling e Seedance. A inconsistência entre falas vem de mexer no prompt a cada clipe.
1. Gere 1 fala e julgue com rigor. Refaça a **mesma** fala até energia, enquadramento, ritmo e jeito ficarem certos.
2. Cada defeito vira uma regra fixa no fim do prompt (energia baixa, pouca confiança, fala lenta, sorriso faltando), em
   vez de reescrever o resto. Toda fala leva "one continuous take, no jump cuts".
3. Travou: **só a fala muda** até o fim do roteiro. Mudança de cenário ou posição é prompt novo, travado do mesmo jeito.
4. Diga sempre o movimento da câmera, mesmo sem movimento: "static, locked-off shot" ou "handheld UGC iPhone shot". Sem
   isso, a câmera deriva. Ordem do prompt no vídeo: movimento, tipo de câmera, cena, o que o avatar faz ("body still,
   mouth moving naturally, eye contact with the camera"), energia, fala entre aspas, regras fixas. Nos 14 blocos, isso
   cabe em CAMERA, ACTION, PERFORMANCE e AUDIO; as regras fixas vão em POSITIVE LOCKS.
5. Guarde o prompt travado (com personagem e voz) no fim de `00_roteiro/falas.md`: a iteração da batch reusa o mesmo avatar e
   a mesma voz sem começar de novo.
- **Energia:** no CAMERA ou PERFORMANCE, conforme o ref. Avatar sem energia sai chapado; em hook de UGC, teste energia
  alta antes de aceitar. A "emoção contida" do modelo acima é para o ref calmo, não regra para todo ad.
- **Ênfase em maiúscula (a testar no Kling):** escreva em caixa alta a palavra que deve pesar na fala. Não use em marca
  nem em termo técnico, que têm grafia própria em "Marca e números". Confira de ouvido e no Whisper.
- **Palavras de sobra no fim (a testar):** se a última palavra embola ou é cortada, some 3 ou 4 palavras neutras depois
  da frase e corte na edição. Pode trocar o segundo a mais de duração, que deixa a fala lenta. Medir antes de virar regra.

## Gemini Omni: liberado junto do Kling (Fefo com o Umut, 02/11/2026)
Omni e Kling podem andar na mesma batch; Seedance segue só em Drama ad. Ainda sem teste nosso e sem custo medido: mida
na 1ª fala e peça ok de crédito, como em todo lote. `kie.py omni`, 720p, durações 4, 6, 8 ou 10 s: fala entre duas durações usa a maior, com palavras de sobra
cortadas na edição. Omni Flash já barrou palavrão na Trendscale; no Omni cheio, não testado. Todo avatar do Omni sai com
os mesmos dentes: repare ao comparar dois avatares no mesmo ad. O vídeo não mostra marca difícil nem termo técnico:
compare com o Kling numa fala com "Vizzy-oh Vance" antes de confiar. Voz entre falas no Omni também não é abordada.

## Duração (errar aqui estraga o ritmo)
- **Kling 4.0** (`kling4_0`, 3217): `ceil(palavras/3,3 + 1,5)`. Com `round(pal/3,3 + 0,7)` ele cortou a última palavra em 4
  de 22 falas (voz a −15/−22 dB no último quadro; o Whisper não acusa). Confira a folga: voz terminando ≥ 0,15 s antes do
  fim do clipe (nível dos últimos 0,15 s < −35 dB); fala lenta se acerta com `velocidade` na montagem.
- **Kling**: duração ≥ fala estimada + ~1,5 s; conferir no Whisper se a última palavra termina antes do fim do clipe.
  Fala que vai até o fim (folga < 0,3 s) embola a última palavra ("windshield"): dê 1 s a mais.

## Marca e números
- **Kling: a grafia fonética vai DENTRO da fala**, não numa nota no fim do AUDIO. Nota "Pronunciation: zeaxanthin is
  zee-uh-ZAN-thin" saiu "zaxanthin"; "zee-uh-zanthin" dentro da fala (+1 s de duração) saiu certo. "dee-generation" na
  fala acertou 4 de 5; a nota "dih-JEN-er-AY-shun" voltou "degemination".
  - Neurobella: `Pronunciation: "Neurobella" is said "NOOR-oh-BELL-uh".` funcionou.
  - VisioVance: "Vizzy-oh Vance" na fala + nota "a crisp, clear 'Vance' that rhymes with 'dance'" → certo de primeira.
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
- **Kling demora a falar** (até 4 s): confira o início de cada corte antes da prévia.
- **Nível**: fala refeita/acelerada pode sair mais baixa que as vizinhas (F11 da 1980, −3,7 dB = "VO weird"): compare o
  LUFS de cada fala cortada com as vizinhas e iguale.
- **Ritmo**: palavras ÷ duração cortada ≈ 3,3 pal/s. Lento → campo `velocidade` na fala do plano (número ou
  {marca: número}, até ×1,2 continua natural; boca e voz juntas em `08_auto/rapido/`). Cru < 3 pal/s = refazer, não acelerar.
- Salve como o plano manda (`03_avatar/hold/F01.mp4`…) e anote IDs em `08_auto/falas_ids.tsv`. Antigos vão para
  `03_avatar/_antigos/`.
- Depois: `fluxo.py fazer` (cortes → prévias → legendas → ADs). Peça ao Fefo para ouvir a prévia; ajuste de corte
  vai em `08_auto/cortes/<clipe>.manual.json` (ex.: `[[0, 3.32]]`; em fala com `velocidade`, no tempo da cópia acelerada).
