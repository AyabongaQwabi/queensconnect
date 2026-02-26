"""Registrar sub-agent: new user onboarding, name, location, business registration."""
import sys
from pathlib import Path

_qc = Path(__file__).resolve().parent.parent.parent
if str(_qc) not in sys.path:
    sys.path.insert(0, str(_qc))

from google.adk.agents import LlmAgent
from tools import fetch_towns_tool, fetch_suburbs_tool

try:
    from ...config import get_sub_agent_model
except ImportError:
    from config import get_sub_agent_model

registrar_agent = LlmAgent(
    name="registrar",
    model=get_sub_agent_model(),
    description="Handles new user onboarding: name, location, business registration.",
    instruction="""You are the Queens Connect Registrar. Help new users onboard: get name, location (area/town—use generic terms like "your area", "your town", or suggest from fetch_towns_tool/fetch_suburbs_tool without assuming a specific place like Ezibeleni unless the user said it), and whether they want to register as business. Use fetch_towns_tool and fetch_suburbs_tool to validate or suggest locations. For saving user records (waNumber, name, location, isBusiness), hand back to the main agent—you do not have a user-save tool. Reply in friendly South African English, short; every reply at least 2 emojis. If you have enough info, say what will be saved and ask to confirm, then transfer to main agent. Reply in Markdown (use **bold** for emphasis, lists where helpful). Output only the reply to the user.""",
    tools=[fetch_towns_tool, fetch_suburbs_tool],
)
