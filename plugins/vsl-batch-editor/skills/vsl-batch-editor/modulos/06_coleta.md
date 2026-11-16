# Módulo: coleta (baixar e identificar o que foi gerado)

> **Logo depois de baixar cada clipe (PDF do Lucas, 16/11/2026; `@CLIENTES/_FLUXO/QUALIDADE_DO_BATCH.md`, seção 2):** todo clipe é conferido num subagente: quadros a cada 0,5 s em tamanho grande (olhar os tempos de contato), régua de lógica e física, fala contra o roteiro (Whisper medium para palavra curta ou rara), primeiro clipe de cada personagem olhado assim que baixa. Veredito por clipe com `prompt_qa.py veredito <clipe> ok|parcial --faixa A-B|reroll --motivo ...`. Regerar só pela lista fechada (identidade, roupa, texto, anatomia, fundo, ação ou batida faltando) e **no máximo 1 vez**; falhou de novo = mudar a abordagem. Uma linha de lição no `LICOES.md` por clipe conferido.

- **Pelo Kie** (padrão): o `kie.py` já baixa no nome pedido; não precisa identificar por quadro. O resto deste módulo
  só vale para batch antiga, gerada pelo site do Higgsfield.
- Liste os vídeos novos no histórico (thumbnails `hf_<data>_<hora>_<uuid>_thumbnail`); baixe de
  `https://d8j0ntlcm91z4.cloudfront.net/user_<conta>/hf_<id>.mp4` (imagens: `.png`).
- **Identifique pelo 1º quadro**: baixe os quadros iniciais (PNG) numa pasta com o nome da cena (`S05.png`, `S03N.png`…) e rode
  `python3 fluxo.py identificar <videos...> --quadros <pasta>` → cena, distância, OK/CONFERIR. Sem quadro (só texto):
  confira a prancha visualmente. Clipes de fala: pelo prompt (modo Grid; o modo List pode travar a aba).
- Salve com o nome do plano, nunca sobrescreva, registre IDs (`falas_ids.tsv` / `broll_ids.tsv`).
- Descarte (não salve) o que saiu errado e diga ao Fefo.
