"""Import the official Japan Dashboard CSV bundle. Usage: python scripts/import_finance.py <extracted-directory>. No inferred expenditure totals."""
import csv,json,sys,pathlib,collections,hashlib
src=pathlib.Path(sys.argv[1]); out=pathlib.Path(__file__).resolve().parents[1]/'dist'
def rows(name):
 with open(src/name,encoding='utf-8-sig',newline='') as f: yield from csv.DictReader(f)
def num(v):
 try:return float(v) if '.' in v else int(v)
 except:return None
cities={}
for r in rows('finance_data_table_master.csv'):
 c=cities.setdefault(r['市区町村コード'],{'code':r['市区町村コード'],'name':r['市区町村名'],'pref':r['都道府県名'],'years':{}})
 c['years'][r['年度']]={'population':num(r['人口数_人']),'group':r['類似団体区分'],'revenue':{},'indicators':{}}
for r in rows('finance_local_finance_data_table_flow.csv'):
 if r['分類']!='歳入':continue
 d=cities[r['市区町村コード']]['years'][r['年度']]['revenue'];k=r['大項目'];v=num(r['値_千円'])
 if v is None: raise ValueError('Missing revenue value')
 d[k]=d.get(k,0)+v
for r in rows('finance_data_table_indicators.csv'):
 cities[r['市区町村コード']]['years'][r['年度']]['indicators'][r['指標名']]=num(r['値'])
meta={'title':'Japan Dashboard 地方財政（市町村ごと）／デジタル庁・総務省','url':'https://www.digital.go.jp/resources/japandashboard/municipal-finance','download':'https://www.digital.go.jp/assets/contents/node/basic_page/field_ref_resources/be6dfce4-0c73-4296-b61f-eba37fc7284b/d40bb7e9/20260424_resources_municipal-finance.zip','published':'2026-04-24','retrieved':'2026-11-03','unit':'千円','coverage':'普通会計を中心とする地方財政状況調査の加工データ。最新の当初予算ではありません。','files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in src.glob('*.csv')},'caution':'歳出の目的別・性質別内訳の単純合計が一致しないレコードを検出したため、本試作では全国歳出データを掲載していません。原資料の集計範囲・項目対応の確認が必要です。'}
out.mkdir(exist_ok=True)
(out/'finance.json').write_text(json.dumps({'meta':meta,'cities':list(cities.values())},ensure_ascii=False,separators=(',',':')))
print('Imported',len(cities),'cities;',sum(len(c['years']) for c in cities.values()),'city-years')
