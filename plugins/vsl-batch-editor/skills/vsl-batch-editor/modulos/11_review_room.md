# Módulo: Review Room (revisão do Fefo, antes do Frame.io; não gasta crédito)
Página privada no claude.ai por batch, do kit do Daniel: nota no quadro exato, desenho na imagem, comparação de versões e
aprovação por AD. Substitui o envio dos exports por SendUserFile (decisão do Fefo, 30/10/2026). O cliente continua no
Frame.io; os comentários de lá seguem `10_revisao.md`. Uma sala por batch, com o mesmo link em todas as versões.

Arquivos: `scripts/sala.py` (monta a sala da batch), `scripts/reviewroom.py` e `scripts/reviewroom/template.html` (kit).
Cópias, página e estado ficam em `~/.vsl-batch-editor/salas/<batch>/`, nunca na batch. As checagens de `07_montagem.md`
vêm antes da sala.

## 1. Publicar (V1 ou versão nova)
1. `python3 scripts/sala.py "<batch>" --nota "<o que mudou>"`. Com cortes 4:5: `--4x5`. Conserte cada linha com `!`.
   A batch com 6 ADs longos pode passar do limite: acima de ~240 MB, publique sem o 4:5 ou divida em duas salas.
2. Leia a skill `artifact-capabilities`. Publique com o `Artifact` pelo `publish_plan.json`, ao lado do `review.json`:
   `file_path` = `page`; `files` = `publishes[0]`; `capabilities: {"db": {}, "comments": {}}`, `icon: "video"` e uma descrição
   de uma linha. Mais de um bloco: publique cada um na `url` devolvida, sem repetir `capabilities`.
   Versão nova: mesma `url`.
3. Grave a URL em `review.json` → `url` e rode `python3 scripts/reviewroom.py commit <review.json>`.
4. Na V1, confira com `ArtifactData` `list` em `notes` nessa url: lista vazia sem erro = banco no ar.
5. Mande o link ao Fefo, com uma linha por marca dizendo o que olhar. A sessão que publicou já acompanha a sala.
   Em sessão nova: `ArtifactComments watch` com a url.

## 2. Aplicar as notas ("apply notes" ou botão ➤ Apply notes)
1. `ArtifactData list` em `notes` e `approvals`. Trabalhe só em `status: "open"`.
2. A nota traz `video` (marca), `hook` (AD), `version`, `ratio`, `t`/`t2`, `seg`/`seg_t`, `tag`, `text`, `all_hooks` e `strokes`
   (`c` cor, `p` pontos em frações de x e y). Extraia o quadro (`ffmpeg -ss <t> -i <export> -frames:v 1`), desenhe as linhas e
   veja antes de decidir. `all_hooks` = hold: vale para todos os ADs. A regra do Fefo também vale aqui: procure o mesmo
   defeito nos outros ADs e na outra marca.
3. Antes de mexer, guarde a versão em `09_export/_old/V<k>/`. Corrigiu, rode as checagens de `07_montagem.md`.
4. Volte ao passo 1 com a mesma url.
5. Responda em cada nota em um único `ArtifactData batch` de `update`, com `if_version` da leitura: `status: "fixed"`,
   `fixed_in`, e `replies` = as respostas que já existem + `{"by": "claude", "text": "<o que mudou>", "version": n, "at": "<ISO>"}`.
   **Nunca use `resolved`:** quem fecha a nota é o Fefo. Pergunta ou pedido que não dá para fazer: responda e deixe `open`.
6. Pelo botão: `ArtifactComments reply` no thread com uma linha e `resolve`.

## 3. Aprovação
1. Com a batch aprovada na sala: `ArtifactData list` em `notes` e `approvals` com `out_dir` = `<pasta da sala>/db/` e
   `python3 scripts/reviewroom.py record <review.json> <pasta da sala>/db` (`record.md` + `record.json`).
2. **Aprovar na sala não libera a entrega.** Faça a pergunta do `09_entrega.md` e espere o OK no chat.
3. O que vai ao Frame.io são os exports de `09_export`, nunca as cópias da sala.

## Limites
15 MB por arquivo (AD de ~3 min pode cair para 540 px), 256 MB por versão, e só as 2 últimas versões ficam tocáveis. A
qualidade da sala é menor que a do export: defeito fino se confere no MP4. A sala é privada até o Fefo compartilhar; nada
dela é entregue ao cliente.
