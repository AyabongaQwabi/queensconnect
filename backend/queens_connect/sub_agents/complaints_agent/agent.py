"""Complaints sub-agent: reports, scam flags, bad deals; logs for human review."""
import sys
from pathlib import Path

_qc = Path(__file__).resolve().parent.parent.parent
if str(_qc) not in sys.path:
    sys.path.insert(0, str(_qc))

from google.adk.agents import LlmAgent
from tools import fetch_complaints_tool, save_complaints_tool

try:
    from ...config import get_sub_agent_model
except ImportError:
    from config import get_sub_agent_model

complaints_agent = LlmAgent(
    name="complaints",
    model=get_sub_agent_model(),
    description="Handles reports, scam flags, bad deals. Logs for human review.",
    instruction="""You are the Complaints agent. Handle reports, scam flags, bad deals. Use fetch_complaints_tool to look up content, save_complaints_tool with collection complaints (reportContent). Be empathetic but firm. Log for human review. Reply short. Reply in Markdown (use **bold** for emphasis, lists where helpful). Output only the reply to the user.""",
    tools=[fetch_complaints_tool, save_complaints_tool],
)
