# Módulo: entrega (Frame.io + Google Drive + "Ready for view" + Notion + Clock Out)
Roda no fim de toda batch e no fim de toda revisão, depois de conferir os ADs. Subir e gerar links publica para o time:
faça quando o Fefo pedir a entrega ou disser que a batch está pronta.

**Antes do "Ready for view", sempre mandar os vídeos ao Fefo para revisar** (regra do Fefo, 13/10/2026): publicar a versão
nova na Review Room (`11_review_room.md`; SendUserFile só se ele pedir) e esperar o OK dele no chat. Aprovar na sala não
libera a entrega. Na mesma pergunta, diga tudo o que o OK libera:
"Posso subir no Frame.io, comentar o Ready for view no card do Notion e mudar o status para CS NEEDS TO REVIEW?"

Ordem depois do OK: 1) Frame.io e links; 2) Google Drive; 3) mensagem "Ready for view"; 4) Notion (comentário +
status); 5) marcar Done no `dia.json` (o Clock Out sai quando o Fefo pedir). Cada passo está numa seção abaixo.

**Horário: com o "pode entregar" (ou OK que cite a entrega), entregar na hora, na própria sessão** (Fefo, 09/11/2026;
`entrega.horario: null` no perfil). Nada de agendar às 18h: tarefa agendada travava em permissão e ficava offline (06/11).
Agendar só se o Fefo pedir um horário; aí vale `create_scheduled_task` único com `fireAt`, prompt autossuficiente com os
5 passos, conferência de bytes dos arquivos aprovados antes de subir e trava `entrega_<hora>.lock` contra repetição.
Várias entregas seguidas: uma de cada vez, porque disputam o navegador do Notion.
**O OK tem de ser escrito pelo Fefo dentro desta thread/sessão:** OK dado no chat do projeto não libera a ação aqui.
Peça um OK único que cubra tudo o que falta ("pode entregar" = Frame.io + Ready for view + Notion + dia.json).

## Trava: checklist da Louise verde, sem dispensa (13/11/2026)
Antes de subir qualquer arquivo (batch nova e revisão), no MP4 **final** (sem `.PREVIA.txt`):
```
py -X utf8 "@CLIENTES/_FLUXO/scripts/fluxo.py" checar "<batch>"                       # roda os 6 itens e grava 08_auto/checklist_V<k>.json
py -X utf8 "@CLIENTES/_FLUXO/scripts/checagens/checklist.py" entrega "<batch>"        # 0 = pode entregar
```
- O `frameio.py nova` e `versao` chamam a mesma trava e **recusam** vídeo sem checklist verde para aquele arquivo
  (mesma impressão digital) ou de prévia. O "pode entregar" e a dispensa do Fefo não valem para estes itens: item
  vermelho se corrige e roda de novo.
- Revisão: o item 6 só fica verde com `00_roteiro/revisao_V<k>.md` todo `[x]` e com prova (`10_revisao.md`, passo 1b).
  Depois de subir, gere o texto das respostas (`notas_revisao.py respostas "<batch>" --versao <k>`) e poste no
  Frame.io só com ok do Fefo.

## Onde fica no Frame.io
Conta "Umut's Account" → projeto **Hike Balance Brand** → pasta de quem usa → `BATCH_<n>/`. Nos comandos abaixo,
`<pasta>` = `frameio.pasta` do perfil (Fefo: `Hike Balance Brand/FEFO`).
Padrão de versões do Fefo: o que está **solto na raiz** de `BATCH_<n>/` é a versão atual; versões antigas ficam em
`V1/`, `V2/`, `V3/`… (próximo número livre). Não usar pilha de versões.

## Script: `scripts/frameio.py` (API Frame.io V4, sem limite de tamanho)
```
cd "<raiz>/_FLUXO_VSL/scripts"
python3 frameio.py ls "<pasta>/BATCH_<n>"                       # o que já está lá (+ subpastas)
python3 frameio.py nova "<pasta>/BATCH_<n>" <arquivos.mp4> --teste   # mostra o plano
python3 frameio.py nova "<pasta>/BATCH_<n>" <arquivos.mp4>           # raiz → V<k>, novos na raiz
python3 frameio.py links "<pasta>/BATCH_<n>"                     # 1 link f.io público por marca
python3 frameio.py comentarios "<pasta>/BATCH_<n>"               # comentários de revisão
```
**No PC Windows:** troque `python3 frameio.py` por `py ~/.vsl-batch-editor/frameio_ev.py` (login do time,
o da conta de time abaixo) e rode com `PYTHONIOENCODING=utf-8`. Nunca `frameio_fefo.py` (conta pessoal) para a EV.
Os ADs sobem com o nome do card: `<título exato do card> - <Marca> - AD<k>.mp4` (regra do Fefo, 23/10/2026). Antes de
subir, confira os nomes contra o título do card; algum ainda em `BATCH<n>_AD<k>_<p>.mp4` → `python3 fluxo.py renomear
"<batch>"`. O `links` separa as marcas pela última marca do nome (o título pode citar "(VisioVance)" antes).
Black Friday 2026 (cliente, 27/10/2026): `[BATCH#] - BF Earliest 2026 - [Concept name] - [Angle/condition] - [Concept level]
- [Awareness stage] - [Creative strategist name]`. Card BF fora desse padrão (ex.: "BF Earliest 2026" depois da condição,
"BATCH 3388" sem #): pergunte ao Fefo se sobe com o título do card ou no padrão, antes de renomear.
1. **Antes de subir, compare**: liste a pasta e confira o tamanho em bytes de cada arquivo da raiz contra os exports
   locais atuais (`09_export/<p>/`; nas antigas `View*/`, `export/`), ignorando `_old/`. Iguais = já está atualizado, não suba de novo.
2. Pasta da batch ainda não existe no Frame.io → crie-a dentro de `<pasta>` antes (ou peça ao aprovador). O `frameio.py`
   não tem comando para criar pasta: crie pela API, `POST /accounts/{aid}/folders/{fid}/folders` com o id da `<pasta>`
   (2480, 2481, 3214 e 3215), e depois rode o `nova`.
3. Depois de subir, confira de novo: tamanhos iguais aos locais e `status=transcoded`.
4. `links` cria 1 share por marca (acesso público, download liberado) com os vídeos da raiz cujo nome tem a marca.

Login: o acesso fica em `~/.frameio/tokens.json` (no Mac de cada pessoa) e renova sozinho. Se expirar,
`python3 frameio.py login` no Terminal de quem usa (run_in_terminal): a pessoa entra na Adobe e só copia a URL do
localhost (Cmd+L, Cmd+C) — o script lê da área de transferência. Nunca peça para colar o código no chat. App da Adobe:
projeto do Developer Console do Fefo com Frame.io API, "OAuth Single-Page App", redirect `https://localhost/callback`;
o e-mail Adobe de cada pessoa precisa estar em **Beta users** (o Fefo adiciona; `modulos/00_configurar.md`).
**Conta de time (Umut, 12/11/2026):** a Empire Vision tem limite de 15 contas no Frame.io e passou a usar uma conta
compartilhada por várias pessoas. O Umut tirou o acesso da Adobe pessoal do Fefo e pôs o e-mail do time.
O login do Frame.io da EV é o **e-mail do time** (está no `frameio_ev.py`; acesso passado pela Louise; convidado no Hike Balance Brand,
pasta `FEFO`). No PC: `py ~/.vsl-batch-editor/frameio_ev.py` (token `~/.frameio/EV_empire_vision_tokens.json`). No Mac,
o `tokens.json` tem de ser refeito com esse login. A conta pessoal do Fefo (`frameio_fefo.py`, projeto "Empire Vision")
foi só um desvio de 12/11: não usar para a EV.
Uso pela API não conta como atividade: no painel de usuários do Umut (12/11), a conta pessoal do Fefo aparecia com "Last active
15 days ago", embora tenha entregado pelo `frameio.py` em 09, 10 e 11/11. Foi esse o motivo da remoção. O e-mail do time
entra como convidado do projeto (`/invited_projects`), não como um dos 15 usuários da conta.
Armadilhas: o firewall do Frame.io dá 403 para o User-Agent padrão do Python (o script manda o próprio); o projeto é
de convidado → os projetos vêm de `/invited_projects`; arquivo 85 MB+ não passa pelo upload do Claude in Chrome (10 MB).

## Google Drive
Conector do Google Drive na conta do perfil (`drive.conta` do `perfil.json`). Raiz fora do Drive
(`drive.conta` vazio) = a mensagem vai sem o bloco do Google Drive. A raiz (no Fefo, a pasta `@EMPIRE VISION`) está como "qualquer pessoa
com o link → Leitor" (tudo dentro herda). Link = a pasta de exports da batch
(`09_export/`; nas batches antigas `View/`, `view/`, `export/`), com a versão atual na raiz e as anteriores em `_old/V<k>/`
dentro dela. Busque com `search_files` (title = '<pasta>' e o parentId da
batch) e confira com `get_file_permissions` que tem `anyone/reader`. Use `viewUrl` + `?usp=sharing`.

## Mensagem final — exatamente neste formato, como TEXTO NORMAL (nunca em bloco de código)
O Fefo cola no Notion; dentro de bloco de código os links não ficam clicáveis. URL pura, uma por linha:

Ready for view:
Visiovance: https://f.io/XXXX
Neurobella: https://f.io/YYYY

Google Drive:
https://drive.google.com/drive/folders/<id>?usp=sharing

## Notion: comentário "Ready for view" + status CS NEEDS TO REVIEW (regra do Fefo, 15/10/2026)
Só com `notion.usar: true` no perfil; senão pule esta seção (a pessoa cola a mensagem à mão).
Faça depois do OK do Fefo e da mensagem acima, com o mesmo texto. Use o navegador interno (`mcp__Claude_Browser__*`,
já logado no Notion com a conta de quem usa).

**Comentário: `scripts/monitor/notion_acao.js`** (uma chamada, URLs já como link, com conferência; testado no card 1969
em 09/11/2026). Quem faz é o `executor-mecanico` (subagente novo, com o OK escrito na tarefa). Numa aba do Notion aberta
com `preview_start` (qualquer página logada), troque o bloco `PEDIDO` e rode o arquivo inteiro com `javascript_tool`:
`CARD` = link do card, `STATUS: null`, `COMENTARIO` = a mensagem "Ready for view" acima, com `\n` entre as linhas (as URLs
viram link sozinhas, sem espaço extra). Primeiro `MODO: 'conferir'` (mostra o status atual e os links previstos), depois
`'aplicar'`. Pronto com `ok: true`, `comentario_confere: true` e `links_no_comentario` = 3. `ok: false` ou `erro`: não
rode de novo; olhe o card e, se o comentário não estiver lá, use o caminho manual do passo 3.
**Status:** pela API o Notion recusa; continua pelos cliques do passo 4.

Caminho manual (clicar e digitar):
1. **Card da batch:** o link está em `00_roteiro/briefing.md` ("Card no Notion"). Sem link: abra o `notion.board` do
   perfil, rode `scripts/monitor/notion_cards.js` com `javascript_tool` (com `RESP` = `notion.responsavel`) e pegue em
   `meus` o card com o número da batch. Grave o link no briefing.md para a próxima vez.
2. Abra o card com `preview_start` e a `url` (em aba escondida, `navigate` às vezes não carrega o Notion).
3. **Comentário:** clique em "Adicionar um comentário..." (`find`). Digite a mensagem linha por linha com `computer`
   `type`. Entre as linhas use `key` "shift+Return" (o Enter sozinho já envia); para a linha em branco, aperte
   shift+Return duas vezes. No fim, `key` "Return" para enviar. Se o Notion abrir menu de colar/link, aperte Escape.
   Confira com `get_page_text` que o comentário apareceu inteiro, com as URLs.
   O shift+Return pode chegar 1–2 s atrasado (BATCH#1977): espere ~2 s e confira o texto da caixa (`javascript_tool`,
   innerHTML da caixa "Adicionar um comentário...") antes de apertar de novo — apertar de novo dobra a quebra.
   **Desde 22/10/2026 (3194 e 3195):** "shift+Return" não quebrou mais a linha; use `key` "shift+Enter". E ponha um
   `wait` de 1 s antes e depois de cada shift+Enter: colado num `type` dentro do `browser_batch`, ele se perdeu e as
   linhas grudaram. Com as pausas, as 2 caixas saíram certas. Para desfazer um trecho: BackSpace com `repeat` (máx. 100).
   **Links clicáveis (regra do Fefo, 21/10/2026):** o Notion só transforma a URL em link quando vem um **espaço** logo
   depois dela. Digite cada URL com espaço no fim (`"Visiovance: https://f.io/XXXX "`) antes do shift+Return/Return.
   URL seguida direto de quebra fica texto puro (todos os comentários até 16/10 ficaram assim). Mesmo com o espaço, o
   teste de 21/10 falhou às vezes (URL do Drive sozinha na linha). **URL no começo da linha (depois do shift+Return)
   leva também um espaço ANTES** (`" https://drive.google.com/... "`): sem ele o Notion não vira link nem com o espaço
   no fim (BATCH#2481, 21/10: com o espaço antes, 2 `<a>` de 2). Mesmo assim, **antes de enviar** confira na caixa
   (`javascript_tool`, `box.querySelectorAll('a')`) que há um `<a href>` para cada URL (3 na mensagem padrão). Se faltar
   algum, não envie: avise o Fefo e mande a mensagem para ele colar à mão.
   Não funcionam: cmd+K (abre a busca global do Notion, não o editor de link), shift+setas (não selecionam texto na
   caixa) e cmd+v (o navegador interno não lê a área de transferência do Mac).
   **Conferir o comentário enviado numa aba nova aberta com `preview_start`** (a aba de `navigate` ficou em branco, e a
   aba de antes do envio mostra a cópia velha). Na aba nova o Notion recolhe os comentários do meio (mostra o 1º e o
   último): expanda antes de concluir que faltou. Não reenvie antes dessa conferência (2481, 3214, 23/10).
   **Nunca cmd+a na caixa de comentário:** em 21/10 o foco tinha saído da caixa, o cmd+a selecionou a página e o
   BackSpace apagou o corpo do card da BATCH#1977. Para recomeçar o rascunho: clique na caixa, confirme com
   `javascript_tool` que `document.activeElement` é a caixa e que a seleção está dentro dela, `End` e BackSpace com
   `repeat` igual ao número de caracteres do rascunho.
4. **Status:** clique no valor atual do Status (ex.: "Started" ou "Revisions") e escolha **CS NEEDS TO REVIEW**.
   Confira que a página mostra "Status" seguido de "CS NEEDS TO REVIEW".
   Clique UMA vez no valor e ache a opção com `find` (o screenshot do Notion atrasa: um 2º clique cai numa opção do
   menu já aberto — na 1977 virou "Not started Shahzad" sem querer). Confirme abrindo o card de novo com `preview_start`.
5. Se algo falhar (login, card não achado), não insista: avise o Fefo e mande a mensagem para ele colar à mão.

## Clock Out: marcar a batch como Done (regra do Fefo, 15/10/2026)
Só com `clock.usar: true` no perfil; senão pule esta seção.
**O CLOCK OUT tem exatamente as mesmas batches do CLOCK IN do dia, na mesma ordem.** No perfil do Fefo, quem posta os
dois no Slack (#video-editor-report, no thread do dia): o 🟢 CLOCK IN sai com o "pega" da sessão principal, quando o
Fefo abre as batches da fila (`scripts/monitor/PEGA.md`, desde 22/10/2026), e o 🔴 CLOCK OUT sai **só quando o Fefo pedir**
("manda meu clock out"; Fefo, 09/11/2026: "deixa que eu aviso"), com envio direto (`slack_send_message`, `SLACK.md`) no
thread do dia. Não há horário fixo nem tarefa automática. A sessão da batch não manda Clock Out por conta própria.
Conector não edita mensagem: lista mudou depois do envio = nova resposta no thread com a lista inteira. Perfil com `clock.automatico` vazio: no passo 3, diga "Marcada como Done; texto do Clock Out para você colar:".
A lista do dia fica no `clock.dia_json` do perfil, relativo à raiz (Fefo: `_FLUXO_VSL/scripts/monitor/dia.json`), no formato
`{"AAAA-MM-DD": {"clock_in": "HH:MM", "batches": {"BATCH#NNNN": "<situação>"}, "fora_do_clock_in": [...], ...}}`.
1. Depois do passo do Notion, em `batches` do dia de hoje, troque a situação da sua batch para
   "Done - CS needs to Review". Não acrescente nem tire nenhuma outra batch. Leia o arquivo, mude só a sua chave e salve.
2. **Sua batch não está na lista de hoje** (ou o dia ainda não existe): acrescente-a no fim de `batches` e também na
   lista `fora_do_clock_in` do dia (se for revisão, também na lista `revisoes`). Quem mandar o Clock Out posta antes um CLOCK IN
   corrigido, para os dois baterem.
3. Diga ao Fefo em uma linha: "Marcada como Done no dia.json; entra no Clock Out quando você pedir." Mostre como vai ficar o Clock
   Out, com as batches de `batches` do dia, em texto normal e sem bloco de código. **Todas saem como "Done - CS needs to
   Review"**, qualquer que seja a situação gravada (regra do Fefo, 23/10/2026). Tasks novas primeiro, depois uma linha em
   branco e as revisões (lista `revisoes` do dia ou situação "Revision …"), numeração contínua; **a revisão leva
   " - Revision" logo depois do número da batch**, como no Clock In (pedido do Fefo, 23/10: "sinalizar visualmente qual
   foi a de revisão"). Data = dia sem zero à esquerda + mês abreviado em inglês (`LC_ALL=en_US.UTF-8 date +"%-d %b"` →
   "15 Oct", "9 Oct"). **Cada linha termina com os ADs e a duração média** (regra do Fefo, 30/10/2026): " - 6 ads - avg 2:22",
   do `python3 scripts/monitor/ads_do_dia.py` (ADs da versão atual em `09_export/<produto>/`, sem `_old/` nem `4x5/`; na
   revisão, todos os ADs da versão atual). Batch sem exports (QA sem edição): a linha sai sem esse trecho:

🔴 CLOCK OUT - Video Editor Date: 15 Oct

1. Task: BATCH#1980 - Done - CS needs to Review - 6 ads - avg 2:22
2. Task: BATCH#1977 - Done - CS needs to Review - 6 ads - avg 1:18

3. Task: BATCH#1975 - Revision - Done - CS needs to Review - 6 ads - avg 1:56

   Batch que ainda não está como Done no `dia.json`: sai como Done no Clock Out do mesmo jeito, mas avise o Fefo para
   conferir se a entrega dela saiu.

## Passo fixo no fim: registrar no segundo cérebro (Fefo, 09/11/2026)
Depois de entregar (inclusive revisão), antes de encerrar, sem o Fefo pedir: acrescentar a entrada da batch em `Meu Drive/@segundo cérebro/3 Recursos/Aprendizados das batches.md` (seção Empire Vision: o que foi, o que se aprendeu, o que se otimizou, custo se houve), uma linha no diário do dia e a Situação da nota/área ([[Batches VSL]]) conforme `@segundo cérebro/CLAUDE.md`. Otimização do fluxo que vale para todas vai na seção "Otimizações do fluxo". Modelo: Sonnet baixo basta.
