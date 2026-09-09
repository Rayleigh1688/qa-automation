from support import ROOT, SCRIPTS
"""Offline business response and lane guards; no browser or environment secrets."""
import subprocess
import unittest
from pathlib import Path


class UiBusinessTests(unittest.TestCase):
    def test_business_rejection_and_lane_isolation(self):
        result = subprocess.run(['node', '--input-type=module', '-e', r'''
import assert from 'node:assert/strict';
import { decodeBusinessBody, requireBusinessResponse, readBusinessRequest } from './ui/framework/business-response.mjs';
import { validateKycEnvironment, validateKycResume } from './ui/framework/kyc-preflight.mjs';
assert.deepEqual(readBusinessRequest({method:()=> 'GET',url:()=> 'https://example.test/finance/payment/deposit?amount=100&rotation_flag=0'}), {amount:'100',rotation_flag:'0'});
const response = (data, ok = true) => ({body: async () => Buffer.from(JSON.stringify(data)), ok: () => ok, status: () => ok ? 200 : 500, url: () => 'https://example.test/member/kyc/insert'});
assert.deepEqual(decodeBusinessBody(Buffer.from('{"status":true,"data":{"id":"123"}}')), {status:true,data:{id:'123'}});
// CBOR {status:true}; JSON-looking content types must not affect decoding.
assert.equal(decodeBusinessBody(Buffer.from([0xa1,0x66,0x73,0x74,0x61,0x74,0x75,0x73,0xf5])).status, true);
await assert.rejects(requireBusinessResponse(response({status:false})), /rejected/);
await assert.rejects(requireBusinessResponse(response({status:true}, false)), /rejected/);
await assert.rejects(requireBusinessResponse(response({data:{}})), /rejected/);
assert.equal((await requireBusinessResponse(response({status:true}))).status, true);
const env = {CLIENT_BASE_URL:'https://client-fat.filbet2025.com', API_URL:'https://client-fat.filbet2025.com', ADMIN_URL:'https://admin-fat.filbet2025.com', KYC_CLIENT_PHONE:'9000000001', KYC_CLIENT_PASSWORD:'test-only', PRE_KYC_CLIENT_PHONE:'9000000002', WRITE_CLIENT_PHONE:'9000000003', KYC_IMAGE:'package.json'};
validateKycEnvironment(env);
const now = Date.now();
const prior = {runId:'this-run',scope:'FAT',stage:'approved_refresh',adminApproved:true,beforeStatus:0,afterStatus:2,uiSubmitted:true,uid:'test-uid',submission:{businessStatus:true,successVisible:true,successfulUploads:3}};
const run = {runId:'this-run',startedAt:new Date(now).toISOString()};
validateKycResume(prior,run,now);
for (const patch of [{runId:'old-run'},{uiSubmitted:false},{adminApproved:false},{beforeStatus:5},{submission:{businessStatus:true,successVisible:false,successfulUploads:3}}]) assert.throws(()=>validateKycResume({...prior,...patch},run,now),/Resume/);
assert.throws(()=>validateKycResume(prior,run,now+3600001),/Resume/);
for (const key of ['PRE_KYC_CLIENT_PHONE','WRITE_CLIENT_PHONE']) {
 assert.throws(() => validateKycEnvironment({...env,[key]:'+639000000001'}), /separate/);
 assert.throws(() => validateKycEnvironment({...env,[key]:'09000000001'}), /separate/);
}
assert.throws(() => validateKycEnvironment({...env, API_URL:'https://client-uat.filbet2025.com'}), /FAT/);
assert.throws(() => validateKycEnvironment({...env, ADMIN_URL:'https://admin-fat.filbet2025.com.evil.test'}), /FAT/);
assert.throws(() => validateKycEnvironment(env,{approve:true}), /TOTP/);
'''], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
