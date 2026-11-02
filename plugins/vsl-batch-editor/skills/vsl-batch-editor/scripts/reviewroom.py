#!/usr/bin/env python3
"""
reviewroom — builds a Review Room: one claude.ai Artifact page per batch of video edits, where the reviewer pins
notes to exact frames and ranges, draws on the picture, compares versions and approves each video. Claude reads
the notes back from the page's database. Skill: .claude/skills/review-room/SKILL.md.

    python3 tools/reviewroom.py build  <review.json>             # review copies + page + upload plan
    python3 tools/reviewroom.py commit <review.json>             # after the publish succeeded: remember what is live
    python3 tools/reviewroom.py record <review.json> <db_dir>    # static record.md + record.json at approval

Kit do Daniel (review-room-kit, 29/10/2026), adaptado: usa o ffmpeg do sistema e lê a timeline de <review.json>/timelines/.
Review.json da batch: `python3 sala.py "<batch>"`. Passo a passo: modulos/11_review_room.md.

review.json sits in its own folder (the build writes site/, publish_plan.json and published.json next to it):
{
  "title": "Spring launch · batch 3",          # shown on the page; also how you ask Claude for the notes
  "id": "spring-03",                           # short unique id, used for the page's remembered view
  "client": "Acme",                            # optional, shown in the breadcrumb
  "url": null,                                 # the Artifact URL, filled in after the first publish
  "videos": [
    {"id": "A", "concept": "Before / after",
     "hooks": [{"n": 1, "label": "Cold open", "ad_name": "spring-03 - Before After - Hook 1"}, ...],
     "versions": [
       {"v": 1, "date": "2026-10-12", "note": "First cut",
        "renders": {"1": {"9x16": "renders/A_v1_H1_9x16.mp4", "4x5": "renders/A_v1_H1_4x5.mp4"},
                    "2": {"9x16": "renders/A_v1_H2_9x16.mp4"}}}],
     "sections": [{"title": "QA", "lines": ["31 s · -14 LUFS · 2.1 s per shot"]}],
     "extras": ["Text-free masters in renders/notext/"]}
  ]
}
"Hooks" are variants of one video that share a body (different openings). A video with no variants has one hook.
Render paths are relative to review.json or absolute. Ratios: "9x16" and "4x5".

Optional timeline sidecar: <render>.timeline.json next to an mp4 adds the edit-structure and on-screen-text lanes
and lets an "all hooks" note land on the same moment of the body under hooks of different lengths:
  {"duration": 32.9, "segments": [{"seg": "hook", "start": 0, "end": 3.8}, {"seg": "body", "start": 3.8, "end": 28.5},
   {"seg": "close", "start": 28.5, "end": 32.9}],
   "text": [{"type": "caption", "text": "These photos", "start": 0, "end": 0.9}]}
Without it, everything still works; "all hooks" notes fall back to the same absolute time.

Size limits (claude.ai Artifacts): 15 MB per file, 64 MB / 255 files per publish, 256 MB / 511 files per version.
Review copies are 720 px wide (~3-4 MB for 40 s). Only the latest two versions of each video keep their files (the
compare view needs the previous one); older versions are retired with a null in the plan, and their notes stay.
"""
import sys, os, json, hashlib, subprocess, datetime, shutil

FF = shutil.which('ffmpeg') or 'ffmpeg'    # o ~/bin/ffmpeg entra na fila
HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, 'reviewroom', 'template.html')
KEEP_VERSIONS = 2
CHUNK_MB = 55
RATIOS = ('9x16', '4x5')


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f'ffmpeg failed: {" ".join(map(str, cmd[:6]))} ...\n{r.stderr[-1500:]}')


def duration(path):
    r = subprocess.run([FF, '-hide_banner', '-i', path], capture_output=True, text=True)
    for line in r.stderr.splitlines():
        if 'Duration:' in line:
            h, m, s = line.split('Duration:')[1].split(',')[0].strip().split(':')
            return int(h) * 3600 + int(m) * 60 + float(s)
    return 0.0


def sha(path):
    h = hashlib.sha1()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()[:16]


def review_copy(src, out):
    """720-wide H.264 for the browser. Re-encoded only when the source is newer than the copy."""
    if os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(src):
        return
    os.makedirs(os.path.dirname(out), exist_ok=True)
    # step down until it fits the 15 MB file cap; long cuts (3+ min) fall through to 540 px wide
    for w, crf, ab in ((720, 25, '128k'), (720, 29, '96k'), (720, 33, '96k'), (540, 30, '96k'), (540, 34, '80k')):
        run([FF, '-y', '-hide_banner', '-i', src, '-vf', f'scale={w}:-2', '-c:v', 'libx264', '-preset', 'medium', '-crf', str(crf),
             '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', ab, '-movflags', '+faststart', out])
        if os.path.getsize(out) <= 14.5e6:
            break


def poster(src, out):
    if os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(src):
        return
    run([FF, '-y', '-hide_banner', '-ss', '0.8', '-i', src, '-frames:v', '1', '-vf', 'scale=360:-2', '-q:v', '4', out])


def load(cfg_path):
    cfg_path = os.path.abspath(cfg_path)
    return json.load(open(cfg_path)), os.path.dirname(cfg_path)


def resolve(base, p):
    return p if os.path.isabs(p) else os.path.normpath(os.path.join(base, p))


def build(cfg_path):
    cfg, base = load(cfg_path)
    site = os.path.join(base, 'site')
    state_p = os.path.join(base, 'published.json')
    state = json.load(open(state_p)) if os.path.exists(state_p) else {'files': {}}
    want, videos, problems = {}, [], []

    for vd in cfg['videos']:
        vers = sorted(vd['versions'], key=lambda x: x['v'])
        live = {x['v'] for x in vers[-KEEP_VERSIONS:]}
        mv = {'id': vd['id'], 'concept': vd.get('concept', ''), 'hooks': vd['hooks'], 'extras': vd.get('extras', []),
              'sections': vd.get('sections', []), 'versions': []}
        for ver in vers:
            entry = {'v': ver['v'], 'date': ver.get('date', ''), 'note': ver.get('note', ''), 'available': ver['v'] in live,
                     'media': {}, 'masters': {}}
            for hk, ratios in ver.get('renders', {}).items():
                for ratio, path in ratios.items():
                    if ratio not in RATIOS:
                        problems.append(f'unknown ratio {ratio} (use 9x16 or 4x5)'); continue
                    src = resolve(base, path)
                    if not os.path.exists(src):
                        problems.append(f'missing render: {path}'); continue
                    entry['masters'].setdefault(str(hk), {})[ratio] = path
                    if ver['v'] not in live:
                        continue
                    rel = f"media/{vd['id']}/v{ver['v']}/H{hk}_{ratio}"
                    review_copy(src, os.path.join(site, rel + '.mp4'))
                    poster(os.path.join(site, rel + '.mp4'), os.path.join(site, rel + '.jpg'))
                    side = os.path.join(base, 'timelines', f"v{ver['v']}_{os.path.basename(src)[:-4]}.timeline.json")
                    tl = json.load(open(side)) if os.path.exists(side) else {}
                    entry['media'].setdefault(str(hk), {})[ratio] = {
                        'src': rel + '.mp4', 'poster': rel + '.jpg', 'duration': tl.get('duration') or round(duration(src), 3),
                        'segments': tl.get('segments', []), 'text': tl.get('text', [])}
                    for ext in ('.mp4', '.jpg'):
                        want[rel + ext] = os.path.join(site, rel + ext)
            mv['versions'].append(entry)
        videos.append(mv)

    manifest = {'title': cfg['title'], 'id': cfg.get('id') or cfg['title'], 'client': cfg.get('client', ''),
                'fps': cfg.get('fps', 30), 'built': datetime.datetime.now().isoformat(timespec='seconds'), 'videos': videos}
    html = open(TEMPLATE).read()
    html = html.replace('__TITLE__', cfg['title'] + ' Review').replace('__MANIFEST__', json.dumps(manifest).replace('</', '<\\/'))
    os.makedirs(site, exist_ok=True)
    open(os.path.join(site, 'index.html'), 'w').write(html)

    changed = {k: v for k, v in want.items() if state['files'].get(k) != sha(v)}
    retired = [k for k in state['files'] if k not in want]
    chunks, cur, size = [], {}, 0
    for k, v in sorted(changed.items()):
        s = os.path.getsize(v)
        if s > 15e6:
            problems.append(f'over 15 MB, cannot publish: {k}'); continue
        if cur and (size + s > CHUNK_MB * 1e6 or len(cur) >= 250):
            chunks.append(cur); cur, size = {}, 0
        cur[k] = v; size += s
    if cur or retired or not chunks:
        chunks.append(cur)
    for k in retired:
        chunks[-1][k] = None
    total = sum(os.path.getsize(v) for v in want.values())
    plan = {'page': os.path.join(site, 'index.html'), 'url': cfg.get('url'), 'publishes': chunks,
            'live_total_mb': round(total / 1e6, 1), 'live_files': len(want), 'want': {k: sha(v) for k, v in want.items()}}
    json.dump(plan, open(os.path.join(base, 'publish_plan.json'), 'w'), indent=1)
    print(f"page     {plan['page']}")
    print(f"live     {len(want)} files, {plan['live_total_mb']} MB (cap 256 MB / 511 files per version)")
    print(f"publish  {len(chunks)} call(s): " + ', '.join(f"{sum(1 for x in c.values() if x)} files" for c in chunks))
    if total > 240e6:
        problems.append(f'live total {total/1e6:.0f} MB is near the 256 MB cap: split the batch into two rooms')
    for p in problems:
        print('  !', p)


def commit(cfg_path):
    cfg, base = load(cfg_path)
    plan = json.load(open(os.path.join(base, 'publish_plan.json')))
    json.dump({'files': plan['want'], 'committed': datetime.datetime.now().isoformat(timespec='seconds')},
              open(os.path.join(base, 'published.json'), 'w'), indent=1)
    print(f"committed {len(plan['want'])} live files")


def fmt(t):
    if t is None:
        return ''
    m = int(t // 60)
    return f'{m:02d}:{t - m * 60:05.2f}'


def record(cfg_path, db_dir):
    """Static record of the review, written at approval. db_dir holds notes/*.json and approvals/*.json
    (an ArtifactData list with out_dir)."""
    cfg, base = load(cfg_path)
    def rd(c):
        d = os.path.join(db_dir, c)
        return [json.load(open(os.path.join(d, f))) for f in sorted(os.listdir(d))] if os.path.isdir(d) else []
    unwrap = lambda d: d.get('data', d) if isinstance(d, dict) else d
    notes = [unwrap(n) for n in rd('notes')]
    approvals = {f"{a['video']}_H{a['hook']}": a for a in map(unwrap, rd('approvals'))}
    today = datetime.date.today().isoformat()
    lines = [f"# {cfg['title']} — review record", '', f"Review Room: {cfg.get('url') or '(not published)'}  ",
             f"Written {today}. A static file: what was approved and what was asked for.", '']
    out = {'title': cfg['title'], 'url': cfg.get('url'), 'written': today, 'videos': [], 'notes': notes}
    for vd in cfg['videos']:
        vers = {x['v']: x for x in vd['versions']}
        last = max(vers)
        lines += [f"## Video {vd['id']}" + (f" — {vd['concept']}" if vd.get('concept') else ''), '',
                  '| Hook | Ad name | Approved | Files |', '|---|---|---|---|']
        for h in vd['hooks']:
            a = approvals.get(f"{vd['id']}_H{h['n']}")
            ver = vers.get(a['version']) if a else vers[last]
            files = list(ver.get('renders', {}).get(str(h['n']), {}).values())
            lines.append(f"| H{h['n']} {h.get('label', '')} | `{h.get('ad_name', '')}` | "
                         f"{'v%s · %s' % (a['version'], a['at'][:10]) if a else 'not approved'} | {'<br>'.join(files)} |")
            out['videos'].append({'video': vd['id'], 'hook': h['n'], 'ad_name': h.get('ad_name'),
                                  'approved_version': a and a['version'], 'approved_at': a and a['at'], 'files': files})
        lines += ['', 'Versions:', ''] + [f"- v{x['v']} ({x.get('date', '')}): {x.get('note', '')}" for x in sorted(vers.values(), key=lambda x: x['v'])] + ['']
        vn = sorted([n for n in notes if n.get('video') == vd['id']], key=lambda n: (n.get('version', 0), n.get('t', 0)))
        if vn:
            lines += ['Notes:', '']
            for n in vn:
                rng = fmt(n.get('t')) + (f"–{fmt(n.get('t2'))}" if n.get('t2') is not None else '')
                lines.append(f"- v{n.get('version')} H{n.get('hook')}{' (all hooks)' if n.get('all_hooks') else ''} {n.get('ratio', '')} @ {rng} "
                             f"[{n.get('tag')}] {n.get('text')} — **{n.get('status')}**" + (f", fixed in v{n['fixed_in']}" if n.get('fixed_in') else ''))
                for r in n.get('replies', []):
                    lines.append(f"  - {'Claude' if r.get('by') == 'claude' else 'Reviewer'}: {r.get('text')}")
            lines.append('')
    open(os.path.join(base, 'record.md'), 'w').write('\n'.join(lines))
    json.dump(out, open(os.path.join(base, 'record.json'), 'w'), indent=1)
    print(f"wrote record.md and record.json ({len(out['videos'])} videos, "
          f"{sum(1 for a in out['videos'] if a['approved_version'])} approved, {len(notes)} notes)")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd == 'build': build(sys.argv[2])
    elif cmd == 'commit': commit(sys.argv[2])
    elif cmd == 'record' and len(sys.argv) > 3: record(sys.argv[2], sys.argv[3])
    else: sys.exit(__doc__)
