# Módulo: busca de referências reais para avatar (não gasta crédito)
Vem antes do `03_personagens.md`, em todo avatar fotográfico de UGC novo (Fefo, 03/11/2026). O vídeo só anima o que está
na imagem: o quadro real dá pele, luz, fundo e pose de verdade, e o Nano Banana Pro troca a pessoa. Este módulo é como achar
esse quadro. Personagem já aprovado em batch anterior não passa por aqui.

## 1. Ficha da busca (antes de abrir o navegador)
Do roteiro e do briefing, escreva em `01_refs/avatar_quadro/busca.md`:
- **Quem:** idade, gênero, jeito (dona de casa de 60, ex-enfermeira, avô aposentado), o que o roteiro diz que ele viveu.
- **Formato:** como a fala acontece no ad de referência: falando para a câmera (storytime), review do produto na mão,
  desabafo no carro, cozinha, quarto. Segue o ref da batch.
- **Enquadramento e luz:** do ref (plano médio, selfie com o braço, celular apoiado), dia ou noite, dentro ou fora.
- **Plataforma pela idade do público:** Facebook para 55+ (o mais comum nas batches), Instagram para millennial, TikTok para
  jovem. Pinterest e banco de imagem não servem: foto posada não tem a imperfeição que precisa ser animada.
- **Termos de busca** (em inglês, o público é americano), 4 a 6, combinando quem + formato:
  `grandma storytime talking to camera`, `65 year old woman vision update`, `retired nurse eye health tips`,
  `senior woman kitchen vlog`, `my eyes after 60`, `granny review`. Use também o assunto do ad (visão, memória, cansaço
  visual), porque criadores reais do nicho já têm o cenário certo.

## 2. Busca no navegador interno
1. Navegador interno (`mcp__Claude_Browser__*`), em aba nova. Login nas redes é do Fefo: se pedir login, pare e avise;
   nunca entre com senha. Sem download de vídeo (pede permissão a cada arquivo); o quadro sai de captura de tela.
2. Busca direta: Facebook `facebook.com/search/videos/?q=<termo>`, Instagram por hashtag (`instagram.com/explore/tags/<tag>/`)
   ou reels de perfil, TikTok `tiktok.com/search/video?q=<termo>`.
3. Passe os resultados rápido e abra só o que já tem o enquadramento do ref. Até 10 vídeos por rodada; nova rodada só se
   nenhum servir. Não fique num perfil só: candidatos de pessoas e cenários diferentes. Navegue e leia a página como
   texto/acessibilidade (`get_page_text`, `read_page`, `find`) sempre que der; captura de tela só do candidato (uma por
   vídeo, `screenshot` com `scale: 0.5`).
4. **Tirar o quadro:** aumente a janela antes (`resize_window` 900 × 1600) para o vídeo ficar grande, pause no instante certo
   (boca fechada, olhar para a câmera, mãos à vista) e use `computer` `zoom` só na área do vídeo, `scale: 1`, e só no quadro
   final escolhido (os outros candidatos ficam na captura de `scale: 0.5`). Copie o
   arquivo da captura para `01_refs/avatar_quadro/q<n>_<plataforma>.png` e confira o tamanho: abaixo de 600 px de altura,
   pause de novo com o vídeo maior.

## 3. O que conferir em cada quadro (descarte sem dó)
- Celular de verdade, não câmera de estúdio; sem filtro de beleza (pele lisa demais = filtro).
- **Nenhum branco estourado no rosto** (dê zoom na testa, nariz e bochechas).
- Fundo com profundidade e personalidade (casa vivida, objetos, plantas), sem logo, marca ou texto legível.
- Mãos naturais e, se der, as duas à vista; nada segurando produto de outra marca na frente.
- Olhar reto para a câmera e boca fechada. Legenda queimada só se não houver quadro sem ela.
- Enquadramento e luz que servem ao ad: o que fica do quadro é enquadramento, pose, luz e fundo.
- Nunca profissional de saúde real (jaleco, consultório) como base de médico ou enfermeira.

## 4. Registro
Uma linha por candidato em `01_refs/avatar_quadro/refs.md`: arquivo, plataforma, link do vídeo (com o tempo do quadro),
perfil, para qual personagem e o que pesa a favor ou contra. O link fica para o caso de precisar de outro quadro do mesmo vídeo.

## 5. Escolha do Fefo pela sala
Os candidatos entram na sala de revisão como etapa (skill `sala-de-revisao`), antes de qualquer crédito:
`reviewroom.py etapa <review.json> refs --ordem 1 --titulo "Referências reais" --status aguardando --nota "Escolher 1 por personagem" 01_refs/avatar_quadro/q*.png`.
Abra a sala na sessão e espere: ele escolhe com uma nota ("esse", "esse mas sem a janela") ou no chat. Só depois o
`03_personagens.md` (Nano Banana Pro com o quadro em `--ref`). O quadro escolhido e o avatar gerado lado a lado vão na etapa
`personagens`, para conferir que é **outra pessoa** (olhos, nariz e pele diferentes; cabelo e roupa não bastam).

## Uso do quadro
O quadro é referência de estrutura, não de pessoa: nunca a identidade, a voz ou o nome de quem está nele. Ele fica no
`01_refs` da batch e não vai para o cliente nem para o ad.
