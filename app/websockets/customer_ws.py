from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from .. import state
from ..helpers import ensure_demo_cards

router = APIRouter()

@router.websocket("/ws/customer/{customer_id}")
async def ws_customer(ws: WebSocket, customer_id: str):
    await ws.accept()
    state.customer_home_ws[customer_id] = ws
    ensure_demo_cards(customer_id)

    try:
        await ws.send_json({"type": "info", "text": "Connected. Step 1: Tap ‘I’m Here’."})
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        if state.customer_home_ws.get(customer_id) is ws:
            del state.customer_home_ws[customer_id]
