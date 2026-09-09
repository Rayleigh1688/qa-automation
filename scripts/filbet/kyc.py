"""FILBET kyc operations on one ControlledFlow instance."""
from __future__ import annotations
import argparse
import mimetypes
import os
import ssl
import time
import uuid
from pathlib import Path
from urllib.request import Request, urlopen


class KycOperations:
    def upload_kyc_attachment(self, args: argparse.Namespace, image_path: Path, field_name: str) -> dict[str, object]:
        boundary = f"----qa-kyc-{uuid.uuid4().hex}"
        content_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
        filename = f"{field_name}_{int(time.time() * 1000)}{image_path.suffix.lower()}"
        prefix = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode("utf-8")
        payload = prefix + image_path.read_bytes() + f"\r\n--{boundary}--\r\n".encode("utf-8")
        upload_row = self.row("POST", "{{api_url}}/member/oss/upload")
        url = self.smoke.resolve_url(upload_row["clean_url"])
        headers = self.smoke.headers_for(upload_row)
        headers["content-type"] = f"multipart/form-data; boundary={boundary}"
        request = Request(url, data=payload, method="POST", headers=headers)
        context = ssl._create_unverified_context() if args.insecure else None
        started = time.monotonic()
        try:
            with urlopen(request, timeout=args.timeout, context=context) as response:
                body_bytes = response.read()
                decoded, sample = self.smoke.decode_body_sample(body_bytes)
                result = {
                    "priority": "CONTROLLED",
                    "method": "POST",
                    "url": url,
                    "status": response.status,
                    "elapsed_ms": int((time.monotonic() - started) * 1000),
                    "decoded_body": decoded,
                    "body_sample": sample,
                }
        except Exception as error:
            raise SystemExit(f"KYC attachment upload failed for {field_name}: {error}") from error
        data = self.data_of(result)
        object_key = str(data.get("object_key") or "") if isinstance(data, dict) else ""
        if not self.business_ok(result) or not object_key:
            raise SystemExit(f"KYC attachment upload rejected for {field_name}: {result.get('body_sample')}")
        return {
            "name": f"kyc_upload_{field_name}",
            "url": result.get("url"),
            "http_status": result.get("status"),
            "business_status": True,
            "object_key": object_key,
            "elapsed_ms": result.get("elapsed_ms"),
        }


    def submit_kyc(self, args: argparse.Namespace) -> list[dict[str, object]]:
        image_path = Path(args.kyc_image)
        if not image_path.is_file():
            raise SystemExit(f"KYC image does not exist: {image_path}")

        detail_before = self.smoke.request_once(
            self.row("GET", "{{api_url}}/member/kyc/detail"), args.timeout, args.insecure
        )
        profile = self.data_of(detail_before)
        if not isinstance(profile, dict):
            raise SystemExit("cannot read KYC profile before submission")
        if int(profile.get("kyc_status") or 0) != 0:
            raise SystemExit(f"KYC account is not submit-ready: kyc_status={profile.get('kyc_status')}")

        shops_result = self.smoke.request_once(
            self.row("POST", "{{api_url}}/member/kyc/shops"), args.timeout, args.insecure
        )
        shops_data = self.data_of(shops_result)
        shops = self.list_rows(shops_data)
        if not shops and isinstance(shops_data, list):
            shops = [item for item in shops_data if isinstance(item, dict)]
        def branch_label(item: dict[str, object]) -> str:
            return str(item.get("label") or item.get("name") or item.get("address") or "")

        branch = next(
            (
                item
                for item in shops
                if branch_label(item) == args.kyc_nearest_branch
                or str(item.get("value") or "") == args.kyc_nearest_branch
            ),
            None,
        )
        if branch is None and "Taft Ave" in args.kyc_nearest_branch:
            branch = next((item for item in shops if "Taft Ave, Pasay" in branch_label(item)), None)
        if branch is None:
            preview = [str(item.get("label") or item.get("name") or item.get("address") or "") for item in shops[:5]]
            raise SystemExit(f"KYC branch is not available: {args.kyc_nearest_branch}; available={preview}")

        uploads = [
            self.upload_kyc_attachment(args, image_path, "front_side_of_id"),
            self.upload_kyc_attachment(args, image_path, "back_side_of_id"),
            self.upload_kyc_attachment(args, image_path, "selfie_with_id_card"),
        ]
        attachment_keys = [str(item["object_key"]) for item in uploads]
        uid = str(profile.get("uid") or "")
        body = {
            "attachments": {
                "face": attachment_keys[0],
                "idPhoto": attachment_keys[1],
                "selfieWithIDPhotoPath": attachment_keys[2],
            },
            "birthday": args.kyc_birthday,
            "country_code": str(profile.get("country_code") or "63"),
            "current_address": args.kyc_current_address,
            "first_name": args.kyc_first_name,
            "middle_name": args.kyc_middle_name,
            "last_name": args.kyc_last_name,
            "nationality": args.kyc_nationality,
            "gender": args.kyc_gender,
            "id_number": args.kyc_id_number or uid,
            "id_type": args.kyc_id_type,
            "nature_of_work": args.kyc_nature_of_work,
            "nearest_branch": branch_label(branch),
            "shop_id": int(branch.get("value") or branch.get("id") or branch.get("shop_id") or 0),
            "occupation": args.kyc_nature_of_work,
            "permanent_address": args.kyc_permanent_address,
            "phone": str(profile.get("phone") or ""),
            "place_of_birth": args.kyc_place_of_birth,
            "source_of_income": args.kyc_source_of_income,
        }
        submit_result = self.smoke.request_once(
            self.row("POST", "{{api_url}}/member/kyc/insert"),
            args.timeout,
            args.insecure,
            body,
            args.body_format,
        )
        detail_after = self.smoke.request_once(
            self.row("GET", "{{api_url}}/member/kyc/detail"), args.timeout, args.insecure
        )
        return [
            self.result_record("kyc_detail_before", detail_before),
            self.result_record("kyc_shops", shops_result),
            *uploads,
            self.result_record("kyc_submit", submit_result),
            self.result_record("kyc_detail_after", detail_after),
        ]


    def find_kyc_record(self, args: argparse.Namespace, uid: str) -> tuple[dict[str, object], dict[str, object] | None]:
        def request_list(body: dict[str, object]) -> dict[str, object]:
            return self.smoke.request_once(
                self.row("POST", "{{admin_url}}/admin/kyc/list", "{{admin_url}}"),
                args.timeout,
                args.insecure,
                body,
                args.body_format,
            )

        query: dict[str, object] = {"page": 1, "page_size": 50, "source": "default"}
        if uid:
            query["uid"] = uid
        result = request_list(query)
        rows = self.list_rows(self.data_of(result))
        target = next((item for item in rows if str(item.get("uid") or item.get("id") or "") == uid), None)
        if uid and target is None:
            result = request_list({"page": 1, "page_size": 100, "source": "default"})
            rows = self.list_rows(self.data_of(result))
            target = next((item for item in rows if str(item.get("uid") or item.get("id") or "") == uid), None)
        record = self.result_record("admin_kyc_list", result)
        record["matched_record"] = target
        return record, target


    def approve_kyc(self, args: argparse.Namespace, uid: str) -> list[dict[str, object]]:
        list_record, target = self.find_kyc_record(args, uid)
        records = [list_record]
        if not target:
            records.append({
                "name": "admin_kyc_approve",
                "business_status": False,
                "reason": f"KYC record not found for uid={uid or '<missing>'}",
            })
            return records
        target_uid = str(target.get("uid") or uid)
        body = self.add_approval_code({"uid": target_uid, "comment": args.approval_desc}, args)
        result = self.smoke.request_once(
            self.row("POST", "{{admin_url}}/admin/kyc/approve", "{{admin_url}}"),
            args.timeout,
            args.insecure,
            body,
            args.body_format,
        )
        approve_record = self.result_record("admin_kyc_approve", result)
        approve_record["uid"] = target_uid
        records.append(approve_record)
        if not self.business_ok(result):
            return records

        detail, profile, attempts = self.wait_for_kyc_status(args, 5)
        detail_record = self.result_record("kyc_detail_after_approval", detail)
        approved = isinstance(profile, dict) and int(profile.get("kyc_status") or 0) == 5
        detail_record["business_status"] = approved
        detail_record["expected_kyc_status"] = 5
        detail_record["actual_kyc_status"] = profile.get("kyc_status") if isinstance(profile, dict) else None
        detail_record["poll_attempts"] = attempts
        records.append(detail_record)
        return records


    def resolve_kyc_uid(self, args: argparse.Namespace, profile: object = None) -> str:
        if args.kyc_uid:
            return args.kyc_uid
        profile_uid = str(profile.get("uid") or "") if isinstance(profile, dict) else ""
        if args.use_register_phone:
            return profile_uid
        return os.environ.get("KYC_CLIENT_UID", "") or profile_uid


    def wait_for_kyc_status(self, 
        args: argparse.Namespace,
        expected_status: int,
    ) -> tuple[dict[str, object], object, int]:
        attempts = max(1, int(getattr(args, "kyc_status_attempts", 1)))
        interval = max(0.0, float(getattr(args, "kyc_status_interval", 0)))
        result: dict[str, object] = {}
        profile: object = None
        for attempt in range(1, attempts + 1):
            result = self.smoke.request_once(
                self.row("GET", "{{api_url}}/member/kyc/detail"), args.timeout, args.insecure
            )
            profile = self.data_of(result)
            actual = int(profile.get("kyc_status") or 0) if isinstance(profile, dict) else -1
            if actual == expected_status or attempt == attempts:
                return result, profile, attempt
            time.sleep(interval)
        return result, profile, attempts


