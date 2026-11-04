"""Build additive expenditure trees from the MIC 2024 original tables.
Usage: primary-runtime python scripts/import_spending_tree.py <xlsx-directory>
Only complete, additive detail groups are linked. 'うち' subsets are excluded.
"""
import json,sys,pathlib,hashlib
import openpyxl
from openpyxl.utils import column_index_from_string as idx
src=pathlib.Path(sys.argv[1]);root=pathlib.Path(__file__).resolve().parents[1]
def node(label,col,children=None):return {'label':label,'cols':col.split(),'children':children or []}
def leaves(pairs):return [node(a,b) for a,b in pairs]
purpose=[node('議会費','Q'),node('総務費','R',leaves([('総務管理費','S'),('徴税費','T'),('戸籍住民基本台帳費','U'),('選挙費','V'),('統計調査費','W'),('監査委員費','X')])),node('民生費','Y',leaves([('社会福祉費','Z'),('老人福祉費','AA'),('児童福祉費','AB'),('生活保護費','AC'),('災害救助費','AD')])),node('衛生費','AE',leaves([('保健衛生費','AF'),('結核対策費','AG'),('保健所費','AH'),('清掃費','AI')])),node('労働費','AJ AK',leaves([('失業対策費','AJ'),('労働諸費','AK')])),node('農林水産業費','AL',leaves([('農業費','AM'),('畜産業費','AN'),('農地費','AO'),('林業費','AP'),('水産業費','AQ')])),node('商工費','AR'),node('土木費','AS',[*leaves([('土木管理費','AT'),('道路橋りょう費','AU'),('河川費','AV'),('港湾費','AW')]),node('都市計画費','BB',leaves([('街路費','AX'),('公園費','AY'),('下水道費','AZ'),('区画整理費等','BA')])),*leaves([('住宅費','BC'),('空港費','BD')])]),node('消防費','BE'),node('教育費','BF',[*leaves([('教育総務費','BG'),('小学校費','BH'),('中学校費','BI'),('高等学校費','BJ'),('特別支援学校費','BK'),('幼稚園費','BL'),('社会教育費','BM')]),node('保健体育費','BN BO',leaves([('体育施設費等','BN'),('学校給食費','BO')])),node('大学費','BP')]),node('災害復旧費','BQ',[node('農林水産施設','BR',leaves([('農地','BS'),('農業用施設','BT'),('林業用施設','BU'),('漁業用施設','BV'),('共同利用施設','BW'),('その他','BX')])),node('公共土木施設','BY',leaves([('河川','BZ'),('海岸','CA'),('道路','CB'),('港湾','CC'),('漁港','CD'),('下水道','CE'),('公園','CF'),('その他','CG')])),node('その他施設','CH',leaves([('公立学校','CI'),('公営住宅','CJ'),('社会福祉施設','CK'),('その他','CL')]))]),node('公債費','CM'),node('諸支出金','CN CO CP',leaves([('普通財産取得費','CN'),('公営企業費','CO'),('市町村たばこ税都道府県交付金','CP')])),node('前年度繰上充用金','CQ')]
nature=[node('人件費','Q',leaves([('議員報酬等','R'),('委員等報酬','S'),('市町村長等特別職の給与','AC'),('任期の定めのない常勤職員','AD'),('任期付職員','BC'),('暫定再任用職員','CB'),('会計年度任用職員（フルタイム）','DA'),('地方公務員共済組合等負担金','DS'),('退職金','DT'),('恩給及び退職年金','EA'),('災害補償費','EB'),('その他','EC')])),node('物件費','EF',leaves([('旅費','EG'),('交際費','EH'),('需用費','EI'),('役務費','EJ'),('備品購入費','EK'),('委託料','EL'),('その他','EM')])),node('維持補修費','EN'),node('扶助費','EO'),node('補助費等','EP',leaves([('負担金・寄附金','EQ'),('補助交付金','ES'),('その他','ET')])),node('普通建設事業費','EU',leaves([('補助事業費','EW'),('単独事業費','FB'),('国直轄事業負担金','FG'),('県営事業負担金','FH'),('同級他団体施行事業負担金','FI'),('受託事業費','FJ')])),node('災害復旧事業費','FL',leaves([('補助事業費','FN'),('単独事業費','FO'),('県営事業負担金','FP'),('同級他団体施行事業負担金','FQ'),('受託事業費','FR')])),node('失業対策事業費','FS',leaves([('補助事業費','FU'),('単独事業費','FV')])),node('公債費','FW',leaves([('地方債元利償還金','FX'),('一時借入金利子','FY')])),*leaves([('積立金','FZ'),('投資及び出資金','GA'),('貸付金','GB'),('繰出金','GC'),('前年度繰上充用金','GD')])]
schemas={'purpose':purpose,'nature':nature}
def allcols(nodes):return sorted({col for n in nodes for col in n['cols']}|{col for n in nodes for col in allcols(n['children'])},key=idx)
cols={k:allcols(nodes) for k,nodes in schemas.items()}
def money(v):
 if v in ('-',None,''):return 0
 if isinstance(v,(int,float)):return v
 raise ValueError(repr(v))
def value(n,raw):return sum(raw[c] for c in n['cols'])
checks=0

def validate(nodes,raw,code,kind):
 global checks
 for n in nodes:
  if n['children']:
   assert value(n,raw)==sum(value(c,raw) for c in n['children']),(code,kind,n['label'],value(n,raw),sum(value(c,raw) for c in n['children']))
   checks+=1;validate(n['children'],raw,code,kind)
base=json.loads((root/'dist/finance.json').read_text());cities={c['code']:{} for c in base['cities']};totals={c['code']:c['years']['2024']['official']['spendingTotal'] for c in base['cities']}
files=[]
for kind,names in [('purpose',['001061671','001061676']),('nature',['001061672','001061677'])]:
 for name in names:
  f=src/(name+'.xlsx');files.append({'url':'https://www.soumu.go.jp/main_content/'+f.name,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
  ws=openpyxl.load_workbook(f,read_only=True,data_only=True).active
  for rownum,r in enumerate(ws.iter_rows(values_only=True),1):
   code=str(r[14] or '')
   if len(code)!=6 or not code.isdigit():continue
   code=code[:5];raw={c:money(r[idx(c)-1]) for c in cols[kind]}
   assert sum(value(n,raw) for n in schemas[kind])==totals[code],(code,kind,'root')
   validate(schemas[kind],raw,code,kind);checks+=1
   cities[code][kind]=[raw[c] for c in cols[kind]]
assert len(cities)==1741 and all(set(c)=={'purpose','nature'} for c in cities.values())
out={'year':'2024','unit':'千円','schema':schemas,'columns':cols,'cities':cities,'validation':{'cities':1741,'parentChildEqualities':checks,'failed':0},'sources':files,'detailLimit':'全国共通の地方財政統計の細目まで。個別事業・契約・支払先の明細は未収録。','dashRule':'原表の「-」は金額集計上0として扱い、0円項目の表示で確認可能。'}
(root/'dist/spending-tree.json').write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')))
print('PASS',len(cities),'cities;',checks,'parent/child reconciliations;', (root/'dist/spending-tree.json').stat().st_size,'bytes')
