"""SMS providers.

For many students a text is the only notification that reliably arrives:
data runs out, but a phone still receives SMS. Termii and Africa's Talking
are both widely used in Nigeria, so either can be selected by configuration
rather than by changing code.
"""

import json
import urllib.error
import urllib.parse
import urllib.request

from flask import current_app


class SmsError(Exception):
    """Raised when a provider rejects or fails to accept a message."""


def _post(url: str, payload: dict, headers: dict, form_encoded: bool = False) -> dict:
    if form_encoded:
        body = urllib.parse.urlencode(payload).encode()
        headers = {**headers, "Content-Type": "application/x-www-form-urlencoded"}
    else:
        body = json.dumps(payload).encode()
        headers = {**headers, "Content-Type": "application/json"}

    request = urllib.request.Request(url, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode() or "{}")
    except urllib.error.HTTPError as error:
        detail = error.read().decode()[:300]
        raise SmsError(f"Provider returned {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise SmsError(f"Could not reach the provider: {error.reason}") from error
    except json.JSONDecodeError as error:
        raise SmsError("Provider returned a response we could not read") from error


def _send_termii(recipient: str, body: str) -> dict:
    api_key = current_app.config.get("TERMII_API_KEY")
    if not api_key:
        raise SmsError("TERMII_API_KEY is not set")

    return _post(
        "https://api.ng.termii.com/api/sms/send",
        {
            "to": recipient,
            "from": current_app.config.get("SMS_SENDER_ID", "Resolve"),
            "sms": body,
            "type": "plain",
            "channel": "generic",
            "api_key": api_key,
        },
        headers={},
    )


def _send_africastalking(recipient: str, body: str) -> dict:
    api_key = current_app.config.get("AFRICASTALKING_API_KEY")
    username = current_app.config.get("AFRICASTALKING_USERNAME")
    if not api_key or not username:
        raise SmsError("AFRICASTALKING_API_KEY and AFRICASTALKING_USERNAME must be set")

    return _post(
        "https://api.africastalking.com/version1/messaging",
        {
            "username": username,
            "to": recipient,
            "message": body,
            "from": current_app.config.get("SMS_SENDER_ID", "Resolve"),
        },
        headers={"apiKey": api_key, "Accept": "application/json"},
        form_encoded=True,
    )


def _send_console(recipient: str, body: str) -> dict:
    """Development sink.

    Writes the message to the log instead of sending it, so the queue can
    be exercised end to end without a provider account.
    """
    current_app.logger.info("SMS to %s: %s", recipient, body)
    return {"status": "logged"}


PROVIDERS = {
    "termii": _send_termii,
    "africastalking": _send_africastalking,
    "console": _send_console,
}


def send(recipient: str, body: str) -> dict:
    name = (current_app.config.get("SMS_PROVIDER") or "").lower()
    if not name:
        raise SmsError("No SMS provider is configured")

    handler = PROVIDERS.get(name)
    if not handler:
        supported = ", ".join(sorted(PROVIDERS))
        raise SmsError(f"Unknown SMS provider '{name}'. Supported: {supported}")

    return handler(recipient, body)
