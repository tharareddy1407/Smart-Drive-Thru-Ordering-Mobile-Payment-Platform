from fastapi import APIRouter
from fastapi.responses import JSONResponse
from uuid import uuid4

from .. import state
from ..helpers import utcnow, push_customer, current_lane_code, rotate_lane_code, ensure_demo_cards

router = APIRouter(prefix="/customer", tags=["customer"])

@router.post("/checkin")
async def customer_checkin(payload: dict):
    customer_id = str(payload.get("customer_id", "")).strip()
    lane_id = str(payload.get("lane_id", "")).strip().upper()

    if not customer_id:
        return JSONResponse({"error": "customer_id required"}, status_code=400)
    if lane_id not in ("L1", "L2"):
        return JSONResponse({"error": "lane_id must be L1 or L2"}, status_code=400)

    state.checkins[customer_id] = {"customer_id": customer_id, "lane_id": lane_id, "ts": utcnow().isoformat()}
    await push_customer(customer_id, {"type": "info", "text": f"Checked in to {lane_id}. Enter station code to connect."})
    return {"customer_id": customer_id, "lane_id": lane_id, "status": "CHECKED_IN"}

@router.post("/connect")
async def customer_connect(payload: dict):
    customer_id = str(payload.get("customer_id", "")).strip()
    lane_id = str(payload.get("lane_id", "")).strip().upper()
    code = str(payload.get("code", "")).strip()

    if not customer_id or lane_id not in ("L1", "L2") or not code:
        return JSONResponse({"error": "customer_id, lane_id, and code required"}, status_code=400)

    ci = state.checkins.get(customer_id)
    if not ci or ci["lane_id"] != lane_id:
        return JSONResponse({"error": "Please click ‘I’m Here’ for this lane first."}, status_code=400)

    rec = current_lane_code(lane_id)
    if utcnow() >= rec["expires_at"]:
        return JSONResponse({"error": "Code expired. Enter the new code shown."}, status_code=400)
    if code != rec["code"]:
        return JSONResponse({"error": "Invalid code. Check the lane display and try again."}, status_code=400)

    order_id = f"ord_{uuid4().hex[:8]}"
    state.orders[order_id] = {
        "order_id": order_id,
        "customer_id": customer_id,
        "lane_id": lane_id,
        "status": "CONNECTED_WAITING_CASHIER",
        "messages": [],
        "items_text": "",
        "total_cents": None,
        "created_at": utcnow().isoformat(),
        "pay_session_id": None,
    }

    rotate_lane_code(lane_id)

    await push_customer(customer_id, {"type": "info", "text": f"Connected. Order {order_id} created. Start ordering."})
    return {"order_id": order_id, "status": state.orders[order_id]["status"]}

@router.get("/{customer_id}/cards")
async def cards(customer_id: str):
    ensure_demo_cards(customer_id)
    return {"customer_id": customer_id, "cards": state.customer_cards.get(customer_id, [])}
