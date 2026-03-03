"""
Stokvel create, list, and join flows.
- create_stokvel: name, about, monthly contribution; store unique accessToken on doc.
- fetch_stokvels: public list (name, about, monthlyContributionCents only; no contact/token).
- add_stokvel_member: add member to stokvel with status pending_first_payment.
- create_stokvel_contribution_payment_link: create Ikhokha-style payment link for first contribution.
"""
import logging
import os
import secrets
from typing import Any, Dict, List

from google.adk.tools import FunctionTool

from .firebase_tools import _get_db, get_user
from .gamification_tools import award_points

logger = logging.getLogger("queens_connect.tools.stokvel")


def _mask_wa(wa: str) -> str:
    if not wa or len(wa) <= 4:
        return "(none)"
    return wa[:4] + "***"


def create_stokvel(
    owner_wa_number: str,
    name: str,
    about: str,
    monthly_contribution_cents: int,
) -> Dict[str, Any]:
    """
    Create a new stokvel. Owner is the current user (owner_wa_number).
    Generates a unique access token and stores it on the stokvel doc for balance/payout use.
    Returns status, stokvelId, and accessToken on success.
    """
    owner = (owner_wa_number or "").strip()
    if not owner:
        return {"status": "error", "error_message": "owner_wa_number required"}
    name = (name or "").strip()
    if not name:
        return {"status": "error", "error_message": "name required"}
    about = (about or "").strip()
    if not about:
        return {"status": "error", "error_message": "about required"}
    try:
        monthly_cents = int(monthly_contribution_cents)
        if monthly_cents <= 0:
            return {"status": "error", "error_message": "monthly_contribution_cents must be positive"}
    except (TypeError, ValueError):
        return {"status": "error", "error_message": "monthly_contribution_cents must be a positive number"}

    try:
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP
    except ImportError:
        from google.cloud.firestore import SERVER_TIMESTAMP

    token = secrets.token_urlsafe(12)
    db = _get_db()
    ref = db.collection("stokvels").document()
    doc = {
        "name": name,
        "about": about,
        "monthlyContributionCents": monthly_cents,
        "ownerWaNumber": owner,
        "accessToken": token,
        "createdAt": SERVER_TIMESTAMP,
        "updatedAt": SERVER_TIMESTAMP,
    }
    ref.set(doc)
    try:
        award_points(owner, 10, "create_stokvel")
    except Exception as e:
        logger.warning("create_stokvel: award_points failed: %s", e)
    logger.info("create_stokvel owner=%s name=%r id=%s", _mask_wa(owner), name[:50], ref.id)
    return {
        "status": "success",
        "stokvelId": ref.id,
        "accessToken": token,
        "name": name,
    }


def fetch_stokvels(limit: int = 20) -> Dict[str, Any]:
    """
    Fetch all stokvels for public listing. Returns only name, about, monthlyContributionCents
    (and id). No owner contact details, no accessToken.
    """
    try:
        from google.cloud.firestore_v1.query import Query
        _DIR_DESC = Query.DESCENDING
    except ImportError:
        _DIR_DESC = "DESCENDING"

    db = _get_db()
    ref = db.collection("stokvels").order_by("createdAt", direction=_DIR_DESC).limit(min(int(limit), 50))
    results: List[Dict[str, Any]] = []
    for doc in ref.stream():
        d = doc.to_dict() or {}
        results.append({
            "id": doc.id,
            "name": d.get("name", ""),
            "about": d.get("about", ""),
            "monthlyContributionCents": d.get("monthlyContributionCents", 0),
        })
    logger.info("fetch_stokvels count=%s", len(results))
    return {"status": "success", "stokvels": results}


def get_stokvel_by_id_or_name(stokvel_id: str, name_query: str = "") -> Dict[str, Any]:
    """
    Get a single stokvel by id, or by name match if id looks like a name.
    Returns full doc (including ownerWaNumber for payment link; do not expose to user).
    Used internally by join flow.
    """
    db = _get_db()
    stokvel_id = (stokvel_id or "").strip()
    name_query = (name_query or "").strip()

    if stokvel_id and len(stokvel_id) >= 10 and "/" not in stokvel_id:
        ref = db.collection("stokvels").document(stokvel_id)
        snap = ref.get()
        if snap.exists:
            d = snap.to_dict() or {}
            return {"status": "success", "stokvel": {"id": snap.id, **d}}
        if not name_query:
            return {"status": "error", "error_message": "Stokvel not found."}

    name_lower = (name_query or stokvel_id).lower()
    for doc in db.collection("stokvels").stream():
        d = doc.to_dict() or {}
        if name_lower in (d.get("name") or "").lower():
            return {"status": "success", "stokvel": {"id": doc.id, **d}}
    return {"status": "error", "error_message": "Stokvel not found."}


def add_stokvel_member(stokvel_id: str, member_wa_number: str) -> Dict[str, Any]:
    """
    Add a member to a stokvel. Writes to stokvel_members with status pending_first_payment.
    Fails if stokvel does not exist or member already in stokvel.
    """
    stokvel_id = (stokvel_id or "").strip()
    member = (member_wa_number or "").strip()
    if not stokvel_id:
        return {"status": "error", "error_message": "stokvel_id required"}
    if not member:
        return {"status": "error", "error_message": "member_wa_number required"}

    try:
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP
    except ImportError:
        from google.cloud.firestore import SERVER_TIMESTAMP

    db = _get_db()
    stokvel_ref = db.collection("stokvels").document(stokvel_id)
    stokvel_snap = stokvel_ref.get()
    if not stokvel_snap.exists:
        return {"status": "error", "error_message": "Stokvel not found."}
    stokvel_data = stokvel_snap.to_dict() or {}

    members_ref = db.collection("stokvel_members")
    existing = members_ref.where("stokvelId", "==", stokvel_id).where("memberWaNumber", "==", member).limit(1).get()
    if existing:
        return {"status": "error", "error_message": "You are already a member of this stokvel."}

    ref = members_ref.document()
    ref.set({
        "stokvelId": stokvel_id,
        "memberWaNumber": member,
        "status": "pending_first_payment",
        "joinedAt": SERVER_TIMESTAMP,
    })
    logger.info("add_stokvel_member stokvel=%s member=%s id=%s", stokvel_id[:8], _mask_wa(member), ref.id)

    # Notify stokvel owner of new member (backend writes to notifications; Firebase callable also exists for client use)
    owner_wa = (stokvel_data.get("ownerWaNumber") or "").strip()
    if owner_wa:
        member_name = ""
        try:
            user_doc = get_user(member)
            if user_doc.get("exists") and user_doc.get("name"):
                member_name = (user_doc.get("name") or "").strip()
        except Exception:
            pass
        display_name = member_name or "A member"
        stokvel_name = (stokvel_data.get("name") or "Stokvel").strip()
        try:
            db.collection("notifications").add({
                "targetUid": owner_wa,
                "title": "New stokvel join request",
                "body": f"{display_name} requested to join your stokvel **{stokvel_name}**.",
                "type": "stokvel_new_member",
                "read": False,
                "createdAt": SERVER_TIMESTAMP,
            })
        except Exception as e:
            logger.warning("add_stokvel_member: failed to write notification: %s", e)

    # Award 5 Kasi Points to stokvel owner when someone joins (max 50 per stokvel)
    if owner_wa:
        try:
            join_count = int(stokvel_data.get("joinPointsAwardedCount") or 0)
            if join_count < 50:
                award_points(owner_wa, 5, "stokvel_join")
                stokvel_ref.update({"joinPointsAwardedCount": join_count + 1})
        except Exception as e:
            logger.warning("add_stokvel_member: award_points failed: %s", e)

    return {
        "status": "success",
        "stokvelMemberId": ref.id,
        "stokvelId": stokvel_id,
        "stokvelName": stokvel_data.get("name", ""),
        "monthlyContributionCents": stokvel_data.get("monthlyContributionCents", 0),
        "ownerWaNumber": stokvel_data.get("ownerWaNumber", ""),
    }


def create_stokvel_contribution_payment_link(
    stokvel_id: str,
    member_wa_number: str,
    amount_cents: int,
    description: str = "",
) -> Dict[str, Any]:
    """
    Create a payment link for a stokvel contribution (e.g. first contribution).
    Looks up stokvel to get owner as payee; creates a doc in payments collection and returns
    the payment URL (Ikhokha-style). Member is the payer.
    """
    stokvel_id = (stokvel_id or "").strip()
    member = (member_wa_number or "").strip()
    if not stokvel_id:
        return {"status": "error", "error_message": "stokvel_id required"}
    if not member:
        return {"status": "error", "error_message": "member_wa_number required"}
    try:
        amount_cents = int(amount_cents)
        if amount_cents <= 0:
            return {"status": "error", "error_message": "amount_cents must be positive"}
    except (TypeError, ValueError):
        return {"status": "error", "error_message": "amount_cents must be a positive number"}

    out = get_stokvel_by_id_or_name(stokvel_id, "")
    if out.get("status") != "success" or not out.get("stokvel"):
        return {"status": "error", "error_message": "Stokvel not found."}
    stokvel = out["stokvel"]
    owner_wa = (stokvel.get("ownerWaNumber") or "").strip()
    if not owner_wa:
        return {"status": "error", "error_message": "Stokvel has no owner."}
    stokvel_name = (stokvel.get("name") or "Stokvel").strip()
    desc = (description or f"First contribution – {stokvel_name}").strip()

    try:
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP
    except ImportError:
        from google.cloud.firestore import SERVER_TIMESTAMP

    db = _get_db()
    payment_ref = db.collection("payments").document()
    payment_ref.set({
        "payerUid": member,
        "payeeUid": owner_wa,
        "amountCents": amount_cents,
        "status": "pending",
        "description": desc,
        "dealId": None,
        "ikhokhaRef": None,
        "createdAt": SERVER_TIMESTAMP,
        "updatedAt": SERVER_TIMESTAMP,
    })
    base_url = (os.environ.get("IKHOKHA_BASE_URL") or "https://pay.ikhokha.com").strip().rstrip("/")
    from urllib.parse import quote
    payment_link = f"{base_url}/pay?ref=qc-{payment_ref.id}&amount={amount_cents}&desc={quote(desc)}"
    logger.info("create_stokvel_contribution_payment_link stokvel=%s member=%s paymentId=%s", stokvel_id[:8], _mask_wa(member), payment_ref.id)
    return {
        "status": "success",
        "paymentLink": payment_link,
        "paymentId": payment_ref.id,
        "amountCents": amount_cents,
        "stokvelName": stokvel_name,
    }


# ADK FunctionTool wrappers for agents
create_stokvel_tool = FunctionTool(create_stokvel)
fetch_stokvels_tool = FunctionTool(fetch_stokvels)
get_stokvel_by_id_or_name_tool = FunctionTool(get_stokvel_by_id_or_name)
add_stokvel_member_tool = FunctionTool(add_stokvel_member)
create_stokvel_contribution_payment_link_tool = FunctionTool(create_stokvel_contribution_payment_link)
