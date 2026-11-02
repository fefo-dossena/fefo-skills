# Módulo: roteiro → plano.json
Entrada: canvas em PDF ou texto em `00_roteiro/`. Saídas: `00_roteiro/roteiro.txt`, `08_auto/plano.json`,
e para leitura humana `00_roteiro/cenas.md` + `00_roteiro/falas.md`.

1. Extraia a copy para `roteiro.txt` (blocos `HOOK 1`, `HOOK 2`, `HOOK 3`, `HOLD` com linhas numeradas).
2. `python3 fluxo.py novo-plano "<batch>"` cria o esqueleto do `plano.json` (hooks, hold com `{MARCA}`).
3. Preencha **falas** (clipes do avatar) e **cenas** (b-roll) no `plano.json`:
```json
"falas": [
 {"id":"H1","tipo":"hook","hook":1,"texto":"<fala do hook>","dur":5},
 {"id":"F01","tipo":"hold","linhas":"1","texto":"<frase(s)>","dur":7},
 {"id":"F06","tipo":"hold","linhas":"12","texto":"... try {MARCA}.","dur":5,"marca":true}
],
"cenas": [
 {"id":"H1-01","nome":"corpo-3d-pelve","tipo":"hook","hook":1,"copy":"<trecho exato da fala>","ref":"-","motion":"<prompt Kling>"},
 {"id":"S03","nome":"frasco-revelado-mao","tipo":"produto","copy":"until I found this.","ref":"B","frame":"<prompt do 1º quadro>","motion":"<prompt Kling com {MARCA}>"},
 {"id":"S05","nome":"homem-sofa-celular","tipo":"geral","copy":"Went on YouTube, found like 50 different videos.","ref":"N","frame":"...","motion":"..."}
]
```
- Falas: agrupe frases em clipes de 5–12 s; duração Kling = ceil(palavras/3,3)+1,5 (mín. 5); Seedance ver `04_falas.md`.
  Linhas que citam a marca viram
  clipe próprio com `"marca": true` (o script espera `F06_neurobella.mp4` e `F06_visiovance.mp4`).
- Cenas: uma por trecho de ~2–3 s de fala, nunca acima de 3 s (frase longa vira duas cenas; ver "Ritmo" em `07_montagem.md`); `copy` = trecho **exato** do roteiro (o script acha o tempo da cena por ele;
  use `{MARCA}` no lugar do nome do produto). Ordem das cenas = ordem da fala.
- `ref`: `-` só texto · `N` narrador · `NW` narrador+esposa · `W` esposa · `B` frasco · `BN` frasco+narrador · `BC`/`BNC` + cápsula.
- `tipo`: `geral` (sem produto) · `produto` (gera uma por marca) · `hook`.
- `frame` e `motion` já são escritos na estrutura de 14 blocos de `modulos/prompts.md` (imagem: só os blocos ●).
- Hooks: classifique cada HOOK do canvas por tipo (`modulos/hooks.md`: linha do tempo, resultado + "this", alerta,
  objeção virada, assunto do momento, abertura nativa) e escreva a cena do hook com a execução do tipo: ação já
  acontecendo no 1º quadro, produto até ~2 s, texto do `hook_header` com o trecho-chave em destaque. Os 3 hooks com
  1º quadro diferente.
4. Gere `cenas.md` e `falas.md` (tabelas legíveis) a partir do plano, para o Fefo revisar. Com o `estilo` definido, o
   próximo passo é o módulo `banco` (`05a_banco.md`), antes de qualquer geração.
5. Palavras sensíveis na fala ("erection" etc.): o Kling passa; o Seedance pelo site barrava como NSFW (pelo MCP passou
   na 2827). Avise se a copy mudar. Oferta/número na copy vale igual para as duas marcas, salvo pedido do Fefo.
