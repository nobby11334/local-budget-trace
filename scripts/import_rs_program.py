"""Extract one nationally reviewed grant from official RS CSV; never sum headers and details."""
import csv,json,pathlib,sys,hashlib,urllib.parse
src=pathlib.Path(sys.argv[1]);root=pathlib.Path(__file__).resolve().parents[1];target='7629';sources={}
def rows(prefix):
 f=next(src.glob(prefix+'*.csv'));sources[prefix]={'filename':f.name,'url':'https://rssystem.go.jp/files/2025/rs/'+urllib.parse.quote(f.stem+'.zip'),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
 with open(f,encoding='utf-8-sig',newline='') as s:
  return [(i,r) for i,r in enumerate(csv.DictReader(s),2) if r['予算事業ID']==target]
def num(v):return int(v.strip()) if v.strip() else None
basic=rows('1-2_');assert len(basic)==1
summaries=[]
for i,r in rows('2-1_'):
 if r['予算年度'] not in ('2024','2023') or not r['計（歳出予算現額合計）']:continue
 summaries.append({'fiscalYear':r['予算年度'],'budget':num(r['計（歳出予算現額合計）']),'execution':num(r['執行額（合計）']),'carryover':num(r['翌年度への繰越し(合計）']),'record':i})
blocks=[];recipients=[]
for i,r in rows('5-1_'):
 if r['ブロックの合計支出額'].strip():blocks.append({'block':r['支出先ブロック番号'],'name':r['支出先ブロック名'],'count':num(r['支出先の数']),'amount':num(r['ブロックの合計支出額']),'role':r['事業を行う上での役割'],'record':i})
 if r['支出先ブロック番号']=='B' and r['支出先の合計支出額'].strip():recipients.append({'name':r['支出先名'],'corporateNumber':r['法人番号'].strip(),'amount':num(r['支出先の合計支出額']),'other':r['その他支出先']=='TRUE','record':i})
b=next(b for b in blocks if b['block']=='B');ex=next(v for v in summaries if v['fiscalYear']=='2024')['execution']
assert sum(r['amount'] for r in recipients)==b['amount']==ex
out={'id':target,'name':basic[0][1]['事業名'],'ministry':basic[0][1]['府省庁'],'office':basic[0][1]['課'],'sheetYear':'2025','executionYear':'2024','retrieved':'2026-11-03','unit':'円','downloadPage':'https://rssystem.go.jp/download-csv/2025','summary':summaries,'blocks':blocks,'recipients':recipients,'sources':sources,'matching':'国側CSVと自治体の公表資料を制度名で照合。自治体別交付決定額と国側記録の全件突合は未実施。県名で掲載された金額を県単体又は県内全市町村への配分と断定しない。','validation':'Bブロック合計＝支出先合計（その他を含む）＝2024年度執行額。ブロックAの移替額は合算しない。'}
(root/'dist/national.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print('PASS: RS program 7629; B block recipients reconciled to 2024 execution; records',len(recipients))
