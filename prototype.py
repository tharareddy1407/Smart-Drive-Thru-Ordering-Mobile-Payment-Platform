from datetime import datetime, timedelta
from typing import Dict, List
from uuid import uuid4
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# -----------------------------------------------------------------------------
# App (✅ create app FIRST)
# -----------------------------------------------------------------------------
app = FastAPI(
    title="Smart Drive-Thru Ordering Platform (Real-Time Voice Ordering, Secure Lane Connection & Mobile Payment)"
)

# -----------------------------------------------------------------------------
# Static files (✅ serve background image from /static)
# Put your background image here:
#   ./static/bg.jpg   (or bg.png)
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

# ✅ Mount ALWAYS (so you notice issues early). If folder missing, create it.
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# -----------------------------------------------------------------------------
# In-memory stores (demo only)
# -----------------------------------------------------------------------------
# Customer “home” websocket for push-like notifications (payment requests, info)
customer_home_ws: Dict[str, WebSocket] = {}  # customer_id -> ws

# Order chat websockets (two parties)
order_customer_ws: Dict[str, WebSocket] = {}  # order_id -> ws
order_cashier_ws: Dict[str, WebSocket] = {}   # order_id -> ws

# Lane codes and check-ins
lane_codes: Dict[str, dict] = {}  # lane_id -> {code, expires_at}
checkins: Dict[str, dict] = {}    # customer_id -> {lane_id, ts}

# Orders + payments
orders: Dict[str, dict] = {}      # order_id -> order
payments: Dict[str, dict] = {}    # pay_session_id -> payment session

# Demo saved cards per customer
customer_cards: Dict[str, List[dict]] = {}  # customer_id -> list[card]

# -----------------------------------------------------------------------------
# ✅ WebRTC signaling websockets (server relays JSON between customer/cashier)
# -----------------------------------------------------------------------------
call_ws: Dict[str, Dict[str, WebSocket]] = {}  # order_id -> {"customer": ws, "cashier": ws}


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def utcnow() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.utcnow()


def money(cents: int) -> str:
    """Format cents to dollars (string). Example: 1384 -> '13.84'."""
    return f"{cents/100:.2f}"


def ensure_demo_cards(customer_id: str) -> None:
    """Seed demo saved cards for a customer (once)."""
    if customer_id in customer_cards:
        return
    customer_cards[customer_id] = [
        {"card_id": "card_demo_1", "brand": "VISA", "last4": "4242", "exp": "12/29"},
        {"card_id": "card_demo_2", "brand": "MASTERCARD", "last4": "4444", "exp": "08/28"},
    ]


def rotate_lane_code(lane_id: str) -> dict:
    """
    Force a new 4-digit code immediately.
    Code is valid for 10 minutes from creation.
    """
    code = f"{uuid4().int % 10000:04d}"
    rec = {"lane_id": lane_id, "code": code, "expires_at": utcnow() + timedelta(minutes=10)}
    lane_codes[lane_id] = rec
    return rec


def current_lane_code(lane_id: str) -> dict:
    """
    Return the current lane code if valid; otherwise rotate and return a new code.
    """
    rec = lane_codes.get(lane_id)
    if rec and utcnow() < rec["expires_at"]:
        return rec
    return rotate_lane_code(lane_id)


async def push_customer(customer_id: str, payload: dict) -> bool:
    """
    Send a JSON message to the customer's “home” websocket.
    Returns False if no websocket is connected for that customer.
    """
    ws = customer_home_ws.get(customer_id)
    if not ws:
        return False
    await ws.send_json(payload)
    return True


async def relay_order(order_id: str, payload: dict) -> None:
    """
    Broadcast a JSON message to both customer and cashier order websockets (if present).
    """
    cws = order_customer_ws.get(order_id)
    pws = order_cashier_ws.get(order_id)
    if cws:
        await cws.send_json(payload)
    if pws:
        await pws.send_json(payload)


async def relay_call(order_id: str, sender_role: str, payload: dict) -> None:
    """
    Relay a WebRTC signaling payload from one role to the other.
    Role must be 'customer' or 'cashier'.
    """
    peers = call_ws.get(order_id) or {}
    target_role = "cashier" if sender_role == "customer" else "customer"
    target_ws = peers.get(target_role)
    if target_ws:
        await target_ws.send_json(payload)


# ----------------------------------------------------------------------------
# HTML Pages
# ----------------------------------------------------------------------------
HOME_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Smart Drive-Thru Ordering Platform</title>

  <style>
    html, body { height: 100%; margin: 0; font-family: Arial, sans-serif; }

    /* ✅ Background stays visible and aligned */
    body {
      background: url('/static/Background.png?v=40') center top / cover no-repeat;
      background-color: #0b1220;
      overflow-x: hidden;
    }

    /* ✅ Layout: keep content at top area so bottom image doesn't feel misaligned */
    .page {
      min-height: 100vh;
      padding: 28px 18px;
      box-sizing: border-box;
      display: flex;
      justify-content: center;
      align-items: flex-start;
    }

    .wrap {
      width: min(1100px, 96vw);
      margin-top: 90px; /* pushes buttons below the SMART title */
      text-align: center;
    }

    .title {
      color: rgba(255,255,255,0.95);
      font-size: clamp(24px, 4vw, 44px);
      margin: 0 0 10px 0;
      text-shadow: 0 10px 30px rgba(0,0,0,0.55);
      letter-spacing: -0.6px;
    }

    .subtitle {
      margin: 0 auto 22px auto;
      max-width: 900px;
      color: rgba(255,255,255,0.88);
      font-size: clamp(14px, 2.2vw, 16px);
      line-height: 1.45;
      text-shadow: 0 10px 30px rgba(0,0,0,0.55);
    }

    /* ✅ Button row */
    .actions {
      display: flex;
      gap: 14px;
      justify-content: center;
      flex-wrap: wrap;
    }

    /* ✅ Big interactive glass buttons */
    .actionBtn {
      width: min(320px, 92vw);
      text-decoration: none;
      color: rgba(255,255,255,0.96);
      border-radius: 18px;
      padding: 16px 18px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;

      /* super transparent */
      background: rgba(255,255,255,0.10);
      border: 1px solid rgba(255,255,255,0.16);
      backdrop-filter: blur(22px) saturate(160%);
      -webkit-backdrop-filter: blur(22px) saturate(160%);
      box-shadow: 0 16px 40px rgba(0,0,0,0.18);

      transition: transform .12s ease, background .12s ease, border .12s ease, box-shadow .12s ease;
    }

    .actionBtn:hover {
      transform: translateY(-2px);
      background: rgba(255,255,255,0.14);
      border: 1px solid rgba(255,255,255,0.24);
      box-shadow: 0 22px 55px rgba(0,0,0,0.26);
    }

    .left {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 4px;
      text-align: left;
    }

    .labelRow {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .label {
      font-weight: 900;
      font-size: 18px;
      letter-spacing: -0.2px;
    }

    .pill {
      font-size: 12px;
      padding: 3px 10px;
      border-radius: 999px;
      background: rgba(0,0,0,0.14);
      border: 1px solid rgba(255,255,255,0.14);
      color: rgba(255,255,255,0.9);
    }

    .desc {
      font-size: 13px;
      color: rgba(255,255,255,0.82);
      line-height: 1.25;
    }

    .arrow {
      font-size: 22px;
      font-weight: 900;
      opacity: 0.9;
    }

    /* ✅ Lane chooser (modal) */
    .modalBack {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.55);
      align-items: center;
      justify-content: center;
      padding: 18px;
      z-index: 9999;
    }

    .modal {
      width: min(520px, 94vw);
      border-radius: 18px;
      padding: 18px;
      background: rgba(255,255,255,0.14);
      border: 1px solid rgba(255,255,255,0.18);
      backdrop-filter: blur(22px) saturate(160%);
      -webkit-backdrop-filter: blur(22px) saturate(160%);
      box-shadow: 0 22px 60px rgba(0,0,0,0.35);
      color: #fff;
    }

    .modalTitle {
      font-weight: 900;
      font-size: 18px;
      margin: 0 0 10px 0;
    }

    .laneBtns {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-top: 12px;
    }

    .laneBtn {
      text-decoration: none;
      color: rgba(255,255,255,0.96);
      padding: 12px 14px;
      border-radius: 14px;
      background: rgba(0,0,0,0.10);
      border: 1px solid rgba(255,255,255,0.16);
      text-align: center;
      font-weight: 900;
      transition: transform .12s ease, background .12s ease;
    }

    .laneBtn:hover {
      transform: translateY(-1px);
      background: rgba(0,0,0,0.18);
    }

    .modalFooter {
      display: flex;
      justify-content: flex-end;
      margin-top: 12px;
    }

    .closeBtn {
      background: rgba(0,0,0,0.18);
      border: 1px solid rgba(255,255,255,0.16);
      color: #fff;
      padding: 10px 12px;
      border-radius: 12px;
      cursor: pointer;
      font-weight: 800;
    }

    /* ✅ Mobile spacing */
    @media (max-width: 980px) {
      .wrap { margin-top: 60px; }
    }
  </style>
</head>

<body>
  <div class="page">
    <div class="wrap">
      <h1 class="title">Smart Drive-Thru Ordering Platform</h1>
      <p class="subtitle">
        Real-time voice ordering, secure lane-based connection, and mobile payment —
        all without opening the car window until pickup.
      </p>

      <div class="actions">
        <!-- Lane button opens lane picker -->
        <a class="actionBtn" href="#" onclick="openLanePicker(); return false;">
          <div class="left">
            <div class="labelRow">
              <div class="label">Lane</div>
              <div class="pill">Display</div>
            </div>
            <div class="desc">Open a lane screen to get the rotating station code.</div>
          </div>
          <div class="arrow">→</div>
        </a>

        <!-- Customer -->
        <a class="actionBtn" href="/customer">
          <div class="left">
            <div class="labelRow">
              <div class="label">Customer</div>
              <div class="pill">Mobile</div>
            </div>
            <div class="desc">Check-in, enter code, chat/call, and pay securely.</div>
          </div>
          <div class="arrow">→</div>
        </a>

        <!-- Cashier -->
        <a class="actionBtn" href="/cashier">
          <div class="left">
            <div class="labelRow">
              <div class="label">Cashier</div>
              <div class="pill">POS + Agent</div>
            </div>
            <div class="desc">Join order, confirm total, and request payment.</div>
          </div>
          <div class="arrow">→</div>
        </a>
      </div>
    </div>
  </div>

  <!-- Lane picker modal -->
  <div id="laneModal" class="modalBack" onclick="closeLanePicker(event)">
    <div class="modal" onclick="event.stopPropagation()">
      <div class="modalTitle">Choose a Lane</div>
      <div class="desc">Open the lane display to show the rotating 4-digit station code.</div>

      <div class="laneBtns">
        <a class="laneBtn" href="/lane/L1">Lane L1</a>
        <a class="laneBtn" href="/lane/L2">Lane L2</a>
      </div>

      <div class="modalFooter">
        <button class="closeBtn" onclick="closeLanePicker()">Close</button>
      </div>
    </div>
  </div>

  <script>
    function openLanePicker() {
      document.getElementById("laneModal").style.display = "flex";
    }
    function closeLanePicker(e) {
      document.getElementById("laneModal").style.display = "none";
    }
  </script>
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
    // Auto-refresh so the screen updates if/when the code rotates.
    setTimeout(()=>location.reload(), 5000);
  </script>
</body>
</html>
"""

# -----------------------------------------------------------------------------
# CASHIER UI
# - Join an order
# - Chat with customer
# - Confirm total -> send payment request
# - WebRTC voice call: Incoming call -> Accept/Reject/Hangup
# -----------------------------------------------------------------------------
CASHIER_HTML = r"""
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
    .callBox { margin-top:10px; padding:12px; border:1px solid #ddd; border-radius:12px; background:#fff; }
    .callBanner { display:none; padding:10px; border-radius:10px; border:1px solid #ffe0a3; background:#fff7e6; font-weight:700; }
    .callLive { display:none; padding:10px; border-radius:10px; border:1px solid #cce5cc; background:#f2fff2; font-weight:700; }
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

        <div class="callBox">
          <div class="muted">Voice Call (WebRTC)</div>
          <div id="incomingCall" class="callBanner">📞 Incoming call request…</div>
          <div id="liveCall" class="callLive">✅ Call connected (audio live)</div>
          <div style="margin-top:10px;">
            <button id="btnAccept" onclick="acceptCall()" disabled>Accept</button>
            <button id="btnReject" onclick="rejectCall()" disabled>Reject</button>
            <button id="btnHangup" onclick="hangupCall()" disabled>Hang up</button>
          </div>
          <audio id="remoteAudio" autoplay playsinline></audio>
          <div class="muted" style="margin-top:8px;">
            Mic permission is requested when you Accept.
          </div>
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

const incomingCallEl = document.getElementById("incomingCall");
const liveCallEl = document.getElementById("liveCall");
const btnAccept = document.getElementById("btnAccept");
const btnReject = document.getElementById("btnReject");
const btnHangup = document.getElementById("btnHangup");
const remoteAudio = document.getElementById("remoteAudio");

function log(line){ logEl.textContent += `[${new Date().toLocaleTimeString()}] ${line}\\n`; }
function chat(who, text){
  const div = document.createElement("div");
  div.className = "msg";
  div.innerHTML = `<b>${who}:</b> ${text}`;
  chatEl.appendChild(div);
  chatEl.scrollTop = chatEl.scrollHeight;
}

// Generate an ephemeral cashier ID for the demo session.
const cashierId = "cashier_" + (crypto.randomUUID ? crypto.randomUUID().slice(0,8) : Math.random().toString(36).slice(2,10));
document.getElementById("cashier").textContent = cashierId;

let orderWs = null;
let callSigWs = null;        // signaling websocket for WebRTC
let pc = null;               // RTCPeerConnection
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
  // Close previous sockets / call resources
  if (orderWs) { try { orderWs.close(); } catch(e){} }
  if (callSigWs) { try { callSigWs.close(); } catch(e){} }
  cleanupCallUI(true);

  currentOrderId = oid;
  chatEl.innerHTML = "";
  joinedPill.textContent = `Joined: ${oid}`;
  wsStateEl.textContent = "WS: connecting…";
  log(`Joining order ${oid}...`);

  // Order chat WS
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

  // Call signaling WS
  callSigWs = new WebSocket(`${WS_PROTO}://${location.host}/ws/call/${oid}/cashier`);
  callSigWs.onopen = () => log("Call signaling WS connected");
  callSigWs.onclose = () => log("Call signaling WS closed");
  callSigWs.onerror = () => log("Call signaling WS error");

  callSigWs.onmessage = async (ev) => {
    const msg = JSON.parse(ev.data);

    if (msg.type === "call_request") {
      incomingCallEl.style.display = "block";
      btnAccept.disabled = false;
      btnReject.disabled = false;
      chat("SYSTEM", "📞 Customer is requesting a voice call.");
      return;
    }

    if (msg.type === "webrtc_offer") {
      // Cashier is callee -> set remote offer, create/send answer.
      await ensurePeerConnection();
      await pc.setRemoteDescription(msg.offer);
      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);
      callSigWs.send(JSON.stringify({ type:"webrtc_answer", answer }));
      return;
    }

    if (msg.type === "webrtc_ice" && msg.candidate) {
      try { await pc?.addIceCandidate(msg.candidate); } catch(e) { log("ICE add error: " + e); }
      return;
    }

    if (msg.type === "hangup") {
      chat("SYSTEM", "Call ended.");
      cleanupCallUI(false);
      return;
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

// --------------------
// WebRTC Voice Call (Cashier as callee)
// --------------------
async function ensurePeerConnection(){
  if (pc) return;

  // STUN server helps with NAT traversal (demo-level).
  pc = new RTCPeerConnection({
    iceServers: [{ urls: "stun:stun.l.google.com:19302" }]
  });

  // Play the remote audio stream when received.
  pc.ontrack = (event) => {
    remoteAudio.srcObject = event.streams[0];
  };

  // Send ICE candidates to the customer via signaling.
  pc.onicecandidate = (event) => {
    if (event.candidate && callSigWs?.readyState === 1) {
      callSigWs.send(JSON.stringify({ type:"webrtc_ice", candidate: event.candidate }));
    }
  };

  // Request microphone and attach audio track(s).
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
  stream.getAudioTracks().forEach(t => pc.addTrack(t, stream));
}

function cleanupCallUI(fullReset){
  try { pc?.close(); } catch(e){}
  pc = null;

  incomingCallEl.style.display = "none";
  liveCallEl.style.display = "none";
  btnAccept.disabled = true;
  btnReject.disabled = true;
  btnHangup.disabled = true;
  remoteAudio.srcObject = null;

  if (fullReset){
    // Reserved for any future hard reset behavior.
  }
}

async function acceptCall(){
  if (!callSigWs || !currentOrderId) return;

  incomingCallEl.style.display = "none";
  liveCallEl.style.display = "block";
  btnHangup.disabled = false;
  btnAccept.disabled = true;
  btnReject.disabled = true;

  // Notify customer to start offer flow.
  callSigWs.send(JSON.stringify({ type:"call_accept" }));
  chat("SYSTEM", "✅ Call accepted. Connecting audio…");

  try {
    await ensurePeerConnection();
  } catch(e){
    chat("SYSTEM", "❌ Microphone permission denied or unavailable.");
    cleanupCallUI(false);
    callSigWs.send(JSON.stringify({ type:"hangup" }));
  }
}

function rejectCall(){
  if (!callSigWs) return;
  chat("SYSTEM", "Call rejected.");
  callSigWs.send(JSON.stringify({ type:"call_reject" }));
  cleanupCallUI(false);
}

function hangupCall(){
  if (!callSigWs) return;
  callSigWs.send(JSON.stringify({ type:"hangup" }));
  chat("SYSTEM", "Call ended.");
  cleanupCallUI(false);
}
</script>
</body>
</html>
"""

# -----------------------------------------------------------------------------
# CUSTOMER UI
# - Check-in & connect via lane code
# - Chat (text)
# - Initiate voice call (WebRTC) with agent
# - Payment selection UI
# -----------------------------------------------------------------------------
CUSTOMER_HTML = r"""
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
    .callLive { display:none; margin-top:10px; padding:10px; border-radius:10px; border:1px solid #cce5cc; background:#f2fff2; font-weight:700; }
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
      <div class="muted">After check-in, you'll be prompted to enter the station code to connect.</div>
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
      <h3>Step 3 — Order + Voice Call</h3>
      <div class="row">
        <div class="col">
          <div class="chat" id="chat"></div>
          <input id="custMsg" placeholder="Type your order..." />
          <div>
            <button onclick="sendText()">Send Text</button>
            <button onclick="requestCall()">📞 Call Agent</button>
            <button onclick="hangupCall()" id="btnHangup" disabled>Hang up</button>
          </div>

          <div id="callLive" class="callLive">✅ Call connected (audio live)</div>
          <audio id="remoteAudio" autoplay playsinline></audio>

          <div class="muted">Voice call uses WebRTC. Chrome recommended.</div>
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

  <!-- Code modal (shown after check-in) -->
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

  <!-- Payment success modal -->
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

const callLiveEl = document.getElementById("callLive");
const btnHangup = document.getElementById("btnHangup");
const remoteAudio = document.getElementById("remoteAudio");

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

// Code modal handlers
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

// Payment success modal handlers
function showPaidModal(text){
  document.getElementById("paidText").textContent = text;
  document.getElementById("paidModal").style.display = "flex";
}
function closePaidModal(){
  document.getElementById("paidModal").style.display = "none";
}

// Create a random customer ID per load (demo)
const customerId = "cust_" + (crypto.randomUUID ? crypto.randomUUID().slice(0,8) : Math.random().toString(36).slice(2,10));
custEl.textContent = customerId;

let homeWs = null;     // push notifications
let orderWs = null;    // order chat
let callSigWs = null;  // WebRTC signaling
let pc = null;         // RTCPeerConnection

let currentOrderId = null;
let paySessionId = null;

// Connect “home” websocket (push notifications like payment requests)
homeWs = new WebSocket(`${WS_PROTO}://${location.host}/ws/customer/${customerId}`);
homeWs.onopen = () => {
  wsStateEl.textContent = "WS: connected";
  toastEl.textContent = "Connected. Step 1: Tap ‘I’m Here’.";
};
homeWs.onerror = () => { wsStateEl.textContent = "WS: error"; toastEl.textContent = "WebSocket error."; };
homeWs.onclose = () => { wsStateEl.textContent = "WS: closed"; toastEl.textContent = "Disconnected. Refresh."; };

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
  openCodeModal();
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
  joinCallWs(currentOrderId);
}

function joinOrderWs(orderId){
  if (orderWs) { try { orderWs.close(); } catch(e){} }
  chatEl.innerHTML = "";

  orderWs = new WebSocket(`${WS_PROTO}://${location.host}/ws/order/${orderId}/customer?customer_id=${encodeURIComponent(customerId)}`);

  orderWs.onopen = () => chat("SYSTEM","Connected. Place your order.");
  orderWs.onerror = () => showError("Order connection error. Try reconnecting.");

  orderWs.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);

    if (msg.type === "chat") chat(msg.from, msg.text);
    if (msg.type === "order_state") statusEl.textContent = msg.status || statusEl.textContent;

    if (msg.type === "payment_status") {
      statusEl.textContent = "PAYMENT: " + msg.status;
      chat("SYSTEM", `Payment ${msg.status}. Method: ${msg.payment_method || "n/a"}`);
    }
  };
}

function sendText(){
  if (!orderWs) return showError("Connect first (Step 2).");
  const text = document.getElementById("custMsg").value.trim();
  if (!text) return;
  orderWs.send(JSON.stringify({type:"chat", from:"CUSTOMER", text}));
  document.getElementById("custMsg").value = "";
}

// --------------------
// WebRTC Voice Call (Customer as caller)
// --------------------
function joinCallWs(orderId){
  if (callSigWs) { try { callSigWs.close(); } catch(e){} }
  cleanupCallUI();

  callSigWs = new WebSocket(`${WS_PROTO}://${location.host}/ws/call/${orderId}/customer`);

  callSigWs.onopen = () => chat("SYSTEM", "Call channel ready.");
  callSigWs.onerror = () => chat("SYSTEM", "❌ Call channel error.");

  callSigWs.onmessage = async (ev) => {
    const msg = JSON.parse(ev.data);

    if (msg.type === "call_accept") {
      chat("SYSTEM", "✅ Cashier accepted. Starting call…");
      await startOffer();
      return;
    }
    if (msg.type === "call_reject") {
      chat("SYSTEM", "❌ Cashier rejected the call.");
      cleanupCallUI();
      return;
    }
    if (msg.type === "webrtc_answer") {
      await pc.setRemoteDescription(msg.answer);
      callLiveEl.style.display = "block";
      btnHangup.disabled = false;
      return;
    }
    if (msg.type === "webrtc_ice" && msg.candidate) {
      try { await pc?.addIceCandidate(msg.candidate); } catch(e) {}
      return;
    }
    if (msg.type === "hangup") {
      chat("SYSTEM", "Call ended.");
      cleanupCallUI();
      return;
    }
  };
}

function requestCall(){
  if (!callSigWs || callSigWs.readyState !== 1) return showError("Call channel not ready. Connect first.");
  chat("SYSTEM", "📞 Calling cashier…");
  callSigWs.send(JSON.stringify({ type:"call_request" }));
}

async function ensurePeerConnection(){
  if (pc) return;

  pc = new RTCPeerConnection({
    iceServers: [{ urls: "stun:stun.l.google.com:19302" }]
  });

  pc.ontrack = (event) => {
    remoteAudio.srcObject = event.streams[0];
  };

  pc.onicecandidate = (event) => {
    if (event.candidate && callSigWs?.readyState === 1) {
      callSigWs.send(JSON.stringify({ type:"webrtc_ice", candidate: event.candidate }));
    }
  };

  // Request mic and attach to peer connection
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
  stream.getAudioTracks().forEach(t => pc.addTrack(t, stream));
}

async function startOffer(){
  await ensurePeerConnection();
  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);
  callSigWs.send(JSON.stringify({ type:"webrtc_offer", offer }));
}

function hangupCall(){
  if (callSigWs?.readyState === 1) callSigWs.send(JSON.stringify({ type:"hangup" }));
  cleanupCallUI();
}

function cleanupCallUI(){
  try { pc?.close(); } catch(e){}
  pc = null;
  callLiveEl.style.display = "none";
  btnHangup.disabled = true;
  remoteAudio.srcObject = null;
}

// --------------------
// Payment UI (demo)
// --------------------
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


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    """Landing page with quick links."""
    return HTMLResponse(HOME_HTML)


@app.get("/lane/{lane_id}", response_class=HTMLResponse)
def lane(lane_id: str) -> HTMLResponse:
    """Lane display page showing the current 4-digit code for the lane."""
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
    """Cashier console (agent + POS controls)."""
    return HTMLResponse(CASHIER_HTML)


@app.get("/customer", response_class=HTMLResponse)
def customer_page() -> HTMLResponse:
    """Customer portal (drive-thru experience)."""
    return HTMLResponse(CUSTOMER_HTML)


# -----------------------------------------------------------------------------
# WebSockets
# -----------------------------------------------------------------------------
@app.websocket("/ws/customer/{customer_id}")
async def ws_customer(ws: WebSocket, customer_id: str):
    """
    Customer “home” websocket used for:
    - info banners / push updates
    - payment request delivery
    """
    await ws.accept()
    customer_home_ws[customer_id] = ws
    ensure_demo_cards(customer_id)

    try:
        await ws.send_json({"type": "info", "text": "Connected. Step 1: Tap ‘I’m Here’."})
        while True:
            # Client typically does not need to send anything
            # we keep the connection alive by receiving text
            await ws.receive_text()
    except WebSocketDisconnect:
        if customer_home_ws.get(customer_id) is ws:
            del customer_home_ws[customer_id]


@app.websocket("/ws/order/{order_id}/customer")
async def ws_order_customer(ws: WebSocket, order_id: str, customer_id: str):
    """
    Customer order websocket:
    - Validates order belongs to customer
    - Receives customer chat messages
    - Relays messages to cashier + customer
    """
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
    """
    Cashier order websocket:
    - Validates order exists
    - Marks order as cashier connected
    - Receives cashier chat messages
    - Relays messages to both sides
    """
    await ws.accept()

    o = orders.get(order_id)
    if not o:
        await ws.send_json({"type": "chat", "from": "SYSTEM", "text": "Order not found."})
        await ws.close()
        return

    order_cashier_ws[order_id] = ws
    o["status"] = "CASHIER_CONNECTED"

    # Push order state to both parties
    await relay_order(
        order_id,
        {
            "type": "order_state",
            "status": o["status"],
            "items_text": o.get("items_text", ""),
            "total_cents": o.get("total_cents"),
        },
    )

    # Send the last N messages to cashier when they join.
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
    """
    WebRTC signaling websocket:
    - role = 'customer' or 'cashier'
    - server relays JSON messages between peers:
      {type: call_request | call_accept | call_reject | webrtc_offer | webrtc_answer | webrtc_ice | hangup, ...}
    """
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
    """
    Customer check-in:
    - Stores lane selection for the customer
    - Enables connect step for that lane
    """
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
    """
    Customer connects using lane code:
    - Validates customer checked-in to the lane
    - Validates lane code is correct & not expired
    - Creates an order and rotates lane code immediately after success
    """
    customer_id = str(payload.get("customer_id", "")).strip()
    lane_id = str(payload.get("lane_id", "")).strip().upper()
    code = str(payload.get("code", "")).strip()

    if not customer_id or lane_id not in ("L1", "L2") or not code:
        return JSONResponse({"error": "customer_id, lane_id, and code required"}, status_code=400)

    # Customer must have checked-in to that lane first.
    ci = checkins.get(customer_id)
    if not ci or ci["lane_id"] != lane_id:
        return JSONResponse({"error": "Please click ‘I’m Here’ for this lane first."}, status_code=400)

    # Validate the current lane code.
    rec = current_lane_code(lane_id)
    if utcnow() >= rec["expires_at"]:
        return JSONResponse({"error": "Code expired. Enter the new code shown."}, status_code=400)
    if code != rec["code"]:
        return JSONResponse({"error": "Invalid code. Check the lane display and try again."}, status_code=400)

    # Create a new order.
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

    # Rotate lane code only after successful connect + order creation.
    rotate_lane_code(lane_id)

    await push_customer(customer_id, {"type": "info", "text": f"Connected. Order {order_id} created. Start ordering."})
    return {"order_id": order_id, "status": orders[order_id]["status"]}


@app.get("/customer/{customer_id}/cards")
async def cards(customer_id: str):
    """Return demo saved cards for the customer."""
    ensure_demo_cards(customer_id)
    return {"customer_id": customer_id, "cards": customer_cards.get(customer_id, [])}


# -----------------------------------------------------------------------------
# Cashier APIs
# -----------------------------------------------------------------------------
@app.get("/cashier/orders")
async def cashier_orders():
    """List orders for the cashier UI dropdown."""
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
    """
    Cashier confirms items + total:
    - Updates the order state
    - Creates a payment session
    - Pushes a payment request to the customer portal
    """
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

    # Create a payment session (demo).
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

    # Push payment request to customer.
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
    """Mark a pending payment session as declined."""
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
    """
    Process a demo payment:
    - Validates session, customer, expiry
    - Supports modes: saved_card, new_card, google_pay, paypal, other_wallet
    - Marks payment APPROVED and updates order status
    """
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

    # Approve (demo)
    s["status"] = "APPROVED"

    o = orders.get(s["order_id"])
    if o:
        o["status"] = "PAID_READY_FOR_PICKUP"
        await relay_order(o["order_id"], {"type": "order_state", "status": o["status"]})
        await relay_order(o["order_id"], {"type": "chat", "from": "SYSTEM", "text": "✅ Payment approved. Move forward to pickup window."})

    await relay_order(s["order_id"], {"type": "payment_status", "status": "APPROVED", "payment_method": s["payment_method"]})
    return {"pay_session_id": pay_session_id, "status": "APPROVED", "payment_method": s["payment_method"]}
