"""InfoBit Tagger sub-agent: extract text, tags, location, expiresAt from raw input."""
import sys
from pathlib import Path

_qc = Path(__file__).resolve().parent.parent.parent
if str(_qc) not in sys.path:
    sys.path.insert(0, str(_qc))

from google.adk.agents import LlmAgent
from tools import fetch_info_bits_tool, save_info_bits_tool

try:
    from ...config import get_sub_agent_model
except ImportError:
    from config import get_sub_agent_model

infobit_tagger_agent = LlmAgent(
    name="infobit_tagger",
    model=get_sub_agent_model(),
    description="Takes raw text/voice note → extracts clean text + auto-tags (lowercase English) + location + expiresAt.",
    instruction="""You are the InfoBit Tagger. From user input extract: clean text, tags (lowercase English only), location, and optional expiresHours (e.g. 4 for temporary). Use fetch_info_bits_tool to search and save_info_bits_tool to post. Required: text, tags; optional: location, expiresHours, link. Reply short and warm. Reply in Markdown (use **bold** for emphasis, lists where helpful). Output only the reply to the user.""",
    tools=[fetch_info_bits_tool, save_info_bits_tool],
)
