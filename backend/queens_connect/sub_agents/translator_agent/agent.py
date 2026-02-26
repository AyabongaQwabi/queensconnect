"""Translator sub-agent: Xhosa ↔ English; internal use, never replies to user directly."""
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

translator_agent = LlmAgent(
    name="translator",
    model=get_sub_agent_model(),
    description="Xhosa ↔ English translation. Internal use only; never replies to user directly.",
    instruction="""You are the Translator. Translate the given text into the requested language (xhosa or english). Preserve kasi slang and natural tone. Use translate_tool. Output ONLY the translated text in Markdown if needed (e.g. **bold**), nothing else.""",
    tools=[translate_tool],
)
