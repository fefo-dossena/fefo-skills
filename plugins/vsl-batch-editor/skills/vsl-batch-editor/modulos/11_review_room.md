# Módulo: sala de revisão (revisão do Fefo, antes do Frame.io; não gasta crédito)
**Desde 22/11/2026 a sala é a do painel local** (`@CLIENTES/_FLUXO/painel`, http://127.0.0.1:8765). A página privada no
claude.ai saiu de vez (Fefo: "Sai de vez"). Não rode `scripts/sala.py` nem `scripts/reviewroom.py` e não publique
`Artifact`: esses arquivos ficam no pacote só como histórico. O cliente continua no Frame.io; os comentários de lá seguem
`10_revisao.md`.

A regra completa mora em `@CLIENTES/_FLUXO/REGRAS_DA_SESSAO.md`, seção "Painel local" (lista das etapas, números e
comandos). Aqui fica só o que a batch precisa saber. Não copie os números para outro lugar.

O painel mostra cada batch por etapa (referência, plano, storyboard, rascunho no Blender, avatares, vozes, takes,
montagem, QA, sala, entrega). Ele lê as pastas numeradas da batch. O Fefo aprova cada etapa por um botão e escreve nota
no quadro exato de qualquer imagem ou vídeo.

## 1. Mandar para a sala (V1 ou versão nova)
1. As checagens de `07_montagem.md` vêm antes, e depois delas o agente `revisor-de-video` (QA; seção "Revisor", abaixo).
   O `revisor.py pedido` roda `fluxo.py checar <batch>` e recusa a versão com falha.
2. Deixe a prévia em `09_export` (ou em `09_export/_previas`). Antes de mexer numa versão, guarde a anterior em
   `09_export/_old/V<k>/`. O painel empilha as versões com a mais nova em cima.
3. Marque a etapa da sala no relógio: `relogio.py passo "<batch>" "sala V<k>" --min N --etapa <número da Sala de revisão>`.
4. Chame o Fefo: `relogio.py espera "<batch>" "<o que olhar, numa linha>" --tipo previa`. O painel toca o aviso e mostra a
   batch em "Esperam você". Diga numa linha, na sessão, o que olhar em cada marca.
5. Etapa anterior (referência, storyboard, Blender, avatares, vozes, takes): não precisa mandar nada. O asset na pasta
   numerada dele já aparece no painel.

## 2. Aplicar as notas
1. As notas chegam pela CENTRAL, que repassa para a sessão da batch: `NOTA <id> · volta para etapa K · <arquivo> em
   <tempo> (quadro N) · <texto>`. Sessão nova ou retomada: `notas_painel.py abertas "<batch>"` antes do plano.
2. Retome na etapa K (a de menor número, se houver várias) e refaça só o que a nota pede. Extraia o quadro
   (`ffmpeg -ss <t> -i <arquivo> -frames:v 1`) e veja antes de decidir. A regra do Fefo também vale aqui: procure o mesmo
   defeito nos outros ADs e na outra marca.
3. Corrigiu, rode as checagens de `07_montagem.md` e mande a versão nova para a sala (seção 1).
4. Nota aplicada: `notas_painel.py feita "<batch>" <id>`. Pergunta ou pedido que não dá para fazer: responda na sessão e
   deixe a nota aberta. Quem fecha a dúvida é o Fefo.

## 3. Aprovação
1. `APROVADA etapa <Sala de revisão>` vale como o "aprovado" da sala: libera o export final.
2. **Aprovar na sala não libera a entrega.** Faça a pergunta do `09_entrega.md` e espere o OK no chat.
3. O painel aprova a etapa inteira. Com montagem por segmentos, trave os segmentos pelo comando de sempre
   (`fluxo.py segmentos <batch> aprovar`). O Fefo quer aprovar só uma parte: ele escreve na nota qual.
4. O que vai ao Frame.io são os exports de `09_export`.

## Limites
O painel toca o arquivo da própria pasta da batch, em tamanho real: não há limite de MB nem cópia de qualidade menor. Ele
só existe no computador onde o `painel.py` está rodando e com o Drive montado. Ainda não tem desenho na imagem nem
versões lado a lado.

## Revisor: contexto e teto de rodadas (Fefo, 09/11/2026)
Rodadas extras por leitura errada custaram horas (4083: corte "no meio" que era do próprio hook; 3842 e 3830: reprovou de
novo o que já vinha da V1 e já tinha sido aceito; M1WK1B2: 5 rodadas pela voz da música).
- **Mande ao revisor junto do vídeo:** `08_auto/ref_medidas.md` (o ref medido), `revisor/aceitos.md` (o que o Fefo já
  dispensou ou aceitou nesta batch, com a data) e a lista do que mudou desde a última versão.
- Item que está em `aceitos.md` não reprova de novo sozinho: o revisor só aponta se piorou.
- **Teto de 2 rodadas por versão.** Reprovou na 2ª: não rode a 3ª. Leve ao Fefo o resumo do parecer, o que você acha
  (inclusive se o revisor leu errado) e a recomendação, e espere a escolha.
- Cada dispensa do Fefo entra em `revisor/aceitos.md` e em `revisor/dispensa_V<k>.txt`.
