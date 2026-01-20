from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json

from .. import state
from ..helpers import utcnow, relay_order

router = APIRouter()

@router.websocket("/ws/order/{order_id}/customer")
async def ws_order_customer(ws: WebSocket, order_id: str, customer_id: str):
    await ws.accept()

    o = state.orders.get(order_id)
    if not o or o["customer_id"] != customer_id:
        await ws.send_json({"type": "chat", "from": "SYSTEM", "text": "Invalid order or customer mismatch."})
        await ws.close()
        return

    state.order_customer_ws[order_id] = ws
    await ws.send_json({"type": "order_state", "status": o["status"]})

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            if msg.get("type") == "chat":
                text = str(msg.get("text", "")).strip()
                if not text:
                    continue
                o["messages"].append({"from": "CUSTOMER", "text": text, "ts": utcnow().isoformat()})
                await relay_order(order_id, {"type": "chat", "from": "CUSTOMER", "text": text})
    except WebSocketDisconnect:
        if state.order_customer_ws.get(order_id) is ws:
            del state.order_customer_ws[order_id]

@router.websocket("/ws/order/{order_id}/cashier")
async def ws_order_cashier(ws: WebSocket, order_id: str, cashier_id: str):
    await ws.accept()

    o = state.orders.get(order_id)
    if not o:
        await ws.send_json({"type": "chat", "from": "SYSTEM", "text": "Order not found."})
        await ws.close()
        return

    state.order_cashier_ws[order_id] = ws
    o["status"] = "CASHIER_CONNECTED"

    await relay_order(order_id, {
        "type": "order_state",
        "status": o["status"],
        "items_text": o.get("items_text", ""),
        "total_cents": o.get("total_cents"),
    })

    for m in o["messages"][-25:]:
        await ws.send_json({"type": "chat", "from": m["from"], "text": m["text"]})

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            if msg.get("type") == "chat":
                text = str(msg.get("text", "")).strip()
                if not text:
                    continue
                o["messages"].append({"from": "CASHIER", "text": text, "ts": utcnow().isoformat()})
                await relay_order(order_id, {"type": "chat", "from": "CASHIER", "text": text})
    except WebSocketDisconnect:
        if state.order_cashier_ws.get(order_id) is ws:
            del state.order_cashier_ws[order_id]
