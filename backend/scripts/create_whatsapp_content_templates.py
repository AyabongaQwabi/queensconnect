#!/usr/bin/env python3
"""
Create Twilio Content Templates for Queens Connect interactive WhatsApp menus.

Creates twilio/quick-reply templates (and twilio/text fallback) for:
- onboarding intent (Borrow / Lend / Other)
- onboarding optional details (Skip / Add details)
- onboarding gender (Male / Female)
- main menu (Taxi, Loans, Stokvel, More)
- loans agent menu (Apply for loan, Check status, Back to menu)
- stokvel agent menu (Create stokvel, Join stokvel, List stokvels, Back)

Usage:
  cd backend && TWILIO_ACCOUNT_SID=... TWILIO_AUTH_TOKEN=... python scripts/create_whatsapp_content_templates.py
  # Optional: submit for WhatsApp approval (for out-of-session sending)
  python scripts/create_whatsapp_content_templates.py --submit-approval

Requires: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN in environment (or backend/.env).
Output: Content SIDs (HX...) to add to .env as TWILIO_CONTENT_*.
Refs: https://www.twilio.com/docs/content/content-api-resources
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests

# Load .env from backend/
_backend_dir = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(_backend_dir / ".env")
    load_dotenv(_backend_dir / "queens_connect" / ".env")
except ImportError:
    pass

CONTENT_API_BASE = "https://content.twilio.com/v1"


def create_content(
    account_sid: str,
    auth_token: str,
    friendly_name: str,
    language: str,
    variables: dict,
    types: dict,
) -> requests.Response:
    """POST to create a Content template."""
    payload = {
        "friendly_name": friendly_name,
        "language": language,
        "variables": variables,
        "types": types,
    }
    return requests.post(
        f"{CONTENT_API_BASE}/Content",
        json=payload,
        auth=(account_sid, auth_token),
        timeout=30,
    )


def submit_approval(
    account_sid: str,
    auth_token: str,
    content_sid: str,
    name: str,
    category: str = "UTILITY",
) -> requests.Response:
    """POST to submit template for WhatsApp approval."""
    return requests.post(
        f"{CONTENT_API_BASE}/Content/{content_sid}/ApprovalRequests/whatsapp",
        json={"name": name, "category": category},
        auth=(account_sid, auth_token),
        headers={"Content-Type": "application/json"},
        timeout=30,
    )


# Template definitions: friendly_name -> (variables, types dict)
TEMPLATES = {
    "qc_onboarding_intent": {
        "variables": {"1": "there"},
        "types": {
            "twilio/quick-reply": {
                "body": "Hi {{1}}! What do you want to do?",
                "actions": [
                    {"title": "Borrow", "id": "intent_borrow"},
                    {"title": "Lend", "id": "intent_lend"},
                    {"title": "Other", "id": "intent_other"},
                ],
            },
            "twilio/text": {
                "body": "Hi {{1}}! What do you want to do? Reply with Borrow, Lend, or Other.",
            },
        },
    },
    "qc_onboarding_optional_details": {
        "variables": {"1": "Friend"},
        "types": {
            "twilio/quick-reply": {
                "body": "Nearly done, {{1}}! Want to add gender and birthday?",
                "actions": [
                    {"title": "Skip", "id": "optional_skip"},
                    {"title": "Add details", "id": "optional_add"},
                ],
            },
            "twilio/text": {
                "body": "Nearly done! Want to add gender and birthday? Reply Skip or Add details.",
            },
        },
    },
    "qc_onboarding_gender": {
        "variables": {"1": "Friend"},
        "types": {
            "twilio/quick-reply": {
                "body": "What's your gender, {{1}}?",
                "actions": [
                    {"title": "Male", "id": "gender_male"},
                    {"title": "Female", "id": "gender_female"},
                ],
            },
            "twilio/text": {
                "body": "What's your gender? Reply Male or Female.",
            },
        },
    },
    "qc_main_menu": {
        "variables": {"1": "Friend"},
        "types": {
            "twilio/quick-reply": {
                "body": "What would you like to do, {{1}}?",
                "actions": [
                    {"title": "Taxi prices", "id": "menu_taxi"},
                    {"title": "Loans", "id": "menu_loans"},
                    {"title": "Stokvel", "id": "menu_stokvel"},
                ],
            },
            "twilio/text": {
                "body": "What would you like to do? Reply with Taxi prices, Loans, Stokvel, or ask in your own words.",
            },
        },
    },
    "qc_loans_menu": {
        "variables": {"1": "Friend"},
        "types": {
            "twilio/quick-reply": {
                "body": "Loans – what do you need, {{1}}?",
                "actions": [
                    {"title": "Apply for loan", "id": "loans_apply"},
                    {"title": "Check status", "id": "loans_status"},
                    {"title": "Back to menu", "id": "menu_back"},
                ],
            },
            "twilio/text": {
                "body": "Loans – reply with Apply for loan, Check status, or Back to menu.",
            },
        },
    },
    "qc_stokvel_menu": {
        "variables": {"1": "Friend"},
        "types": {
            "twilio/quick-reply": {
                "body": "Stokvel – what would you like, {{1}}?",
                "actions": [
                    {"title": "Create stokvel", "id": "stokvel_create"},
                    {"title": "Join stokvel", "id": "stokvel_join"},
                    {"title": "List stokvels", "id": "stokvel_list"},
                ],
            },
            "twilio/text": {
                "body": "Stokvel – reply with Create stokvel, Join stokvel, or List stokvels.",
            },
        },
    },
}

# Map friendly_name -> env var name for Content SID
ENV_KEYS = {
    "qc_onboarding_intent": "TWILIO_CONTENT_ONBOARDING_INTENT",
    "qc_onboarding_optional_details": "TWILIO_CONTENT_ONBOARDING_OPTIONAL_DETAILS",
    "qc_onboarding_gender": "TWILIO_CONTENT_ONBOARDING_GENDER",
    "qc_main_menu": "TWILIO_CONTENT_MAIN_MENU",
    "qc_loans_menu": "TWILIO_CONTENT_LOANS_MENU",
    "qc_stokvel_menu": "TWILIO_CONTENT_STOKVEL_MENU",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create Twilio Content templates for Queens Connect WhatsApp menus.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--submit-approval",
        action="store_true",
        help="Submit each created template for WhatsApp approval (UTILITY category)",
    )
    args = parser.parse_args()

    account_sid = (os.environ.get("TWILIO_ACCOUNT_SID") or "").strip()
    auth_token = (os.environ.get("TWILIO_AUTH_TOKEN") or "").strip()
    if not account_sid or not auth_token:
        print(
            "Error: Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN (e.g. in backend/.env).",
            file=sys.stderr,
        )
        return 1

    created = {}
    for friendly_name, spec in TEMPLATES.items():
        print(f"Creating {friendly_name}...")
        resp = create_content(
            account_sid,
            auth_token,
            friendly_name=friendly_name,
            language="en",
            variables=spec["variables"],
            types=spec["types"],
        )
        if resp.status_code >= 400:
            print(f"  Failed ({resp.status_code}): {resp.text}", file=sys.stderr)
            continue
        data = resp.json()
        sid = data.get("sid")
        if not sid:
            print(f"  Response missing sid: {data}", file=sys.stderr)
            continue
        created[friendly_name] = sid
        print(f"  SID: {sid}")

        if args.submit_approval:
            approval_name = friendly_name
            print(f"  Submitting for WhatsApp approval as {approval_name}...")
            ar = submit_approval(account_sid, auth_token, sid, approval_name)
            if ar.status_code >= 400:
                print(f"  Approval submit failed ({ar.status_code}): {ar.text}", file=sys.stderr)
            else:
                print(f"  Approval submitted.")

    if not created:
        print("No templates created.", file=sys.stderr)
        return 1

    print("\n--- Add these to backend/.env ---")
    for friendly_name, sid in created.items():
        key = ENV_KEYS.get(friendly_name, friendly_name.upper().replace("-", "_"))
        print(f"{key}={sid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
