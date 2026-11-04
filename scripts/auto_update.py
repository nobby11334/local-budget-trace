"""Fetch official sources, stage updates, validate, then publish data files atomically.
No generated data is copied back if a parser or integrity check fails.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.parse
import urllib.request
from ledger_parser import parse_ledger

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {'www.city.bunkyo.lg.jp', 'www.soumu.go.jp', 'www.pref.osaka.lg.jp', 'www.pref.fukuoka.lg.jp'}

class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []; self.current = None
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.current = [dict(attrs).get('href', ''), '']
    def handle_data(self, text):
        if self.current is not None:
            self.current[1] += text
    def handle_endtag(self, tag):
        if tag == 'a' and self.current is not None:
            self.links.append(tuple(self.current)); self.current = None

def links(blob, base):
    p = Links()
    try:
        text = blob.decode('utf-8-sig')
    except UnicodeDecodeError:
        text = blob.decode('cp932')
    p.feed(text)
    return [(urllib.parse.urljoin(base, u), unicodedata.normalize('NFKC', t).strip()) for u,t in p.links]

def fetch(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname not in ALLOWED:
        raise ValueError('Unapproved source URL: '+url)
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent':'local-budget-trace/1.0 (+https://github.com/nobby11334/local-budget-trace)'})
            with urllib.request.urlopen(req, timeout=45) as r:
                if urllib.parse.urlparse(r.url).hostname not in ALLOWED:
                    raise ValueError('Unexpected redirect host')
                data = r.read(60_000_001)
                if len(data) > 60_000_000:
                    raise ValueError('Source exceeds download limit')
                return data
        except (OSError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)

def digest(blob):
    return hashlib.sha256(blob).hexdigest()

def dump(path, obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,separators=(',',':'))+'\n')

def discover(config, get):
    result = {p['year']:dict(p) for p in config['ledgers']}
    base = config['bunkyoIndex']
    for url, title in links(get(base),base):
        m = re.search(r'決算審査特別委員会.*令和(\d+)年', title)
        if m and int(m[1]) >= 7:
            year = str(2017 + int(m[1]))
            result.setdefault(year,dict(year=year,page=url,file=f'bunkyo-ledger-{year}.json'))
    return sorted(result.values(),key=lambda p:p['year'])

def run(config_path=None):
    config = json.loads(Path(config_path or ROOT/'config/update-sources.json').read_text())
    checked = datetime.now(timezone.utc).isoformat(timespec='seconds')
    report = dict(checkedAt=checked,scope=config['scope'],datasets=[],errors=[],needsAction=[])
    cache = {}
    def get(url):
        if url not in cache:
            cache[url] = fetch(url)
        return cache[url]
    with tempfile.TemporaryDirectory(prefix='budget-update-') as temp:
        stage = Path(temp)
        shutil.copytree(ROOT/'dist',stage/'dist')
        shutil.copytree(ROOT/'scripts',stage/'scripts',ignore=shutil.ignore_patterns('__pycache__'))
        index = json.loads((stage/'dist/ledger-index.json').read_text())
        # Discovery and PDF parse failures are fatal: never silently miss a new local year.
        for profile in discover(config,get):
            year, page_url = profile['year'], profile['page']
            targets = [(u,t) for u,t in links(get(page_url),page_url) if re.search(r'令和'+str(int(year)-2018)+r'年度主要施策の成果',t.replace(' ','')) and urllib.parse.urlparse(u).path.endswith('.pdf')]
            targets = list(dict.fromkeys(targets))
            if len(targets) != 1:
                raise ValueError(f'Expected one annual report for {year}; found {len(targets)}')
            url, title = targets[0]
            blob = get(url)
            if not blob.startswith(b'%PDF-'):
                raise ValueError('Annual report is not PDF')
            target = stage/'dist'/profile['file']
            previous = json.loads(target.read_text()) if target.exists() else None
            changed = not previous or previous.get('sha256') != digest(blob) or previous.get('url') != url
            if changed:
                pdf = stage/f'bunkyo-{year}.pdf'; pdf.write_bytes(blob)
                data = parse_ledger(pdf,year,url)
                dump(target,data)
            else:
                data = previous
            index['years'][year] = {k:data[k] for k in ['nodes','total','url','sha256']}
            index['years'][year]['file'] = profile['file']
            report['datasets'].append(dict(id='bunkyo-ledger-'+year,status='updated' if changed else 'unchanged',year=year,page=page_url,url=url,sha256=digest(blob),nodes=data['nodes'],parentChildChecks=data['counts']['complete']))
        index['latest'] = max(index['years'])
        dump(stage/'dist/ledger-index.json',index)
        # Corrections to already-supported nationwide FY2024 tables can be re-imported.
        national = config['national2024']; source_dir = stage/'national2024'; source_dir.mkdir()
        source_errors = []
        def download_file(item):
            name, meta = item
            try:
                data = get(meta['url'])
                if not data.startswith(b'PK'):
                    raise ValueError('Not an XLSX: '+name)
                (source_dir/name).write_bytes(data)
                return name,digest(data),meta['sha256']
            except (OSError,TimeoutError) as exc:
                return name,None,str(exc)
        results = list(ThreadPoolExecutor(max_workers=4).map(download_file,national['files'].items()))
        for name, sha, old in results:
            if sha is None:
                source_errors.append(dict(id='national-2024',file=name,message=old))
        if source_errors:
            report['errors'].extend(source_errors)
            report['datasets'].append(dict(id='national-2024',status='unavailable-kept-existing',url=national['page']))
        else:
            # Compare with the current data provenance, rather than a stale original hash.
            old_files=json.loads((stage/'dist/finance.json').read_text())['meta']['official2024']['files']
            changed=any(sha!=old_files[name]['sha256'] for name,sha,_ in results)
            if changed:
                for script in ['import_official_2024.py','import_spending_tree.py']:
                    subprocess.run([sys.executable,str(stage/'scripts'/script),str(source_dir)],cwd=stage,check=True)
                finance=json.loads((stage/'dist/finance.json').read_text())
                finance['meta']['official2024']['retrieved']=checked[:10]
                dump(stage/'dist/finance.json',finance)
            report['datasets'].append(dict(id='national-2024',status='updated' if changed else 'unchanged',url=national['page'],files=[dict(file=n,sha256=s) for n,s,_ in results]))
        # New nationwide years need a matching column-schema adapter. Detect, don't guess.
        release_url='https://www.soumu.go.jp/iken/kessan_jokyo_2.html'
        try:
            for url,title in links(get(release_url),release_url):
                match=re.search(r'/r(\d+)_shichouson\.html',url)
                if match and 2018+int(match[1])>2024:
                    item=dict(id='national-new-year',year=str(2018+int(match[1])),url=url,status='adapter-review-required')
                    if item not in report['needsAction']:
                        report['needsAction'].append(item)
        except (OSError,TimeoutError) as exc:
            report['errors'].append(dict(id='national-discovery',message=str(exc)))
        if config.get('latest2025'):
            from import_latest_2025 import update
            try:
                report['datasets'].append(update(stage,get))
            except (OSError,TimeoutError) as exc:
                # Network failures retain the entire previous FY2025 snapshot.
                report['errors'].append(dict(id='latest-2025',message=str(exc)))
                report['datasets'].append(dict(id='latest-2025',status='unavailable-kept-existing'))
        # A stale or manually modified unchanged JSON must still pass full validation.
        dump(stage/'dist/update-status.json',report)
        subprocess.run([sys.executable,str(stage/'scripts/validate_site.py')],cwd=stage,check=True)
        changes=[]
        for path in (stage/'dist').iterdir():
            dest=ROOT/'dist'/path.name
            if path.is_file() and (not dest.exists() or dest.read_bytes()!=path.read_bytes()):
                changes.append((path,dest))
        for source,dest in changes:
            temp_dest=dest.with_suffix(dest.suffix+'.tmp')
            shutil.copyfile(source,temp_dest);temp_dest.replace(dest)
        print(json.dumps(dict(changedFiles=[d.name for _,d in changes],report=report),ensure_ascii=False))
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config');args=parser.parse_args()
    try:
        report=run(args.config)
        summary=__import__('os').environ.get('GITHUB_STEP_SUMMARY')
        if summary:
            with open(summary,'a') as f:
                f.write('## Official-source update\n\n'+json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        if report['errors'] or report['needsAction']:
            print('::warning::Some sources are unavailable or require a new adapter; existing datasets are retained. See update-status.json.')
    except Exception as exc:
        print(f'::error::Update aborted; published data kept unchanged: {exc}',file=sys.stderr)
        raise
