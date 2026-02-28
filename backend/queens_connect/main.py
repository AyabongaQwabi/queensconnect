"""
Queens Connect – Agent entry point (ADK).
run(wa_number, message, session_state, language_pref) -> reply string.
One-time load of user + userSession into session state (no DB call on every message).
Moderation: root agent blocks bad input; optional outbound filter replaces replies that contain prohibited terms.
"""
import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Optional

# Substrings that must not appear in outbound replies (drug/illegal terms); lowercase for check
_OUTBOUND_BANNED_SUBSTRINGS = frozenset({
    "intash", "ntash", "tik", "itik", "iganja", "intsango", "iweed", "izoli", "iwiti", "iwit",
    "umgwinyo", "inyaope", "itsufu", "tsuf", "indanda", "ipilisi", "cocaine", "heroin", "meth",
})


def _moderate_outbound(reply: str) -> str:
    """If reply contains prohibited terms, return a safe fallback; otherwise return reply."""
    if not reply:
        return reply
    lower = reply.lower()
    for term in _OUTBOUND_BANNED_SUBSTRINGS:
        if term in lower:
            return "Eish, something went wrong on our side — try again in a bit, sharp. main.py"
    return reply

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

try:
    from .tools import get_user, get_user_session, get_lender_and_borrower_profile_summaries
except ImportError:
    from tools import get_user, get_user_session, get_lender_and_borrower_profile_summaries

try:
    from .agent import get_root_agent
except ImportError:
    from agent import get_root_agent

APP_NAME = "queens_connect"


async def _run_async(
    wa_number: str,
    message: str,
    session_state: dict[str, Any],
    language_pref: str,
) -> str:
    """Run one user message through ADK Runner and return the final reply text."""
    session_service = InMemorySessionService()
    session_id = f"wa_{wa_number}"
    # One-time load: user + userSession + lender/borrower for gatekeeper/onboarding
    user_doc = get_user(wa_number)
    session_doc = get_user_session(wa_number)
    profiles = get_lender_and_borrower_profile_summaries(wa_number)
    initial_state = {
        "currentDate": datetime.now(timezone.utc).isoformat(),
        "waNumber": wa_number,
        "languagePref": language_pref,
        "currentState": json.dumps(session_state, default=str) if isinstance(session_state, dict) else str(session_state),
        "userProfile": json.dumps(user_doc, default=str),
        "userSession": json.dumps(session_doc, default=str),
        "lenderOrBorrowerSummary": json.dumps(profiles.get("lenderOrBorrowerSummary") or {}, default=str),
        "lenderProfile": json.dumps(profiles.get("lenderProfile"), default=str) if profiles.get("lenderProfile") is not None else "null",
        "borrowerProfile": json.dumps(profiles.get("borrowerProfile"), default=str) if profiles.get("borrowerProfile") is not None else "null",
    }
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=wa_number,
        session_id=session_id,
        state=initial_state,
    )

    root_agent = get_root_agent()
    runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)

    content = types.Content(role="user", parts=[types.Part(text=message)])
    reply_text = ""
    async for event in runner.run_async(
        user_id=wa_number,
        session_id=session_id,
        new_message=content,
    ):
        if getattr(event, "is_final_response", lambda: False)():
            if getattr(event, "content", None) and getattr(event.content, "parts", None):
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        reply_text += part.text or ""
    reply_text = reply_text.strip() or "We apologise for the inconvenience. We are experiencing technical difficulties. Please try again in a few minutes."
    reply_text = _moderate_outbound(reply_text)
    return reply_text


def run(
    wa_number: str,
    message: str,
    session_state: Optional[dict[str, Any]] = None,
    language_pref: str = "xhosa",
) -> str:
    """
    Process one user message and return the reply string for WhatsApp.
    Uses ADK Runner + InMemorySessionService; state is seeded for orchestrator instruction.
    """
    return asyncio.run(_run_async(
        wa_number=wa_number,
        message=message,
        session_state=session_state or {},
        language_pref=language_pref,
    ))


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python main.py <wa_number> <message>")
        sys.exit(1)
    wa = sys.argv[1]
    msg = " ".join(sys.argv[2:])
    print("--------------------------------")
    
    print(wa)
    print(msg)
    print(run(wa_number=wa, message=msg))
