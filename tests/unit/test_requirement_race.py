import unittest
from types import SimpleNamespace
from unittest.mock import patch
from support import ROOT
from filbet.requirement_race import race, validate_race


class RaceTests(unittest.TestCase):
    def test_two_successes_fail_unique_winner_and_never_retry(self):
        calls=[]
        class Session:
            def request(self,method,path,body,encoding):
                calls.append(body['uid'])
                return {'http':200,'body':{'status':True}}
        adapter=SimpleNamespace(args=SimpleNamespace(allow_write=['kyc-review']),
            plan={'contracts':{'edit':{'scope':'kyc-review','ownership':'uid','method':'POST','path':'/admin/kyc/edit','encoding':'cbor'}}},
            fixtures={'case':{'owned':{'uid':{'u'}}}},session=lambda actor:Session(),journal=lambda *a,**kw:None)
        before={'formal':{},'audit':[]}
        step={'id':'race','params':{'before':before,'requests':[{'actor':a,'contract':'edit','body':{'uid':'u'}} for a in ['A','B']]}}
        after={'formal':{},'audit':[{},{}],'pending':[{},{}],'processed':[]}
        with patch('filbet.requirement_race.snapshot_data',return_value=after):result=race(adapter,step,'case')
        self.assertEqual(len(calls),2)
        self.assertFalse(result['checks']['one_winner'])
        self.assertFalse(result['checks']['one_transition'])
        step['params']['requests'][0]['body']['uid']='not-owned'
        with self.assertRaises(ValueError):race(adapter,step,'case')
        self.assertEqual(len(calls),2)

    def test_invalid_race_rejected_offline(self):
        with self.assertRaises(ValueError):validate_race({'actors':{'A':{}}},{'params':{'requests':[{'actor':'A','contract':'finance'}]}})
