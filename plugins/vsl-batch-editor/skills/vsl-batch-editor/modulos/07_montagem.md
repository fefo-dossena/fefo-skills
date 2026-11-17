# Módulo: montagem (local, sem crédito)

> **Antes do render e na edição (PDF do Lucas, 16/11/2026; `@CLIENTES/_FLUXO/QUALIDADE_DO_BATCH.md`, seções 3 e 4):** conferir a timeline (prévia) e a folha dos clipes antes do render; nenhum quadro de fonte usado duas vezes (esticar = desacelerar até ~0,6x ou outro clipe); nenhum trecho em faixa ruim do veredito nem clipe com reroll pendente; ponto de entrada tirado do clipe real. A cena flui: clipe inteiro, corte só na troca de cena ou na reação, nunca picado por linha de roteiro. Ouvir cada emenda de fala. Pausa dramática de diálogo de drama fica (só ar morto > ~4 s sai); **VO narrada de anúncio segue o item 3 da Louise** (pausa > 0,45 s é falha). **Legenda continua a nossa** (pílula TikTok Sans Medium, `pilula.py`, dentro do 4:5 na EV e do 1:1 na TS).

`python3 fluxo.py fazer "<batch>"` roda, só onde precisa e nesta ordem:
1. **cortes** — silêncio de cada clipe (`batch.json` → corte_silencio). Se existir `<clipe>.manual.json`, ele vence.
   Toda borda de corte (automático e manual) é levada ao silêncio de verdade (`bordas_no_silencio`: janela de 20 ms
   < −52 dB, busca ≤ 0,25 s) e cada trecho ganha fade de 8 ms — corte com a voz soando = "cortes na voz".
   1ª fala da hold começa 0,1 s antes da 1ª palavra e o hook mantém +0,2 s de cauda (`respiro_hook_s`).
   **Clipe com ruído de fundo alto** (Kling no carro, −39 a −45 dB; Kling em geral ~−38): o −52 fixo nunca é atingido e
   toda borda anda os 0,25 s inteiros = pausas de ~0,65 s ("deadspace", 1977). No `batch.json` → `corte_silencio`:
   `"borda_relativa_db": 3, "silencio_min_s": 0.30, "folga_depois_s": 0.10, "respiro_hook_s": 0.05` (silêncio = piso do
   clipe + 3 dB). Meça o piso antes (envelope dos clipes); na 1977 os ADs foram de ~1:27 para ~1:14, pausas ≤ 0,37 s.
   **Clipes do Seedance**: estalo ~50 ms antes do fim do arquivo (`04_falas.md`). Nenhum trecho pode ir até o fim do
   clipe. Desde a 2480 o `fluxo.py` corta sozinho em `duração − 0,08 s` quando `plano.modelo_falas` começa com
   "seedance" (vale também para o `.manual.json`). Batch que mistura modelos (Kling 4.0 + Seedance, 3219): o teste é por fala,
   pelo `falas[i].modelo_clip` (texto ou {marca: texto}) — `fluxo.eh_seedance()`, desde 27/10/2026. Fala curta do Seedance costuma ter respiração/ruído depois da última
   palavra (trecho de 0,1–0,4 s no fim): limpe com `.manual.json` até ~0,25 s depois da última palavra do Whisper.
   Só encurte pausa que seja silêncio real; "pausa" a −30/−45 dB é respiração/fim de palavra — cortar ali soa picotado.
   Meça pausa na voz dos cortes (envelope dos clipes na linha do tempo), não no AD exportado: a trilha enche os silêncios.
   Fala com `velocidade` no plano usa a cópia acelerada de `08_auto/rapido/`.
   **Fala sem voz para a montagem** (3378 V1, regra de 30/10/2026): guia a −30 dB, clipe do Seedance com pico de −28 dB,
   corte `[]` e "Cocoa? Like hot chocolate?" fora dos 6 ADs sem nenhum erro; o cliente reclamou. Corte vazio ou clipe
   quase mudo (pico < −20 dB, sem os 0,25 s iniciais e os 0,1 s finais, onde ficam o clique e o estalo) aparece como
   `✖ Fala sem voz` no `status`, e o `fazer` para logo depois dos cortes, antes das prévias. Conserto: refazer a fala e
   conferir o nível da guia. `--aceitar-sem-voz` só com fala fora de propósito ou clipe baixo já conferido de ouvido. O `montar`
   direto não passa por essa trava. Teste: `python3 scripts/teste_fala_sem_voz.py` (clipes M1F03 da 3378, sem gravar lá).
   **Volume igual entre as falas**: meça o LUFS de cada fala cortada; diferença > ~1,5 dB = "o volume da loc muda"
   (Fefo, 3219 V1: Kling 4.0 a −13/−15 e Seedance a −19/−21). `falas[i].ganho_db` (número ou {marca: número}) leva
   todas ao mesmo alvo (−14) — só ganho, sem EQ. A prévia depende só dos cortes: apague `preview_hold_*.mp4` ao mudar.
2. **prévias** — `preview_hold_<produto>.mp4` (falas da hold cortadas, em ordem).
3. **legendas** — faster-whisper na prévia e nos hooks cortados; o texto da legenda é o do roteiro (tempos alinhados por
   difflib), quebrando por EXPRESSÕES completas: corta em fim de frase/vírgula/pausa e escolhe as quebras mais
   equilibradas; nunca termina em palavra fraca (a, the, to, with...); nada de palavra sozinha ou bloco relâmpago
   (<0,8 s) — junta ao vizinho. `max_caracteres` (22) é meta, pode passar até 1,5x. SRT da hold, dos hooks e de cada AD.
   Dois-pontos sempre quebra; palavras que não podem abrir bloco ficam em `PRESAS` ("Nobel | Prize" = "split").
   Expressão que não pode quebrar → `estilo.legenda.inteiras` (lista de trechos da copy, com a pontuação ou sem):
   nome próprio ("National Eye Institute"), termo ("macular degeneration"), item + nota ("Lutein. 7 out of 10", junta
   por cima do ponto) e bloco-relâmpago que o teto de 1,5x não deixava juntar. Sem a lista o SRT não muda (BATCH#3214).
4. **ads** — `09_export/<p>/<título do card> - <Marca> - AD<k>.mp4` (título exato do card no Notion, `batch.json` →
   `card`; ex. `BATCH#3215 - Thinning Shield - Macular Degeneration - L2 - Problem Aware - Daniel - Neurobella - AD1.mp4`,
   regra do Fefo de 23/10/2026; nome antigo → `fluxo.py renomear`): hook + hold no layout de `plano.json` → `estilo` (definido a partir de
   `01_refs/`: avatar colorido ou P&B, b-roll em tela cheia ou na metade de baixo, estilo e posição da legenda); o b-roll
   entra no intervalo da `copy` de cada cena (posições em `08_auto/broll_posicoes_*.json`), trilha se houver,
   loudnorm −20 LUFS. Cada cena começa em `inicio` (pula o trecho parado do clipe, ≥ 0,5 s — `scripts/inicio_movimento.py`).
   Buraco < 0,5 s entre duas cenas é fechado (senão o avatar "pisca" 1–2 quadros); ≥ 0,5 s = avatar de propósito.
   `callout` de cena sai no meio da tela; em cena de frasco ele cobre o nome no rótulo → `callout_y` (topo do texto em px
   de 1920, ex. 330 = acima da tampa; BATCH#3222).
   **Legenda:** a pílula do `pilula.py`; estilo, margem e altura moram em `@CLIENTES/_FLUXO/LEIA-ME.md`, seção Legenda.
   Aqui só o uso: a pílula sai como PNGs; o plano muda só a altura (`legenda_y` por cena desvia de rótulo ou rosto, só para cima).
   Trecho de avatar sem cena (ex.: placa na mão) → `estilo.legenda.y_trechos` [{de, ate, y}] pelo texto da legenda. Com SRT de
   1 linha, `quebra` ≥ maior linha (a pílula não pode re-quebrar "Nobel / Prize").
   Banner/sticker com alfa (.mov 1080x1920, em loop) por cima do vídeo: `estilo.overlays` = [{"arquivo": "06_elementos/...mov",
   "trechos": [{"cena": "S14"}, {"de": "<texto da legenda>", "ate": "<texto>" ou "fim"}], "fade": 0.12}]. Banners da
   campanha em `@assets/` (Halloween 2026: zip em `@assets/halloween 2026/`; Black Friday 2026 ("Earliest", EXTRA 25% OFF,
   code EARLIESTBF25): `@assets/#BLACKFRIDAY_BANNERS-20261027T124845Z-1-001.zip`, prévias em `_PREVIEW (mp4)/`, detalhes em
   `CALIBRACAO.md` 27/10; extrair, copiar o usado para `06_elementos/`; BF Early 2026 (aviso de 02/11, code EARLYBF, não usar
   os do Earliest): `@assets/BF Early 2026/`, subpastas `25% OFF` (EXTRA 25% OFF) e `75% OFF` (75% OFF + EXTRA 25%)).
   Banner de baixo bate na legenda dos takes de frasco e no botão do Meta → preferir o de cima.
   `estilo.trilha_final_db` sobe a trilha na tela final sem voz (a −22 dB ela some ali).
   Elementos de hook (`modulos/hooks.md`, `scripts/elementos_hook.py`): `estilo.barra_tempo` (barra de marcos no topo),
   `estilo.tag_nativa` (legenda estilo Snapchat nos ~2 s iniciais) e cena `"formato": "split"` + `clipe_direita` (tela
   dividida). Campos em `02_referencia.md`. Conferir os quadros da troca de marco, da faixa e do split antes de mandar.
   Sem `estilo` no plano o `montar` para e pede o módulo referencia.
5. ~~xml~~ — fora do fluxo (Fefo, 10/11/2026): não gerar XML nem script de import para o Premiere. `fluxo.py xml` só se o Fefo pedir.
Opções: `--ate legendas` (para antes dos ADs), `--so AD2_neurobella`, `--forcar`.
## Montagem por segmentos (Fefo, 17/11/2026)
Pedido do Fefo: "trabalha uma vez no hold e nos hooks e no fim junta tudo; não remonta a cada ajuste; monta o final só quando eu aprovo hold e hooks individualmente". Origem: a BATCH#4380 remontou a batch inteira 12 vezes antes de ele ver.
- **Decisões do Fefo (17/11/2026, "Aceito as 4"):** (1) trilha: hook desde o 0 e hold a partir do fim do hook mais longo é o padrão; `trilha_momentos` só para mudar numa batch. (2) Selo do revisor: no segmento é só sugestão (prévia, sala cedo); obrigatório só no final juntado, antes da entrega. (3) Ligado para toda batch nova; batch em andamento não muda. (4) Loudness do final pelo loudnorm linear em 2 passadas aceito (prova: até 0,1 LU do entregue).
- **Liga** com `"por_segmentos": true` no `plano.json`. O `novo-plano` já cria com ele: vale para toda batch nova. Batch em andamento segue no `montar` antigo.
- **Segmentos:** `hook<n>` e `hold_<marca>`. Cada um é montado sozinho, com o mesmo grafo do AD (corte, b-roll, legenda, textos, SFX, trilha), num intermediário de alta qualidade fora do Drive. **Uma pasta por segmento** (Fefo): `%TEMP%/linha_do_tempo/<batch>/<hook1|hold_<marca>>/` (intermediário, voz e trilha) e `08_auto/segmentos/<segmento>/` (prévia da sala). Cache por hash das entradas: o `fazer` refaz só o segmento que mudou. Hook igual nas duas marcas = um arquivo só.
- **Trilha:** cada segmento leva o próprio momento da música (Fefo: "um momento pro hook e um pra hold"). Campo opcional `"trilha_momentos": {"hook": 0, "hold": 12.5}` (s da faixa). Sem o campo: hook do 0, hold do fim do hook mais longo da marca. A queda de volume na emenda continua dentro de cada segmento. No fim da hold a trilha cobre até o último quadro e sai em fade-out (`estilo.trilha_fade_s`, padrão 1 s; BATCH#4607: cortava seca no fim da voz).
- **Ao mesmo tempo:** hook e hold do AD são montados em paralelo (2 de uma vez; `LDT_PARALELO=0` desliga). Cada pedaço tem a própria pasta de trabalho.
- **Cache e estado (Central, 17/11/2026, defeitos da M1WK3B8):** o hash do segmento cobre só entradas e parâmetros que mudam imagem e som; código do montador (`.py`) nunca entra (é ignorado com aviso). Mudou a saída de propósito: troque à mão `formato=` no `Linha.segmento` (ou o `MOTOR` do `linha_do_tempo.py`). O `segmentos.json` tem trava entre processos (`segmentos.json.lock`) e escrita atômica: corpo e hook podem montar ao mesmo tempo em faixas diferentes da fila.
- **Sala:** `08_auto/segmentos/<segmento>/<id>.mp4`. A hold vai sozinha; cada hook vai com 2 s da hold depois dele. Diga na sala que é por segmento.
- **OK do Fefo:** `fluxo.py segmentos <batch> aprovar hook1 hold_neurobella` (papel ou id). O segmento aprovado fica **travado**: o AD continua com ele mesmo que as entradas mudem. Só refaz com pedido do Fefo: `fluxo.py segmentos <batch> reabrir hook1`.
- **Final:** só roda com todos os segmentos do AD aprovados (`fazer` ou `fluxo.py segmentos <batch> montar [--so AD1_neurobella]`). Ele junta os pedaços e aplica só o que atravessa a emenda: banner (`estilo.overlays`), loudnorm em 2 passadas, 720p e o lado do checklist. Um encode só. Com `PREVIA=1` o final sai em NVENC com o marcador.
- `fluxo.py segmentos <batch>` mostra cada AD com os segmentos e o OK. Estado em `08_auto/segmentos.json` (fora do `plano.json`: gravar no plano faria o `fazer` achar a batch inteira desatualizada). `limpar` apaga do cache o que nenhum AD usa.
- Fora do modo por segmentos: `one_take` e layout `cartao` (usam o `montar` antigo).

## Script de batch só para o que é único dela (Central, 17/11/2026)
Origem: desde 01/11 as batches copiaram scripts próprios em `08_auto/` (`gemini_tts.py` em 9 batches, `gerar_quadros.py` e `gerar_clipes.py` em 6, `gerar_vo.py`, `monta_lote.py`, `legenda_topo.py`). Conserto feito numa cópia não chegava às outras, e o `gemini_tts.py` lia a chave do Kie direto, sem as travas do `kie.py`.
- **O que se repete mora no núcleo** (`@CLIENTES/_FLUXO/scripts`), como comando ou opção do `fluxo.py`/`kie.py`:
  - voz Gemini: `kie.py gemini-tts TEXTO.txt SAIDA.wav --voz Sulafat [--estilo] [--ritmo] [--cena] [--contexto] [--perfil]` (no lugar do `gemini_tts.py`);
  - quadros, clipes e VO do `plano.json`: `fluxo.py pedidos <batch> quadros|clipes|vo [--so IDs] [--voz ...]` grava `08_auto/pedidos_<tipo>.json` e **não gasta**; depois do ok de crédito, `kie.py lote <json>` (no lugar de `gerar_quadros.py`, `gerar_clipes.py`, `gerar_vo.py` e `monta_lote.py`). `ref "-"`: padrão = sem quadro, clipe só de texto; `--traco quadro` = quadro sem referência;
  - clipe preto com a voz da fala para o montador: `fluxo.py vo-clipes <batch>`;
  - legenda mais alta numa cena (frasco na bancada): campo `legenda_y` da cena no `plano.json`, ou `estilo.legenda.y_trechos` (no lugar do `legenda_topo.py`).
- **Script novo em `08_auto/` só para o que é único da batch:** o `montar_plano.py` (conteúdo do plano), um formato visto pela 1ª vez (split da 4293, texto por palavra-chave da 4205, packshot da 4382). Nada de whisper, loudnorm, silêncio, legenda, export nem chamada ao Kie dentro dele.
- **Repetiu numa 2ª batch = vai para o núcleo, pela Central.** Não copie o script de uma batch para outra: anote no estado da batch, siga com o contorno e mande à Central uma linha com o caminho e o que falta (trava 3 de `@CLIENTES/_FLUXO/REGRAS_DA_SESSAO.md`). A Central muda o núcleo com backup `*.bak_<data>_<motivo>`.
- Batch com sessão aberta segue com os scripts dela até fechar (ordem do Fefo, 17/11/2026).

## Resolução
Regra do Fefo (02/11/2026): vídeo gerado e AD final sempre em **720p** (720x1280). `fluxo.py`, `cartao.py` e `umtake.py` compõem em
1080x1920 (por isso posições e overlays seguem em px de 1920) e descem na saída.

## Conferência: só o `fluxo.py checar` (pelo `montador`)
O passo de conferência é um só: `fluxo.py checar <batch>`, uma vez por versão (roteiro único de `@CLIENTES/_FLUXO/QUALIDADE_DO_BATCH.md`).
O resto desta seção **não é passo**: é como entender e corrigir o que o `checar` ou o revisor acusou.
**Trava antes do render final (Frente 1, 09/11/2026):** depois do `fluxo.py fazer <batch> --ate legendas` e antes do `fazer`
final, rode `python3 @CLIENTES/_FLUXO/scripts/lint_plano.py <batch>`. Ele monta a linha do tempo de cada AD pela mesma
conta da montagem, sem renderizar, e **sai com 1** quando acha: 3D seguido ou acima de 2,5 s; pausa hook→hold abaixo de
0,30 s; AD do Daniel sem trilha; trecho acima de 3 s sem troca; legenda ou header em cima do rosto ou do rótulo (visão do
Mac no quadro do clipe). Corrija no `plano.json` (`dur_max`, avatar entre os 3D, `respiro_hook_s_H<n>`, `legenda_y`) e rode
de novo até sair 0. Aviso (`!`) não trava: é o que o script não conseguiu ler. Versão já exportada:
`lint_plano.py <batch> --export <AD.mp4>` (lê o vídeo e casa cada trecho com o clipe de origem; ~1,5 min por AD).
O pedido ao revisor roda `fluxo.py checar <batch>` (freeze, lascas, ritmo e lint, pela ficha) e recusa com falha.
**Checklist da Louise (13/11/2026, sem dispensa):** o `checar` também roda os 6 itens em cada AD (`@CLIENTES/_FLUXO/scripts/checagens/checklist.py`) e grava `08_auto/checklist_V<k>.json`: 1 texto no 4:5 e legenda com centro até 0,65 (OCR a 2 fps + camadas do montar); 2 legenda na lista fechada (pílula; outra só com `estilo.legenda.pedido_brief`); 3 Whisper no AD inteiro contra o plano (palavra trocada, faltando, repetida, fim cortado, marca, pausa > 0,45 s); 4 trilha ≥ 15 dB abaixo da voz (falha < 12; o montar grava `08_auto/mix_AD<n>_<p>.json` pelos stems) e −20 LUFS; 5 plano parado, tremido ou borrado; 6 notas da revisão. Item vermelho: o revisor não recebe o pedido, a sala não aprova e o `frameio.py` não sobe. `--sem-checagens` e `dispensa_V<k>.txt` não valem para estes itens. Rodar só ele: `fluxo.py checar <batch> --so checklist` (~1 min por minuto de vídeo, pela fila).
**Conferência = um comando (16/11/2026, `@CLIENTES/_FLUXO/QUALIDADE_DO_BATCH.md`, "Roteiro único"):** `fluxo.py checar <batch>` roda as baratas (lint, freeze, lascas, ritmo) e, se passam, o checklist L1–L6 com true peak, com uma transcrição só por vídeo. Não rodar à mão nenhum dos scripts abaixo como passo: a lista serve para **entender e corrigir** o que o `checar` ou o revisor acusou. "Imagem × fala" e "assistir o AD" são do revisor (passo 9) e da sala.
- Prancha `ffmpeg -i AD.mp4 -vf "fps=1/6,scale=180:-1,tile=8x2" s.jpg` (prancha com fps+tile pode mostrar quadro preto
  falso — conferir com `-ss`); loudness `-af ebur128`.
- Emendas internas de voz < −50 dB; respiro hook → hold ≥ 0,2 s; ritmo de cada fala ~3,3 pal/s.
- Buraco entre quadros: `ffmpeg -i AD.mp4 -map 0:v -vf showinfo -f null -` → nenhum `pts_time` pulando > 0,1 s (era o
  último quadro do hook parado 0,2 s na emenda com a hold; corrigido pelo `vtrim()`, BATCH#2480).
- Hooks: conferência de `modulos/hooks.md` (quadro 0 com ação, produto até ~2 s, header legível sem som, 1º corte até
  ~4,5 s, 3 hooks com 1º quadro diferente).
- **Ritmo** (SOP do Daniel, regra do Fefo, 30/10/2026): algo muda na tela a cada 1 a 3 s. Copie o AD para o scratchpad e rode
  `python3 scripts/ritmo.py <AD.mp4>` no AD1 de cada marca e nos hooks dos outros ADs. Cada trecho acima de 3 s é corrigido
  com novo corte, punch-in ou zoom (`punch_in`, `efeitos_<n>.py`), ou justificado ao Fefo: ref mais lento manda. O script
  conta corte e punch-in, não vê zoom lento e pode perder corte entre clipes parecidos (acertou 125 de 130 emendas em 3465,
  3467 e 3222): olhe o trecho antes de mexer.
- **Legenda:** no máximo 7 palavras na tela (`srt()`, ajuste em `batch.json` → `legenda.max_palavras`); só expressão de `inteiras`
  passa disso. Na revisão, legenda regerada pode quebrar diferente nos blocos que passavam de 7 (~1% em 3222, 3467 e 3219):
  se o pedido não é de legenda, confira que só esses mudaram.
- **Imagem × fala** (regra do Fefo, 30/10/2026): as checagens técnicas não veem se a imagem combina com a frase. Rode
  `python3 scripts/imagem_fala.py <AD.mp4> --srt 08_auto/legendas/AD<k>_<p>.srt --pos 08_auto/broll_posicoes_AD<k>_<p>.json`
  (pranchas e tabela em `$TMPDIR/vsl_conferencia/`, fora da batch; cada legenda ou troca de cena vira um quadro numerado).
  AD1 de cada marca inteiro; nos outros ADs, com `--hook`, só o hook, se a hold for a mesma. Trecho a trecho: a imagem mostra
  o que a frase diz (item, parte do corpo, produto da marca certa)? Está genérica, repetida ou com energia errada para a
  frase? Antes de apontar, abra o quadro real (`-ss <t> -frames:v 1`) e veja o trecho: um quadro só pode enganar. Só o
  que ficar confirmado vai ao Fefo, com nº, tempo, frase, o que aparece e a troca proposta; o resto vira uma linha de
  "verificado e liberado". Roteiro e VO aprovados não entram. Trocar cena que gasta crédito segue "crédito só com ok".
  A prancha não substitui as checagens abaixo: defeito de poucos quadros só aparece nelas.
- `freezedetect=n=0.008:d=0.4` no AD (congelamento = `inicio` faltando); buracos de 0–0,7 s em `broll_posicoes_*.json`.
  Trecho parado escolhido: a janela de mais movimento do clipe (diferença entre quadros) ou push-in leve (1,00→1,06).
  Fala inteira com pouco movimento (plano aberto, personagem pequeno no quadro) → `falas[i].push_in: 0.02` (zoom
  contínuo 2%/s na prévia da hold, centrado, rosto no terço de cima; BATCH#2480). Vale também para o avatar sentado de
  câmera fixa em que só a boca mexe: 0,015–0,02 em todas as falas da hold zerou ~55 trechos parados por AD na 3214 e ~18
  na 3215 (zoom máx. ~18% numa fala de 12 s, rosto inteiro). B-roll lento (frasco parado, 3D lento, POV, item na mesa):
  push-in local de 5–8% num `08_auto/efeitos_<n>.py` (3214, 3215); cena escura pede 12–22% (a diferença entre quadros é
  pequena no escuro e o freezedetect continua acusando).
  **Todo push-in em subpixel** (`perspective` com `interpolation=cubic:eval=frame`, t = quadro ÷ fps), nunca
  `scale eval=frame` + `crop`: esse anda em pixel inteiro, a imagem fica parada ~10 quadros e pula 2–3 px, e o cliente
  vê tremor ("why are the doctor videos shaking", 3214 V1). O `fluxo.push()` e o `efeitos_3214.py` já usam o
  `perspective`. Com o zoom suave a cena escura precisa de mais: S10 (noite) 0,26 e S35 (3D escuro) 0,30 em 5 s
  (0,15 e 0,12 bastavam com os pulos). Conferir o tremor: deslocamento quadro a quadro (correlação de fase) num canto
  de fundo, sem pulos isolados de ≥ 2 px.
  Imagem desfocada (avatar com blur 30 sob gráfico) só passa com push-in ≥ 18% (usado 20%); end card parado → push-in
  contínuo de 2%/s. Avatar falando com pouco movimento (0,4–0,5 s) pode ser marcado: recorte no rosto e confira se pisca/fala.
- `python3 scripts/lascas.py <AD.mp4> 08_auto/broll_posicoes_AD<k>_<p>.json` em todo AD: plano de até 12 quadros =
  "frame estranho" (Fefo, BATCH#1977). O `segmentos` já cobre a lasca de avatar entre cena e emenda (corte de silêncio,
  troca de fala, hook → hold, fim do AD, e a emenda "rente" de −0,02 a +0,04 s); o que sobrar costuma ser corte de
  silêncio curto demais → `.manual.json`. Falsos positivos: b-roll de 24 fps passado a 30 (quadro repetido a cada 5,
  diferença ~0) e, na `divisao`, troca de legenda fora da máscara (y 0,55–0,9) — confira na fps nativa antes de mexer.
- **Tremido no b-roll** (o `lascas.py` não pega; AD2 da 3214): mapeie cada quadro do AD para o quadro do clipe-fonte
  (argmin da diferença) e conte saltos ≥ 2. A cadência certa de um clipe de 24 fps é 1-1-1-2; pulo de 2 com quadro
  triplicado = o overlay do b-roll empatando com o quadro principal (corrigido no `montar` em 23/10/2026).
- **Cortes duplos no `metade_baixo`**: emenda do avatar (pulo do punch-in em cima) a 1–12 quadros da troca do b-roll
  embaixo = dois cortes seguidos. Puxe a borda do b-roll para o quadro da emenda (2080 V3; ainda não está no `fluxo.py`).
- Troca de setup do avatar: sobra de fala depois da última palavra que o b-roll não cobre = quadros do avatar errado
  ("weird cut") → aparar no `.manual.json`.
- **Imagem × áudio** (2082): conte os quadros (`ffmpeg -i AD.mp4 -map 0:v -c copy -f null -`, linha "frame=") contra a
  duração do áudio, e rode o Whisper nos últimos 5 s do AD (a fala final inteira tem de estar lá). Em montagem por script
  com concat de muitos trechos: `fps=30` ANTES do `trim` e corte por quadros (`trim=start_frame:end_frame`); `setpts=N/(30*TB)`
  antes da legenda (o `concat -c copy` de mp4 encurta cada trecho e o encode seguinte descarta quadros). Mux sem
  `-shortest` quando o áudio é mais curto (comeu 4 quadros do fim na 2086): `apad=whole_dur` + `-t` da duração do vídeo.
- **Hook de 24 fps**: corte alinhado à grade de 24 fps (na 1980, 80 quadros de imagem para 2,74 s de áudio congelaram o
  b-roll 3 quadros antes do avatar).
- Emenda hook → hold: desde 23/10/2026 o `montar` apara o áudio do hook no nº de quadros do vídeo (o AAC completava o
  último pacote e a hold começava até 23 ms depois = pulo de 2 quadros, 3215) e põe o b-roll na grade de 30 fps meio
  quadro antes (3214). A regra antiga "borda = t(quadro) − meio quadro" não precisa mais ser feita à mão.
- **Intermediários fora do Drive, apagados no fim** (regra do Fefo, 29/10/2026): desde essa data o `montar` e o
  `umtake` gravam os trechos, PNGs, `.ass` e `fc_*.txt` em `$TMPDIR/vsl_montar/<batch>/` (`fluxo.tmp_montar`) e apagam
  a pasta no fim de cada AD. Montagem ou checagem à mão (frames, trechos, testes de render) vai para o scratchpad da
  sessão ou `$TMPDIR`, nunca para a batch. Só o MP4 final vai para `09_export`. Ao fechar a sessão, apagar o que
  sobrou (`rm -rf "$TMPDIR/vsl_montar/<batch>"` e as pastas de trabalho do scratchpad), depois de conferir que o
  export abre e passou nas checagens. Não confundir com quadro de origem: `_quadros/` do b-roll (ex.: 3375) são os
  stills que viraram clipe no Kling/Seedance e ficam na batch.
- Se o ffmpeg falhar ele deixa mp4 de 0 byte que o `status` vê como "ok": apagar antes de rodar de novo.
- **Várias sessões renderizando ao mesmo tempo** no Drive dão "Error sending frames to consumers: Operation timed out":
  monte numa cópia espelhada no scratchpad (symlinks para a batch; `09_export` local; o `_tmp_montar` já fica fora do Drive) e copie o MP4 depois.
  O `broll_posicoes_*.json` e o XML saem com o caminho do espelho: antes de entregar, regenere o XML com o `fluxo.py`
  apontando para a batch no Drive (3214).
- `~/bin/ffprobe` deste Mac é um atalho que SÓ imprime a duração (ignora `-show_entries`): para fps e streams use `ffmpeg -i`.
- **Olhar de revisor** (curso Ad Creators Lab, 29/10/2026) é do `revisor-de-video`, não do montador: AD em 1,75x; um texto
  na tela por vez; produto nunca coberto; no item citado, mostrar o próprio; close do produto nas pausas do avatar.
- A versão vai ao Fefo pela sala (`modulos/11_review_room.md`), não por SendUserFile. Sala cedo: trava 5 de `REGRAS_DA_SESSAO.md`.

## Fim e emendas da voz (checagem fixa, Fefo, 09/11/2026)
- **Fim do AD:** a última palavra ganha +0,45 s de cauda no recorte e fade de 0,3 s na voz; depois, 1,4 s de cauda com fade
  de trilha e de vídeo. Corte seco no fim foi nota do Fefo na 4205.
- **Entre frases** (VO única cortada em trechos): emenda com crossfade curto (10–20 ms), nunca corte seco com a voz soando.
- O item 3 do checklist (no `checar`) transcreve o AD inteiro contra o roteiro. Palavra fraca no fim some ("breakfast",
  "flow"): se ele acusar, ouça os últimos 5 s antes de mexer.
