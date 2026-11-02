# Módulo: personagens (gasta crédito)
- Modelo: **GPT Image 2.5 Sunburst** (`kie.py sunburst`, 2K, 9:16; ver `modulos/kie.md`), 1 imagem por vez. Mostre ao Fefo e espere a aprovação antes de qualquer vídeo.
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
