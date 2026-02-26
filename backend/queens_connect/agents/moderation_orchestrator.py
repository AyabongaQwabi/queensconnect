"""Moderation: root agent. Checks incoming messages for foul language, illegal requests, drug mentions; blocks with professional reply or transfers to gatekeeper."""
from pathlib import Path

from google.adk.agents import Agent

from .. import config
from .gatekeeper_orchestrator import get_gatekeeper_agent


def _load_moderation_instruction() -> str:
    path = getattr(config, "MODERATION_PROMPT_PATH", None) or (
        config.REPO_ROOT / "docs" / "prompts" / "moderation-system-prompt.md"
    )
    if not path.exists():
        return (
            "You are the moderation layer. Block messages that contain foul language, "
            "illegal requests, or drug mentions. Reply with a short professional moderator "
            "message and do not transfer. If the message is clean, transfer_to_agent('gatekeeper_orchestrator')."
        )
    text = path.read_text(encoding="utf-8")
    text = text.replace("{currentDate}", "{currentDate?}").replace("{waNumber}", "{waNumber?}")
    return text


def get_moderation_agent() -> Agent:
    """Build the root moderation agent. Blocks bad input; otherwise transfers to gatekeeper."""
    return Agent(
        name="moderation_orchestrator",
        model=config.GEMINI_MODEL,
        description="Root moderator: blocks foul language, illegal requests, drug mentions; otherwise transfers to gatekeeper.",
        instruction=_load_moderation_instruction(),
        tools=[],
        sub_agents=[get_gatekeeper_agent()],
    )
