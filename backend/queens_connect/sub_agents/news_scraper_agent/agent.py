"""News Scraper sub-agent: Daily Dispatch + local sites, summarise, post to news."""
import sys
from pathlib import Path

_qc = Path(__file__).resolve().parent.parent.parent
if str(_qc) not in sys.path:
    sys.path.insert(0, str(_qc))

from google.adk.agents import LlmAgent
from tools import browser_tool, save_news_tool, translate_tool

try:
    from ...config import get_sub_agent_model
except ImportError:
    from config import get_sub_agent_model

news_scraper_agent = LlmAgent(
    name="news_scraper",
    model=get_sub_agent_model(),
    description="Pulls Daily Dispatch + local sites → summarises in Xhosa + English → posts to news.",
    instruction="""You are the News Scraper. Use browser_tool to fetch local news URLs, translate_tool for Xhosa/English, save_news_tool to post to news (title, tags required; optional summaryEn, summaryXh, sourceUrl, link). Summarise briefly. Reply short. Reply in Markdown (use **bold** for emphasis, lists where helpful). Output only the reply to the user.""",
    tools=[browser_tool, save_news_tool, translate_tool],
)
