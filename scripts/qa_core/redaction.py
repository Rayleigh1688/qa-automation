"""Pure log redaction shared by runners; never loads credentials."""
import re

SENSITIVE_MARKERS = ("PASSWORD", "SECRET", "TOKEN", "OTP", "CODE", "PHONE", "EMAIL", "DEVICE")

def sanitize_error(error: BaseException | str, env: dict[str, str]) -> str:
    message = str(error) or (type(error).__name__ if isinstance(error, BaseException) else "unknown error")
    for name, value in env.items():
        if len(value) >= 4 and any(marker in name.upper() for marker in SENSITIVE_MARKERS):
            message = message.replace(value, "<redacted>")
    message = re.sub(
        r"([?&](?:token|code|otp|phone|email|uid|device_id|x-device-id)=)[^&\s]+",
        r"\1<redacted>",
        message,
        flags=re.IGNORECASE,
    )
    return message[:2000]

def display_command(command: list[str], sensitive_flags: set[str]) -> str:
    visible: list[str] = []
    redact_next = False
    for value in command:
        if redact_next:
            visible.append("<redacted>")
            redact_next = False
            continue
        visible.append(value)
        redact_next = value in sensitive_flags
    return " ".join(visible)
