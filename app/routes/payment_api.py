from fastapi import APIRouter
from fastapi.responses import JSONResponse
from uuid import uuid4

from .. import state
from ..helpers import utcnow, relay_order, ensure_demo_cards

router = APIRouter(prefix="/payment", tags=["payment"])

@router.post("/{pay_session_id}/decline")
async def payment_decline(pay_session_id: str):
    s = state.payments.get(pay_session_id)
    if not s:
        return JSONResponse({"error": "payment session not found"}, status_code=404)

    if s["status"] != "PENDING":
        return {"pay_session_id": pay_session_id, "status": s["status"]}

    s["status"] = "DECLINED"

    o = state.orders.get(s["order_id"])
    if o:
        o["status"] = "PAYMENT_DECLINED"
        await relay_order(o["order_id"], {"type": "order_state", "status": o["status"]})
        await relay_order(o["order_id"], {"type": "chat", "from": "SYSTEM", "text": "Payment declined. You can try again or pay at window."})

    await relay_order(s["order_id"], {"type": "payment_status", "status": "DECLINED", "payment_method": None})
    return {"pay_session_id": pay_session_id, "status": "DECLINED"}

@router.post("/{pay_session_id}/pay")
async def payment_pay(pay_session_id: str, payload: dict):
    s = state.payments.get(pay_session_id)
    if not s:
        return JSONResponse({"error": "payment session not found"}, status_code=404)

    customer_id = str(payload.get("customer_id", "")).strip()
    mode = str(payload.get("mode", "")).strip()

    if s["customer_id"] != customer_id:
        return JSONResponse({"error": "customer mismatch"}, status_code=403)

    if s["status"] != "PENDING":
        return {"pay_session_id": pay_session_id, "status": s["status"], "payment_method": s.get("payment_method")}

    if utcnow() > s["expires_at"]:
        s["status"] = "EXPIRED"
        return {"pay_session_id": pay_session_id, "status": "EXPIRED"}

    ensure_demo_cards(customer_id)

    if mode == "saved_card":
        card_id = str(payload.get("card_id", "")).strip()
        card = next((c for c in state.customer_cards.get(customer_id, []) if c["card_id"] == card_id), None)
        if not card:
            return JSONResponse({"error": "invalid saved card"}, status_code=400)
        s["payment_method"] = f"saved_card:{card['brand']}:{card['last4']}"

    elif mode == "new_card":
        nc = payload.get("new_card") or {}
        number = str(nc.get("number", "")).replace(" ", "")
        exp = str(nc.get("exp", "")).strip()
        cvv = str(nc.get("cvv", "")).strip()

        if len(number) < 12 or not exp or not cvv:
            return JSONResponse({"error": "new_card requires number, exp, cvv"}, status_code=400)

        last4 = number[-4:]
        brand = "VISA" if number.startswith("4") else "CARD"
        state.customer_cards[customer_id].append(
            {"card_id": f"card_{uuid4().hex[:8]}", "brand": brand, "last4": last4, "exp": exp}
        )
        s["payment_method"] = f"new_card:{brand}:{last4}"

    elif mode in ("google_pay", "paypal", "other_wallet"):
        s["payment_method"] = mode
    else:
        return JSONResponse({"error": "unsupported mode"}, status_code=400)

    s["status"] = "APPROVED"

    o = state.orders.get(s["order_id"])
    if o:
        o["status"] = "PAID_READY_FOR_PICKUP"
        await relay_order(o["order_id"], {"type": "order_state", "status": o["status"]})
        await relay_order(o["order_id"], {"type": "chat", "from": "SYSTEM", "text": "✅ Payment approved. Move forward to pickup window."})

    await relay_order(s["order_id"], {"type": "payment_status", "status": "APPROVED", "payment_method": s["payment_method"]})
    return {"pay_session_id": pay_session_id, "status": "APPROVED", "payment_method": s["payment_method"]}
