// Rodar com mcp__Claude_Browser__javascript_tool numa aba do app.milanote.com (qualquer página do Milanote logado).
// Troque __URL__ pelo link do briefing (ex.: https://app.milanote.com/1X8mvX1OG5G36M?p=Z7DM0jMbiXe).
// O canvas só desenha o que está na tela; por isso o quadro é lido pela API do próprio app.
const URL_BRIEF = '__URL__';
const u = new URL(URL_BRIEF);
const boardId = u.pathname.split('/').filter(Boolean)[0];
const p = u.searchParams.get('p') || '';
const tj = await (await fetch(`/api/permissions/token/?ids=${p}&elementIds=${boardId}`, { credentials: 'include' })).json();
const j = await (await fetch(`/api/boards?loadAncestors=true&tokens=${encodeURIComponent(tj.token)}&ids=${boardId}`, { credentials: 'include' })).json();
const els = j.elements || {};

// Texto de um card: formato ProseMirror (type/content) ou Draft.js (blocks).
const pm = nd => !nd ? '' : (nd.text || '') + (nd.content || []).map(pm).join('') + (['paragraph', 'heading', 'listItem', 'taskItem'].includes(nd.type) ? '\n' : '');
const txt = c => { if (!c) return ''; if (c.blocks) return c.blocks.map(b => b.text).join('\n'); return pm(c); };
const clean = s => s.replace(/\n{2,}/g, '\n').trim();
const all = Object.values(els);
const kids = id => all.filter(x => x.location?.parentId === id);
const col = re => all.find(x => x.elementType === 'COLUMN' && x.location?.parentId === boardId && re.test(x.content?.title || ''));
const colTxt = re => { const c = col(re); return c ? kids(c.id).map(x => clean(txt(x.content?.textContent))).filter(Boolean) : []; };
const tasks = re => { const c = col(re); if (!c) return []; return kids(c.id).flatMap(tl => kids(tl.id)).map(t => (t.content?.isComplete ? '[x] ' : '[ ] ') + clean(txt(t.content?.textContent))); };
const links = re => { const c = col(re); if (!c) return []; return kids(c.id).filter(x => x.elementType === 'LINK').map(x => x.content?.link?.url || x.content?.url || ''); };

// Hooks: textos soltos no canvas logo abaixo das colunas HOOK 1/2/3 (mesmo x, y maior).
const hooks = [1, 2, 3].map(k => {
  const c = col(new RegExp(`HOOK ${k}\\b`));
  if (!c) return null;
  const cx = c.location.position.x, cy = c.location.position.y;
  const cand = all.filter(x => x.elementType === 'CARD' && x.location?.parentId === boardId && x.location.position
    && Math.abs(x.location.position.x - cx) < 12 && x.location.position.y > cy && x.location.position.y < cy + 60)
    .map(x => clean(txt(x.content?.textContent))).filter(s => s && !/Goes Here/i.test(s));
  return { hook: k, texto: cand.join(' / '), visual: kids(c.id).map(x => clean(txt(x.content?.textContent))).join(' ') };
});

// Hold: card "Entire Hold Copy" (tira as 3 linhas do modelo).
const holdCard = all.find(x => /Entire Hold Copy/.test(txt(x.content?.textContent)));
const hold = holdCard ? clean(txt(holdCard.content.textContent)).split('\n')
  .filter(l => !/^Entire Hold Copy$|^All copy for the hold goes here$|^this is line #1/i.test(l.trim())) : [];

// Ad de referência: links dentro das colunas AD EXAMPLE, ou qualquer LINK do quadro.
const adLinks = [...links(/AD EXAMPLE 1/), ...links(/AD EXAMPLE 2/)];
const outrosLinks = all.filter(x => x.elementType === 'LINK' && !adLinks.includes(x.content?.link?.url)).map(x => x.content?.link?.url || '');

JSON.stringify({
  quadro: els[boardId]?.content?.title,
  cliente: colTxt(/CLIENT'S NAME/),
  dct: colTxt(/DCT NUMBER/),
  conceito: colTxt(/IDEATION AD CONCEPT/),
  ad_links_to: colTxt(/AD LINKS TO/),
  tipo: tasks(/TYPE OF AD/),
  tamanhos: tasks(/SIZES NEEDED/),
  variacoes: colTxt(/VARIATIONS NEEDED/),
  hooks,
  hold,
  cta: colTxt(/^CTA$/),
  ad_exemplo: adLinks,
  outros_links: outrosLinks,
}, null, 1);
