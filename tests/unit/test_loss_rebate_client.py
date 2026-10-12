import unittest
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from filbet.loss_rebate import ContractError
from filbet.loss_rebate_client import analyse, analyse_recorded, data_object, eligible, game_id, run_client_readonly, source_array


class ClientLossRebateContract(unittest.TestCase):
    def test_nullable_recommendations_and_encoded_arrays(self):
        self.assertEqual(source_array(None), [])
        self.assertEqual(source_array('[{"id":"1"}]'), [{"id": "1"}])
        with self.assertRaises(ContractError):
            source_array({"d": []})
        with self.assertRaises(ContractError):
            data_object({"http": 200, "body": {"status": False, "data": {"game_list": []}}})

    def test_frontend_eligibility_is_code_and_image_not_guessed_compliance(self):
        game = {"id": "catalog-id", "game_id": "provider-id", "code": "  code  ", "img": "img", "compliance": 0}
        self.assertEqual(game_id(game), "catalog-id")
        self.assertTrue(eligible(game))
        self.assertFalse(eligible({**game, "img": " "}))
        self.assertFalse(eligible({**game, "code": ""}))

    def test_observed_null_detail_uses_fallback_and_numeric_rates(self):
        rates = [{"level": "bronze", "ratio": "2.00"}]
        config = {"venue": [{"game_class": "3", "rebate_ratio": rates}], "games": [{"list": ["first"], "state": 0}]}
        admin = {"response": {"http": 200, "body": {"status": True, "data": {"d": [{"ty": "41", "config": json.dumps(config), "summary": "richtext"}]}}}}
        detail = {"http": 200, "body": {"status": True, "data": {"start_time": 1, "end_time": 2, "cur_time": 1, "state": 1, "detail": "richtext", "game_list": None, "conf": [{"level": "bronze", "ratio": "2"}]}}}
        fallback = {"http": 200, "body": {"status": True, "data": {"d": [{"id": "fallback", "code": "code", "img": "img"}], "t": 1}}}
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "admin.json"
            path.write_text(json.dumps(admin))
            result = analyse(detail, fallback, path)
            self.assertTrue(result["rate_table_matches_saved_slot"])
            self.assertTrue(result["detail_text_matches_saved_summary"])
            self.assertEqual(result["selection_source"], "Slot Popular fallback")
            self.assertFalse(result["selected_matches_first_group"])
            detail["body"]["data"].pop("game_list")
            with self.assertRaises(ContractError):
                analyse(detail, fallback, path)

    def test_recorded_analysis_preserves_capture_and_never_constructs_session(self):
        rates = [{"level": "bronze", "ratio": "2.00"}]
        config = {"venue": [{"game_class": "3", "rebate_ratio": rates}], "games": [{"list": ["first"], "state": 0}]}
        admin = {"response": {"http": 200, "body": {"status": True, "data": {"d": [{"ty": "41", "config": config, "summary": "richtext"}]}}}}
        detail = {"http": 200, "body": {"status": True, "data": {"start_time": 1, "end_time": 2, "cur_time": 1, "state": 1, "detail": "richtext", "game_list": None, "conf": rates}}}
        fallback = {"http": 200, "body": {"status": True, "data": {"d": [{"id": "fallback", "code": "code", "img": "img"}], "t": 1}}}
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            admin_path = root / "admin.json"
            admin_path.write_text(json.dumps(admin))
            requests = []
            for index, response in enumerate((detail, fallback)):
                path = root / f"response-{index}.json"
                path.write_text(json.dumps({"response": response}))
                requests.append({"method": "GET", "private_evidence": path.name})
            source_time = "2026-10-12T16:50:48+08:00"
            original = root / "original.json"
            original.write_text(json.dumps({"mode": "directed-client-readonly", "run_id": "original-batch",
                "source_time": source_time, "requests": requests, "boundaries": ["API子项"], "error": "old parsing failure"}))
            original_bytes = original.read_bytes()
            args = SimpleNamespace(recorded=original, admin_snapshot=admin_path, selection_context=None, out=root)
            with patch("filbet.loss_rebate_client.ROOT", root), patch("filbet.loss_rebate_client.Session") as session, redirect_stdout(io.StringIO()):
                self.assertEqual(analyse_recorded(args), 0)
            session.assert_not_called()
            result_path = next(root.glob("client-readonly-*-analysis/result.json"))
            result = json.loads(result_path.read_text())
            self.assertEqual(original.read_bytes(), original_bytes)
            self.assertEqual(result["source_time"], source_time)
            self.assertEqual(result["source_run_id"], "original-batch")
            self.assertEqual(result["classification"]["source_time"], source_time)
            self.assertEqual(result["classification"]["source_run_id"], "original-batch")
            self.assertNotEqual(result["classification"]["reviewed_at"], source_time)
            self.assertEqual(result["mode"], "recorded-readonly-reassessment")
            self.assertEqual(result["network_requests"], 0)
            self.assertEqual(result["requests"], requests)
            self.assertNotIn("error", result)
            html = (result_path.parent / "views/results.html").read_text()
            self.assertIn("2026-10-12 16:50:48", html)
            self.assertIn("original-batch", html)
            self.assertIn("新请求0次", html)
            self.assertIn("离线", html)

    def test_execution_exit_code_tracks_business_failure_after_successful_requests(self):
        for client_ratio, expected_exit in (("3", 1), ("2", 0)):
            with self.subTest(client_ratio=client_ratio), TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                admin_path = root / "admin.json"
                config = {"venue": [{"game_class": "3", "rebate_ratio": [{"level": "bronze", "ratio": "2"}]}],
                          "games": [{"list": ["first"], "state": 0}]}
                admin_path.write_text(json.dumps({"response": {"http": 200, "body": {"status": True,
                    "data": {"d": [{"ty": "41", "config": config, "summary": "richtext"}]}}}}))
                detail = {"http": 200, "body": {"status": True, "data": {
                    "start_time": 1, "end_time": 2, "cur_time": 1, "state": 1, "detail": "richtext",
                    "game_list": None, "conf": [{"level": "bronze", "ratio": client_ratio}]}}}
                fallback = {"http": 200, "body": {"status": True, "data": {"d": [], "t": 0}}}
                args = SimpleNamespace(env=".env.fat", execute=True, insecure=False, out=root, admin_snapshot=admin_path)
                with patch("filbet.loss_rebate_client.ROOT", root), \
                     patch("filbet.loss_rebate_client.load_environment", return_value={"API_URL": "https://client-fat.filbet2025.com"}), \
                     patch("filbet.loss_rebate_client.Session") as factory, redirect_stdout(io.StringIO()):
                    session = factory.return_value
                    session.request.side_effect = [detail, fallback]
                    self.assertEqual(run_client_readonly(args), expected_exit)
                session.login_client_password.assert_called_once_with()
                self.assertEqual([call.args for call in session.request.call_args_list],
                                 [("GET", "/promo/net/loss/detail"), ("GET", "/member/game/listRw")])
                self.assertEqual(session.token, "")
                result = json.loads(next(root.glob("client-readonly-*/result.json")).read_text())
                self.assertNotIn("error", result)
                rates = next(item for item in result["results"] if item["check_key"] == "slot-rates")
                self.assertEqual(rates["status"], "FAIL" if expected_exit else "PASS")
