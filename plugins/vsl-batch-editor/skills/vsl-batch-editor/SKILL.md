---
name: vsl-batch-editor
description: Produz vídeo gerado por IA para qualquer cliente (anúncio, UGC, VSL, short drama) de ponta a ponta - pede o contexto do cliente no início, roteiro e plano, personagens, falas, b-roll, montagem, conferência única pelo fluxo.py checar, sala de revisão e entrega. Empire Vision (Neurobella, VisioVance) e Trendscale têm ficha pronta.
---

# Vídeo gerado: do pedido à entrega

Responda em português do Brasil, frases curtas. "Encerrar/fechar o projeto" = **terminar de produzir**, não parar.
Este arquivo é um índice. Cada regra mora num lugar só; aqui fica o ponteiro.

## 1. Início: cliente e contexto
1. Tire do pedido ou da pasta: cliente, tarefa (nova ou revisão), pasta de trabalho. Faltou algo: pergunte.
2. Leia a **ficha do cliente**: `@CLIENTES/_FLUXO/clientes/<cliente>.md` e o `.json` ao lado (no PC do Fefo, `@CLIENTES` =
   `G:/Meu Drive/@CLIENTES`; fora dele, `<pasta desta skill>/clientes/`). Leia só a do cliente da tarefa.
   - Empire Vision: `empire-vision.md`.
   - Trendscale: `@TRENDSCALE/CLAUDE.md` e `@TRENDSCALE/2026/_FLUXO/LEIA-ME.md` (fluxo próprio; daqui vêm o roteiro único e os agentes).
3. **Sem ficha:** faça as perguntas de início numa mensagem só e grave as respostas em `clientes/<cliente>.md` antes de planejar:
   entrega (formato, duração, resolução, quantos vídeos e versões), gerador e conta (quem paga o crédito), referência e estilo,
   legenda (padrão: pílula), loudness, quem aprova, onde entrega e como nomeia, prazo.
4. **Aprendizados:** antes de planejar, leia as ~10 entradas mais recentes do mesmo cliente em `@CLIENTES/_FLUXO/APRENDIZADOS.md`
   e cite no plano as que se aplicam (módulo `referencia`). Sem o arquivo (outra máquina): avise numa linha e siga.
5. Ordem de quem manda: brief do pedido > referência da tarefa > ficha do cliente > padrão desta skill.
   O estilo vem do ref da tarefa, nunca de tarefa anterior. Sem ref: proponha um estilo e espere o OK antes de gerar.

## 2. Onde está tudo (uma fonte só)
- Código comum: `@CLIENTES/_FLUXO/scripts/` (`fluxo.py`, `fluxo_partes/`, `checagens/`, `kie.py`, `pilula.py`).
- Texto desta skill, módulos e agentes: `@EMPIRE VISION/2026/_FLUXO_VSL/` (`SKILL.md`, `modulos/`, `plugin/agents/`, `plugin/plugin.json`).
  Os `scripts/` de lá são atalhos para o núcleo ou scripts só da EV.
- O plugin (GitHub e cache em `~/.claude/plugins`) é **só saída** do `fluxo.py publicar`: nunca edite lá. No PC do Fefo,
  rode sempre do Drive. Mudou a skill: `py fluxo.py publicar "<o que mudou>"`, só com o OK do Fefo (`--teste` mostra o diff).
- Outra pessoa: `py "<pasta da skill>/scripts/fluxo.py" instalar "<raiz>"`; perfil no módulo `configurar`.

## 3. Sessão
- **Tamanho:** vídeo (ou batch de ADs) de até ~30 s = **uma sessão só**, do pega à entrega. Acima: 2 etapas
  (`<tarefa> · 1 plano e geração`, `<tarefa> · 2 montagem e entrega`); cada revisão do cliente numa sessão nova.
  Passagem pelo arquivo de estado (`ESTADO.md` ou o do job) e por `@CLIENTES/_FLUXO/SESSAO_MAE.md`.
- **Fechamento com aprendizado:** no fim de etapa, de entrega ou de sessão que para, escreva a entrada em `@CLIENTES/_FLUXO/APRENDIZADOS.md`
  (modelo de lá) e avise a Central. Regra: `REGRAS_DA_SESSAO.md`, seção "Fechamento com aprendizado". Sem o arquivo: avise e siga.
- **Regras da sessão** (subagente, teto de crédito, cabeçalho, prévia, modelo por etapa, travas 1–5): `@CLIENTES/_FLUXO/REGRAS_DA_SESSAO.md`. Leia no começo.
- **Agentes:** `montador` (montagem, `checar`, render; um por versão), `executor-mecanico` (passo já aprovado: subir,
  renomear, status), `revisor-de-video` (só o que a máquina não mede).

## 4. Caminho de trabalho: roteiro único
Siga a tabela "Roteiro único" de `@CLIENTES/_FLUXO/QUALIDADE_DO_BATCH.md`, passo a passo. Lá moram também o checklist
da Louise (L1–L6) e os 4 pontos de controle.
- **A conferência é uma só: `fluxo.py checar`, pelo `montador`, uma vez por versão.** Não rode freezedetect, lascas,
  ritmo, imagem × fala, Whisper nem prancha à mão como passo; esses scripts servem só para investigar um achado.
- Pedido principal primeiro (trava 1) e sala cedo (trava 5): `REGRAS_DA_SESSAO.md`.

## 5. Módulos (leia o módulo antes de rodá-lo)
| Módulo | Quando | Crédito | Modelo · esforço | Arquivo |
|---|---|---|---|---|
| configurar | primeira vez de cada pessoa; sem raiz ou perfil | não | Sonnet · baixo | `modulos/00_configurar.md` |
| ambiente | primeira vez na máquina; script reclama de ffmpeg | não | Haiku/Sonnet · baixo | `modulos/00_ambiente.md` |
| roteiro | texto ou PDF novo; sem plano | não | Opus · alto | `modulos/01_roteiro.md` |
| referencia | início de toda tarefa; ref novo (define o estilo) | não | Opus · alto | `modulos/02_referencia.md` |
| banco (EV) | tarefa nova da EV, antes de gerar | não | Sonnet · médio | `modulos/05a_banco.md` |
| busca_avatar | avatar fotográfico novo sem quadro real | não | Sonnet · médio | `modulos/03a_busca_avatar.md` |
| personagens | personagem sem imagem aprovada | sim | Opus · alto | `modulos/03_personagens.md` |
| falas | falas faltando | sim | Sonnet · médio | `modulos/04_falas.md`, `modulos/04b_seedance.md` |
| broll | b-roll faltando | sim | Sonnet · médio | `modulos/05_broll.md` |
| coleta | gerações antigas a baixar | não | Haiku/Sonnet · baixo | `modulos/06_coleta.md` |
| montagem | cortes, legendas, ADs pendentes | não | Sonnet · baixo (`montador`) | `modulos/07_montagem.md` |
| motions | pedido explícito (punch-in, CTA, legenda animada) | não | Sonnet · médio | `modulos/08_motions.md` |
| review room | versão conferida para o Fefo; "apply notes" | não | Sonnet · baixo | `modulos/11_review_room.md` |
| entrega | fim da tarefa ou revisão | não | Haiku/Sonnet · baixo | `modulos/09_entrega.md` (EV) ou ficha |
| revisao | notas do cliente; card "só QA" | depende | Opus para decidir, Sonnet para aplicar | `modulos/10_revisao.md`, `10b`, `10c` |
Geração: `modulos/kie.md` (Kie, padrão) e `modulos/higgsfield.md` (só com pedido). Prompts: `modulos/prompts.md` e
QUALIDADE 1.2. Hooks: `modulos/hooks.md`. Modelos permitidos: a ficha do cliente manda.

## 6. Regras de todo cliente (moram aqui)
- **Crédito só com OK**, com teto (regra 2 de REGRAS_DA_SESSAO). Caiu a conexão numa geração: `kie.py espera <taskId> <saída>`; nunca reenviar.
- **Sempre 720p**, na geração e no export, salvo ficha.
- **Legenda:** pílula TikTok Sans Medium do `pilula.py`, na margem de 16/11. Regra única: `@CLIENTES/_FLUXO/LEIA-ME.md`, seção Legenda.
- **Sem selo de IA** (rótulo, sticker, marca d'água de gerador) no vídeo final, mesmo se o brief pedir.
- **Texto inventado pela IA = gerar de novo.** Personagem fotográfico com o bloco de pele realista (`modulos/03_personagens.md`).
- **Não remendar palavra colando voz:** refazer a fala inteira.
- **Versões:** atual na pasta de export; anteriores em `_old/V<k>/`, nunca pasta irmã. Nunca sobrescrever arquivo do Fefo.
- **Intermediários fora do Drive** (`$TEMP` ou scratchpad), apagados no fim. Mover pasta no Drive = mover a pasta inteira.
- Sem acento nem espaço em nome novo (menos o vídeo final, que segue a ficha).
- **Esperar o Fefo = avisar na hora**, com o que destrava e a frase pronta; ~30 min sem resposta, lembre uma vez.
  O OK vale só escrito na sessão da tarefa; peça um OK que cubra a etapa inteira.
- **Economia de contexto:** saída curta (`ffmpeg -v error`, `| tail -20`); script grande por trecho (`grep -n` + leitura do trecho);
  o `fluxo.py` está dividido em `fluxo_partes/`: mexa só na parte do assunto.
