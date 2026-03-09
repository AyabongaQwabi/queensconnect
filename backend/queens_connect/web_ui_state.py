"""
State-to-interactive UI spec for the web frontend (Option A).

Maps session state (e.g. onboardingStep) to an optional interactive spec
(dropdown, radio, buttons) so the frontend can render forms/buttons.
Used only for web /chat responses; WhatsApp webhook stays text-only.
"""

from __future__ import annotations

from typing import Any

try:
    from .config import ONBOARDING_COMPLETE_STEP
except ImportError:
    from config import ONBOARDING_COMPLETE_STEP


def get_interactive_for_web(state: dict[str, Any]) -> dict[str, Any] | None:
    """
    Return an interactive UI spec for the web channel, or None.

    state should include:
      - userSession: dict with onboardingStep, etc.
      - userProfile: dict with name, onboardingComplete, etc.

    Returns a spec suitable for the frontend, e.g.:
      {"type": "dropdown", "name": "gender", "label": "Gender",
       "options": [{"value": "male", "label": "Male"}, ...], "submitLabel": "Continue"}
    """
    if not state:
        return None

    session = state.get("userSession") or {}
    profile = state.get("userProfile") or {}
    step = (session.get("onboardingStep") or "").strip()
    onboarding_complete = profile.get("onboardingComplete") is True or step == ONBOARDING_COMPLETE_STEP

    # Onboarding steps: show matching control
    if not onboarding_complete:
        if step == "asked_gender":
            return {
                "type": "dropdown",
                "name": "gender",
                "label": "Gender",
                "options": [
                    {"value": "male", "label": "Male"},
                    {"value": "female", "label": "Female"},
                ],
                "submitLabel": "Continue",
            }
        if step == "asked_intent":
            return {
                "type": "buttons",
                "name": "intent",
                "label": "What do you want to do?",
                "options": [
                    {"value": "Get a loan", "label": "Get a loan"},
                    {"value": "Open loan business", "label": "Open loan business"},
                    {"value": "Create a stokvel", "label": "Create a stokvel"},
                    {"value": "Join a stokvel", "label": "Join a stokvel"},
                    {"value": "Sell or buy", "label": "Sell or buy"},
                    {"value": "Find a cab", "label": "Find a cab"},
                    {"value": "Other", "label": "Other"},
                ],
                "submitLabel": None,
            }
        if step == "asked_optional_details":
            return {
                "type": "buttons",
                "name": "optional_details",
                "label": "Add gender and birthday?",
                "options": [
                    {"value": "Skip", "label": "Skip"},
                    {"value": "Add details", "label": "Add details"},
                ],
                "submitLabel": None,
            }
        return None

    # Do NOT show interactive for post-onboarding. Interactive is only for steps where
    # the user must pick from a fixed set (asked_gender, asked_intent, asked_optional_details).
    # When the agent is e.g. asking "how much do you want to borrow?", we must not show
    # a main menu — so we never return main_menu from state here.
    return None
