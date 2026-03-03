"""
Gamification tools: Kasi Points (award, balance, upvote, redeem voucher).
- award_points_tool: increment user kasiPoints (used when approved by upvotes, create listing, etc.)
- check_balance_tool: read user kasiPoints
- record_upvote_tool: add one upvote by shortCode; at 3 upvotes → approve and award 25 pts, notify poster
- redeem_voucher_tool: exchange points for preloaded voucher code (A/B/C tiers)
- get_voucher_stock_tool: count available vouchers per value for menu
"""
import logging
from typing import Any, Optional

from google.adk.tools import FunctionTool
from google.cloud import firestore

from .firebase_tools import _get_db, _mask_author, _normalize_wa_number, get_user

logger = logging.getLogger("queens_connect.tools.gamification")

# Voucher tiers: A=R10/50pts, B=R20/100pts, C=R50/200pts
VOUCHER_TIERS = {
    "A": {"value": 10, "cost": 50},
    "B": {"value": 20, "cost": 100},
    "C": {"value": 50, "cost": 200},
}


def _create_notification(target_uid: str, title: str, body: str) -> None:
    """Write a notification doc for the user (e.g. when their item gets 3 upvotes)."""
    try:
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP
    except ImportError:
        from google.cloud.firestore import SERVER_TIMESTAMP
    db = _get_db()
    ref = db.collection("notifications").document()
    ref.set({
        "targetUid": target_uid,
        "title": title,
        "body": body,
        "read": False,
        "createdAt": SERVER_TIMESTAMP,
    })
    logger.info("_create_notification created for target=%s", _mask_author(target_uid))


def award_points(wa_number: str, points: int, reason: str) -> dict:
    """
    Award Kasi Points to a user (atomic increment). Use for: community upvote approval (25),
    create listing (15), create event (5), stokvel create/join, repay on time (30), lend success (15), etc.
    Returns status and new balance (if read) or success.
    """
    wa = _normalize_wa_number(wa_number)
    if not wa:
        return {"status": "error", "error_message": "wa_number required"}
    if not isinstance(points, int) or points <= 0:
        return {"status": "error", "error_message": "points must be a positive integer"}
    try:
        from google.cloud.firestore_v1 import Increment
    except ImportError:
        try:
            from google.cloud.firestore import Increment
        except ImportError:
            return {"status": "error", "error_message": "Firestore Increment not available"}
    db = _get_db()
    ref = db.collection("users").document(wa)
    ref.update({"kasiPoints": Increment(points)})
    logger.info("award_points wa=%s points=%s reason=%s", _mask_author(wa), points, reason)
    return {"status": "success", "points_awarded": points, "reason": reason}


def check_balance(wa_number: str) -> dict:
    """Get user's current Kasi Points balance (default 0 if missing)."""
    wa = _normalize_wa_number(wa_number)
    if not wa:
        return {"status": "error", "error_message": "wa_number required", "balance": 0}
    out = get_user(wa)
    if not out.get("exists"):
        return {"status": "success", "balance": 0}
    balance = out.get("kasiPoints")
    if balance is None:
        balance = 0
    try:
        balance = int(balance)
    except (TypeError, ValueError):
        balance = 0
    return {"status": "success", "balance": balance}


def record_upvote(wa_number: str, short_code: str) -> dict:
    """
    Record an upvote for a pending InfoBit or transport fare by shortCode.
    Exactly 3 unique upvotes (different waNumbers) → status approved, 25 points to author, notification.
    Author cannot upvote own; duplicate upvotes are ignored with message.
    """
    wa = _normalize_wa_number(wa_number)
    if not wa:
        return {"status": "error", "error_message": "wa_number required"}
    code = (short_code or "").strip().upper()
    if not code or len(code) != 6:
        return {"status": "error", "error_message": "short_code must be 6 characters (e.g. ABC123)"}
    db = _get_db()
    # Resolve shortCode to doc in infoBits or transportFares
    for coll in ("infoBits", "transportFares"):
        q = db.collection(coll).where("shortCode", "==", code).limit(1)
        docs = list(q.stream())
        if not docs:
            continue
        doc_ref = docs[0].reference
        data = docs[0].to_dict() or {}
        author_uid = data.get("authorUid") or ""
        if author_uid == wa:
            return {"status": "error", "error_message": "You can't upvote your own post."}
        status = (data.get("status") or "").strip()
        if status != "pending":
            return {"status": "error", "error_message": "This one is no longer pending (already approved or expired)."}
        upvote_wa = data.get("upvoteWaNumbers") or []
        if wa in upvote_wa:
            return {"status": "error", "error_message": "You already upvoted this one."}
        upvote_wa = list(upvote_wa) + [wa]
        try:
            from google.cloud.firestore_v1 import SERVER_TIMESTAMP
        except ImportError:
            from google.cloud.firestore import SERVER_TIMESTAMP
        update_data = {"upvoteWaNumbers": upvote_wa}
        if len(upvote_wa) >= 3:
            update_data["status"] = "approved"
            update_data["pointsAwardedForApproval"] = True
        doc_ref.update(update_data)
        if len(upvote_wa) >= 3:
            reason = "community_upvoted_infobit" if coll == "infoBits" else "community_upvoted_taxi_price"
            award_points(author_uid, 25, reason)
            # Notify poster
            title = "3 upvotes — 25 Kasi Points!"
            snippet = (data.get("text") or data.get("fromPlace") or "")[:40]
            body = f"Yoh legend! Your post just got 3 upvotes — 25 Kasi Points added! Community says it's real."
            _create_notification(author_uid, title, body)
        return {"status": "success", "message": "Upvote counted!", "upvotes_now": len(upvote_wa)}
    return {"status": "error", "error_message": "No pending post found with that code. Check the code and try again."}


def redeem_voucher(wa_number: str, tier: str) -> dict:
    """
    Redeem Kasi Points for a voucher code. tier: A (R10, 50 pts), B (R20, 100 pts), C (R50, 200 pts).
    Uses a transaction: check balance, claim one available code, deduct points, return code.
    """
    wa = _normalize_wa_number(wa_number)
    if not wa:
        return {"status": "error", "error_message": "wa_number required"}
    t = (tier or "").strip().upper()
    if t not in VOUCHER_TIERS:
        return {"status": "error", "error_message": "Invalid tier. Use A, B, or C."}
    value = VOUCHER_TIERS[t]["value"]
    cost = VOUCHER_TIERS[t]["cost"]
    try:
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP, Increment
    except ImportError:
        from google.cloud.firestore import SERVER_TIMESTAMP, Increment
    db = _get_db()
    user_ref = db.collection("users").document(wa)
    # Find one available voucher with this value
    q = db.collection("voucher_pool").where("value", "==", value).where("status", "==", "available").limit(1)
    code_docs = list(q.stream())
    if not code_docs:
        return {"status": "error", "error_message": "no_stock", "tier": t, "value": value}
    code_ref = code_docs[0].reference
    code_id = code_docs[0].id
    user_snap = user_ref.get()
    if not user_snap.exists:
        return {"status": "error", "error_message": "User not found."}
    current = user_snap.to_dict().get("kasiPoints") or 0
    try:
        current = int(current)
    except (TypeError, ValueError):
        current = 0
    if current < cost:
        return {"status": "error", "error_message": "insufficient_points", "balance": current, "cost": cost}
    # Transaction: claim code and deduct points
    @firestore.transactional
    def _redeem_txn(transaction, code_ref, user_ref, wa, cost):
        code_snap = code_ref.get(transaction=transaction)
        if not code_snap.exists or (code_snap.to_dict() or {}).get("status") != "available":
            raise ValueError("voucher_no_longer_available")
        user_snap2 = user_ref.get(transaction=transaction)
        bal = (user_snap2.to_dict() or {}).get("kasiPoints") or 0
        try:
            bal = int(bal)
        except (TypeError, ValueError):
            bal = 0
        if bal < cost:
            raise ValueError("insufficient_points")
        transaction.update(code_ref, {
            "status": "redeemed",
            "redeemedBy": wa,
            "redeemedAt": SERVER_TIMESTAMP,
        })
        transaction.update(user_ref, {"kasiPoints": Increment(-cost)})

    try:
        transaction = db.transaction()
        _redeem_txn(transaction, code_ref, user_ref, wa, cost)
    except ValueError as e:
        if str(e) == "voucher_no_longer_available":
            return {"status": "error", "error_message": "no_stock", "tier": t}
        if str(e) == "insufficient_points":
            return {"status": "error", "error_message": "insufficient_points", "cost": cost}
        return {"status": "error", "error_message": str(e)}
    new_balance = current - cost
    logger.info("redeem_voucher wa=%s tier=%s code=%s", _mask_author(wa), t, code_id[:8] + "...")
    return {"status": "success", "code": code_id, "tier": t, "value": value, "points_left": new_balance}


def get_voucher_stock() -> dict:
    """Return counts of available vouchers per value (R10, R20, R50) for menu display."""
    db = _get_db()
    out = {"R10": 0, "R20": 0, "R50": 0}
    for value, key in [(10, "R10"), (20, "R20"), (50, "R50")]:
        q = db.collection("voucher_pool").where("value", "==", value).where("status", "==", "available")
        out[key] = len(list(q.stream()))
    return {"status": "success", "stock": out}


# ---------- ADK FunctionTool wrappers ----------
award_points_tool = FunctionTool(award_points)
check_balance_tool = FunctionTool(check_balance)
record_upvote_tool = FunctionTool(record_upvote)
redeem_voucher_tool = FunctionTool(redeem_voucher)
get_voucher_stock_tool = FunctionTool(get_voucher_stock)
