"""Matcher sub-agent: general search on listings, infoBits, transport fares; matches user intent."""
import sys
from pathlib import Path

_qc = Path(__file__).resolve().parent.parent.parent
if str(_qc) not in sys.path:
    sys.path.insert(0, str(_qc))

from google.adk.agents import LlmAgent
from tools import fetch_listings_tool, fetch_info_bits_tool, fetch_transport_fares_tool

try:
    from ...config import get_sub_agent_model
except ImportError:
    from config import get_sub_agent_model

matcher_agent = LlmAgent(
    name="matcher",
    model=get_sub_agent_model(),
    description="General search: listings, infoBits, transport fares. Matches user intent to results.",
    instruction="""You are the Matcher. Use fetch_listings_tool and fetch_info_bits_tool for listings and tips. For taxi/fare queries (e.g. "taxi to Joburg price", "fare to East London") use fetch_transport_fares_tool — it returns results from both the fare database and community tips; each result has sourceCollection. Return max 3 results, short previews. When showing fetch_info_bits_tool or fetch_transport_fares_tool results: use each result's verificationPrefix and upvoteInstruction; show at most 2 pending items first (with the upvote CTA each), then verified. When the user asks for contact details of a listing and the listing has no contact field, share the creator's WhatsApp number (ownerUid from the listing). Reply in kasi style. Reply in Markdown (use **bold** for emphasis, lists where helpful). Output only the reply to the user.""",
    tools=[fetch_listings_tool, fetch_info_bits_tool, fetch_transport_fares_tool],
)
