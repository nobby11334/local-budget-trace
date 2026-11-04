"""Parse Bunkyo annual report spreads; reject incomplete or inconsistent hierarchies."""
import collections
import hashlib
import re
import unicodedata
from pathlib import Path
import pdfplumber

NUMBER = r'([\d,]+)'
HEADER = re.compile(r'^\d+ (.+?) '+NUMBER+' '+NUMBER+' '+NUMBER+' '+NUMBER+r' (\d+\.\d+)$')
BUSINESS = re.compile('^'+NUMBER+' '+NUMBER+' '+NUMBER+' '+NUMBER+r' (\d+\.\d+) \d+ (.+?) '+NUMBER+'$')
SUB = re.compile(r'^\(\s*\d+\)\s*(.+?)\s+([\d,]+)\s*円?$')
WRAP = re.compile(r'^\(\s*\d+\)\s*(.+)$')

def normal(text):
    return unicodedata.normalize('NFKC', text)

def money(text):
    return int(text.replace(',', ''))

def parse_ledger(path, year, url):
    roots, stack, issues = [], [], []
    count, base, start, end, total = 0, None, None, None, None
    pending = None
    def add(label, amount, level, page, budget=None):
        nonlocal count
        while stack and stack[-1]['level'] >= level:
            stack.pop()
        if level and (not stack or stack[-1]['level'] != level - 1):
            raise ValueError(f'Orphan item p.{page}: {label}')
        count += 1
        n = dict(id=f'b{count}', label=label, amount=amount, level=level, page=page, children=[])
        if budget is not None:
            n['budget'] = budget
        (roots if level == 0 else stack[-1]['children']).append(n)
        stack.append(n)
    with pdfplumber.open(path) as pdf:
        cover = re.sub(r'\(cid:3\)|\s', '', normal(pdf.pages[0].extract_text() or ''))
        if f'令和{int(year)-2018}年度' not in cover:
            raise ValueError('PDF cover year differs from the linked fiscal year')
        for i in range(1, len(pdf.pages), 2):
            page = pdf.pages[i]
            chars = page.chars
            text = ''.join(c['text'] for c in chars)
            duplicate = text.find(text[:40], 40) if len(text) > 80 else -1
            # The 2024 report has a repeated shifted text layer. 2025 does not.
            if duplicate > 0:
                ids = set(map(id, chars[:duplicate]))
                surface = page.filter(lambda o: o['object_type'] != 'char' or id(o) in ids)
            else:
                surface = page
            lines = surface.extract_text_lines(x_tolerance=2, y_tolerance=2)
            candidates = [(l, HEADER.match(normal(l['text']))) for l in lines]
            headers = [(l, m) for l, m in candidates if m]
            if start is None:
                if len(headers) < 3 or any(m[1].replace(' ', '') != '議会費' for _, m in headers[:3]):
                    page.close()
                    continue
                positions = [l['x0'] for l, _ in headers[:3]]
                if not (10 < positions[1]-positions[0] < 16 and 10 < positions[2]-positions[1] < 16):
                    raise ValueError('Unrecognized chapter/section/item indentation')
                base, start = positions[0], i + 1
            for line in lines:
                t = normal(line['text'])
                m = HEADER.match(t)
                if m:
                    pending = None
                    dx = line['x0'] - base
                    level = 0 if dx < 6 else 1 if dx < 20 else 2
                    add(m[1], money(m[4]), level, i+1, money(m[2]))
                    continue
                m = BUSINESS.match(t)
                if m:
                    pending = None
                    if money(m[3]) != money(m[7]):
                        raise ValueError(f'Business amount mismatch p.{i+1}')
                    add(m[6], money(m[7]), 3, i+2, money(m[1]))
                    continue
                if line['x0'] < base + 500:
                    continue
                m = SUB.match(t)
                if m:
                    pending = None
                    add(m[1].strip(), money(m[2]), 4, i+2)
                elif WRAP.match(t) and '円' not in t:
                    pending = WRAP.match(t)[1].strip()
                elif pending and re.fullmatch(r'[\d,]+円', t.replace(' ', '')):
                    add(pending, money(t.replace(' ', '')[:-1]), 4, i+2)
                    pending = None
            # Narrow word tolerance separates the adjacent carryover and expense columns.
            words = surface.extract_words(x_tolerance=1, y_tolerance=2)
            rows = collections.defaultdict(list)
            for word in words:
                rows[round(word['top'])].append(word)
            for row in rows.values():
                text = ' '.join(normal(w['text']) for w in sorted(row, key=lambda w: w['x0']))
                if text.replace(' ', '').startswith('歳出合計'):
                    nums = re.findall(r'(?<![\d,])[\d,]+(?:\.\d+)?', text)
                    if len(nums) != 5:
                        raise ValueError(f'Cannot read independent grand total: {text}')
                    total = money(nums[2])
                    end = i + 2
            page.close()
            if total is not None:
                break
    if total is None or len(roots) != 12:
        raise ValueError('General-account table or grand total not found')
    parents = 0
    partial = []
    def validate(node):
        nonlocal parents
        if node['children']:
            parents += 1
            delta = node['amount'] - sum(c['amount'] for c in node['children'])
            node['difference'] = delta
            node['coverage'] = 'complete' if delta == 0 else 'partial'
            if delta:
                partial.append((node['label'], delta, node['page']))
        for child in node['children']:
            validate(child)
    for n in roots:
        validate(n)
    if sum(n['amount'] for n in roots) != total:
        raise ValueError('Chapter sum differs from independent source grand total')
    if partial:
        raise ValueError(f'Incomplete parent/child sums: {partial[:12]}')
    if count < 1000 or parents < 200:
        raise ValueError('Unexpectedly few detailed items')
    return dict(city='13105', year=str(year), account='一般会計', url=url,
                sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                total=total, sourcePages=[start,end], counts={'complete':parents},
                nodes=count, issues=issues, roots=roots)
