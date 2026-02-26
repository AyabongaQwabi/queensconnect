"""Loans agent: entry point for lending. Routes to loans_registration_agent when user has no lender/borrower profile."""
from pathlib import Path

from google.adk.agents import LlmAgent

from ... import config
from ...tools import get_lender_or_borrower_tool
from ..loans_registration_agent.agent import loans_registration_agent


def _load_instruction() -> str:
    path = getattr(config, "LOANS_AGENT_PROMPT_PATH", None) or (
        config.REPO_ROOT / "docs" / "prompts" / "loans-agent.md"
    )
    if not path.exists():
        return (
            "You are the Queens Connect Loans agent. Call get_lender_or_borrower_tool(wa_number). "
            "If needsRegistration is true, transfer_to_agent('loans_registration_agent'). "
            "Otherwise reply that they're already in the program. Warm kasi tone. Output only the reply."
        )
    text = path.read_text(encoding="utf-8")
    text = text.replace("{currentDate}", "{currentDate?}").replace("{waNumber}", "{waNumber?}")
    text = text.replace("{languagePref}", "{languagePref?}")
    return text


loans_agent = LlmAgent(
    name="loans_agent",
    model=config.get_sub_agent_model(),
    description="Entry point for lending. Checks lender/borrower profile; transfers to loans_registration_agent if needed.",
    instruction=_load_instruction(),
    tools=[get_lender_or_borrower_tool],
    sub_agents=[loans_registration_agent],
)
