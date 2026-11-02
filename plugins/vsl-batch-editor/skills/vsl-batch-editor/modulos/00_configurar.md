# Módulo: configurar (perguntas de início, 1x por pessoa/Mac)
Roda quando não existe `~/.vsl-batch-editor/raiz` ou quando `python3 fluxo.py perfil` diz "Sem perfil". Cada pessoa tem
a **própria pasta de batches** (a raiz), com o seu `_FLUXO_VSL/` (scripts e módulos copiados da skill, `perfil.json`,
`CALIBRACAO.md`) e o seu `_BATCH_MODELO/`. Nada é compartilhado com a pasta do Fefo. Não gasta crédito.
Para refazer: editar `<raiz>/_FLUXO_VSL/perfil.json` ou apagá-lo e rodar de novo.

## 1. Onde fica a pasta (primeira pergunta)
Diga em duas linhas o que vai fazer ("montar a sua pasta de batches e ligar as suas contas — Kie, Notion,
Frame.io, Drive"). Pergunte com AskUserQuestion:
- **Onde ficam as suas batches?** — "Criar no meu Google Drive (Recomendado)" / "Já tenho uma pasta" (Other = caminho).
  No Drive, o link do "Ready for view" sai sozinho; pasta fora do Drive = a entrega vai sem link do Drive.
  - Criar: `ls -d ~/Library/CloudStorage/GoogleDrive-*/*/` mostra o "Meu Drive"/"My Drive" de cada conta. Nome padrão
    `VSL_BATCHES` (pergunte se quer outro). Mais de uma conta → pergunte qual.
- Monte a pasta com o `fluxo.py` **da pasta desta skill** (a "Base directory" que aparece quando a skill carrega):
  ```
  python3 "<pasta da skill>/scripts/fluxo.py" instalar "<raiz>"
  ```
  Ele cria `<raiz>/_FLUXO_VSL/` e `<raiz>/_BATCH_MODELO/` e grava a raiz em `~/.vsl-batch-editor/raiz`. Depois mude a
  sessão para a raiz (`change_directory`). A partir daqui os comandos rodam de `<raiz>/_FLUXO_VSL/scripts`.
- `_BATCH_MODELO/01_refs/` vem vazio: as fotos dos frascos (Neurobella, VisioVance) e os elementos de campanha
  (`@assets/`) a pessoa pega com o Fefo ou com o cliente e põe na raiz dela.

## 2. Ambiente e conectores (sem perguntar)
- `~/bin/ffmpeg`, `~/bin/ffprobe` e `python3 -c "import faster_whisper, numpy, PIL"`. Faltou → módulo `ambiente` agora.
- Chave do Kie em `~/.vsl-batch-editor/kie_chave`: a pessoa salva o arquivo ela mesma, sem colar a chave no chat. Faltou → pare e peça.
- Conectores da sessão (ToolSearch): Google Drive (`search_files`) e o navegador
  interno (`mcp__Claude_Browser__*`). Faltou o Drive → a pessoa conecta em claude.ai (Configurações →
  Conectores) **com a conta dela** e abre uma sessão nova; o configurar continua de onde parou.

## 3. Perguntas
**Rodada 1 — AskUserQuestion (4 de uma vez):**
1. Quem vê os exports e dá o OK antes de subir no Frame.io? — "Eu mesmo" / "O Fefo" (Other = outro nome) → `aprovador`
2. Depois do OK, quando subir e mexer no Notion? — "Logo depois do OK" / "Às 18h (tarefa agendada)" → `entrega.horario`
3. O Claude comenta o Ready for view e muda o status no card do Notion? — "Sim, pelo navegador do app" / "Não, eu colo à
   mão" → `notion.usar`
4. Você posta Clock In / Clock Out no Slack? — "Não" / "Sim, o Claude me mostra o texto" → `clock.usar`

**Rodada 2 — no chat, numerada, só o que se aplica (texto livre):**
5. Como quer ser chamado.
6. Pule: o Kie não tem workspace.
7. Link do board do Notion e o seu nome como aparece atribuído nos cards (o Fefo é "fefo" no board do time).
8. Conta e pasta do Frame.io onde ficam as suas batches (o Fefo usa `Hike Balance Brand/FEFO`) e o e-mail da conta Adobe.

## 4. Testar cada conexão (sem crédito)
- **Kie**: `python3 scripts/kie.py saldo` devolve o saldo. Não gere nada para testar.
- **Google Drive**: `search_files` acha a pasta da raiz. Para o link do Ready for view, a raiz tem de estar como
  "qualquer pessoa com o link → Leitor": a pessoa muda no Drive, ou você faz com o conector depois de um sim claro.
- **Notion** (se `usar`): `preview_start` com a `url` do board. Tela de login → a pessoa entra com a conta dela no painel
  do navegador (nunca digite e-mail, senha ou código por ela) e avisa. Depois rode `scripts/monitor/notion_cards.js`
  com `javascript_tool`, trocando `RESP` pelo nome da pergunta 7, e confira que `meus` traz os cards dela.
- **Frame.io**: o `frameio.py` usa o app da Adobe do Fefo, que só aceita contas em **Beta users**: antes do login, o
  Fefo adiciona o e-mail Adobe da pessoa no Adobe Developer Console (projeto do Frame.io API → OAuth Single-Page App →
  Beta users). Depois `python3 frameio.py login` no terminal da pessoa (`run_in_terminal`): ela entra na Adobe e copia a
  URL do localhost (Cmd+L, Cmd+C); o script lê da área de transferência — nunca peça para colar o código no chat. Por
  fim `python3 frameio.py ls "<pasta>"` tem de listar a pasta.
- Teste que falhou não trava: grave o perfil com o item em `pendente`, diga o que falta e quem resolve. O módulo que
  depende dele para e avisa.

## 5. Gravar e mostrar
Grave `<raiz>/_FLUXO_VSL/perfil.json` no modelo abaixo. Termine com `python3 fluxo.py perfil` e um resumo de uma linha
por item (✔ ou o que falta). O próximo passo é a primeira batch: copiar `_BATCH_MODELO` e renomear.

```json
{
 "nome": "<pergunta 5>",
 "conta_google": "<conta do Drive da raiz, ou null>",
 "aprovador": "<pergunta 1>",
 "entrega": {"horario": "null (logo depois do OK) | 18:00"},
 "geracao": {"servico": "kie", "script": "scripts/kie.py", "chave": "~/.vsl-batch-editor/kie_chave"},
 "frameio": {"pasta": "<pergunta 8>", "email_adobe": "<pergunta 8>"},
 "notion": {"usar": true, "board": "<pergunta 7>", "responsavel": "<pergunta 7>", "status_entrega": "CS NEEDS TO REVIEW"},
 "drive": {"conta": "<conta Google>"},
 "clock": {"usar": false, "dia_json": "_FLUXO_VSL/dia.json", "automatico": null},
 "pendente": [],
 "configurado_em": "AAAA-MM-DD"
}
```
`clock.dia_json` é relativo à raiz. `clock.automatico` = quem posta no Slack sozinho (só o Fefo tem: monitor do Notion e
tarefa `clock-out-slack`); vazio = o Claude só mostra o texto do Clock Out no fim da batch para a pessoa colar.
Nunca ponha `fonte_da_skill` no perfil de outra pessoa: ele marca o `_FLUXO_VSL` do Fefo, de onde sai o zip da skill.
