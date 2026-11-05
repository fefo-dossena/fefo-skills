# Revisão: card "só QA"

Tirado de `10_revisao.md` em 05/11/2026.

## Card "só QA" (vídeo pronto de outro editor)
Cards de versão VisioVance que o Daniel já editou no CapCut (3194–3197, 22–23/10/2026): o briefing é uma pasta do Drive
com os dois vídeos prontos (`BATCH<n>_h1.mp4` Neurobella e `BATCH<n>_h1_VISIOVANCE.mp4`) e um "LAUNCH PACKAGE" no card.
Pergunte ao Fefo o que a tarefa pede (recriar no padrão da casa, ajustar ou só revisar). **Só revisar** = sem editar,
sem export, sem Frame.io, sem crédito:
1. Com o OK, baixe os vídeos para `01_refs/drive_daniel/`; copy em `00_roteiro/roteiro.txt`, transcrição com tempos em
   `00_roteiro/transcricao_visiovance.txt`.
2. `00_roteiro/diagnostico.md`, com as seções da 3194: **Marca** (sobra de Neurobella? compare o áudio das duas versões:
   onde muda, emenda no silêncio, legenda com a marca, frasco e cápsula certos em todo trecho de produto), **SOP do
   Daniel** (tabela: vídeo × roteiro, VO e ritmo, dead space, hook com ação imediata, detalhes de IA, 4:5, lascas),
   **Outros pontos**, **Limite para mexer** (só o export com legenda queimada = polir pede o projeto do CapCut) e
   **Decisão**. Marca pelo Whisper medium e large-v3 (o medium escreve "Viziovance"/"flavonols" e pula palavras curtas).
3. Olhe também: palavrão na VO ou na legenda (3196: "scammed as fuck"), suplemento tratando doença ou trocando remédio
   de receita (3197: "instead of Farxiga"), card sem Landing Page no LAUNCH PACKAGE ("NONE YET… Hold this card") e
   promessa do texto do anúncio que o vídeo não faz. Imagem × fala: `python3 scripts/imagem_fala.py <video.mp4>` (um
   quadro a cada 2 s; sem `.srt`, case com a transcrição) e os critérios de `07_montagem.md`; revise também a ortografia
   da legenda queimada, porque aqui ela não vem do nosso roteiro.
4. Comentário de QA em inglês em `00_roteiro/comentario_qa.md` (exemplo: `BATCH#3196`): o que está limpo na marca,
   pontos numerados para conferir antes do lançamento, "No edits made" e o que faltaria para polir, e o funil.
5. Com o OK do Fefo: comentário no card + status CS NEEDS TO REVIEW (passos do Notion de `09_entrega.md`, sem Ready for
   view) e Done no `dia.json`, no `entrega.horario` ou na hora, se ele pedir (a 3197 fechou de manhã).

