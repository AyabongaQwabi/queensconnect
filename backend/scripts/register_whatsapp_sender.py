#!/usr/bin/env python3
"""
Register a WhatsApp sender using the Twilio Senders API (v2).

Usage:
  cd backend && python scripts/register_whatsapp_sender.py --name "Your Business Name"
  python scripts/register_whatsapp_sender.py --number +27600173284 --name "Queens Connect" \\
    --webhook-url https://your-app.onrender.com/webhook/twilio/whatsapp --verification-method voice

Requires: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN in environment (or backend/.env).
The first WhatsApp sender on an account must be registered via Twilio Console Self Sign-up;
this script is for additional senders.

Refs:
  https://www.twilio.com/docs/whatsapp/api/senders#verify-a-whatsapp-sender
  https://www.twilio.com/docs/whatsapp/register-senders-using-api
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

import requests

# Load .env from backend/ when run from repo root or backend/
_backend_dir = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(_backend_dir / ".env")
except ImportError:
    pass

SENDERS_BASE = "https://messaging.twilio.com/v2/Channels/Senders"
POLL_INTERVAL_SEC = 20
POLL_TIMEOUT_SEC = 600  # 10 minutes


def e164_validate(number: str) -> bool:
    """Check E.164: leading + and digits only."""
    return bool(re.match(r"^\+[1-9]\d{1,14}$", number.strip()))


def create_sender(
    account_sid: str,
    auth_token: str,
    sender_id: str,
    profile_name: str,
    webhook_url: str | None = None,
    verification_method: str | None = None,
) -> requests.Response:
    """POST to create a WhatsApp sender."""
    payload: dict = {
        "sender_id": f"whatsapp:{sender_id}" if not sender_id.startswith("whatsapp:") else sender_id,
        "profile": {"name": profile_name},
    }
    if webhook_url:
        payload["webhook"] = {
            "callback_url": webhook_url.rstrip("/"),
            "callback_method": "POST",
        }
    if verification_method and verification_method in ("sms", "voice"):
        payload["configuration"] = {"verification_method": verification_method}

    return requests.post(
        SENDERS_BASE,
        json=payload,
        auth=(account_sid, auth_token),
        headers={"Content-Type": "application/json"},
        timeout=30,
    )


def update_sender_verification(
    account_sid: str,
    auth_token: str,
    sid: str,
    verification_code: str,
) -> requests.Response:
    """POST to submit OTP and verify the sender."""
    return requests.post(
        f"{SENDERS_BASE}/{sid}",
        json={"configuration": {"verification_code": verification_code}},
        auth=(account_sid, auth_token),
        headers={"Content-Type": "application/json"},
        timeout=30,
    )


def fetch_sender(account_sid: str, auth_token: str, sid: str) -> requests.Response:
    """GET sender status."""
    return requests.get(
        f"{SENDERS_BASE}/{sid}",
        auth=(account_sid, auth_token),
        timeout=15,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Register a WhatsApp sender via Twilio Senders API (v2).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--number",
        default="+27600173284",
        help="E.164 phone number to register (default: +27600173284)",
    )
    parser.add_argument(
        "-n",
        "--name",
        required=True,
        help="WhatsApp sender display name (required; must follow Meta display name guidelines)",
    )
    parser.add_argument(
        "--webhook-url",
        default=None,
        help="Webhook URL for incoming messages (e.g. https://your-app.onrender.com/webhook/twilio/whatsapp)",
    )
    parser.add_argument(
        "--verification-method",
        choices=["sms", "voice"],
        default=None,
        help="Use voice for OTP instead of SMS (e.g. for Twilio voice numbers)",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Do not prompt for OTP; only create and poll (use when verification is automatic)",
    )
    args = parser.parse_args()

    number = args.number.strip()
    if not e164_validate(number):
        print("Error: --number must be E.164 (e.g. +27600173284)", file=sys.stderr)
        return 1

    account_sid = (os.environ.get("TWILIO_ACCOUNT_SID") or "").strip()
    auth_token = (os.environ.get("TWILIO_AUTH_TOKEN") or "").strip()
    if not account_sid or not auth_token:
        print(
            "Error: Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN (e.g. in backend/.env).",
            file=sys.stderr,
        )
        return 1

    # Create sender
    print(f"Creating sender for {number} with profile name '{args.name}'...")
    resp = create_sender(
        account_sid,
        auth_token,
        number,
        args.name,
        webhook_url=args.webhook_url,
        verification_method=args.verification_method,
    )
    if resp.status_code >= 400:
        print(f"Create failed ({resp.status_code}): {resp.text}", file=sys.stderr)
        # Common Twilio errors: 63110 = number already registered; 63116 = OTP not received
        if "63110" in resp.text:
            print("Hint: This number may already be registered with WhatsApp.", file=sys.stderr)
        elif "63116" in resp.text:
            print("Hint: OTP was not received. Try --verification-method voice or check Error Logs in Twilio Console.", file=sys.stderr)
        return 1

    data = resp.json()
    sid = data.get("sid")
    status = data.get("status", "")
    if not sid:
        print("Create response missing sid:", data, file=sys.stderr)
        return 1

    print(f"Sender created: SID={sid} status={status}")

    # If verification is needed (non-Twilio or voice), prompt for OTP
    needs_otp = status in ("PENDING_VERIFICATION", "VERIFYING") or (
        status == "CREATING" and args.verification_method == "voice"
    )
    if needs_otp and not args.no_verify:
        code = input("Enter the OTP received via SMS or voice: ").strip()
        if not code:
            print("No OTP entered; skipping verify step.", file=sys.stderr)
        else:
            print("Submitting verification code...")
            up = update_sender_verification(account_sid, auth_token, sid, code)
            if up.status_code >= 400:
                print(f"Verify failed ({up.status_code}): {up.text}", file=sys.stderr)
                return 1
            status = up.json().get("status", status)
            print(f"Verification submitted; status={status}")

    # Poll until ONLINE or timeout
    print("Polling for status ONLINE (can take a few minutes)...")
    deadline = time.monotonic() + POLL_TIMEOUT_SEC
    while time.monotonic() < deadline:
        r = fetch_sender(account_sid, auth_token, sid)
        if r.status_code >= 400:
            print(f"Fetch failed ({r.status_code}): {r.text}", file=sys.stderr)
            return 1
        data = r.json()
        status = data.get("status", "")
        print(f"  status={status}")
        if status == "ONLINE":
            print(f"\nDone. Sender SID: {sid}")
            print("Use this SID as TWILIO_WHATSAPP_FROM (or the From value when sending messages).")
            return 0
        if status in ("TWILIO_REVIEW", "DRAFT", "STUBBED"):
            print(f"\nSender is in {status}. Check Twilio Console / Error Logs.", file=sys.stderr)
            return 1
        time.sleep(POLL_INTERVAL_SEC)

    print(f"\nTimeout waiting for ONLINE (last status={status}). Check Twilio Console.", file=sys.stderr)
    print(f"Sender SID: {sid}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
