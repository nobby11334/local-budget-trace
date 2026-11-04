"""Read official MIC tables, validate independent totals, and enrich the 2024 snapshot.
Run with the primary Python runtime: scripts/import_official_2024.py <source-dir>
No values are inferred from old positional mappings.
"""
import json,sys,pathlib,re,hashlib
import openpyxl
from openpyxl.utils import column_index_from_string as idx
root=pathlib.Path(__file__).resolve().parents[1];src=pathlib.Path(sys.argv[1]);path=root/'dist/finance.json'
db=json.loads(path.read_text());cities={c['code']:c for c in db['cities']}
URL='https://www.soumu.go.jp/iken/zaisei/r06_shichouson.html'
def read(n):
 ws=openpyxl.load_workbook(src/(n+'.xlsx'),read_only=True,data_only=True).active
 return {str(r[14])[:5]:(i,r) for i,r in enumerate(ws.iter_rows(values_only=True),1) if len(str(r[14] or ''))==6 and str(r[14]).isdigit()}
def number(v):
 if v in ('-',None,''):return 0
 if isinstance(v,(int,float)):return v
 raise ValueError(f'Unexpected number {v!r}')
def cell(r,c):return number(r[idx(c)-1])
def fields(r,mapping):return {k:sum(cell(r,c) for c in cols.split()) for k,cols in mapping.items()}
purpose={'議会費':'Q','総務費':'R','民生費':'Y','衛生費':'AE','労働費':'AJ AK','農林水産業費':'AL','商工費':'AR','土木費':'AS','消防費':'BE','教育費':'BF','災害復旧費':'BQ','公債費':'CM','諸支出金':'CN CO CP','前年度繰上充用金':'CQ'}
nature={'人件費':'Q','物件費':'EF','維持補修費':'EN','扶助費':'EO','補助費等':'EP','普通建設事業費':'EU','災害復旧事業費':'FL','失業対策事業費':'FS','公債費':'FW','積立金':'FZ','投資及び出資金':'GA','貸付金':'GB','繰出金':'GC','前年度繰上充用金':'GD'}
revenue={'地方税':'Q','地方譲与税':'X','地方税関連交付金':'Y Z AA AB AC AD AE AF AG AH','地方特例交付金等':'AI','地方交付税':'AM','交通安全対策特別交付金':'AQ','分担金及び負担金':'AR','使用料':'AU','手数料':'BB','国庫支出金':'BE','国有提供施設等所在市町村助成交付金':'BZ','都道府県支出金':'CA','財産収入':'CS','寄附金':'CV','繰入金':'CZ','繰越金':'DA','諸収入':'DD','地方債':'DL','特別区財政調整交付金':'DM'}
seen=set();checks=[]
for names in [('001061669','001061670','001061671','001061672'),('001061674','001061675','001061676','001061677')]:
 tables=[read(n) for n in names]
 assert all(set(t)==set(tables[0]) for t in tables)
 for code,(sr,r) in tables[0].items():
  if code not in cities:raise ValueError(f'Unknown city {code}')
  assert cities[code]['name'].replace('ヶ','ケ').replace('檮','梼')==str(r[15]).replace('ヶ','ケ').replace('檮','梼'),(code,cities[code]['name'],r[15])
  income=cell(r,'AN');spend=cell(r,'AO');p=fields(tables[2][code][1],purpose);n=fields(tables[3][code][1],nature);rev=fields(tables[1][code][1],revenue)
  assert sum(p.values())==spend,(code,'purpose',sum(p.values()),spend)
  assert sum(n.values())==spend,(code,'nature',sum(n.values()),spend)
  assert abs(sum(rev.values())-income)<=1,(code,'revenue',sum(rev.values()),income)
  d=cities[code]['years']['2024'];d['revenue']=rev;d['spending']=p;d['spendingNature']=n
  d['official']={'revenueTotal':income,'revenueRoundingDifference':income-sum(rev.values()),'spendingTotal':spend,'formalBalance':income-spend,'carryoverFunds':cell(r,'AQ'),'realBalance':cell(r,'AR'),'source':URL,'tables':{kind:{'url':'https://www.soumu.go.jp/main_content/'+file+'.xlsx','row':table[code][0]} for kind,file,table in zip(['summary','revenue','purpose','nature'],names,tables)},'validated':True}
  for key,col,percent in [('経常収支比率','AD',True),('実質公債費比率','AL',True),('将来負担比率','AM',True),('財政力指数','AI',False)]:
   v=r[idx(col)-1]
   d['indicators'][key]=number(v)/(100 if percent else 1) if isinstance(v,(int,float)) else None
  d['indicators']['実質収支']=cell(r,'AR');d['official']['precision']='原表の百分率を保持。対象外・記載なしはnull。'
  seen.add(code)
assert len(seen)==1741 and set(cities)==seen
files={p.name:{'url':'https://www.soumu.go.jp/main_content/'+p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(src.glob('*.xlsx'))}
db['meta']['official2024']={'title':'総務省 令和6年度市町村別決算状況調','url':URL,'retrieved':'2026-11-03','unit':'千円','coverage':1741,'checks':'全1,741団体で目的別歳出＝性質別歳出＝歳出総額を確認。歳入内訳は1団体で1千円差。','files':files}
db['meta']['caution']='2024年度は加工CSVの項目と元表の対応ずれを検出したため、総務省原表から歳入・歳出・指標を再取込。原表の総額と全団体照合済み。2020～2023年度は従来の加工CSVを使用し、歳出は未収録。'
path.write_text(json.dumps(db,ensure_ascii=False,separators=(',',':')))
rounding=[{'code':c['code'],'name':c['name'],'differenceThousandYen':c['years']['2024']['official']['revenueRoundingDifference']} for c in db['cities'] if c['years']['2024']['official']['revenueRoundingDifference']]
(root/'dist/validation.json').write_text(json.dumps({'date':'2026-11-03','year':'2024','cities':len(seen),'passed':len(seen)*3,'failed':0,'exactMatches':len(seen)*3-len(rounding),'withinOneThousandYen':len(rounding),'rounding':rounding,'checks':['歳入の内訳合計と概況の総額（1千円差以内を明示）','目的別歳出合計＝概況の歳出総額','性質別歳出合計＝概況の歳出総額'],'source':URL,'limitations':['金額整合性の検査であり政策効果の検証ではない','国と自治体の資金移転全件照合ではない','2020～2023年度の原表再照合は未実施']},ensure_ascii=False,indent=2))
print(f'PASS: {len(seen)*3-len(rounding)} exact reconciliations; {len(rounding)} disclosed one-thousand-yen difference; 0 failures.')
