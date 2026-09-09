"""Independent state for a controlled API flow; no login during construction."""
from pathlib import Path
import os
from totp import current_totp
from . import smoke
from .constants import OPERATION_FLAGS
from .common import CommonOperations
from .auth import AuthOperations
from .wallet import WalletOperations
from .registration import RegistrationOperations
from .kyc import KycOperations
from .turnover import TurnoverOperations
from .deposit import DepositOperations
from .withdrawal import WithdrawalOperations
from .flow import FlowOperations


class ControlledFlow(
    CommonOperations, AuthOperations, WalletOperations, RegistrationOperations,
    KycOperations, TurnoverOperations, DepositOperations, WithdrawalOperations, FlowOperations,
):
    OPERATION_FLAGS = OPERATION_FLAGS
    current_totp = staticmethod(current_totp)

    def __init__(self):
        self.smoke = smoke
        self.PHONE_CURSOR_DIR = Path(__file__).resolve().parents[2] / 'api/local-state'
        self.ACTIVE_ARGS = None
        self.ACTIVE_RECORDS = None
        self.OPERATION_REPORT_WRITTEN = False
        self.LAST_APPROVAL_CODE = ''

    def execute(self):
        try:
            self.main()
        except BaseException as error:
            if (
                self.ACTIVE_ARGS
                and (self.ACTIVE_ARGS.operation or self.ACTIVE_ARGS.flow_name)
                and not self.OPERATION_REPORT_WRITTEN
            ):
                message = str(error) or type(error).__name__
                sensitive_markers = ("PASSWORD", "SECRET", "TOKEN", "OTP", "CODE", "PHONE", "EMAIL")
                for name, value in os.environ.items():
                    if value and any(marker in name.upper() for marker in sensitive_markers):
                        message = message.replace(value, "<redacted>")
                message = message[:1000]
                failure_records = list(self.ACTIVE_RECORDS or [])
                failure_records.append({
                    "name": "operation_error",
                    "business_status": False,
                    "reason": message,
                })
                try:
                    self.finish(self.ACTIVE_ARGS, failure_records)
                except BaseException:
                    pass
                raise SystemExit(message) from None
            raise
