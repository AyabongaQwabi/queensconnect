"""
Queens Connect Web Chat – FastAPI backend.
Keeps the ADK agent loaded once at startup; POST /chat reuses the same runner.
POST /chat/stream runs the pipeline and streams the raw reply via SSE.
POST /webhook/twilio/whatsapp receives incoming Twilio WhatsApp messages and returns TwiML.
"""
import json
import logging
import os
import re
import time
from contextlib import asynccontextmanager
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

try:
    from backend.agent_runner import (
        init_runner,
        run_message_async,
        run_message_async_raw,
    )
    from backend.queens_connect.tools.lending_tools import (
        create_lender_profile,
        create_borrower_profile,
        complete_unlock_after_payment,
        create_unlock_payment_link,
        record_proof_of_payment,
    )
except ImportError:
    from agent_runner import (
        init_runner,
        run_message_async,
        run_message_async_raw,
    )
    from queens_connect.tools.lending_tools import (
        create_lender_profile,
        create_borrower_profile,
        complete_unlock_after_payment,
        create_unlock_payment_link,
        record_proof_of_payment,
    )

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    wa_number: str = Field(..., description="User identifier (e.g. web_guest or WhatsApp number)")
    message: str = Field(..., min_length=1, description="User message")
    language_pref: str = Field(default="english", description="Language preference")


class ChatResponse(BaseModel):
    reply: str
    error: str | None = None


class CreateLenderRequest(BaseModel):
    wa_number: str = Field(..., min_length=1, description="WhatsApp number or user ID")
    display_name: str = Field(..., min_length=1, description="Full name and surname (e.g. Sipho Ngcobo)")
    id_number: str | None = Field(default=None, description="South African ID number (13 digits)")
    address: str | None = Field(default=None, description="Physical address (e.g. 123 Ezibeleni, Zone 3, Komani)")


class CreateBorrowerRequest(BaseModel):
    wa_number: str = Field(..., min_length=1, description="WhatsApp number or user ID")
    display_name: str = Field(..., min_length=1, description="Full name and surname (e.g. Awonke S.)")
    id_number: str | None = Field(default=None, description="South African ID number (13 digits)")
    address: str | None = Field(default=None, description="Physical address (e.g. 123 Ezibeleni, Zone 3, Komani)")


class CreateUnlockPaylinkRequest(BaseModel):
    lender_uid: str = Field(..., min_length=1, description="Lender WhatsApp number or user ID")
    loan_request_ids: list[str] = Field(..., min_length=1, max_length=3, description="1–3 loan request IDs to unlock")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Agent/runner are lazy-inited on first /chat or /chat/stream so the server can bind to PORT quickly (e.g. Render)."""
    yield
    # Shutdown: nothing to tear down (in-memory only)


app = FastAPI(
    title="Queens Connect Web Chat API",
    description="Persistent ADK agent behind a simple /chat endpoint",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://homiest-simonne-unofficious.ngrok-free.dev",
        "https://qwabi.co.za",
        "https://www.qwabi.co.za",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Proof-of-payment uploads: store under backend/uploads/pop/{loan_id}/
UPLOADS_DIR = Path(__file__).resolve().parent / "uploads"
POP_DIR = UPLOADS_DIR / "pop"
if not POP_DIR.exists():
    POP_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# React app (SPA) serving is registered at the end so API routes take precedence

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process one chat message and return the agent reply."""
    logger.info("chat wa_number=%s message_len=%d", request.wa_number, len(request.message))
    try:
        reply = await run_message_async(
            wa_number=request.wa_number,
            message=request.message.strip(),
            language_pref=request.language_pref,
        )
        return ChatResponse(reply=reply, error=None)
    except Exception as e:
        logger.exception("chat failed: %s", e)
        return ChatResponse(
            reply="We apologise for the inconvenience. We are experiencing technical difficulties. Please try again in a few minutes.",
            error=str(e),
        )


async def _stream_chat_generator(wa_number: str, message: str, language_pref: str):
    """Run pipeline to get raw_reply, then stream it via SSE. Final event includes reply and responseTimeMs."""
    start = time.perf_counter()
    try:
        raw_reply = await run_message_async_raw(
            wa_number=wa_number,
            message=message,
            language_pref=language_pref,
        )
    except Exception as e:
        logger.exception("run_message_async_raw failed: %s", e)
        yield f"data: {json.dumps({'error': str(e), 'reply': 'We apologise for the inconvenience. We are experiencing technical difficulties. Please try again in a few minutes.'})}\n\n"
        return
    yield f"data: {json.dumps({'text': raw_reply})}\n\n"
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    yield f"data: {json.dumps({'done': True, 'reply': raw_reply, 'responseTimeMs': elapsed_ms})}\n\n"


@app.post("/admin/lenders")
async def admin_create_lender(request: CreateLenderRequest):
    """Create a lender profile (admin UI). Same as agent create_lender_profile_tool."""
    result = create_lender_profile(
        wa_number=request.wa_number.strip(),
        display_name=request.display_name.strip(),
        id_number=request.id_number.strip() if request.id_number else None,
        address=request.address.strip() if request.address else None,
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error_message", "Failed to create lender"))
    return result


@app.post("/admin/borrowers")
async def admin_create_borrower(request: CreateBorrowerRequest):
    """Create a borrower profile (admin UI). Same as agent create_borrower_profile_tool."""
    result = create_borrower_profile(
        wa_number=request.wa_number.strip(),
        display_name=request.display_name.strip(),
        id_number=request.id_number.strip() if request.id_number else None,
        address=request.address.strip() if request.address else None,
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error_message", "Failed to create borrower"))
    return result


@app.post("/api/lending/create-unlock-paylink")
async def api_create_unlock_paylink(request: CreateUnlockPaylinkRequest):
    """
    Create an iKhoka payment link for unlocking loan request(s). Returns paylinkUrl for the lender to pay
    (R5 per request or R10 for 3). On payment success iKhoka calls /api/lending/ikhokha-callback.
    """
    result = create_unlock_payment_link(
        lender_uid=request.lender_uid.strip(),
        loan_request_ids=[x.strip() for x in request.loan_request_ids if x.strip()],
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error_message", "Failed to create pay link"))
    return result


@app.post("/api/lending/loans/{loan_id}/proof")
async def upload_proof_of_payment(loan_id: str, request: Request, file: UploadFile = File(...)):
    """
    Upload proof of payment for a loan (image or PDF). Saves the file, records the URL on the loan,
    and sets loan status to active. Lenders use the link shared in WhatsApp (e.g. /pop/<loanId>).
    """
    loan_id_clean = (loan_id or "").strip()
    if not loan_id_clean:
        raise HTTPException(status_code=400, detail="loan_id required")
    # Sanitize for path: alphanumeric and hyphen only
    if not re.match(r"^[a-zA-Z0-9_-]+$", loan_id_clean):
        raise HTTPException(status_code=400, detail="Invalid loan_id")
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    # Allow image/* and PDF
    content_type = (file.content_type or "").lower()
    if not (
        content_type.startswith("image/")
        or content_type == "application/pdf"
    ):
        raise HTTPException(
            status_code=400,
            detail="File must be an image (JPEG, PNG, etc.) or PDF",
        )
    ext = Path(file.filename).suffix or ".bin"
    if not re.match(r"^.[a-zA-Z0-9]+$", ext):
        ext = ".bin"
    # Save to uploads/pop/{loan_id}/{timestamp}{ext}
    subdir = POP_DIR / loan_id_clean
    subdir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{int(time.time() * 1000)}{ext}"
    file_path = subdir / safe_name
    try:
        contents = await file.read()
        file_path.write_bytes(contents)
    except Exception as e:
        logger.exception("Failed to save POP file: %s", e)
        raise HTTPException(status_code=500, detail="Failed to save file")
    base_url = str(request.base_url).rstrip("/")
    pop_url = f"{base_url}/uploads/pop/{loan_id_clean}/{safe_name}"
    result = record_proof_of_payment(loan_id=loan_id_clean, pop_url=pop_url)
    if result.get("status") == "error":
        try:
            file_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise HTTPException(
            status_code=400,
            detail=result.get("error_message", "Failed to record proof of payment"),
        )
    logger.info("upload_proof_of_payment loan_id=%s pop_url=%s", loan_id_clean, pop_url)
    return {"status": "success", "message": "Proof of payment recorded."}


@app.post("/api/lending/ikhokha-callback")
async def ikhokha_callback(request: Request):
    """
    iKhoka payment callback. On successful payment they POST with paylinkID and/or
    externalTransactionID. We look up pending_unlocks and call unlock_loan_request.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}
    logger.info("ikhokha_callback body: %s", body)
    paylink_id = (body.get("paylinkID") or body.get("payLinkID") or "").strip()
    external_id = (body.get("externalTransactionID") or body.get("externalTransactionId") or "").strip()
    key = external_id or paylink_id
    if not key:
        logger.warning("ikhokha_callback missing paylinkID and externalTransactionID")
        raise HTTPException(status_code=400, detail="Missing paylinkID or externalTransactionID")
    result = complete_unlock_after_payment(key)
    if result.get("status") == "error":
        logger.warning("ikhokha_callback complete_unlock failed: %s", result.get("error_message"))
        raise HTTPException(status_code=400, detail=result.get("error_message", "Unlock failed"))
    return {"status": "ok"}


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Run pipeline once, then stream the raw reply via Server-Sent Events."""
    logger.info("chat/stream wa_number=%s message_len=%d", request.wa_number, len(request.message))
    return StreamingResponse(
        _stream_chat_generator(
            wa_number=request.wa_number,
            message=request.message.strip(),
            language_pref=request.language_pref,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _twiml_message(reply: str) -> str:
    """Build TwiML Response with a single Message. Reply text is escaped by ElementTree."""
    response = Element("Response")
    msg = SubElement(response, "Message")
    msg.text = reply
    return '<?xml version="1.0" encoding="UTF-8"?>' + tostring(response, encoding="unicode", method="xml")


@app.post("/webhook/twilio/whatsapp")
@app.post("/webhook/twillio/whatsapp")  # common typo: accept so Twilio webhook URL works either way
async def webhook_twilio_whatsapp(request: Request):
    """
    Incoming Twilio WhatsApp webhook.

    Twilio POSTs application/x-www-form-urlencoded with From, To, Body, NumMedia, MediaUrl0, etc.
    We run the message through the agent and return TwiML with the reply.
    See: https://www.twilio.com/docs/whatsapp/tutorial/send-and-receive-media-messages-whatsapp-nodejs
    """
    # Parse form (Twilio sends application/x-www-form-urlencoded)
    form = await request.form()
    form_dict = dict(form)

    # Optional: validate X-Twilio-Signature (if TWILIO_AUTH_TOKEN is set)
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
    if auth_token:
        try:
            from twilio.request_validator import RequestValidator
            validator = RequestValidator(auth_token)
            signature = request.headers.get("X-Twilio-Signature", "")
            # Full URL including scheme and query string (Twilio uses this for signing)
            url = str(request.url)
            if not validator.validate(url, form_dict, signature):
                logger.warning("Twilio webhook signature validation failed")
                raise HTTPException(status_code=403, detail="Invalid Twilio signature")
        except ImportError:
            logger.warning("twilio package not installed; skipping signature validation")

    from_ = form_dict.get("From", "")
    to = form_dict.get("To", "")
    body = (form_dict.get("Body") or "").strip()
    num_media = int(form_dict.get("NumMedia") or "0")

    # Normalize wa_number: strip whatsapp: prefix
    wa_number = from_.replace("whatsapp:", "").strip() if from_ else ""
    if not wa_number:
        logger.warning("Twilio webhook missing From")
        return Response(
            content=_twiml_message("We didn't get your number — please try again."),
            media_type="application/xml",
        )

    # Build message: include text and optional note about attached media
    message = body
    if num_media > 0 and not message:
        message = "[User sent media]"
    elif num_media > 0:
        message = f"{message} [User also sent {num_media} media attachment(s)]"
    if not message:
        message = "[Empty message]"

    logger.info("webhook_twilio_whatsapp from=%s to=%s body_len=%d num_media=%d", wa_number, to, len(body), num_media)

    try:
        reply = await run_message_async(
            wa_number=wa_number,
            message=message,
            language_pref="english",
        )
    except Exception as e:
        logger.exception("run_message_async failed in Twilio webhook: %s", e)
        reply = "We're having a quick hiccup — try again in a moment."

    return Response(
        content=_twiml_message(reply),
        media_type="application/xml",
    )


# --- React app (SPA): serve static files and fallback to index.html for client-side routes ---
# Registered last so /health, /chat, /api/*, /admin/*, /webhook/*, /uploads/* are matched first
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
SPA_PATHS = ("/api/", "/admin/", "/webhook/", "/uploads/", "/chat", "/health")


@app.exception_handler(404)
async def spa_fallback(request: Request, _exc: HTTPException):
    """For GET requests to non-API paths, serve the React app so SPA routing works."""
    if request.method != "GET":
        raise HTTPException(status_code=404)
    path = (request.url.path or "").strip()
    if any(path.startswith(p) for p in SPA_PATHS):
        raise HTTPException(status_code=404)
    index_html = FRONTEND_DIST / "index.html"
    if not index_html.exists():
        raise HTTPException(status_code=404)
    return FileResponse(index_html, media_type="text/html")


if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
else:
    logger.warning("frontend/dist not found at %s; build frontend (npm run build) to serve the React app", FRONTEND_DIST)
