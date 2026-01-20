from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from .. import state
from ..helpers import relay_call

router = APIRouter()

@router.websocket("/ws/call/{order_id}/{role}")
async def ws_call_signaling(ws: WebSocket, order_id: str, role: str):
    role = role.strip().lower()
    if role not in ("customer", "cashier"):
        await ws.close()
        return

    await ws.accept()

    state.call_ws.setdefault(order_id, {})
    state.call_ws[order_id][role] = ws

    try:
        while True:
            data = await ws.receive_json()
            await relay_call(order_id, role, data)
    except WebSocketDisconnect:
        peers = state.call_ws.get(order_id) or {}
        if peers.get(role) is ws:
            del peers[role]
        if not peers:
            state.call_ws.pop(order_id, None)
