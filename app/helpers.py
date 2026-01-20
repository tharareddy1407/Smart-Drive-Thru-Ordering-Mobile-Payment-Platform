from datetime import datetime, timedelta
from uuid import uuid4
from . import state

def utcnow() -> datetime:
    return datetime.utcnow()

def money(cents: int) -> str:
    return f"{cents/100:.2f}"

def ensure_demo_cards(customer_id: str) -> None:
    if customer_id in state.customer_cards:
        return
    state.customer_cards[customer_id] = [
        {"card_id": "card_demo_1", "brand": "VISA", "last4": "4242", "exp": "12/29"},
        {"card_id": "card_demo_2", "brand": "MASTERCARD", "last4": "4444", "exp": "08/28"},
    ]

def rotate_lane_code(lane_id: str) -> dict:
    code = f"{uuid4().int % 10000:04d}"
    rec = {"lane_id": lane_id, "code": code, "expires_at": utcnow() + timedelta(minutes=10)}
    state.lane_codes[lane_id] = rec
    return rec

def current_lane_code(lane_id: str) -> dict:
    rec = state.lane_codes.get(lane_id)
    if rec and utcnow() < rec["expires_at"]:
        return rec
    return rotate_lane_code(lane_id)

async def push_customer(customer_id: str, payload: dict) -> bool:
    ws = state.customer_home_ws.get(customer_id)
    if not ws:
        return False
    await ws.send_json(payload)
    return True

async def relay_order(order_id: str, payload: dict) -> None:
    cws = state.order_customer_ws.get(order_id)
    pws = state.order_cashier_ws.get(order_id)
    if cws:
        await cws.send_json(payload)
    if pws:
        await pws.send_json(payload)

async def relay_call(order_id: str, sender_role: str, payload: dict) -> None:
    peers = state.call_ws.get(order_id) or {}
    target_role = "cashier" if sender_role == "customer" else "customer"
    target_ws = peers.get(target_role)
    if target_ws:
        await target_ws.send_json(payload)
