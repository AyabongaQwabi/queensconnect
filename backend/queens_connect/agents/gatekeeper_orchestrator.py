"""Gatekeeper: slim root agent. Uses cached userProfile/userSession; transfers to onboarding_agent or core_orchestrator."""
from pathlib import Path

from google.adk.agents import Agent

from .. import config
from ..tools import (
    get_user_tool,
    get_user_session_tool,
    create_user_tool,
    get_lender_or_borrower_tool,
    update_user_session_tool,
)
from ..sub_agents.onboarding_agent import onboarding_agent
from .core_orchestrator import core_orchestrator


def _load_gatekeeper_instruction() -> str:
    path = getattr(config, "GATEKEEPER_PROMPT_PATH", None) or (
        config.REPO_ROOT / "docs" / "prompts" / "gatekeeper-system-prompt.md"
    )
    if not path.exists():
        return (
            "You are the gatekeeper. Use cached {userProfile?} and {userSession?}. "
            "If no user or onboarding not complete, transfer to onboarding_agent. "
            "Else transfer to core_orchestrator. Use get_user_tool/create_user_tool only when cache missing."
        )
    text = path.read_text(encoding="utf-8")
    text = text.replace("{currentDate}", "{currentDate?}").replace("{waNumber}", "{waNumber?}")
    text = text.replace("{userProfile}", "{userProfile?}").replace("{userSession}", "{userSession?}")
    text = text.replace("{lenderOrBorrowerSummary}", "{lenderOrBorrowerSummary?}")
    return text


def get_gatekeeper_agent() -> Agent:
    """Build the root gatekeeper agent (slim; routes to onboarding or core)."""
    return Agent(
        name="gatekeeper_orchestrator",
        model=config.GEMINI_MODEL,
        description="Root gatekeeper: checks cached user/session state, transfers to onboarding_agent or core_orchestrator.",
        instruction=_load_gatekeeper_instruction(),
        tools=[
            get_user_tool,
            get_user_session_tool,
            create_user_tool,
            get_lender_or_borrower_tool,
            update_user_session_tool,
        ],
        sub_agents=[onboarding_agent, core_orchestrator],
    )
