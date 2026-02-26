"""Payment sub-agent: Ikhokha links, wallet balance; only after clear user confirmation."""
import sys
from pathlib import Path

_qc = Path(__file__).resolve().parent.parent.parent
if str(_qc) not in sys.path:
    sys.path.insert(0, str(_qc))

from google.adk.agents import LlmAgent
from tools import fetch_listings_tool, fetch_info_bits_tool

try:
    from ...config import get_sub_agent_model
except ImportError:
    from config import get_sub_agent_model

payment_agent = LlmAgent(
    name="payment_agent",
    model=get_sub_agent_model(),
    description="Ikhokha payment links, wallet balance. Only after clear user confirmation.",
    instruction="""You are the Payment agent. Only create payment links after explicit confirmation (e.g. "You sure you want to send R50 to Sipho? Reply YES to get the link."). Use fetch_listings_tool or fetch_info_bits_tool to look up listing/context when needed. Never create payment without confirmation. Reply short. Reply in Markdown (use **bold** for emphasis, lists where helpful). Output only the reply to the user.""",
    tools=[fetch_listings_tool, fetch_info_bits_tool],
)
