"""Import FY2024 general-account hierarchy from Bunkyo original PDF.
Usage: python scripts/import_bunkyo_ledger.py /path/to/2seika.pdf
The PDF repeats a spread in two shifted text layers; retain the first layer
and one instance per spread. Physical page anchors preserve visible source.
"""
import pdfplumber,json,pathlib,sys,tempfile
source_pdf=pathlib.Path(sys.argv[1]);p=pdfplumber.open(source_pdf)
out=[]
for n in range(139,270,2):
 q=p.pages[n];s=''.join(c['text'] for c in q.chars);k=s.find(s[:40],40)
 assert k>0,n
 ids=set(map(id,q.chars[:k]));f=q.filter(lambda o:o['object_type']!='char' or id(o) in ids)
 # First of two page instances in each spread; ignore content outside this visible page.
 # left page x0 positive, right side x0 > page width; here first stream holds both pages.
 t=f.extract_text(x_tolerance=2,y_tolerance=2)
 out.append({'page':n+1,'text':t,'lines':[{'text':x['text'],'x':round(x['x0'],2)} for x in f.extract_text_lines(x_tolerance=2,y_tolerance=2)]})

import json,re,unicodedata,hashlib,pathlib,collections
pages=out;roots=[];stack=[];issues=[];seq=0
num=r'([\d,]+)';header=re.compile(r'^\d+ (.+?) '+num+' '+num+' '+num+' '+num+r' (\d+\.\d+)$');business=re.compile('^'+num+' '+num+' '+num+' '+num+r' (\d+\.\d+) \d+ (.+?) '+num+'$');sub=re.compile(r'^\(\s*\d+\)\s*(.+?)\s+([\d,]+)\s*円?$')
def yen(x):return int(x.replace(',',''))
def add(name,a,level,page,budget=None):
 global seq
 seq+=1;n=dict(id=f'b{seq}',label=name,amount=a,level=level,page=page,children=[])
 if budget is not None:n['budget']=budget
 while stack and stack[-1]['level']>=level:stack.pop()
 if level==0:roots.append(n)
 elif stack and stack[-1]['level']==level-1:stack[-1]['children'].append(n)
 else:issues.append(['orphan',page,name,level]);return
 stack.append(n)
for p in pages:
 for line in p['lines']:
  t=unicodedata.normalize('NFKC',line['text']);m=header.match(t)
  if m:
   x=line['x'];level=0 if x<130 else 1 if x<144 else 2
   add(m[1],yen(m[4]),level,p['page'],yen(m[2]));continue
  m=business.match(t)
  if m:
   if yen(m[3])!=yen(m[7]):issues.append(['unequal',p['page'],t]);continue
   add(m[6],yen(m[7]),3,p['page']+1,yen(m[1]));continue
  m=sub.match(t)
  if m and line['x']>650:add(m[1].strip(),yen(m[2]),4,p['page']+1)
# Wrapped sub-item on printed/PDF p.143, verified against source lines.
wrapped=next(n for n in roots[1]['children'][0]['children'][0]['children'] if n['label']=='外国人学校児童・生徒保護者負担軽減補助')
seq+=1
wrapped['children'].append(dict(id=f'b{seq}',label='文京区における小学校就学前の子どもを対象とした各種学校の利用支援事業',amount=1098000,level=4,page=143,children=[]))
checks=collections.Counter();bad=[]
def walk(n):
 if n['children']:
  delta=n['amount']-sum(c['amount'] for c in n['children']);n['difference']=delta
  n['coverage']='complete' if delta==0 else 'partial' if delta>0 else 'overlap';checks[n['coverage']]+=1
  if delta!=0:bad.append([n['id'],n['label'],n['amount'],delta,n['page']])
 for c in n['children']:walk(c)
for n in roots:walk(n)
meta=dict(city='13105',year='2024',account='一般会計',url='https://www.city.bunkyo.lg.jp/documents/11735/2seika.pdf',sha256=hashlib.sha256(source_pdf.read_bytes()).hexdigest(),total=135937867776,sourcePages=[140,271],counts=dict(checks),nodes=seq,issues=issues,roots=roots)
assert sum(n['amount'] for n in roots)==meta['total']
assert len(roots)==12 and seq==1654 and not issues
assert checks=={'complete':367},dict(checks)
pathlib.Path('dist/bunkyo-ledger.json').write_text(json.dumps(meta,ensure_ascii=False,separators=(',',':')))
print('Nodes',seq,'checks',checks,'issues',issues[:10]);print('Top',[(n['label'],n['amount']) for n in roots]);print('sum',sum(n['amount'] for n in roots));print('gaps',bad[:30])
