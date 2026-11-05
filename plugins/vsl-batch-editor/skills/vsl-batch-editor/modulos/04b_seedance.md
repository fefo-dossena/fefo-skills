# Falas: Seedance e rotas antigas

Abrir só para Drama ad (único caso em que o Seedance entra), revisão de batch antiga feita no Seedance ou para entender a rota Seed Audio (que não existe no Kie). Tirado de `04_falas.md` em 05/11/2026; texto inteiro anterior em `old/04_falas_antes_tokens_2026-11-05.md`.

As notas de Seedance abaixo valem para Drama ad e para entender batch antiga. O que pesa entre os dois (BATCH#1977 no
Kling × BATCH#1980 no Seedance, 15/10/2026):
| | Kling 3.0 std | Seedance 2.5 720p |
|---|---|---|
| Custo real | 15 falas = 359 cr em 23 gerações (7 refeitas) | 91 s de fala = 637 cr |
| Voz | muda um pouco entre takes (o Kling não aceita áudio de referência) | igual em todos os takes com `audio_references` (F0 170–180 Hz nos 16 takes) |
| Mãos | levanta a mão em ~metade dos takes, mesmo com trava | estável |
| Começo | começa a falar entre 0 e 4 s | fala logo |
| Defeitos típicos | mão deformada subindo; última palavra embolada se a fala vai até o fim do clipe | repete palavra ("is, is"); **estalo ~50 ms antes do fim de todo clipe**; mostra o celular se o prompt citar |
| Marca | grafia fonética dentro da fala acerta | "VisioVance" pode exigir a rota Seed Audio (abaixo) |

- **480p** (3/s) só para teste de voz/ritmo antes do lote; nunca em take com frasco/rótulo legível. **Vídeo gerado é sempre 720p**
  (regra do Fefo, 02/11/2026): 1080p e 4k não se usam.
- Pelo MCP o Seedance sai **com áudio** e não barrou "strong erections" (pelo site saía mudo e barrava).
- `start_image` no Seedance vira referência: o enquadramento sai um pouco mais aberto que o quadro.
- Kling e Seedance sugerem o preset "IN THE DARK" (ou um com o nome da cena) em quase todo pedido com `start_image`,
  até de dia: mande já com `declined_preset_id` (não cobra).


## Voz igual em todos os clipes (Seedance)
- Rota que deu certo (1980): gere a **F01 com a voz nativa** do Seedance (sem áudio de referência), aprove a voz com o
  Fefo e use o áudio da F01 (~6 s, sem marca nem número) como `audio_references` de todas as outras falas.
- `audio_references` = trecho de ~6 s de **outra** fala aprovada da mesma voz, **sem** a frase que muda, sem números,
  oferta ou marca — com o take inteiro/a própria fala antiga ele repete as palavras da referência ("74%" em vez de 71).
- No prompt: "use the audio reference ONLY for voice identity; do NOT repeat its words".
- Alternativa: gerar a fala inteira no Seed Audio (`seed_audio`, voz clonada de um trecho sem a marca) e passar esse áudio
  como `audio_references` — o Seedance segue palavra por palavra com lip-sync ("follow its timing and pronunciation").
- Entrega: "fast, fluent, one single breath, no pauses between words, no stretched words"; frase longa que não pode cair
  o tom: "'…molecule that won the Nobel Prize…' is ONE continuous phrase, no falling tone after 'molecule'".


## Duração no Seedance
- **Seedance**: duração ≈ palavras ÷ 3,3 + 0,5 s (mín. 4 s), ou a duração do áudio de referência arredondada para cima.
  Sobra > 1 s = fala lenta e picotada (microsilêncios entre palavras); curta demais comprime palavras ("compsulas").
  Linha curta (8–10 palavras) no mínimo de 4 s sai a 2,5–2,8 pal/s; o corte de silêncio sobe para ~3,2.
  Arredonde para o inteiro mais próximo, não para cima: `round(palavras/3,3 + 0,6)` deu 2,9–3,3 pal/s cru nas 25 falas da
  3215, o `ceil` deixou as mais lentas a 2,8. Palavra longa (meso-zeaxanthin) +1 s. O Seedance **enche a duração pedida**:
  segundo a mais = fala mais lenta, não folga (a folga antes do estalo vem do corte; H1 da 3214 com 7 s = 2,7 pal/s).
  Hook de selfie andando (6 s) sai a 2,7–2,9 pal/s → `velocidade` 1,08–1,15; a hold sentada (11–13 s) já sai a 3,0–3,3.


## Marca no Seedance e rota Seed Audio (rota acabou no Kie)
- **Seedance**: grafia fonética **dentro** da fala — "Neuro-Bella". VisioVance é instável: "Vizzy-oh Vance" + "VIZ-ee-oh
  VANCE, NOT 'vivo'" deu certo na 2822 e saiu "VizioVaints" na 1980; "Vizio Vance" direto sai "Vivo Vance";
  "Visio-Vance" sai "Vage/Vade". Nota "pronunciation guide, not spoken" foi FALADA — não use.
  **Pronúncia aprovada pelo Fefo (2480, "pronúncia 6"): Seed Audio com a grafia "Visio Vance", speech_rate 5** → guia
  do Seedance. "Vizio Vance" (abaixo, rota antiga da 1980) foi reprovada na 3214: não usar.
  **Rota Seed Audio para a marca** (1980): `seed_audio` com `audio_references` = F01 (voz, sem marca), texto com
  "Vizio Vance", speech_rate 10 (lento, marca nítida; com 40 a marca embola) → aparar e acelerar ×1,35 no ffmpeg →
  `audio_references` do Seedance 720p ("follow its timing and pronunciation"). ~1 cr por teste de Seed Audio.
  **Termos técnicos no Seedance** (macula, lutein, degeneration, fovea, meso-zeaxanthin): a grafia fonética falhou em
  ~40% das falas da 3214 ("deterioration", "demesia", "Luton", "maxilla"). Fala com termo técnico vai pelo guia Seed
  Audio (texto escrito normal, mesma voz) como `audio_references`; F03 e F10 da 3214 acertaram de primeira assim.
  Guia lento: não acelere a fala inteira no ffmpeg (embola); mande o guia original e use `velocidade` na montagem.
  Tom do guia: com `audio_references` = 6,5 s da F01, o Seed Audio sai a 106–136 Hz conforme o texto e o rate (F01 = 121).
  Se destoar da voz, corrija no ffmpeg (`asetrate=44100*r,aresample=44100,atempo=1/r`, r = F0 alvo ÷ F0 do guia; o
  Whisper continua ouvindo certo). `pitch_rate −2` com "Vizio Vance" embolou a marca ("VZO Vance"); com "Visio Vance"
  rate 5 passou (F16/F19 da 3215, com a dica "crisp, clear 'Vance' with a sharp 'nce' sound" no prompt do Seedance).

## Depois de gerar no Seedance
- **Seedance: estalo no fim do clipe.** Todo clipe do Seedance 2.5 tem um estalo de ~20 ms (−30 dB, 15–20 dB acima do
  ruído) uns 40–60 ms antes do fim do arquivo. O corte da fala tem de terminar ANTES dele: corte que vai até o fim do
  clipe = "weird sound whenever there is a new scene", e o estalo ainda impede o corte do silêncio final (sobra ~0,5 s
  parado entre falas = "deadspace"). Confira o envelope dos últimos 100 ms de cada clipe.
  O estalo fica 35–55 ms antes do fim do **áudio** (21 de 25 takes da 3215), e o áudio do clipe às vezes é mais curto que
  o vídeo: o teto do `fluxo.py` (duração do vídeo − 0,08 s) passou do estalo em 7 dos 25. Em toda fala do Seedance, depois
  do `fazer --ate cortes`: `python3 scripts/estalo.py "<batch>" F01 F02 … H1 …` (só mostra) e, conferido,
  `--gravar` (grava `<clipe>.manual.json` terminando 8 ms antes do estalo; não mexe em manual que já existe).
- **Seedance repete palavra** ("is, is"): ouça/Whisper em todo take; o corte manual que tira a repetição não pode cair
  dentro da palavra vizinha (na 1980 caiu dentro de "happening" = "VO wrong").
