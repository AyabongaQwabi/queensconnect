"""Lost & Found sub-agent: report/match lost or found items."""
import sys
from pathlib import Path

_qc = Path(__file__).resolve().parent.parent.parent
if str(_qc) not in sys.path:
    sys.path.insert(0, str(_qc))

from google.adk.agents import LlmAgent
from tools import fetch_lost_and_found_tool, save_lost_and_found_tool

try:
    from ...config import get_sub_agent_model
except ImportError:
    from config import get_sub_agent_model

lost_found_agent = LlmAgent(
    name="lost_found",
    model=get_sub_agent_model(),
    description="Specialised lost & found (phones, puppies, IDs, wallets). Matches lost vs found items.",
    instruction="""You are the Lost & Found agent. Help users report lost or found items. Use save_lost_and_found_tool to add reports (text, location, type 'lost' or 'found', tags; optional photoUrl, link). Use fetch_lost_and_found_tool to match lost vs found when possible. Reply short, warm. Reply in Markdown (use **bold** for emphasis, lists where helpful). Output only the reply to the user.""",
    tools=[fetch_lost_and_found_tool, save_lost_and_found_tool],
)
