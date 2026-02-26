"""Event sub-agent: community events, funerals, church, stokvels, sports."""
import sys
from pathlib import Path

_qc = Path(__file__).resolve().parent.parent.parent
if str(_qc) not in sys.path:
    sys.path.insert(0, str(_qc))

from google.adk.agents import LlmAgent
from tools import fetch_events_tool, fetch_news_tool, save_events_tool, browser_tool

try:
    from ...config import get_sub_agent_model
except ImportError:
    from config import get_sub_agent_model

event_agent = LlmAgent(
    name="event_agent",
    model=get_sub_agent_model(),
    description="Community events, funerals, church, stokvels, sports. Discovers + posts.",
    instruction="""You are the Event agent. Help with community events, funerals, church, stokvels, sports. Use fetch_events_tool and fetch_news_tool to search events/news, browser_tool to scrape local sites if needed, save_events_tool to post new events (title, description, when, where, tags; optional contactDetails, link). Reply short, warm. Reply in Markdown (use **bold** for emphasis, lists where helpful). Output only the reply to the user.""",
    tools=[fetch_events_tool, fetch_news_tool, save_events_tool, browser_tool],
)
