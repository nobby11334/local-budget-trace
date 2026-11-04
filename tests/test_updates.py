"""Test monetary corruption and update failures without making network requests."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import auto_update
import ledger_parser

class Updates(unittest.TestCase):
    def fixture(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root=Path(tmp.name)
        shutil.copytree(ROOT/'dist',root/'dist')
        shutil.copytree(ROOT/'scripts',root/'scripts',ignore=shutil.ignore_patterns('__pycache__'))
        return root

    def test_future_local_year_is_discovered_without_changing_code(self):
        config={'bunkyoIndex':'https://www.city.bunkyo.lg.jp/index.html','ledgers':[{'year':'2025','page':'https://www.city.bunkyo.lg.jp/old.html','file':'bunkyo-ledger-2025.json'}]}
        html='<a href="/future.html">決算審査特別委員会（令和9年9月定例議会）</a>'.encode()
        result=auto_update.discover(config,lambda u:html)
        self.assertEqual(result[-1],{'year':'2026','page':'https://www.city.bunkyo.lg.jp/future.html','file':'bunkyo-ledger-2026.json'})

    def test_cp932_source_links(self):
        raw='<a href="r07_shichouson.html">令和7年度</a>'.encode('cp932')
        result=auto_update.links(raw,'https://www.soumu.go.jp/iken/')
        self.assertEqual(result,[('https://www.soumu.go.jp/iken/r07_shichouson.html','令和7年度')])

    def test_wrong_fiscal_year_rejected(self):
        pdf=MagicMock();pdf.__enter__.return_value.pages[0].extract_text.return_value='令和6年度 主要施策の成果'
        with patch.object(ledger_parser.pdfplumber,'open',return_value=pdf):
            with self.assertRaisesRegex(ValueError,'cover year'):
                ledger_parser.parse_ledger('unused.pdf','2025','https://www.city.bunkyo.lg.jp/a.pdf')

    def test_corrupted_child_amount_rejected(self):
        root=self.fixture();p=root/'dist/bunkyo-ledger-2025.json';d=json.loads(p.read_text())
        d['roots'][0]['children'][0]['amount']+=1;p.write_text(json.dumps(d))
        result=subprocess.run([sys.executable,str(root/'scripts/validate_site.py')],capture_output=True)
        self.assertNotEqual(result.returncode,0)

    def test_parser_failure_preserves_every_published_file(self):
        root=self.fixture();config=root/'sources.json';config.write_text(json.dumps({'scope':'test'}))
        before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'dist').iterdir() if p.is_file()}
        profile={'year':'2025','page':'https://www.city.bunkyo.lg.jp/test.html','file':'bunkyo-ledger-2025.json'}
        html='<a href="/new.pdf">令和7年度主要施策の成果</a>'.encode()
        def get(url):
            return html if url.endswith('.html') else b'%PDF-invalid-updated-source'
        with patch.object(auto_update,'ROOT',root),patch.object(auto_update,'discover',return_value=[profile]),patch.object(auto_update,'fetch',side_effect=get),patch.object(auto_update,'parse_ledger',side_effect=ValueError('parent-child mismatch')):
            with self.assertRaisesRegex(ValueError,'parent-child mismatch'):
                auto_update.run(config)
        after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'dist').iterdir() if p.is_file()}
        self.assertEqual(before,after)

    def test_unchanged_pdf_is_not_reparsed_and_network_failure_retains_national(self):
        root=self.fixture();blob=b'%PDF-unchanged';sha=hashlib.sha256(blob).hexdigest()
        p=root/'dist/bunkyo-ledger-2025.json';d=json.loads(p.read_text());d['sha256']=sha;p.write_text(json.dumps(d))
        p=root/'dist/ledger-index.json';d=json.loads(p.read_text());d['years']['2025']['sha256']=sha;p.write_text(json.dumps(d))
        config=root/'sources.json';config.write_text(json.dumps({'scope':'test','national2024':{'page':'https://www.soumu.go.jp/test','files':{'a.xlsx':{'url':'https://www.soumu.go.jp/a.xlsx','sha256':'unused'}}}}))
        profile={'year':'2025','page':'https://www.city.bunkyo.lg.jp/test.html','file':'bunkyo-ledger-2025.json'}
        data=root/'dist/bunkyo-ledger-2025.json';d=json.loads(data.read_text());d['url']='https://www.city.bunkyo.lg.jp/new.pdf';data.write_text(json.dumps(d))
        html='<a href="/new.pdf">令和7年度主要施策の成果</a>'.encode()
        before=(root/'dist/finance.json').read_bytes()
        def get(url):
            if url.endswith('test.html'):return html
            if url.endswith('new.pdf'):return blob
            if url.endswith('.xlsx'):raise OSError('temporary outage')
            return b'<html></html>'
        with patch.object(auto_update,'ROOT',root),patch.object(auto_update,'discover',return_value=[profile]),patch.object(auto_update,'fetch',side_effect=get),patch.object(auto_update,'parse_ledger',side_effect=AssertionError('must not reparse')):
            result=auto_update.run(config)
        self.assertTrue(result['errors'])
        self.assertEqual(result['datasets'][0]['status'],'unchanged')
        self.assertEqual((root/'dist/finance.json').read_bytes(),before)

if __name__=='__main__':unittest.main()
