from datetime import datetime, timedelta
from typing import Dict, List
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles  # ✅ NEW

app = FastAPI(
    title="Smart Drive-Thru Ordering Platform (Real-Time Voice Ordering, Secure Lane Connection & Mobile Payment)"
)

# ✅ NEW: serve images/css/js from /static
# Put your image here: ./static/drive_thru_hero.png
app.mount("/static", StaticFiles(directory="static"), name="static")

# -----------------------------------------------------------------------------
# In-memory stores (demo only)
# -----------------------------------------------------------------------------
customer_home_ws: Dict[str, WebSocket] = {}  # customer_id -> ws
order_customer_ws: Dict[str, WebSocket] = {}  # order_id -> ws
order_cashier_ws: Dict[str, WebSocket] = {}   # order_id -> ws

lane_codes: Dict[str, dict] = {}  # lane_id -> {code, expires_at}
checkins: Dict[str, dict] = {}    # customer_id -> {lane_id, ts}

orders: Dict[str, dict] = {}      # order_id -> order
payments: Dict[str, dict] = {}    # pay_session_id -> payment session

customer_cards: Dict[str, List[dict]] = {}  # customer_id -> list[card]

# ✅ WebRTC signaling websockets (server relays JSON between customer/cashier)
call_ws: Dict[str, Dict[str, WebSocket]] = {}  # order_id -> {"customer": ws, "cashier": ws}


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def utcnow() -> datetime:
    return datetime.utcnow()


def money(cents: int) -> str:
    return f"{cents/100:.2f}"


def ensure_demo_cards(customer_id: str) -> None:
    if customer_id in customer_cards:
        return
    customer_cards[customer_id] = [
        {"card_id": "card_demo_1", "brand": "VISA", "last4": "4242", "exp": "12/29"},
        {"card_id": "card_demo_2", "brand": "MASTERCARD", "last4": "4444", "exp": "08/28"},
    ]


def rotate_lane_code(lane_id: str) -> dict:
    code = f"{uuid4().int % 10000:04d}"
    rec = {"lane_id": lane_id, "code": code, "expires_at": utcnow() + timedelta(minutes=10)}
    lane_codes[lane_id] = rec
    return rec


def current_lane_code(lane_id: str) -> dict:
    rec = lane_codes.get(lane_id)
    if rec and utcnow() < rec["expires_at"]:
        return rec
    return rotate_lane_code(lane_id)


async def push_customer(customer_id: str, payload: dict) -> bool:
    ws = customer_home_ws.get(customer_id)
    if not ws:
        return False
    await ws.send_json(payload)
    return True


async def relay_order(order_id: str, payload: dict) -> None:
    cws = order_customer_ws.get(order_id)
    pws = order_cashier_ws.get(order_id)
    if cws:
        await cws.send_json(payload)
    if pws:
        await pws.send_json(payload)


async def relay_call(order_id: str, sender_role: str, payload: dict) -> None:
    peers = call_ws.get(order_id) or {}
    target_role = "cashier" if sender_role == "customer" else "customer"
    target_ws = peers.get(target_role)
    if target_ws:
        await target_ws.send_json(payload)


# -----------------------------------------------------------------------------
# HTML Pages
# -----------------------------------------------------------------------------
# ✅ UPDATED: added hero image on main page
HOME_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>Smart Drive-Thru Ordering Platform</title>
</head>
<body style="font-family:Arial, sans-serif; margin:24px; max-width:900px;">

  <h2>Smart Drive-Thru Ordering Platform</h2>
  <p style="color:#444;">
    Real-time voice ordering, secure lane-based connection, and mobile payment —
    all without opening the car window until pickup.
  </p>

  <!-- ✅ Hero image -->
  <div style="margin:18px 0;">
    <img
      src="/static/drive_thru_hero.png"
      alt="Smart Drive-Thru Ordering Platform"
      style="
        width:100%;
        max-width:860px;
        border-radius:16px;
        box-shadow:0 12px 30px rgba(0,0,0,0.15);
        display:block;
      "
    />
    <div style="color:#666; font-size:13px; margin-top:6px;">
      Demo: Lane code → Customer connect → Cashier join → Voice/Chat → Payment
    </div>
  </div>

  <h3>Quick Demo Steps</h3>
  <ol>
    <li>Open a lane display to view the 4-digit station code.</li>
    <li>Open the Customer Portal, click <b>“I’m Here”</b>, and enter the lane code.</li>
    <li>Open the Cashier Console, refresh orders, and click <b>Join</b>.</li>
    <li>Customer places the order via chat or voice call.</li>
    <li>Cashier sends payment request → customer pays → order ready for pickup.</li>
  </ol>

  <h3>Demo Links</h3>
  <ul>
    <li><a href="/customer">Customer Portal</a></li>
    <li><a href="/cashier">Cashier Console (POS + Agent)</a></li>
    <li>Lane Display:
      <a href="/lane/L1">Lane L1</a> |
      <a href="/lane/L2">Lane L2</a>
    </li>
  </ul>

  <p style="color:#666; font-size:14px;">
    Tip: Use a phone for the Customer Portal and a laptop for the Cashier Console.<br/>
    WebRTC voice calls require HTTPS (or localhost) for microphone access.
  </p>

</body>
</html>
"""

LANE_HTML_TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>Lane {lane_id} Code</title>
  <style>
    body {{ font-family: Arial; margin: 24px; }}
    .big {{ font-size: 64px; font-weight: 800; letter-spacing: 6px; }}
    .box {{ padding: 18px; border: 1px solid #ddd; border-radius: 12px; max-width: 560px; }}
    .muted {{ color:#666; }}
  </style>
</head>
<body>
  <h2>Drive-Thru Station — Lane {lane_id}</h2>
  <div class="box">
    <div class="muted">Enter this code in the app to connect:</div>
    <div class="big">{code}</div>
    <div class="muted">Valid until: {expires_at}</div>
    <div class="muted">Code rotates after a successful connect (order created).</div>
  </div>
  <script>
    setTimeout(()=>location.reload(), 5000);
  </script>
</body>
</html>
"""

# -----------------------------------------------------------------------------
# (Keep your CASHIER_HTML and CUSTOMER_HTML exactly as you already have them)
# -----------------------------------------------------------------------------
# CASHIER_HTML = r""" ... """
# CUSTOMER_HTML = r""" ... """

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    return HTMLResponse(HOME_HTML)


@app.get("/lane/{lane_id}", response_class=HTMLResponse)
def lane(lane_id: str) -> HTMLResponse:
    lane_id = lane_id.upper()
    if lane_id not in ("L1", "L2"):
        return HTMLResponse("Use L1 or L2", status_code=400)

    rec = current_lane_code(lane_id)
    return HTMLResponse(
        LANE_HTML_TEMPLATE.format(
            lane_id=lane_id,
            code=rec["code"],
            expires_at=rec["expires_at"].strftime("%H:%M:%S UTC"),
        )
    )


@app.get("/cashier", response_class=HTMLResponse)
def cashier_page() -> HTMLResponse:
    return HTMLResponse(CASHIER_HTML)


@app.get("/customer", response_class=HTMLResponse)
def customer_page() -> HTMLResponse:
    return HTMLResponse(CUSTOMER_HTML)


# -----------------------------------------------------------------------------
# WebSockets
# -----------------------------------------------------------------------------
@app.websocket("/ws/customer/{customer_id}")
async def ws_customer(ws: WebSocket, customer_id: str):
    await ws.accept()
    customer_home_ws[customer_id] = ws
    ensure_demo_cards(customer_id)

    try:
        await ws.send_json({"type": "info", "text": "Connected. Step 1: Tap ‘I’m Here’."})
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        if customer_home_ws.get(customer_id) is ws:
            del customer_home_ws[customer_id]


@app.websocket("/ws/order/{order_id}/customer")
async def ws_order_customer(ws: WebSocket, order_id: str, customer_id: str):
    await ws.accept()

    o = orders.get(order_id)
    if not o or o["customer_id"] != customer_id:
        await ws.send_json({"type": "chat", "from": "SYSTEM", "text": "Invalid order or customer mismatch."})
        await ws.close()
        return

    order_customer_ws[order_id] = ws
    await ws.send_json({"type": "order_state", "status": o["status"]})

    try:
        while True:
            raw = await ws.receive_text()
            import json
            msg = json.loads(raw)

            if msg.get("type") == "chat":
                text = str(msg.get("text", "")).strip()
                if not text:
                    continue

                o["messages"].append({"from": "CUSTOMER", "text": text, "ts": utcnow().isoformat()})
                await relay_order(order_id, {"type": "chat", "from": "CUSTOMER", "text": text})
    except WebSocketDisconnect:
        if order_customer_ws.get(order_id) is ws:
            del order_customer_ws[order_id]


@app.websocket("/ws/order/{order_id}/cashier")
async def ws_order_cashier(ws: WebSocket, order_id: str, cashier_id: str):
    await ws.accept()

    o = orders.get(order_id)
    if not o:
        await ws.send_json({"type": "chat", "from": "SYSTEM", "text": "Order not found."})
        await ws.close()
        return

    order_cashier_ws[order_id] = ws
    o["status"] = "CASHIER_CONNECTED"

    await relay_order(
        order_id,
        {
            "type": "order_state",
            "status": o["status"],
            "items_text": o.get("items_text", ""),
            "total_cents": o.get("total_cents"),
        },
    )

    for m in o["messages"][-25:]:
        await ws.send_json({"type": "chat", "from": m["from"], "text": m["text"]})

    try:
        while True:
            raw = await ws.receive_text()
            import json
            msg = json.loads(raw)

            if msg.get("type") == "chat":
                text = str(msg.get("text", "")).strip()
                if not text:
                    continue

                o["messages"].append({"from": "CASHIER", "text": text, "ts": utcnow().isoformat()})
                await relay_order(order_id, {"type": "chat", "from": "CASHIER", "text": text})
    except WebSocketDisconnect:
        if order_cashier_ws.get(order_id) is ws:
            del order_cashier_ws[order_id]


@app.websocket("/ws/call/{order_id}/{role}")
async def ws_call_signaling(ws: WebSocket, order_id: str, role: str):
    role = role.strip().lower()
    if role not in ("customer", "cashier"):
        await ws.close()
        return

    await ws.accept()

    call_ws.setdefault(order_id, {})
    call_ws[order_id][role] = ws

    try:
        while True:
            data = await ws.receive_json()
            await relay_call(order_id, role, data)
    except WebSocketDisconnect:
        peers = call_ws.get(order_id) or {}
        if peers.get(role) is ws:
            del peers[role]
        if not peers:
            call_ws.pop(order_id, None)


# -----------------------------------------------------------------------------
# Customer APIs
# -----------------------------------------------------------------------------
@app.post("/customer/checkin")
async def customer_checkin(payload: dict):
    customer_id = str(payload.get("customer_id", "")).strip()
    lane_id = str(payload.get("lane_id", "")).strip().upper()

    if not customer_id:
        return JSONResponse({"error": "customer_id required"}, status_code=400)
    if lane_id not in ("L1", "L2"):
        return JSONResponse({"error": "lane_id must be L1 or L2"}, status_code=400)

    checkins[customer_id] = {"customer_id": customer_id, "lane_id": lane_id, "ts": utcnow().isoformat()}
    await push_customer(customer_id, {"type": "info", "text": f"Checked in to {lane_id}. Enter station code to connect."})
    return {"customer_id": customer_id, "lane_id": lane_id, "status": "CHECKED_IN"}


@app.post("/customer/connect")
async def customer_connect(payload: dict):
    customer_id = str(payload.get("customer_id", "")).strip()
    lane_id = str(payload.get("lane_id", "")).strip().upper()
    code = str(payload.get("code", "")).strip()

    if not customer_id or lane_id not in ("L1", "L2") or not code:
        return JSONResponse({"error": "customer_id, lane_id, and code required"}, status_code=400)

    ci = checkins.get(customer_id)
    if not ci or ci["lane_id"] != lane_id:
        return JSONResponse({"error": "Please click ‘I’m Here’ for this lane first."}, status_code=400)

    rec = current_lane_code(lane_id)
    if utcnow() >= rec["expires_at"]:
        return JSONResponse({"error": "Code expired. Enter the new code shown."}, status_code=400)
    if code != rec["code"]:
        return JSONResponse({"error": "Invalid code. Check the lane display and try again."}, status_code=400)

    order_id = f"ord_{uuid4().hex[:8]}"
    orders[order_id] = {
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
    return {"order_id": order_id, "status": orders[order_id]["status"]}


@app.get("/customer/{customer_id}/cards")
async def cards(customer_id: str):
    ensure_demo_cards(customer_id)
    return {"customer_id": customer_id, "cards": customer_cards.get(customer_id, [])}


# -----------------------------------------------------------------------------
# Cashier APIs
# -----------------------------------------------------------------------------
@app.get("/cashier/orders")
async def cashier_orders():
    out = []
    for o in orders.values():
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


@app.post("/cashier/order/{order_id}/confirm_total")
async def cashier_confirm_total(order_id: str, payload: dict):
    o = orders.get(order_id)
    if not o:
        return JSONResponse({"error": "order not found"}, status_code=404)

    items_text = str(payload.get("items_text", "")).strip()
    total_cents = int(payload.get("total_cents", 0))

    if total_cents <= 0:
        return JSONResponse({"error": "total_cents must be > 0"}, status_code=400)

    o["items_text"] = items_text
    o["total_cents"] = total_cents
    o["status"] = "TOTAL_CONFIRMED_WAITING_PAYMENT"

    await relay_order(
        order_id,
        {"type": "order_state", "status": o["status"], "items_text": items_text, "total_cents": total_cents},
    )
    await relay_order(
        order_id,
        {"type": "chat", "from": "CASHIER", "text": f"Total confirmed: ${money(total_cents)}. Please pay in the app."},
    )

    pay_session_id = f"pay_{uuid4().hex[:8]}"
    payments[pay_session_id] = {
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


# -----------------------------------------------------------------------------
# Payment APIs
# -----------------------------------------------------------------------------
@app.post("/payment/{pay_session_id}/decline")
async def payment_decline(pay_session_id: str):
    s = payments.get(pay_session_id)
    if not s:
        return JSONResponse({"error": "payment session not found"}, status_code=404)

    if s["status"] != "PENDING":
        return {"pay_session_id": pay_session_id, "status": s["status"]}

    s["status"] = "DECLINED"

    o = orders.get(s["order_id"])
    if o:
        o["status"] = "PAYMENT_DECLINED"
        await relay_order(o["order_id"], {"type": "order_state", "status": o["status"]})
        await relay_order(
            o["order_id"],
            {"type": "chat", "from": "SYSTEM", "text": "Payment declined. You can try again or pay at window."},
        )

    await relay_order(s["order_id"], {"type": "payment_status", "status": "DECLINED", "payment_method": None})
    return {"pay_session_id": pay_session_id, "status": "DECLINED"}


@app.post("/payment/{pay_session_id}/pay")
async def payment_pay(pay_session_id: str, payload: dict):
    s = payments.get(pay_session_id)
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
        card = next((c for c in customer_cards.get(customer_id, []) if c["card_id"] == card_id), None)
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
        customer_cards[customer_id].append(
            {"card_id": f"card_{uuid4().hex[:8]}", "brand": brand, "last4": last4, "exp": exp}
        )
        s["payment_method"] = f"new_card:{brand}:{last4}"

    elif mode in ("google_pay", "paypal", "other_wallet"):
        s["payment_method"] = mode

    else:
        return JSONResponse({"error": "unsupported mode"}, status_code=400)

    s["status"] = "APPROVED"

    o = orders.get(s["order_id"])
    if o:
        o["status"] = "PAID_READY_FOR_PICKUP"
        await relay_order(o["order_id"], {"type": "order_state", "status": o["status"]})
        await relay_order(
            o["order_id"],
            {"type": "chat", "from": "SYSTEM", "text": "✅ Payment approved. Move forward to pickup window."},
        )

    await relay_order(
        s["order_id"], {"type": "payment_status", "status": "APPROVED", "payment_method": s["payment_method"]}
    )
    return {"pay_session_id": pay_session_id, "status": "APPROVED", "payment_method": s["payment_method"]}
