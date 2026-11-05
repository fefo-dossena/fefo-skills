---
name: vsl-batch-editor
description: Produz batches de VSL/UGC ads de Neurobella e VisioVance de ponta a ponta, em módulos que rodam conforme a necessidade - roteiro e plano de cenas, personagens, falas do avatar com áudio nativo (Kling; Seedance só em Drama ad), b-roll (Sunburst + Kling no Kie), corte de silêncio, legendas (faster-whisper), montagem final em MP4 e timeline XML para o Premiere.
---

# VSL Batch Editor — Neurobella / VisioVance

Fluxo de produção dos ads do Fefo. Responder sempre em português do Brasil.
"Encerrar/fechar o projeto" para o Fefo = **terminar de produzir**, não parar.

## Quem está usando: a raiz e o perfil
Mais de uma pessoa usa esta skill, cada uma na **própria pasta de batches** (a raiz) e com as próprias contas.
Comece toda conversa assim:
```
cat ~/.vsl-batch-editor/raiz                                  # a raiz deste Mac
cd "<raiz>/_FLUXO_VSL/scripts" && python3 fluxo.py perfil      # quem usa, contas, quem aprova
```
- Sem o arquivo da raiz ou sem perfil → módulo `configurar` (perguntas de início; monta a pasta) antes de qualquer outro.
- Perfil sem `fonte_da_skill` (qualquer pessoa menos o Fefo): rode antes
  `python3 "<pasta desta skill>/scripts/fluxo.py" instalar "<raiz>"` — traz para o `_FLUXO_VSL` o que o zip da skill
  tiver de mais novo (scripts, módulos, este arquivo) e não mexe em perfil, `CALIBRACAO.md` nem batches.
- Onde a skill diz "o Fefo" como quem recebe os exports e dá o OK → o `aprovador` do perfil; chame a pessoa pelo `nome`.
  "Regra do Fefo" (qualidade, estilo, cortes, legendas, prompts) vale para todos.
- Geração → `geracao` do perfil (Kie). Frame.io → `frameio.pasta` no lugar de `Hike Balance Brand/FEFO`. Google Drive →
  `drive.conta`. Notion → `notion` (`usar: false` = não mexer no Notion, só mandar a mensagem). Horário da entrega →
  `entrega.horario` (`null` = logo depois do OK). Clock → `clock` (`usar: false` = pular; lista do dia = `clock.dia_json`).
- Item em `pendente` (ex.: login do Frame.io): o módulo que precisa dele para e diz o que falta.

## Onde está tudo
- Raiz: a pasta de batches de quem usa (`~/.vsl-batch-editor/raiz`). A do Fefo é
  `/Users/escala/Library/CloudStorage/GoogleDrive-fefo.dossena@gmail.com/Meu Drive/@CLIENTES/@EMPIRE VISION/2026`.
- `_BATCH_MODELO/` = estrutura de uma batch nova (copiar e renomear). `_FLUXO_VSL/` = esta skill, `scripts/`, `modulos/`, `CALIBRACAO.md`.
- Versões antigas da skill (zips anteriores e backup de arquivo antes de mudar) vão para `_FLUXO_VSL/old/`; na raiz fica só o zip atual.
  Zip novo: `python3 fluxo.py empacotar` (leva `SKILL.md`, `modulos/`, `scripts/` com só os scripts de navegador do `monitor/`, e o
  `_BATCH_MODELO` sem fotos; nunca `perfil.json`, `CALIBRACAO.md` nem os arquivos do monitor do Fefo).
  Depois de mudar a skill: `python3 fluxo.py publicar "<o que mudou>"` manda os mesmos arquivos do zip para o GitHub (plugin com auto-update).
- Se a pasta não estiver conectada, mude a sessão para ela (`change_directory`) antes de qualquer coisa.

## Como trabalhar: sempre pelo status
A batch inteira é descrita por **`08_auto/plano.json`** (falas, cenas, personagens, frascos). Cada arquivo esperado
tem dependências; o script sabe o que falta e o que ficou desatualizado (como um "make").

```
cd "<raiz>/_FLUXO_VSL/scripts"
python3 fluxo.py status "<pasta da batch>"     # o que falta, por módulo, e o próximo passo
python3 fluxo.py fazer  "<pasta da batch>"     # roda SÓ as etapas locais pendentes, em ordem
```
1. Comece toda conversa com `perfil` e `status`. Mostre o resumo em uma linha por módulo.
2. Rode só o módulo que ele pedir, ou o próximo pendente se ele disser "segue".
3. Módulos **locais** (sem crédito) rodam direto via `fazer`. Módulos que **gastam crédito** mostram quantas
   gerações e o custo estimado e esperam um ok claro.
4. Depois de qualquer mudança (clipe novo, copy alterada, trilha nova), `status` → `fazer` refaz só o afetado.
5. **Banco de conteúdo antes de gerar** (regra do Fefo, 30/10/2026): toda batch nova passa pelo módulo `banco`. Cada cena
   sai como REUSE ou NEW em `08_auto/banco_reuso.tsv`, e só o NEW entra no pedido de crédito. O `status` não cobra esta etapa.
6. **Uma sessão por etapa grande** (economia de tokens, 05/11/2026): 1. plano e geração; 2. montagem e QC; 3. cada revisão.
   Cada sessão começa pelo `fluxo.py status` e pelo `08_auto/ESTADO.md` da batch, não pelo histórico da anterior. Ao fechar
   a etapa, reescrever o `ESTADO.md` (curto, até ~20 linhas: etapa feita, versão, prompts e vozes travados, o que falta) e
   sugerir ao Fefo abrir a próxima sessão. Todas continuam no grupo EMPIRE VISION da barra lateral.

## Módulos (leia o arquivo do módulo antes de rodá-lo)
Modelo e esforço por etapa (economia de tokens, 05/11/2026): ao entrar numa etapa cujo modelo difere do da sessão, avise em uma linha para trocar (`/model`, `/effort`) ou abrir sessão nova. Criativo = Opus; conferir e rodar script = Sonnet; mecânico (subir, renomear, Notion/Asana, Clock) = Haiku ou Sonnet baixo. **Troca automática por agente:** passo mecânico já aprovado vai para o agente `executor-mecanico` (Haiku), com o OK do Fefo escrito na tarefa; montagem e checagens por script vão para o `montador` (Sonnet); QC visual para o `revisor-de-video` (Sonnet). A sessão principal fica com as decisões e recebe só o resumo.

| Módulo | Quando | Crédito | Modelo · esforço | Arquivo |
|---|---|---|---|---|
| configurar | primeira vez de cada pessoa / sem `~/.vsl-batch-editor/raiz` / `perfil` diz "Sem perfil" | não | Sonnet · baixo | `modulos/00_configurar.md` |
| ambiente | primeira vez no Mac / script reclama de ffmpeg | não | Haiku/Sonnet · baixo | `modulos/00_ambiente.md` |
| roteiro | chegou PDF/texto novo; ou não existe `plano.json` | não | Opus · alto | `modulos/01_roteiro.md` |
| referencia | início de toda batch, ou ref novo em `01_refs/` (define `estilo`) | não | Opus · alto | `modulos/02_referencia.md` |
| banco | **toda batch nova**, depois de `roteiro` e `referencia` e antes de gerar qualquer coisa; b-roll novo em revisão | não | Sonnet · médio | `modulos/05a_banco.md` |
| busca_avatar | avatar fotográfico de UGC novo sem quadro real escolhido | não | Sonnet · médio | `modulos/03a_busca_avatar.md` |
| personagens | plano tem personagem sem imagem aprovada | sim (custo em `modulos/kie.md`) | Opus · alto | `modulos/03_personagens.md` |
| falas | `status` mostra falas faltando | sim (Kling; Seedance só em Drama ad) | Sonnet · médio | `modulos/04_falas.md` |
| broll | `status` mostra b-roll faltando | sim (Sunburst + Kling) | Sonnet · médio | `modulos/05_broll.md` |
| coleta | há gerações de batch antiga no Higgsfield a baixar (o `kie.py` já baixa as dele) | não | Haiku/Sonnet · baixo | `modulos/06_coleta.md` |
| cortes / legendas / ads / xml | `status` mostra pendente | não | Sonnet · baixo | `modulos/07_montagem.md` |
| motions | pedido explícito (punch-in, CTA, legenda animada) | não | Sonnet · médio | `modulos/08_motions.md` |
| review room | ADs conferidos, para o Fefo revisar; "apply notes"; batch aprovada na sala | não | Sonnet · baixo | `modulos/11_review_room.md` |
| entrega | fim da batch/revisão: Frame.io (raiz → V<k>), links f.io por marca, link do Drive, "Ready for view", comentário no card do Notion + status CS NEEDS TO REVIEW, Clock Out | não | Haiku/Sonnet · baixo | `modulos/09_entrega.md` |
| revisao | link/comentários do Frame.io para ajustar (vale para os 6 ADs e as 2 marcas, não só o ponto); card "só QA" (vídeo pronto de outro editor, sem editar) | depende | Opus · alto para decidir; Sonnet para aplicar | `modulos/10_revisao.md` |

Geração: **sempre pelo Kie** (`scripts/kie.py`; `kie.py saldo` antes de gastar crédito). Comandos, modelos, limites e custos: `modulos/kie.md`.
O Higgsfield saiu das batches em 02/11/2026 e só entra com pedido do Fefo (`modulos/higgsfield.md`).
**Vídeo só com Kling. Seedance só em Drama ad** (ordem do cliente, 30/10/2026: é caro demais; vale para falas, b-roll
e revisão, em qualquer outro formato). Drama ad é o que o card ou o briefing chama assim; na dúvida, Kling e pergunte ao
Fefo. Kling falhou ou não faz a ação: pare e avise o Fefo, o Seedance não é mais reserva automática. MiniMax saiu em
16/10/2026. Falas: `modulos/04_falas.md`. B-roll: `modulos/05_broll.md`.
**Todo prompt de vídeo e de imagem segue a estrutura de 14 blocos** do Fefo (Scene Context → Positive Locks):
`modulos/prompts.md`.
**Hooks** (tipo de cada HOOK do canvas, 1º quadro, header, ponte para a hold, conferência): `modulos/hooks.md`, tirado
dos ads que mais rodaram no board "Great hooks" do Hookd. O ref da batch continua mandando no estilo.
Barra de linha do tempo, legenda estilo Snapchat e tela dividida já saem do `montar` (`estilo.barra_tempo`,
`estilo.tag_nativa`, cena `"formato": "split"`; campos em `modulos/02_referencia.md`).

## Regras fixas
Origem e data de cada regra: `historico_regras.md` (só abrir se precisar do motivo).
- **ED descontinuado:** nicho de ED acabou (Cocoa ED incluso), nas duas marcas: nada de edição, revisão, review nem entrega. Card de ED na fila ou em Revisions: não pegar, avisar o Fefo.
- **AD do Daniel sempre com música:** sem música no banco ou no card, gerar no Kie da Empire Vision (`scripts/kie.py suno` / `suno-ref`; nunca o Kie da Trendscale), com ok de crédito.
- **VisioVance só em eye vitamin:** batch de outro nicho (pele, neuropatia, rim…) sai só Neurobella.
- **Criador real é intocável:** UGC com bruto de criador contratado usa o vídeo e a voz originais dele. Nada de voz de IA (troca, TTS, clone) nem avatar parecido com ele. Batch com versão de IA do criador: reeditar com o original. Bruto difícil: avisar a Louise antes. Avatar novo a partir de quadro real continua, sempre pessoa diferente (`modulos/03_personagens.md`).
- **Gerações em paralelo:** depois do ok de crédito, montar `08_auto/pedidos_<etapa>.json` e rodar `kie.py lote` em segundo plano (um comando, um resumo; `modulos/kie.md`, seção Lote), em vez de um `kie.py` por geração conferido um por um. Enquanto roda, adiantar trabalho local; no fim, ler só o resumo.
- **Sempre 720p** na geração e no AD final (`modulos/07_montagem.md`).
- **Crédito só com ok:** antes de cada lote, quantas gerações, modelo, duração e custo. Aprovar imagens não autoriza vídeos.
- **Versões dos exports:** atual em `09_export/<p>/`, anteriores em `09_export/_old/V<k>/<p>/`, nunca pasta irmã. Antes de re-renderizar: `mkdir -p 09_export/_old/V<k> && cp -Rp 09_export/neurobella 09_export/visiovance 09_export/_old/V<k>/`. Mudar pasta de lugar no Drive = `mv` da pasta inteira (mantém ID e links).
- **Nunca sobrescrever** arquivo do Fefo. Corte à mão em `08_auto/cortes/<clipe>.manual.json` sempre vence o automático.
- **Caiu a conexão numa geração:** `kie.py espera <taskId> <saída>`. Nunca reenviar (cobra de novo).
- Sem acentos/espaços em nomes novos (menos os ADs finais). IDs de geração em `08_auto/falas_ids.tsv` e `08_auto/broll_ids.tsv`.
- **Qualidade:** personagem fotográfico com o bloco de pele realista (`modulos/03_personagens.md`); texto inventado pela IA = gerar de novo; clipe do Kling/Seedance entra depois do trecho parado do início (`inicio` ≥ 0,5 s, `scripts/inicio_movimento.py`); fala ~3,3 palavras/s; emendas no silêncio (e antes do estalo do fim do Seedance).
- **Checagens em todo AD antes de mandar ao Fefo** (`modulos/07_montagem.md`): `freezedetect=n=0.008:d=0.4`, `scripts/lascas.py`, quadros × duração do áudio, Whisper nos últimos 5 s, `scripts/ritmo.py` (nada parado acima de 3 s) e `scripts/imagem_fala.py`. Na revisão, rodar também na versão antiga.
- Várias sessões renderizando no Drive = timeout do ffmpeg: montar numa cópia no scratchpad e copiar o MP4. Intermediários nunca na batch: `$TMPDIR` ou scratchpad, apagados no fim.
- **Não remendar palavra colando voz:** refazer a fala inteira.
- **Aprendizado novo:** `python3 scripts/anotar.py "<título>" "- item"` (diário do mês em `CALIBRACAO/`). **Nunca abrir o diário para editar nem ler um mês inteiro**; consulta só com `grep -rn -i "<tema>" CALIBRACAO/`. Regra que vale para toda batch sobe para o módulo certo, sem data nem caso (isso vai para o diário).
- **Economia de contexto:** saída de terminal curta (`ffmpeg -v error`, `| tail -20`), nunca colar JSON inteiro de geração; conferência visual por prancha (`imagem_fala.py`), não quadro a quadro; editar script grande com `grep -n` + leitura do trecho, não do arquivo inteiro. O `fluxo.py` está dividido por assunto em `scripts/fluxo_partes/` (skill, plano, status, acoes, legenda, broll, montar, xml): mexer só na parte do assunto; todas rodam juntas como um arquivo só.
- **Fim de toda batch:** publicar a Review Room (`modulos/11_review_room.md`) e **esperar o OK no chat**. Só então, no `entrega.horario` do perfil (Fefo: 18h; OK antes disso = agendar tarefa única), subir no Frame.io, mandar o "Ready for view" como texto normal sem bloco de código, comentar no card do Notion, status **CS NEEDS TO REVIEW** e "Done - CS needs to Review" no `clock.dia_json`. O OK precisa citar esses passos. Tarefa agendada que pega o limite de uso não tenta de novo: depois do horário, conferir se saiu. A sessão não posta no Slack; Clock In sai pelo "pega" (`scripts/monitor/PEGA.md`) e Clock Out às 19h (tarefa `clock-out-slack`): sessão aberta pelo "pega" não repete. Perfil com `clock.automatico` vazio = mostrar o texto do Clock Out para colar. Detalhes em `modulos/09_entrega.md`.

## Nomes que o script espera (definidos pelo plano.json)
- Falas: `03_avatar/hold/F01.mp4` … (com marca: `F06_neurobella.mp4` / `F06_visiovance.mp4`); hooks `03_avatar/hooks/H1.mp4`.
- B-roll: `04_broll_hold/geral/S05_<nome>.mp4`; produto em `04_broll_hold/<produto>/S03_<nome>.mp4` (mesmo nome nas duas); hooks `05_broll_hooks/hook1/H1-01_<nome>.mp4`.
- Saídas: `08_auto/cortes/`, `08_auto/preview_hold_<p>.mp4`, `08_auto/legendas/`, `09_export/<p>/<título do card> - <Marca> - AD<k>.mp4` (versões anteriores em `09_export/_old/V<k>/<p>/`), `08_auto/BATCH<n>_premiere.xml`.
- **Nome dos ADs = título exato do card no Notion + marca + AD** (regra do Fefo, 23/10/2026):
  `BATCH#3215 - Thinning Shield - Macular Degeneration - L2 - Problem Aware - Daniel - Neurobella - AD1.mp4` (marca
  `Neurobella` / `VisioVance`). O título vem de `batch.json` → `card` (copie do Notion, igual ao "Título:" da fila);
  sem `card`, o script monta `BATCH#<n> - <titulo>`. Confira com o card antes de entregar. Só `/ : * ? " < > | \` viram
  "-". Export que ainda está com o nome antigo (`BATCH<n>_AD<k>_<p>.mp4`) → `python3 fluxo.py renomear "<batch>"`
  (sem renderizar); o `montar` já apaga o do nome antigo quando renderiza o novo.

## Estilo do ad: sempre o da pasta `01_refs/` da batch atual
- O estilo **não** vem de batch anterior nem desta skill. Cada batch segue o(s) ad(s) de referência em `01_refs/`
  (e o canvas/brief em `00_roteiro/`), mesmo que seja diferente do que foi feito da última vez.
- O módulo `referencia` analisa o ref e grava o resultado em `plano.json` → `estilo` (formato do avatar, onde e como
  entra o b-roll, legenda, cor, elementos, CTA, ritmo). Personagens, cenário e prompts também partem do ref.
- Sem `estilo` no plano, o `status` aponta o módulo `referencia` como pendente e o `montar` não roda.
- Se `01_refs/` estiver vazio, pergunte ao Fefo qual ad seguir antes de planejar cenas ou gerar qualquer coisa.
  Card sem ad de referência (Milanote sem ref, BATCH#3214 e #3215): proponha um estilo UGC (personagem, cenário e
  enquadramento, ex.: médica na mesa do consultório + selfie andando) e espere o OK antes de gerar.
- O que for igual em toda batch vem do `batch.json` (loudness, corte de silêncio). Na dúvida entre ref e `batch.json`, vale o ref.
