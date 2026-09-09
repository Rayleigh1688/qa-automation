"""FILBET operation flags and legacy defaults."""
DEFAULT_REGISTER_PHONE_START = "9000000001"

DEFAULT_WITHDRAW_AMOUNT = "100"

OPERATION_FLAGS = {
    "register": "register",
    "kyc-submit": "submit_kyc",
    "kyc-approve": "approve_kyc",
    "deposit-create": "deposit",
    "deposit-check-client": "check_client_deposit_list",
    "deposit-check-admin": "check_admin_deposit_list",
    "deposit-approve": "approve_deposit",
    "withdraw-create": "withdraw",
    "withdraw-account-prepare": "prepare_withdraw_account",
    "withdraw-check-client": "check_client_withdraw_list",
    "withdraw-check-admin": "check_admin_withdraw_list",
    "withdraw-approve": "approve_withdraw",
    "turnover-clear": "clear_turnover",
}

CLIENT_OPERATION_LANES = {
    "kyc-submit": "KYC_CLIENT",
    "kyc-approve": "KYC_CLIENT",
    "deposit-create": "WRITE_CLIENT",
    "deposit-check-client": "WRITE_CLIENT",
    "withdraw-create": "WITHDRAW_CLIENT",
    "withdraw-check-client": "WITHDRAW_CLIENT",
}
