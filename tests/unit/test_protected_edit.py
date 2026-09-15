import copy
import json
import unittest
from support import ROOT
from filbet.protected_edit import checks

class ProtectedEditTests(unittest.TestCase):
    def setUp(self):
        self.before={'formal':{'admin':{'phone':'9000000001','kyc_status':2}},'pending':[],'processed':[],'audit':[]}
        self.after=copy.deepcopy(self.before)
        self.after.update(pending=[{'after_info':{'kyc_status':2,'user_message':'editable'}}],audit=[{'id':'new'}])
    def test_editable_message_allowed_protected_fields_not(self):
        self.assertTrue(all(checks(self.before,self.after,True,{'user_message':'editable'}).values()))
        for k,v in [('phone','000000000000'),('kyc_status',5),('user_message','wrong')]:
            after=copy.deepcopy(self.after);after['pending'][0]['after_info'][k]=v
            self.assertFalse(all(checks(self.before,after,True,{'user_message':'editable'}).values()))
    def test_rejection_must_have_no_effect_and_acceptance_needs_real_transition(self):
        self.assertTrue(all(checks(self.before,self.before,False,{}).values()))
        self.assertFalse(all(checks(self.before,self.after,False,{}).values()))
        self.assertFalse(all(checks(self.before,self.before,True,{}).values()))
    def test_formal_and_processed_must_stay_unchanged(self):
        for key in ['formal','processed']:
            after=copy.deepcopy(self.after);after[key]={} if key=='formal' else [{'id':'unexpected'}]
            self.assertFalse(all(checks(self.before,after,True,{}).values()))
