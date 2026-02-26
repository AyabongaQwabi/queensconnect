"""Taxi & Trip Planner sub-agent: prices, lifts, load-shedding aware."""
import sys
from pathlib import Path

_qc = Path(__file__).resolve().parent.parent.parent
if str(_qc) not in sys.path:
    sys.path.insert(0, str(_qc))

from google.adk.agents import LlmAgent
from tools import fetch_transport_fares_tool, fetch_info_bits_tool

try:
    from ...config import get_sub_agent_model
except ImportError:
    from config import get_sub_agent_model

taxi_planner_agent = LlmAgent(
    name="taxi_planner",
    model=get_sub_agent_model(),
    description="Real-time taxi prices, lifts to Joburg/PE, trip planning (cost, time, load-shedding aware).",
    instruction="""You are the Taxi & Trip Planner. Use fetch_transport_fares_tool for local taxi/lift/bus/cab fares and fetch_info_bits_tool for tips (e.g. load-shedding, "full now"). Give prices, times, and mention load-shedding when relevant. Reply short, kasi style. Reply in Markdown (use **bold** for emphasis, lists where helpful). Output only the reply to the user.""",
    tools=[fetch_transport_fares_tool, fetch_info_bits_tool],
)
