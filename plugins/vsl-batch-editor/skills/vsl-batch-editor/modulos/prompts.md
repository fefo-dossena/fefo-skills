# Estrutura de prompt (padrão do Fefo desde 13/10/2026)
Todo prompt de **vídeo** (fala do avatar no Kling/Seedance, movimento de b-roll, hook) é escrito nestes 14 blocos, nesta
ordem. Prompt de **imagem** (personagem, quadro inicial no Sunburst) usa só os blocos marcados com ●.

| # | Bloco | O que vai | Eixo | Imagem |
|---|---|---|---|---|
| 01 | **Scene Context** | O que acontece, onde, quando | contexto | ● |
| 02 | **Active References** | @tags de quem aparece no shot | identidade | ● |
| 03 | **Location Map** | Espaço em camadas, câmera no mapa | espaço | ● |
| 04 | **First Frame** | Frame zero: cheio, posicionado, certo | espaço | ● |
| 05 | **Format Mode** | Shot contínuo ou sequência de cortes | tempo | |
| 06 | **Optics** | FOV em graus — nunca em milímetros | câmera | ● |
| 07 | **Camera** | Operador físico com job dramático | câmera | |
| 08 | **Action** | O que acontece e quando, separado | tempo | |
| 09 | **Performance** | Sistema de atuação — não lista de tics | identidade | ● (expressão) |
| 10 | **Physics** | Peso, tecido, fluido, inércia, contato | espaço | |
| 11 | **Lighting** | Fonte real, catchlight, sombra motivada | câmera | ● |
| 12 | **Audio** | Diálogo exato ou ambiente necessário | tempo | |
| 13 | **Style** | Look técnico, grão, formato, velocidade | técnico | ● |
| 14 | **Positive Locks** | Travamentos críticos em forma positiva | travamento | ● |

## Como preencher nos nossos ads
- **01 Scene Context** — uma frase: quem, fazendo o quê, onde, que hora do dia. Vem do ref (`01_refs/`) e da `copy` da cena.
- **02 Active References** — nomeie cada referência do pedido e quem/o que ela é: start frame, `Image 1`/`Image 2`
  (personagem aprovado, packshot do frasco da marca), `audio_references` (voz). Só quem está **neste** shot.
- **03 Location Map** — o espaço em camadas (primeiro plano / meio / fundo) e onde a câmera está nele
  ("camera at the kitchen island, he stands behind it, window at back left").
- **04 First Frame** — como o quadro 0 já começa: enquadramento cheio, sujeito posicionado, ação já em curso. Com
  `start_image`, descreva o que está nele ("as in the start frame"); o vídeo não deve "montar" a cena nem começar posando.
- **05 Format Mode** — nossos clipes são **um shot contínuo** ("single continuous shot, no cuts"); os cortes são feitos
  na edição. Sequência de cortes só se o ref pedir um clipe multi-shot.
- **06 Optics** — campo de visão em graus ("~70° horizontal FOV, selfie distance"; close "~30° FOV"), nunca "35mm".
- **07 Camera** — a câmera como um operador com intenção: "handheld selfie held at arm's length by him, small natural
  sway", "slow push-in that leans toward the label". Nada de movimento sem motivo.
- **08 Action** — beats separados e na ordem, com tempo: "0–1 s he lifts the bottle; 1–3 s turns the label to camera;
  3–5 s holds still". Uma ação principal por clipe.
- **09 Performance** — o estado interno que gera a atuação (objetivo, emoção, para quem fala), não uma lista de gestos:
  "talking to a friend he trusts, relieved, a little embarrassed". Expressão contida; mãos longe da câmera.
- **10 Physics** — peso e contato reais: frasco com peso na mão, dedos apertando, tecido que dobra, líquido que escorre,
  inércia ao parar. Frasco fechado, em pé, parado (só a mão se mexe — ver `05_broll.md`).
- **11 Lighting** — fonte real da cena (janela, luminária, tela do celular), catchlight nos olhos, sombra coerente com
  a fonte. Igual ao start frame.
- **12 Audio** — fala: o texto **exato** entre aspas, "word for word, in English", voz (timbre, sotaque, ritmo) e
  "only his voice and room tone, no music". B-roll sem som (Sound Off): bloco omitido.
  Só a fala vai entre aspas — nota de pronúncia fora das aspas pode ser falada pelo Seedance (ver `04_falas.md`).
- **13 Style** — look técnico do ref: "UGC smartphone footage, 9:16 vertical, natural grain, real-time speed, no slow
  motion". Pessoa fotográfica: bloco de pele realista do `03_personagens.md`.
- **14 Positive Locks** — o que não pode mudar, dito em forma **positiva**: "his face, hair and outfit stay exactly as in
  the start frame", "the bottle stays upright and closed, label sharp and readable", "the only text in the frame is the
  real printed label", "mouth stays fully visible". Se uma geração vier com texto inventado, ao refazer acrescente
  também o reforço negativo de `05_broll.md` (passo 5).

## Forma do prompt
Rótulo curto + 1–2 frases por bloco, na ordem acima (ex.: `SCENE CONTEXT: ... ACTIVE REFERENCES: ...`). Bloco que não se
aplica é omitido, não preenchido com "none". Mantenha o prompt enxuto e confira se o pedido aceitou o texto inteiro.
Exemplos preenchidos: fala em `04_falas.md`, b-roll em `05_broll.md`.

## Reforços para UGC realista (curso Ad Creators Lab, 29/10/2026)
Somam-se aos 14 blocos; não trocam nada acima. Resumo do curso em `@cursos/trendscale/Ad Creators Lab - síntese completa.md`.
- **13 Style** em UGC: "shot on iPhone, handheld, window light, slight natural shake, 9:16". **Nunca** "cinematic", marca de
  câmera (ARRI, RED), "film grain", lens flare, bokeh, color grade/LUT, "epic", "stunning", slow motion (só "iPhone
  slow-mo"). Grão e grade, se precisar, entram na edição.
- **03 Location Map / 10 Physics**: diga também **o que NÃO está** na cena e o que cada mão faz ("left hand holds the
  bottle, right hand rests on the counter; nothing else on the counter"). O que não é descrito o modelo inventa.
- **12 Audio**: além da voz, o **room tone** do lugar (banheiro = reverb de azulejo; quarto = abafado; cozinha = espaço
  aberto, zumbido leve). A entrega segue `04_falas.md` (rápida, fluente); não meter muletas na copy, que é do time de copy.
- **Seedance 2.0**: até 15 s por geração e **uma ação por prompt**; para continuidade entre clipes, o último quadro de um
  vira o start frame do seguinte.
- **Referências**: foto de personagem **limpa** (sticker, texto ou interface viram objeto na cena); start frame do avatar
  **olhando reto para a câmera e de boca fechada** (de ângulo a testa deforma; boca fechada articula melhor P/B).
- **Teste barato antes do caro**: 5 s em 720p no modelo barato para checar timing e movimento; modelo caro só no final.

## Reforços para Drama ad e peça cinematográfica (kaye.creatives, 30/10/2026) — a testar
Somam-se aos 14 blocos e **não valem para UGC**. Ainda sem teste nosso: confirmar com o Fefo antes de gastar crédito. Fonte
e o que ficou de fora: `Pesquisas/Realismo em filme de IA.md` no segundo cérebro.
- **Folha de personagem**: tríptico em fundo branco liso (close de frente, corpo inteiro, perfil a 90°), mesma luz e roupa
  nos 3 painéis. Personagem que muda de idade ou de roupa ganha uma folha por fase, com a mesma referência de rosto.
- **Folha de cenário**: uma imagem por local antes das cenas (camadas, materiais, fonte de luz, paleta em %), usada como
  referência em todo shot daquele local. Sem ela o lugar muda a cada plano.
- **02 Active References**: além da referência, copie um **bloco de identidade** igual em todo prompt (rosto, cabelo, marcas,
  roupa). Só o estado muda de uma fase para outra (nova → riscada → gasta).
- **Lapso de tempo em match cut**: um prompt-base com "same composition and camera position as the final frame of the
  previous scene", câmera quase parada e uma variável só (janela/estação/estado). Gere o último quadro como referência.
- **07 Camera**: POV de dentro de objeto fechado sai como câmera flutuando; diga de onde olha e "static extreme low angle
  looking straight up from inside". Em diálogo, preserve o eixo: diga em qual borda do quadro cada silhueta fica.
- **10 Physics**: externa com tudo parado parece falsa; acrescente vento leve em roupa e cabelo.
- **11 Lighting**: a luz vem do lugar (mesma fonte, direção e cor da folha de cenário), para o personagem pertencer à cena.
- **Rascunho**: `seedance_2_5` em 480p (3/s) para testar movimento; só o plano certo sobe de resolução. Não serve para
  testar fala: no site o Draft sai mudo.
- **Roteiro**: uma virada emocional clara, tons alternados (choro, alegria, rotina) e final contido em vez de melodrama.
