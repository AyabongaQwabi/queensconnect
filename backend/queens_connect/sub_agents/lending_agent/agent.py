"""Lending agent: full Lending & Borrowing flows for borrowers and lenders."""
from pathlib import Path

from google.adk.agents import LlmAgent

from ... import config
from ...tools import (
    get_lender_or_borrower_tool,
    create_loan_request_tool,
    fetch_loan_requests_tool,
    fetch_unpaid_loans_tool,
    create_unlock_payment_link_tool,
    check_unlock_payment_status_tool,
    get_unlocked_request_details_tool,
    accept_loan_request_tool,
    update_lender_repayment_details_tool,
    create_repayment_payment_link_tool,
    check_repayment_payment_status_tool,
    get_my_lending_stats_tool,
    record_proof_of_payment_tool,
)


def _load_instruction() -> str:
    """
    Load the lending_agent system prompt.

    We keep placeholders {currentDate}, {waNumber}, {languagePref} consistent with other agents
    and replace them with the ADK-style {currentDate?} etc. that the runtime fills in.
    """
    path: Path = getattr(config, "LENDING_AGENT_PROMPT_PATH", None) or (
        config.REPO_ROOT / "docs" / "prompts" / "lending-agent.md"
    )
    if not path.exists():
        # Fallback: minimal description if prompt file is missing.
        return (
            "You are the Queens Connect Lending & Borrowing agent. "
            "Help borrowers post loan requests and help lenders browse, unlock and accept those requests. "
            "Always call tools to read/write Firestore (loan_requests, loans, lender_views). "
            "Call get_lender_or_borrower_tool first; if needsRegistration is true, "
            "transfer_to_agent('loans_registration_agent'). Output only the final WhatsApp reply."
        )
    text = path.read_text(encoding="utf-8")
    text = text.replace("{currentDate}", "{currentDate?}").replace("{waNumber}", "{waNumber?}")
    text = text.replace("{languagePref}", "{languagePref?}")
    return text


lending_agent = LlmAgent(
    name="lending_agent",
    model=config.get_sub_agent_model(),
    description="Handles full Lending & Borrowing flows: loan_requests browsing/unlocking, loan creation, and proof-of-payment.",
    instruction=_load_instruction(),
    tools=[
        get_lender_or_borrower_tool,
        create_loan_request_tool,
        fetch_loan_requests_tool,
        fetch_unpaid_loans_tool,
        create_unlock_payment_link_tool,
        check_unlock_payment_status_tool,
        get_unlocked_request_details_tool,
        accept_loan_request_tool,
        update_lender_repayment_details_tool,
        create_repayment_payment_link_tool,
        check_repayment_payment_status_tool,
        get_my_lending_stats_tool,
        record_proof_of_payment_tool,
    ],
    sub_agents=[],  # loans_registration_agent is already sub_agent of loans_agent; ADK allows only one parent
)

