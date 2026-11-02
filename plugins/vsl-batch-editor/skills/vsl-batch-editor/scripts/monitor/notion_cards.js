// Rodar com mcp__Claude_Browser__javascript_tool numa aba aberta no board do Notion (view "By Status"):
// https://app.notion.com/p/1b203cdd345080d9b49ad36d57789ce5?v=1b203cdd3450819c87ef000c92a3b9d1
// Rola o board até o fim (cada coluna só mostra 25 cards antes disso) e devolve, por coluna,
// quantos cards ela tem e quais estão atribuídos a RESP (notion.responsavel do perfil; troque antes de rodar).
// Igual ao notion_cards_fefo.js, que fica como está porque o monitor do Fefo lê a chave "fefo".
const RESP = 'fefo';
await new Promise(r => setTimeout(r, 3000));
const scs = [...document.querySelectorAll('.notion-scroller')].filter(e => e.scrollHeight > e.clientHeight + 50);
for (let k = 0; k < 4; k++) { scs.forEach(s => s.scrollTop = s.scrollHeight); await new Promise(r => setTimeout(r, 2000)); }

// Títulos das colunas ficam fora dos grupos; casam com o grupo pela posição x.
const heads = [];
const w = document.createTreeWalker(document.querySelector('main'), NodeFilter.SHOW_TEXT);
let n;
while ((n = w.nextNode())) {
  const s = n.textContent.trim();
  if (!s || s.length > 40 || n.parentElement.closest('a') || n.parentElement.closest('.notion-board-group')) continue;
  if (/^(Not started [A-Za-z]+|Started|Revisions|Designing\/Editing|For Approval|Done|Ready to launch)$/.test(s)) {
    heads.push({ s, x: n.parentElement.getBoundingClientRect().x });
  }
}
const out = {};
for (const g of document.querySelectorAll('.notion-board-group')) {
  const gx = g.getBoundingClientRect().x;
  const h = heads.find(h => h.x >= gx - 5 && h.x < gx + 280);
  const col = h ? h.s : '?';
  const cards = [...g.querySelectorAll('a[href]')].filter(a => /BATCH/i.test(a.innerText));
  out[col] = {
    total: cards.length,
    meus: cards
      .filter(a => a.innerText.split('\n').some(l => l.trim().toLowerCase() === RESP.toLowerCase()))
      .map(a => ({ titulo: a.innerText.split('\n')[0].trim(), url: a.href.split('?')[0], id: a.href.split('?')[0].slice(-32) })),
  };
}
JSON.stringify(out, null, 1);
