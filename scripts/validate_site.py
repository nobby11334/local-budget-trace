"""Validate deployable static assets and source-backed ledger totals; stdlib only."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1] / 'dist'
for file in root.glob('*.json'):
    json.loads(file.read_text())
index = json.loads((root / 'ledger-index.json').read_text())
assert index['latest'] == max(index['years'])
total_nodes = total_parents = 0
for year, info in index['years'].items():
    ledger = json.loads((root / info['file']).read_text())
    assert ledger['year'] == year and ledger['sha256'] == info['sha256']
    assert ledger['total'] == info['total'] and ledger['nodes'] == info['nodes']
    seen = set()
    counts = [0]
    def visit(node, level):
        assert node['id'] not in seen, f"Duplicate ID: {node['id']}"
        seen.add(node['id'])
        assert node['level'] == level
        assert isinstance(node['amount'], int) and node['amount'] >= 0
        assert ledger['sourcePages'][0] <= node['page'] <= ledger['sourcePages'][1]
        if node['children']:
            counts[0] += 1
            assert node['amount'] == sum(c['amount'] for c in node['children']), node['id']
        for child in node['children']:
            visit(child, level + 1)
    for node in ledger['roots']:
        visit(node, 0)
    assert len(ledger['roots']) == 12
    assert sum(n['amount'] for n in ledger['roots']) == ledger['total']
    assert len(seen) == ledger['nodes']
    assert counts[0] == ledger['counts']['complete']
    total_nodes += len(seen); total_parents += counts[0]
parties = json.loads((root / 'transactions.json').read_text())
assert len({r['id'] for r in parties['records']}) == len(parties['records'])
assert all(isinstance(r['amount'], int) and r['amount'] >= 0 for r in parties['records'])
assert all((root / name).is_file() for name in ['index.html', 'style.css', 'app.js', 'ledger.js', 'parties.js', 'finance.json', 'spending-tree.json', 'national.json', 'trace.json', 'transactions.json'])
print(f'Validated {total_nodes:,} ledger nodes, {total_parents} parent-child totals, all annual chapter totals, and static data files.')
# The FY2025 release has a different scope from the complete FY2024 finance tables.
import math
latest=json.loads((root/'latest-2025.json').read_text())
finance=json.loads((root/'finance.json').read_text())
codes={c['code'] for c in finance['cities']}
assert latest['year']=='2025' and latest['status']=='速報'
assert set(latest['cities'])==codes and len(codes)==1741
assert len({c['pref'] for c in finance['cities']})==47
for code,rec in latest['cities'].items():
    assert len(rec['ratios'])==4 and rec['sourceRow']>=6
    assert all(v=='-' or (type(v) in (int,float) and math.isfinite(v)) for v in rec['ratios'])
assert len(latest['basic'])==101
for source,count,unit,pref in [('osaka2025',41,1000000,'大阪府'),('fukuoka2025',60,1000,'福岡県')]:
    records={k:v for k,v in latest['basic'].items() if v['source']==source}
    assert len(records)==count
    assert all(next(c['pref'] for c in finance['cities'] if c['code']==k)==pref for k in records)
    for r in records.values():
        assert r['unit']==unit and r['revenue']>0 and r['spending']>0 and r['sourceRow']>0
        assert all(type(r[k]) in (int,float) and math.isfinite(r[k]) for k in ['revenue','spending','balance','currentRatio'])
for s in latest['sources'].values():
    assert len(s['sha256'])==64 and s['url'].startswith('https://')
assert (root/'latest.js').is_file()
print('Validated FY2025: 1,741 national ratio records across 47 prefectures and 101 provisional settlement totals.')
