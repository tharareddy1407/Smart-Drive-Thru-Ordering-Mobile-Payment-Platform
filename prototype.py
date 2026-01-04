# prototype.py
# ✅ Drive-Thru Prototype (ONE person does POS + Agent in a single Cashier Console)
#
# ✅ Includes everything requested:
# 1) Lane code valid for 10 minutes
# 2) Lane code rotates AFTER successful connect/order creation
# 3) After customer clicks “I’m Here”, POPUP asks: “Please enter the code to connect with agent”
# 4) Clear “✅ Connected” banner after connect
# 5) Voice-to-text ordering (browser SpeechRecognition)
# 6) Payment request -> customer chooses: saved cards / new card / Google Pay / PayPal / other wallet
# 7) Payment success popup: “✅ Payment done — move forward to pickup window”
# 8) ✅ Works on localhost AND hosted universal link (Render/Fly/Railway) because WS uses ws/wss auto-detect
#
# Pages:
# - Home:           /                 (links)
# - Customer:       /customer
# - Cashier:        /cashier
# - Lane Display:   /lane/L1 or /lane/L2
#
# Run local:
#   pip install "uvicorn[standard]" fastapi
#   uvicorn prototype:app --reload --host 0.0.0.0 --port 8000
#
# Deploy (Render):
#   startCommand: uvicorn prototype:app --host 0.0.0.0 --port $PORT

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from uuid import uuid4
from datetime import datetime, timedelta
from typing import Dict, List

app = FastAPI(title="Drive-Thru Voice Ordering + Easy Payment (Cashier Combined)")

# -----------------------------
# In-memory stores (use Redis/DB in production)
# -----------------------------
customer_home_ws: Dict[str, WebSocket] = {}         # customer_id -> ws (push-like events)
order_customer_ws: Dict[str, WebSocket] = {}        # order_id -> ws (order chat)
order_cashier_ws: Dict[str, WebSocket] = {}         # order_id -> ws (order chat)

lane_codes: Dict[str, dict] = {}                    # lane_id -> {code, expires_at}
checkins: Dict[str, dict] = {}                      # customer_id -> {lane_id, ts}

orders: Dict[str, dict] = {}                        # order_id -> order state
payments: Dict[str, dict] = {}                      # pay_session_id -> session state

customer_cards: Dict[str, List[dict]] = {}          # demo saved cards


# -----------------------------
# Helpers
# -----------------------------
def utcnow() -> datetime:
    return datetime.utcnow()


def ensure_demo_cards(customer_id: str) -> None:
    if customer_id in customer_cards:
        return
    customer_cards[customer_id] = [
        {"card_id": "card_demo_1", "brand": "VISA", "last4": "4242", "exp": "12/29"},
        {"card_id": "card_demo_2", "brand": "MASTERCARD", "last4": "4444", "exp": "08/28"},
    ]


def money(cents: int) -> str:
    return f"{cents/100:.2f}"


def rotate_lane_code(lane_id: str) -> dict:
    """Force a new code immediately; valid for 10 minutes."""
    code = f"{uuid4().int % 10000:04d}"  # 4-digit
    rec = {"lane_id": lane_id, "code": code, "expires_at": utcnow() + timedelta(minutes=10)}
    lane_codes[lane_id] = rec
    return rec


def current_lane_code(lane_id: str) -> dict:
    """Code stays valid for 10 minutes unless rotated earlier."""
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


# -----------------------------
# HTML PAGES
# -----------------------------
HOME_HTML = """
<!doctype html>
<html>
<head><meta charset="utf-8"/><title>Drive-Thru Demo</title></head>
<body style="font-family:Arial;margin:24px;">
  <h2>Drive-Thru Demo (Universal Link Ready)</h2>
  <ul>
    <li><a href="/customer">Customer Portal</a></li>
    <li><a href="/cashier">Cashier Console (POS + Agent)</a></li>
    <li>Lane display: <a href="/lane/L1">/lane/L1</a> or <a href="/lane/L2">/lane/L2</a></li>
  </ul>
  <p style="color:#666">Tip: Open Customer on phone and Cashier on laptop for best demo.</p>
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

CASHIER_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>Cashier Console</title>
  <style>
    body { font-family: Arial; margin: 24px; }
    .box { padding: 14px; border: 1px solid #ddd; border-radius: 10px; max-width: 980px; }
    .row { display:flex; gap:12px; }
    .col { flex:1; }
    select,input,textarea { padding:8px; width:100%; margin:6px 0 12px 0; }
    button { padding:10px 14px; cursor:pointer; margin-right:10px; margin-top:6px; }
    .pill { display:inline-block; padding:2px 8px; border:1px solid #ccc; border-radius:999px; font-size:12px; margin-left:8px; }
    .chat { background:#fff; border:1px solid #ddd; border-radius:10px; padding:10px; height:260px; overflow:auto; }
    .msg { margin:6px 0; }
    .msg b { display:inline-block; width:88px; }
    #log { white-space: pre-wrap; margin-top: 10px; background:#f7f7f7; padding:12px; border-radius:10px; }
    .muted { color:#666; font-size:12px; }
    .status { font-weight:bold; }
  </style>
</head>
<body>
  <h2>Cashier Console (POS + Agent)</h2>
  <div class="box">
    <div>
      <b>Cashier ID:</b> <span id="cashier"></span>
      <span id="wsState" class="pill">WS: idle</span>
      <span class="pill" id="joinedPill">No order joined</span>
    </div>

    <div class="row">
      <div class="col">
        <label>Orders:</label>
        <div class="row">
          <div class="col">
            <select id="orderSelect"></select>
          </div>
          <div class="col" style="flex:0.7">
            <button onclick="refreshOrders()">Refresh</button>
            <button onclick="joinSelected()">Join</button>
          </div>
        </div>

        <div class="chat" id="chat"></div>
        <input id="cashierMsg" placeholder="Message customer..." />
        <button onclick="sendCashierMsg()">Send</button>
      </div>

      <div class="col">
        <div class="muted">Order control</div>
        <label>Items (optional):</label>
        <textarea id="items" rows="6" placeholder="e.g., 1x Burger, 1x Fries, 1x Coke"></textarea>

        <label>Set Total (USD):</label>
        <input id="total" placeholder="e.g., 13.84" />

        <button onclick="confirmTotal()">Confirm Total & Send Payment</button>

        <div style="margin-top:10px;">
          <div class="muted">Current status:</div>
          <div class="status" id="statusLine">—</div>
        </div>
      </div>
    </div>

    <div id="log"></div>
  </div>

<script>
const WS_PROTO = location.protocol === "https:" ? "wss" : "ws";

const wsStateEl = document.getElementById("wsState");
const orderSelect = document.getElementById("orderSelect");
const chatEl = document.getElementById("chat");
const logEl = document.getElementById("log");
const joinedPill = document.getElementById("joinedPill");
const statusLine = document.getElementById("statusLine");

function log(line){ logEl.textContent += `[${new Date().toLocaleTimeString()}] ${line}\\n`; }
function chat(who, text){
  const div = document.createElement("div");
  div.className = "msg";
  div.innerHTML = `<b>${who}:</b> ${text}`;
  chatEl.appendChild(div);
  chatEl.scrollTop = chatEl.scrollHeight;
}

const cashierId = "cashier_" + (crypto.randomUUID ? crypto.randomUUID().slice(0,8) : Math.random().toString(36).slice(2,10));
document.getElementById("cashier").textContent = cashierId;

let orderWs = null;
let currentOrderId = null;

async function refreshOrders(){
  const res = await fetch("/cashier/orders");
  const data = await res.json();
  orderSelect.innerHTML = "";
  (data.orders || []).forEach(o => {
    const opt = document.createElement("option");
    opt.value = o.order_id;
    opt.textContent = `Order ${o.order_id} | lane=${o.lane_id} | status=${o.status} | total=$${(o.total_cents/100).toFixed(2)}`;
    orderSelect.appendChild(opt);
  });
  if (!data.orders?.length){
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "No orders yet";
    orderSelect.appendChild(opt);
  }
}
refreshOrders();

function joinSelected(){
  const oid = orderSelect.value;
  if (!oid) return alert("No order selected");
  joinOrder(oid);
}

function joinOrder(oid){
  if (orderWs) { try { orderWs.close(); } catch(e){} }
  currentOrderId = oid;
  chatEl.innerHTML = "";
  joinedPill.textContent = `Joined: ${oid}`;
  wsStateEl.textContent = "WS: connecting…";
  log(`Joining order ${oid}...`);

  orderWs = new WebSocket(`${WS_PROTO}://${location.host}/ws/order/${oid}/cashier?cashier_id=${encodeURIComponent(cashierId)}`);

  orderWs.onopen = () => { wsStateEl.textContent = "WS: connected"; log("Order WS connected"); };
  orderWs.onerror = () => { wsStateEl.textContent = "WS: error"; log("Order WS error"); };
  orderWs.onclose = () => { wsStateEl.textContent = "WS: closed"; log("Order WS closed"); };

  orderWs.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.type === "chat") chat(msg.from, msg.text);

    if (msg.type === "order_state") {
      statusLine.textContent = msg.status || "—";
      if (msg.items_text != null) document.getElementById("items").value = msg.items_text;
      if (msg.total_cents != null) document.getElementById("total").value = (msg.total_cents/100).toFixed(2);
      log(JSON.stringify(msg));
    }

    if (msg.type === "payment_status") {
      statusLine.textContent = `PAYMENT: ${msg.status} (${msg.payment_method || "n/a"})`;
      chat("SYSTEM", `Payment ${msg.status}. Method: ${msg.payment_method || "n/a"}`);
      log(JSON.stringify(msg));
    }
  };
}

function sendCashierMsg(){
  if (!orderWs || !currentOrderId) return;
  const text = document.getElementById("cashierMsg").value.trim();
  if (!text) return;
  orderWs.send(JSON.stringify({type:"chat", from:"CASHIER", text}));
  document.getElementById("cashierMsg").value = "";
}

async function confirmTotal(){
  if (!currentOrderId) return alert("Join an order first");
  const items_text = document.getElementById("items").value.trim();
  const total = parseFloat(document.getElementById("total").value.trim());
  if (!Number.isFinite(total) || total <= 0) return alert("Enter a valid total like 13.84");

  const res = await fetch(`/cashier/order/${currentOrderId}/confirm_total`, {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body: JSON.stringify({ items_text, total_cents: Math.round(total*100) })
  });
  const data = await res.json();
  if (data.error) return alert(data.error);
  statusLine.textContent = "Payment request sent to customer…";
  chat("SYSTEM", "Payment request sent to customer.");
  refreshOrders();
}
</script>
</body>
</html>
"""

CUSTOMER_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>Customer Portal</title>
  <style>
    body { font-family: Arial; margin: 24px; }
    .box { padding: 14px; border: 1px solid #ddd; border-radius: 10px; max-width: 900px; }
    .row { display:flex; gap:12px; }
    .col { flex:1; }
    input,select,textarea { padding:8px; width:100%; margin:6px 0 12px 0; }
    button { padding:10px 14px; cursor:pointer; margin-right:10px; margin-top:6px; }
    .pill { display:inline-block; padding:2px 8px; border:1px solid #ccc; border-radius:999px; font-size:12px; margin-left:8px; }
    .chat { background:#fff; border:1px solid #ddd; border-radius:10px; padding:10px; height:240px; overflow:auto; }
    .msg { margin:6px 0; }
    .msg b { display:inline-block; width:88px; }
    .section { margin-top:14px; padding-top:10px; border-top:1px solid #eee; }
    .muted { color:#666; font-size:12px; }
    .method { padding: 10px; border: 1px solid #ddd; border-radius: 10px; margin-top: 10px; background:#fff; }
    .divider { height:1px; background:#e5e5e5; margin:12px 0; }
    .bannerOk { display:none; margin-top:10px; padding:10px; border-radius:10px; border:1px solid #cce5cc; background:#f2fff2; font-weight:700; }
    .bannerErr { display:none; margin-top:10px; padding:10px; border-radius:10px; border:1px solid #f0c2c2; background:#fff2f2; font-weight:700; }
  </style>
</head>
<body>
  <h2>Customer Portal (Drive-Thru Mode)</h2>
  <div class="box">
    <div>
      <b>Customer ID:</b> <span id="cust"></span>
      <span id="wsState" class="pill">WS: connecting…</span>
    </div>

    <div id="toast" style="font-weight:bold; margin-top:10px;">Loading…</div>
    <div id="okBanner" class="bannerOk">✅ Connected to cashier. You can order now.</div>
    <div id="errBanner" class="bannerErr"></div>

    <div class="section">
      <h3>Step 1 — I’m here in Drive-Thru</h3>
      <div class="row">
        <div class="col">
          <label>Lane:</label>
          <select id="lane">
            <option value="L1">Lane L1</option>
            <option value="L2">Lane L2</option>
          </select>
        </div>
        <div class="col" style="flex:0.6">
          <label>&nbsp;</label>
          <button onclick="checkIn()">I’m Here</button>
        </div>
      </div>
      <div class="muted">After check-in, you’ll be prompted to enter the station code to connect.</div>
    </div>

    <div class="section">
      <h3>Step 2 — Enter Station Code</h3>
      <div class="row">
        <div class="col">
          <input id="code" placeholder="Enter 4-digit lane code (shown at station)" />
        </div>
        <div class="col" style="flex:0.6">
          <button onclick="connect()">Connect</button>
        </div>
      </div>
      <div class="muted">
        Lane display: /lane/L1 or /lane/L2 (code valid 10 minutes, rotates after successful connect)
      </div>
    </div>

    <div class="section">
      <h3>Step 3 — Order (Voice or Text)</h3>
      <div class="row">
        <div class="col">
          <div class="chat" id="chat"></div>
          <input id="custMsg" placeholder="Type your order..." />
          <div>
            <button onclick="sendText()">Send Text</button>
            <button onclick="startVoice()">🎙️ Voice to Text</button>
          </div>
          <div class="muted">Voice uses browser Speech-to-Text (Chrome best).</div>
        </div>
        <div class="col" style="flex:0.8">
          <div class="muted">Status:</div>
          <div id="status" style="font-weight:bold;">Not connected</div>
          <div class="muted" style="margin-top:10px;">After cashier confirms total, payment options appear.</div>
        </div>
      </div>
    </div>

    <div class="section">
      <h3>Step 4 — Payment</h3>
      <div id="paymentArea" class="muted">Waiting for cashier to confirm total…</div>
    </div>
  </div>

  <!-- ✅ POPUP after "I'm Here" -->
  <div id="codeModal" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.6);
       align-items:center; justify-content:center; z-index:9998;">
    <div style="background:#fff; border-radius:16px; padding:20px; width:min(520px, 92vw);
         box-shadow:0 10px 30px rgba(0,0,0,0.25);">
      <h3 style="margin:0 0 10px 0;">Connect to Cashier</h3>
      <div style="color:#333; margin-bottom:14px;">
        ✅ You're checked in. Please enter the <b>4-digit station code</b> to connect with the cashier.
      </div>
      <div style="display:flex; gap:10px;">
        <input id="codeModalInput" placeholder="Enter 4-digit code" style="padding:10px; flex:1;" />
        <button onclick="connectFromModal()" style="padding:10px 14px; cursor:pointer;">Connect</button>
      </div>
      <div style="display:flex; justify-content:flex-end; margin-top:12px;">
        <button onclick="closeCodeModal()" style="padding:8px 12px; cursor:pointer;">Close</button>
      </div>
    </div>
  </div>

  <!-- ✅ Payment success modal -->
  <div id="paidModal" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.6);
       align-items:center; justify-content:center; z-index:9999;">
    <div style="background:#fff; border-radius:16px; padding:22px; width:min(520px, 92vw);
         text-align:center; box-shadow:0 10px 30px rgba(0,0,0,0.25);">
      <div style="font-size:44px;">✅</div>
      <h2 style="margin:10px 0 6px 0;">Payment Completed</h2>
      <div id="paidText" style="font-size:16px; color:#333; margin:10px 0 18px 0;">
        Move forward to the pickup window to collect your order.
      </div>
      <button onclick="closePaidModal()" style="padding:10px 14px; cursor:pointer;">OK</button>
    </div>
  </div>

<script>
const WS_PROTO = location.protocol === "https:" ? "wss" : "ws";

const custEl = document.getElementById("cust");
const wsStateEl = document.getElementById("wsState");
const toastEl = document.getElementById("toast");
const okBanner = document.getElementById("okBanner");
const errBanner = document.getElementById("errBanner");
const chatEl = document.getElementById("chat");
const statusEl = document.getElementById("status");
const paymentArea = document.getElementById("paymentArea");

function clearBanners(){
  okBanner.style.display = "none";
  errBanner.style.display = "none";
  errBanner.textContent = "";
}
function showError(text){
  errBanner.textContent = "❌ " + text;
  errBanner.style.display = "block";
  okBanner.style.display = "none";
}
function showOk(text){
  okBanner.textContent = "✅ " + text;
  okBanner.style.display = "block";
  errBanner.style.display = "none";
}

function chat(who, text){
  const div = document.createElement("div");
  div.className = "msg";
  div.innerHTML = `<b>${who}:</b> ${text}`;
  chatEl.appendChild(div);
  chatEl.scrollTop = chatEl.scrollHeight;
}

// ✅ Code modal handlers
function openCodeModal(){
  const modal = document.getElementById("codeModal");
  const input = document.getElementById("codeModalInput");
  modal.style.display = "flex";
  input.value = "";
  setTimeout(() => input.focus(), 50);
}
function closeCodeModal(){
  document.getElementById("codeModal").style.display = "none";
}
function connectFromModal(){
  const v = document.getElementById("codeModalInput").value.trim();
  document.getElementById("code").value = v;
  closeCodeModal();
  connect();
}

// ✅ Payment modal handlers
function showPaidModal(text){
  document.getElementById("paidText").textContent = text;
  document.getElementById("paidModal").style.display = "flex";
}
function closePaidModal(){
  document.getElementById("paidModal").style.display = "none";
}

// Random customer id every load
const customerId = "cust_" + (crypto.randomUUID ? crypto.randomUUID().slice(0,8) : Math.random().toString(36).slice(2,10));
custEl.textContent = customerId;

let homeWs = null;
let orderWs = null;
let currentOrderId = null;
let paySessionId = null;

// Home WS for push payment request
homeWs = new WebSocket(`${WS_PROTO}://${location.host}/ws/customer/${customerId}`);
homeWs.onopen = () => { wsStateEl.textContent = "WS: connected"; toastEl.textContent="Connected. Step 1: Tap ‘I’m Here’."; };
homeWs.onerror = () => { wsStateEl.textContent = "WS: error"; toastEl.textContent="WebSocket error."; };
homeWs.onclose = () => { wsStateEl.textContent = "WS: closed"; toastEl.textContent="Disconnected. Refresh."; };

homeWs.onmessage = (ev) => {
  const msg = JSON.parse(ev.data);
  if (msg.type === "info") toastEl.textContent = msg.text;

  if (msg.type === "payment_request") {
    paySessionId = msg.pay_session_id;
    toastEl.textContent = "Payment request received — choose payment method.";
    renderPaymentUI(msg);
  }
};

async function checkIn(){
  clearBanners();
  const lane_id = document.getElementById("lane").value;

  const res = await fetch("/customer/checkin", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body: JSON.stringify({ customer_id: customerId, lane_id })
  });

  const data = await res.json();
  if (data.error) return showError(data.error);

  toastEl.textContent = `Checked in to ${data.lane_id}. Please enter the station code to connect.`;
  openCodeModal(); // ✅ popup
}

async function connect(){
  clearBanners();
  const lane_id = document.getElementById("lane").value;
  const code = document.getElementById("code").value.trim();
  if (!code) return showError("Enter the 4-digit code.");

  const res = await fetch("/customer/connect", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body: JSON.stringify({ customer_id: customerId, lane_id, code })
  });

  const data = await res.json();
  if (data.error) return showError(data.error);

  currentOrderId = data.order_id;
  statusEl.textContent = `Connected (Order ${currentOrderId})`;
  toastEl.textContent = "Connected. Start ordering.";
  showOk("Connected to cashier. You can order now.");
  joinOrderWs(currentOrderId);
}

function joinOrderWs(orderId){
  if (orderWs) { try { orderWs.close(); } catch(e){} }
  chatEl.innerHTML = "";
  orderWs = new WebSocket(`${WS_PROTO}://${location.host}/ws/order/${orderId}/customer?customer_id=${encodeURIComponent(customerId)}`);

  orderWs.onopen = () => chat("SYSTEM","Connected. Place your order.");
  orderWs.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.type === "chat") chat(msg.from, msg.text);
    if (msg.type === "order_state") statusEl.textContent = msg.status || statusEl.textContent;
    if (msg.type === "payment_status") {
      statusEl.textContent = "PAYMENT: " + msg.status;
      chat("SYSTEM", `Payment ${msg.status}. Method: ${msg.payment_method || "n/a"}`);
    }
  };
  orderWs.onerror = () => showError("Order connection error. Try reconnecting.");
}

function sendText(){
  if (!orderWs) return showError("Connect first (Step 2).");
  const text = document.getElementById("custMsg").value.trim();
  if (!text) return;
  orderWs.send(JSON.stringify({type:"chat", from:"CUSTOMER", text}));
  document.getElementById("custMsg").value = "";
}

function startVoice(){
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)){
    showError("Speech-to-text not supported. Use Chrome or type.");
    return;
  }
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const rec = new SR();
  rec.lang = "en-US";
  rec.interimResults = false;

  toastEl.textContent = "Listening… speak your order.";
  rec.onresult = (e) => {
    const text = e.results[0][0].transcript;
    document.getElementById("custMsg").value = text;
    toastEl.textContent = "Sending voice order…";
    sendText();
  };
  rec.onerror = () => showError("Voice capture failed. Try again.");
  rec.start();
}

// Payment UI
async function fetchCards(){
  const res = await fetch(`/customer/${customerId}/cards`);
  const data = await res.json();
  return data.cards || [];
}

function renderPaymentUI(msg){
  paymentArea.innerHTML = `
    <div><b>${msg.merchant_name}</b></div>
    <div>Order: <b>${msg.order_id}</b></div>
    <div>Total: <b>$${(msg.amount_cents/100).toFixed(2)} ${msg.currency}</b></div>

    <div class="method">
      <h4>Saved Card</h4>
      <select id="savedCardSelect"><option>Loading…</option></select>
      <button onclick="paySaved()">Pay</button>
    </div>

    <div class="method">
      <h4>Add New Card</h4>
      <div class="muted">Demo only (no real charge).</div>
      <div class="row">
        <div class="col"><input id="newCardNumber" placeholder="Card number (e.g., 4242...)" /></div>
        <div class="col"><input id="newCardExp" placeholder="MM/YY" /></div>
      </div>
      <div class="row">
        <div class="col"><input id="newCardName" placeholder="Name" /></div>
        <div class="col"><input id="newCardCvv" placeholder="CVV" /></div>
      </div>
      <button onclick="payNew()">Add & Pay</button>
    </div>

    <div class="method"><h4>Google Pay</h4><button onclick="payWallet('google_pay')">Pay with Google Pay</button></div>
    <div class="method"><h4>PayPal</h4><button onclick="payWallet('paypal')">Pay with PayPal</button></div>
    <div class="method"><h4>Other Wallet</h4><button onclick="payWallet('other_wallet')">Pay with Other Wallet</button></div>

    <div class="divider"></div>
    <button onclick="declinePay()">Decline</button>
  `;
  loadCards();
}

async function loadCards(){
  const sel = document.getElementById("savedCardSelect");
  if (!sel) return;
  const cards = await fetchCards();
  sel.innerHTML = "";
  if (!cards.length){
    const opt = document.createElement("option");
    opt.value = ""; opt.textContent = "No saved cards";
    sel.appendChild(opt);
    return;
  }
  for (const c of cards){
    const opt = document.createElement("option");
    opt.value = c.card_id;
    opt.textContent = `${c.brand} •••• ${c.last4} (exp ${c.exp})`;
    sel.appendChild(opt);
  }
}

async function paySaved(){
  const sel = document.getElementById("savedCardSelect");
  const card_id = sel ? sel.value : "";
  if (!card_id) return showError("Select a card.");
  await doPay({ mode:"saved_card", card_id });
}

async function payNew(){
  const number = (document.getElementById("newCardNumber")||{}).value || "";
  const exp = (document.getElementById("newCardExp")||{}).value || "";
  const name = (document.getElementById("newCardName")||{}).value || "";
  const cvv = (document.getElementById("newCardCvv")||{}).value || "";
  if (!number.trim() || !exp.trim() || !cvv.trim()) return showError("Enter number/exp/cvv.");
  await doPay({ mode:"new_card", new_card:{ number, exp, name, cvv }});
}

async function payWallet(mode){ await doPay({ mode }); }

async function declinePay(){
  const res = await fetch(`/payment/${paySessionId}/decline`, { method:"POST" });
  const data = await res.json();
  if (data.error) return showError(data.error);
  toastEl.textContent = "Declined: " + data.status;
}

async function doPay(payload){
  const res = await fetch(`/payment/${paySessionId}/pay`, {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body: JSON.stringify({ customer_id: customerId, ...payload })
  });
  const data = await res.json();
  if (data.error) return showError(data.error);

  toastEl.textContent = `Payment: ${data.status} (method: ${data.payment_method})`;

  if (data.status === "APPROVED"){
    showPaidModal("✅ Payment done — move forward to pickup window to pick up your order.");
  }
}
</script>
</body>
</html>
"""


# -----------------------------
# Routes
# -----------------------------
@app.get("/", response_class=HTMLResponse)
def home():
    return HTMLResponse(HOME_HTML)


@app.get("/lane/{lane_id}", response_class=HTMLResponse)
def lane(lane_id: str):
    lane_id = lane_id.upper()
    if lane_id not in ("L1", "L2"):
        return HTMLResponse("Use L1 or L2", status_code=400)

    rec = current_lane_code(lane_id)
    return HTMLResponse(LANE_HTML_TEMPLATE.format(
        lane_id=lane_id,
        code=rec["code"],
        expires_at=rec["expires_at"].strftime("%H:%M:%S UTC")
    ))


@app.get("/cashier", response_class=HTMLResponse)
def cashier_page():
    return HTMLResponse(CASHIER_HTML)


@app.get("/customer", response_class=HTMLResponse)
def customer_page():
    return HTMLResponse(CUSTOMER_HTML)


# -----------------------------
# WebSockets
# -----------------------------
@app.websocket("/ws/customer/{customer_id}")
async def ws_customer(ws: WebSocket, customer_id: str):
    await ws.accept()
    customer_home_ws[customer_id] = ws
    ensure_demo_cards(customer_id)
    try:
        await ws.send_json({"type": "info", "text": "Connected. Step 1: Tap ‘I’m Here’."})
        while True:
            # Keep socket alive; client doesn't need to send anything
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


# -----------------------------
# Customer APIs
# -----------------------------
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

    # ✅ Rotate lane code AFTER successful connect/order creation
    rotate_lane_code(lane_id)

    await push_customer(customer_id, {"type": "info", "text": f"Connected. Order {order_id} created. Start ordering."})
    return {"order_id": order_id, "status": orders[order_id]["status"]}


@app.get("/customer/{customer_id}/cards")
async def cards(customer_id: str):
    ensure_demo_cards(customer_id)
    return {"customer_id": customer_id, "cards": customer_cards.get(customer_id, [])}


# -----------------------------
# Cashier APIs
# -----------------------------
@app.get("/cashier/orders")
async def cashier_orders():
    out = []
    for o in orders.values():
        out.append({
            "order_id": o["order_id"],
            "lane_id": o["lane_id"],
            "status": o["status"],
            "total_cents": o["total_cents"] or 0,
        })
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

    await relay_order(order_id, {
        "type": "order_state",
        "status": o["status"],
        "items_text": items_text,
        "total_cents": total_cents,
    })
    await relay_order(order_id, {"type": "chat", "from": "CASHIER", "text": f"Total confirmed: ${money(total_cents)}. Please pay in the app."})

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

    await push_customer(o["customer_id"], {
        "type": "payment_request",
        "pay_session_id": pay_session_id,
        "order_id": order_id,
        "merchant_name": "DriveThru Demo",
        "amount_cents": total_cents,
        "currency": "USD",
    })

    return {"order_id": order_id, "pay_session_id": pay_session_id, "status": "PAYMENT_REQUESTED"}


# -----------------------------
# Payment APIs
# -----------------------------
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
        await relay_order(o["order_id"], {"type": "chat", "from": "SYSTEM", "text": "Payment declined. You can try again or pay at window."})

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
        customer_cards[customer_id].append({"card_id": f"card_{uuid4().hex[:8]}", "brand": brand, "last4": last4, "exp": exp})
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
        await relay_order(o["order_id"], {"type": "chat", "from": "SYSTEM", "text": "✅ Payment approved. Move forward to pickup window."})

    await relay_order(s["order_id"], {"type": "payment_status", "status": "APPROVED", "payment_method": s["payment_method"]})
    return {"pay_session_id": pay_session_id, "status": "APPROVED", "payment_method": s["payment_method"]}
