# Módulo: motions (pedido explícito; local)
Dá para fazer em ffmpeg/libass sobre o AD já montado (ou dentro do `montar`):
- Punch-in: extinto (Fefo, 19/11/2026). Ênfase = corte para outra cena. Regra: `@CLIENTES/_FLUXO/LEIA-ME.md`, seção "Cenas, não punch-in".
- Legenda animada: ASS com `\t(\fscx120\fscy120)` (pop) e palavra-chave em outra cor (tempos do `palavras_*.json`).
- Stickers/setas/CTA: PNG com transparência (`06_elementos/` ou gerado no Sunburst) com `overlay` e x/y por expressão
  (deslize, quique, pulsar), `enable='between(t,a,b)'`.
- Animações complexas (gráfico, mockup de post animado): HyperFrames (Remotion removido em 19/11/2026; ver `_FLUXO/MANUAL_DO_MONTADOR.md`, seção 0).
Ainda não implementado no script — fazer sob demanda e, se aprovado, incorporar ao `fluxo.py montar`.
