"""Web Search Fallback sub-agent: when local search returns nothing."""
import sys
from pathlib import Path

_qc = Path(__file__).resolve().parent.parent.parent
if str(_qc) not in sys.path:
    sys.path.insert(0, str(_qc))

from google.adk.agents import LlmAgent
from tools import translate_tool

try:
    from ...config import get_sub_agent_model
except ImportError:
    from config import get_sub_agent_model

web_search_fallback_agent = LlmAgent(
    name="web_search_fallback",
    model=get_sub_agent_model(),
    description="Only when local search returns nothing. Web search outside Komani.",
    instruction="""You are the Web Search Fallback. Only when local data isn't enough, use google_search and translate_tool. Say something like "Eish, let me check outside Komani quick..." then give a short answer. Reply in Markdown (use **bold** for emphasis, lists where helpful). Output only the reply to the user.""",
    tools=[translate_tool],
)
