# Módulo: revisão (comentários do Frame.io → nova versão)
Quando o Fefo manda um link do Frame.io ou pede "faz os comentários".
**Seedance só em Drama ad** (30/10/2026, `04_falas.md`): as correções com Seedance neste módulo são histórico; fora de
Drama ad, refaça no Kling.

1. **Ler**: `python3 frameio.py comentarios "<frameio.pasta do perfil>/BATCH_<n>"` (Fefo: `Hike Balance Brand/FEFO`; ou abrir o link no navegador). No PC: `py ~/.vsl-batch-editor/frameio_ev.py` (login do time; `09_entrega.md`).
   O número entre [] é o QUADRO na fps do vídeo (exports a 30 fps → segundos = n/30; conferido na BATCH#2820).
   **Batch exportada do Premiere pode estar a 24 fps** (2086: q110 = 4,6 s, não 3,7): confira a fps do MP4 com
   `ffmpeg -i` antes de converter. Card sem pedido escrito no Notion = os pedidos estão nos comentários do Frame.io.
   **Antes de concluir que o card não tem pedido, leia a discussão inteira do card** (`javascript_tool` com o innerText de
   `.notion-page-view-discussion` ou dos `[data-block-id]`): o comentário do estrategista pode vir logo abaixo dos
   "Ready for view" (selo "Novo") e o `get_page_text` corta a lista (BATCH#2481 V2, 23/10: pedido de legenda do Zane).
1b. **Lista de notas** (checklist da Louise, 13/11/2026; item 6, com trava): gere a lista dos comentários do Frame.io
   com `py ~/.vsl-batch-editor/frameio_ev.py comentarios "<pasta>/BATCH_<n>" --revisao "<batch>"` (só os vídeos da raiz;
   grava `00_roteiro/revisao_V<k>.md`, k = a versão nova). Uma linha por nota:
   `- [ ] AD1 0:07.07 · "deadspace" · vou mudar: ? · mudei: ? · prova:`. Acrescente à mão as notas do card do Notion
   (mesmo formato, `card` no lugar do AD). Nota vaga ("still", "deadspace", "fix the text"): ache a causa no passo 2 e
   escreva a leitura em "vou mudar". Nota marcada **JÁ APARECEU** (está em `preferencias_daniel.md`): além de corrigir,
   vira checagem ou regra fixa nesta revisão. Antes de mandar ao Fefo, confira cada nota **na versão nova exportada**,
   troque `[ ]` por `[x]`, diga o que mudou em "mudei:" e ponha em "prova:" o quadro da versão nova (caminho relativo à
   batch, ex. `08_auto/prova/AD1_0m07.jpg`, tirado por subagente). Linha sem `[x]` ou sem prova deixa o item 6
   vermelho: a sala não aprova e o `frameio.py` não sobe. Na entrega, `notas_revisao.py respostas "<batch>" --versao <k>`
   escreve a resposta de cada nota (em inglês); postar no Frame.io só com ok do Fefo. Depois passe o checklist inteiro
   (`fluxo.py checar`): revisão também passa por ele, sem dispensa.
2. **Comentário parecido já apareceu?** `grep -n -i "<palavra do comentário>" modulos/10b_casos_revisao.md` e leia só a linha achada (tabela de causas e correções de revisões antigas; não abrir o arquivo inteiro).
   **Card "só QA"** (vídeo pronto de outro editor): `modulos/10c_so_qa.md`. **Trocar trecho direto no MP4** (batch do Premiere, sem fontes): seção no fim de `10b_casos_revisao.md`.
2b. **Localizar**: extrair quadros no ponto e em volta (prancha) e a fala (faster-whisper) para entender o que o revisor viu.
   Comentário de áudio ("weird sound", "VO wrong", "deadspace") quase sempre vem da hold: vale para os 6 ADs.
   Além do pedido, rode as checagens de `07_montagem.md` na versão antiga (freezedetect, lascas, imagem × áudio, Whisper
   no fim): em 16/10 elas acharam defeitos sem comentário em 4 das 7 revisões (fim cortado, piscada, congelados, quadro solto).
3. **Achar o padrão, não só o ponto** (regra do Fefo): um comentário vale para todos os ADs que usam a mesma hold e para
   todo trecho com o mesmo defeito. Varra os 6 ADs inteiros (prancha 1 fps) e confira:
   - avatar com mão/relógio perto da câmera (IA deforma) → punch-in ~1,6× no rosto recompondo a pílula da legenda;
   - texto gerado pela IA dentro do b-roll (selos, rótulos) → errado = tirar (zoom leve no b-roll-fonte sem legenda),
     não trocar por outro texto;
   - hooks: AD1/AD2/AD3 diferentes entre si; b-roll e trecho do avatar não se repetem dentro do AD.
   - Selo FDA no frasco: conferir a embalagem em `01_refs/`/`Refs` — se a embalagem real tem, fica.
4. **Batch montada à mão no Premiere** (sem `plano.json`): `gunzip -c X.prproj > p.xml && python3 prproj_parse.py p.xml
   out.json` dá todas as sequências/clipes; AD = hook + hold aninhada. Corrigir direto no MP4 exportado (exemplo:
   `BATCH_1971/patch_frameio_1971.py`) e salvar a versão nova na raiz da pasta de exports, com a anterior movida para `_old/V<k>/` dentro dela — nunca sobrescrever o export do Fefo.
   Copie o MP4 para o scratchpad antes de processar (leitura do Google Drive às vezes falha no meio do decode).
5. **Guardar a versão anterior** (ANTES de re-renderizar): `09_export/<p>/` → `09_export/_old/V<k>/<p>/` (k = versão que está
   no Frame.io hoje; `mkdir -p 09_export/_old/V<k> && cp -Rp 09_export/neurobella 09_export/visiovance 09_export/_old/V<k>/`).
   Nunca pasta irmã `09_export_V<k>`. Falas/b-rolls trocados em `_antigos/`.
6. **Refazer só o pedido**: se o `fluxo.py` mudou depois da versão anterior, remontar com ele muda o que ninguém pediu.
   Use o `segmentos()` da época e confira `broll_posicoes` iguais + SSIM só caindo no trecho corrigido (BATCH#2820 V3).
7. **Mandar ao Fefo e esperar o OK**, depois entregar: módulo `09_entrega` (raiz atual → `V<k>`, nova versão na raiz,
   links, mensagem "Ready for view").

## Se vierem métricas do ad (hook rate, hold rate, curva)
Do curso Ad Creators Lab (29/10/2026). Hook rate = plays de 3 s ÷ impressões; hold rate = plays até 50% ÷ impressões.
- **Hook baixo (< 30%) e hold boa**: o corpo funciona → 3 a 5 hooks novos sobre a mesma hold (`hooks.md`).
- **Hook bom e hold baixa**: achar na curva de retenção o segundo em que o público sai → versão cortada antes da queda e
  versão média sem o trecho (ou com a ordem trocada). Perguntar: o ritmo caiu? informação demais? produto cedo demais?
- Menos de ~20% ainda assistindo aos 5 s = abertura fraca (fala ou primeiro visual).

## Entrega da revisão
Com o OK, o Fefo pediu em todas as revisões de 16/10 para subir e mexer no Notion **só às 18h**. Ver `09_entrega.md`.
