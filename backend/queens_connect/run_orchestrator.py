"""
Run the Queens Connect orchestrator with session state (currentDate, waNumber, etc.)
so context variables are available. Use this instead of `adk run` when you need
injected context.

Setup (once):
  cd queens_connect
  python3 -m venv .venv
  source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
  pip install -r requirements.txt

Usage:
  source .venv/bin/activate
  python run_orchestrator.py
  python run_orchestrator.py "what is eskom"
"""
import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure queens_connect is importable as a package (agent.py uses relative imports)
_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

# Show tool call logs when running from CLI
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from queens_connect.agent import get_root_agent
from queens_connect.tools import get_user, get_user_session

APP_NAME = "queens_connect"
USER_ID = "27712345678"
SESSION_ID = "cli_session_1"


async def setup_session_and_runner(
    wa_number: str = USER_ID,
    language_pref: str = "english",
    session_state: dict | None = None,
):
    """Create session with state so {currentDate?}, {waNumber?}, userProfile, userSession are filled. One-time load of user + session."""
    session_service = InMemorySessionService()
    user_doc = get_user(wa_number)
    session_doc = get_user_session(wa_number)
    initial_state = {
        "currentDate": datetime.now(timezone.utc).isoformat(),
        "waNumber": wa_number,
        "languagePref": language_pref,
        "currentState": json.dumps(session_state or {}, default=str),
        "userProfile": json.dumps(user_doc, default=str),
        "userSession": json.dumps(session_doc, default=str),
    }
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=wa_number,
        session_id=SESSION_ID,
        state=initial_state,
    )
    root_agent = get_root_agent()
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )
    return session_service, runner


async def call_agent_async(
    query: str,
    wa_number: str = USER_ID,
    language_pref: str = "english",
    session_state: dict | None = None,
) -> str:
    """Send one message to the orchestrator and return the final reply text."""
    _, runner = await setup_session_and_runner(
        wa_number=wa_number,
        language_pref=language_pref,
        session_state=session_state,
    )
    content = types.Content(role="user", parts=[types.Part(text=query)])
    reply_text = ""
    async for event in runner.run_async(
        user_id=wa_number,
        session_id=SESSION_ID,
        new_message=content,
    ):
        if getattr(event, "is_final_response", lambda: False)():
            if getattr(event, "content", None) and getattr(event.content, "parts", None):
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        reply_text += part.text or ""
    return reply_text.strip()


async def _run_demos():
    """Run a few test queries including ones that may use search."""
    demos = [
        "what is eskom",
        "what's the latest ai news",
        "search for load shedding schedule today",
        "hello, who are you?",
    ]
    for q in demos:
        print(f"\n[user]: {q}")
        try:
            reply = await call_agent_async(q)
            print(f"[orchestrator]: {reply or '(no reply)'}")
        except Exception as e:
            print(f"[error]: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        reply = asyncio.run(call_agent_async(query))
        print(reply)
    else:
        asyncio.run(_run_demos())
