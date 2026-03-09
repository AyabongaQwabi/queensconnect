"""
CV tools: get/save CV doc (Firestore cvs/{waNumber}), generate PDF/DOCX and upload to Firebase Storage.
Used by cv_agent to collect CV data and produce downloadable files.
"""
import io
import logging
from datetime import timedelta, timezone
from typing import Optional

from google.adk.tools import FunctionTool

try:
    from ..config import FIREBASE_PROJECT_ID, FIREBASE_STORAGE_BUCKET
except ImportError:
    from config import FIREBASE_PROJECT_ID, FIREBASE_STORAGE_BUCKET

logger = logging.getLogger("queens_connect.tools.cv")

# Allowed top-level keys when saving CV doc (merge only these)
CV_TOP_LEVEL_KEYS = frozenset({
    "particulars", "education", "higherEducation", "workExperience",
    "bio", "contact", "references", "fileLink", "format", "updatedAt",
})

# Minimum required for generation: must have these sections (content can be minimal)
REQUIRED_FOR_GENERATION = ("particulars", "education", "contact")


def _get_db():
    """Use Firestore from firebase_tools (ensures Firebase app is initialized)."""
    from .firebase_tools import _get_db as _firestore_db
    return _firestore_db()


def _get_storage_bucket():
    """Return the default Storage bucket for CV uploads."""
    bucket_name = FIREBASE_STORAGE_BUCKET or f"{FIREBASE_PROJECT_ID}.firebasestorage.app"
    try:
        from google.cloud import storage
        client = storage.Client(project=FIREBASE_PROJECT_ID)
        return client.bucket(bucket_name)
    except Exception as e:
        logger.exception("_get_storage_bucket failed: %s", e)
        raise


def _normalize_wa(wa_number: Optional[str]) -> str:
    if wa_number is None:
        return ""
    return str(wa_number).strip()


def _serialize_doc(data: dict) -> dict:
    """Convert Firestore timestamps to ISO strings for JSON-friendly return."""
    from datetime import datetime
    out = dict(data)
    for key in ("updatedAt", "createdAt"):
        if key in out and out[key] is not None:
            v = out[key]
            if hasattr(v, "seconds"):  # Firestore Timestamp
                out[key] = datetime.fromtimestamp(v.seconds + (getattr(v, "nanoseconds", 0) or 0) / 1e9, tz=timezone.utc).isoformat()
            elif hasattr(v, "isoformat"):
                out[key] = v.isoformat()
    return out


# ---------- Public tool implementations ----------


def get_cv_doc(wa_number: str) -> dict:
    """
    Get the CV document for this user. Call with waNumber from session state.
    Returns the document (including fileLink if a CV has been generated) or empty dict if none exists.
    Use on entry to decide: if fileLink is present, give the user the link; else start or continue collection.
    """
    wa = _normalize_wa(wa_number)
    if not wa:
        return {"exists": False, "error": "wa_number required"}
    try:
        db = _get_db()
        ref = db.collection("cvs").document(wa)
        doc = ref.get()
        if not doc.exists:
            return {"exists": False}
        data = doc.to_dict()
        out = _serialize_doc({"exists": True, "id": doc.id, **(data or {})})
        return out
    except Exception as e:
        logger.exception("get_cv_doc failed: %s", e)
        return {"exists": False, "error": str(e)}


def save_cv_doc(wa_number: str, data: dict) -> dict:
    """
    Save or merge CV data for this user. Call with waNumber from session and a dict containing
    any of: particulars, education, higherEducation, workExperience, bio, contact, references.
    Used after each section or at end of collection. Merges into existing doc.
    Returns status and message.
    """
    wa = _normalize_wa(wa_number)
    if not wa:
        return {"status": "error", "error_message": "wa_number required"}
    # Only merge allowed top-level keys; do not allow fileLink/format to be set by agent (only generate_* set those)
    allowed = {k: v for k, v in (data or {}).items() if k in CV_TOP_LEVEL_KEYS and k not in ("fileLink", "format")}
    if not allowed:
        return {"status": "error", "error_message": "No valid CV fields to save. Use: particulars, education, higherEducation, workExperience, bio, contact, references."}
    try:
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP
    except ImportError:
        from google.cloud.firestore import SERVER_TIMESTAMP
    payload = {**allowed, "updatedAt": SERVER_TIMESTAMP}
    try:
        db = _get_db()
        ref = db.collection("cvs").document(wa)
        ref.set(payload, merge=True)
        logger.info("save_cv_doc wa=%s keys=%s", wa[:6] + "***", list(payload.keys()))
        return {"status": "success", "message": "CV data saved."}
    except Exception as e:
        logger.exception("save_cv_doc failed: %s", e)
        return {"status": "error", "error_message": str(e)}


def _validate_cv_for_generation(doc: dict) -> Optional[str]:
    """Return None if doc has all required sections; else return error message."""
    for key in REQUIRED_FOR_GENERATION:
        if key not in doc or doc[key] is None:
            return f"Missing required section: {key}. Please collect all sections before generating."
    p = doc.get("particulars") or {}
    if not isinstance(p, dict):
        return "particulars must be an object."
    if not (p.get("name") or p.get("surname")):
        return "Particulars must include at least name and surname."
    c = doc.get("contact") or {}
    if not isinstance(c, dict):
        return "contact must be an object."
    if not (c.get("email") or c.get("contactNumber")):
        return "Contact must include at least email or contact number."
    return None


def _build_pdf_bytes(doc: dict) -> bytes:
    """Render CV document to PDF bytes."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    except ImportError:
        raise RuntimeError("reportlab is required for PDF generation. Install with: pip install reportlab")
    buffer = io.BytesIO()
    story = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(name="CVTitle", parent=styles["Heading1"], fontSize=16, spaceAfter=6)
    heading_style = ParagraphStyle(name="CVHeading", parent=styles["Heading2"], fontSize=12, spaceAfter=4)
    body_style = styles["Normal"]

    def add_para(text: str, style=None):
        if not text:
            return
        safe = (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        story.append(Paragraph(safe, style or body_style))
        story.append(Spacer(1, 4))

    p = doc.get("particulars") or {}
    name = f"{p.get('name', '')} {p.get('surname', '')}".strip() or "CV"
    add_para(name, title_style)
    add_para(f"DOB: {p.get('dateOfBirth', '')} | Nationality: {p.get('nationality', '')} | ID: {p.get('idNumber', '')} | Gender: {p.get('gender', '')}")
    if p.get("taxNumber"):
        add_para(f"Tax number: {p.get('taxNumber')}")
    add_para(f"Criminal record: {'Yes' if p.get('hasCriminalRecord') else 'No'}")
    story.append(Spacer(1, 8))

    add_para("Education", heading_style)
    e = doc.get("education") or {}
    add_para(f"High school: {e.get('highSchoolName', '')}. Highest grade: {e.get('highestGradePassed', '')}. Matriculated: {'Yes' + (' (' + str(e.get('matriculationYear', '')) + ')' if e.get('matriculationYear') else '') if e.get('matriculated') else 'No'}.")
    story.append(Spacer(1, 6))

    higher = doc.get("higherEducation") or []
    if higher:
        add_para("Higher Education", heading_style)
        for h in higher:
            if isinstance(h, dict):
                add_para(f"{h.get('degreeOrDiplomaOrCertificate', '')} – {h.get('institution', '')} ({h.get('yearPassed', '')})")
        story.append(Spacer(1, 6))

    work = doc.get("workExperience") or []
    if work:
        add_para("Work Experience", heading_style)
        for w in work:
            if isinstance(w, dict):
                pos = (w.get("position") or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                company = (w.get("companyName") or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                year = (w.get("year") or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                add_para(f"<b>{pos}</b> at {company} ({year})")
                add_para(w.get("description", ""))
        story.append(Spacer(1, 6))

    bio = doc.get("bio") or ""
    if bio:
        add_para("About", heading_style)
        add_para(bio)
        story.append(Spacer(1, 6))

    add_para("Contact", heading_style)
    c = doc.get("contact") or {}
    add_para(f"Address: {c.get('address', '')}")
    add_para(f"Email: {c.get('email', '')} | Phone: {c.get('contactNumber', '')}")
    story.append(Spacer(1, 6))

    refs = doc.get("references") or []
    if refs:
        add_para("References", heading_style)
        for r in refs:
            if isinstance(r, dict):
                add_para(f"{r.get('name', '')} – {r.get('relationship', '')}: {r.get('contactDetail', '')}")

    pdf = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20 * mm, leftMargin=20 * mm, topMargin=15 * mm, bottomMargin=15 * mm)
    pdf.build(story)
    return buffer.getvalue()


def _build_docx_bytes(doc: dict) -> bytes:
    """Render CV document to DOCX bytes."""
    try:
        from docx import Document
        from docx.shared import Pt
    except ImportError:
        raise RuntimeError("python-docx is required for DOCX generation. Install with: pip install python-docx")
    buffer = io.BytesIO()
    document = Document()
    style = document.styles["Normal"]
    style.font.size = Pt(11)

    def add_heading(text: str, level: int = 1):
        if text:
            document.add_heading(text, level=level)

    def add_para(text: str):
        if text:
            document.add_paragraph(text)

    p = doc.get("particulars") or {}
    name = f"{p.get('name', '')} {p.get('surname', '')}".strip() or "CV"
    add_heading(name, 0)
    add_para(f"DOB: {p.get('dateOfBirth', '')} | Nationality: {p.get('nationality', '')} | ID: {p.get('idNumber', '')} | Gender: {p.get('gender', '')}")
    if p.get("taxNumber"):
        add_para(f"Tax number: {p.get('taxNumber')}")
    add_para(f"Criminal record: {'Yes' if p.get('hasCriminalRecord') else 'No'}")

    add_heading("Education", level=1)
    e = doc.get("education") or {}
    add_para(f"High school: {e.get('highSchoolName', '')}. Highest grade: {e.get('highestGradePassed', '')}. Matriculated: {'Yes' + (' (' + str(e.get('matriculationYear', '')) + ')' if e.get('matriculationYear') else '') if e.get('matriculated') else 'No'}.")

    higher = doc.get("higherEducation") or []
    if higher:
        add_heading("Higher Education", level=1)
        for h in higher:
            if isinstance(h, dict):
                add_para(f"{h.get('degreeOrDiplomaOrCertificate', '')} – {h.get('institution', '')} ({h.get('yearPassed', '')})")

    work = doc.get("workExperience") or []
    if work:
        add_heading("Work Experience", level=1)
        for w in work:
            if isinstance(w, dict):
                document.add_paragraph()
                add_para(f"{w.get('position', '')} at {w.get('companyName', '')} ({w.get('year', '')})")
                add_para(w.get("description", ""))

    bio = doc.get("bio") or ""
    if bio:
        add_heading("About", level=1)
        add_para(bio)

    add_heading("Contact", level=1)
    c = doc.get("contact") or {}
    add_para(f"Address: {c.get('address', '')}")
    add_para(f"Email: {c.get('email', '')} | Phone: {c.get('contactNumber', '')}")

    refs = doc.get("references") or []
    if refs:
        add_heading("References", level=1)
        for r in refs:
            if isinstance(r, dict):
                add_para(f"{r.get('name', '')} – {r.get('relationship', '')}: {r.get('contactDetail', '')}")

    document.save(buffer)
    return buffer.getvalue()


def _upload_cv_and_get_url(wa_number: str, file_bytes: bytes, extension: str) -> str:
    """Upload bytes to cvs/{wa_number}/cv.{extension}, return signed URL (48h)."""
    wa = _normalize_wa(wa_number)
    bucket = _get_storage_bucket()
    blob_path = f"cvs/{wa}/cv.{extension}"
    blob = bucket.blob(blob_path)
    blob.upload_from_string(file_bytes, content_type="application/pdf" if extension == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    try:
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(hours=48),
            method="GET",
        )
        return url
    except Exception as e:
        logger.warning("generate_signed_url failed (%s), using public URL if available", e)
        return blob.public_url or blob_path


def generate_cv_pdf(wa_number: str) -> dict:
    """
    Generate a PDF CV from the user's saved CV data, upload it to Firebase Storage,
    update the CV doc with the download link, and return the link.
    Call only after all sections have been collected and save_cv_doc has been used.
    Returns { status, message, fileLink } or { status: "error", error_message: "..." }.
    """
    wa = _normalize_wa(wa_number)
    if not wa:
        return {"status": "error", "error_message": "wa_number required"}
    try:
        db = _get_db()
        ref = db.collection("cvs").document(wa)
        doc_snap = ref.get()
        if not doc_snap or not doc_snap.exists:
            return {"status": "error", "error_message": "No CV data found. Please complete the CV collection first."}
        doc = doc_snap.to_dict() or {}
        err = _validate_cv_for_generation(doc)
        if err:
            return {"status": "error", "error_message": err}
        pdf_bytes = _build_pdf_bytes(doc)
        file_link = _upload_cv_and_get_url(wa, pdf_bytes, "pdf")
        try:
            from google.cloud.firestore_v1 import SERVER_TIMESTAMP
        except ImportError:
            from google.cloud.firestore import SERVER_TIMESTAMP
        ref.set({"fileLink": file_link, "format": "pdf", "updatedAt": SERVER_TIMESTAMP}, merge=True)
        logger.info("generate_cv_pdf wa=%s success", wa[:6] + "***")
        return {"status": "success", "message": "Your CV (PDF) is ready.", "fileLink": file_link}
    except Exception as e:
        logger.exception("generate_cv_pdf failed: %s", e)
        return {"status": "error", "error_message": str(e)}


def generate_cv_docx(wa_number: str) -> dict:
    """
    Generate a Microsoft Word (DOCX) CV from the user's saved CV data, upload it to Firebase Storage,
    update the CV doc with the download link, and return the link.
    Call only after all sections have been collected. Returns { status, message, fileLink } or error.
    """
    wa = _normalize_wa(wa_number)
    if not wa:
        return {"status": "error", "error_message": "wa_number required"}
    try:
        db = _get_db()
        ref = db.collection("cvs").document(wa)
        doc_snap = ref.get()
        if not doc_snap or not doc_snap.exists:
            return {"status": "error", "error_message": "No CV data found. Please complete the CV collection first."}
        doc = doc_snap.to_dict() or {}
        err = _validate_cv_for_generation(doc)
        if err:
            return {"status": "error", "error_message": err}
        docx_bytes = _build_docx_bytes(doc)
        file_link = _upload_cv_and_get_url(wa, docx_bytes, "docx")
        try:
            from google.cloud.firestore_v1 import SERVER_TIMESTAMP
        except ImportError:
            from google.cloud.firestore import SERVER_TIMESTAMP
        ref.set({"fileLink": file_link, "format": "docx", "updatedAt": SERVER_TIMESTAMP}, merge=True)
        logger.info("generate_cv_docx wa=%s success", wa[:6] + "***")
        return {"status": "success", "message": "Your CV (Word) is ready.", "fileLink": file_link}
    except Exception as e:
        logger.exception("generate_cv_docx failed: %s", e)
        return {"status": "error", "error_message": str(e)}


# ---------- ADK FunctionTool wrappers ----------
get_cv_doc_tool = FunctionTool(get_cv_doc)
save_cv_doc_tool = FunctionTool(save_cv_doc)
generate_cv_pdf_tool = FunctionTool(generate_cv_pdf)
generate_cv_docx_tool = FunctionTool(generate_cv_docx)
