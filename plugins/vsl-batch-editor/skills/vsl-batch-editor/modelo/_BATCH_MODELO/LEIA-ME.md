# BATCH MODELO

Copie esta pasta e renomeie para:
BATCH_XXXX - Nome do Ad - Condição - L2 - Nível de Awareness - Avatar
(ex.: BATCH_1975 - Not Finished - Erectile Dysfunction - L2 - Problem Aware - Daniel)

## Fluxo
1. 00_roteiro  -> copy + lista de cenas (S01, S02...)
2. 01_refs     -> ad de referência e fotos do produto
3. 02_audio    -> VO do ElevenLabs (hold + hooks) por produto, e trilha
4. 03_avatar   -> vídeo do avatar falando
5. 04_broll_hold / 05_broll_hooks -> assets gerados, nomeados pela cena
6. 06_elementos -> stickers, sliders, overlays de campanha
7. 08_auto     -> a skill gera aqui: hold cortada (XML), legendas (SRT), timelines
8. 07_premiere -> projeto final
9. 09_export   -> vídeos finais por produto

## Regras de nome (o que a skill usa para montar sozinha)
- Cenas numeradas pela ordem do roteiro: S01, S02, S03...
- Arquivo de b-roll: S05_descricao-curta.mp4 (o S05 liga o asset ao trecho da copy)
- Cena COM produto: mesmo nome nas duas pastas de produto
    04_broll_hold/neurobella/S07_mulher-segurando-frasco.mp4
    04_broll_hold/visiovance/S07_mulher-segurando-frasco.mp4
  -> a skill troca uma pela outra e mantém o mesmo tempo.
- Cena SEM produto vai em 04_broll_hold/geral/ e serve para as duas versões.
- Hooks: hook1, hook2, hook3 (áudio, avatar e b-roll com o mesmo número).
- Sem acentos nem espaços nos nomes de arquivo (use hífen).

## Sequências no Premiere (padrão da BATCH_2281)
- 'HOLD_neurobella' e 'HOLD_visiovance' como sequências próprias
- AD1/AD2/AD3 = hook + sequência da hold aninhada
- Um projeto por produto, ou as duas holds no mesmo projeto

## batch.json
Configuração da batch (produtos, estilo da legenda, elementos de campanha).
A skill lê esse arquivo; ajuste por batch.
`card` = título exato do card no Notion (ex.: `BATCH#3215 - Thinning Shield - Macular Degeneration - L2 - Problem Aware - Daniel`):
é o nome dos ADs finais, com a marca e o AD no fim (`... - Daniel - Neurobella - AD1.mp4`).

## Fluxo modular (desde a BATCH_2080)
A batch é descrita por `08_auto/plano.json`. Na pasta `_FLUXO_VSL/scripts`:
`python3 fluxo.py status "<batch>"` mostra o que falta e `python3 fluxo.py fazer "<batch>"` refaz só o necessário.
Detalhes em `_FLUXO_VSL/SKILL.md` e `_FLUXO_VSL/modulos/`.
