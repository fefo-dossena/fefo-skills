# Módulo: b-roll (gasta crédito: Sunburst por quadro + Kling sem som; custo em `modulos/kie.md`)
**Antes de tudo: módulo `banco` (`05a_banco.md`).** Sem `08_auto/banco_reuso.tsv`, não gere. Este módulo só roda as cenas NEW.
1. **Quadros iniciais** (cenas com `ref` ≠ `-`): GPT Image 2.5 Sunburst (`kie.py sunburst --res 2K`)
   com as referências certas em `--ref` (PNGs dos personagens/frascos do plano). Ordem das referências =
   "Image 1, Image 2…" no prompt. Agrupe por conjunto de referências (N → NW → W → B → BN → BNC → BC; depois a outra
   marca — de preferência editando o quadro aprovado só no frasco, ver `03_personagens.md`).
   Prompt do quadro com os blocos de imagem (●) de `modulos/prompts.md`. Prancha para conferir antes de animar
   (`vsl.py prancha`). Pessoas fotográficas: bloco de pele realista do `03_personagens.md`.
2. **Vídeos**: Kling 3.0 std, 720p, 5 s, **sem som** (`kie.py kling3 --sem-som`). Com quadro: start frame = quadro; sem quadro: só texto.
   Prompt de movimento na **estrutura de 14 blocos** (`modulos/prompts.md`; sem som → sem bloco AUDIO), ex.:
   ```
   SCENE CONTEXT: a man in his 60s shows the supplement he takes every morning, home kitchen, early morning.
   ACTIVE REFERENCES: start frame = the approved kitchen shot with the {MARCA} bottle.
   LOCATION MAP: bottle on the counter in the foreground, his hand enters from the right, window at the back left.
   FIRST FRAME: exactly the start frame, close on the counter, his hand already entering the frame.
   FORMAT MODE: single continuous shot, no cuts.
   OPTICS: ~35° horizontal FOV, close.
   CAMERA: handheld phone held by him, slow push-in that leans toward the label.
   ACTION: 0–2 s his hand comes to rest beside the bottle; 2–5 s his index finger points at the label.
   PERFORMANCE: calm, matter-of-fact, a daily habit.
   PHYSICS: the bottle is heavy and planted on the counter, upright and closed; his fingertip touches the counter, not the bottle.
   LIGHTING: soft morning window light from the left, shadow falling to the right.
   STYLE: UGC smartphone footage, 9:16 vertical, natural grain, real-time speed.
   POSITIVE LOCKS: the bottle and label stay exactly as in the start frame, "{MARCA}" sharp and readable; the only text
   in the frame is the real printed label.
   ```
   Gere com folga de duração: o início parado é cortado na montagem (passo 6).
3. **Uma geração por vez** (regra do Fefo, 12/10/2026): o `kie.py` espera e baixa. Anote o taskId e os créditos de cada
   uma em `08_auto/broll_ids.tsv` na hora. Limites e queda de conexão: `modulos/kie.md`.
   Antes de cada envio, **confira que o quadro inicial e o prompt estão certos**.
4. Revisar (`vsl.py revisar`) e salvar via módulo coleta.
5. **Texto de anomalia = descartar e gerar de novo** (regra do Fefo, 13/10/2026): quadro ou vídeo com texto que a IA
   inventou (letreiro, legenda, palavras soltas, rótulo deformado, selo com texto torto) não entra na batch. Gere de novo
   (um pedido por vez) e reforce no prompt: "no text, no captions, no letters, no words, no signs, no watermarks
   anywhere in the frame" — no frasco, só o rótulo real legível. Confira de novo antes de aceitar.
   Não peça texto/selo no prompt; selo entra na edição. Selo errado já gerado = tirar (zoom leve), não substituir.
6. **Início parado** (regra do Fefo): Kling/Seedance começam "posando" no 1º quadro. Rode
   `python3 scripts/inicio_movimento.py <clipes.mp4>` em todo b-roll novo e grave `inicio` na cena do plano
   (≥ 0,5 s, ou o trecho parado detectado). Conferir no AD com `freezedetect`.

## O que funciona (e o que não)
- **Frasco**: fechado, em pé e parado — só a mão se mexe. Aberto/inclinado/girando deforma rótulo e gargalo.
  Rótulo legível em close: frasco a ~1/3 da altura, sempre em 720p (regra do Fefo, 02/11/2026: o Kling 3.0 pro, 1080x1912, saiu do fluxo). **Nunca Seedance 480p** com
  rótulo legível (o quadro estava perfeito, o vídeo deformou). O Kling às vezes traz o frasco para a câmera e o rótulo
  deforma: "the bottle keeps the same size and position as in the start frame for the whole clip".
  **Frasco que cresce no quadro** (push-in até o frasco, revelação): só no **pro** (7,5 por 5 s). No std as linhas
  pequenas do rótulo viram rabisco no fim ("Prenium Eye Sapdment", S36 da 3214); no pro, com "very slow, subtle… only a
  few centimeters" + "the bottle keeps almost the same size", saiu limpo até o último quadro. O "leve" não é garantido
  (a Neurobella aproximou bem mais que a VisioVance com o mesmo prompt): confira o último quadro.
- **Mãos**: uma pessoa por vez no quadro com mão em cena (marido no quadro + mão POV = "3 hands"); prefira POV com só
  a mão de quem está de frente. Confira as mãos já no quadro do Sunburst (o "3 arms" da 1977 nasceu no quadro) e trave
  a contagem no quadro e no vídeo: "exactly two arms and two hands: the hand nearest the monitor rests on a mouse, the
  other forearm along the desk edge with that hand flat; no hand near his face". Cena só de mão: "only one hand and no
  faces" (sem isso o Sunburst inventou uma pessoa). Mãos em concha + frasco despejando cápsulas pede 3 mãos: troque por
  frasco deitado na mesa (3214).
- **Toque entre duas pessoas** (1970, "anatomicamente incorreto"): cada antebraço entra por um lado do quadro (dele pela
  esquerda, dela pela direita), sem ombro, tronco ou rosto. Gere SEM o quadro antigo como referência: ele herda a
  composição em que os dois braços saem do mesmo tronco.
- **Pessoa no b-roll**: sem fala, boca fechada, olhar baixo, mãos paradas ("AI doesn't look good" quando gesticula/fala).
  O Kling faz a pessoa falar/gesticular depois de ~1,5–2 s mesmo com "mouth closed": use "her lips stay gently pressed
  together the whole time, she never speaks or opens her mouth; no hand gestures" e anote até onde o clipe é usável.
- **Figurante** (2+ pessoas além do avatar/casal): descreva-o bem diferente do avatar (idade, cabelo, barba, roupa);
  senão o Sunburst clona o avatar ("o mesmo homem 2x", farmacêutico da 2082).
- **Roupa**: com personagem de referência o Sunburst copia a roupa dela; para trocar, "wearing X instead of the outfit in
  her reference image".
- **Objetos contáveis** (cápsulas): o Kling pro duplicou cápsula. "Exactly two capsules exist; the saucer stays empty; no
  new capsules appear" resolveu.
- **Tela, monitor, papel, bolo com glacê → sempre pela rota do quadro.** O Kling só texto inventa interface, marca no
  monitor e "Happy Birthday" no bolo mesmo com "no text" reforçado. Quadro Sunburst conferido sem texto ("pure black
  screen, two fundus photos"; foto impressa na mesa; glacê liso) + Kling a partir dele saiu limpo. Celular na mão: tela
  "seen almost edge-on… thin blank glow"; tela de busca/app que precisa aparecer = desenhar localmente (sem crédito e sem
  texto da IA; exemplo `BATCH_1970/revisao_V3/scripts/hook_v3.py`). Cenas 3D (olho, mácula) e POV só texto saíram limpas.
- **3D da batch a partir de um quadro-base**: o 3D só com texto sai limpo, mas cada clipe com outra cara (olho de frente
  num, de lado no outro; S27 da 3215 com uma haste de metal que parecia agulha). Na 3215 os 2 quadros do S09 (escudo
  grosso/fino) viraram `start_image` de 13 clipes 3D coerentes e o S33 usou os mesmos 2 como início/fim, sem crédito a mais.
- **Consultório** (3214): "clinic"/"eye clinic" põe pôster de anatomia na parede com rótulos que imitam texto e livros
  com lombada rabiscada. Na cena escreva "plain bare wall with no posters, charts or framed pictures" e confira os
  cantos do quadro com zoom; quadro já gerado: edição do Sunburst "remove the poster… plain bare wall" manteve o resto igual.
- **Mesa com itens** (ranking da 3214): troque o item por edição do mesmo quadro-base ("remove the amber bottle… instead
  her hand is lowering X"): mão, mesa e luz saíram idênticas em 5 de 5. Fila de itens em 9:16: "three-quarter view…
  row running diagonally… filling the frame" (o "front view at desk height" deixa a fila minúscula no terço de cima).
  Close de item ("hand sets X down… slides out"): a mão "acena" aos ~2 s, o trecho útil é 0,5–2 s. Clipe que parte do
  mesmo quadro de outro repete a ação dele; ação em duas etapas pode vir na ordem trocada (S28) → cubra com 2 clipes.
- **Porta, gaveta ou tampa se mexendo** no Kling morfa: na S01 da 3214 a porta do armário fechou, a maçaneta pulou e
  abriu de novo ("o comportamento das portas tá estranho", Fefo). Peça o quadro já aberto e só a câmera se mexendo.
- **Ação clara** (arremessar, rasgar) e causa e efeito (antes/depois): Kling com `start_image` + `end_image`.
- **Seedance só em Drama ad** (ordem do cliente, 30/10/2026; regra em `04_falas.md`). Fora dele, Kling falhou, travou
  (429 o dia todo) ou não faz a ação: tente de novo mais tarde ou simplifique o plano, e avise o Fefo. Seedance sem o ok
  dele, nunca. Em Drama ad: **Seedance 2.5** (`seedance_2_5`, `omni_reference`, `start_image`, 720p,
  `generate_audio: false`, ~35 cr/5 s), com ou sem pessoas; ação clara com `start_image` + `end_image`.
  Frasco com rótulo legível fica no Kling pro.
- **Efeito sutil** (camada afinando, sintoma de visão): o modelo quase não mostra; faça na edição. Efeitos de sintoma em
  ffmpeg sem crédito (onda/bojo, metade cinza, cor sumindo, mancha central): `BATCH#1980/08_auto/efeitos_1980.py`.
- NSFW do Sunburst: cama + toque ou roupa íntima barra (ver `03_personagens.md`).

- **Frasco sempre inteiro** (Fefo, BATCH#3375, 29/10/2026): em cena/PiP com o frasco, o pote aparece todo (tampa e base), sem close cortando o rótulo; card do hook e legenda não passam por cima dele (conferir também no 4:5). Close de rótulo = packshot inteiro com margem e zoom bem leve.
- **Produto integrado à cena** (feedback do cliente, 31/10/2026): toda geração vai para o banco, e produto com luz diferente da do avatar e da cena parece falso e não será usado. No frasco, a luz vem da mesma fonte, direção, cor e contraste da cena, com o mesmo foco e grão, sem o brilho nítido de foto de estúdio. Editar a imagem aprovada do avatar ou da cena com o frasco como referência: "the bottle has the same light direction, color and contrast as the scene, and casts a natural contact shadow; keep the label readable". Rejeitar o quadro **antes de animar** se o frasco parecer colado na mão, mesmo com rótulo perfeito. Ao trocar o frasco para a outra marca por edição, conferir isto de novo nas duas versões.
