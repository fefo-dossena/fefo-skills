# Ficha: Empire Vision (EV)

Contexto do cliente para a skill `vsl-batch-editor` (17/11/2026: a skill ficou genérica; o que é só da EV mora aqui).
Dados de máquina (pastas, loudness, checagens ligadas): `empire-vision.json` ao lado. Conector, Slack, Frame.io e
banners de BF: `@EMPIRE VISION/CLAUDE.md`. Origem e data de cada regra: `_FLUXO_VSL/historico_regras.md`.

## O que é
- Batches de anúncio (VSL/UGC) de **Neurobella** e **VisioVance**, pedidas por card no Notion (pega: `_FLUXO_VSL/scripts/monitor/PEGA.md`).
- Raiz: `@EMPIRE VISION/2026` (no PC, `G:/Meu Drive/@CLIENTES/@EMPIRE VISION/2026`). Batch nova = cópia de `_BATCH_MODELO/`.
- Aprova: o Fefo (ou o `aprovador` do perfil). Cliente revisa: Louise, Daniel, Umut.
- Sessões no grupo **EMPIRE VISION** da barra lateral.

## Perfil e começo
```
cat ~/.vsl-batch-editor/raiz                                   # a raiz desta máquina
cd "<raiz>/_FLUXO_VSL/scripts" && py fluxo.py perfil            # quem usa, contas, quem aprova
py fluxo.py status "<pasta da batch>"                           # o que falta, por módulo
```
- Sem raiz ou sem perfil: módulo `configurar`. Perfil sem `fonte_da_skill` (outra pessoa): antes,
  `py "<pasta da skill>/scripts/fluxo.py" instalar "<raiz>"`.
- Onde a skill diz "o Fefo" como quem aprova: o `aprovador` do perfil. Geração → `geracao`; Frame.io → `frameio.pasta`;
  Drive → `drive.conta`; Notion → `notion` (`usar: false` = não mexer); entrega → `entrega.horario`; Clock → `clock`.
  Item em `pendente`: o módulo que precisa dele para e diz o que falta.

## Motor: `08_auto/plano.json`
- A batch inteira está no `plano.json` (falas, cenas, personagens, frascos). O `status` sabe o que falta ou está velho;
  o `fazer` roda só as etapas locais pendentes, pelo `montador`. Depois de qualquer mudança: `status` → `fazer`.
- Passo 0: baixar e medir o ref (`modulos/02_referencia.md`) antes do banco e do plano.
- **Banco antes de gerar:** toda batch nova passa pelo módulo `banco`; cada cena REUSE ou NEW em `08_auto/banco_reuso.tsv`;
  só o NEW entra no pedido de crédito.
- Brief antes do ref: `brief_regras` e `brief_conflitos` no `plano.json` (o `lint_plano` trava sem eles). Notas que já
  voltaram do cliente: `_FLUXO_VSL/preferencias_daniel.md`, lido no plano de toda batch.

## Geração
- Kie da EV (`kie.py`; `kie.py saldo` antes). Higgsfield só com pedido do Fefo (`modulos/higgsfield.md`).
- **Vídeo só com Kling (e Gemini Omni). Seedance só em Drama ad** (ordem do cliente, 30/10/2026). Kling falhou: pare e
  avise; Seedance não é reserva automática. Na dúvida se é Drama ad: Kling e pergunte.
- Geração em `kie.py lote`, com `08_auto/pedidos_<etapa>.json`. Reserva de crédito em `scripts/monitor/reservas.json`;
  teto e gasto no `08_auto/ESTADO.md`.
- Clipe do Kling/Seedance entra depois do trecho parado do início (`inicio` ≥ 0,5 s, `scripts/inicio_movimento.py`);
  fala ~3,3 palavras/s; emendas no silêncio e antes do estalo do fim do Seedance.
- Hooks: `modulos/hooks.md` (tirado do board "Great hooks" do Hookd; o ref manda no estilo).

## Regras só da EV
- **ED descontinuado** nas duas marcas: card de ED não se pega; avisar o Fefo.
- **AD do Daniel sempre com música.** Sem trilha no banco ou no card: `kie.py suno` / `suno-ref` no Kie da EV, com ok de crédito.
- **VisioVance só em eye vitamin.** Outro nicho sai só Neurobella.
- **Criador real é intocável:** bruto de criador contratado usa vídeo e voz originais; nada de voz de IA nem avatar parecido.
  Bruto difícil: avisar a Louise antes.
- **Legenda:** y 0,63 em todo AD, nunca abaixo de 0,65; cena que cobre frasco, rótulo ou rosto sobe (~0,40 ou 0,20),
  nunca desce. Estilo e margem: `@CLIENTES/_FLUXO/LEIA-ME.md`, seção Legenda.
- **Black Friday e promo:** só batch BF ou promo sai também em 1,91:1 (1200×628) e 1:1 (1200×1200); batch comum só vertical.
  Banners de BF Late e BFCM: `@EMPIRE VISION/CLAUDE.md`. Em aberto o pixel do vídeo: perguntar antes de exportar BF.
- Loudness −20 LUFS (no `empire-vision.json`).

## Nomes
- Falas: `03_avatar/hold/F01.mp4` (com marca: `F06_neurobella.mp4`); hooks `03_avatar/hooks/H1.mp4`.
- B-roll: `04_broll_hold/geral/S05_<nome>.mp4`; produto `04_broll_hold/<produto>/S03_<nome>.mp4`; hooks `05_broll_hooks/hook1/H1-01_<nome>.mp4`.
- IDs de geração em `08_auto/falas_ids.tsv` e `08_auto/broll_ids.tsv`. Corte à mão em `08_auto/cortes/<clipe>.manual.json` vence o automático.
- **AD final = título exato do card + marca + AD:** `BATCH#3215 - Thinning Shield - Macular Degeneration - L2 - Problem Aware - Daniel - Neurobella - AD1.mp4`.
  Título do `batch.json` → `card`. Só `/ : * ? " < > | \` viram "-". Nome antigo: `fluxo.py renomear "<batch>"`.
- Exports: `09_export/<p>/`; anteriores em `09_export/_old/V<k>/<p>/`. Sem XML do Premiere.

## Entrega
- Sala de revisão (`modulos/11_review_room.md`), OK escrito no chat, então na hora: Frame.io (conta de time, `frameio_ev.py`),
  "Ready for view" em texto normal, comentário no card do Notion, status **CS NEEDS TO REVIEW**, "Done - CS needs to Review"
  no `clock.dia_json`. O OK cita esses passos. Clock Out só quando o Fefo pedir. Detalhe: `modulos/09_entrega.md`.
- Por último: registro no segundo cérebro (Aprendizados das batches, diário, nota).
- Aprendizado novo: `py scripts/anotar.py "<título>" "- item"` (diário em `CALIBRACAO/`; consulta só com `grep -rn -i`).
