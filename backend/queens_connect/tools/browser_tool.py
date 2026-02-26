"""
Browser tool: Playwright-based scrape for local news (Daily Dispatch, The Rep, Komani). ADK function tool returns dict.
"""
import logging
from typing import Optional

logger = logging.getLogger("queens_connect.tools.browser")

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


def browser_tool(url: str, instructions: Optional[str] = None) -> dict:
    """
    Scrape a URL and extract text (e.g. local news sites: Daily Dispatch, The Rep, Komani community pages).

    Args:
        url: URL to fetch.
        instructions: Optional extraction instructions for the page content.

    Returns:
        dict: status, url, text (extracted body text up to 8000 chars). On error: status "error", error_message.
    """
    logger.info("browser_tool called: url=%r", url)
    if not PLAYWRIGHT_AVAILABLE:
        return {
            "status": "error",
            "error_message": "Playwright not installed. pip install playwright && playwright install chromium",
            "url": url,
            "text": "",
        }
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            text = page.evaluate("""() => document.body ? document.body.innerText.slice(0, 15000) : ''""")
            browser.close()
        return {
            "status": "success",
            "url": url,
            "text": (text or "")[:8000],
            "instructions_note": instructions or "Full page text extracted",
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e), "url": url, "text": ""}


# Expose as ADK FunctionTool for AFC-compatible tool use
from google.adk.tools import FunctionTool

browser_tool = FunctionTool(browser_tool)
