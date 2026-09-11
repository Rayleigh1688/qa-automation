import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from support import ROOT
from filbet.requirement_permissions import permission_case
from filbet.requirement_kyc import reserve_phone


class PermissionAndFixtureTests(unittest.TestCase):
    def test_reservation_survives_stale_search_and_process_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            flow=SimpleNamespace(PHONE_CURSOR_DIR=Path(folder),load_phone_cursor=lambda p:'9000000001',phone_cursor_path=lambda e:None,
                allocate_registration_phone=lambda args:(args.register_phone,{}))
            one=SimpleNamespace(env='.env.fat');reserve_phone(flow,one)
            two=SimpleNamespace(env='.env.fat');reserve_phone(flow,two)
            self.assertEqual((one.register_phone,two.register_phone),('9000000002','9000000003'))

    def test_failed_business_does_not_get_replaced_by_restore_pass(self):
        for restore_fails in [False,True]:
            with self.subTest(restore_fails=restore_fails):
                original={'gid':'g','name':'Codex','permission':'["20001", "20006", "20007"]','button_permission':'[]','noted':'','pid':'0','state':1,'sortlevel':0}
                current=copy.deepcopy(original)
                writes=[]
                def request(method,path,body=None,query=None):
                    if path=='/admin/group/update':
                        writes.append(copy.deepcopy(body))
                        if len(writes)==2 and restore_fails: raise TimeoutError()
                        current.clear();current.update(body)
                        return {'http':200,'body':{'status':True}}
                    # Baseline succeeds; revoked call incorrectly succeeds too.
                    return {'http':200,'body':{'status':True}}
                def read(adapter,actor,path,method='GET',body=None,query=None):
                    if path=='/admin/me/detail':return {'id':'B','group_id':'g'}
                    if path=='/admin/group/list':return {'d':[current]}
                    if path=='/admin/user/list':return {'d':[{'id':'B','group_id':'g'}],'t':1}
                adapter=SimpleNamespace(args=SimpleNamespace(allow_write=['kyc-permissions']),
                    plan={'contracts':{'kyc_list':{'method':'POST','path':'/admin/kyc/list'},'role_update':{'method':'POST','path':'/admin/group/update'},'admin_users':{'method':'POST','path':'/admin/user/list'}}},
                    sessions={},session=lambda a:SimpleNamespace(request=request),fixtures={'case':{'uid':'u'}},journal=lambda *a,**kw:None,recoveries={},recovery_failed=False)
                with patch('filbet.requirement_permissions.read',side_effect=read),patch('filbet.requirement_permissions.snapshot_data',return_value={'pending':[]}):
                    result=permission_case(adapter,{'params':{'kind':'list'}},'case')
                self.assertFalse(result['checks']['denied'])
                self.assertEqual(writes[-1],original)
                self.assertEqual(adapter.recoveries['case'][0]['status'],'ERROR' if restore_fails else 'PASS')
                self.assertEqual(adapter.recovery_failed,restore_fails)
