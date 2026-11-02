# Módulo: coleta (baixar e identificar o que foi gerado)
- **Pelo Kie** (padrão): o `kie.py` já baixa no nome pedido; não precisa identificar por quadro. O resto deste módulo
  só vale para batch antiga, gerada pelo site do Higgsfield.
- Liste os vídeos novos no histórico (thumbnails `hf_<data>_<hora>_<uuid>_thumbnail`); baixe de
  `https://d8j0ntlcm91z4.cloudfront.net/user_<conta>/hf_<id>.mp4` (imagens: `.png`).
- **Identifique pelo 1º quadro**: baixe os quadros iniciais (PNG) numa pasta com o nome da cena (`S05.png`, `S03N.png`…) e rode
  `python3 fluxo.py identificar <videos...> --quadros <pasta>` → cena, distância, OK/CONFERIR. Sem quadro (só texto):
  confira a prancha visualmente. Clipes de fala: pelo prompt (modo Grid; o modo List pode travar a aba).
- Salve com o nome do plano, nunca sobrescreva, registre IDs (`falas_ids.tsv` / `broll_ids.tsv`).
- Descarte (não salve) o que saiu errado e diga ao Fefo.
