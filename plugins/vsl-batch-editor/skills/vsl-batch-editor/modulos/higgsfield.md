# Higgsfield
**Fora das batches desde 02/11/2026: a geração saiu para o Kie (`modulos/kie.md`). Este módulo só vale com pedido do Fefo e para entender batch antiga.**

**Outra pessoa:** o conector "Higgsfield" do claude.ai dela, com o workspace do perfil (`higgsfield.workspace_id`,
Empire Vision) selecionado antes de gastar crédito. Os nomes HiggsEV/HiggsFefo e o id `mcp__23663d62-…` abaixo valem só
no perfil do Fefo.

**Conector: HiggsEV** (pedido do Fefo, 20/10/2026). Toda geração das batches da Empire Vision (imagem, vídeo, voz,
upload, `jobs_wait`, `show_generations`) sai pelo **HiggsEV** = o conector do claude.ai que aparece na sessão como
"Higgsfield" (ferramentas `mcp__23663d62-…`), com o workspace **Empire Vision** (`d347e11c-f8da-46fd-8c3e-0ff504aa17ed`)
selecionado. Antes de gastar crédito: `list_workspaces` e conferir Empire Vision com `is_selected: true` (senão
`select_workspace` com esse id). Nunca gerar no workspace privado nem pelo **HiggsFefo** (`mcp__HiggsFefo__*`, outra
conta). Se o conector não estiver na sessão ou pedir login, pare e avise o Fefo; não reconecte o HiggsEV.

## Pela integração MCP (preferido desde 12/10/2026)
- Imagem: `generate_image_batch` (gpt_image_2_5, variant sunburst) · vídeo: `generate_video_batch` (`kling3_0` ou
  `seedance_2_5`) · voz: `generate_audio_batch` (`seed_audio`; text2speech_v2/elevenlabs) · `jobs_wait` · uploads:
  `media_upload` + curl PUT + `media_confirm`.
- **Envie um pedido por vez, com ~10–15 s de intervalo** — não lotes de 12. O plano limita pedidos e vídeos simultâneos (429).
- Kling/Seedance com `start_image` voltam "Preset IN THE DARK recommended" (ou um preset com o nome da cena, ex. "RED
  THREAD") sem enviar nada, em quase toda cena, até de dia: mande já com `declined_preset_id` (não cobra).
- 429 `rate_limit_reached`: limite da conta (compartilhada), não do modelo — aparece em Kling e Seedance quando há ~11
  vídeos rodando, inclusive os do time (Grok, Wan, Seedance). Não cobra; esperar ~2,5 min ou o anterior terminar e seguir um por vez.
- **Saldo**: a conta é compartilhada e as sessões em paralelo gastam do mesmo saldo (23/10/2026: 4.985 cr às 10h →
  ~1.040 às 11h20, com 4 batches rodando). `balance` antes de cada lote grande; se não cobrir, avise o Fefo antes de
  mandar. Em dia cheio a fila do Seedance leva 7–12 min por clipe.
- Timeout do conector ("server isn't responding") pode ter enviado a geração: conferir `show_generations`
  (only_completed=false) ou `transactions` antes de reenviar (senão cobra duas vezes).

## Modelos de vídeo que usamos (MCP, conferido em 16/10/2026)
Qual usar em cada caso: falas em `04_falas.md`, b-roll em `05_broll.md`. MiniMax saiu do fluxo (16/10/2026).
**Seedance só em Drama ad** (ordem do cliente, 30/10/2026); fora dele, só Kling.
| Modelo | id | Duração | Opções | Mídias |
|---|---|---|---|---|
| Kling 3.0 | `kling3_0` | 3–15 s | `mode` std / pro (1080x1912) / 4k · `sound` on/off | `start_image`, `end_image` (sem áudio de referência) |
| Seedance 2.5 | `seedance_2_5` | 4–30 s | `mode` t2v / omni_reference / video_edit / video_extension · 480p/720p/1080p · `generate_audio` | `start_image`, `end_image`, `image_references`, `video_references`, `audio_references` |
Existem e ainda não foram testados: `kling3_0_turbo` (barato, só start), `kling_o3_image_reference` (Kling Omni, até 7
imagens de referência), `kling_video_edit`, `seedance_2_0`, e de imagem `seedream_v5_pro` (folha de personagem) e
`soul_cinematic` (folha de cenário, só 1 referência). Antes de usar um deles, `models_explore` (action get) e
teste com o Fefo.

## Custos pelo MCP (out/2026)
Sunburst high 2K 2,75/img · Kling 3.0 std 1,75/s com som, 6,25 por 5 s sem som · Kling 3.0 pro 7,5 por 5 s sem som
(3215) · Seedance 2.5 720p 7/s com áudio
(91 s de fala na 1980 = 637 cr), 35 por 5 s sem som · Seedance 480p 3/s · Seed Audio ~1 por teste (0,6–2,5) ·
ElevenLabs (text2speech_v2) ~2 por 38 s.

## Pelo navegador interno (fallback)
Até existir integração por API/MCP, o Higgsfield é operado pelo navegador interno (login já feito pelo Fefo).
**Melhoria pendente:** testar a API/MCP do Higgsfield (menus "API" e "MCP" do site) — devolveria o ID de cada geração e
eliminaria cliques e a identificação por quadro.

## Configuração da tela
- `resize_window` 1440x900 a cada turno (o app limpa). Se a tela renderizar minúscula, use refs/JS em vez de coordenadas.
- Prompt: clicar no textbox (ref), `cmd+a Delete`, `type`. `form_input` NÃO funciona no editor.
- Duração (Kling): abrir "Duration", focar `[data-duration-slider-thumb]` via JS e usar setas ←/→ (1 s por tecla).
- Quadro inicial (Kling): `__unpick()`, clicar no botão de start frame (ref do `button type=file`), `__pickR('<id8>')`,
  Escape. Atalhos em `scripts/higgsfield_helpers.js`. Sempre rodar a **guarda** antes do Generate.
- Referências de imagem (Sunburst): botão "@"/"Elements" > abas Generations/Uploads; ali `.click()` em JS funciona.
  Remover: `[data-tour-anchor="tour-image-reference-remove"][data-media-id^="<id8>"]`.

## Armadilhas conhecidas
- Conta **compartilhada**: colegas geram no mesmo histórico e mudam o formulário (duração, resolução, modelo). Conferir
  modelo, duração, resolução, som e custo antes de cada lote; identificar resultados pelo 1º quadro/prompt.
- Configurações ficam no `localStorage` (`hf:video-<modelo>-store:*`). O Seedance 2.5 pode herdar `generateAudio=false`
  do Draft — não há botão para isso na tela; checar/ajustar o store.
- Seedance 2.5 Draft = vídeo mudo. Seedance 2.5 com áudio = barra fala sensível (NSFW). Kling 3.0 = ok para fala.
- `data-job-status` nos cards: queued / in_progress / completed / nsfw. Polling em JS com laços ≤ 38 s.
- O modo **List** do histórico pode travar a aba com histórico grande; preferir Grid.
- Downloads: `https://d8j0ntlcm91z4.cloudfront.net/user_<conta>/hf_<id>.mp4|png` (curl direto, sem passar pelo proxy de imagem).
- Upload de arquivo local pelo navegador interno não funciona (sem file chooser e o site bloqueia fetch de 127.0.0.1):
  pedir ao Fefo para subir o arquivo, ou usar o que já está em Uploads.

## Custos observados pelo site (out/2026, antes do MCP)
Sunburst 5/img · Kling 720p 1,75/s com som, ~1,25/s sem som (5 s = 6,25) · Seedance Draft 3/s · GPT Image 2 (2 imgs) 17.
Batch 2080 inteira (20 falas + 45 b-rolls + 28 imagens + testes): ~850 créditos.

## Com o painel do navegador escondido (10/10, BATCH#2078)
Cliques/teclas por coordenada falham ("not compositing"). Tudo funciona por JS:
- Prompt (editor **Lexical**): `ed.__lexicalEditor.setEditorState(E.parseEditorState(JSON))` com um parágrafo de texto
  (`execCommand` não limpa o texto antigo). Conferir `ed.innerText === prompt`.
- Botões/abas: `__fire(el, x, y)`. Duração: abrir o botão "Ns", `thumb.focus()` + `KeyboardEvent('keydown', ArrowRight)`.
- Som: o 3º switch (`[role=switch],input[type=checkbox]`) = Sound; preço 1,75/s com som.
- Imagem (Sunburst): checar `[data-tour-anchor="tour-image-reference-remove"]` antes de gerar — o formulário pode vir
  com referências de outra pessoa (conta compartilhada).
- Se o viewport voltar ao padrão, o site abre em layout de celular ("MOBILE ACCESS") e o histórico some: rodar
  `resize_window 1440x900` e recarregar. Lotes longos no histórico podem travar a aba ("Target crashed"): recarregar e
  conferir no histórico o que já foi gerado antes de repetir (cobra de novo).
