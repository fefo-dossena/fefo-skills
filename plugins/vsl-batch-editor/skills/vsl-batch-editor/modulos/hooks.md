# Guia de hooks (estudo do board "Great hooks" do Hookd, 16/10/2026)
Fonte: os 10 ads públicos do board (o board tem 26; os outros 16 só abrem com conta no Hookd). Todos vídeo 9:16, UGC
de celular, no ar de 89 a 301 dias (quanto mais dias, mais o ad se pagou). Tabela no fim.

## Quando usar
- O estilo continua vindo do ref em `01_refs/` (SKILL.md). Este guia vale onde o ref deixa espaço: 1º quadro e b-roll
  dos hooks (`05_broll_hooks/`), header do hook (`estilo.hook_header`), ponte hook → hold e a conferência dos hooks.
- A copy do hook vem do canvas: não reescreva. No `roteiro`, classifique cada HOOK 1/2/3 em um dos tipos abaixo e
  planeje a cena do hook com a execução daquele tipo. Mostre ao Fefo o tipo de cada hook junto com o `estilo`.
- Hooks novos só se o Fefo pedir (modelos no fim), marcados como sugestão.

## O que os 10 fazem igual
1. **Ação já acontecendo no quadro 0.** Nada de pose, "oi", logo ou cartela: balde de água suja já caindo, escova de
   rímel no olho, luz vermelha no nariz, mão abrindo o pote, homem puxando a camiseta, linha desenhada no rosto,
   artéria com placa em 3D. No hook o corte entra no 1º movimento forte do clipe, não só depois da pose (≥ 0,5 s).
2. **Fala no 0 s** em 7 de 10. As duas exceções são as duas que mais rodaram (Pureskin, 301 e 191 dias): abrem com
   1,9–2,4 s de cena "nativa" sem fala (tipo F).
3. **Frase curta:** 2–4,2 s, 8 a 15 palavras, 3,0–3,4 palavras/s (o nosso 3,3). O INIA ainda corta o começo e entra
   no meio da frase ("get accused of…", sem o "I").
4. **Header no topo durante o hook** (8 de 10): a frase do hook, ou a promessa, em 1–2 linhas de caixa branca, com o
   trecho-chave em outra cor (verde, verde-água, azul, amarelo): "Here's what happened after / **4 weeks with the NoMore
   Device**", "2 daily spoonfuls / **of Sea Moss**", "…slept for 10 hours / **after using this**". Sai quando o hook
   acaba. É o nosso `estilo.hook_header` {"1": [branco, destaque]}.
5. **Produto na tela até ~2 s** em 8 de 10 (na mão, no rosto, no balcão). Exceção: hook de alerta (tipo C), em que o
   problema vem primeiro (na Pureskin de 301 dias o produto só entra aos ~14 s).
6. **1º corte entre 1,5 e 4,5 s**, depois corte a cada 1–2 s.
7. **Ponte falada do hook para o corpo:** "and here's why", "Here's what happens to…", "Seriously. Pause. Because…",
   "It's called PrimeLash". Ela promete o próximo trecho e segura quem já ia passar.
8. **Funciona mudo:** header e legenda contam o hook sozinhos. A True Classic de 91 dias nem tem voz, só texto e música.

## Tipos de hook e como executar
### A. Linha do tempo: "o que acontece se…" (3 de 10: NoMore 205 d, Resilia 90 d, Sea Moss 89 d)
- Fala: "Here's what happens to your arteries if you take two softgels of aged odorless garlic every day for four
  weeks." / "A woman uses the NoMore device for four weeks. Here's what happens to her facial pressure." /
  "What happens to you if you take two daily spoonfuls of sea moss for two weeks?"
- Corpo em marcos: "Minutes after… / After one day… / Week two… / After four weeks…".
- 1º quadro: o problema dentro do corpo (Resilia: corte da artéria com a placa amarela, 1,4 s) ou o produto em uso
  no corpo com setas apontando (NoMore: 2 setas vermelhas e olhinhos de sticker).
- Barra de progresso no topo (NoMore): pílula "1 min · Day 1 · Week 1 · Week 3 · Week 4"; o marco atual fica verde e
  avança a cada marco, e a pessoa ganha contorno verde brilhante na troca. No `montar`: `estilo.barra_tempo`
  {"marcos": [...], "gatilhos": [texto da legenda em que cada marco acende], "de", "ate", "y"} (detalhes em
  `02_referencia.md`). O contorno verde na pessoa não está no script: módulo `motions` ou `.mov` com alfa em
  `estilo.overlays`.
- 3D médico em cada mecanismo (mitocôndria, seio nasal, placa saindo da artéria) e mashup de pessoas diferentes
  repetindo o mesmo gesto (tomar a cápsula), com whip-pan borrado entre elas. O Resilia parece todo feito com IA: o
  formato inteiro cabe no nosso Kling + 3D.
- Para nós: Neurobella → vasos/fluxo de sangue em 3D; VisioVance → olho, retina e mácula em 3D.

### B. Resultado emocional + "this" (3 de 10: 8 Sheep 152 d, True Classic 138 d e 91 d)
- "I almost cried when my baby finally slept for 10 hours after using this." / "If a man wears THIS he's definitely
  getting lucky tonight." / "My wife threw out all of my shirts when she found this."
- Fórmula: emoção, ou reação de outra pessoa (esposa, namorada), + resultado concreto com número + "this" apontando o
  produto. "THIS" em caixa alta no texto.
- Visual: tela dividida (8 Sheep: à esquerda o resultado, mãe e bebê dormindo; à direita a mão abrindo o pote) ou a
  pessoa que fala recortada no canto, sorrindo e apontando para o homem (True Classic: mulher falando do homem, como a
  esposa da 2820).
- Tela dividida no `montar`: cena do hook com `"formato": "split"` (o clipe da cena fica à esquerda, o resultado) e
  `"clipe_direita"` (o produto, ex.: `"05_broll_hooks/hook1/H1-01d_pote_{p}.mp4"`); `inicio_direita`, `divisoria`
  opcionais (`02_referencia.md`). Gere os dois clipes já pensando em meia largura: assunto no centro do quadro.
- Para nós: Neurobella na voz da esposa.

### C. Alerta sobre algo comum (2 de 10, os 2 que mais rodaram: Pureskin 301 d e 191 d)
- "A towel like this might ruin your life, and here's why." / "Don't touch your face for 5 seconds. Seriously. Pause.
  Because if you dried it with a towel this morning, you're basically putting as much bacteria on your skin as if
  someone sneezed directly on your face."
- Objeto banal na mão em plano médio; a consequência aparece literal na palavra forte (o balde de água suja cai na
  cabeça dele em "ruin your life"); comparação nojenta; ordem direta para quem assiste com o número gigante em vermelho
  ("FOR 5 SECONDS"); palavras-chave grandes e animadas uma a uma, seta desenhada à mão.
- Corpo: metáfora visual para cada número (50 milhões = confeitos espalhados na mesa, post-it escrito à mão), 3D,
  quadro branco, tela preta, mudança de estilo a cada frase.

### D. Objeção virada ou prova social ousada (Prime Prometics 211 d, INIA 128 d)
- "This mascara is not cheap, but it actually works." / "[I] get accused of getting work done on my face on the daily,
  and it's because I swear by frequency technology."
- Demonstração já armada no quadro 0: rosto dividido por uma linha desenhada, um lado tratado e o outro não (INIA,
  selfie em take único). Citação entre aspas no texto, com a palavra-chave colorida entrando animada ("ACTUALLY WORKS").

### E. Assunto do momento (Prime Prometics 211 d)
- "Mulberry is the color of the season." Entra pela tendência, depois revela o público ("made especially for women over
  50") e mostra várias mulheres de 50+ usando. Inset redondo com a cor/textura no canto do close.
- Para nós: Halloween, Black Friday, data da oferta (como na 2827).

### F. Abertura "nativa" de isca (Pureskin 301 d e 191 d)
- 1,9–2,4 s antes da fala: plano aberto de algo estranho acontecendo, com legenda no estilo Snapchat (faixa preta
  translúcida de ponta a ponta, texto branco pequeno e 2 emojis): "what are these dudes doing 🤯🤯", "no way this just
  happened 🤢🤢". Parece vídeo orgânico, não anúncio. Depois corte ou whip para quem fala.
- Para nós: b-roll de ~2 s (Kling) de uma cena curiosa ligada ao hook + texto nativo, depois o avatar. Muda a duração
  do hook: só com OK do Fefo e se o ref permitir.
- Texto nativo no `montar`: `estilo.tag_nativa` {"texto": "no way this just happened 🤢🤢", "y": 0.42, "ate": 2.2,
  "hooks": [1]} (faixa preta translúcida de ponta a ponta, Helvetica fina branca, emoji colorido). Ele não esconde a
  legenda nem o `hook_header`: nesses ~2 s, hook sem header fica mais "orgânico".

## Conferência dos hooks (antes de mandar os ADs ao Fefo)
- Quadro 0 com ação acontecendo, sem pose.
- Produto visível até ~2 s (salvo o tipo C).
- Header em 1–2 linhas, trecho-chave em outra cor; entende-se o hook sem som.
- 1º corte até ~4,5 s.
- Ponte para a hold clara.
- Os 3 hooks com 1º quadro diferente entre si (regra do `10_revisao`).
- Abre no ato, nunca no setup ("hey guys", pegar o frasco); se a fala tem virada ("…but"), punch-in no rosto ali.
- O texto do header fica na tela o hook inteiro (80–90% assiste sem som, segundo o curso Ad Creators Lab).

## Hook novo sobre um corpo que já funciona (curso Ad Creators Lab, 29/10/2026)
Quando o pedido é "mais hooks" para uma hold aprovada: hook com **música própria** (contrasta com a da hold), **riser**
terminando no fim do hook, **hit** no corte para a hold e whip/slide curto. Conferir a mixagem de música, riser, hit e voz
com scrub (Shift+S). Cada hook muda **um eixo** (dor, emoção, visual de abertura), não só a frase.

## Modelos para sugerir (só se o Fefo pedir hooks novos)
Promessa de saúde só a que o canvas/lander já usa; a copy final é do time de copy.
- Neurobella, A: "Here's what happens to your blood flow if you take two cocoa capsules every day for 30 days."
- Neurobella, B (esposa): "If my husband takes THIS before dinner, I know exactly how the night ends."
- Neurobella, D: "These cocoa capsules aren't cheap, but they actually work."
- VisioVance, A: "Here's what happens to your eyes if you take the 15-in-1 Eye Formula every day for four weeks."
- VisioVance, B: "My husband almost cried when he could read the menu without his glasses again."
- VisioVance, E: "Halloween is the one sale I wait for all year, and this is what I'm stocking up on."

## Os 10 ads (ordem de dias no ar)
| # | Marca | Dias | Dur. | Hook falado | Quadro 0 | Texto do hook | 1º corte |
|---|---|---|---|---|---|---|---|
| 1 | Pureskin (toalha facial) | 301 (encerrado) | 1:51 | 2,4 s mudo; "A towel like this might ruin your life, and here's why." | aberto no terraço: um despeja balde de água suja no outro | Snapchat "what are these dudes doing" → palavras animadas "a towel / LIKE THIS / LIFE / AND HERE'S WHY:" + seta | 2,9 s |
| 2 | Prime Prometics (rímel) | 211 (no ar) | 0:38 | "Mulberry is the color of the season. This mascara is not cheap, but it actually works." | close do olho com a escova + inset redondo da cor | caixa escura no topo → citação em caixa branca, "ACTUALLY WORKS" em azul | 3,0 s |
| 3 | NoMore (luz vermelha nasal) | 205 (no ar) | 0:59 | "A woman uses the NoMore device for four weeks. Here's what happens to her facial pressure." | perfil na cama com o aparelho aceso no nariz, 2 setas e olhinhos | header amarelo + verde; legenda cinza translúcida; barra de progresso | 2,3 s |
| 4 | Pureskin | 191 (encerrado) | 2:03 | 1,9 s mudo; "Don't touch your face for 5 seconds. Seriously. Pause." | estação de metrô, plano aberto, o homem ao lado se vira | Snapchat "no way this just happened" → "FOR 5 SECONDS" vermelho gigante | 1,9 s |
| 5 | 8 Sheep (loção de bebê) | 152 (no ar) | 0:36 | "I almost cried when my baby finally slept for 10 hours after using this." | tela dividida: mãe e bebê dormindo / mão abrindo o pote | 2 linhas em caixa branca + tag verde-água inclinada "after using this" | 4,5 s |
| 6 | True Classic (camiseta) | 138 (encerrado) | 0:39 | voz de mulher: "If a man wears THIS he's definitely getting lucky tonight." | homem ajeitando a camiseta + mulher recortada no canto apontando | 2 linhas em caixa branca, "THIS" em caixa alta | 3,9 s |
| 7 | INIA (aparelho facial) | 128 (no ar) | 2:09 | "[I] get accused of getting work done on my face on the daily…" | selfie, rosto dividido por linha desenhada, aparelho na mão em 1 s | header fixo com a promessa: "Frequency technology for a lifted appearance in real time" | 4,5 s |
| 8 | True Classic | 91 (encerrado) | 0:21 | sem voz, só música | homem puxando a camiseta para baixo | "My wife threw out all of my shirts when she found this" | 3,3 s |
| 9 | Resilia (alho envelhecido) | 90 (encerrado) | 1:55 | "Here's what happens to your arteries if you take two softgels of aged odorless garlic every day for four weeks." | 3D: corte da artéria com placa | legenda pequena de 1 linha | ~1,5 s |
| 10 | Fitness Addiction (Sea Moss) | 89 (encerrado) | 0:44 | "What happens to you if you take two daily spoonfuls of sea moss for two weeks?" | mulher atrás de 3 potes no balcão, mãos nas tampas | 2 linhas: branca + verde | 2,0 s |
