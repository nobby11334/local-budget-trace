"""Import published Bunkyo FY2024 facts. Source PDFs must be downloaded first.
Usage: python scripts/import_bunkyo_parties.py /path/to/bunkyo-detail
PDF digit glyphs are missing Unicode maps: CID19..28 map to 0..9, CID15 to comma.
Validated against rendered PDF p11; keep original extracted headings for auditing.
"""
import sys,re,json,pathlib,hashlib,subprocess
root=pathlib.Path(sys.argv[1]); out=pathlib.Path('dist/transactions.json')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
subprocess.run(['pdftotext','-layout',str(root/'programs2024.pdf'),str(root/'programs2024.txt')],check=True)
tr={i:chr(i+29) for i in range(19,29)};tr.update({15:',',3:' '})
records=[];source='https://www.city.bunkyo.lg.jp/documents/11735/2seika.pdf'
for page,text in enumerate((root/'programs2024.txt').read_text().split('\f')[:47],1):
 for line in text.split('\n'):
  m=re.match(r'^\s*[０-９0-9]+\s+(.+?)【経費\s*([\d,]+)\s*円】',line.translate(tr))
  if not m or re.search(r'[A-Za-z\\]',m[1]):continue
  records.append(dict(id=f'program-{len(records)+1}',kind='program',name=m[1].strip(),amount=int(m[2].replace(',','')),party=None,page=page,url=source,sha256=sha(root/'programs2024.pdf'),evidence='主要施策の概要・見出しの「経費」',note='概要に掲載された個別施策の経費。掲載範囲には重複・内数があり、全件合算しません。契約先・支払先と統計科目の対応は未確認。'))
contracturl='https://www.city.bunkyo.lg.jp/b007/p007761.html'
for i,(n,a,p) in enumerate([
 ('文京シビックセンター清掃等業務委託',339691440,'文京建物管理事業協同組合'),
 ('文京シビックセンター警備及び駐車場管理業務委託',177936000,'株式会社全日本ガードシステム本社'),
 ('文京シビックセンター設備運転管理業務委託',482900000,'株式会社太平エンジニアリング'),
 ('文京シビックセンター中水・厨房排水除害設備保守業務委託',11864600,'三機アクテック株式会社')]):
 records.append(dict(id=f'contract-{i+1}',kind='contract',name=n,amount=a,party=p,url=contracturl,page=None,evidence='令和6年度優良日々履行型業務委託・案件名の行',note='優良委託として公表された4案件の契約金額。全契約一覧ではありません。支払実績・支払日・契約期間は未確認。'))
# All figures from the R6 column of each report's income table, not the current website directory's party names.
parties=['株式会社オーエンス','株式会社日本保育サービス','株式会社オーエンス','公益財団法人文京アカデミー','株式会社丹青社','文京区スポーツ推進共同事業体','株式会社東急コミュニティー','社会福祉法人武蔵野会','目白台運動公園共創パートナーズ','軽井沢フード株式会社','株式会社日本保育サービス','株式会社日本保育サービス']
names=['白山交流館外1施設','目白台交流館外1施設','勤労福祉会館','アカデミー文京外6施設','森鷗外記念館','文京総合体育館外6スポーツ施設','文京区営住宅等','文京福祉センター江戸川橋・湯島','目白台運動公園','少年自然の家八ケ岳高原学園','根津児童館・目白台第二児童館','千石児童館']
amounts=[26735070,30070600,28814150,85418804+147369522,97508528+3252294,433055397,27346440+230821726,191283858,61109000,62269350,59574244,41630322]
pages=[3,3,2,2,2,3,2,2,2,3,2,2]
components={3:[['響きの森文京公会堂等',85418804],['アカデミー文京等',147369522]],4:[['前金払',97508528],['概算払',3252294]],6:[['入居者管理費',27346440],['施設維持管理費',230821726]]}
urls=json.loads((root/'managers.json').read_text())
for i in range(12):
 note='2024年4月～2025年3月の受取側の指定管理料収入。振込記録・支払伝票は未確認。利用料金・自主事業収入は含みません。'
 if i==1:note+=' 一覧ページの管理者名（オーエンス）と評価PDF（日本保育サービス）が不一致。本画面は対象年度のPDFを採用。'
 if i==6:note+=' 区への指定管理料返還61,674,839円が別掲。収入額を純支出とは扱いません。'
 if i==4:note+=' 区への返金22,407円が別掲。収入額を純支出とは扱いません。'
 records.append(dict(id=f'receipt-{i+1}',kind='receipt',name=names[i]+'の管理運営',party=parties[i],amount=amounts[i],page=pages[i],url=urls[i][2],sha256=sha(root/f'manager{i+1}.pdf'),evidence='令和6年度実績・収支状況の収入欄 R6（管理者名称はPDF p.2）',components=components.get(i,[]),note=note))
assert len({r['id'] for r in records})==len(records)
assert all(isinstance(r['amount'],int) and r['amount']>=0 for r in records)
assert len([r for r in records if r['kind']=='contract'])==4
assert len([r for r in records if r['kind']=='receipt'])==12
out.write_text(json.dumps(dict(city='13105',year='2024',retrieved='2026-11-03',coverage='文京区の主要施策概要から抽出できた見出し、優良委託4案件、指定管理者評価12報告。全支出・全契約・全支払先の一覧ではありません。',records=records),ensure_ascii=False,separators=(',',':')))
print('Imported',len(records),'records;',len(records)-16,'program headings')
