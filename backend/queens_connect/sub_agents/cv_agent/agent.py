"""CV sub-agent: collect CV sections from the user, save to Firestore, generate PDF or DOCX and upload to Storage."""
from pathlib import Path

from google.adk.agents import LlmAgent

from ... import config
from ...tools import (
    get_cv_doc_tool,
    save_cv_doc_tool,
    generate_cv_pdf_tool,
    generate_cv_docx_tool,
)


def _load_instruction() -> str:
    path = getattr(config, "CV_AGENT_PROMPT_PATH", None) or (
        config.REPO_ROOT / "docs" / "prompts" / "cv-agent.md"
    )
    if not path.exists():
        return (
            "You are the Queens Connect CV agent. Call get_cv_doc_tool(wa_number) with waNumber from session. "
            "If fileLink exists, give the user the link. Otherwise collect: particulars, education, higher education, "
            "work experience, bio, contact, references. Save with save_cv_doc_tool after each section. "
            "Then ask PDF or DOCX and call generate_cv_pdf_tool or generate_cv_docx_tool. "
            "Friendly, short replies; at least 2 emojis. Output only the final reply."
        )
    text = path.read_text(encoding="utf-8")
    text = text.replace("{currentDate}", "{currentDate?}").replace("{waNumber}", "{waNumber?}")
    text = text.replace("{languagePref}", "{languagePref?}")
    return text


cv_agent = LlmAgent(
    name="cv_agent",
    model=config.get_sub_agent_model(),
    description="Collect CV data from the user (particulars, education, work experience, bio, contact, references), save to Firestore, and generate a PDF or DOCX file for download.",
    instruction=_load_instruction(),
    tools=[
        get_cv_doc_tool,
        save_cv_doc_tool,
        generate_cv_pdf_tool,
        generate_cv_docx_tool,
    ],
    sub_agents=[],
)
