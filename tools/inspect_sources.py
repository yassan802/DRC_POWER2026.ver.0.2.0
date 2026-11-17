from pathlib import Path
import re, json, hashlib, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT.parent.parent/'DRC_POWER2026'

class Atom(str): pass
def parse(text):
    tokens=re.findall(r'"(?:\\.|[^"\\])*"|[^\s()]+|[()]',text)
    stack=[]; root=None
    for tok in tokens:
        if tok=='(':
            x=[]
            if stack: stack[-1].append(x)
            else: root=x
            stack.append(x)
        elif tok==')': stack.pop()
        else:
            stack[-1].append(json.loads(tok) if tok.startswith('"') else Atom(tok))
    return root
def kids(x,key): return [i for i in x if isinstance(i,list) and i and i[0]==key]
def one(x,key,default=None): return next(iter(kids(x,key)),default)
def val(x,key,default=''): return (one(x,key) or [None,default])[1]

if __name__=='__main__':
    out=[]
    for file in SOURCE.glob('*.kicad_sch'):
        if file.name=='Relay_24V.kicad_sch': continue
        s=file.read_text(encoding='utf-8'); tree=parse(s)
        out.append(f'\nFILE {file.name} git-blob '+hashlib.sha1(f'blob {len(s.encode())}\0'.encode()+s.encode()).hexdigest())
        for x in kids(tree,'symbol'):
            ps={i[1]:i[2] for i in kids(x,'property')}
            if ps.get('Reference','').startswith('#'): continue
            out.append(json.dumps({'ref':ps.get('Reference'),'value':ps.get('Value'),'lib':val(x,'lib_id'),'fp':ps.get('Footprint'),'at':one(x,'at')[1:]},ensure_ascii=False))
        for x in kids(tree,'sheet'):
            out.append('SHEET '+json.dumps({i[1]:i[2] for i in kids(x,'property')},ensure_ascii=False))
    text='\n'.join(out)
    (ROOT/'docs'/'original_inventory.txt').write_text(text,encoding='utf-8')
    print(text)
