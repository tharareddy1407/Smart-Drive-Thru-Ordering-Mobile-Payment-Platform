from typing import Dict, List
from fastapi import WebSocket

# In-memory stores (demo only)
customer_home_ws: Dict[str, WebSocket] = {}      # customer_id -> ws
order_customer_ws: Dict[str, WebSocket] = {}     # order_id -> ws
order_cashier_ws: Dict[str, WebSocket] = {}      # order_id -> ws

lane_codes: Dict[str, dict] = {}                 # lane_id -> {code, expires_at}
checkins: Dict[str, dict] = {}                   # customer_id -> {lane_id, ts}

orders: Dict[str, dict] = {}                     # order_id -> order
payments: Dict[str, dict] = {}                   # pay_session_id -> payment session

customer_cards: Dict[str, List[dict]] = {}       # customer_id -> list[card]

call_ws: Dict[str, Dict[str, WebSocket]] = {}    # order_id -> {"customer": ws, "cashier": ws}
