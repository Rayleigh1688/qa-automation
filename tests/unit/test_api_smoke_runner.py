import argparse
import os
import unittest
from unittest.mock import patch

import support
from filbet import smoke
from filbet.controlled import ControlledFlow


def reply(data):
    return {
        "priority": "LOGIN",
        "status": 200,
        "elapsed_ms": 1,
        "ok": True,
        "decoded_body": {"status": True, "data": data},
        "body_sample": repr(data),
    }


class SmokeAssertionTests(unittest.TestCase):
    def test_unknown_or_malformed_rules_fail_a_successful_response(self):
        response = reply({"uid": 123})
        self.assertEqual(
            smoke.assertion_result(response, "http_200,decoded,status_true,data_object,keys:data.uid,non_empty:data.uid"),
            (True, []),
        )
        for rule in ("status_ture", "keys:", "keys:data.uid|", "non_empty:"):
            with self.subTest(rule=rule):
                passed, failures = smoke.assertion_result(response, "status_true," + rule)
                self.assertFalse(passed)
                self.assertEqual(len(failures), 1)


class SmokeLoginTests(unittest.TestCase):
    def setUp(self):
        self.args = argparse.Namespace(timeout=1, insecure=False, body_format="cbor")

    def test_client_otp_uses_current_response_but_reports_only_status(self):
        env = {"CLIENT_PHONE": "fixture", "CLIENT_AUTH_MODE": "otp", "CLIENT_OTP": "123456"}
        replies = [reply({"id": "synthetic-otp-id"}), reply({"t": "synthetic-client-token"})]
        with patch.dict(os.environ, env, clear=True), patch.object(smoke, "request_once", side_effect=replies) as request:
            results, token = smoke.client_login(self.args)
            self.assertEqual(request.call_args.args[3]["otp_id"], "synthetic-otp-id")
            self.assertEqual(token, "synthetic-client-token")
            self.assertEqual(smoke.headers_for({"suggested_base_var": "{{api_url}}"})["t"], token)
        self.assertEqual([record["decoded_body"] for record in results], [{"status": True}] * 2)
        self.assertEqual([record["body_sample"] for record in results], ["", ""])

    def test_admin_scalar_token_stays_in_session_and_out_of_results(self):
        env = {"ADMIN_EMAIL": "fixture@example.test", "ADMIN_PASSWORD": "fixture", "ADMIN_GOOGLE_CODE": "123456"}
        replies = [reply({"challenge": "synthetic-challenge"}), reply("synthetic-admin-token")]
        with patch.dict(os.environ, env, clear=True), patch.object(smoke, "request_once", side_effect=replies):
            results, token = smoke.admin_login(self.args)
            self.assertEqual(token, "synthetic-admin-token")
            self.assertEqual(smoke.headers_for({"suggested_base_var": "{{admin_url}}"})["t"], token)
        self.assertEqual([record["decoded_body"] for record in results], [{"status": True}] * 2)
        self.assertEqual([record["body_sample"] for record in results], ["", ""])

    def test_controlled_client_token_reuse_drops_member_payload(self):
        with patch.dict(os.environ, {"API_TOKEN": "synthetic-client-token"}, clear=True), patch.object(
            smoke, "request_once", return_value=reply({"wallet_password": "synthetic-member-data"})
        ):
            record, = ControlledFlow().client_login(self.args)
        self.assertEqual(record["name"], "client_token_reuse")
        self.assertIs(record["business_status"], True)
        self.assertIsNone(record["data"])
        self.assertNotIn("synthetic-member-data", record["body_sample"])
