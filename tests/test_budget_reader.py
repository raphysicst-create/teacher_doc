"""Budget hierarchy and row-position regressions for the XLS reader migration."""
import json
from pathlib import Path
import sys,tempfile,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import refresh_reference as ref

class BudgetReaderTests(unittest.TestCase):
    def setUp(self):
        scratch=ROOT/'.claude/scratchpad/dev-tests';scratch.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=scratch);self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name);self.source=self.folder/'fixture.xls';self.source.write_bytes(b'fixture')
    def parse(self,rows):
        target=self.folder/'derived.json'
        with patch.object(ref,'BUDGET_XLS',self.source),patch.object(ref,'BUDGET_JSON',target),patch.object(ref,'read_budget_rows',return_value=rows):
            counts=ref.build_budget()
        return counts,json.loads(target.read_text(encoding='utf-8'))
    def test_blank_headers_indent_hierarchy_and_amounts(self):
        counts,data=self.parse([[],['학교'],[],[],[' 사업', '', 1000.0],['      항목','',1000],['재료비','실험 재료',123.0],['비목',10,False],['합 계','',1000]])
        self.assertEqual(counts,(1,2))
        program=data['사업'][0];self.assertEqual(program['세부사업'],'사업');self.assertEqual(program['예산현액'],1000)
        self.assertEqual(program['세부항목'][0]['산출내역'],[{'비목':'재료비','명':'실험 재료','예산현액':123},{'비목':'비목','명':'10.0','예산현액':None}])
    def test_orphan_detail_is_rejected(self):
        with self.assertRaisesRegex(SystemExit,'상위 세부항목'):self.parse([[],[],[],[],['비목','내용',1]])
    def test_orphan_item_is_rejected(self):
        with self.assertRaisesRegex(SystemExit,'상위 세부사업'):self.parse([[],[],[],[],['      항목','',1]])
    def test_empty_result_is_rejected(self):
        with self.assertRaisesRegex(SystemExit,'파싱 결과가 비었음'):self.parse([[],[],[],[],['사업','',1]])
    def test_source_cannot_be_output(self):
        before=self.source.read_bytes()
        with patch.object(ref,'BUDGET_XLS',self.source),patch.object(ref,'BUDGET_JSON',self.source):
            with self.assertRaisesRegex(ValueError,'서로 다른'):ref.build_budget()
        self.assertEqual(self.source.read_bytes(),before)
    def test_reader_preserves_absolute_excel_coordinates(self):
        import python_calamine
        with patch.object(python_calamine,'CalamineWorkbook') as book:
            rows=[[],[],[],[],['사업','',1]]
            sheet=book.from_path.return_value.__enter__.return_value.get_sheet_by_index.return_value
            sheet.to_python.return_value=rows
            self.assertEqual(ref.read_budget_rows(self.source),rows)
            sheet.to_python.assert_called_once_with(skip_empty_area=False)
            book.from_path.return_value.__exit__.assert_called_once()

if __name__=='__main__':unittest.main()
