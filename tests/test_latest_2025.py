"""Guard fiscal-year, glyph matching, missing symbols, coverage and monetary reconciliation."""
import io
from pathlib import Path
import sys
import unittest
import openpyxl
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from import_latest_2025 import parse_health,parse_basic,BASIC

class Latest(unittest.TestCase):
    def blob(self,w):
        f=io.BytesIO();w.save(f);return f.getvalue()
    def health(self):
        w=openpyxl.Workbook();s=w.active;s.title='1(2)'
        s.cell(3,3,'(2) 市区町村（政令市を含む）');s.cell(5,10,'実質公債費比率')
        for col,val in [(3,'高知県'),(4,'梼原町'),(6,'-'),(8,'-'),(10,7.5),(11,'-')]:s.cell(6,col,val)
        return w
    def test_exact_glyph_mapping_and_missing_symbol_preserved(self):
        records=parse_health(self.blob(self.health()),[dict(code='39405',pref='高知県',name='檮原町')])
        self.assertEqual(records['39405']['ratios'],['-','-',7.5,'-'])
    def test_incomplete_national_coverage_rejected(self):
        with self.assertRaisesRegex(ValueError,'Incomplete'):
            parse_health(self.blob(self.health()),[dict(code='39405',pref='高知県',name='檮原町'),dict(code='13105',pref='東京都',name='文京区')])
    def test_shifted_ratio_column_rejected(self):
        w=self.health();w.active.cell(5,10,'将来負担比率')
        with self.assertRaisesRegex(ValueError,'schema'):
            parse_health(self.blob(w),[dict(code='39405',pref='高知県',name='檮原町')])
    def basic(self):
        w=openpyxl.Workbook();s=w.active
        s.cell(2,4,'令和７年度 市町村別普通会計決算状況');s.cell(3,12,'（単位：百万円；％）')
        s.cell(5,2,'歳入総額');s.cell(5,3,'歳出総額')
        for col,val in enumerate(['岸和田市',100,80,20,1,19,0,0,0,0,0,95],1):s.cell(9,col,val)
        return w
    def test_wrong_fiscal_year_rejected(self):
        w=self.basic();w.active.cell(2,4,'令和６年度')
        with self.assertRaisesRegex(ValueError,'Wrong year'):
            parse_basic(self.blob(w),{**BASIC[0],'count':1},[dict(code='27202',pref='大阪府',name='岸和田市')])
    def test_amount_mismatch_rejected_beyond_source_rounding(self):
        w=self.basic();w.active.cell(9,4,23)
        with self.assertRaisesRegex(ValueError,'reconcile'):
            parse_basic(self.blob(w),{**BASIC[0],'count':1},[dict(code='27202',pref='大阪府',name='岸和田市')])
    def test_million_yen_precision_retained(self):
        r=parse_basic(self.blob(self.basic()),{**BASIC[0],'count':1},[dict(code='27202',pref='大阪府',name='岸和田市')])['27202']
        self.assertEqual((r['revenue'],r['spending'],r['unit']),(100,80,1000000))
