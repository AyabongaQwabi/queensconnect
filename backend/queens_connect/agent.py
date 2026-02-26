"""
Queens Connect – Root agent (ADK). Returns moderation as root; moderation blocks bad input or transfers to gatekeeper.
Gatekeeper routes to onboarding_agent or core_orchestrator. Session state includes userProfile and userSession (one-time load in Python).
"""
from google.adk.agents import Agent

from .agents import get_moderation_agent


def get_root_agent() -> Agent:
    """Build the root agent (moderation). Moderation blocks foul/illegal/drug content or transfers to gatekeeper."""
    return get_moderation_agent()