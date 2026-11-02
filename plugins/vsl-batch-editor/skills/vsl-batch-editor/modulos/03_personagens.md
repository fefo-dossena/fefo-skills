# Módulo: personagens (gasta crédito)
- Avatar fotográfico de UGC novo: parte de **quadro real** + **Nano Banana Pro** (seção abaixo). Frasco, rótulo, cartão e ilustração seguem no **GPT Image 2.5 Sunburst** (`kie.py sunburst`, 2K, 9:16; ver `modulos/kie.md`). 1 imagem por vez. Mostre ao Fefo e espere a aprovação antes de qualquer vídeo.
- Aparência, idade, roupa e cenário seguem o ad em `01_refs/` desta batch e o brief do canvas — não a batch anterior.
  O personagem que fala (avatar) e o que aparece no b-roll devem ser a mesma pessoa.
- Registre no `plano.json` → `personagens` o caminho do PNG aprovado (batch antiga: ID `hf_<data>_<hora>_<id8>`).
- Frascos: fotos de produto em `01_refs/`; registre os caminhos em `plano.json` → `frascos`.
- **Filtro NSFW do Sunburst** (pedido barrado não cobra): evite fitted/flirty/sexy/silk camisole/satin robe. Cama + toque
  ou roupa íntima = barra — tire um dos dois (casal de pijama acordando, cardigan no sofá à luz de vela passam).
  "Dressed up for a dinner date in a classic red knee-length dress with sleeves" + "warm happy smile" passou.
- **Expressão contida**: "subtle content half-smile, mouth closed, not exaggerated". "Big surprised grin" vira careta fake.
- Duas gerações independentes saem com rostos diferentes: toda variação parte da imagem aprovada (ver abaixo).
- Trocar só o frasco/marca: editar a imagem aprovada com o packshot da outra marca como 2ª referência ("Keep Image 1
  exactly the same... only replace the bottle with the one in Image 2") — sai idêntica.

## Avatar a partir de quadro real (desde 02/11/2026; sem teste nosso ainda)
Fonte: vídeo e guia do Kristian Jennings (`3 Recursos/Pesquisas/Avatar realista de IA a partir de quadro real.md`, no segundo
cérebro). Ideia central: o vídeo só anima o que está na imagem. Imagem gerada do zero não tem ruído de sensor nem poro de
verdade e parece real parada, mas vira cera ao animar. Vale para avatar novo; personagem já aprovado segue como está, com
a variação partindo da imagem aprovada. Metade do esforço do avatar vai aqui, antes de qualquer vídeo.
1. **Quadro:** still de vídeo real de criador real, gravado no celular, escolhido pela idade do público: mais novo no
   TikTok, millennial no Instagram, mais velho no Facebook (o nosso caso comum). Pinterest não serve: está cheio de IA.
   Salve em `01_refs/avatar_quadro/`, com o link de origem.
2. **O que olhar:** enquadramento escolhido de propósito; **nenhum branco estourado** no rosto (dê zoom: brilho com
   detalhe passa, branco puro vira cera ao animar); fundo com alguma profundidade e personalidade, sem bagunça; mãos
   naturais, de preferência as duas à vista; olhar reto para a câmera e boca fechada (`prompts.md`). Legenda queimada só
   se não houver quadro sem ela. Enquadramento, pose, luz e fundo são o que fica do quadro: escolha já com o ad na cabeça.
3. **Pessoa nova, sempre:** nunca usar a identidade de quem está no quadro. Mude traços que cabelo e roupa não mudam
   (olhos, nariz, pele), até não poder ser a mesma pessoa. Médico, enfermeiro ou profissional de saúde nunca sai de foto
   de profissional real. Dúvida se ficou parecido: mostre os dois ao Fefo.
4. **Mudar tudo em um só prompt** (`kie.py nanopro`, quadro em `--ref`): pessoa, fundo, acessórios, microfone e o bloco
   PELE juntos. Edição em cima de edição deixa emenda que o olho não vê e aparece ao animar. Saiu ruim: gere de novo a
   partir do quadro, sem editar o resultado. Cada coisa pedida é mais uma camada de IA: mude só o que precisa. Pela mesma razão, o RETOQUE abaixo é para imagem já aprovada de antes, não
   um passo fixo deste caminho.
5. **Detalhe fora da média:** a IA tende ao padrão (camiseta lisa, cabelo genérico). Dê 1 ou 2 detalhes da vida da
   pessoa: brinco, colar, um fone numa orelha só, planta ou luminária no fundo. Coerente com a personagem do ref.
6. **Motivo para o áudio limpo:** microfone de lapela visível, microfone na mão ou celular perto do rosto. Sem isso, a
   voz limpa da IA não combina com a cena.
7. **Quem é o avatar:** em geral alguém que já resolveu o problema, não quem ainda sofre com ele, salvo se o ref ou o
   roteiro pedir o contrário. O ref da batch continua mandando na aparência, idade e roupa.
8. **Descartar cedo:** ~1 em 10 imagens não anima bem mesmo certa. Depois de 2 ou 3 testes curtos que quebram, troque o
   quadro em vez de insistir: imagem custa bem menos que vídeo.

## Pele realista (padrão do Fefo desde 13/10/2026)
Todo personagem **fotográfico** leva os parâmetros de pele abaixo (ilustração, ex. anos 50, não leva):
- **Gerado do zero:** prompt nos blocos de imagem (●) de `modulos/prompts.md` (Scene Context, Active References,
  Location Map, First Frame, Optics, Performance/expressão, Lighting, Style, Positive Locks) com aparência/roupa/cenário
  do ref + o bloco "PELE" abaixo no fim (dentro de STYLE).
- **Variação do personagem aprovado** (roupa/cenário): "the same person from the reference image, exact same face" +
  o que muda + bloco "PELE", com a imagem aprovada em `image_references`.
- **Retoque de uma imagem já gerada** (pele de plástico, sem mudar mais nada): prompt "RETOQUE" abaixo, sem alterar,
  com a imagem em `image_references`.
- **UGC de celular** (hook/cena que tem de parecer gravada pela pessoa): troque a última frase do PELE ("captured on a
  professional DSLR camera with a prime lens") por "authentic, unretouched phone photo" e acrescente "authentic amateur
  smartphone photo… nothing polished, it must not look like an advertisement". Com o DSLR o hook da 1970 saiu "too good…
  doesn't look authentic" (Daniel). Consistência entre quadros do mesmo hook: primeiro o rosto (com a ref do avatar),
  depois o close das mãos com a imagem do rosto como referência (mesma cama, luz e roupa).

### PELE (anexar ao prompt de geração)
```
Skin micro-realism: subtle natural skin texture with visible pores, fine surface lines and micro imperfections;
very light realistic micro-wrinkles (under eyes, smile lines, forehead) without aging the subject; slight natural
skin tone variation: tiny blemishes, soft uneven texture, natural redness in subtle areas (nose tip, cheeks, eyelids);
natural subsurface scattering and skin translucency; natural oil/moisture variation on the skin surface (not glossy,
just realistic); pores and fine skin texture visible as if captured on a high-end camera lens.
No beautification filters or skin smoothing, no face symmetry correction, no color grading or stylization, no AI
enhancement that removes human imperfections, no plastic or airbrushed skin. Must look like an authentic, unretouched
photo captured on a professional DSLR camera with a prime lens, where real human skin texture, depth and natural
imperfections are visible and believable.
```

### RETOQUE (com imagem de referência — texto original do Fefo)
```
Use the uploaded image as the strict reference. Do not alter the composition,
expression, lighting, colors, background, clothing, hair, or any facial
features. The only goal is to enhance skin micro-realism.
SKIN ENHANCEMENTS ALLOWED:
- Add subtle natural skin texture: visible pores, fine surface lines,
micro imperfections
- Introduce very light, realistic micro-wrinkles (under eyes, smile lines,
forehead) without aging the subject
- Add slight natural skin tone variation: tiny blemishes, soft uneven texture,
natural redness in subtle areas (nose tip, cheeks, eyelids)
- Preserve and enhance natural subsurface scattering and skin translucency
- Add natural oil/moisture variation on skin surface (not glossy, just realistic)
- Make pores and fine skin texture visible as if captured on a high-end
camera lens
STRICTLY FORBIDDEN:
- No beautification filters or skin smoothing
- No face reshaping, symmetry correction, or facial structure changes
- No color grading, saturation changes, or stylization
- No AI "enhancement" that removes human imperfections
- No plastic or airbrushed skin appearance
The final result must look like an authentic, unretouched photo captured on a
professional DSLR camera with a prime lens — where real human skin texture,
depth, and natural imperfections are visible and believable.
Keep everything else in the image EXACTLY identical to the original.
```
