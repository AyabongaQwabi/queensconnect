"""
Queens Connect – config for tools (env-based). Used when running sub-agents.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

QC_DIR = Path(__file__).resolve().parent
load_dotenv(QC_DIR / ".env")
load_dotenv(QC_DIR.parent / ".env")

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
# Tool/function calling: gemini-2.5-pro (or 2.5-flash, 2.0-flash). Override with MODEL= in .env.
GEMINI_MODEL = os.environ.get("MODEL", "gemini-2.5-flash")
# Sub-agents: Llama 4 70B via Groq (LiteLLM). Set GROQ_API_KEY in .env.
GROQ_MODEL = os.environ.get("GROQ_MODEL", "groq/llama-3.3-70b-versatile")
# Grok rewrite step: xai/grok-4-1-fast-reasoning. Set XAI_API_KEY in .env.
GROK_MODEL = os.environ.get("GROK_MODEL", "xai/grok-4-1-fast-reasoning")
# Direct Firestore access (tools/firebase_tools.py).
# Firestore expects host:port only (no http://). Leave FIRESTORE_EMULATOR_HOST unset or "" for production.
FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID", "queens-connect-2c94d")
FIRESTORE_EMULATOR_HOST = (os.environ.get("FIRESTORE_EMULATOR_HOST") or "").strip()
# Firebase Storage bucket for CV uploads (default: project_id.appspot.com).
FIREBASE_STORAGE_BUCKET = os.environ.get("FIREBASE_STORAGE_BUCKET", "").strip() or None  # None => use FIREBASE_PROJECT_ID + ".appspot.com"
FIREBASE_ID_TOKEN = ""
SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "")

# Yoco Payment Links (loan unlock fees). Set YOCO_SECRET_KEY in .env (e.g. sk_test_... or sk_live_...).
YOCO_SECRET_KEY = os.environ.get("YOCO_SECRET_KEY", "")

# Base URL for payment callbacks/success pages. Set LENDING_BASE_URL or BASE_URL in .env.
LENDING_BASE_URL = (os.environ.get("LENDING_BASE_URL") or os.environ.get("BASE_URL") or "").strip().rstrip("/")
BASE_URL = (os.environ.get("BASE_URL") or "").strip().rstrip("/")

REPO_ROOT = Path(__file__).resolve().parent

# LiteLLM model for sub-agents (Llama via Groq). Used with LlmAgent: model=get_sub_agent_model().



ORCHESTRATOR_PROMPT_PATH = REPO_ROOT / "docs" / "prompts" / "orchestrator-system-prompt.md"
GATEKEEPER_PROMPT_PATH = REPO_ROOT / "docs" / "prompts" / "gatekeeper-system-prompt.md"
MODERATION_PROMPT_PATH = REPO_ROOT / "docs" / "prompts" / "moderation-system-prompt.md"
CORE_ORCHESTRATOR_PROMPT_PATH = REPO_ROOT / "docs" / "prompts" / "core-orchestrator-system-prompt.md"
LOANS_AGENT_PROMPT_PATH = REPO_ROOT / "docs" / "prompts" / "loans-agent.md"
LOANS_REGISTRATION_AGENT_PROMPT_PATH = REPO_ROOT / "docs" / "prompts" / "loans-registration-agent.md"
LENDING_AGENT_PROMPT_PATH = REPO_ROOT / "docs" / "prompts" / "lending-agent.md"
STOKVEL_AGENT_PROMPT_PATH = REPO_ROOT / "docs" / "prompts" / "stokvel-agent.md"
CV_AGENT_PROMPT_PATH = REPO_ROOT / "docs" / "prompts" / "cv-agent.md"
GROK_REWRITE_PROMPT_PATH = REPO_ROOT / "docs" / "prompts" / "grok-rewrite-system-prompt.md"

# Onboarding state machine: step meaning "user finished onboarding"
ONBOARDING_COMPLETE_STEP = "onboardingComplete"

# Canonical field names – do not invent synonyms (see field reference.md)
FIELD_NAMES = [
    "waNumber",
    "ownerUid",
    "authorUid",
    "text",
    "tags",
    "location",
    "priceRange",
    "expiresAt",
    "createdAt",
    "title",
    "description",
    "contact",
    "type",
    "languagePref",
    "name",
    "verified",
    "priorityUntil",
    "rating",
]

# orchestratorCall actions (must match functions/src/index.ts)
ACTIONS = [
    "createUserIfNotExists",
    "updateUserProfile",
    "addInfoBit",
    "createListing",
    "searchEverything",
    "startNegotiation",
    "sendNegotiationMessage",
    "createIkhokhaPaymentLink",
    "getWalletBalance",
    "addLostAndFound",
    "reportContent",
    "getCommunityUpdates",
    "notifyStokvelNewMember",
]

def get_sub_agent_model():
    return GEMINI_MODEL