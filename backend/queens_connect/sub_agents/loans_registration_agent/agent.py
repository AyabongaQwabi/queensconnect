"""Loans registration sub-agent: Small Loans Program explanation, KYC via Didit.me, create lender/borrower profile."""
from pathlib import Path

from google.adk.agents import LlmAgent

from ... import config
from ...tools import (
    get_lender_or_borrower_tool,
    create_verification_link_tool,
    check_verification_result_tool,
    create_lender_profile_tool,
    create_borrower_profile_tool,
    update_borrower_verified_tool,
)


def _load_instruction() -> str:
    path = getattr(config, "LOANS_REGISTRATION_AGENT_PROMPT_PATH", None) or (
        config.REPO_ROOT / "docs" / "prompts" / "loans-registration-agent.md"
    )
    if not path.exists():
        return (
            "You are the Queens Connect Loans Registration agent. Explain the Small Loans Program, "
            "collect full name, SA ID (13 digits), and address. Call create_verification_link_tool, then when user says DONE call check_verification_result_tool. "
            "On success call create_lender_profile_tool or create_borrower_profile_tool and transfer_to_agent('loans_agent'). Warm kasi tone. Output only the reply."
        )
    text = path.read_text(encoding="utf-8")
    text = text.replace("{currentDate}", "{currentDate?}").replace("{waNumber}", "{waNumber?}")
    text = text.replace("{languagePref}", "{languagePref?}")
    return text


loans_registration_agent = LlmAgent(
    name="loans_registration_agent",
    model=config.get_sub_agent_model(),
    description="Explains Small Loans Program, runs KYC via Didit.me, creates lender or borrower profile. Transfer back to loans_agent on success.",
    instruction=_load_instruction(),
    tools=[
        get_lender_or_borrower_tool,
        create_verification_link_tool,
        check_verification_result_tool,
        create_lender_profile_tool,
        create_borrower_profile_tool,
        update_borrower_verified_tool,
    ],
)
