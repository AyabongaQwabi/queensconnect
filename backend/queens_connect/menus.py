"""
Menu registry for interactive WhatsApp Content Templates.

Maps (agent_name, session state) to a Twilio Content SID and variables.
Used by the Twilio webhook to send quick-reply buttons when appropriate.
"""

from __future__ import annotations

from typing import Any

try:
    from .config import (
        ONBOARDING_COMPLETE_STEP,
        TWILIO_CONTENT_LOANS_MENU,
        TWILIO_CONTENT_MAIN_MENU,
        TWILIO_CONTENT_ONBOARDING_GENDER,
        TWILIO_CONTENT_ONBOARDING_INTENT,
        TWILIO_CONTENT_ONBOARDING_OPTIONAL_DETAILS,
        TWILIO_CONTENT_STOKVEL_MENU,
    )
except ImportError:
    from config import (
        ONBOARDING_COMPLETE_STEP,
        TWILIO_CONTENT_LOANS_MENU,
        TWILIO_CONTENT_MAIN_MENU,
        TWILIO_CONTENT_ONBOARDING_GENDER,
        TWILIO_CONTENT_ONBOARDING_INTENT,
        TWILIO_CONTENT_ONBOARDING_OPTIONAL_DETAILS,
        TWILIO_CONTENT_STOKVEL_MENU,
    )


def get_buttons_for_context(agent_name: str | None, state: dict[str, Any]) -> dict[str, Any] | None:
    """
    Return Content template to send for this context, or None for plain text.

    state should include:
      - userSession: dict with onboardingStep, optionally resumeFor
      - userProfile: dict with name, onboardingComplete, etc.

    Returns:
      None — no buttons; send plain text.
      {"content_sid": "HX...", "content_variables": {"1": "..."}} — send this Content template.
    """
    if not state:
        return None

    session = state.get("userSession") or {}
    profile = state.get("userProfile") or {}
    step = (session.get("onboardingStep") or "").strip()
    name = (profile.get("name") or "there").strip() or "there"
    onboarding_complete = profile.get("onboardingComplete") is True or step == ONBOARDING_COMPLETE_STEP

    # Onboarding: step-based menus
    if not onboarding_complete:
        if step == "asked_intent" and TWILIO_CONTENT_ONBOARDING_INTENT:
            return {"content_sid": TWILIO_CONTENT_ONBOARDING_INTENT, "content_variables": {"1": name}}
        if step == "asked_optional_details" and TWILIO_CONTENT_ONBOARDING_OPTIONAL_DETAILS:
            return {"content_sid": TWILIO_CONTENT_ONBOARDING_OPTIONAL_DETAILS, "content_variables": {"1": name}}
        if step == "asked_gender" and TWILIO_CONTENT_ONBOARDING_GENDER:
            return {"content_sid": TWILIO_CONTENT_ONBOARDING_GENDER, "content_variables": {"1": name}}
        return None

    # Post-onboarding: main menu or sub-agent menu
    if agent_name == "loans_agent" and TWILIO_CONTENT_LOANS_MENU:
        return {"content_sid": TWILIO_CONTENT_LOANS_MENU, "content_variables": {"1": name}}
    if agent_name == "stokvel_agent" and TWILIO_CONTENT_STOKVEL_MENU:
        return {"content_sid": TWILIO_CONTENT_STOKVEL_MENU, "content_variables": {"1": name}}

    # Core / gatekeeper / no clear sub-agent: main menu
    if TWILIO_CONTENT_MAIN_MENU:
        return {"content_sid": TWILIO_CONTENT_MAIN_MENU, "content_variables": {"1": name}}

    return None
