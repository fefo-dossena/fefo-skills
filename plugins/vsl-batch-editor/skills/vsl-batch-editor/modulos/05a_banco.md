# Módulo: banco de conteúdo (toda batch nova, antes de gerar; não gasta crédito)
Banco da Empire Vision: `https://neurobella-content-bank.empirevision.workers.dev`. Tem todo o b-roll do time (9.751 vídeos
em 30/10/2026, com QA e busca por campos). **Regra do Fefo (30/10/2026): nenhuma batch gera b-roll sem passar por aqui.**
Roda depois de `roteiro` e `referencia`, porque precisa das cenas e do `estilo`, e antes de `personagens`, `falas` e `broll`.
Vale também para b-roll novo numa revisão. Fala do avatar não vem do banco.

## Como acessar
1. **Chave** em `~/.vsl-batch-editor/banco_chave` (fora do Drive e do zip; nunca em `perfil.json`, nota ou módulo):
   `GET /agent/search?q=<palavras>&qa=pass&limit=20` com o header `X-Agent-Key`, nunca na URL. `GET /agent` mostra a ajuda.
   Filtros: `role= who= style= setting= segment= new=1`. Marca não tem filtro: confira o campo `brand` de cada resultado.
   Devolve `clip_url`, `thumb_url`, `description`, `prompt`, campos, `qa`, `higgsfield_job_id`. `clip_url` e `thumb_url` também
   pedem o header. Clipe com `qa` fail não aparece; `qa=flag` lista os que têm alerta.
2. **Sem chave:** navegador interno (`mcp__Claude_Browser__*`), onde o Fefo já entrou no site. A página carrega
   `/data.json`; leia com `javascript_tool`, pelo `fetch` da própria página. A senha é só do Fefo: pedir a ele que entre,
   nunca digitar.
   Campos: `i` id · `sg` segmento (`md_eye`, `cocoa_ed`, `neuropathy`, `kidney`, `unknown`) · `br` marca (`n`, `v`) · `ro` função
   do plano · `wh` quem · `sy` estilo · `se` cenário · `d`/`tg`/`p` descrição, tags, prompt · `du` duração · `w`/`h` · `u` URL · `j` job_id
   · `qa`/`qn` alerta · `st` status. Miniatura: `/t/<i>.jpg`. Sem `u`: abra o clipe no site (`openAsset(<i>)`).
3. **Banco inacessível:** avise o Fefo e não gere b-roll até ele entrar no site ou mandar seguir sem o banco.

## O que fazer
1. Busque **cada cena** do `plano.json` pelo que ela mostra, com filtro de segmento e marca, e classifique:
   **REUSE #id** (encaixe exato) ou **NEW**. "Quase serve" é NEW.
2. Encaixe exato precisa de tudo isto:
   - mostra o que a `copy` da cena diz (`imagem_fala.py` confere depois);
   - mesmo estilo do ref da batch (`01_refs/`); o clipe de outra batch não dita o estilo;
   - marca certa no rótulo, frasco inteiro e legível, sem texto inventado pela IA;
   - frasco integrado: mesma luz do avatar e da cena; com cara de colado, não reusar, mesmo com QA aprovado (cliente, 31/10/2026);
   - 9:16, lado menor ≥ 720 e duração suficiente depois do `inicio`;
   - pessoa não contradiz os personagens do plano (sem rosto reconhecível de outro personagem).
3. Fora do reuso: `trybe/…` (vídeo de criador, só com OK do Fefo), talking head e clipe com oferta/data vencida no quadro.
   `qa` com alerta ("Check before reuse") = só depois de ver o clipe inteiro.
4. **Veja o clipe antes de aprovar:** prancha com início, meio e fim, nunca só a miniatura. O QA do banco não substitui as
   regras do Fefo.
5. Cena `produto` que só tem clipe de uma marca: reuse nessa e faça a outra como NEW, de preferência trocando o frasco no
   quadro (`03_personagens.md`). Cena com clipe parecido, mas não exato, pode usar o `higgsfield_job_id` como quadro inicial.
6. Grave `08_auto/banco_reuso.tsv`: `cena  marca  decisao  id_banco  arquivo  motivo` (toda cena, REUSE e NEW).
7. Mostre ao Fefo, junto do custo do lote (`05_broll.md`): nº de REUSE, nº de NEW, créditos poupados (~12 a 14 por clipe
   reusado) e a prancha dos REUSE. **Só o NEW entra no pedido de crédito.**
8. Com o OK: baixe cada REUSE com o nome que o plano espera (`04_broll_hold/…`, `05_broll_hooks/…`), sem sobrescrever, e
   registre em `08_auto/broll_ids.tsv` com modelo `banco#<id>`. Daí em diante é b-roll normal: `inicio_movimento.py`, `inicio`
   no plano e todas as checagens de `07_montagem.md`.
9. O mesmo clipe não se repete dentro de um AD.
