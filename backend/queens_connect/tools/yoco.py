"""
Yoco Checkout API client.
Creates checkouts via POST https://payments.yoco.com/api/checkouts and fetches status via GET same base + /{id}.
Uses config (YOCO_SECRET_KEY) for auth. See:
- https://developer.yoco.com/api-reference/checkout-api/checkout/create-checkout
"""
import logging
from typing import Any, Dict, Optional

import requests

from queens_connect import config as qc_config

logger = logging.getLogger("queens_connect.tools.yoco")

# Checkout API (secure payment page / redirect URL)
YOCO_CHECKOUTS_URL = "https://payments.yoco.com/api/checkouts"
YocoSecretKey = "sk_test_4755f59c8mYvz67ef274a8784581"

def _auth_headers(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Headers with Bearer token from config."""
    secret_key = (YocoSecretKey or "").strip()
    headers = {
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json",
    }
    if extra:
        headers.update(extra)
    return headers


def fetch_payment_link_status(payment_link_id: str) -> Dict[str, Any]:
    """
    Fetch a checkout's status from Yoco (GET /api/checkouts/{id}).
    Checkout status: created|started|processing|completed. Map completed → "paid", else → "pending".
    Returns { "status": "success", "yoco_status": "pending"|"paid", "id", "redirectUrl", ... } or error.
    """
    payment_link_id = (payment_link_id or "").strip()
    logger.info("fetch_payment_link_status: payment_link_id=%s", payment_link_id[:24] if payment_link_id else "(empty)")
    if not payment_link_id:
        logger.warning("fetch_payment_link_status: missing payment_link_id")
        return {"status": "error", "error_message": "payment_link_id required"}

    if not (YocoSecretKey or "").strip():
        logger.warning("fetch_payment_link_status: YOCO_SECRET_KEY not set")
        return {"status": "error", "error_message": "Yoco not configured"}

    url = f"{YOCO_CHECKOUTS_URL.rstrip('/')}/{payment_link_id}"
    logger.info("yoco GET %s", url)
    try:
        resp = requests.get(url, headers=_auth_headers(), timeout=15)
        data = resp.json() if resp.content else {}
        logger.info("yoco fetch response: status_code=%s body_keys=%s", resp.status_code, list(data.keys()) if isinstance(data, dict) else "n/a")
        if resp.status_code != 200:
            msg = data.get("message") or data.get("detail") or f"Yoco returned {resp.status_code}"
            logger.warning("yoco fetch checkout failed: status=%s body=%s", resp.status_code, data)
            return {"status": "error", "error_message": msg}
        # Checkout API: status = created|started|processing|completed
        raw_status = (data.get("status") or "created").lower()
        yoco_status = "paid" if raw_status == "completed" else "pending"
        logger.info("yoco checkout status: id=%s raw_status=%s yoco_status=%s", payment_link_id[:20], raw_status, yoco_status)
        out = {
            "status": "success",
            "yoco_status": yoco_status,
            "id": data.get("id"),
            "url": data.get("redirectUrl"),
            "redirectUrl": data.get("redirectUrl"),
            "order_id": data.get("paymentId"),
            "customer_reference": data.get("clientReferenceId"),
            "created_at": None,
            "updated_at": None,
        }
        logger.info("fetch_payment_link_status: returning success yoco_status=%s", yoco_status)
        return out
    except requests.RequestException as e:
        logger.exception("yoco fetch checkout request failed: %s", e)
        return {"status": "error", "error_message": str(e)}


def create_paylink(
    amount_cents: int,
    currency: str = "ZAR",
    external_transaction_id: str = "",
    description: str = "Unlock loan request",
    payment_reference: str = "",
    callback_url: str = "",
    success_page_url: str = "",
    failure_page_url: str = "",
    cancel_url: str = "",
    mode: str = "live",
    entity_id: str = "",
    requester_url: str = "",
) -> Dict[str, Any]:
    """
    Create a Yoco Checkout (POST /api/checkouts). Returns redirectUrl for the customer to pay.
    Returns { "status": "success", "paylinkUrl", "paylinkID", "externalTransactionID" } or error.
    """
    logger.info(
        "create_paylink: amount_cents=%s currency=%s description=%r external_txn_id=%s",
        amount_cents, currency, (description or "")[:60], (external_transaction_id or "")[:20] or "(none)",
    )
    if not (YocoSecretKey or "").strip():
        logger.warning("create_paylink: YOCO_SECRET_KEY not set", YocoSecretKey)
        return {"status": "error", "error_message": "Yoco not configured"}

    # Checkout API: amount (integer cents), currency, optional success/cancel/failure URLs, clientReferenceId, externalId
    payload: Dict[str, Any] = {
        "amount": amount_cents,
        "currency": currency,
    }
    if success_page_url:
        payload["successUrl"] = success_page_url
    if cancel_url:
        payload["cancelUrl"] = cancel_url
    if failure_page_url:
        payload["failureUrl"] = failure_page_url
    client_ref = (payment_reference or external_transaction_id or "Queens Connect")[:64]
    payload["clientReferenceId"] = client_ref
    if external_transaction_id:
        payload["externalId"] = external_transaction_id

    # Idempotency-Key to avoid duplicate checkouts when retrying
    idem_key = (external_transaction_id or "").strip() or None
    headers = _auth_headers({"Idempotency-Key": idem_key} if idem_key else None)

    logger.info(
        "yoco create_checkout payload: amount=%s currency=%s clientReferenceId=%s externalId=%s",
        amount_cents, currency, client_ref[:24], (external_transaction_id or "")[:20] or "(none)",
    )
    try:
        logger.info("yoco POST %s (amount=%s cents)", YOCO_CHECKOUTS_URL, amount_cents)
        resp = requests.post(
            YOCO_CHECKOUTS_URL,
            json=payload,
            headers=headers,
            timeout=15,
        )
        data = resp.json() if resp.content else {}
        logger.info(
            "yoco create response: status_code=%s body_keys=%s",
            resp.status_code,
            list(data.keys()) if isinstance(data, dict) else "n/a",
        )

        if resp.status_code not in (200, 201):
            msg = data.get("message") or data.get("detail") or f"Yoco returned {resp.status_code}"
            logger.warning("yoco create checkout failed: status=%s body=%s", resp.status_code, data)
            return {"status": "error", "error_message": msg}

        # Checkout API returns redirectUrl (URL to send the user to), id (checkout id)
        paylink_url = data.get("redirectUrl")
        paylink_id = data.get("id")
        if not paylink_url:
            logger.warning("yoco create response missing redirectUrl; full body keys=%s", list(data.keys()) if isinstance(data, dict) else "n/a")
            return {"status": "error", "error_message": "Yoco response missing redirect URL"}

        logger.info(
            "yoco checkout created: id=%s redirectUrl=%s... external_txn_id=%s",
            paylink_id,
            (paylink_url or "")[:50],
            (external_transaction_id or "")[:16],
        )
        return {
            "status": "success",
            "paylinkUrl": paylink_url,
            "paylinkID": paylink_id or "",
            "externalTransactionID": external_transaction_id,
        }
    except requests.RequestException as e:
        logger.exception("yoco create checkout request failed: %s", e)
        return {"status": "error", "error_message": str(e)}
