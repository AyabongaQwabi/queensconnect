"""
Translate tool: Xhosa <-> English via an ADK agent. Preserves kasi slang.
Exposes translate_tool(text, target_lang) returning dict for use as a FunctionTool.
"""
import asyncio
import logging
from typing import Literal

logger = logging.getLogger("queens_connect.tools.translate")

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

try:
    from ..config import get_sub_agent_model
except ImportError:
    from config import get_sub_agent_model

APP_NAME = "queens_connect"
TRANSLATOR_USER_ID = "translator_tool"
TRANSLATOR_SESSION_ID = "translate_session"

translator_agent = LlmAgent(
    name="translator_agent",
    model=get_sub_agent_model(),
    description="Translates text between Xhosa and English. Outputs only the translation.",
    instruction="""You are a translator. Given text and a target language (xhosa or english), output ONLY the translated text. Preserve kasi slang and natural tone. No explanations, no quotes, no preamble.""",
    tools=[],
)


async def _translate_async(text: str, target_lang: str) -> str:
    if not text or not text.strip():
        return ""
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=TRANSLATOR_USER_ID,
        session_id=TRANSLATOR_SESSION_ID,
    )
    runner = Runner(
        agent=translator_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )
    prompt = f"Translate the following into {target_lang}. Output only the translation.\n\n{text}"
    content = types.Content(role="user", parts=[types.Part(text=prompt)])
    reply = ""
    async for event in runner.run_async(
        user_id=TRANSLATOR_USER_ID,
        session_id=TRANSLATOR_SESSION_ID,
        new_message=content,
    ):
        if getattr(event, "is_final_response", lambda: False)():
            if getattr(event, "content", None) and getattr(event.content, "parts", None):
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        reply += (part.text or "").strip()
    return reply.strip()


def translate_tool(text: str, target_lang: Literal["xhosa", "english"]) -> dict:
    """
    High-quality translation between Xhosa and English via translator agent. Preserves kasi slang and tone.

    Args:
        text: Text to translate.
        target_lang: Target language: "xhosa" or "english".

    Returns:
        dict: status, translated text, target_lang. On error: status "error", error_message.
    """
    logger.info(
        "translate_tool called: target_lang=%r text_len=%s",
        target_lang, len(text) if text else 0,
    )
    if not text or not text.strip():
        return {"status": "success", "translated": "", "target_lang": target_lang}
    try:
        translated = asyncio.run(_translate_async(text, target_lang))
        return {"status": "success", "translated": translated, "target_lang": target_lang}
    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "translated": "",
            "target_lang": target_lang,
        }


# Expose as ADK FunctionTool for AFC-compatible tool use
from google.adk.tools import FunctionTool

translate_tool = FunctionTool(translate_tool)
