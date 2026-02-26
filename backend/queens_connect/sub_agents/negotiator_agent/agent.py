"""Negotiator sub-agent: middleman negotiation with consent; history visible to both parties."""
import sys
from pathlib import Path

_qc = Path(__file__).resolve().parent.parent.parent
if str(_qc) not in sys.path:
    sys.path.insert(0, str(_qc))

from google.adk.agents import LlmAgent
from tools import fetch_listings_tool, fetch_info_bits_tool, save_info_bits_tool

try:
    from ...config import get_sub_agent_model
except ImportError:
    from config import get_sub_agent_model

negotiator_agent = LlmAgent(
    name="negotiator",
    model=get_sub_agent_model(),
    description="Middleman negotiation with consent. Keeps history visible to both parties.",
    instruction="""You are the Negotiator. Handle middleman negotiation: get explicit consent before sharing offers. Use fetch_listings_tool and fetch_info_bits_tool to get listing/party info; use save_info_bits_tool for negotiation notes/threads if needed (text, tags). Never expose numbers without double consent. After ~5 messages with no agreement, suggest middle ground or direct connect. Reply short. Reply in Markdown (use **bold** for emphasis, lists where helpful). Output only the reply to the user.""",
    tools=[fetch_listings_tool, fetch_info_bits_tool, save_info_bits_tool],
)
