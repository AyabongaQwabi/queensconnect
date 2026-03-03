"""Gamification sub-agent: Kasi Points balance, redeem voucher (A/B/C), upvote by shortCode."""
from pathlib import Path

from google.adk.agents import LlmAgent

from ... import config
from ...tools import (
    check_balance_tool,
    get_voucher_stock_tool,
    record_upvote_tool,
    redeem_voucher_tool,
)


def _load_instruction() -> str:
    path = config.REPO_ROOT / "docs" / "prompts" / "gamification-agent.md"
    if path.exists():
        text = path.read_text(encoding="utf-8")
        text = text.replace("{waNumber}", "{waNumber?}").replace("{currentDate}", "{currentDate?}")
        # Escape literal placeholder so ADK does not treat it as a context variable
        text = text.replace("{code}", "[voucher code from redeem_voucher_tool result]")
        return text
    return _default_instruction()


def _default_instruction() -> str:
    return """You are the Kasi Points agent. When the user says "points" or "redeem", call check_balance_tool(wa_number) and show balance + menu: 1. Points history 2. Redeem voucher 3. Back. When they say "2", call get_voucher_stock_tool() and show tiers A/B/C with stock. When they reply A, B or C, call redeem_voucher_tool(wa_number, tier). When they say "upvote <CODE>", call record_upvote_tool(wa_number, short_code). Reply warm and short in Markdown. Output only the final reply."""


gamification_agent = LlmAgent(
    name="gamification_agent",
    model=config.get_sub_agent_model(),
    description="Kasi Points: check balance, redeem vouchers (A/B/C), or record upvote by short code (e.g. upvote ABC123).",
    instruction=_load_instruction(),
    tools=[
        check_balance_tool,
        get_voucher_stock_tool,
        record_upvote_tool,
        redeem_voucher_tool,
    ],
    sub_agents=[],
)
