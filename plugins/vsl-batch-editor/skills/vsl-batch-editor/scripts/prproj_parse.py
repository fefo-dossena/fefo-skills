#!/usr/bin/env python3
"""Lê um .prproj (descompactado com gunzip) e lista todos os clipes de todas as sequências.
Uso: gunzip -c projeto.prproj > p.xml && python3 prproj_parse.py p.xml saida.json"""
import xml.etree.ElementTree as ET, sys, json
TPS=254016000000
r=ET.parse(sys.argv[1]).getroot()
ids={}
for el in r:
    for k in ('ObjectID','ObjectUID'):
        if el.get(k): ids[el.get(k)]=el
def ref(e):
    if e is None: return None
    k=e.get('ObjectRef') or e.get('ObjectURef'); return ids.get(k)
def txt(el,path):
    x=el.find(path); return x.text if x is not None else None
def media_name(clip):
    # clip: VideoClip/AudioClip
    src=ref(clip.find('.//Source'))
    if src is None: return None
    m=ref(src.find('.//MediaSource/Media'))
    if m is None: m=ref(src.find('.//Media'))
    if m is None: return None
    return txt(m,'Title') or (txt(m,'FilePath') or '').split('/')[-1]
out=[]
for seq in [e for e in r if e.tag=='Sequence']:
    name=txt(seq,'Name')
    for tg in seq.iter('TrackGroup'):
        g=ref(tg.find('Second'))
        if g is None: continue
        for t in g.iter('Track'):
            tr=ref(t)
            if tr is None: continue
            kind=tr.tag; idx=t.get('Index')
            for ci in tr.iter('TrackItem'):
                it=ref(ci)
                if it is None or 'ClipTrackItem' not in it.tag: continue
                ti=it.find('.//TrackItem')
                if ti is None or ti.find('End') is None: continue   # Start ausente = clipe em 0 (Premiere omite)
                s=int(txt(ti,'Start') or 0); e_=int(txt(ti,'End') or 0)
                sc=ref(it.find('.//SubClip'))
                clip=ref(sc.find('Clip')) if sc is not None else None
                ip=op=None; mn=None
                if clip is not None:
                    c=clip.find('.//InPoint/..')
                    if c is None: c=clip
                    ip=c.find('InPoint'); op=c.find('OutPoint')
                    ip=int(ip.text)/TPS if ip is not None else None
                    op=int(op.text)/TPS if op is not None else None
                    mn=media_name(clip)
                out.append(dict(seq=name,track=f"{kind}{idx}",kind=it.tag,start=s/TPS,end=e_/TPS,src=mn,inp=ip,outp=op))
json.dump(out,open(sys.argv[2],'w'),indent=0)
print(len(out))
