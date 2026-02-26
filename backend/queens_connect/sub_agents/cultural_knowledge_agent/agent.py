"""Cultural Knowledge sub-agent: Xhosa proverbs, local history, traditions."""
import sys
from pathlib import Path

_qc = Path(__file__).resolve().parent.parent.parent
if str(_qc) not in sys.path:
    sys.path.insert(0, str(_qc))

from google.adk.agents import LlmAgent
from tools import fetch_knowledge_share_tool, fetch_info_bits_tool

try:
    from ...config import get_sub_agent_model
except ImportError:
    from config import get_sub_agent_model

cultural_knowledge_agent = LlmAgent(
    name="cultural_knowledge",
    model=get_sub_agent_model(),
    description="Xhosa proverbs, local history, traditions. Answers deep cultural questions about Komani.",
    instruction="""You are the Cultural Knowledge agent. Answer questions about Xhosa proverbs, local history, traditions, "why we do things this way in Komani". Use fetch_knowledge_share_tool and fetch_info_bits_tool to search local knowledge. Be warm and accurate. Reply short. Reply in Markdown (use **bold** for emphasis, lists where helpful). Output only the reply to the user.""",
    tools=[fetch_knowledge_share_tool, fetch_info_bits_tool],
)
