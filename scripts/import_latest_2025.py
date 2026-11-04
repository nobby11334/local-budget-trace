"""FY2025 provisional releases. Keep source precision, missing symbols and coverage explicit."""
import hashlib
import io
import json
import math
from pathlib import Path
import re
import unicodedata
import openpyxl

HEALTH = dict(id='health2025', year='2025', published='2026-09-29', page='https://www.soumu.go.jp/menu_news/s-news/01zaisei07_02000460.html', url='https://www.soumu.go.jp/main_content/001092921.xlsx', label='総務省・令和7年度健全化判断比率（速報）')
BASIC = [
 dict(id='osaka2025', pref='大阪府', count=41, unit=1000000, published='2026-09-29', page='https://www.pref.osaka.lg.jp/o040050/shichoson/zaiseijoukyo/zaiseimieruka.html', url='https://www.pref.osaka.lg.jp/documents/27710/7futsuukaikei_kessannjyoukyou.xlsx', label='大阪府・令和7年度市町村別普通会計決算状況（速報）'),
 dict(id='fukuoka2025', pref='福岡県', count=60, unit=1000, published='2026-09-30', page='https://www.pref.fukuoka.lg.jp/contents/07kessan.html', url='https://www.pref.fukuoka.lg.jp/uploaded/attachment/298412.xlsx', label='福岡県・令和7年度普通会計決算（速報）'),
]

def norm(v):
    # Explicit old/new glyph equivalence; never fuzzy-match municipalities.
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC',str(v or ''))).replace('梼','檮')

def number(v, symbol=False):
    if symbol and norm(v) in ('-','−','―','ー'):
        return '-'
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):
        raise ValueError('Unexpected numeric cell: '+repr(v))
    return round(v,6)

def parse_health(blob, cities):
    lookup={(norm(c['pref']),norm(c['name'])):c['code'] for c in cities}
    ws=openpyxl.load_workbook(io.BytesIO(blob),data_only=True)['1(2)']
    if norm(ws.cell(3,3).value) != '(2)市区町村(政令市を含む)' or norm(ws.cell(5,10).value) != '実質公債費比率':
        raise ValueError('Health table schema changed')
    records={}
    for rowno,row in enumerate(ws.values,1):
        key=(norm(row[2]),norm(row[3]))
        if key not in lookup:
            if key[0] in {norm(c['pref']) for c in cities} and row[3]:
                raise ValueError('Unknown municipality '+str(key))
            continue
        code=lookup[key]
        if code in records:raise ValueError('Duplicate municipality '+code)
        vals=[number(row[i],True) for i in (5,7,9,10)]
        records[code]=dict(ratios=vals, sourceRow=rowno)
    if set(records)!={c['code'] for c in cities}:
        raise ValueError('Incomplete national FY2025 coverage')
    return records

def parse_basic(blob, profile, cities):
    lookup={norm(c['name']):c['code'] for c in cities if c['pref']==profile['pref']}
    ws=openpyxl.load_workbook(io.BytesIO(blob),data_only=True).active
    text=''.join(norm(v) for row in ws.iter_rows(min_row=1,max_row=8,values_only=True) for v in row if v is not None)
    if '令和7年度' not in text or '歳入総額' not in text or '歳出総額' not in text:
        raise ValueError('Wrong year or basic table schema')
    osaka=profile['id']=='osaka2025'
    if norm(ws.cell(5 if osaka else 3,2).value)!='歳入総額' or norm(ws.cell(5 if osaka else 3,3).value)!='歳出総額':
        raise ValueError('Basic amount columns shifted')
    if (osaka and '百万円' not in text) or (not osaka and ws.cell(6,2).value!='千円'):
        raise ValueError('Basic amount unit changed')
    result={}
    for rowno,row in enumerate(ws.values,1):
        key=norm(row[0])
        if key not in lookup:continue
        code=lookup[key]
        if code in result:raise ValueError('Duplicate basic record')
        inc,exp=number(row[1]),number(row[2])
        if inc<=0 or exp<=0:raise ValueError('Invalid settlement amount')
        # Osaka rounds each cell to million yen. A 1-million difference is allowed only there.
        if abs(inc-exp-number(row[3])) > (1 if osaka else 0):
            raise ValueError('Income minus expense does not reconcile')
        result[code]=dict(revenue=inc,spending=exp,unit=profile['unit'],balance=number(row[5 if osaka else 4]),currentRatio=number(row[11 if osaka else 12]),source=profile['id'],sourceRow=rowno)
    if len(result)!=profile['count']:raise ValueError('Incomplete prefectural coverage')
    if not osaka:
        total=list(ws.values)[69]
        for key,col in [('revenue',1),('spending',2)]:
            if sum(r[key] for r in result.values())!=number(total[col]):
                raise ValueError('Prefectural aggregate mismatch')
    return result

def update(root,get):
    root=Path(root);target=root/'dist/latest-2025.json';cities=json.loads((root/'dist/finance.json').read_text())['cities']
    previous=json.loads(target.read_text()) if target.exists() else None
    output=dict(year='2025',status='速報',ratioNames=['実質赤字比率','連結実質赤字比率','実質公債費比率','将来負担比率'],sources={},cities={},basic={})
    # Verify fiscal year against the release caption; the workbook itself has no year caption.
    page=get(HEALTH['page'])
    try:text=page.decode('utf-8-sig')
    except UnicodeDecodeError:text=page.decode('cp932')
    if '令和7年度決算に基づく' not in unicodedata.normalize('NFKC',text):
        raise ValueError('National release fiscal year changed')
    for p in [HEALTH]+BASIC:
        b=get(p['url']);sha=hashlib.sha256(b).hexdigest()
        if previous and previous['sources'].get(p['id'],{}).get('sha256')==sha:
            parsed=previous['cities'] if p is HEALTH else {k:v for k,v in previous['basic'].items() if v['source']==p['id']}
        else:parsed=parse_health(b,cities) if p is HEALTH else parse_basic(b,p,cities)
        output['sources'][p['id']]={**p,'sha256':sha,'count':len(parsed)}
        output['cities' if p is HEALTH else 'basic'].update(parsed)
    if len(output['cities'])!=1741 or len(output['basic'])!=101:raise ValueError('FY2025 coverage mismatch')
    target.write_text(json.dumps(output,ensure_ascii=False,separators=(',',':'))+'\n')
    return dict(id='latest-2025',status='unchanged' if output==previous else 'updated',year='2025',municipalities=len(output['cities']),settlements=len(output['basic']),sources=list(output['sources'].values()))

if __name__=='__main__':
    from auto_update import fetch
    print(json.dumps(update(Path(__file__).resolve().parents[1],fetch),ensure_ascii=False))
