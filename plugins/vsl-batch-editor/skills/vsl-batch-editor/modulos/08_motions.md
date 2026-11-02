# Módulo: motions (pedido explícito; local)
Dá para fazer em ffmpeg/libass sobre o AD já montado (ou dentro do `montar`):
- Punch-in: `zoompan`/`scale` com expressão de tempo (100%→110% em 0,15 s) nos momentos de ênfase.
- Legenda animada: ASS com `\t(\fscx120\fscy120)` (pop) e palavra-chave em outra cor (tempos do `palavras_*.json`).
- Stickers/setas/CTA: PNG com transparência (`06_elementos/` ou gerado no Sunburst) com `overlay` e x/y por expressão
  (deslize, quique, pulsar), `enable='between(t,a,b)'`.
- Animações complexas (gráfico, mockup de post animado): considerar Remotion (roda no Mac sem admin).
Ainda não implementado no script — fazer sob demanda e, se aprovado, incorporar ao `fluxo.py montar`.
