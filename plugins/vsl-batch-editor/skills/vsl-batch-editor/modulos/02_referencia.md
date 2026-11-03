# Módulo: referência → estilo do ad
O estilo de cada batch vem do(s) ad(s) em `01_refs/` **desta** batch (e do canvas/brief), nunca da batch anterior.
Se `01_refs/` estiver vazio, pergunte ao Fefo qual ad seguir antes de seguir. Card sem ad de referência (Milanote sem
ref, BATCH#3214 e #3215): proponha um estilo UGC (personagem, cenário, enquadramento de cada setup, legenda) e espere o
OK; nas duas, médico(a) falando para a câmera fixa na mesa do consultório + selfie andando nos hooks foi aprovado.

## Régua de qualidade: BATCH#3217
Elogiada pelo Daniel (31/10/2026: "this one bro, really good"; ele não disse o motivo). Serve para comparar o nível antes de ir ao Fefo, em especial em build de médico em PIP, **nunca como fonte de estilo**: o estilo continua vindo de `01_refs/` e do card. O que olhar em `BATCH#3217/09_export/`:
- Voz e rosto iguais do início ao fim (Kling 4.0 com a 1ª fala aprovada como referência), fala sem palavra cortada.
- B-roll trocando a cada 1 a 3 s, sempre casado com a fala: gente da idade do público, closes e 3D da mesma anatomia ao longo do ad; 3D nunca dois seguidos.
- Legenda em expressões inteiras, faixa só no dado que vende (dose, garantia), frasco inteiro e rótulo nítido.
- Os exports são de 27/10, em 1080p: a saída agora é 720p.

## Como analisar
- Com ffmpeg: `ffmpeg -i ref.mp4 -vf "fps=1/2,scale=150:-1,tile=8x6" sheet.jpg` (prancha a cada 2 s) e, se precisar,
  `-ss <t> -frames:v 1` para ver um momento. Transcreva o áudio do ref (`vsl.py transcrever`) para casar copy × cena.
- Sem ffmpeg: copie para o scratchpad, sirva com `python3 -m http.server`, abra no navegador interno (127.0.0.1) e capture
  quadros tocando o vídeo em 4× com `requestVideoFrameCallback` (o http.server não aceita seek).

## Regras do ad, antes das cenas (desde 02/11/2026)
Antes de pensar em imagem, escreva 5 a 10 linhas do que o ref faz, no topo de `cenas.md` e em `estilo.observacoes`, e siga
até o fim: ritmo, tom da fala, tempo de corte no hook e na hold, quanto o avatar aparece, quem apresenta o produto, tipo de
b-roll (real, sem meme nem estúdio) e arte do 3D (uma só no ad). Iteração de ganhador: assista ao ganhador e anote o que se
repete e o que dá sensação. Sem ref: procure ads e conteúdo orgânico do que o público já consome.
- **Ritmo vem do público:** técnica de retenção de TikTok afasta quem tem 60+. Dentro de "algo muda a cada 1 a 3 s"
  (`07_montagem`), prefira a ponta calma, sem efeito de rehook, salvo se o ref fizer diferente.

## O que registrar em `plano.json` → `estilo` (o `montar` lê daqui)
```json
"estilo": {
  "fonte": "01_refs/<arquivo>",
  "avatar": {"pb": false, "enquadramento": "tela_cheia"},
  "broll": {"layout": "tela_cheia"},
  "legenda": {"estilo": "caixa_branca", "posicao": "centro_baixo", "max_caracteres": 22},
  "ritmo": "corte a cada ~2-3 s",
  "elementos": ["seta no CTA", "banner no topo"],
  "observacoes": "texto livre: cenário do avatar, tipo de b-roll (live-action, 3D, stickers), CTA, música"
}
```
- `avatar.pb`: avatar em preto e branco (true/false).
- `broll.layout`: `tela_cheia` (b-roll cobre o avatar) ou `metade_baixo` (avatar em cima, b-roll embaixo), ou `cartao`
  (avatar colorido em tela cheia; b-roll em cartão quadrado centralizado ou inset quadrado com borda; ver `scripts/cartao.py`).
  No `cartao`, cada cena tem `formato`: `tela_cheia` (cartão) · `inset` · `avatar` (variação do avatar, ocupa o quadro) ·
  `cta_final` (tela final: vídeo do frasco no topo branco + faixa escura com seta). Parâmetros opcionais em `estilo`:
  `avatar.quadro` [x,y,w,h] (ex.: [0,285,1080,1350] = 4:5 com tarjas; [0,0,1080,1920] = 9:16 cheio), `avatar.punch_in`
  (zoom alternado por clipe), `broll.cartao`/`broll.inset` [x,y,w,h], `legenda.tamanho`/`y`,
  `hook_banner.texto` (`**negrito**`, `|` quebra linha), `cta.titulo`/`rodape`. Exemplo completo: BATCH#2078.
- `legenda.estilo`: `amarelo_contorno`, `branca_contorno` (sem caixa), `caixa_branca` / `caixa_branca_compacta` /
  `caixa_branca_justa` (caixa colada no texto — a preferida do Fefo quando o ref tem caixa reta), `pilula` (caixa de
  cantos arredondados por linha, 1–2 linhas, estilo texto do Instagram; header do hook no mesmo desenho via
  `estilo.header_pilula`; `y`, `tamanho`, `quebra`; o texto do header é `plano.header`, um só para os 3 hooks, não o
  `hook_header`, e aceita emoji colorido como o 😩 do Milanote, BATCH#3215), `palavra_brilho` (uma palavra por vez, só no layout `cartao`),
  `branca_fina_caps` (branca sem caixa, Avenir Next Demi Bold, contorno fino; com `legenda.caixa_alta: true` e posição
  `peito_alto` = ~64% da altura; ref mini-filme da 2480), `branca_fina` (Helvetica Neue 10, contorno fino; ref cartoon
  da 2481) e `branca_legivel` (a mesma em Bold 13, contorno 1,8, sombra 0,9: a `branca_fina` sumia no fundo cartoon
  colorido, "hard to read" na 2481 V2 — prefira esta). `legenda.caixa_alta: true` vale para qualquer estilo de SRT.
  Se o ref usar outro, descreva em `observacoes` e implemente no `fluxo.py` → `ESTILOS`. `posicao`: `divisao` (linha
  entre avatar e b-roll), `centro_baixo`, `centro`, `meio_alto`, `peito_alto` (~64%) ou `peito` (y≈1550, cabe no 4:5).
- **Copie o desenho do texto do ref**, não só a cor: forma da caixa, nº de linhas, posição/altura e o header do hook. O time
  compara lado a lado ("text box looks horrible", "hook doesn't look the same text wise" na 2824).
- Outros campos que o `montar` lê: `avatar.enquadramento = "nenhum"` (só VO, b-roll cobre 100%), `hook_header`
  {"1": [branco, destaque]} + `hook_header_y` + `hook_header_quebra` (caracteres por linha, padrão 24), `titulo_hook`
  {"1": "Eye doctor", …} (um título por hook, caixa azul no peito, `estilo.titulo_hook_y` = 1240; BATCH#3214),
  `tag_hook` {"texto","y","so_broll"}, `trilha_final_db`, `one_take: true`
  (ad em um take contínuo, `umtake.py`; ali `falas[].texto_por_marca` dá texto diferente por marca na legenda).
- **Elementos de hook** (`modulos/hooks.md`, desenhados por `scripts/elementos_hook.py`; só entram se o ref pedir; valem
  nos layouts `tela_cheia` e `metade_baixo`, não no `cartao` nem no `one_take`):
  - `estilo.barra_tempo` (tipo A, ref NoMore): pílula no topo com os marcos; o atual fica verde (com "pop" na troca) e os
    já passados ficam com texto verde. `{"marcos": ["1 min", "Day 1", "Week 1", "Week 3", "Week 4"], "gatilhos": [um
    texto da legenda por marco], "de": "<texto>" (opcional: aparece antes, sem marco aceso), "ate": "fim" ou "<texto>",
    "y": 110, "tamanho": 38, "hooks": [1, 2]}`. Gatilho = trecho da legenda do AD (a da hold; a do hook só se ele não tem
    `hook_header`), procurado em ordem. Cores opcionais: `cor_fundo`, `opacidade`, `cor_texto`, `cor_ativo`,
    `cor_texto_ativo`, `cor_passado`; `"pop": false` desliga o pulo.
  - `estilo.tag_nativa` (tipo F, ref Pureskin): faixa preta translúcida de ponta a ponta com texto branco pequeno e emoji,
    nos primeiros segundos do hook. `{"texto": "what are these dudes doing 🤯🤯", "y": 0.42, "ate": 2.2, "hooks": [1]}`
    (`y` = centro da faixa, fração da altura ou px; `ate` em s ou `"hook"`; opcionais `de`, `tamanho` 40, `opacidade`
    0.6). Emoji simples (sem tom de pele nem emoji composto). Não esconde legenda nem `hook_header`: para o visual
    "orgânico", deixe o hook sem header nesses segundos.
  - Cena com `"formato": "split"` (tipo B, ref 8 Sheep): tela dividida, esquerda = clipe da cena (resultado), direita =
    `"clipe_direita"` (produto), caminho relativo à batch com `{p}` = marca (ex.: `"04_broll_hold/{p}/S14_frasco.mp4"`).
    Opcionais `inicio_direita` (pular o começo parado, ≥ 0,5 s) e `divisoria` (px de linha branca no meio). A cena dura
    no máximo o clipe mais curto (nenhum lado congela). Cena com `usa` não herda: repita `formato`/`clipe_direita`. O `status` lista
    o clipe da direita no b-roll; no XML ele vai para V3 (cada metade com escala, centro e crop).
- Cena com `"formato": "inset"` (antes/depois sobre a selfie, BATCH#3223): o clipe entra num cartão quadrado de cantos
  arredondados, com borda branca e sombra, por cima do avatar, que continua falando; `"rotulo"` (ex. "2 MONTHS AGO" /
  "NOW") vira uma pílula branca no canto do cartão; `"inset_cy"` escolhe a faixa vertical do 9:16 que vira o quadrado e
  `"inset_filtro"` aplica um filtro no clipe ("hue=s=0.35" no "antes"). Geometria em `estilo.inset` {x, y, lado, raio,
  borda, tamanho} (padrão 150, 870, 780: rosto livre em cima, legenda pílula em 0,66 dentro do cartão). Só no
  `tela_cheia` (`elementos_hook.inset_*`); o XML ainda põe o clipe em tela cheia.
- **Médico em picture-in-picture** (`estilo.avatar.enquadramento: "pip"`, BATCH#3217, build "doctor PIP over b-roll" da
  3213): o b-roll cobre a tela o AD inteiro (cenas emendadas, a 1ª no quadro 0, a última até o fim da fala) e o avatar
  fala numa janela de cantos arredondados com borda branca e sombra. `estilo.avatar.pip` = {x, y, w, h, raio, borda,
  recorte: [x, y, w, h] no quadro 720x1280 do avatar}; na 3217: x 40, y 1150, 330x440, recorte [60, 60, 600, 800],
  legenda pílula em y 0,555 (logo acima da janela) e `estilo.destaque_y` 760 (o destaque no meio batia na legenda).
  Corte de b-roll a < 0,4 s de uma emenda do avatar vai para a emenda (meio quadro antes) e cena < 0,45 s pega tempo das
  vizinhas. Cena com `"pip": false` esconde a janela (frasco em close que ela cobria; 3217: S53, S54, S62, S64), com
  `legenda_y` acima do rótulo. Freezedetect do AD só na faixa de cima (`crop=720:660:0:0`): a janela falando esconde b-roll
  parado; os reaproveitados que eram cortados pelo médico em tela cheia pediram push 8–25% (`efeitos_3217.py`). O XML
  ainda não monta a janela (falas em V1 em tela cheia).
- O que o script ainda não faz (outros elementos, motions, música do ref) vai em `elementos`/`observacoes` e entra pelo
  módulo `motions` ou pela trilha em `02_audio/trilha/`.

## Use também para
Personagem e cenário do avatar, tipo de b-roll e ritmo de cortes do plano de cenas. A copy costuma seguir o ref frase a
frase — case o ritmo das cenas com ele. Mostre ao Fefo o `estilo` em uma frase antes de gerar qualquer coisa.
