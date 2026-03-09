"""
Lending registration and flows tools.
- Didit.me KYC verification and lender/borrower profile creation.
- Lending & Borrowing flows: loan_requests, loans, lender_views, and WhatsApp notifications via Twilio.
- Yoco payment links for unlock fees; pending_unlocks + callback to complete unlock after payment.
"""
import json
import logging
import os
import random
import string
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from google.adk.tools import FunctionTool

from queens_connect import config as qc_config

from .firebase_tools import _get_db, get_user, update_user
from .gamification_tools import award_points
from .yoco import create_paylink, fetch_payment_link_status

logger = logging.getLogger("queens_connect.tools.lending")

DIDIT_API_BASE = "https://verification.didit.me/v3"
FACE_MATCH_APPROVED_THRESHOLD = 60

ALLOWED_BANKS = {"capitec", "fnb", "standard_bank", "absa", "other"}
DISBURSEMENT_METHODS = {"immediate_eft", "atm_voucher"}
DEFAULT_LOAN_PAGE_SIZE = 3

# Human-readable loan request ID: LR-YYMMDD-XXXX (e.g. LR-260226-A7K2)
_LOAN_REQUEST_ID_CHARS = string.ascii_uppercase + string.digits


def _generate_loan_request_id() -> str:
    """Generate a human-readable loan request ID: LR-YYMMDD-XXXX."""
    now = datetime.utcnow()
    date_part = now.strftime("%y%m%d")
    random_part = "".join(random.choices(_LOAN_REQUEST_ID_CHARS, k=4))
    return f"LR-{date_part}-{random_part}"


def create_verification_link(
    wa_number: str,
    full_name: str,
    id_number: str,
    address: str,
) -> dict[str, Any]:
    """
    Create a Didit.me verification session and save session_id/session_token to user.
    Name, ID, address are for our records and lender/borrower profile displayName; not sent to Didit at creation.
    Returns verification URL and a short message for the agent to send (reply DONE when finished).
    """
    wa = (wa_number or "").strip()
    if not wa:
        return {"status": "error", "error_message": "wa_number required"}
    api_key = os.environ.get("DIDIT_API_KEY")
    workflow_id = os.environ.get("DIDIT_WORKFLOW_ID")
    if not api_key or not workflow_id:
        logger.warning("DIDIT_API_KEY or DIDIT_WORKFLOW_ID not set")
        return {"status": "error", "error_message": "Verification not configured."}
    body: dict[str, Any] = {"workflow_id": workflow_id, "vendor_data": wa}
    try:
        res = requests.post(
            f"{DIDIT_API_BASE}/session/",
            headers={"x-api-key": api_key, "Content-Type": "application/json"},
            json=body,
            timeout=15,
        )
        res.raise_for_status()
        data = res.json()
    except requests.RequestException as e:
        logger.exception("Didit create session failed: %s", e)
        return {"status": "error", "error_message": f"Could not create verification link: {e}"}
    session_id = data.get("session_id")
    session_token = data.get("session_token")
    url = data.get("url")
    if not session_id or not session_token or not url:
        return {"status": "error", "error_message": "Didit response missing session_id, session_token or url."}
    out = update_user(wa, {"diditSessionId": session_id, "diditSessionToken": session_token})
    #out = update_user(wa, {"diditSessionId": "4c1aa613-e5ba-402b-8aa5-81e5ff893fd6", "diditSessionToken": session_token})
    if out.get("status") != "success":
        return {"status": "error", "error_message": out.get("error_message", "Could not save session to user.")}
    logger.info("create_verification_link wa=%s session_id=%s", wa[:6] + "***", session_id)
    return {
        "status": "success",
        "url": url,
        "message": f"Done! Open this link to do the quick ID + face check: {url} When finished, reply DONE here.",
    }


def check_verification_result(wa_number: str) -> dict[str, Any]:
    """
    Get Didit.me decision for the user's current session (uses diditSessionId from user doc).
    On success: write verifications/{waNumber}, update user kycVerifiedAt and kycStatus; return approved.
    On failure: set kycStatus failed and return message for retry.
    Does not create lender/borrower doc; agent calls create_lender_profile_tool / create_borrower_profile_tool after.
    """
    wa = (wa_number or "").strip()
    if not wa:
        return {"status": "error", "approved": False, "error_message": "wa_number required"}
    user_out = get_user(wa)
    if not user_out.get("exists"):
        return {"status": "error", "approved": False, "error_message": "User not found."}
    didit_session_id = user_out.get("diditSessionId")
    if not didit_session_id:
        return {"status": "error", "approved": False, "error_message": "No verification session found. Start verification first."}
    api_key = os.environ.get("DIDIT_API_KEY")
    if not api_key:
        return {"status": "error", "approved": False, "error_message": "Verification not configured."}
    try:
        logger.info("Checking Didit decision for session %s", didit_session_id)
        res = requests.get(
            f"{DIDIT_API_BASE}/session/{didit_session_id}/decision/",
            headers={"x-api-key": api_key},
            timeout=15,
        )
        res.raise_for_status()
        decision = res.json()
    except requests.RequestException as e:
        logger.exception("Didit decision fetch failed: %s", e)
        return {"status": "error", "approved": False, "error_message": str(e)}
    id_verifications = decision.get("id_verifications") or []
    logger.info("id_verifications: %s", id_verifications)
    face_matches = decision.get("face_matches") or []
    logger.info("face_matches: %s", face_matches)
    id_ok = id_verifications[0].get("status") == "Approved" if id_verifications else False
    face_ok = (
        len(face_matches) == 0
        or any(
            f.get("status") == "Approved"
            or (isinstance(f.get("score"), (int, float)) and f.get("score", 0) >= FACE_MATCH_APPROVED_THRESHOLD)
            for f in face_matches
        )
    )
    approved = id_ok and face_ok
    try:
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP
    except ImportError:
        from google.cloud.firestore import SERVER_TIMESTAMP
    db = _get_db()
    now = SERVER_TIMESTAMP
    if approved:
        db.collection("verifications").document(wa).set({
            "waNumber": wa,
            "sessionId": didit_session_id,
            "status": "verified",
            "rawResponse": decision,
            "createdAt": now,
        })
        update_user(wa, {"kycVerifiedAt": now, "kycStatus": "verified"})
        logger.info("check_verification_result approved wa=%s", wa[:6] + "***")
        return {"status": "success", "approved": True, "message": "Verification approved. You can now create lender/borrower profile."}
    else:
        update_user(wa, {"kycStatus": "failed"})
        return {"status": "success", "approved": False, "message": "Eish, something didn't match up. Want to try again? Reply YES for a new link."}


def create_lender_profile(
    wa_number: str,
    display_name: str,
    id_number: str | None = None,
    address: str | None = None,
) -> dict[str, Any]:
    """
    Create lenders/{waNumber} with minimal required fields and schema defaults.
    Call only after KYC is verified. Fails if doc already exists.
    Optional id_number (SA ID 13 digits) and address match loans_registration_agent flow.
    """
    wa = (wa_number or "").strip()
    if not wa:
        return {"status": "error", "error_message": "wa_number required"}
    if not (display_name or "").strip():
        return {"status": "error", "error_message": "display_name required"}
    try:
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP
    except ImportError:
        from google.cloud.firestore import SERVER_TIMESTAMP
    db = _get_db()
    ref = db.collection("lenders").document(wa)
    if ref.get().exists:
        return {"status": "error", "error_message": "Lender profile already exists."}
    now = SERVER_TIMESTAMP
    doc: dict[str, Any] = {
        "lenderUid": wa,
        "displayName": (display_name or "").strip(),
        "maxAmountCents": 50000,
        "maxDurationDays": 30,
        "interestRatePercent": 0,
        "currentAvailableCents": 0,
        "maxLoansAtOnce": 3,
        "reputationScore": 0.0,
        "totalLoansGiven": 0,
        "totalRepaid": 0,
        "totalDefaulted": 0,
        "totalValueRepaidCents": 0,
        "badges": [],
        "preferredLocations": [],
        "preferredBanks": [],
        "status": "active",
        "verifiedAt": now,
        "lendingSince": now,
        "lastActive": now,
        "createdAt": now,
        "updatedAt": now,
    }
    if (id_number or "").strip():
        doc["idNumber"] = (id_number or "").strip()
    if (address or "").strip():
        doc["address"] = (address or "").strip()
    ref.set(doc)
    logger.info("create_lender_profile wa=%s", wa[:6] + "***")
    return {"status": "success", "lenderUid": wa}


def create_borrower_profile(
    wa_number: str,
    display_name: str,
    id_number: str | None = None,
    address: str | None = None,
    verified: bool = True,
) -> dict[str, Any]:
    """
    Create borrowers/{waNumber} with minimal required fields and schema defaults.
    When verified=True (default), set verifiedAt=now (post-KYC). When verified=False,
    create profile as unverified (e.g. after user provides details, before Didit check).
    Fails if doc already exists. Optional id_number and address match loans_registration_agent flow.
    """
    wa = (wa_number or "").strip()
    if not wa:
        return {"status": "error", "error_message": "wa_number required"}
    if not (display_name or "").strip():
        return {"status": "error", "error_message": "display_name required"}
    try:
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP
    except ImportError:
        from google.cloud.firestore import SERVER_TIMESTAMP
    db = _get_db()
    ref = db.collection("borrowers").document(wa)
    if ref.get().exists:
        return {"status": "error", "error_message": "Borrower profile already exists."}
    now = SERVER_TIMESTAMP
    doc: dict[str, Any] = {
        "borrowerUid": wa,
        "displayName": (display_name or "").strip(),
        "totalLoansTaken": 0,
        "totalRepaidOnTime": 0,
        "totalRepaidLate": 0,
        "totalDefaulted": 0,
        "totalAmountRepaidCents": 0,
        "totalAmountOwingCents": 0,
        "currentActiveLoansCount": 0,
        "reputationScore": 0.0,
        "badges": [],
        "preferredBanks": [],
        "status": "active",
        "createdAt": now,
        "updatedAt": now,
    }
    if verified:
        doc["verifiedAt"] = now
    else:
        doc["verifiedAt"] = None
    if (id_number or "").strip():
        doc["idNumber"] = (id_number or "").strip()
    if (address or "").strip():
        doc["address"] = (address or "").strip()
    ref.set(doc)
    logger.info("create_borrower_profile wa=%s verified=%s", wa[:6] + "***", verified)
    return {"status": "success", "borrowerUid": wa}


def update_borrower_verified(wa_number: str) -> dict[str, Any]:
    """
    Set borrowers/{waNumber}.verifiedAt to now (mark as verified after KYC approval).
    Call after check_verification_result returns approved for a borrower who was created unverified.
    """
    wa = (wa_number or "").strip()
    if not wa:
        return {"status": "error", "error_message": "wa_number required"}
    try:
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP
    except ImportError:
        from google.cloud.firestore import SERVER_TIMESTAMP
    db = _get_db()
    ref = db.collection("borrowers").document(wa)
    snap = ref.get()
    if not snap.exists:
        return {"status": "error", "error_message": "Borrower profile not found."}
    now = SERVER_TIMESTAMP
    ref.update({"verifiedAt": now, "updatedAt": now})
    logger.info("update_borrower_verified wa=%s", wa[:6] + "***")
    return {"status": "success", "borrowerUid": wa}


def get_lender_or_borrower(wa_number: str) -> dict[str, Any]:
    """
    Check if user has a lender or borrower profile. Returns which profile exists and, for borrowers, whether verified.
    Used by loans_agent and lending_agent to decide routing and whether borrower can request a loan.
    """
    wa = (wa_number or "").strip()
    if not wa:
        return {"status": "error", "error_message": "wa_number required", "hasLender": False, "hasBorrower": False}
    db = _get_db()
    lender_ref = db.collection("lenders").document(wa)
    borrower_ref = db.collection("borrowers").document(wa)
    has_lender = lender_ref.get().exists
    borrower_snap = borrower_ref.get()
    has_borrower = borrower_snap.exists
    borrower_verified = False
    if has_borrower and borrower_snap.exists:
        data = borrower_snap.to_dict() or {}
        borrower_verified = data.get("verifiedAt") is not None
    profiles = []
    if has_lender:
        profiles.append("lender")
    if has_borrower:
        profiles.append("borrower")
    return {
        "status": "success",
        "hasLender": has_lender,
        "hasBorrower": has_borrower,
        "borrowerVerified": borrower_verified,
        "profiles": profiles,
        "needsRegistration": not (has_lender or has_borrower),
    }


def get_lender_and_borrower_profile_summaries(wa_number: str) -> Dict[str, Any]:
    """
    Fetch minimal lender and/or borrower profile data for session state.
    Used by the agent runner to refresh session state from Firestore so the agent
    can see if the user has already joined the loans programme without re-asking.
    Returns lenderProfile (dict or None), borrowerProfile (dict or None), and
    lenderOrBorrowerSummary: { hasLender, hasBorrower, borrowerVerified }.
    """
    wa = (wa_number or "").strip()
    if not wa:
        return {
            "lenderProfile": None,
            "borrowerProfile": None,
            "lenderOrBorrowerSummary": {"hasLender": False, "hasBorrower": False, "borrowerVerified": False},
        }
    out: Dict[str, Any] = {
        "lenderProfile": None,
        "borrowerProfile": None,
        "lenderOrBorrowerSummary": {"hasLender": False, "hasBorrower": False, "borrowerVerified": False},
    }
    db = _get_db()
    lor = get_lender_or_borrower(wa)
    if lor.get("status") != "success":
        return out
    out["lenderOrBorrowerSummary"] = {
        "hasLender": bool(lor.get("hasLender")),
        "hasBorrower": bool(lor.get("hasBorrower")),
        "borrowerVerified": bool(lor.get("borrowerVerified")),
    }
    if lor.get("hasLender"):
        snap = db.collection("lenders").document(wa).get()
        if snap.exists:
            d = snap.to_dict() or {}
            v = d.get("verifiedAt")
            out["lenderProfile"] = {
                "lenderUid": d.get("lenderUid"),
                "displayName": d.get("displayName"),
                "status": d.get("status"),
                "verifiedAt": v.isoformat() if v is not None and hasattr(v, "isoformat") else v,
            }
    if lor.get("hasBorrower"):
        snap = db.collection("borrowers").document(wa).get()
        if snap.exists:
            d = snap.to_dict() or {}
            v = d.get("verifiedAt")
            out["borrowerProfile"] = {
                "borrowerUid": d.get("borrowerUid"),
                "displayName": d.get("displayName"),
                "status": d.get("status"),
                "verifiedAt": v.isoformat() if v is not None and hasattr(v, "isoformat") else v,
            }
    return out


def _mask_display_name(display_name: str) -> str:
    """Return first name + last initial for masked borrower display."""
    name = (display_name or "").strip()
    if not name:
        return "Unknown"
    parts = name.split()
    first = parts[0].capitalize()
    if len(parts) == 1:
        return first
    last_initial = parts[-1][:1].upper()
    return f"{first} {last_initial}."


def _format_reputation_summary(borrower_doc: Dict[str, Any]) -> str:
    score = float(borrower_doc.get("reputationScore") or 0.0)
    total_loans = int(borrower_doc.get("totalLoansTaken") or 0)
    on_time = int(borrower_doc.get("totalRepaidOnTime") or 0)
    late = int(borrower_doc.get("totalRepaidLate") or 0)
    defaulted = int(borrower_doc.get("totalDefaulted") or 0)
    if total_loans <= 0:
        return f"{score:.1f}★ (new borrower)"
    parts: List[str] = []
    if on_time:
        parts.append(f"{on_time} on time")
    if late:
        parts.append(f"{late} late")
    if defaulted:
        parts.append(f"{defaulted} defaulted")
    details = ", ".join(parts) if parts else "history"
    return f"{score:.1f}★ ({total_loans} loans, {details})"


def _parse_repay_by_date(repay_by_date: str) -> Optional[datetime]:
    """Parse repayByDate from ISO-like string to datetime."""
    s = (repay_by_date or "").strip()
    if not s:
        return None
    try:
        # Accept simple YYYY-MM-DD or full ISO 8601
        return datetime.fromisoformat(s)
    except ValueError:
        # Try common fallback formats if needed later
        return None


def send_whatsapp_twilio(
    to_wa_number: str,
    content_sid: str,
    content_variables: Dict[str, str],
) -> Dict[str, Any]:
    """
    Send a WhatsApp template message via Twilio.

    - to_wa_number: MSISDN with or without + (e.g. 2776... or +2776...); normalized to E.164 for Twilio.
    - content_sid: Twilio ContentSid for approved WhatsApp template
    - content_variables: template variables as {"1": "...", "2": "..."}
    """
    to_wa_number = (to_wa_number or "").strip()
    if not to_wa_number:
        return {"status": "error", "error_message": "to_wa_number required"}
    if not to_wa_number.startswith("+"):
        to_wa_number = "+" + to_wa_number
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID") or ""
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN") or ""
    from_whatsapp = os.environ.get("TWILIO_WHATSAPP_FROM") or ""
    if not account_sid or not auth_token or not from_whatsapp or not content_sid:
        logger.warning("send_whatsapp_twilio missing config (SID/token/from/content_sid)")
        return {"status": "error", "error_message": "Twilio WhatsApp not configured"}

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    data = {
        "To": f"whatsapp:{to_wa_number}",
        "From": from_whatsapp,
        "ContentSid": content_sid,
        "ContentVariables": json.dumps(content_variables),
    }
    try:
        res = requests.post(url, data=data, auth=(account_sid, auth_token), timeout=15)
        res.raise_for_status()
        logger.info("send_whatsapp_twilio ok to=%s content_sid=%s", to_wa_number[:6] + "***", content_sid)
        return {"status": "success"}
    except requests.RequestException as e:
        logger.exception("send_whatsapp_twilio failed: %s", e)
        return {"status": "error", "error_message": str(e)}


def create_loan_request(
    borrower_uid: str,
    amount_cents: int,
    repay_by_date: str,
    purpose: str,
    bank: str,
    disbursement_method: str,
    account_number: Optional[str] = None,
    branch_code: Optional[str] = None,
    account_type: Optional[str] = None,
    atm_voucher_cellphone: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create loan_requests/{id} with strict schema.

    - borrower_uid: waNumber of borrower
    - amount_cents: principal in cents (>0)
    - repay_by_date: ISO date string (YYYY-MM-DD or ISO 8601)
    - purpose: max 80 chars
    - bank: enum: capitec | fnb | standard_bank | absa | other
    - disbursement_method: "immediate_eft" | "atm_voucher"
    - For immediate_eft: account_number, branch_code, account_type (e.g. current/savings), bank
    - For atm_voucher: atm_voucher_cellphone (voucher sent to this number)
    """
    borrower = (borrower_uid or "").strip()
    if not borrower:
        return {"status": "error", "error_message": "borrower_uid required"}
    try:
        amount = int(amount_cents)
    except (TypeError, ValueError):
        return {"status": "error", "error_message": "amount_cents must be an integer"}
    if amount <= 0:
        return {"status": "error", "error_message": "amount_cents must be > 0"}
    purpose_clean = (purpose or "").strip()
    if not purpose_clean:
        return {"status": "error", "error_message": "purpose required"}
    if len(purpose_clean) > 80:
        return {"status": "error", "error_message": "purpose must be at most 80 characters"}
    bank_key = (bank or "").strip().lower()
    if bank_key not in ALLOWED_BANKS:
        return {"status": "error", "error_message": f"bank must be one of {sorted(ALLOWED_BANKS)}"}
    disp = (disbursement_method or "").strip().lower()
    if disp not in DISBURSEMENT_METHODS:
        return {"status": "error", "error_message": f"disbursement_method must be one of {sorted(DISBURSEMENT_METHODS)}"}
    repay_dt = _parse_repay_by_date(repay_by_date)
    if repay_dt is None:
        return {"status": "error", "error_message": "repay_by_date must be an ISO date string (e.g. 2026-03-01)"}

    if disp == "immediate_eft":
        if not (account_number or "").strip():
            return {"status": "error", "error_message": "account_number required for immediate_eft"}
        if not (branch_code or "").strip():
            return {"status": "error", "error_message": "branch_code required for immediate_eft"}
    else:  # atm_voucher
        if not (atm_voucher_cellphone or "").strip():
            return {"status": "error", "error_message": "atm_voucher_cellphone required for atm_voucher"}

    db = _get_db()
    borrower_ref = db.collection("borrowers").document(borrower)
    borrower_snap = borrower_ref.get()
    if not borrower_snap.exists:
        return {"status": "error", "error_message": "Borrower profile not found. Join the loans program first."}
    borrower_data = borrower_snap.to_dict() or {}
    if borrower_data.get("verifiedAt") is None:
        return {"status": "error", "error_message": "You must be verified first to request a loan. Complete verification in the loans program, then try again."}

    try:
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP
    except ImportError:  # pragma: no cover - fallback for older client
        from google.cloud.firestore import SERVER_TIMESTAMP

    # Use human-readable ID (LR-YYMMDD-XXXX); retry on collision
    for _ in range(5):
        loan_request_id = _generate_loan_request_id()
        ref = db.collection("loan_requests").document(loan_request_id)
        if ref.get().exists:
            continue
        break
    else:
        # Fallback to uuid-based id if all attempts collided
        loan_request_id = f"LR-{uuid.uuid4().hex[:8].upper()}"
        ref = db.collection("loan_requests").document(loan_request_id)

    now = SERVER_TIMESTAMP
    doc: Dict[str, Any] = {
        "borrowerUid": borrower,
        "amountCents": amount,
        "repayByDate": repay_dt,
        "purpose": purpose_clean,
        "bank": bank_key,
        "disbursementMethod": disp,
        "status": "open",
        "createdAt": now,
        "updatedAt": now,
    }
    if disp == "immediate_eft":
        doc["accountNumber"] = (account_number or "").strip()
        doc["branchCode"] = (branch_code or "").strip()
        doc["accountType"] = (account_type or "current").strip() or "current"
    else:
        doc["atmVoucherCellphone"] = (atm_voucher_cellphone or "").strip()
    ref.set(doc)
    logger.info("create_loan_request borrower=%s id=%s", borrower[:6] + "***", ref.id)
    return {"status": "success", "loanRequestId": ref.id}


def fetch_loan_requests(
    lender_uid: str,
    page_size: int = DEFAULT_LOAN_PAGE_SIZE,
    page_cursor: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetch open loan_requests for lender browsing, 3 at a time.

    Includes both locked and unlocked requests. For requests this lender has already
    unlocked: returns full details (borrower name, address, stats, etc.) and
    unlockedByLender: true. For locked requests: returns masked details only and
    unlockedByLender: false.
    """
    lender = (lender_uid or "").strip()
    if not lender:
        return {"status": "error", "error_message": "lender_uid required"}

    db = _get_db()

    # Find already-unlocked requests for this lender
    unlocked_ids: set[str] = set()
    views_ref = db.collection("lenders").document(lender).collection("views")
    for view_doc in views_ref.stream():
        data = view_doc.to_dict() or {}
        unlocked_ids.add(str(data.get("loanRequestId") or view_doc.id))

    from google.cloud.firestore_v1 import Query  # type: ignore[import]

    query = (
        db.collection("loan_requests")
        .where("status", "==", "open")
        .order_by("createdAt", direction=Query.DESCENDING)
    )
    if page_cursor:
        cursor_doc = db.collection("loan_requests").document(page_cursor).get()
        if cursor_doc.exists:
            query = query.start_after(cursor_doc)

    # Fetch one extra to compute next cursor
    snapshots = list(query.limit(page_size + 1).stream())
    items: List[Dict[str, Any]] = []
    next_cursor: Optional[str] = None

    for snap in snapshots:
        req_id = snap.id
        data = snap.to_dict() or {}
        borrower_uid = str(data.get("borrowerUid") or "")

        if req_id in unlocked_ids:
            # Full details for already-unlocked request
            full_detail = _build_full_request_detail(req_id, data, borrower_uid, db)
            full_detail["unlockedByLender"] = True
            items.append(full_detail)
        else:
            # Masked details for locked request
            borrower_doc = (
                db.collection("borrowers").document(borrower_uid).get() if borrower_uid else None
            )
            borrower_data: Dict[str, Any] = borrower_doc.to_dict() if borrower_doc and borrower_doc.exists else {}
            display_name = borrower_data.get("displayName") or borrower_uid
            masked_name = _mask_display_name(display_name)
            rep_summary = _format_reputation_summary(borrower_data)
            created_at = data.get("createdAt")
            repay_by = data.get("repayByDate")
            items.append({
                "loanRequestId": req_id,
                "maskedName": masked_name,
                "amountCents": int(data.get("amountCents") or 0),
                "repayByDate": repay_by.isoformat() if hasattr(repay_by, "isoformat") else None,
                "reputationSummary": rep_summary,
                "reputationScore": float(borrower_data.get("reputationScore") or 0.0),
                "createdAt": created_at.isoformat() if hasattr(created_at, "isoformat") else None,
                "unlockedByLender": False,
            })
        if len(items) == page_size:
            next_cursor = req_id
            break

    logger.info(
        "fetch_loan_requests lender=%s count=%s next_cursor=%s",
        lender[:6] + "***",
        len(items),
        next_cursor,
    )
    return {
        "status": "success",
        "items": items,
        "nextCursor": next_cursor,
    }


def fetch_unpaid_loans(wa_number: str, role: str) -> Dict[str, Any]:
    """
    Fetch loans that are not yet repaid for the current user (lender or borrower).
    role: "lender" | "borrower". Returns list with loanId, amountCents, totalToRepayCents,
    dueDate, status, otherPartyDisplayName (name only, no phone/waNumber).
    """
    wa = (wa_number or "").strip()
    if not wa:
        return {"status": "error", "error_message": "wa_number required"}
    role_clean = (role or "").strip().lower()
    if role_clean not in ("lender", "borrower"):
        return {"status": "error", "error_message": "role must be 'lender' or 'borrower'"}

    db = _get_db()
    from google.cloud.firestore_v1 import Query  # type: ignore[import]

    items: List[Dict[str, Any]] = []
    for status_val in ("matched", "active"):
        query = (
            db.collection("loans")
            .where("status", "==", status_val)
            .order_by("dueDate", direction=Query.ASCENDING)
        )
        for snap in query.stream():
            data = snap.to_dict() or {}
            lender_uid = str(data.get("lenderUid") or "")
            borrower_uid = str(data.get("borrowerUid") or "")
            if role_clean == "lender" and lender_uid != wa:
                continue
            if role_clean == "borrower" and borrower_uid != wa:
                continue
            other_uid = borrower_uid if role_clean == "lender" else lender_uid
            other_doc = db.collection("borrowers" if role_clean == "lender" else "lenders").document(other_uid).get()
            other_data = other_doc.to_dict() if other_doc.exists else {}
            other_name = (other_data.get("displayName") or "").strip() or _mask_display_name(other_uid)

            due = data.get("dueDate")
            items.append({
                "loanId": snap.id,
                "amountCents": int(data.get("amountCents") or 0),
                "interestCents": int(data.get("interestCents") or 0),
                "totalToRepayCents": int(data.get("totalToRepayCents") or 0),
                "dueDate": due.isoformat() if hasattr(due, "isoformat") else None,
                "status": data.get("status") or "active",
                "otherPartyDisplayName": other_name,
                "createdAt": (data.get("createdAt").isoformat() if hasattr(data.get("createdAt"), "isoformat") else None),
            })
    # Sort by due date
    items.sort(key=lambda x: (x.get("dueDate") or ""))
    return {"status": "success", "loans": items}


def unlock_loan_request(
    lender_uid: str,
    loan_request_ids: List[str],
) -> Dict[str, Any]:
    """
    Mark one or more loan_requests as unlocked for a lender and return full details.

    NOTE: Payment integration (e.g. Yoco webhook) should ensure this is only called after payment success.
    This tool records lender_views and returns unlocked request details.
    """
    lender = (lender_uid or "").strip()
    if not lender:
        return {"status": "error", "error_message": "lender_uid required"}
    if not loan_request_ids:
        return {"status": "error", "error_message": "loan_request_ids required"}
    if len(loan_request_ids) > 3:
        return {"status": "error", "error_message": "Can only unlock up to 3 requests at a time"}

    try:
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP
    except ImportError:  # pragma: no cover
        from google.cloud.firestore import SERVER_TIMESTAMP

    db = _get_db()
    views_ref = db.collection("lenders").document(lender).collection("views")

    # Fee: R5 per request (500 cents) or R10 for batch of 3 (1000 cents)
    if len(loan_request_ids) == 1:
        total_fee_cents = 500
    elif len(loan_request_ids) == 3:
        total_fee_cents = 1000
    else:
        # For 2 requests, charge R5 each (spec says R5/request or R10 for batch of 3)
        total_fee_cents = 500 * len(loan_request_ids)
    per_request_fee = int(total_fee_cents / len(loan_request_ids))

    unlocked: List[Dict[str, Any]] = []
    now = SERVER_TIMESTAMP

    for req_id in loan_request_ids:
        req_id_clean = (req_id or "").strip()
        if not req_id_clean:
            continue
        req_ref = db.collection("loan_requests").document(req_id_clean)
        req_snap = req_ref.get()
        if not req_snap.exists:
            logger.warning("unlock_loan_request missing loan_request id=%s", req_id_clean)
            continue
        req_data = req_snap.to_dict() or {}
        if req_data.get("status") != "open":
            logger.info(
                "unlock_loan_request skipping non-open id=%s status=%s",
                req_id_clean,
                req_data.get("status"),
            )
            continue

        # Idempotent: if view already exists, keep it; else create
        view_doc = views_ref.document(req_id_clean).get()
        if not view_doc.exists:
            views_ref.document(req_id_clean).set(
                {
                    "loanRequestId": req_id_clean,
                    "unlockedAt": now,
                    "feePaidCents": per_request_fee,
                }
            )

        borrower_uid = str(req_data.get("borrowerUid") or "")
        borrower_doc = (
            db.collection("borrowers").document(borrower_uid).get() if borrower_uid else None
        )
        borrower_data: Dict[str, Any] = borrower_doc.to_dict() if borrower_doc and borrower_doc.exists else {}
        display_name = borrower_data.get("displayName") or borrower_uid
        rep_summary = _format_reputation_summary(borrower_data)
        repay_by = req_data.get("repayByDate")

        unlocked.append(
            {
                "loanRequestId": req_id_clean,
                "borrowerUid": borrower_uid,
                "borrowerName": display_name,
                "amountCents": int(req_data.get("amountCents") or 0),
                "repayByDate": repay_by.isoformat() if hasattr(repay_by, "isoformat") else None,
                "purpose": req_data.get("purpose"),
                "bank": req_data.get("bank"),
                "reputationSummary": rep_summary,
                "reputationScore": float(borrower_data.get("reputationScore") or 0.0),
            }
        )

    logger.info(
        "unlock_loan_request lender=%s unlocked_count=%s total_fee_cents=%s",
        lender[:6] + "***",
        len(unlocked),
        total_fee_cents,
    )
    return {
        "status": "success",
        "totalFeeCents": total_fee_cents,
        "unlocked": unlocked,
    }


def _unlock_fee_cents(loan_request_count: int) -> int:
    """R5 per request or R10 for batch of 3."""
    if loan_request_count == 1:
        return 500
    if loan_request_count == 3:
        return 1000
    return 500 * loan_request_count


def create_unlock_payment_link(
    lender_uid: str,
    loan_request_ids: List[str],
) -> Dict[str, Any]:
    """
    Create a Yoco payment link for the unlock fee. Store pending_unlocks; when Yoco
    calls our callback (payment success), we call unlock_loan_request. Returns paylinkUrl
    for the agent to send to the lender. Lender replies DONE after paying; agent then
    calls get_unlocked_request_details_tool to show full (non-banking) details.
    """
    lender = (lender_uid or "").strip()
    if not lender:
        return {"status": "error", "error_message": "lender_uid required"}
    if not loan_request_ids:
        return {"status": "error", "error_message": "loan_request_ids required"}
    if len(loan_request_ids) > 3:
        return {"status": "error", "error_message": "Can only unlock up to 3 requests at a time"}

    total_fee_cents = _unlock_fee_cents(len(loan_request_ids))
    external_id = str(uuid.uuid4())
    base_url = qc_config.LENDING_BASE_URL or qc_config.BASE_URL
    if not base_url:
        logger.warning("LENDING_BASE_URL or BASE_URL not set; payment callback will be incomplete")
    callback_url = f"{base_url}/api/lending/ikhokha-callback" if base_url else ""
    success_url = f"{base_url}/lending/unlock-success?ref={external_id}" if base_url else ""
    failure_url = f"{base_url}/lending/unlock-failure" if base_url else ""
    cancel_url = f"{base_url}/lending/unlock-cancel" if base_url else ""

    try:
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP
    except ImportError:
        from google.cloud.firestore import SERVER_TIMESTAMP

    db = _get_db()
    pending_ref = db.collection("pending_unlocks").document(external_id)
    now = SERVER_TIMESTAMP
    pending_ref.set({
        "lenderUid": lender,
        "loanRequestIds": list(loan_request_ids),
        "totalFeeCents": total_fee_cents,
        "externalTransactionID": external_id,
        "createdAt": now,
    })

    result = create_paylink(
        amount_cents=total_fee_cents,
        currency="ZAR",
        external_transaction_id=external_id,
        description="Unlock loan request(s) – Queens Connect",
        payment_reference=external_id[:8],
        callback_url=callback_url,
        success_page_url=success_url,
        failure_page_url=failure_url,
        cancel_url=cancel_url,
    )
    if result.get("status") != "success":
        pending_ref.delete()
        return result
    paylink_id = result.get("paylinkID")
    if paylink_id:
        pending_ref.update({"paylinkID": paylink_id})
    logger.info(
        "create_unlock_payment_link lender=%s external_id=%s total_fee_cents=%s",
        lender[:6] + "***",
        external_id[:8],
        total_fee_cents,
    )
    return {
        "status": "success",
        "paylinkUrl": result.get("paylinkUrl"),
        "totalFeeCents": total_fee_cents,
        "externalTransactionID": external_id,
    }


def _build_full_request_detail(
    req_id_clean: str,
    req_data: Dict[str, Any],
    borrower_uid: str,
    db,
) -> Dict[str, Any]:
    """
    Build one full request detail dict (borrower name, address, stats, verified, age, gender,
    purpose, amount, repayByDate, bank, reputationSummary, etc.). No borrowerUid or phone.
    """
    borrower_doc = (
        db.collection("borrowers").document(borrower_uid).get() if borrower_uid else None
    )
    borrower_data = borrower_doc.to_dict() if borrower_doc and borrower_doc.exists else {}
    display_name = borrower_data.get("displayName") or "Borrower"
    rep_summary = _format_reputation_summary(borrower_data)
    repay_by = req_data.get("repayByDate")
    user_doc = db.collection("users").document(borrower_uid).get() if borrower_uid else None
    user_data = user_doc.to_dict() if user_doc and user_doc.exists else {}
    age = user_data.get("age")
    if age is None and user_data.get("dateOfBirth"):
        try:
            from datetime import datetime, date
            dob_str = user_data.get("dateOfBirth") or ""
            if isinstance(dob_str, str) and len(dob_str) >= 10:
                dob = datetime.fromisoformat(dob_str[:10].replace("Z", "")).date()
                age = max(0, date.today().year - dob.year - ((date.today().month, date.today().day) < (dob.month, dob.day)))
        except Exception:
            pass
    return {
        "loanRequestId": req_id_clean,
        "borrowerName": display_name,
        "address": (borrower_data.get("address") or "").strip() or None,
        "amountCents": int(req_data.get("amountCents") or 0),
        "repayByDate": repay_by.isoformat() if hasattr(repay_by, "isoformat") else None,
        "purpose": req_data.get("purpose"),
        "bank": req_data.get("bank"),
        "reputationSummary": rep_summary,
        "reputationScore": float(borrower_data.get("reputationScore") or 0.0),
        "totalLoansTaken": int(borrower_data.get("totalLoansTaken") or 0),
        "totalRepaidOnTime": int(borrower_data.get("totalRepaidOnTime") or 0),
        "totalRepaidLate": int(borrower_data.get("totalRepaidLate") or 0),
        "totalDefaulted": int(borrower_data.get("totalDefaulted") or 0),
        "totalAmountRepaidCents": int(borrower_data.get("totalAmountRepaidCents") or 0),
        "totalAmountOwingCents": int(borrower_data.get("totalAmountOwingCents") or 0),
        "currentActiveLoansCount": int(borrower_data.get("currentActiveLoansCount") or 0),
        "borrowerVerified": borrower_data.get("verifiedAt") is not None,
        "age": age,
        "gender": (user_data.get("gender") or "").strip() or None,
    }


def get_unlocked_request_details(
    lender_uid: str,
    loan_request_ids: List[str],
) -> Dict[str, Any]:
    """
    Return full details for the given loan_request_ids only if this lender has
    unlocked them (after paying via Yoco). Does NOT include borrower banking
    details (account number, cellphone for disbursement); those are shown only
    after the lender accepts the request via accept_loan_request_tool.
    """
    lender = (lender_uid or "").strip()
    if not lender:
        return {"status": "error", "error_message": "lender_uid required"}
    if not loan_request_ids:
        return {"status": "error", "error_message": "loan_request_ids required"}

    db = _get_db()
    views_ref = db.collection("lenders").document(lender).collection("views")
    unlocked: List[Dict[str, Any]] = []
    not_unlocked_yet: List[str] = []

    for req_id in loan_request_ids:
        req_id_clean = (req_id or "").strip()
        if not req_id_clean:
            continue
        view_doc = views_ref.document(req_id_clean).get()
        if not view_doc.exists:
            not_unlocked_yet.append(req_id_clean)
            continue
        req_ref = db.collection("loan_requests").document(req_id_clean)
        req_snap = req_ref.get()
        if not req_snap.exists:
            not_unlocked_yet.append(req_id_clean)
            continue
        req_data = req_snap.to_dict() or {}
        if req_data.get("status") != "open":
            not_unlocked_yet.append(req_id_clean)
            continue
        borrower_uid = str(req_data.get("borrowerUid") or "")
        unlocked.append(_build_full_request_detail(req_id_clean, req_data, borrower_uid, db))
    return {
        "status": "success",
        "unlocked": unlocked,
        "notUnlockedYet": not_unlocked_yet,
    }


def complete_unlock_after_payment(paylink_id_or_external_id: str) -> Dict[str, Any]:
    """
    Look up pending_unlocks by externalTransactionID (doc id) or paylinkID, then
    call unlock_loan_request and clear the pending record. Used by payment webhook/callback.
    """
    key = (paylink_id_or_external_id or "").strip()
    if not key:
        return {"status": "error", "error_message": "paylink_id_or_external_id required"}
    db = _get_db()
    pending_ref = db.collection("pending_unlocks").document(key)
    pending_snap = pending_ref.get()
    if not pending_snap.exists:
        # Try find by paylinkID
        from google.cloud.firestore_v1 import Query
        q = db.collection("pending_unlocks").where("paylinkID", "==", key).limit(1)
        for doc in q.stream():
            pending_ref = doc.reference
            pending_snap = doc
            break
        else:
            logger.warning("complete_unlock_after_payment no pending_unlock for key=%s", key[:16])
            return {"status": "error", "error_message": "Pending unlock not found"}
    data = pending_snap.to_dict() or {}
    lender_uid = data.get("lenderUid")
    loan_request_ids = data.get("loanRequestIds") or []
    if not lender_uid or not loan_request_ids:
        pending_ref.delete()
        return {"status": "error", "error_message": "Invalid pending unlock data"}
    out = unlock_loan_request(lender_uid, loan_request_ids)
    pending_ref.delete()
    return out


def check_unlock_payment_status(external_transaction_id: str) -> Dict[str, Any]:
    """
    When the user says they are done paying, fetch the Yoco payment link status.
    If status is 'paid', complete the unlock (grant lender access to the request details).
    Pass the external_transaction_id that was returned when the payment link was created.
    """
    key = (external_transaction_id or "").strip()
    if not key:
        return {"status": "error", "error_message": "external_transaction_id required"}

    db = _get_db()
    pending_ref = db.collection("pending_unlocks").document(key)
    pending_snap = pending_ref.get()
    if not pending_snap.exists:
        # Try find by paylinkID in case caller passed Yoco link id
        from google.cloud.firestore_v1 import Query
        q = db.collection("pending_unlocks").where("paylinkID", "==", key).limit(1)
        external_id = None
        paylink_id = key
        for doc in q.stream():
            pending_ref = doc.reference
            external_id = doc.id
            break
        if external_id is None:
            logger.warning("check_unlock_payment_status no pending_unlock for key=%s", key[:16])
            return {"status": "error", "error_message": "Pending unlock not found"}
        key = external_id
    else:
        data = pending_snap.to_dict() or {}
        paylink_id = (data.get("paylinkID") or "").strip()
        if not paylink_id:
            logger.warning("check_unlock_payment_status pending_unlock missing paylinkID doc_id=%s", key[:16])
            return {"status": "error", "error_message": "Pending unlock has no payment link id"}

    result = fetch_payment_link_status(paylink_id)
    if result.get("status") == "error":
        return result

    yoco_status = (result.get("yoco_status") or "pending").lower()
    if yoco_status == "paid":
        return complete_unlock_after_payment(key)
    return {
        "status": "success",
        "payment_status": yoco_status,
        "message": "Payment not yet completed. Ask the user to complete payment at the link, then try again.",
    }


def accept_loan_request(
    lender_uid: str,
    loan_request_id: str,
    interest_cents: int,
) -> Dict[str, Any]:
    """
    Accept an open loan_request:
    - Lender may accept based on masked or full details; unlock is optional.
    - Create loans/{loanId} document.
    - Update loan_requests status -> "matched".
    - Notify borrower via WhatsApp (Twilio template when TWILIO_LOAN_MATCH_CONTENT_SID is set).
    - Returns borrowerNotified: true if the WhatsApp message was sent successfully.
    """
    lender = (lender_uid or "").strip()
    req_id = (loan_request_id or "").strip()
    if not lender:
        return {"status": "error", "error_message": "lender_uid required"}
    if not req_id:
        return {"status": "error", "error_message": "loan_request_id required"}
    try:
        icents = int(interest_cents)
    except (TypeError, ValueError):
        return {"status": "error", "error_message": "interest_cents must be an integer"}
    if icents < 0:
        return {"status": "error", "error_message": "interest_cents must be >= 0"}

    try:
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP
    except ImportError:  # pragma: no cover
        from google.cloud.firestore import SERVER_TIMESTAMP

    db = _get_db()
    req_ref = db.collection("loan_requests").document(req_id)
    req_snap = req_ref.get()
    if not req_snap.exists:
        return {"status": "error", "error_message": "loan_request not found"}
    req_data = req_snap.to_dict() or {}
    if req_data.get("status") != "open":
        return {"status": "error", "error_message": f"loan_request is not open (status={req_data.get('status')})"}

    borrower_uid = str(req_data.get("borrowerUid") or "")
    if not borrower_uid:
        return {"status": "error", "error_message": "loan_request is missing borrowerUid"}

    amount = int(req_data.get("amountCents") or 0)
    total_to_repay = amount + icents

    now = SERVER_TIMESTAMP
    loan_ref = db.collection("loans").document()
    loan_doc = {
        "borrowerUid": borrower_uid,
        "lenderUid": lender,
        "loanRequestId": req_id,
        "amountCents": amount,
        "interestCents": icents,
        "totalToRepayCents": total_to_repay,
        "status": "matched",
        "createdAt": now,
        "matchedAt": now,
        "dueDate": req_data.get("repayByDate"),
        "repaidAt": None,
        "popUrl": None,
        "popUploadedAt": None,
        "notesFromBorrower": "",
        "notesFromLender": "",
    }
    loan_ref.set(loan_doc)

    # Update loan_request status -> matched
    req_ref.update({"status": "matched", "updatedAt": now})

    # Increment borrower totalLoansTaken, currentActiveLoansCount, and totalAmountOwingCents
    try:
        b_ref = db.collection("borrowers").document(borrower_uid)
        b_snap = b_ref.get()
        if b_snap.exists:
            b_data = b_snap.to_dict() or {}
            total_taken = int(b_data.get("totalLoansTaken") or 0) + 1
            active_count = int(b_data.get("currentActiveLoansCount") or 0) + 1
            total_amount_owing_cents = int(b_data.get("totalAmountOwingCents") or 0) + total_to_repay
            b_ref.update({
                "totalLoansTaken": total_taken,
                "currentActiveLoansCount": active_count,
                "totalAmountOwingCents": total_amount_owing_cents,
                "updatedAt": now,
            })
    except Exception as e:
        logger.warning("accept_loan_request: could not update borrower stats: %s", e)
    # Increment lender totalLoansGiven
    try:
        l_ref = db.collection("lenders").document(lender)
        l_snap = l_ref.get()
        if l_snap.exists:
            l_data = l_snap.to_dict() or {}
            total_given = int(l_data.get("totalLoansGiven") or 0) + 1
            l_ref.update({"totalLoansGiven": total_given, "updatedAt": now})
    except Exception as e:
        logger.warning("accept_loan_request: could not update lender stats: %s", e)

    # Load borrower profile for notification & lender view
    borrower_doc = db.collection("borrowers").document(borrower_uid).get()
    borrower_data = borrower_doc.to_dict() if borrower_doc.exists else {}
    borrower_name = borrower_data.get("displayName") or borrower_uid

    # Notify borrower via WhatsApp when a lender accepts (Twilio template)
    borrower_notified = False
    content_sid = os.environ.get("TWILIO_LOAN_MATCH_CONTENT_SID") or ""
    if not content_sid:
        logger.warning(
            "accept_loan_request: borrower WhatsApp notification skipped — set TWILIO_LOAN_MATCH_CONTENT_SID (Twilio Content SID for loan-accepted template) to notify borrower when a lender accepts."
        )
    else:
        try:
            amount_rands = int(round(amount / 100)) if amount else 0
            content_vars = {
                "1": borrower_name,
                "2": f"R{amount_rands}",
            }
            result = send_whatsapp_twilio(borrower_uid, content_sid, content_vars)
            borrower_notified = result.get("status") == "success"
            if borrower_notified:
                logger.info("accept_loan_request: borrower notified via WhatsApp to=%s", borrower_uid[:6] + "***")
        except Exception as e:  # pragma: no cover - best effort
            logger.exception("accept_loan_request: WhatsApp notify failed: %s", e)

    logger.info(
        "accept_loan_request lender=%s borrower=%s loan_id=%s",
        lender[:6] + "***",
        borrower_uid[:6] + "***",
        loan_ref.id,
    )

    # Disbursement: only EFT details exposed (no phone/waNumber). For atm_voucher, instruction only.
    disbursement_method = req_data.get("disbursementMethod") or "immediate_eft"
    disbursement: Dict[str, Any] = {"disbursementMethod": disbursement_method}
    if disbursement_method == "immediate_eft":
        disbursement["accountNumber"] = req_data.get("accountNumber")
        disbursement["branchCode"] = req_data.get("branchCode")
        disbursement["accountType"] = req_data.get("accountType") or "current"
        disbursement["bank"] = req_data.get("bank")
    else:
        # atm_voucher: do not expose cellphone; give in-app instruction only
        disbursement["instruction"] = "Send the ATM voucher via the app when the borrower requests payout. Do not share phone numbers."

    return {
        "status": "success",
        "loanId": loan_ref.id,
        "borrowerNotified": borrower_notified,
        "borrower": {
            "name": borrower_name,
            "bank": req_data.get("bank"),
            "purpose": req_data.get("purpose"),
            "repayByDate": req_data.get("repayByDate").isoformat()
            if hasattr(req_data.get("repayByDate"), "isoformat")
            else None,
            "amountCents": amount,
            "disbursement": disbursement,
        },
    }


def update_lender_repayment_details(
    lender_uid: str,
    method: str,
    account_number: Optional[str] = None,
    branch_code: Optional[str] = None,
    bank: Optional[str] = None,
    account_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Save the lender's repayment EFT details so the borrower can repay via the platform.
    Call after a loan is created (e.g. after accept_loan_request). method must be "eft".
    """
    lender = (lender_uid or "").strip()
    if not lender:
        return {"status": "error", "error_message": "lender_uid required"}
    method_clean = (method or "").strip().lower()
    if method_clean != "eft":
        return {"status": "error", "error_message": "method must be 'eft'"}
    if not (account_number or "").strip():
        return {"status": "error", "error_message": "account_number required for eft"}
    if not (branch_code or "").strip():
        return {"status": "error", "error_message": "branch_code required for eft"}
    bank_key = (bank or "").strip().lower()
    if bank_key and bank_key not in ALLOWED_BANKS:
        return {"status": "error", "error_message": f"bank must be one of {sorted(ALLOWED_BANKS)}"}

    try:
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP
    except ImportError:
        from google.cloud.firestore import SERVER_TIMESTAMP

    db = _get_db()
    ref = db.collection("lenders").document(lender)
    if not ref.get().exists:
        return {"status": "error", "error_message": "Lender profile not found."}
    details: Dict[str, Any] = {
        "method": "eft",
        "accountNumber": (account_number or "").strip(),
        "branchCode": (branch_code or "").strip(),
        "bank": (bank or "").strip().lower() or None,
        "accountType": (account_type or "current").strip() or "current",
    }
    ref.update({
        "repaymentBankingDetails": details,
        "updatedAt": SERVER_TIMESTAMP,
    })
    logger.info("update_lender_repayment_details lender=%s method=eft", lender[:6] + "***")
    return {"status": "success", "lenderUid": lender}


def _compute_borrower_reputation_score(
    total_loans: int,
    on_time: int,
    late: int,
    defaulted: int,
) -> float:
    """Compute reputation score 0-5 from repayment history."""
    if total_loans <= 0:
        return 0.0
    # Simple: reward on-time, penalize late and defaulted
    good = on_time + 0.5 * late
    bad = 2 * defaulted
    raw = max(0.0, (good - bad) / total_loans * 2.5 + 2.5)
    return round(min(5.0, max(0.0, raw)), 1)


def complete_repayment(loan_id: str) -> Dict[str, Any]:
    """
    Mark loan as repaid and update borrower + lender stats.
    Called only after repayment payment is confirmed (e.g. via check_repayment_payment_status).
    """
    loan_id_clean = (loan_id or "").strip()
    if not loan_id_clean:
        return {"status": "error", "error_message": "loan_id required"}

    try:
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP
    except ImportError:
        from google.cloud.firestore import SERVER_TIMESTAMP

    db = _get_db()
    loan_ref = db.collection("loans").document(loan_id_clean)
    loan_snap = loan_ref.get()
    if not loan_snap.exists:
        return {"status": "error", "error_message": "loan not found"}
    loan_data = loan_snap.to_dict() or {}
    if loan_data.get("status") == "repaid":
        return {"status": "success", "message": "Already repaid"}
    borrower_uid = str(loan_data.get("borrowerUid") or "")
    lender_uid = str(loan_data.get("lenderUid") or "")
    total_to_repay = int(loan_data.get("totalToRepayCents") or 0)
    due_date = loan_data.get("dueDate")
    now = SERVER_TIMESTAMP

    loan_ref.update({"status": "repaid", "repaidAt": now})

    # Borrower stats: on-time vs late by due date
    import time
    now_sec = time.time()
    due_sec = None
    if due_date is not None:
        if hasattr(due_date, "timestamp"):
            due_sec = due_date.timestamp()
        elif hasattr(due_date, "isoformat"):
            try:
                due_sec = datetime.fromisoformat(due_date.isoformat().replace("Z", "+00:00")).timestamp()
            except Exception:
                pass
    is_on_time = due_sec is None or now_sec <= due_sec

    if borrower_uid:
        b_ref = db.collection("borrowers").document(borrower_uid)
        b_snap = b_ref.get()
        if b_snap.exists:
            b_data = b_snap.to_dict() or {}
            on_time = int(b_data.get("totalRepaidOnTime") or 0)
            late = int(b_data.get("totalRepaidLate") or 0)
            defaulted = int(b_data.get("totalDefaulted") or 0)
            total_loans_taken = int(b_data.get("totalLoansTaken") or 0)
            total_repaid_cents = int(b_data.get("totalAmountRepaidCents") or 0)
            active_count = int(b_data.get("currentActiveLoansCount") or 0)
            total_amount_owing_cents = int(b_data.get("totalAmountOwingCents") or 0)
            if is_on_time:
                on_time += 1
            else:
                late += 1
            total_repaid_cents += total_to_repay
            active_count = max(0, active_count - 1)
            new_owing = max(0, total_amount_owing_cents - total_to_repay)
            new_score = _compute_borrower_reputation_score(total_loans_taken, on_time, late, defaulted)
            b_ref.update({
                "totalRepaidOnTime": on_time,
                "totalRepaidLate": late,
                "totalAmountRepaidCents": total_repaid_cents,
                "currentActiveLoansCount": active_count,
                "totalAmountOwingCents": new_owing,
                "reputationScore": new_score,
                "updatedAt": now,
            })

    # Lender stats
    if lender_uid:
        l_ref = db.collection("lenders").document(lender_uid)
        l_snap = l_ref.get()
        if l_snap.exists:
            l_data = l_snap.to_dict() or {}
            total_repaid = int(l_data.get("totalRepaid") or 0)
            total_value = int(l_data.get("totalValueRepaidCents") or 0)
            l_ref.update({
                "totalRepaid": total_repaid + 1,
                "totalValueRepaidCents": total_value + total_to_repay,
                "updatedAt": now,
            })

    # Kasi Points: repay on time +30 to borrower, lend success +15 to lender
    try:
        if is_on_time and borrower_uid:
            award_points(borrower_uid, 30, "repay_on_time")
        if lender_uid:
            award_points(lender_uid, 15, "lend_success")
    except Exception as e:
        logger.warning("complete_repayment: award_points failed: %s", e)

    logger.info("complete_repayment loan_id=%s", loan_id_clean)
    return {"status": "success"}


def create_repayment_payment_link(loan_id: str, borrower_uid: str) -> Dict[str, Any]:
    """
    Create a Yoco payment link for the borrower to repay a loan (totalToRepayCents).
    Only the borrower can repay. Loan must be active (money already sent by lender).
    Returns paylinkUrl and externalTransactionID; store externalTransactionID for check_repayment_payment_status when they say done.
    """
    loan_id_clean = (loan_id or "").strip()
    borrower = (borrower_uid or "").strip()
    if not loan_id_clean:
        return {"status": "error", "error_message": "loan_id required"}
    if not borrower:
        return {"status": "error", "error_message": "borrower_uid required"}

    db = _get_db()
    loan_ref = db.collection("loans").document(loan_id_clean)
    loan_snap = loan_ref.get()
    if not loan_snap.exists:
        return {"status": "error", "error_message": "loan not found"}
    loan_data = loan_snap.to_dict() or {}
    if str(loan_data.get("borrowerUid") or "") != borrower:
        return {"status": "error", "error_message": "Only the borrower can repay this loan."}
    if loan_data.get("status") != "active":
        return {"status": "error", "error_message": "Loan is not active (lender must send money and upload proof first)."}
    total_cents = int(loan_data.get("totalToRepayCents") or 0)
    if total_cents <= 0:
        return {"status": "error", "error_message": "Invalid loan amount."}

    external_id = str(uuid.uuid4())
    result = create_paylink(
        amount_cents=total_cents,
        currency="ZAR",
        external_transaction_id=external_id,
        description="Loan repayment – Queens Connect",
        payment_reference=loan_id_clean[:16],
    )
    if result.get("status") != "success":
        return result
    paylink_id = result.get("paylinkID") or ""

    try:
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP
    except ImportError:
        from google.cloud.firestore import SERVER_TIMESTAMP

    pending_ref = db.collection("pending_repayments").document(external_id)
    pending_ref.set({
        "loanId": loan_id_clean,
        "borrowerUid": borrower,
        "totalCents": total_cents,
        "paylinkID": paylink_id,
        "externalTransactionID": external_id,
        "createdAt": SERVER_TIMESTAMP,
    })
    return {
        "status": "success",
        "paylinkUrl": result.get("paylinkUrl"),
        "externalTransactionID": external_id,
        "totalToRepayCents": total_cents,
    }


def check_repayment_payment_status(external_transaction_id: str) -> Dict[str, Any]:
    """
    When the borrower says they have paid, check Yoco payment status.
    If paid, mark pending_repayment as yocoPaidAt and return loanId + message to upload POP.
    The loan is only marked repaid and stats updated when record_proof_of_payment is called with this loan_id (repayment POP).
    """
    key = (external_transaction_id or "").strip()
    if not key:
        return {"status": "error", "error_message": "external_transaction_id required"}

    try:
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP
    except ImportError:
        from google.cloud.firestore import SERVER_TIMESTAMP

    db = _get_db()
    pending_ref = db.collection("pending_repayments").document(key)
    pending_snap = pending_ref.get()
    if not pending_snap.exists:
        return {"status": "error", "error_message": "Pending repayment not found. Use the repayment link from when you requested to pay."}
    data = pending_snap.to_dict() or {}
    loan_id = (data.get("loanId") or "").strip()
    paylink_id = (data.get("paylinkID") or "").strip()
    if not paylink_id:
        return {"status": "error", "error_message": "Pending repayment has no payment link id."}

    status_result = fetch_payment_link_status(paylink_id)
    if status_result.get("status") == "error":
        return status_result
    yoco_status = (status_result.get("yoco_status") or "pending").lower()
    if yoco_status != "paid":
        return {
            "status": "success",
            "payment_completed": False,
            "payment_status": yoco_status,
            "message": "Payment not yet completed. Complete payment at the link, then reply DONE again.",
        }
    # Paid: mark pending as yoco paid; do NOT call complete_repayment yet — borrower must upload POP
    pending_ref.update({"yocoPaidAt": SERVER_TIMESTAMP})
    return {
        "status": "success",
        "payment_completed": True,
        "loanId": loan_id,
        "repayment_recorded": False,
        "message": "Payment received. You must upload proof of payment so we can mark the loan as repaid. Reply DONE after you have uploaded.",
    }


def get_my_lending_stats(wa_number: str) -> Dict[str, Any]:
    """
    Return the current user's lender and/or borrower stats (no waNumber in output).
    Use for "my stats", "my rating", "how am I doing".
    """
    wa = (wa_number or "").strip()
    if not wa:
        return {"status": "error", "error_message": "wa_number required"}
    db = _get_db()
    out: Dict[str, Any] = {"status": "success", "lenderStats": None, "borrowerStats": None}
    lender_snap = db.collection("lenders").document(wa).get()
    if lender_snap.exists:
        d = lender_snap.to_dict() or {}
        out["lenderStats"] = {
            "displayName": d.get("displayName"),
            "reputationScore": float(d.get("reputationScore") or 0),
            "totalLoansGiven": int(d.get("totalLoansGiven") or 0),
            "totalRepaid": int(d.get("totalRepaid") or 0),
            "totalDefaulted": int(d.get("totalDefaulted") or 0),
            "totalValueRepaidCents": int(d.get("totalValueRepaidCents") or 0),
            "status": d.get("status"),
            "badges": d.get("badges") or [],
        }
    borrower_snap = db.collection("borrowers").document(wa).get()
    if borrower_snap.exists:
        d = borrower_snap.to_dict() or {}
        out["borrowerStats"] = {
            "displayName": d.get("displayName"),
            "reputationScore": float(d.get("reputationScore") or 0),
            "totalLoansTaken": int(d.get("totalLoansTaken") or 0),
            "totalRepaidOnTime": int(d.get("totalRepaidOnTime") or 0),
            "totalRepaidLate": int(d.get("totalRepaidLate") or 0),
            "totalDefaulted": int(d.get("totalDefaulted") or 0),
            "totalAmountRepaidCents": int(d.get("totalAmountRepaidCents") or 0),
            "currentActiveLoansCount": int(d.get("currentActiveLoansCount") or 0),
            "status": d.get("status"),
            "badges": d.get("badges") or [],
        }
    if not out["lenderStats"] and not out["borrowerStats"]:
        return {"status": "error", "error_message": "No lender or borrower profile found."}
    return out


def record_proof_of_payment(
    loan_id: str,
    pop_url: str,
) -> Dict[str, Any]:
    """
    Record proof-of-payment for a loan.
    - If loan status is \"matched\": lender POP (proof they sent the money) -> set popUrl, popUploadedAt, status \"active\", loan_request \"loaned\".
    - If loan status is \"active\": borrower repayment POP (proof they repaid). Requires a pending_repayment for this loan with yocoPaidAt set.
      Then: set repaymentPopUrl, repaymentPopUploadedAt, call complete_repayment(loan_id), delete pending_repayment.
    """
    loan_id_clean = (loan_id or "").strip()
    if not loan_id_clean:
        return {"status": "error", "error_message": "loan_id required"}
    pop_url_clean = (pop_url or "").strip()
    if not pop_url_clean:
        return {"status": "error", "error_message": "pop_url required"}

    try:
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP
    except ImportError:  # pragma: no cover
        from google.cloud.firestore import SERVER_TIMESTAMP

    db = _get_db()
    loan_ref = db.collection("loans").document(loan_id_clean)
    loan_snap = loan_ref.get()
    if not loan_snap.exists:
        return {"status": "error", "error_message": "loan not found"}
    loan_data = loan_snap.to_dict() or {}
    current_status = (loan_data.get("status") or "").strip()
    loan_request_id = loan_data.get("loanRequestId")
    now = SERVER_TIMESTAMP

    # Repayment POP: loan already active, borrower uploaded proof of repaying (Yoco must already be paid)
    if current_status == "active":
        pending_query = db.collection("pending_repayments").where("loanId", "==", loan_id_clean).limit(1)
        pending_docs = list(pending_query.stream())
        pending_with_yoco_paid = None
        for doc in pending_docs:
            d = doc.to_dict() or {}
            if d.get("yocoPaidAt") is not None:
                pending_with_yoco_paid = doc
                break
        if pending_with_yoco_paid is None:
            return {"status": "error", "error_message": "No repaid Yoco payment found for this loan. Pay via the repayment link first, then upload proof."}
        loan_ref.update({
            "repaymentPopUrl": pop_url_clean,
            "repaymentPopUploadedAt": now,
        })
        complete_repayment(loan_id_clean)
        db.collection("pending_repayments").document(pending_with_yoco_paid.id).delete()
        logger.info("record_proof_of_payment loan_id=%s (repayment POP)", loan_id_clean)
        return {"status": "success", "repayment_recorded": True}

    # Lender POP: proof they sent the loan money
    if current_status != "matched":
        return {"status": "error", "error_message": "Loan is not in matched or active status."}
    loan_ref.update(
        {
            "popUrl": pop_url_clean,
            "popUploadedAt": now,
            "status": "active",
        }
    )
    if loan_request_id:
        req_ref = db.collection("loan_requests").document(str(loan_request_id))
        req_ref.update({"status": "loaned", "updatedAt": now})
    logger.info("record_proof_of_payment loan_id=%s (lender POP)", loan_id_clean)
    return {"status": "success"}


# ---------- Wrap as ADK FunctionTools ----------
create_verification_link_tool = FunctionTool(create_verification_link)
check_verification_result_tool = FunctionTool(check_verification_result)
create_lender_profile_tool = FunctionTool(create_lender_profile)
create_borrower_profile_tool = FunctionTool(create_borrower_profile)
update_borrower_verified_tool = FunctionTool(update_borrower_verified)
get_lender_or_borrower_tool = FunctionTool(get_lender_or_borrower)
create_loan_request_tool = FunctionTool(create_loan_request)
fetch_loan_requests_tool = FunctionTool(fetch_loan_requests)
fetch_unpaid_loans_tool = FunctionTool(fetch_unpaid_loans)
unlock_loan_request_tool = FunctionTool(unlock_loan_request)
create_unlock_payment_link_tool = FunctionTool(create_unlock_payment_link)
check_unlock_payment_status_tool = FunctionTool(check_unlock_payment_status)
get_unlocked_request_details_tool = FunctionTool(get_unlocked_request_details)
accept_loan_request_tool = FunctionTool(accept_loan_request)
update_lender_repayment_details_tool = FunctionTool(update_lender_repayment_details)
create_repayment_payment_link_tool = FunctionTool(create_repayment_payment_link)
check_repayment_payment_status_tool = FunctionTool(check_repayment_payment_status)
get_my_lending_stats_tool = FunctionTool(get_my_lending_stats)
record_proof_of_payment_tool = FunctionTool(record_proof_of_payment)
