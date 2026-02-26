"""Core orchestrator: all save/fetch tools and sub-agents. No onboarding logic."""

from google.adk.agents import Agent

from .. import config
from ..tools import (
    save_community_updates_tool,
    save_complaints_tool,
    save_emergency_numbers_tool,
    save_events_tool,
    save_gov_info_tool,
    save_info_bits_tool,
    save_knowledge_share_tool,
    save_listings_tool,
    save_lost_and_found_tool,
    save_news_tool,
    save_places_tool,
    save_suburbs_tool,
    save_towns_tool,
    save_transport_fares_tool,
    fetch_community_updates_tool,
    fetch_complaints_tool,
    fetch_emergency_numbers_tool,
    fetch_events_tool,
    fetch_gov_info_tool,
    fetch_info_bits_tool,
    fetch_knowledge_share_tool,
    fetch_listings_tool,
    fetch_lost_and_found_tool,
    fetch_news_tool,
    fetch_places_tool,
    fetch_suburbs_tool,
    fetch_towns_tool,
    fetch_transport_fares_tool,
    browser_tool,
    translate_tool,
    append_to_custom_info_tool,
    update_user_tool,
)
from ..sub_agents.complaints_agent import complaints_agent
from ..sub_agents.event_agent import event_agent
from ..sub_agents.infobit_tagger_agent import infobit_tagger_agent
from ..sub_agents.lost_found_agent import lost_found_agent
from ..sub_agents.news_scraper_agent import news_scraper_agent
from ..sub_agents.cultural_knowledge_agent import cultural_knowledge_agent
from ..sub_agents.translator_agent import translator_agent
from ..sub_agents.registrar_agent import registrar_agent
from ..sub_agents.taxi_planner_agent import taxi_planner_agent
from ..sub_agents.loans_agent import loans_agent
from ..sub_agents.lending_agent import lending_agent


def _load_core_instruction() -> str:
    path = getattr(config, "CORE_ORCHESTRATOR_PROMPT_PATH", None) or (
        config.REPO_ROOT / "docs" / "prompts" / "core-orchestrator-system-prompt.md"
    )
    if not path.exists():
        return (
            "You are Queens Connect – friendly local assistant. Speak in friendly, fun South African English (no kasi slang unless user uses it). "
            "Be warm, short, use tools when needed. Never leak numbers without double consent. "
            "Reply in user's languagePref (default english). Never ask for language preference. "
            "Every reply at least 2 emojis. When no clear request, tell user what they can do on the app. "
            "Never assume a specific area (e.g. Ezibeleni)—use 'your area' or 'your town' unless user said a place. "
            "Current date: {currentDate?}. User WA number: {waNumber?}. Language: {languagePref?}. "
            "Output ONLY the final reply."
        )
    text = path.read_text(encoding="utf-8")
    text = text.replace("{currentDate}", "{currentDate?}").replace("{waNumber}", "{waNumber?}")
    text = text.replace("{languagePref}", "{languagePref?}").replace("{currentState}", "{currentState?}")
    text = text.replace("{userProfile}", "{userProfile?}").replace("{userSession}", "{userSession?}")
    text = text.replace("{lenderOrBorrowerSummary}", "{lenderOrBorrowerSummary?}")
    text = text.replace("{lenderProfile}", "{lenderProfile?}").replace("{borrowerProfile}", "{borrowerProfile?}")
    return text


def get_core_orchestrator() -> Agent:
    """Build the core orchestrator (all tools + sub-agents, no onboarding)."""
    return Agent(
        name="core_orchestrator",
        model=config.GEMINI_MODEL,
        description="Main brain: receives messages after onboarding, classifies intent, routes to sub-agents or uses tools.",
        instruction=_load_core_instruction(),
        tools=[
            save_community_updates_tool,
            save_complaints_tool,
            save_emergency_numbers_tool,
            save_events_tool,
            save_gov_info_tool,
            save_info_bits_tool,
            save_knowledge_share_tool,
            save_listings_tool,
            save_lost_and_found_tool,
            save_news_tool,
            save_places_tool,
            save_suburbs_tool,
            save_towns_tool,
            save_transport_fares_tool,
            fetch_community_updates_tool,
            fetch_complaints_tool,
            fetch_emergency_numbers_tool,
            fetch_events_tool,
            fetch_gov_info_tool,
            fetch_info_bits_tool,
            fetch_knowledge_share_tool,
            fetch_listings_tool,
            fetch_lost_and_found_tool,
            fetch_news_tool,
            fetch_places_tool,
            fetch_suburbs_tool,
            fetch_towns_tool,
            fetch_transport_fares_tool,
            browser_tool,
            translate_tool,
            append_to_custom_info_tool,
            update_user_tool,
        ],
        sub_agents=[
            complaints_agent,
            event_agent,
            infobit_tagger_agent,
            lost_found_agent,
            news_scraper_agent,
            cultural_knowledge_agent,
            translator_agent,
            registrar_agent,
            taxi_planner_agent,
            loans_agent,
            lending_agent,
        ],
    )


core_orchestrator = get_core_orchestrator()
