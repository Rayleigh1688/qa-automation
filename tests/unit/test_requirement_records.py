import unittest
import support
from filbet.requirement_records import inspect_record_response


class RecordChecks(unittest.TestCase):
    def sample(self):
        return {'d':[{'bet_time':1001,'settle_time':2001,'node':2,'state':1,'game_class':'3','bet_type':2,'bet_amount':'10','valid_bet_amount':'8','net_amount':'-7','payout_amount':'17'}], 's':1,'t':1,'a':{'subtotal':{'bet_amount':'10','valid_bet_amount':'8','ggr':'-7','grand_inc':'17','order_count':1}}}

    def test_amount_sign_and_filter(self):
        checks=inspect_record_response(self.sample(),{'page_size':20,'settle_start_time':2001,'settle_end_time':2001,'node':2,'order_type':2,'state':'1'})
        self.assertTrue(all(checks.values()))

    def test_outside_and_wrong_sign_fail(self):
        data=self.sample();data['d'][0]['payout_amount']='3'
        checks=inspect_record_response(data,{'page_size':20,'start_time':1002,'end_time':2000,'node':1})
        self.assertFalse(checks['bet_time_range']);self.assertFalse(checks['node_filter']);self.assertFalse(checks['payout_sign'])

    def test_missing_or_nonfinite_amount_fails(self):
        data=self.sample();data['d'][0]['bet_amount']='NaN'
        self.assertFalse(inspect_record_response(data,{'page_size':20})['amount_fields_valid'])

    def test_empty_checks_only_counts(self):
        self.assertEqual(set(inspect_record_response({'d':[],'s':0,'t':0},{'page_size':20})),{'page_count','page_limit','total_count'})
