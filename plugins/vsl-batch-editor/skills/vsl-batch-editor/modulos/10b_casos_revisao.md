# Revisão: casos já vistos

Consultar com `grep -n -i "<palavra>"`, não ler inteiro. Tirado de `10_revisao.md` em 05/11/2026. Correções com Seedance ou Seed Audio são histórico fora de Drama ad.

## Comentários que já apareceram (13–14/10/2026)
| Comentário | Causa encontrada | Correção |
|---|---|---|
| oferta/número ("switch to 71%") em 1 marca | copy da oferta | vale para as **duas marcas**; refazer a fala inteira (voz de ref sem o número) |
| "cortes na voz" | emenda caindo com a voz soando | `bordas_no_silencio` + fade (já no `fluxo.py`); conferir emendas < −50 dB |
| "corte estranho" entre hook e hold | 0,04–0,15 s de silêncio entre as frases | respiro ≥ 0,2 s (já no `fluxo.py`) |
| "muito pausado" / "fala devagar" | Seedance com duração ≫ fala; pausas reais | `velocidade` (≤ ×1,2) ou refazer com duração certa; encurtar só silêncio real |
| "cena fica congelada" | início parado do Kling/Seedance | `inicio` na cena (`inicio_movimento.py`) |
| "frame muito rápido dela falando" | buraco < 0,5 s entre cenas | já fechado em `segmentos()`; conferir `broll_posicoes_*.json` |
| "weird cut" na troca de setup | sobra de fala que o b-roll não cobre | aparar no `.manual.json` |
| "text looks bad" no frasco | vídeo em Seedance draft 480p deformou o rótulo | refazer só o vídeo no Kling (pro, frasco a ~1/3, parado) |
| "looks so fake" (sorriso) | "big grin" no prompt | expressão contida, boca fechada |
| "3 hands" | duas pessoas com mão em cena | POV com só uma pessoa estendendo a mão |
| "split" na legenda | expressão quebrada ("Nobel / Prize") | `PRESAS` / dois-pontos no `srt()` |
| "text box looks horrible" | legenda diferente do ref | copiar forma/linhas/posição do ref (`pilula`) |
| "text still looks bad, you did the text so much better on other ads" (2822 V2) | `caixa_branca_justa` quadrada; ref e outra batch com caixa arredondada | `pilula` com `quebra` ≥ maior linha do SRT (não re-quebrar "Nobel / Prize") + `legenda_y` nos takes de frasco |
| "change song to something more sexy" / "song does not fit the vibe" | trilha padrão (UI groove) num ad sensual | trilha pelo clima do ad (Suno); mesmo LUFS relativo à voz; trocar só o áudio |
| (Fefo) callout na frente do frasco | `Callout` centralizado (y=960) sobre o rótulo | callout acima dos frascos, dentro do 4:5 (topo ~310 de 1920) |
| "add music" (2082 V2) | export sem trilha (ref tem base contínua, pausas ~−36 dB) | trilha pelo clima do ad (Suno, `02_audio/trilha/prompt_suno.md`), ~15 dB abaixo da voz pelo LUFS, do 1º quadro do hook até o fim |
| (sem comentário, 2082 V2) fim cortado / boca adiantada | imagem mais curta que o áudio: `fps` no fim da cadeia + `concat -c copy` de mp4 | `fps` antes do trim, corte por quadros, `setpts=N/(30*TB)` antes da legenda; conferir quadros × áudio e Whisper no fim |
| "deadspace" / "a lot of deadspace in the ads" (1977 V1) | ruído do clipe (Kling no carro, −39 a −45 dB) acima do −52 da `bordas_no_silencio` → toda emenda anda 0,25 s; pausas ~0,65 s (~30 por AD) | `corte_silencio`: `borda_relativa_db` 3, `silencio_min_s` 0,30, `folga_depois_s` 0,10, `respiro_hook_s` 0,05; pausa longa no corte manual (risada) aparada à mão. Medir pausas na voz dos cortes, não no AD com trilha |
| "3 arms" no b-roll (1977 V1) | quadro do Sunburst já com 3 mãos (queixo + mouse + mesa) | refazer quadro + vídeo com as mãos travadas no prompt ("exactly two hands… one on the mouse, the other flat on the desk; no hand near his face"); recorte 1,6× só como saída sem crédito |
| "here it needs to switch scene" / "here too" nas trocas de parágrafo (2084 V1, batch de card/motion) | painel C com a mesma ilustração em 4 parágrafos (~49 s), copiado da ref | uma ilustração por parágrafo (Sunburst com o quadro do clipe da batch como referência; produto = frasco real); sem fontes do render, trocar só a área da ilustração no MP4 (`BATCH_2084/08_auto/motion_src/patch_2084.py`), inclusive o fundo desfocado do end card. Regra para card/motion: nada de imagem parada > ~12 s |
| "there is a weird sound whenever there is a new scene" (1980 V2) | estalo de ~20 ms uns 40–60 ms antes do fim de todo clipe do Seedance; os cortes iam até o fim do clipe | todo trecho termina antes do estalo (`04_falas.md`, `07_montagem.md`) |
| "deadspace" (1980 V2, Seedance) | o estalo deixava o silêncio final menor que `silencio_min` → ~0,5 s parado entre falas e no hook → hold | cortar antes do estalo; pausas ~0,2 s, hook → hold 0,26–0,32 s |
| "deadspace" + "stills" (3858 V4, Kling 4.0, 12/11) | deadspace = legenda parada na pausa da voz (silencio_min 0,45 deixava ~0,5 s); stills = b-roll de produto quase parado por 3,9 s (S37) | `corte_silencio` do caso 1977 (+ `respiro_hook_s` ~0,29); plano parado → dividir a copy em 2 cenas (selo/ação do banco) e trocar o clipe sem movimento por REUSE com ação; o Whisper exagera os vãos: medir a voz da prévia da hold |
| "VO wrong here" (1980 V2) | corte manual que tirava o "is, is" repetido caiu dentro de "happening" | cortar a palavra repetida, conferindo no Whisper a frase inteira em volta da emenda |
| "VO weird here" (1980 V2, F11 com a marca) | fala acelerada 3,7 dB abaixo das vizinhas; corte comia o "I" de "It's" | igualar o LUFS da fala com as vizinhas; início do corte no ataque da 1ª palavra. Pronúncia só refazendo a fala |
| "lower music" (2080 V2) | trilha −22 dB = ~14 dB abaixo da voz na pausa | trilha −28 dB no `batch.json` (~20 dB abaixo na pausa) |
| "bottom video cuts out here" (2080 V2, `metade_baixo`) | buraco de 0,17 s entre duas cenas: o b-roll some e o avatar fica em tela cheia por 2 quadros; a V2 saiu antes do `fechar_buracos` | remontar com o `segmentos()` atual (ou o da época + só o fecha-buraco); conferir todas as trocas nos 6 ADs |
| "add music" (2086 V2, batch do Premiere) | batch inteira sem trilha | trilha nova no Suno pelo clima (Fefo gera com o `prompt_suno.md`), 15 dB abaixo da voz pelo LUFS, fade-out 1,5 s; mux com `apad` e `-t` do vídeo |
| "this hook is bad, it looks too good… doesn't look authentic" (1970 V2, H1 VV) | os 3 hooks eram as mesmas 4 cenas de cinema (MacBook, luz de filme) mudando só o texto da busca | hooks UGC de celular, um cenário por hook, mesmo homem do corpo, PELE com "unretouched phone photo" (`03_personagens.md`), tela de busca desenhada localmente |
| (Fefo) "anatomicamente incorreto" (1970, mãos do casal) | antebraço torto e grosso; quadro novo com o antigo de referência herdou os dois braços saindo do mesmo tronco | sem referência, cada antebraço entra por um lado do quadro (`05_broll.md`); varrer todos os closes de mão |
| (Fefo) "o mesmo homem 2x" (2082 V3, farmacêutico) | figurante gerado = avatar clonado | quadro editado no Sunburst só trocando o figurante (idade, cabelo, roupa bem diferentes) + Kling |
| (sem comentário) piscada do avatar dizendo a marca antes do frasco (2086 V2) | take começando antes do salto | no MP4: o take começa no salto; legenda queimada recomposta por camada (`BATCH_2086/08_auto/v3/compoe2.py`) |
| "all good, just improvement the subtitle visibility… rn it's hard to read" (2481 V2, Zane, no card do Notion) | `branca_fina` (Helvetica Neue 10, contorno 0,4) some no fundo cartoon | estilo `branca_legivel` (Bold 13, contorno 1,8, sombra 0,9), mesma posição e SRT; remontar só o `montar` e conferir áudio com o mesmo MD5 + SSIM só caindo na faixa da legenda |
| (Fefo) "o comportamento das portas tá estranho" (3214 V1, S01 armário abrindo) | Kling std com a porta em movimento: fecha, a maçaneta pula de lado (~1,6 s) e abre de novo | sem crédito: `inicio` 2,4 (porta já aberta, só o push-in) e a `copy` da cena começando uma palavra depois; porta/gaveta/tampa = quadro já aberto (`05_broll.md`) |
| "VO says macula wrong" / "VO wrong here" (3215 V1, Daniel) | Seedance dizia "makesula/maxula/macella" (o Whisper já escrevia assim; o Fefo tinha aprovado de ouvido) | guia Seed Audio com a voz da F01 e o texto normal → Fefo ouve → Seedance com a guia em `audio_references`; refazer só as falas que o Whisper erra |
| "idk why the video is shaking here" / "make the doctor video not shake" (3215 V1) | push-in das falas em pixel inteiro: fundo parado e salto de ~1,5 px a cada 4–8 quadros | push subpixel (perspective depois do fps=30, no `fluxo.py` desde 26/10); conferir com correlação de fase no fundo |
| "scene has to change here, it can't be the same for this long" / "same scene over and over again" (3215 V1) | 13 clipes 3D do mesmo quadro-base: 7–9 s seguidos do mesmo corte do olho + clipes repetidos no AD | 3D no máximo ~2,5 s por vez, nunca dois seguidos, nada repetido no AD; cena real nova ou o médico no lugar |
| "split sunlight and screens" + "show what the text is saying" (3215 V1, lista de 4 itens) | legenda "Years of sunlight screens" e um só plano para "screens, headlights and reading" | uma cena por item + `estilo.legenda.separar` (um bloco por item) |
| "why are the doctor videos shaking lol" (3214 V1, cliente no Frame.io) | `push_in` da hold em `scale eval=frame` + `crop`: parada ~10 quadros e pulo de 3 px | `fluxo.push()` em subpixel (`perspective` cúbico depois do `fps=30`); mesmo defeito, menor, nos b-rolls do `efeitos_3214.py` → refeitos do `_limpos` (`07_montagem.md`) |
| "text is not following the vouce" (3214 V1, hook 1) | hook com `hook_header` sai sem legenda da fala (só o banner fixo e o título) | `estilo.legenda_no_hook: true` (legenda da fala no hook, por baixo do banner) e `titulo_hook_y` 1140 (título logo acima da pílula; em 480 caía na testa) |
| "VO says macula wrong" / "lutein is said wrong" / "says trials wrong" (3214 V1, 6 pontos) | Seedance com grafia fonética ou sem guia: "maculus/maxilla", "Lutitin/Luton", "tries", "FOEA"; o Fefo tinha deixado passar ("fica") | refazer a fala inteira pelo guia Seed Audio (voz da F01, rate 10, grafia normal; rate 20 se sair lento), pausas > 0,3 s do guia encurtadas, Fefo ouve os guias antes do Seedance; refazer também as falas sem comentário com o mesmo erro no Whisper. **"lutein" não se confere pelo Whisper**: ele escreve certo onde o cliente ouviu errado |
| "says macular degeneration wrong" (3215 V2, F07) | os 2 Whisper ouviam certo, até isolado; a reclamação do cliente vale mesmo assim | fala refeita no Kling 4.0 (Kie, `--imagem` + `--voz`, grafia "dee-generation"); conferir repetição de frase (cortar no silêncio), F0 e LUFS antes de montar |
| "different voice" (3215 V2, F16 VV) | F16 e F19 VV a 111–113 Hz (guias com `pitch_rate −2`); demais falas 116–129 Hz | medir F0 de todas as falas; tom no ffmpeg (`asetrate` + `atempo`, ×1,08–1,10), sem crédito, mantém boca e marca |
| "dont show blood like that" (4029 V4, Daniel no Frame.io) | b-roll de glicosímetro com gota de sangue grande no dedo (S15) | plano novo no Kling a partir de zoom no medidor (crop sem a gota), prompt "no blood, no drops, no finger prick, no lancet"; conferir os outros planos de medidor (pontinho mínimo passou) |

## Trocar um trecho direto no MP4 (batch do Premiere, sem fontes)
- Copie o áudio do export (`-c:a copy`) e troque só os quadros do trecho; tudo numa passada só a partir da versão anterior
  (uma recodificação). Exemplo completo (hook + trechos do corpo): `BATCH_1970/revisao_V3/scripts/hook_v3.py --trocas`.
- Legenda queimada por cima do trecho: recomponha a legenda em vez de mascarar. Legenda com contorno: camada
  V = u·cor + (1−a)·fundo por mínimos quadrados (`BATCH_2086/08_auto/v3/compoe2.py`); legenda com sombra suave:
  "difference matting" com a fonte limpa, só onde há ≥ 150 px de letra nova (`BATCH_1970`).
- Ache o trecho da fonte no export (`acha_trecho.py` da 1970): fonte da hold 768x1344 a 24 fps preenchida a 1080x1920.

