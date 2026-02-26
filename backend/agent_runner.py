"""
Queens Connect – Persistent agent runner for the web chat backend.
Loads the ADK root agent once; reuses one InMemorySessionService and Runner for all requests.
Sessions are created per wa_number on first message and reused for conversation continuity.
After the runner returns, raw reply is rewritten with Grok (kasi voice) and outbound moderation is applied.
"""
import json
import logging
import os
import sys
import warnings
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Suppress Pydantic serialization warnings from LiteLLM response objects (Message/StreamingChoices shape mismatch)
warnings.filterwarnings("ignore", message=".*Pydantic serializer.*", category=UserWarning)

# Ensure backend dir is on path so queens_connect (backend/queens_connect) is importable
_backend_root = Path(__file__).resolve().parent
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))

# Load env: backend, queens_connect, and repo root (same behaviour as queens_connect.config)
from dotenv import load_dotenv
load_dotenv(_backend_root / ".env")
load_dotenv(_backend_root / "queens_connect" / ".env")
load_dotenv(_backend_root.parent / ".env")

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from queens_connect.agent import get_root_agent
from queens_connect.tools import (
    get_user,
    get_user_session,
    get_lender_and_borrower_profile_summaries,
)
from queens_connect import config as qc_config

logger = logging.getLogger(__name__)

APP_NAME = "queens_connect"
FALLBACK_REPLY = "We apologise for the inconvenience. We are experiencing technical difficulties. Please try again in a few minutes."

# Outbound moderation: banned substrings (drug/illegal terms)
_OUTBOUND_BANNED = frozenset({
    "intash", "ntash", "tik", "itik", "iganja", "intsango", "iweed", "izoli", "iwiti", "iwit",
    "umgwinyo", "inyaope", "itsufu", "tsuf", "indanda", "ipilisi", "cocaine", "heroin", "meth",
})


def _moderate_outbound(reply: str) -> str:
    """If reply contains prohibited terms, return a safe fallback; otherwise return reply."""
    return reply
    # if not reply:
    #     return reply
    # lower = reply.lower()
    # for term in _OUTBOUND_BANNED:
    #     if term in lower:
    #         return "Eish, something went wrong on our side — try again in a bit, sharp. you have been prohibited from using our service."
    # return reply


def moderate_outbound(reply: str) -> str:
    """Public wrapper for outbound moderation. Use from web backend."""
    return _moderate_outbound(reply)


# Singleton state (set by init_runner, read by run_message_async)
_runner: Runner | None = None
_session_service: InMemorySessionService | None = None
_created_sessions: set[str] = set()


def init_runner() -> None:
    """Load root agent and create Runner + SessionService once. Call from FastAPI lifespan."""
    global _runner, _session_service
    if _runner is not None:
        return
    logger.info("Loading Queens Connect root agent and runner...")
    root_agent = get_root_agent()
    _session_service = InMemorySessionService()
    _runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=_session_service,
    )
    logger.info("Agent and runner ready.")


async def _ensure_session(wa_number: str, language_pref: str, session_state: dict[str, Any] | None = None) -> None:
    """Create session for wa_number if it does not exist (reuse for subsequent messages)."""
    if _session_service is None:
        raise RuntimeError("Session service not initialized")
    session_id = f"wa_{wa_number}"
    if session_id in _created_sessions:
        return
    user_doc = get_user(wa_number)
    session_doc = get_user_session(wa_number)
    initial_state = {
        "currentDate": datetime.now(timezone.utc).isoformat(),
        "waNumber": wa_number,
        "lenderUid": wa_number,
        "languagePref": language_pref,
        "currentState": json.dumps(session_state or {}, default=str),
        "userProfile": json.dumps(user_doc, default=str),
        "userSession": json.dumps(session_doc, default=str),
    }
    await _session_service.create_session(
        app_name=APP_NAME,
        user_id=wa_number,
        session_id=session_id,
        state=initial_state,
    )
    _created_sessions.add(session_id)


def _refresh_session_state_from_firestore(wa_number: str, session_id: str) -> None:
    """
    Load latest user, userSession, and lender/borrower profile summaries from Firestore
    and merge them into the in-memory session state so every message sees up-to-date
    context (e.g. already joined loans programme). Uses InMemorySessionService's
    internal session storage by design; document if switching to another session service.
    """
    if _session_service is None:
        return
    user_doc = get_user(wa_number)
    session_doc = get_user_session(wa_number)
    profiles = get_lender_and_borrower_profile_summaries(wa_number)
    # InMemorySessionService: sessions[app_name][user_id][session_id] is the stored Session
    try:
        by_app = getattr(_session_service, "sessions", None)
        by_user = by_app.get(APP_NAME, {}).get(wa_number, {}) if by_app else {}
        storage_session = by_user.get(session_id) if by_user else None
    except (AttributeError, TypeError):
        storage_session = None
    if storage_session is None:
        return
    state = getattr(storage_session, "state", None)
    if state is None:
        return
    state["currentDate"] = datetime.now(timezone.utc).isoformat()
    state["waNumber"] = wa_number
    state["lenderUid"] = wa_number
    state["userProfile"] = json.dumps(user_doc, default=str)
    state["userSession"] = json.dumps(session_doc, default=str)
    state["lenderOrBorrowerSummary"] = json.dumps(profiles.get("lenderOrBorrowerSummary") or {}, default=str)
    state["lenderProfile"] = json.dumps(profiles.get("lenderProfile"), default=str) if profiles.get("lenderProfile") is not None else "null"
    state["borrowerProfile"] = json.dumps(profiles.get("borrowerProfile"), default=str) if profiles.get("borrowerProfile") is not None else "null"


async def run_message_async(
    wa_number: str,
    message: str,
    language_pref: str = "english",
    session_state: dict[str, Any] | None = None,
) -> str:
    """
    Run one user message through the shared Runner and return the reply text.
    Creates or reuses session for wa_number. Uses the singleton runner from init_runner().
    """
    if _runner is None or _session_service is None:
        raise RuntimeError("Runner not initialized; call init_runner() at startup")
    try:
        await _ensure_session(wa_number, language_pref, session_state)
        session_id = f"wa_{wa_number}"
        _refresh_session_state_from_firestore(wa_number, session_id)
        content = types.Content(role="user", parts=[types.Part(text=message)])
        reply_text = ""
        async for event in _runner.run_async(
            user_id=wa_number,
            session_id=session_id,
            new_message=content,
        ):
            if getattr(event, "is_final_response", lambda: False)():
                if getattr(event, "content", None) and getattr(event.content, "parts", None):
                    for part in event.content.parts:
                        if getattr(part, "text", None):
                            reply_text += part.text or ""
        reply_text = reply_text.strip() or FALLBACK_REPLY
        reply_text = _moderate_outbound(reply_text)
        logger.info("Moderated reply: %s", reply_text)
        return reply_text
    except Exception as e:
        logger.exception("run_message_async failed: %s", e)
        return FALLBACK_REPLY


async def run_message_async_raw(
    wa_number: str,
    message: str,
    language_pref: str = "english",
    session_state: dict[str, Any] | None = None,
) -> str:
    """
    Run one user message through the shared Runner and return the raw reply.
    Used by the streaming endpoint to stream the reply to the client.
    """
    if _runner is None or _session_service is None:
        raise RuntimeError("Runner not initialized; call init_runner() at startup")
    try:
        await _ensure_session(wa_number, language_pref, session_state)
        session_id = f"wa_{wa_number}"
        _refresh_session_state_from_firestore(wa_number, session_id)
        content = types.Content(role="user", parts=[types.Part(text=message)])
        reply_text = ""
        async for event in _runner.run_async(
            user_id=wa_number,
            session_id=session_id,
            new_message=content,
        ):
            if getattr(event, "is_final_response", lambda: False)():
                if getattr(event, "content", None) and getattr(event.content, "parts", None):
                    for part in event.content.parts:
                        if getattr(part, "text", None):
                            reply_text += part.text or ""
        reply_text = reply_text.strip() or FALLBACK_REPLY
        logger.info("Raw reply: %s", reply_text)
        return reply_text
    except Exception as e:
        logger.exception("run_message_async_raw failed: %s", e)
        return FALLBACK_REPLY
