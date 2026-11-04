"""Validate deployable static assets and source-backed ledger totals; stdlib only."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1] / 'dist'
for file in root.glob('*.json'):
    json.loads(file.read_text())
ledger = json.loads((root / 'bunkyo-ledger.json').read_text())
seen = set()
parents = 0

def visit(node, level):
    global parents
    assert node['id'] not in seen, f"Duplicate ID: {node['id']}"
    seen.add(node['id'])
    assert node['level'] == level
    assert isinstance(node['amount'], int) and node['amount'] >= 0
    assert 140 <= node['page'] <= 271
    if node['children']:
        parents += 1
        assert node['amount'] == sum(c['amount'] for c in node['children']), node['id']
    for child in node['children']:
        visit(child, level + 1)

for node in ledger['roots']:
    visit(node, 0)
assert len(ledger['roots']) == 12
assert sum(n['amount'] for n in ledger['roots']) == ledger['total'] == 135_937_867_776
assert len(seen) == ledger['nodes'] == 1654
assert parents == ledger['counts']['complete'] == 367
parties = json.loads((root / 'transactions.json').read_text())
assert len({r['id'] for r in parties['records']}) == len(parties['records'])
assert all(isinstance(r['amount'], int) and r['amount'] >= 0 for r in parties['records'])
assert all((root / name).is_file() for name in ['index.html', 'style.css', 'app.js', 'ledger.js', 'parties.js', 'finance.json', 'spending-tree.json', 'national.json', 'trace.json', 'transactions.json'])
print(f'Validated {len(seen):,} ledger nodes, {parents} parent-child totals, 12 chapter totals, and static data files.')
