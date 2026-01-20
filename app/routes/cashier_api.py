from fastapi import APIRouter
from fastapi.responses import JSONResponse
from uuid import uuid4
from datetime import timedelta

from .. import state
from ..helpers import utcnow, relay_order, push_customer, money

router = APIRouter(prefix="/cashier", tags=["cashier"])

@router.get("/orders")
async def cashier_orders():
    out = []
    for o in state.orders.values():
        out.append(
            {
                "order_id": o["order_id"],
                "lane_id": o["lane_id"],
                "status": o["status"],
                "total_cents": o["total_cents"] or 0,
            }
        )
    out.sort(key=lambda x: x["order_id"], reverse=True)
    return {"orders": out}

@router.post("/order/{order_id}/confirm_total")
async def cashier_confirm_total(order_id: str, payload: dict):
    o = state.orders.get(order_id)
    if not o:
        return JSONResponse({"error": "order not found"}, status_code=404)

    items_text = str(payload.get("items_text", "")).strip()
    total_cents = int(payload.get("total_cents", 0))

    if total_cents <= 0:
        return JSONResponse({"error": "total_cents must be > 0"}, status_code=400)

    o["items_text"] = items_text
    o["total_cents"] = total_cents
    o["status"] = "TOTAL_CONFIRMED_WAITING_PAYMENT"

    await relay_order(order_id, {"type": "order_state", "status": o["status"], "items_text": items_text, "total_cents": total_cents})
    await relay_order(order_id, {"type": "chat", "from": "CASHIER", "text": f"Total confirmed: ${money(total_cents)}. Please pay in the app."})

    pay_session_id = f"pay_{uuid4().hex[:8]}"
    state.payments[pay_session_id] = {
        "pay_session_id": pay_session_id,
        "order_id": order_id,
        "customer_id": o["customer_id"],
        "amount_cents": total_cents,
        "currency": "USD",
        "merchant_name": "DriveThru Demo",
        "status": "PENDING",
        "payment_method": None,
        "expires_at": utcnow() + timedelta(minutes=5),
    }
    o["pay_session_id"] = pay_session_id

    await push_customer(
        o["customer_id"],
        {
            "type": "payment_request",
            "pay_session_id": pay_session_id,
            "order_id": order_id,
            "merchant_name": "DriveThru Demo",
            "amount_cents": total_cents,
            "currency": "USD",
        },
    )

    return {"order_id": order_id, "pay_session_id": pay_session_id, "status": "PAYMENT_REQUESTED"}
