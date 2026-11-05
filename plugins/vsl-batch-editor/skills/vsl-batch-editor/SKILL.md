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

## Módulos (leia o arquivo do módulo antes de rodá-lo)
| Módulo | Quando | Crédito | Arquivo |
|---|---|---|---|
| configurar | primeira vez de cada pessoa / sem `~/.vsl-batch-editor/raiz` / `perfil` diz "Sem perfil" | não | `modulos/00_configurar.md` |
| ambiente | primeira vez no Mac / script reclama de ffmpeg | não | `modulos/00_ambiente.md` |
| roteiro | chegou PDF/texto novo; ou não existe `plano.json` | não | `modulos/01_roteiro.md` |
| referencia | início de toda batch, ou ref novo em `01_refs/` (define `estilo`) | não | `modulos/02_referencia.md` |
| banco | **toda batch nova**, depois de `roteiro` e `referencia` e antes de gerar qualquer coisa; b-roll novo em revisão | não | `modulos/05a_banco.md` |
| busca_avatar | avatar fotográfico de UGC novo sem quadro real escolhido | não | `modulos/03a_busca_avatar.md` |
| personagens | plano tem personagem sem imagem aprovada | sim (custo em `modulos/kie.md`) | `modulos/03_personagens.md` |
| falas | `status` mostra falas faltando | sim (Kling; Seedance só em Drama ad) | `modulos/04_falas.md` |
| broll | `status` mostra b-roll faltando | sim (Sunburst + Kling) | `modulos/05_broll.md` |
| coleta | há gerações de batch antiga no Higgsfield a baixar (o `kie.py` já baixa as dele) | não | `modulos/06_coleta.md` |
| cortes / legendas / ads / xml | `status` mostra pendente | não | `modulos/07_montagem.md` |
| motions | pedido explícito (punch-in, CTA, legenda animada) | não | `modulos/08_motions.md` |
| review room | ADs conferidos, para o Fefo revisar; "apply notes"; batch aprovada na sala | não | `modulos/11_review_room.md` |
| entrega | fim da batch/revisão: Frame.io (raiz → V<k>), links f.io por marca, link do Drive, "Ready for view", comentário no card do Notion + status CS NEEDS TO REVIEW, Clock Out | não | `modulos/09_entrega.md` |
| revisao | link/comentários do Frame.io para ajustar (vale para os 6 ADs e as 2 marcas, não só o ponto); card "só QA" (vídeo pronto de outro editor, sem editar) | depende | `modulos/10_revisao.md` |

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
- **ED descontinuado (call com a Empire Vision, 05/11/2026; suspenso desde 04/11 pela Louise):** o nicho de ED acabou, Cocoa ED incluso, na Neurobella e na VisioVance: nada de edição, revisão, review nem entrega. Card de ED na fila ou em Revisions: não pegar, avisar o Fefo.
- **AD do Daniel sempre com música (Fefo, 05/11/2026):** todo AD de card do Daniel sai com trilha musical, nunca só voz. Sem música no banco ou no card, gerar no Kie da Empire Vision (`scripts/kie.py suno` / `suno-ref`, comandos no cabeçalho do script; nunca o Kie da Trendscale). Crédito segue pedindo o ok do Fefo.
- **VisioVance só em eye vitamin (call, 05/11/2026):** a VisioVance fica só com o nicho de olho. Batch de outro nicho (pele, neuropatia, rim…) sai só Neurobella, mesmo sem menção no card; versão VisioVance só em batch de olho.
- **Criador real é intocável (Louise, 04/11/2026):** em UGC com bruto de criador contratado, entram o vídeo e a voz originais dele. Nada de voz de IA no lugar da dele (troca de voz, TTS, clone) nem avatar de IA parecido com ele; ritmo, legenda, b-roll, música e hooks seguem iguais. Batch em andamento com versão de IA do criador: reeditar com o original. Bruto difícil (áudio ruim): avisar a Louise antes. Motivo: autenticidade e consentimento (o contrato com os criadores não cobre réplica de IA). Avatar novo a partir de quadro real (`modulos/03_personagens.md`) continua, sempre como pessoa diferente.
- **Gerações em paralelo** (Fefo, 04/11/2026): depois do ok de crédito, um `kie.py` em segundo plano por geração (~10–15 s entre disparos), nunca uma fila única. Cada um espera e baixa o seu.
- **Sempre 720p.** Vídeo gerado e AD final em 720p (720x1280), detalhe em `modulos/07_montagem.md`.
- **Crédito só com ok.** Antes de cada lote: quantas gerações, modelo, duração, custo estimado. Aprovar imagens não autoriza vídeos.
- **Versões dos exports (toda batch):** todas ficam dentro da pasta de exports. A atual em `09_export/<p>/`; toda versão
  anterior em `09_export/_old/V<k>/<p>/`. Nunca pasta irmã (`09_export_V1`, `_export_v1`, `View_v2`…). Antes de
  re-renderizar uma revisão: `mkdir -p 09_export/_old/V<k> && cp -Rp 09_export/neurobella 09_export/visiovance 09_export/_old/V<k>/`.
  Para mudar pasta de lugar no Drive, mova a pasta inteira (`mv`), sem copiar e apagar: assim o ID e os links enviados continuam valendo.
- **Nunca sobrescrever** arquivo do Fefo; arquivo existente fica. Corte ajustado à mão vive em `08_auto/cortes/<clipe>.manual.json` e sempre vence o automático.
- **Caiu a conexão no meio de uma geração**: `kie.py espera <taskId> <saída>`. Nunca reenvie: cobra de novo.
- Sem acentos/espaços em nomes novos (menos os ADs finais, que levam o título do card; ver abaixo). Registrar IDs de geração em `08_auto/falas_ids.tsv` e `08_auto/broll_ids.tsv`.
- **Qualidade antes de entregar** (regras do Fefo): personagem fotográfico com o bloco de pele realista
  (`modulos/03_personagens.md`); texto inventado pela IA em quadro/vídeo = descartar e gerar de novo; todo clipe do
  Kling/Seedance entra depois do trecho parado do início (`inicio` ≥ 0,5 s, `scripts/inicio_movimento.py`); ritmo de
  fala ~3,3 palavras/s; emendas de corte no silêncio (e antes do estalo do fim dos clipes do Seedance).
- **Checagens em todo AD antes de mandar ao Fefo** (`modulos/07_montagem.md`): `freezedetect=n=0.008:d=0.4`,
  `scripts/lascas.py`, quadros do vídeo × duração do áudio, Whisper nos últimos 5 s, ritmo (`scripts/ritmo.py`: nada parado
  acima de 3 s) e imagem × fala
  (`scripts/imagem_fala.py`). Na revisão, rode-as também na versão antiga: acham defeito que ninguém comentou.
- Várias sessões renderizando no Drive ao mesmo tempo = timeout do ffmpeg: monte numa cópia no scratchpad e copie o MP4.
- Intermediários (trechos, frames, testes) nunca na batch: `$TMPDIR` ou scratchpad, apagados no fim (`modulos/07_montagem.md`).
- **Não remendar palavra colando voz** (marca, número): refazer a fala inteira — o remendo soa "estranho" para o Fefo.
- Aprendizado novo → `_FLUXO_VSL/CALIBRACAO.md` (diário). Regra que vale para toda batch sobe para o módulo certo.
- **Fim de toda batch:** publicar a Review Room para o Fefo (`modulos/11_review_room.md`; SendUserFile só se ele pedir) e
  **esperar o OK no chat**; só então subir no Frame.io e mandar
  a mensagem "Ready for view" (Visiovance/Neurobella f.io + link do Google Drive) como **texto normal, sem bloco de
  código** (ele cola no Notion), no formato de `modulos/09_entrega.md`. Antes de subir, confira se o Frame.io já está atualizado.
  Depois (desde 15/10/2026, com o mesmo OK, que deve citar esses passos): comentar o "Ready for view" no card da batch no
  Notion, mudar o status para **CS NEEDS TO REVIEW**, marcar a batch como "Done - CS needs to Review" no
  `clock.dia_json` do perfil (Fefo: `scripts/monitor/dia.json`). **Subir e mexer no Notion só no `entrega.horario`** do
  perfil (Fefo: 18h, pedido em todas as revisões de 16/10): com o OK antes disso, agende uma tarefa única para esse
  horário (`modulos/09_entrega.md`). Tarefa que pega o limite de uso falha e não tenta de novo (23/10): depois do
  horário, confira se a entrega saiu.
  A sessão não posta no Slack. No perfil do Fefo, o 🟢 CLOCK IN sai com o "pega" da sessão principal
  (`scripts/monitor/PEGA.md`, desde 22/10/2026) e o **🔴 CLOCK OUT** sai às 19h (tarefa `clock-out-slack`), as duas no
  thread do dia em #video-editor-report e com as mesmas batches. Sessão de batch aberta pelo "pega" já tem o Started e o
  Clock In feitos: não repita;
  perfil com `clock.automatico` vazio = mostrar o texto do Clock Out para a pessoa colar (detalhes em `modulos/09_entrega.md`).

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
