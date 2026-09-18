"""Report assessment must not hide positive-query failures or real side effects."""
import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest
from support import ROOT
from requirement_paths import requirement_dir, requirement_dirs
from filbet.requirement_report import assessment_status, write_assessment


def empty_result():
    return {'id':'2027-API-030','status':'FAIL','actual':'raw null assertion','steps':[
        {'id':'prepare','status':'PASS','assertions':[]},
        {'id':'filter','status':'FAIL','observation':{'http':200,'business_status':True},'assertions':[
            {'path':'body.data.t','op':'eq','status':'PASS'},
            {'path':'body.data.d','op':'pluck_set','status':'FAIL','actual_type':'NoneType'}]},
        {'id':'query-no-effects','status':'PASS','assertions':[]}], 'recovery':[]}


class RequirementReportTests(unittest.TestCase):
    def test_only_known_empty_query_with_no_other_failure_is_review(self):
        item=empty_result();before=copy.deepcopy(item)
        self.assertEqual(assessment_status(item),'REASSESSED_PASS')
        self.assertEqual(item,before)
        for change in [{'id':'2027-API-029'},{'status':'NOT_RUN'},{'status':'ERROR'}]:
            candidate={**item,**change}
            self.assertEqual(assessment_status(candidate),candidate['status'])

    def test_http_business_wrong_rows_side_effects_and_recovery_remain_failures(self):
        for kind in ['http','business','wrong_rows','side_effect','missing_readback','recovery','wrong_total']:
            item=empty_result()
            if kind=='http':item['steps'][1]['observation']['http']=502
            if kind=='business':item['steps'][1]['observation']['business_status']=False
            if kind=='wrong_rows':item['steps'][1]['assertions'][1]['actual_type']='list'
            if kind=='side_effect':item['steps'][-1]['status']='FAIL'
            if kind=='missing_readback':item['steps'].pop()
            if kind=='wrong_total':item['steps'][1]['assertions'][0]['status']='FAIL'
            if kind=='recovery':item['recovery']=[{'status':'ERROR'}]
            with self.subTest(kind=kind):self.assertEqual(assessment_status(item),'FAIL')

    def test_html_and_csv_agree_without_mutating_evidence(self):
        item=empty_result();report={'results':[item],'environment':'FAT','source_time':'2026-09-14T10:00:00Z'}
        before=copy.deepcopy(report)
        cases=[{'用例编号':item['id'],'用例名称':'手机号不命中','参数/步骤':'用不匹配的手机号查询'}]
        with tempfile.TemporaryDirectory() as directory:
            write_assessment(directory,cases,report,{'cases':{}})
            html=(Path(directory)/'assessment.html').read_text()
            self.assertIn('1通过（含1项规则复评）',html);self.assertIn('0失败',html)
            self.assertIn('原始技术断言计数（未修改）',html)
            with (Path(directory)/'assessment.csv').open(encoding='utf-8-sig') as f:row=next(csv.DictReader(f))
            self.assertEqual(row['报告结论'],'通过（规则复评）');self.assertEqual(row['原始断言状态'],'FAIL')
        self.assertEqual(report,before)

    def test_known_ids_are_empty_set_queries_in_actual_plan(self):
        from filbet.requirement_report import EMPTY_QUERY_IDS
        plan=json.loads((requirement_dir(ROOT, 'ISOP-2027') / 'plan.json').read_text())
        cases={x['id']:x for x in plan['cases']}
        for ident in EMPTY_QUERY_IDS:
            query=next(x for x in cases[ident]['steps'] if x['id']=='filter')
            assertion=next(x for x in query['expect'] if x['path']=='body.data.d')
            self.assertEqual(assertion['op'],'empty_or_null')
            self.assertTrue(any(x['path']=='body.data.t' and x['op']=='eq' and x['value']==0 for x in query['expect']))


class NullableEmptyAssertionTests(unittest.TestCase):
    def test_empty_or_null_is_narrow_and_missing_is_rejected(self):
        from qa_core.execution_plan import assertions
        check={'path':'body.data.d','op':'empty_or_null'}
        for value in [None, [], {}, '', 0, False, [1], [{'id':'unexpected'}]]:
            result=assertions([check],{'body':{'data':{'d':value}}})[0]
            self.assertEqual(result['status'],'PASS' if value is None or type(value) is list and not value else 'FAIL')
        self.assertEqual(assertions([check],{'body':{'data':{}}})[0]['status'],'FAIL')
        positive={'path':'body.data.d','op':'pluck_set','field':'id','value':['expected']}
        self.assertEqual(assertions([positive],{'body':{'data':{'d':None}}})[0]['status'],'FAIL')


class ConsistentReportViewsTests(unittest.TestCase):
    def test_detail_html_csv_and_assessment_share_reassessed_status(self):
        from filbet.requirement_report import write_reviewed_views, display_report
        from qa_core.case_report import FIELDS
        item=empty_result();item['evidence']=str(requirement_dir(ROOT, 'ISOP-2027') / 'plan.json')
        report={'results':[item],'environment':'FAT','source_time':'2026-09-14T10:00:00Z'}
        original=copy.deepcopy(report)
        row={k:'测试' for k in FIELDS};row.update({'用例编号':item['id'],'用例名称':'手机号不命中','类型':'API'})
        with tempfile.TemporaryDirectory() as directory:
            write_reviewed_views(directory,[row],report)
            page=(Path(directory)/'results.html').read_text()
            self.assertIn('class="case" data-status="PASS"',page)
            self.assertNotIn('class="case" data-status="FAIL"',page)
            self.assertNotIn('预期返回记录列表',page)
            with (Path(directory)/'results.csv').open(encoding='utf-8-sig') as f:result=next(csv.DictReader(f))
            self.assertEqual(result['执行结果'],'PASS')
            self.assertIn('规则复评',result['分类'])
            self.assertIn('未重新请求',result['实际结果/失败点'])
        self.assertEqual(report,original)
        other=empty_result();other['id']='2027-API-029'
        self.assertEqual(display_report({'results':[other]})['results'][0]['status'],'FAIL')
