"""
Direct Firestore access via Firebase Admin SDK.
Granular save/fetch tools per collection with strict schemas. All saved data must include tags.
No random fields on insert; validation enforces schema per collection.
"""
import logging
import random
import string
from datetime import date, datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("queens_connect.tools.firebase")

try:
    from ..config import FIREBASE_PROJECT_ID, FIRESTORE_EMULATOR_HOST
except ImportError:
    from config import FIREBASE_PROJECT_ID, FIRESTORE_EMULATOR_HOST

# ---------------------------------------------------------------------------
# Schemas: required keys, optional keys. Only these fields are allowed.
# All collections require "tags" (list of strings). System adds authorUid/reporterUid, createdAt.
# ---------------------------------------------------------------------------
# All table schemas include an optional "link" field (URL) for reference.
SCHEMAS = {
    "communityUpdates": {
        "required": ["title", "text", "tags"],
        "optional": ["location", "link"],
    },
    "complaints": {
        "required": ["itemType", "itemId", "reason", "tags"],
        "optional": ["link"],
    },
    "emergencyNumbers": {
        "required": ["name", "number", "category", "tags"],
        "optional": ["location", "link"],
    },
    "events": {
        "required": ["title", "description", "when", "where", "tags"],
        "optional": ["contactDetails", "link"],
    },
    "govInfo": {
        "required": ["title", "description", "category", "tags"],
        "optional": ["link"],
    },
    "infoBits": {
        "required": ["text", "tags"],
        "optional": ["location", "expiresHours", "link"],
    },
    "knowledgeShare": {
        "required": ["title", "content", "category", "tags"],
        "optional": ["link"],
    },
    "listings": {
        "required": ["title", "description", "location", "type", "tags"],
        "optional": ["priceRange", "contact", "link"],
    },
    "lostAndFound": {
        "required": ["text", "location", "type", "tags"],
        "optional": ["photoUrl", "link"],
    },
    "news": {
        "required": ["title", "tags"],
        "optional": ["summaryEn", "summaryXh", "sourceUrl", "link"],
    },
    "places": {
        "required": ["foundAt", "name", "description", "opens", "closes", "contactDetails", "tags"],
        "optional": ["link"],
    },
    "suburbs": {
        "required": ["name", "townId", "tags"],
        "optional": ["description", "link"],
    },
    "towns": {
        "required": ["name", "tags"],
        "optional": ["description", "link"],
    },
    "transportFares": {
        "required": ["fromPlace", "toPlace", "fare", "howLongItTakesToTravel", "transportType", "tags"],
        "optional": ["link"],
    },
}

TRANSPORT_TYPES = frozenset({"cab", "lift", "bus", "taxi"})
LOST_FOUND_TYPES = frozenset({"lost", "found"})

_db = None


def _normalize_emulator_host(value: str) -> str:
    """Return host:port only. gRPC fails if given http://host:port."""
    if not value or not value.strip():
        return ""
    s = value.strip()
    if "://" in s:
        s = s.split("://", 1)[1]
    return s


def _get_db():
    global _db
    if _db is not None:
        logger.debug("_get_db: reusing existing Firestore client")
        return _db
    import os
    emulator = _normalize_emulator_host(FIRESTORE_EMULATOR_HOST or "")
    if emulator:
        os.environ["FIRESTORE_EMULATOR_HOST"] = emulator
        logger.info("_get_db: using Firestore emulator at %s", emulator)
    else:
        logger.info("_get_db: using production Firestore")
    import firebase_admin
    from firebase_admin import firestore
    try:
        firebase_admin.get_app()
        logger.debug("_get_db: Firebase app already initialized")
    except ValueError:
        firebase_admin.initialize_app(options={"projectId": FIREBASE_PROJECT_ID})
        logger.info("_get_db: initialized Firebase app project_id=%s", FIREBASE_PROJECT_ID)
    _db = firestore.client()
    return _db


def _mask_author(uid: str) -> str:
    """Return a short mask of author/WA number for logging (e.g. 082***)."""
    if not uid or len(uid) <= 4:
        return "(none)"
    return (uid[:4] + "***") if len(uid) > 4 else uid


def _validate_and_prepare(
    collection: str,
    data: dict,
    author_wa_number: str,
) -> tuple[dict, Optional[str]]:
    """
    Validate data against collection schema; only allow schema fields.
    Returns (document_dict for Firestore, error_message or None).
    """
    logger.debug("_validate_and_prepare collection=%s author=%s keys=%s", collection, _mask_author(author_wa_number or ""), list(data.keys()) if data else [])
    if collection not in SCHEMAS:
        logger.warning("_validate_and_prepare unknown collection=%s", collection)
        return {}, f"Unknown collection: {collection}"
    schema = SCHEMAS[collection]
    required = set(schema["required"])
    optional = set(schema.get("optional", []))
    allowed = required | optional

    # Strip to allowed keys only
    doc = {k: v for k, v in data.items() if k in allowed}
    # Ensure tags present and is list of strings
    tags = doc.get("tags")
    if not tags:
        logger.warning("_validate_and_prepare collection=%s validation failed: missing tags", collection)
        return {}, "Every saved record must include 'tags' (list of strings)."
    if isinstance(tags, list):
        tags = [str(t).strip().lower() for t in tags if str(t).strip()]
    else:
        tags = [str(tags).strip().lower()] if str(tags).strip() else []
    if not tags:
        logger.warning("_validate_and_prepare collection=%s validation failed: empty tags", collection)
        return {}, "At least one non-empty tag is required."
    doc["tags"] = tags

    missing = required - set(doc.keys())
    if missing:
        logger.warning("_validate_and_prepare collection=%s validation failed: missing required %s", collection, sorted(missing))
        return {}, f"Missing required fields: {sorted(missing)}"

    # Enums
    if collection == "transportFares":
        tt = (doc.get("transportType") or "").strip().lower()
        if tt not in TRANSPORT_TYPES:
            logger.warning("_validate_and_prepare collection=transportFares invalid transportType=%r", doc.get("transportType"))
            return {}, f"transportType must be one of: {sorted(TRANSPORT_TYPES)}"
        doc["transportType"] = tt
    if collection == "lostAndFound":
        t = (doc.get("type") or "lost").strip().lower()
        doc["type"] = "found" if t == "found" else "lost"

    # Author/reporter UID
    uid = (author_wa_number or "").strip()
    if not uid:
        logger.warning("_validate_and_prepare collection=%s validation failed: missing author_wa_number", collection)
        return {}, "author_wa_number is required for saving data."
    if collection == "complaints":
        doc["reporterUid"] = uid
    else:
        doc["authorUid"] = uid

    try:
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP
    except ImportError:
        from google.cloud.firestore import SERVER_TIMESTAMP
    doc["createdAt"] = SERVER_TIMESTAMP

    # Optional expiresAt for infoBits
    if collection == "infoBits" and doc.get("expiresHours"):
        from datetime import datetime, timezone, timedelta
        doc["expiresAt"] = datetime.now(timezone.utc) + timedelta(hours=float(doc.pop("expiresHours", 0)))
    elif collection == "infoBits":
        doc.pop("expiresHours", None)
        doc.pop("expiresAt", None)

    logger.debug("_validate_and_prepare collection=%s ok", collection)
    return doc, None


def _generate_short_code() -> str:
    """Generate a 6-character alphanumeric code for pending InfoBits/transportFares (for upvote ABC123 style)."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


def _save_doc(collection: str, doc: dict) -> str:
    """Insert document into collection; returns document id."""
    db = _get_db()
    ref = db.collection(collection).document()
    try:
        ref.set(doc)
        logger.info("_save_doc collection=%s id=%s", collection, ref.id)
        return ref.id
    except Exception as e:
        logger.exception("_save_doc collection=%s failed: %s", collection, e)
        raise


def _posted_ago(created_at: Any) -> str:
    """Turn createdAt (Firestore timestamp or datetime) into a short relative string e.g. '2h ago', '1 day ago'."""
    if created_at is None:
        return ""
    now = datetime.now(timezone.utc)
    try:
        if hasattr(created_at, "seconds"):
            # Firestore Timestamp
            from datetime import timedelta
            dt = datetime.fromtimestamp(created_at.seconds, tz=timezone.utc)
        elif hasattr(created_at, "isoformat"):
            dt = created_at
            if getattr(dt, "tzinfo", None) is None:
                dt = dt.replace(tzinfo=timezone.utc)
        else:
            return ""
        delta = now - dt
        total_seconds = int(delta.total_seconds())
        if total_seconds < 60:
            return "just now"
        if total_seconds < 3600:
            return f"{total_seconds // 60}m ago"
        if total_seconds < 86400:
            return f"{total_seconds // 3600}h ago"
        days = total_seconds // 86400
        if days == 1:
            return "1 day ago"
        if days < 7:
            return f"{days} days ago"
        return f"{days // 7}w ago"
    except Exception:
        return ""


def _created_at_sort_key(created_at: Any) -> float:
    """Return a numeric sort key for createdAt (Firestore Timestamp or datetime). Older = smaller."""
    if created_at is None:
        return 0.0
    try:
        if hasattr(created_at, "seconds"):
            return float(created_at.seconds) + (float(getattr(created_at, "nanoseconds", 0)) / 1e9)
        if hasattr(created_at, "timestamp"):
            return created_at.timestamp()
        if hasattr(created_at, "isoformat"):
            dt = created_at
            if getattr(dt, "tzinfo", None) is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp()
    except Exception:
        pass
    return 0.0


def _format_verification_hint(result: dict, collection: str) -> dict:
    """
    Add verification display hints to a single result from infoBits or transportFares.
    Adds: verificationPrefix, upvoteInstruction (only when pending + shortCode), postedAgo.
    """
    out = dict(result)
    status = (result.get("status") or "").strip().lower()
    short_code = (result.get("shortCode") or "").strip()
    if status == "pending":
        out["verificationPrefix"] = "UNVERIFIED (waiting for community love)"
        if short_code:
            out["upvoteInstruction"] = (
                f"Reply exactly: upvote {short_code} if true "
                "(3 upvotes = 25 Kasi Points for the poster and it becomes verified)."
            )
        else:
            out["upvoteInstruction"] = ""
    else:
        out["verificationPrefix"] = "Verified by community"
        out["upvoteInstruction"] = ""
    created = result.get("createdAt")
    out["postedAgo"] = _posted_ago(created) if created else ""
    return out


def _fetch_docs(
    collection: str,
    query: str = "",
    filters: Optional[dict] = None,
    limit: int = 10,
) -> list[dict]:
    """Stream collection, filter by query/filters, return list of dicts (id + data)."""
    logger.info("_fetch_docs collection=%s query=%r filters=%s limit=%s", collection, (query or "").strip()[:80], filters, limit)
    db = _get_db()
    try:
        from google.cloud.firestore_v1.query import Query
        _DIR_DESC = Query.DESCENDING
    except ImportError:
        _DIR_DESC = "DESCENDING"

    try:
        ref = db.collection(collection).order_by("createdAt", direction=_DIR_DESC).limit(50)
        q = (query or "").lower()
        location = ((filters or {}).get("location") or "").lower()
        results = []
        for doc in ref.stream():
            if len(results) >= min(int(limit), 20):
                break
            d = doc.to_dict()
            # Simple text match on string fields and tags (include fromPlace, toPlace, transportType for transportFares)
            text_parts = " ".join(
                str(d.get(k, ""))
                for k in (
                    "title",
                    "text",
                    "description",
                    "name",
                    "content",
                    "summaryEn",
                    "summaryXh",
                    "fromPlace",
                    "toPlace",
                    "transportType",
                )
            ).lower()
            tags_str = " ".join(d.get("tags") or []).lower()
            loc = (d.get("location") or d.get("foundAt") or "").lower()
            match = not q or q in text_parts or q in tags_str or (location and location in loc)
            if match:
                results.append({"id": doc.id, **d})
        logger.info("_fetch_docs collection=%s returning count=%s", collection, len(results))
        return results
    except Exception as e:
        logger.exception("_fetch_docs collection=%s failed: %s", collection, e)
        raise


# ---------- Save tools (one per table) ----------


def save_community_updates_tool(data: dict, author_wa_number: str) -> dict:
    """
    Save a community update (local announcements, notices) to Firestore.
    Use when the user shares or reports community news, notices, or updates.
    Required: title, text, tags. Optional: location.
    Tags are required and must be a non-empty list.
    Returns status and document id on success; error message on validation failure.
    """
    logger.info("save_community_updates_tool called author=%s title=%r", _mask_author(author_wa_number), (data.get("title") or "")[:60])
    doc, err = _validate_and_prepare("communityUpdates", data, author_wa_number)
    if err:
        logger.warning("save_community_updates_tool validation failed: %s", err)
        return {"status": "error", "error_message": err}
    doc_id = _save_doc("communityUpdates", doc)
    return {"status": "success", "data": {"id": doc_id}}


def save_complaints_tool(data: dict, author_wa_number: str) -> dict:
    """
    Save a complaint or report (e.g. about a listing or user) to Firestore.
    Use when the user wants to report something (itemType, itemId, reason).
    Required: itemType, itemId, reason, tags.
    Returns status and id on success.
    """
    logger.info("save_complaints_tool called author=%s itemType=%s itemId=%s", _mask_author(author_wa_number), data.get("itemType"), data.get("itemId"))
    doc, err = _validate_and_prepare("complaints", data, author_wa_number)
    if err:
        logger.warning("save_complaints_tool validation failed: %s", err)
        return {"status": "error", "error_message": err}
    doc_id = _save_doc("complaints", doc)
    return {"status": "success", "data": {"id": doc_id}}


def save_emergency_numbers_tool(data: dict, author_wa_number: str) -> dict:
    """
    Save an emergency or useful contact number (police, ambulance, clinic, etc.) to Firestore.
    Use when the user shares or asks to store a contact for emergencies.
    Required: name, number, category, tags. Optional: location.
    Returns status and document id on success.
    """
    logger.info("save_emergency_numbers_tool called author=%s name=%s category=%s", _mask_author(author_wa_number), data.get("name"), data.get("category"))
    doc, err = _validate_and_prepare("emergencyNumbers", data, author_wa_number)
    if err:
        logger.warning("save_emergency_numbers_tool validation failed: %s", err)
        return {"status": "error", "error_message": err}
    doc_id = _save_doc("emergencyNumbers", doc)
    return {"status": "success", "data": {"id": doc_id}}


def save_events_tool(data: dict, author_wa_number: str) -> dict:
    """
    Save an event (meetup, concert, market, etc.) to Firestore.
    Use when the user shares or creates an event. Required: title, description, when, where, tags.
    Optional: contactDetails. Returns status and document id on success.
    """
    logger.info("save_events_tool called author=%s title=%r when=%s", _mask_author(author_wa_number), (data.get("title") or "")[:50], data.get("when"))
    doc, err = _validate_and_prepare("events", data, author_wa_number)
    if err:
        logger.warning("save_events_tool validation failed: %s", err)
        return {"status": "error", "error_message": err}
    doc_id = _save_doc("events", doc)
    try:
        from .gamification_tools import award_points
        award_points(author_wa_number, 5, "create_event")
    except Exception as e:
        logger.warning("save_events_tool: award_points failed: %s", e)
    return {"status": "success", "data": {"id": doc_id}}


def save_gov_info_tool(data: dict, author_wa_number: str) -> dict:
    """
    Save government or official information (forms, deadlines, offices) to Firestore.
    Use when the user shares or requests to store gov info. Required: title, description, category, tags.
    Optional: link. Returns status and document id on success.
    """
    logger.info("save_gov_info_tool called author=%s title=%r category=%s", _mask_author(author_wa_number), (data.get("title") or "")[:50], data.get("category"))
    doc, err = _validate_and_prepare("govInfo", data, author_wa_number)
    if err:
        logger.warning("save_gov_info_tool validation failed: %s", err)
        return {"status": "error", "error_message": err}
    doc_id = _save_doc("govInfo", doc)
    return {"status": "success", "data": {"id": doc_id}}


def save_info_bits_tool(data: dict, author_wa_number: str) -> dict:
    """
    Save a short info bit (tip, taxi price, load-shedding note, etc.) to Firestore.
    Use when the user shares a quick local fact or update. Required: text, tags.
    Optional: location, expiresHours. Returns status, document id, and shortCode (for community upvotes).
    New docs start as status pending; 3 upvotes in 7 days → approved → 25 Kasi Points.
    """
    logger.info("save_info_bits_tool called author=%s text=%r", _mask_author(author_wa_number), (data.get("text") or "")[:60])
    doc, err = _validate_and_prepare("infoBits", data, author_wa_number)
    if err:
        logger.warning("save_info_bits_tool validation failed: %s", err)
        return {"status": "error", "error_message": err}
    try:
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP
    except ImportError:
        from google.cloud.firestore import SERVER_TIMESTAMP
    doc["status"] = "pending"
    doc["shortCode"] = _generate_short_code()
    doc["upvoteWaNumbers"] = []
    doc["pendingCreatedAt"] = SERVER_TIMESTAMP
    doc_id = _save_doc("infoBits", doc)
    return {"status": "success", "data": {"id": doc_id, "shortCode": doc["shortCode"]}}


def save_knowledge_share_tool(data: dict, author_wa_number: str) -> dict:
    """
    Save a knowledge-share post (how-to, advice, cultural tip) to Firestore.
    Use when the user shares knowledge or how-to content. Required: title, content, category, tags.
    Returns status and document id on success.
    """
    logger.info("save_knowledge_share_tool called author=%s title=%r category=%s", _mask_author(author_wa_number), (data.get("title") or "")[:50], data.get("category"))
    doc, err = _validate_and_prepare("knowledgeShare", data, author_wa_number)
    if err:
        logger.warning("save_knowledge_share_tool validation failed: %s", err)
        return {"status": "error", "error_message": err}
    doc_id = _save_doc("knowledgeShare", doc)
    return {"status": "success", "data": {"id": doc_id}}


def save_listings_tool(data: dict, author_wa_number: str) -> dict:
    """
    Save a marketplace listing (buy/sell/offer) to Firestore.
    Use when the user wants to list something. Required: title, description, location, type, tags.
    Optional: priceRange, contact. Returns status and document id on success.
    """
    logger.info("save_listings_tool called author=%s title=%r type=%s location=%s", _mask_author(author_wa_number), (data.get("title") or "")[:50], data.get("type"), data.get("location"))
    doc, err = _validate_and_prepare("listings", data, author_wa_number)
    if err:
        logger.warning("save_listings_tool validation failed: %s", err)
        return {"status": "error", "error_message": err}
    doc["ownerUid"] = doc.pop("authorUid")
    doc_id = _save_doc("listings", doc)
    try:
        from .gamification_tools import award_points
        award_points(author_wa_number, 15, "create_listing")
    except Exception as e:
        logger.warning("save_listings_tool: award_points failed: %s", e)
    return {"status": "success", "data": {"id": doc_id}}


def save_lost_and_found_tool(data: dict, author_wa_number: str) -> dict:
    """
    Save a lost or found item report to Firestore.
    Use when the user reports something lost or found. Required: text, location, type ('lost' or 'found'), tags.
    Optional: photoUrl. Returns status and document id on success.
    """
    logger.info("save_lost_and_found_tool called author=%s type=%s location=%s text=%r", _mask_author(author_wa_number), data.get("type"), data.get("location"), (data.get("text") or "")[:50])
    doc, err = _validate_and_prepare("lostAndFound", data, author_wa_number)
    if err:
        logger.warning("save_lost_and_found_tool validation failed: %s", err)
        return {"status": "error", "error_message": err}
    doc["reporterUid"] = doc.pop("authorUid")
    doc_id = _save_doc("lostAndFound", doc)
    return {"status": "success", "data": {"id": doc_id}}


def save_news_tool(data: dict, author_wa_number: str) -> dict:
    """
    Save a news item (headline, summary, link) to Firestore.
    Use when the user shares or submits local news. Required: title, tags.
    Optional: summaryEn, summaryXh, sourceUrl. Returns status and document id on success.
    """
    logger.info("save_news_tool called author=%s title=%r", _mask_author(author_wa_number), (data.get("title") or "")[:60])
    doc, err = _validate_and_prepare("news", data, author_wa_number)
    if err:
        logger.warning("save_news_tool validation failed: %s", err)
        return {"status": "error", "error_message": err}
    doc_id = _save_doc("news", doc)
    return {"status": "success", "data": {"id": doc_id}}


def save_places_tool(data: dict, author_wa_number: str) -> dict:
    """
    Save a place (shop, clinic, spaza, etc.) to Firestore.
    Schema: foundAt (where it is), name, description, opens, closes, contactDetails, tags.
    Use when the user shares or adds a local place. Returns status and document id on success.
    """
    logger.info("save_places_tool called author=%s name=%s foundAt=%s", _mask_author(author_wa_number), data.get("name"), data.get("foundAt"))
    doc, err = _validate_and_prepare("places", data, author_wa_number)
    if err:
        logger.warning("save_places_tool validation failed: %s", err)
        return {"status": "error", "error_message": err}
    doc_id = _save_doc("places", doc)
    return {"status": "success", "data": {"id": doc_id}}


def save_suburbs_tool(data: dict, author_wa_number: str) -> dict:
    """
    Save a suburb (area within a town) to Firestore.
    Required: name, townId (reference or id of the town), tags. Optional: description.
    Use when the user shares or adds suburb info. Returns status and document id on success.
    """
    logger.info("save_suburbs_tool called author=%s name=%s townId=%s", _mask_author(author_wa_number), data.get("name"), data.get("townId"))
    doc, err = _validate_and_prepare("suburbs", data, author_wa_number)
    if err:
        logger.warning("save_suburbs_tool validation failed: %s", err)
        return {"status": "error", "error_message": err}
    doc_id = _save_doc("suburbs", doc)
    return {"status": "success", "data": {"id": doc_id}}


def save_towns_tool(data: dict, author_wa_number: str) -> dict:
    """
    Save a town to Firestore (e.g. Komani, Whittlesea, Cofimvaba).
    Required: name, tags. Optional: description.
    Use when the user shares or adds town info. Returns status and document id on success.
    """
    logger.info("save_towns_tool called author=%s name=%s", _mask_author(author_wa_number), data.get("name"))
    doc, err = _validate_and_prepare("towns", data, author_wa_number)
    if err:
        logger.warning("save_towns_tool validation failed: %s", err)
        return {"status": "error", "error_message": err}
    doc_id = _save_doc("towns", doc)
    return {"status": "success", "data": {"id": doc_id}}


def save_transport_fares_tool(data: dict, author_wa_number: str) -> dict:
    """
    Save a transport fare (taxi, bus, lift, cab) between two places to Firestore.
    Required: fromPlace, toPlace, fare, howLongItTakesToTravel, transportType, tags.
    transportType must be one of: cab, lift, bus, taxi.
    Use when the user shares or asks to store a fare. Returns status, document id, and shortCode (for community upvotes).
    New docs start as status pending; 3 upvotes in 7 days → approved → 25 Kasi Points.
    """
    logger.info("save_transport_fares_tool called author=%s fromPlace=%s toPlace=%s transportType=%s fare=%s", _mask_author(author_wa_number), data.get("fromPlace"), data.get("toPlace"), data.get("transportType"), data.get("fare"))
    doc, err = _validate_and_prepare("transportFares", data, author_wa_number)
    if err:
        logger.warning("save_transport_fares_tool validation failed: %s", err)
        return {"status": "error", "error_message": err}
    try:
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP
    except ImportError:
        from google.cloud.firestore import SERVER_TIMESTAMP
    doc["status"] = "pending"
    doc["shortCode"] = _generate_short_code()
    doc["upvoteWaNumbers"] = []
    doc["pendingCreatedAt"] = SERVER_TIMESTAMP
    doc_id = _save_doc("transportFares", doc)
    return {"status": "success", "data": {"id": doc_id, "shortCode": doc["shortCode"]}}


# ---------- Fetch tools (one per table) ----------


def fetch_community_updates_tool(
    query: str = "",
    filters: Optional[dict] = None,
    limit: int = 10,
) -> dict:
    """
    Fetch community updates from Firestore. Use when the user asks for local announcements or notices.
    query: optional search text; filters: e.g. location; limit: max results (default 10, max 20).
    Returns status, results list, and count.
    """
    logger.info("fetch_community_updates_tool called query=%r limit=%s", (query or "")[:80], limit)
    results = _fetch_docs("communityUpdates", query, filters, limit)
    return {"status": "success", "results": results, "count": len(results)}


def fetch_complaints_tool(
    query: str = "",
    filters: Optional[dict] = None,
    limit: int = 10,
) -> dict:
    """
    Fetch complaints/reports from Firestore. Use when the user or admin needs to see reported items.
    query, filters, limit as in other fetch tools. Returns status, results, count.
    """
    logger.info("fetch_complaints_tool called query=%r limit=%s", (query or "")[:80], limit)
    results = _fetch_docs("complaints", query, filters, limit)
    return {"status": "success", "results": results, "count": len(results)}


def fetch_emergency_numbers_tool(
    query: str = "",
    filters: Optional[dict] = None,
    limit: int = 10,
) -> dict:
    """
    Fetch emergency and useful contact numbers from Firestore.
    Use when the user asks for police, ambulance, clinic, or other emergency numbers.
    query, filters (e.g. location, category), limit. Returns status, results, count.
    """
    logger.info("fetch_emergency_numbers_tool called query=%r limit=%s", (query or "")[:80], limit)
    results = _fetch_docs("emergencyNumbers", query, filters, limit)
    return {"status": "success", "results": results, "count": len(results)}


def fetch_events_tool(
    query: str = "",
    filters: Optional[dict] = None,
    limit: int = 10,
) -> dict:
    """
    Fetch events from Firestore. Use when the user asks what's on, or for events in an area.
    query, filters, limit. Returns status, results, count.
    """
    logger.info("fetch_events_tool called query=%r limit=%s", (query or "")[:80], limit)
    results = _fetch_docs("events", query, filters, limit)
    return {"status": "success", "results": results, "count": len(results)}


def fetch_gov_info_tool(
    query: str = "",
    filters: Optional[dict] = None,
    limit: int = 10,
) -> dict:
    """
    Fetch government/official info from Firestore. Use when the user asks for forms, deadlines, offices.
    query, filters, limit. Returns status, results, count.
    """
    logger.info("fetch_gov_info_tool called query=%r limit=%s", (query or "")[:80], limit)
    results = _fetch_docs("govInfo", query, filters, limit)
    return {"status": "success", "results": results, "count": len(results)}


def fetch_info_bits_tool(
    query: str = "",
    filters: Optional[dict] = None,
    limit: int = 10,
) -> dict:
    """
    Fetch info bits (tips, taxi prices, load-shedding notes) from Firestore.
    Use when the user asks for local tips or quick info. query, filters (e.g. location), limit.
    Each result includes verificationPrefix, upvoteInstruction (if pending), and postedAgo for display.
    Returns status, results, count.
    """
    logger.info("fetch_info_bits_tool called query=%r limit=%s", (query or "")[:80], limit)
    results = _fetch_docs("infoBits", query, filters, limit)
    results = [_format_verification_hint(r, "infoBits") for r in results]
    return {"status": "success", "results": results, "count": len(results)}


def fetch_knowledge_share_tool(
    query: str = "",
    filters: Optional[dict] = None,
    limit: int = 10,
) -> dict:
    """
    Fetch knowledge-share posts from Firestore. Use when the user asks for how-tos or advice.
    query, filters, limit. Returns status, results, count.
    """
    logger.info("fetch_knowledge_share_tool called query=%r limit=%s", (query or "")[:80], limit)
    results = _fetch_docs("knowledgeShare", query, filters, limit)
    return {"status": "success", "results": results, "count": len(results)}


def fetch_listings_tool(
    query: str = "",
    filters: Optional[dict] = None,
    limit: int = 10,
) -> dict:
    """
    Fetch marketplace listings from Firestore. Use when the user wants to search or browse listings.
    query, filters (e.g. location, type), limit. Returns status, results, count.
    Each result includes: id, title, description, location, type, tags, priceRange (optional), contact (optional), link (optional), ownerUid (creator's WhatsApp number), createdAt.
    When the user asks for contact details of a listing and the listing has no 'contact' field, you may share the listing creator's WhatsApp number (ownerUid) so they can be reached.
    """
    logger.info("fetch_listings_tool called query=%r limit=%s", (query or "")[:80], limit)
    results = _fetch_docs("listings", query, filters, limit)
    return {"status": "success", "results": results, "count": len(results)}


def fetch_lost_and_found_tool(
    query: str = "",
    filters: Optional[dict] = None,
    limit: int = 10,
) -> dict:
    """
    Fetch lost and found reports from Firestore. Use when the user asks what's been lost or found.
    query, filters (e.g. location), limit. Returns status, results, count.
    """
    logger.info("fetch_lost_and_found_tool called query=%r limit=%s", (query or "")[:80], limit)
    results = _fetch_docs("lostAndFound", query, filters, limit)
    return {"status": "success", "results": results, "count": len(results)}


def fetch_news_tool(
    query: str = "",
    filters: Optional[dict] = None,
    limit: int = 10,
) -> dict:
    """
    Fetch news items from Firestore. Use when the user asks for local news or headlines.
    query, filters, limit. Returns status, results, count.
    """
    logger.info("fetch_news_tool called query=%r limit=%s", (query or "")[:80], limit)
    results = _fetch_docs("news", query, filters, limit)
    return {"status": "success", "results": results, "count": len(results)}


def fetch_places_tool(
    query: str = "",
    filters: Optional[dict] = None,
    limit: int = 10,
) -> dict:
    """
    Fetch place-related information from both places and infoBits.
    Use when the user asks for a place, business, or where to find something (e.g. charcoal, spaza, clinic).
    Searches the places collection (structured places) and the infoBits collection (where users often post
    tips like "charcoal at X in Ezibeleni"). Each result includes sourceCollection ("places" or "infoBits");
    infoBits also include verificationPrefix, upvoteInstruction, postedAgo when relevant.
    query, filters (e.g. foundAt/location), limit. Returns status, results (merged, sorted by createdAt desc), count.
    """
    logger.info("fetch_places_tool called query=%r limit=%s", (query or "")[:80], limit)
    cap = min(int(limit), 20)
    places_results = _fetch_docs("places", query, filters, cap)
    infobits_results = _fetch_docs("infoBits", query, filters, cap)
    infobits_results = [_format_verification_hint(r, "infoBits") for r in infobits_results]
    for r in places_results:
        r["sourceCollection"] = "places"
    for r in infobits_results:
        r["sourceCollection"] = "infoBits"
    merged = places_results + infobits_results
    merged.sort(key=lambda r: _created_at_sort_key(r.get("createdAt")), reverse=True)
    merged = merged[:cap]
    return {"status": "success", "results": merged, "count": len(merged)}


def fetch_suburbs_tool(
    query: str = "",
    filters: Optional[dict] = None,
    limit: int = 10,
) -> dict:
    """
    Fetch suburbs from Firestore. Use when the user asks about areas or suburbs in a town.
    query, filters (e.g. townId), limit. Returns status, results, count.
    """
    logger.info("fetch_suburbs_tool called query=%r limit=%s", (query or "")[:80], limit)
    results = _fetch_docs("suburbs", query, filters, limit)
    return {"status": "success", "results": results, "count": len(results)}


def fetch_towns_tool(
    query: str = "",
    filters: Optional[dict] = None,
    limit: int = 10,
) -> dict:
    """
    Fetch towns from Firestore. Use when the user asks about towns (Komani, Whittlesea, etc.).
    query, filters, limit. Returns status, results, count.
    """
    logger.info("fetch_towns_tool called query=%r limit=%s", (query or "")[:80], limit)
    results = _fetch_docs("towns", query, filters, limit)
    return {"status": "success", "results": results, "count": len(results)}


def fetch_transport_fares_tool(
    query: str = "",
    filters: Optional[dict] = None,
    limit: int = 10,
) -> dict:
    """
    Fetch transport fare information from both transportFares and infoBits.
    Use when the user asks for fare from A to B or transport prices. Searches the transportFares
    collection (structured fares) and the infoBits collection (where users sometimes post fare tips).
    Each result includes verificationPrefix, upvoteInstruction (if pending), postedAgo, and
    sourceCollection ("transportFares" or "infoBits") so you can label e.g. "from fare database" vs
    "from community tips". query (e.g. place names), filters (e.g. transportType), limit.
    Returns status, results (merged and sorted by createdAt desc), count.
    """
    logger.info("fetch_transport_fares_tool called query=%r limit=%s", (query or "")[:80], limit)
    cap = min(int(limit), 20)
    transport_results = _fetch_docs("transportFares", query, filters, cap)
    infobits_results = _fetch_docs("infoBits", query, filters, cap)
    transport_results = [_format_verification_hint(r, "transportFares") for r in transport_results]
    infobits_results = [_format_verification_hint(r, "infoBits") for r in infobits_results]
    for r in transport_results:
        r["sourceCollection"] = "transportFares"
    for r in infobits_results:
        r["sourceCollection"] = "infoBits"
    merged = transport_results + infobits_results
    merged.sort(key=lambda r: _created_at_sort_key(r.get("createdAt")), reverse=True)
    merged = merged[:cap]
    return {"status": "success", "results": merged, "count": len(merged)}


# ---------- Users & userSessions (onboarding); no SCHEMAS, free-form per spec ----------
USER_ALLOWED_UPDATE_KEYS = frozenset({
    "name", "email", "town", "areaSection", "province", "languagePref",
    "primaryIntent", "watchTags", "customInfo", "onboardingComplete",
    "loansRole", "interactionsCount", "lastActiveAt",
    "diditSessionToken", "diditSessionId", "kycVerifiedAt", "kycStatus",
    "gender", "dateOfBirth", "age",
})


def _normalize_wa_number(wa_number: str) -> str:
    """Return stripped string; doc ids are waNumber."""
    if wa_number is None:
        return ""
    return str(wa_number).strip()


def get_user(wa_number: str) -> dict:
    """
    Raw function: get user doc by waNumber. Used by Python layer for one-time load and by agents.
    Returns {"exists": true, **doc} or {"exists": false}. On error returns {"exists": false, "error": "..."}.
    """
    wa = _normalize_wa_number(wa_number)
    if not wa:
        logger.warning("get_user empty wa_number")
        return {"exists": False, "error": "wa_number required"}
    logger.info("get_user wa=%s", _mask_author(wa))
    try:
        db = _get_db()
        ref = db.collection("users").document(wa)
        doc = ref.get()
        if not doc.exists:
            return {"exists": False}
        data = doc.to_dict()
        # Firestore timestamps -> ISO string for JSON in session state
        out = {"exists": True, "id": doc.id, **data}
        for key in ("createdAt", "lastActiveAt"):
            if key in out and hasattr(out[key], "isoformat"):
                out[key] = out[key].isoformat()
        return out
    except Exception as e:
        logger.exception("get_user failed: %s", e)
        return {"exists": False, "error": str(e)}


def get_user_session(wa_number: str) -> dict:
    """
    Raw function: get userSessions doc. Used by Python layer for one-time load and by agents.
    Returns {"exists": true, **doc} or {"exists": false, "onboardingStep": "new"}.
    """
    wa = _normalize_wa_number(wa_number)
    if not wa:
        logger.warning("get_user_session empty wa_number")
        return {"exists": False, "onboardingStep": "new", "error": "wa_number required"}
    logger.info("get_user_session wa=%s", _mask_author(wa))
    try:
        db = _get_db()
        ref = db.collection("userSessions").document(wa)
        doc = ref.get()
        if not doc.exists:
            return {"exists": False, "onboardingStep": "new"}
        data = doc.to_dict()
        out = {"exists": True, "id": doc.id, **data}
        if "lastActiveAt" in out and hasattr(out["lastActiveAt"], "isoformat"):
            out["lastActiveAt"] = out["lastActiveAt"].isoformat()
        return out
    except Exception as e:
        logger.exception("get_user_session failed: %s", e)
        return {"exists": False, "onboardingStep": "new", "error": str(e)}


def create_user(wa_number: str, initial_data: Optional[dict] = None) -> dict:
    """
    Create users/{wa_number}. Minimal: waNumber, createdAt, languagePref (default english).
    Optional initial_data can add name, town, areaSection, province, etc.
    Returns {"status": "success", "waNumber": "..."} or {"status": "error", "error_message": "..."}.
    Fails if doc already exists.
    """
    wa = _normalize_wa_number(wa_number)
    if not wa:
        return {"status": "error", "error_message": "wa_number required"}
    logger.info("create_user wa=%s", _mask_author(wa))
    try:
        db = _get_db()
        ref = db.collection("users").document(wa)
        if ref.get().exists:
            return {"status": "error", "error_message": "User already exists"}
        try:
            from google.cloud.firestore_v1 import SERVER_TIMESTAMP
        except ImportError:
            from google.cloud.firestore import SERVER_TIMESTAMP
        data = {
            "waNumber": wa,
            "createdAt": SERVER_TIMESTAMP,
            "languagePref": (initial_data or {}).get("languagePref", "english"),
            "kasiPoints": 0,
        }
        allowed = {"name", "email", "town", "areaSection", "province", "languagePref"}
        for k, v in (initial_data or {}).items():
            if k in allowed and v is not None:
                data[k] = v
        ref.set(data)
        logger.info("create_user success wa=%s", _mask_author(wa))
        return {"status": "success", "waNumber": wa}
    except Exception as e:
        logger.exception("create_user failed: %s", e)
        return {"status": "error", "error_message": str(e)}


def update_user(wa_number: str, updates: dict) -> dict:
    """
    Partial update on users/{wa_number}. Allowed fields: name, email, town, areaSection,
    province, languagePref, primaryIntent, watchTags, customInfo, onboardingComplete,
    interactionsCount, lastActiveAt. customInfo must be list of dicts only (no strings).
    Sets lastActiveAt to SERVER_TIMESTAMP. Returns status/error_message.
    """
    wa = _normalize_wa_number(wa_number)
    if not wa:
        return {"status": "error", "error_message": "wa_number required"}
    filtered = {k: v for k, v in updates.items() if k in USER_ALLOWED_UPDATE_KEYS}
    # Compute age from dateOfBirth when present (YYYY-MM-DD string)
    if "dateOfBirth" in filtered:
        dob_val = filtered["dateOfBirth"]
        if isinstance(dob_val, str):
            try:
                dob = datetime.strptime(dob_val.strip()[:10], "%Y-%m-%d").date()
                today = date.today()
                age_years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                filtered["age"] = max(0, age_years)
            except (ValueError, TypeError):
                logger.warning("update_user: could not parse dateOfBirth %r for age", dob_val[:20] if dob_val else None)
        elif hasattr(dob_val, "date") and callable(getattr(dob_val, "date", None)):
            dob = dob_val.date()
            try:
                today = date.today()
                age_years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                filtered["age"] = max(0, age_years)
            except (TypeError, AttributeError):
                pass
    if "customInfo" in filtered and filtered["customInfo"] is not None:
        arr = filtered["customInfo"]
        if not isinstance(arr, list):
            return {"status": "error", "error_message": "customInfo must be a list of dicts"}
        for i, item in enumerate(arr):
            if not isinstance(item, dict):
                return {"status": "error", "error_message": f"customInfo[{i}] must be a dict (key, value, addedAt, source)"}
    try:
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP
    except ImportError:
        from google.cloud.firestore import SERVER_TIMESTAMP
    filtered["lastActiveAt"] = SERVER_TIMESTAMP
    logger.info("update_user wa=%s keys=%s", _mask_author(wa), list(filtered.keys()))
    try:
        db = _get_db()
        ref = db.collection("users").document(wa)
        ref.update(filtered)
        return {"status": "success"}
    except Exception as e:
        logger.exception("update_user failed: %s", e)
        return {"status": "error", "error_message": str(e)}


def append_to_custom_info(wa_number: str, info: dict) -> dict:
    """
    Append one entry to user's customInfo. info must be dict with "key" and "value".
    addedAt (ISO8601) and source (default "user_message") are auto-added.
    customInfo is dict-only per v1.1. Returns status/error_message.
    """
    wa = _normalize_wa_number(wa_number)
    if not wa:
        return {"status": "error", "error_message": "wa_number required"}
    if not isinstance(info, dict):
        return {"status": "error", "error_message": "info must be a dict with key and value"}
    key = info.get("key")
    value = info.get("value")
    if key is None or value is None:
        return {"status": "error", "error_message": "info must include key and value"}
    from datetime import datetime, timezone
    entry = {
        "key": str(key),
        "value": str(value) if not isinstance(value, (dict, list)) else value,
        "addedAt": datetime.now(timezone.utc).isoformat(),
        "source": info.get("source", "user_message"),
    }
    logger.info("append_to_custom_info wa=%s key=%s", _mask_author(wa), key)
    try:
        db = _get_db()
        ref = db.collection("users").document(wa)
        doc = ref.get()
        if not doc.exists:
            return {"status": "error", "error_message": "User not found"}
        data = doc.to_dict()
        custom = list(data.get("customInfo") or [])
        custom.append(entry)
        try:
            from google.cloud.firestore_v1 import SERVER_TIMESTAMP
        except ImportError:
            from google.cloud.firestore import SERVER_TIMESTAMP
        ref.update({"customInfo": custom, "lastActiveAt": SERVER_TIMESTAMP})
        return {"status": "success"}
    except Exception as e:
        logger.exception("append_to_custom_info failed: %s", e)
        return {"status": "error", "error_message": str(e)}


def update_user_session(wa_number: str, updates: dict) -> dict:
    """
    Partial update on userSessions/{wa_number}; creates doc if missing.
    Allowed: onboardingStep, lastActiveAt, etc. Returns status/error_message.
    """
    wa = _normalize_wa_number(wa_number)
    if not wa:
        return {"status": "error", "error_message": "wa_number required"}
    try:
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP
    except ImportError:
        from google.cloud.firestore import SERVER_TIMESTAMP
    if "lastActiveAt" not in updates:
        updates = {**updates, "lastActiveAt": SERVER_TIMESTAMP}
    logger.info("update_user_session wa=%s keys=%s", _mask_author(wa), list(updates.keys()))
    try:
        db = _get_db()
        ref = db.collection("userSessions").document(wa)
        ref.set(updates, merge=True)
        return {"status": "success"}
    except Exception as e:
        logger.exception("update_user_session failed: %s", e)
        return {"status": "error", "error_message": str(e)}


def sync_user_to_session_state(wa_number: str) -> dict:
    """
    Return merged user + session for updating ADK session state after onboarding updates.
    Used so next message has fresh cache. Returns {userProfile, userSession} or error.
    """
    wa = _normalize_wa_number(wa_number)
    if not wa:
        return {"status": "error", "error_message": "wa_number required"}
    user_out = get_user(wa)
    session_out = get_user_session(wa)
    if not user_out.get("exists"):
        return {"status": "error", "error_message": "User not found"}
    return {
        "status": "success",
        "userProfile": user_out,
        "userSession": session_out,
    }


# ---------- Web chat persistence (chats/{wa_number}, messages subcollection) ----------
def upsert_web_chat(wa_number: str, channel: str = "web") -> dict:
    """Create or update chat doc for wa_number. Sets lastActiveAt. Used before appending messages."""
    wa = _normalize_wa_number(wa_number)
    if not wa:
        return {"status": "error", "error_message": "wa_number required"}
    try:
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP
    except ImportError:
        from google.cloud.firestore import SERVER_TIMESTAMP
    try:
        db = _get_db()
        ref = db.collection("chats").document(wa)
        ref.set(
            {
                "waNumber": wa,
                "channel": channel,
                "lastActiveAt": SERVER_TIMESTAMP,
            },
            merge=True,
        )
        doc = ref.get()
        if doc.exists and "createdAt" not in (doc.to_dict() or {}):
            ref.update({"createdAt": SERVER_TIMESTAMP})
        return {"status": "success"}
    except Exception as e:
        logger.exception("upsert_web_chat failed: %s", e)
        return {"status": "error", "error_message": str(e)}


def append_web_chat_message(
    wa_number: str,
    sender: str,
    text: str,
    metadata: Optional[dict] = None,
) -> dict:
    """Append one message to chats/{wa_number}/messages. sender is 'user' or 'bot'."""
    wa = _normalize_wa_number(wa_number)
    if not wa:
        return {"status": "error", "error_message": "wa_number required"}
    if sender not in ("user", "bot"):
        return {"status": "error", "error_message": "sender must be 'user' or 'bot'"}
    try:
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP
    except ImportError:
        from google.cloud.firestore import SERVER_TIMESTAMP
    try:
        upsert_web_chat(wa_number)
        db = _get_db()
        col = db.collection("chats").document(wa).collection("messages")
        doc_ref = col.document()
        doc_ref.set(
            {
                "sender": sender,
                "text": text,
                "timestamp": SERVER_TIMESTAMP,
                **({"metadata": metadata} if metadata else {}),
            }
        )
        return {"status": "success", "id": doc_ref.id}
    except Exception as e:
        logger.exception("append_web_chat_message failed: %s", e)
        return {"status": "error", "error_message": str(e)}


def get_web_chat_messages(wa_number: str, limit: int = 200) -> dict:
    """Return messages for chats/{wa_number}, ordered by timestamp ascending."""
    wa = _normalize_wa_number(wa_number)
    if not wa:
        return {"status": "error", "error_message": "wa_number required", "messages": []}
    try:
        from google.cloud.firestore_v1.query import Query
        _DIR_DESC = Query.DESCENDING
    except ImportError:
        _DIR_DESC = "DESCENDING"
    try:
        db = _get_db()
        ref = db.collection("chats").document(wa).collection("messages")
        docs = ref.order_by("timestamp", direction=_DIR_DESC).limit(limit).get()
        messages = []
        for doc in reversed(docs):
            d = doc.to_dict() or {}
            ts = d.get("timestamp")
            if hasattr(ts, "isoformat"):
                ts = ts.isoformat()
            messages.append(
                {
                    "id": doc.id,
                    "sender": d.get("sender", "bot"),
                    "text": d.get("text", ""),
                    "timestamp": ts,
                    "metadata": d.get("metadata"),
                }
            )
        return {"status": "success", "messages": messages}
    except Exception as e:
        logger.exception("get_web_chat_messages failed: %s", e)
        return {"status": "error", "error_message": str(e), "messages": []}


# ---------- Wrap as ADK FunctionTools (user/session tools) ----------
def get_user_tool(wa_number: str) -> dict:
    """Get user by waNumber. Returns {exists: true, **doc} or {exists: false}. Use cached userProfile from state when possible."""
    return get_user(wa_number)


def get_user_session_tool(wa_number: str) -> dict:
    """Get userSessions doc. Returns {exists: true, **doc} or {exists: false, onboardingStep: 'new'}. Use cached userSession from state when possible."""
    return get_user_session(wa_number)


def create_user_tool(wa_number: str, initial_data: Optional[dict] = None) -> dict:
    """Create user when they do not exist. Then transfer to onboarding_agent."""
    return create_user(wa_number, initial_data)


def update_user_tool(wa_number: str, updates: dict) -> dict:
    """Partial update on user profile. customInfo must be list of dicts only."""
    return update_user(wa_number, updates)


def append_to_custom_info_tool(wa_number: str, info: dict) -> dict:
    """Append one dict entry to customInfo (key, value; addedAt and source auto-added)."""
    return append_to_custom_info(wa_number, info)


def update_user_session_tool(wa_number: str, updates: dict) -> dict:
    """Update onboarding step etc. in userSessions. Creates doc if missing."""
    return update_user_session(wa_number, updates)


def sync_user_to_session_state_tool(wa_number: str) -> dict:
    """After onboarding update, call to get fresh userProfile and userSession for cache."""
    return sync_user_to_session_state(wa_number)


# ---------- Wrap as ADK FunctionTools ----------
from google.adk.tools import FunctionTool

save_community_updates_tool = FunctionTool(save_community_updates_tool)
save_complaints_tool = FunctionTool(save_complaints_tool)
save_emergency_numbers_tool = FunctionTool(save_emergency_numbers_tool)
save_events_tool = FunctionTool(save_events_tool)
save_gov_info_tool = FunctionTool(save_gov_info_tool)
save_info_bits_tool = FunctionTool(save_info_bits_tool)
save_knowledge_share_tool = FunctionTool(save_knowledge_share_tool)
save_listings_tool = FunctionTool(save_listings_tool)
save_lost_and_found_tool = FunctionTool(save_lost_and_found_tool)
save_news_tool = FunctionTool(save_news_tool)
save_places_tool = FunctionTool(save_places_tool)
save_suburbs_tool = FunctionTool(save_suburbs_tool)
save_towns_tool = FunctionTool(save_towns_tool)
save_transport_fares_tool = FunctionTool(save_transport_fares_tool)

fetch_community_updates_tool = FunctionTool(fetch_community_updates_tool)
fetch_complaints_tool = FunctionTool(fetch_complaints_tool)
fetch_emergency_numbers_tool = FunctionTool(fetch_emergency_numbers_tool)
fetch_events_tool = FunctionTool(fetch_events_tool)
fetch_gov_info_tool = FunctionTool(fetch_gov_info_tool)
fetch_info_bits_tool = FunctionTool(fetch_info_bits_tool)
fetch_knowledge_share_tool = FunctionTool(fetch_knowledge_share_tool)
fetch_listings_tool = FunctionTool(fetch_listings_tool)
fetch_lost_and_found_tool = FunctionTool(fetch_lost_and_found_tool)
fetch_news_tool = FunctionTool(fetch_news_tool)
fetch_places_tool = FunctionTool(fetch_places_tool)
fetch_suburbs_tool = FunctionTool(fetch_suburbs_tool)
fetch_towns_tool = FunctionTool(fetch_towns_tool)
fetch_transport_fares_tool = FunctionTool(fetch_transport_fares_tool)

get_user_tool = FunctionTool(get_user_tool)
get_user_session_tool = FunctionTool(get_user_session_tool)
create_user_tool = FunctionTool(create_user_tool)
update_user_tool = FunctionTool(update_user_tool)
append_to_custom_info_tool = FunctionTool(append_to_custom_info_tool)
update_user_session_tool = FunctionTool(update_user_session_tool)
sync_user_to_session_state_tool = FunctionTool(sync_user_to_session_state_tool)
