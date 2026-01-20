from datetime import datetime, timedelta
from typing import Dict, List
from uuid import uuid4
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="Smart Drive-Thru Ordering Platform (Real-Time Voice Ordering, Secure Lane Connection & Mobile Payment)"
)

# -----------------------------------------------------------------------------
# Paths + Static
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

# Ensure static dir exists (prevents startup crash on fresh deploy)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

VALID_LANES = {"L1", "L2"}

# -----------------------------------------------------------------------------
# In-memory stores (demo only)
# -----------------------------------------------------------------------------
customer_home_ws: Dict[str, WebSocket] = {}      # customer_id -> ws
order_customer_ws: Dict[str, WebSocket] = {}     # order_id -> ws
order_cashier_ws: Dict[str, WebSocket] = {}      # order_id -> ws

lane_codes: Dict[str, dict] = {}                 # lane_id -> {code, expires_at}
checkins: Dict[str, dict] = {}                   # customer_id -> {lane_id, ts}

orders: Dict[str, dict] = {}                     # order_id -> order
payments: Dict[str, dict] = {}                   # pay_session_id -> payment session

customer_cards: Dict[str, List[dict]] = {}       # customer_id -> list[card]

call_ws: Dict[str, Dict[str, WebSocket]] = {}    # order_id -> {"customer": ws, "cashier": ws}

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
    :root{
      --text: rgba(255,255,255,0.96);
      --muted: rgba(255,255,255,0.82);
      --shadow: 0 22px 70px rgba(0,0,0,0.28);
    }

    *{ box-sizing:border-box; margin:0; padding:0; }
    html, body{ height:100%; font-family: Arial, sans-serif; }

    body{
      background-color:#0b1220;
      background-image:
        linear-gradient(rgba(0,0,0,0.10), rgba(0,0,0,0.22)),
        url('/static/BG-desktop.png');
      background-repeat:no-repeat;
      background-size: contain;
      background-position: center center;
    }

    /* Mobile background */
    @media (max-width: 768px){
      body{
        background-image:
          linear-gradient(rgba(0,0,0,0.10), rgba(0,0,0,0.22)),
          url('/static/BG-mobile.png');
        background-size: contain;
        background-position: center top;
      }
    }

    .hero{
      min-height: 100svh;
      display:flex;
      flex-direction:column;
      align-items:center;
      justify-content:center;
      padding: 18px;
      text-align:center;
      position: relative;
    }

    /* Wrap buttons + popover together so we can close popover
       when the cursor leaves this whole area */
    .interactionArea{
      display:flex;
      flex-direction:column;
      align-items:center;
      justify-content:center;
      width: 100%;
    }

    .circleRow{
      display:flex;
      gap: 28px;
      flex-wrap: wrap;
      align-items:center;
      justify-content:center;
      margin-top: 130px;
    }

    .circleBtn{
      width: 160px;
      height: 160px;
      border-radius: 999px;

      border: 2px solid rgba(255,255,255,0.20);
      background: rgba(120,140,160,0.40);
      backdrop-filter: blur(10px) saturate(140%);
      -webkit-backdrop-filter: blur(10px) saturate(140%);

      color: var(--text);
      font-size: 22px;
      font-weight: 800;
      cursor: pointer;

      box-shadow: var(--shadow);
      transition: transform .16s ease, background .16s ease, border .16s ease;
    }

    .circleBtn:hover{
      transform: translateY(-4px) scale(1.03);
      background: rgba(120,140,160,0.55);
      border-color: rgba(255,255,255,0.28);
    }

    .popover{
      display:none;
      margin-top: 16px;
      width: min(680px, 92vw);
      padding: 14px 16px;
      border-radius: 16px;
      background: rgba(0,0,0,0.55);
      border: 1px solid rgba(255,255,255,0.16);
      color: rgba(255,255,255,0.90);
      box-shadow: var(--shadow);
      backdrop-filter: blur(12px) saturate(140%);
      -webkit-backdrop-filter: blur(12px) saturate(140%);
      line-height: 1.4;
      font-size: 16px;
    }
    .popover.show{ display:block; }

    .actions{
      margin-top: 10px;
      display:flex;
      gap: 10px;
      flex-wrap: wrap;
      justify-content:center;
    }

    .linkBtn{
      text-decoration:none;
      padding: 10px 14px;
      border-radius: 12px;
      font-weight: 800;
      color: rgba(255,255,255,0.92);
      background: rgba(255,255,255,0.10);
      border: 1px solid rgba(255,255,255,0.16);
      transition: transform .12s ease, background .12s ease;
    }
    .linkBtn:hover{
      transform: translateY(-1px);
      background: rgba(255,255,255,0.14);
    }

    .tip{
      position: absolute;
      bottom: 20px;
      left: 0;
      right: 0;
      padding: 0 14px;
      font-size: 14px;
      color: var(--muted);
      text-shadow: 0 10px 24px rgba(0,0,0,0.45);
    }

    @media (max-width: 520px){
      body{ overflow:auto; }

      .circleRow{
        margin-top: 160px;
        gap: 18px;
      }

      .circleBtn{
        width: 120px;
        height: 120px;
        font-size: 18px;
      }

      .tip{
        position: static;
        margin-top: 18px;
      }
    }
  </style>
</head>

<body>
  <div class="hero">

    <div class="interactionArea">
      <div class="circleRow">
        <button type="button" class="circleBtn" data-role="lane">Lane</button>
        <button type="button" class="circleBtn" data-role="customer">Customer</button>
        <button type="button" class="circleBtn" data-role="cashier">Cashier</button>
      </div>

      <div class="popover" id="infoBox"></div>
    </div>

    <div class="tip">
      Tip: Use phone for Customer and laptop for Cashier. WebRTC mic needs HTTPS (or localhost).
    </div>
  </div>

  <script>
    document.addEventListener("DOMContentLoaded", () => {
      const box = document.getElementById("infoBox");
      const buttons = document.querySelectorAll(".circleBtn");
      const area = document.querySelector(".interactionArea");

      function render(role){
        box.classList.add("show");

        if(role === "lane"){
          box.innerHTML = `
            <b>Lane:</b> Open a lane screen to get the rotating 4-digit station code.
            <div class="actions">
              <a class="linkBtn" href="/lane/L1" target="_blank" rel="noopener">Open Lane L1 →</a>
              <a class="linkBtn" href="/lane/L2" target="_blank" rel="noopener">Open Lane L2 →</a>
            </div>
          `;
        } else if(role === "customer"){
          box.innerHTML = `
            <b>Customer:</b> Check-in, enter code, chat/call with cashier, and pay securely.
            <div class="actions">
              <a class="linkBtn" href="/customer" target="_blank" rel="noopener">Open Customer Portal →</a>
            </div>
          `;
        } else if(role === "cashier"){
          box.innerHTML = `
            <b>Cashier:</b> Join the order, confirm total, and send payment request.
            <div class="actions">
              <a class="linkBtn" href="/cashier" target="_blank" rel="noopener">Open Cashier Console →</a>
            </div>
          `;
        }
      }

      function openRole(role){
        if(role === "lane"){
          // Default lane open on click (L1). User can still choose L2 from popover.
          window.open("/lane/L1", "_blank", "noopener,noreferrer");
        } else if(role === "customer"){
          window.open("/customer", "_blank", "noopener,noreferrer");
        } else if(role === "cashier"){
          window.open("/cashier", "_blank", "noopener,noreferrer");
        }
      }

      // Hover shows popover (desktop), click opens new tab
      buttons.forEach(btn => {
        btn.addEventListener("mouseenter", () => render(btn.dataset.role));
        btn.addEventListener("focus", () => render(btn.dataset.role)); // keyboard-friendly
        btn.addEventListener("click", () => openRole(btn.dataset.role));
      });

      // Hide popover when cursor leaves BOTH buttons and popover area
      area.addEventListener("mouseleave", () => box.classList.remove("show"));

      // Hide popover if user taps elsewhere (mobile/desktop)
      document.addEventListener("click", (e) => {
        if(!area.contains(e.target)){
          box.classList.remove("show");
        }
      });
    });
  </script>
</body>
</html>
"""




LANE_HTML_TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Lane __LANE_ID__</title>

  <style>
    :root{
      /* “big brand QSR” neutral base */
      --bgTop:#0b1220;
      --bgBottom:#0a0f1e;

      /* subtle multi-accent (gold/red/green) */
      --gold:#ffb703;
      --red:#ff4d6d;
      --green:#22c55e;

      --text: rgba(255,255,255,.96);
      --muted: rgba(255,255,255,.78);

      --card: rgba(255,255,255,.10);
      --stroke: rgba(255,255,255,.16);
      --shadow: 0 22px 70px rgba(0,0,0,.34);
      --radius: 22px;
    }

    *{ box-sizing:border-box; }
    html, body{ height:100%; }

    body{
      margin:0;
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial;
      color: var(--text);
      overflow:hidden;

      /* Clean modern QSR background (no photo) */
      background:
        radial-gradient(900px 520px at 15% 20%, rgba(255,183,3,.18), transparent 60%),
        radial-gradient(900px 520px at 85% 25%, rgba(34,197,94,.14), transparent 60%),
        radial-gradient(900px 520px at 55% 95%, rgba(255,77,109,.12), transparent 60%),
        linear-gradient(180deg, var(--bgTop), var(--bgBottom));
    }

    /* subtle texture (keeps it “premium” like KFC/Starbucks/McD screens) */
    .texture{
      position:absolute; inset:0;
      background-image: radial-gradient(rgba(255,255,255,.10) 1px, transparent 1px);
      background-size: 28px 28px;
      opacity:.14;
      pointer-events:none;
      mask-image: radial-gradient(700px 420px at 50% 35%, #000 45%, transparent 75%);
    }

    .wrap{
      position:relative;
      min-height:100vh;
      display:grid;
      place-items:center;
      padding: 22px;
    }

    .topbar{
      position:absolute;
      top: 18px; left: 18px; right: 18px;
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:12px;
    }

    .brandMark{
      display:flex;
      align-items:center;
      gap:10px;
      font-weight: 950;
      letter-spacing:.2px;
      opacity:.98;
    }

    /* “triple-dot” accent hint (gold/red/green) */
    .dots{
      display:flex;
      gap:6px;
      align-items:center;
    }
    .d{
      width:10px; height:10px; border-radius:999px;
      box-shadow: 0 0 0 6px rgba(255,255,255,.06);
    }
    .d.gold{ background: radial-gradient(circle at 30% 30%, #fff, var(--gold)); }
    .d.red{ background: radial-gradient(circle at 30% 30%, #fff, var(--red)); }
    .d.green{ background: radial-gradient(circle at 30% 30%, #fff, var(--green)); }

    .pill{
      display:inline-flex;
      align-items:center;
      gap:10px;
      padding:10px 14px;
      border-radius:999px;
      background: rgba(255,255,255,.10);
      border: 1px solid rgba(255,255,255,.16);
      backdrop-filter: blur(10px);
      box-shadow: 0 12px 28px rgba(0,0,0,.22);
      color: var(--muted);
      font-size: 14px;
    }

    .laneBadge{
      font-weight: 950;
      letter-spacing: .9px;
      padding: 6px 10px;
      border-radius: 999px;
      color: #111;
      background: linear-gradient(135deg, var(--gold), var(--green));
    }

    .card{
      width: min(920px, 100%);
      border-radius: var(--radius);
      background: var(--card);
      border: 1px solid var(--stroke);
      box-shadow: var(--shadow);
      backdrop-filter: blur(16px);
      overflow:hidden;
      position:relative;
    }

    .card::before{
      content:"";
      position:absolute; inset:-2px;
      background:
        radial-gradient(700px 220px at 15% 0%, rgba(255,183,3,.18), transparent 60%),
        radial-gradient(700px 220px at 90% 10%, rgba(34,197,94,.14), transparent 60%),
        radial-gradient(700px 220px at 50% 110%, rgba(255,77,109,.10), transparent 60%);
      pointer-events:none;
    }

    .inner{
      position:relative;
      padding: 32px;
      display:grid;
      grid-template-columns: 1.2fr .8fr;
      gap: 18px;
    }

    @media (max-width: 860px){
      .inner{ grid-template-columns: 1fr; padding: 22px; }
    }

    .title{
      margin:0 0 8px 0;
      font-size: 30px;
      letter-spacing:.2px;
    }

    .subtitle{
      margin:0 0 16px 0;
      color: var(--muted);
      line-height:1.5;
      font-size: 16px;
    }

    .codeBox{
      border-radius: 18px;
      padding: 18px;
      background: rgba(255,255,255,.94);
      color: #111;
      border: 1px solid rgba(0,0,0,.08);
      box-shadow: 0 18px 45px rgba(0,0,0,.22);
    }

    .codeLabel{
      display:flex; align-items:center; gap:10px;
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: .4px;
      color: rgba(0,0,0,.65);
      font-weight: 950;
      margin-bottom: 10px;
    }

    .pulse{
      width: 10px; height: 10px; border-radius:999px;
      background: var(--green);
      box-shadow: 0 0 0 0 rgba(34,197,94,.35);
      animation: pulse 1.6s ease-out infinite;
    }
    @keyframes pulse{
      0%{ box-shadow: 0 0 0 0 rgba(34,197,94,.38); }
      100%{ box-shadow: 0 0 0 14px rgba(34,197,94,0); }
    }

    .code{
      margin:0;
      font-weight: 950;
      letter-spacing: 12px;
      line-height: 1.05;
      font-size: clamp(58px, 7vw, 98px);
      word-break: break-word;
    }

    @media (max-width: 420px){
      .code{ letter-spacing: 6px; }
    }

    .meta{
      margin-top: 14px;
      display:flex;
      flex-wrap:wrap;
      gap: 10px;
      color: rgba(0,0,0,.68);
      font-size: 14px;
    }

    .metaItem{
      display:inline-flex;
      align-items:center;
      gap: 8px;
      padding: 10px 12px;
      border-radius: 14px;
      background: rgba(0,0,0,.05);
      border: 1px solid rgba(0,0,0,.08);
      font-weight: 800;
    }

    /* ✅ prevents “big clock icon” issue */
    .icon, .metaItem svg{
      width: 18px !important;
      height: 18px !important;
      flex: 0 0 18px;
      display:inline-block;
    }

    .right{
      display:grid;
      gap: 12px;
      align-content:start;
    }

    .panel{
      border-radius: 18px;
      padding: 16px;
      background: rgba(255,255,255,.10);
      border: 1px solid rgba(255,255,255,.14);
    }

    .panel h4{
      margin:0 0 8px 0;
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: .35px;
      color: rgba(255,255,255,.92);
    }

    .panel p{
      margin:0;
      color: var(--muted);
      line-height:1.45;
      font-size: 14px;
    }

    .footer{
      position:relative;
      padding: 14px 22px;
      border-top: 1px solid rgba(255,255,255,.10);
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap: 10px;
      color: rgba(255,255,255,.72);
      font-size: 13px;
    }

    .status{
      display:inline-flex;
      align-items:center;
      gap: 10px;
      font-weight: 950;
    }

    .statusDot{
      width: 10px; height: 10px; border-radius:999px;
      background: var(--green);
      box-shadow: 0 0 0 7px rgba(34,197,94,.18);
    }
  </style>
</head>

<body>
  <div class="texture"></div>

  <div class="wrap">
    <div class="topbar">
      <div class="brandMark">
        <div class="dots">
          <span class="d gold"></span>
          <span class="d red"></span>
          <span class="d green"></span>
        </div>
        <span>Drive-Thru Pairing</span>
      </div>
      <div class="pill">
        <span class="laneBadge">LANE __LANE_ID__</span>
        <span id="clock">--:--:--</span>
      </div>
    </div>

    <div class="card">
      <div class="inner">
        <div>
          <h2 class="title">Customer Pairing Code</h2>
          <p class="subtitle">Ask the customer to enter this code in the mobile app to connect to <b>Lane __LANE_ID__</b>.</p>

          <div class="codeBox">
            <div class="codeLabel"><span class="pulse"></span> Active code</div>
            <p class="code">__CODE__</p>

            <div class="meta">
              <div class="metaItem">
                <svg class="icon" viewBox="0 0 24 24" fill="none">
                  <path d="M12 8v5l3 2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                  <path d="M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" stroke="currentColor" stroke-width="2"/>
                </svg>
                <span>Expires at <b id="expiresLocal">--</b></span>
              </div>

              <div class="metaItem">
                <svg class="icon" viewBox="0 0 24 24" fill="none">
                  <path d="M4 12a8 8 0 1 0 8-8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                  <path d="M4 4v6h6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
                <span>Expires in <b id="expiresIn">--:--</b></span>
              </div>
            </div>

            <div style="margin-top:10px; color:rgba(0,0,0,.62); font-weight:700;">
              Code rotates after a successful connect (order created).
            </div>
          </div>
        </div>

        <div class="right">
          <div class="panel">
            <h4>How it works</h4>
            <p>Once the customer connects and an order is created, this code rotates automatically for the next vehicle.</p>
          </div>
          <div class="panel">
            <h4>Visibility tip</h4>
            <p>Keep this screen fullscreen for best readability in the lane.</p>
          </div>
        </div>
      </div>

      <div class="footer">
        <div class="status"><span class="statusDot"></span> READY</div>
        <div>Secure lane pairing</div>
      </div>
    </div>
  </div>

  <script>
    // Local clock
    const clockEl = document.getElementById("clock");
    function tickClock(){
      const d = new Date();
      clockEl.textContent = d.toLocaleTimeString([], {hour:"2-digit", minute:"2-digit", second:"2-digit"});
    }
    tickClock(); setInterval(tickClock, 1000);

    // Expiry (local time + countdown)
    const expiresIsoUtc = "__EXPIRES_AT__"; // ISO UTC like 2026-01-20T04:17:02Z
    const expiresDate = new Date(expiresIsoUtc);

    const expiresLocalEl = document.getElementById("expiresLocal");
    const expiresInEl = document.getElementById("expiresIn");

    function formatMMSS(sec){
      const s = Math.max(0, Math.floor(sec));
      const mm = String(Math.floor(s/60)).padStart(2,"0");
      const ss = String(s%60).padStart(2,"0");
      return `${mm}:${ss}`;
    }

    function updateExpiry(){
      if (isNaN(expiresDate.getTime())){
        expiresLocalEl.textContent = expiresIsoUtc;
        expiresInEl.textContent = "--:--";
        return;
      }

      expiresLocalEl.textContent = expiresDate.toLocaleTimeString([], {hour:"2-digit", minute:"2-digit", second:"2-digit"});
      const diffSec = (expiresDate.getTime() - Date.now()) / 1000;
      expiresInEl.textContent = formatMMSS(diffSec);

      if (diffSec <= 0) setTimeout(()=>location.reload(), 800);
    }

    updateExpiry();
    setInterval(updateExpiry, 1000);

    // Refresh for rotation updates
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
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <style>
    :root{
      --bg:#0b1020;
      --card:#111a33;
      --card2:#0f1730;
      --text:#e9ecf5;
      --muted:#a9b3d1;
      --line:rgba(255,255,255,.10);
      --good:#22c55e;
      --warn:#f59e0b;
      --bad:#ef4444;
      --accent:#7c3aed;
      --accent2:#06b6d4;
      --chip:rgba(255,255,255,.08);
      --shadow: 0 10px 30px rgba(0,0,0,.35);
      --radius:16px;
    }
    *{box-sizing:border-box}
    body{
      margin:0;
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial;
      color:var(--text);
      background:
        radial-gradient(1200px 700px at 20% -10%, rgba(124,58,237,.35), transparent 55%),
        radial-gradient(900px 600px at 90% 0%, rgba(6,182,212,.25), transparent 55%),
        radial-gradient(900px 700px at 60% 110%, rgba(34,197,94,.12), transparent 60%),
        var(--bg);
      padding:18px;
    }

    /* Top bar */
    .topbar{
      display:flex; align-items:center; justify-content:space-between;
      gap:12px; padding:14px 16px;
      background:linear-gradient(135deg, rgba(255,255,255,.06), rgba(255,255,255,.03));
      border:1px solid var(--line);
      border-radius:var(--radius);
      box-shadow:var(--shadow);
      position:sticky; top:12px; z-index:10;
      backdrop-filter: blur(10px);
    }
    .brand{
      display:flex; align-items:center; gap:10px;
    }
    .logo{
      width:38px; height:38px; border-radius:12px;
      background: linear-gradient(135deg, var(--accent), var(--accent2));
      box-shadow: 0 8px 24px rgba(124,58,237,.35);
    }
    .title{
      line-height:1.1;
    }
    .title h2{margin:0; font-size:16px; font-weight:800; letter-spacing:.2px;}
    .title .sub{margin-top:2px; font-size:12px; color:var(--muted);}
    .meta{
      display:flex; align-items:center; gap:10px; flex-wrap:wrap;
      justify-content:flex-end;
    }

    .chip{
      display:inline-flex; align-items:center; gap:8px;
      padding:7px 10px; border-radius:999px;
      background:var(--chip);
      border:1px solid var(--line);
      font-size:12px; color:var(--text);
      white-space:nowrap;
    }
    .dot{
      width:10px; height:10px; border-radius:50%;
      background: #64748b;
      box-shadow: 0 0 0 4px rgba(100,116,139,.15);
    }
    .dot.good{ background:var(--good); box-shadow:0 0 0 4px rgba(34,197,94,.15); }
    .dot.warn{ background:var(--warn); box-shadow:0 0 0 4px rgba(245,158,11,.15); }
    .dot.bad { background:var(--bad); box-shadow:0 0 0 4px rgba(239,68,68,.15); }

    /* Layout */
    .grid{
      margin-top:14px;
      display:grid;
      grid-template-columns: 1.3fr 1fr;
      gap:14px;
    }
    @media (max-width: 980px){
      .grid{grid-template-columns:1fr;}
      .topbar{position:static;}
    }

    .card{
      background:linear-gradient(180deg, rgba(255,255,255,.05), rgba(255,255,255,.03));
      border:1px solid var(--line);
      border-radius:var(--radius);
      box-shadow:var(--shadow);
      overflow:hidden;
    }
    .cardHeader{
      display:flex; align-items:center; justify-content:space-between;
      padding:12px 14px;
      border-bottom:1px solid var(--line);
      background: rgba(255,255,255,.03);
    }
    .cardHeader .h{
      font-size:13px; font-weight:800; letter-spacing:.2px;
    }
    .cardBody{ padding:14px; }

    label{ display:block; font-size:12px; color:var(--muted); margin:10px 0 6px; }
    select,input,textarea{
      width:100%;
      padding:10px 12px;
      border-radius:12px;
      border:1px solid var(--line);
      background: rgba(0,0,0,.25);
      color:var(--text);
      outline:none;
    }
    textarea{ min-height:120px; resize:vertical; }

    .row{ display:flex; gap:10px; align-items:center; }
    .row > *{ flex:1; }
    .row.tight > *{ flex:0 0 auto; }

    button{
      padding:10px 12px;
      border-radius:12px;
      border:1px solid var(--line);
      background: rgba(255,255,255,.06);
      color:var(--text);
      cursor:pointer;
      font-weight:700;
      transition:.15s ease;
      white-space:nowrap;
    }
    button:hover{ transform: translateY(-1px); background: rgba(255,255,255,.08); }
    button:disabled{ opacity:.45; cursor:not-allowed; transform:none; }

    .btnPrimary{
      background: linear-gradient(135deg, rgba(124,58,237,.95), rgba(6,182,212,.75));
      border: none;
      box-shadow: 0 10px 24px rgba(124,58,237,.25);
    }
    .btnDanger{
      background: rgba(239,68,68,.12);
      border-color: rgba(239,68,68,.35);
    }
    .btnGhost{
      background: transparent;
    }
    .helper{ font-size:12px; color:var(--muted); margin-top:6px; }

    /* Order summary */
    .summary{
      display:grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap:10px;
      margin-top:10px;
    }
    .stat{
      padding:10px 12px;
      border:1px solid var(--line);
      border-radius:14px;
      background: rgba(0,0,0,.20);
    }
    .stat .k{ font-size:11px; color:var(--muted); }
    .stat .v{ margin-top:4px; font-weight:900; font-size:14px; }

    /* Chat */
    .chat{
      height:320px;
      overflow:auto;
      padding:10px;
      border-radius:14px;
      border:1px solid var(--line);
      background: rgba(0,0,0,.20);
    }
    .bubbleWrap{
      display:flex; margin:8px 0;
    }
    .bubble{
      max-width: 78%;
      padding:10px 12px;
      border-radius:16px;
      border:1px solid var(--line);
      background: rgba(255,255,255,.05);
      font-size:13px;
      line-height:1.25;
    }
    .bubble small{
      display:block;
      margin-bottom:4px;
      color:var(--muted);
      font-size:11px;
      font-weight:800;
      letter-spacing:.2px;
    }
    .me{ justify-content:flex-end; }
    .me .bubble{
      background: rgba(124,58,237,.18);
      border-color: rgba(124,58,237,.28);
    }
    .sys .bubble{
      background: rgba(245,158,11,.10);
      border-color: rgba(245,158,11,.25);
    }

    /* Call UI */
    .callBanner{
      display:none;
      padding:12px;
      border-radius:14px;
      border:1px solid rgba(245,158,11,.35);
      background: rgba(245,158,11,.12);
      font-weight:900;
      margin-bottom:10px;
    }
    .callLive{
      display:none;
      padding:12px;
      border-radius:14px;
      border:1px solid rgba(34,197,94,.35);
      background: rgba(34,197,94,.10);
      font-weight:900;
      margin-bottom:10px;
    }

    /* Log */
    #log{
      margin-top:12px;
      white-space: pre-wrap;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
      font-size:12px;
      border:1px solid var(--line);
      background: rgba(0,0,0,.22);
      border-radius:14px;
      padding:12px;
      max-height:180px;
      overflow:auto;
      color: #d6ddf5;
    }
  </style>
</head>

<body>
  <div class="topbar">
    <div class="brand">
      <div class="logo"></div>
      <div class="title">
        <h2>Cashier Console</h2>
        <div class="sub">POS + Agent • Real-time chat • Payment request • WebRTC voice</div>
      </div>
    </div>

    <div class="meta">
      <div class="chip">
        <span class="dot" id="wsDot"></span>
        <span id="wsState">WS: idle</span>
      </div>
      <div class="chip"><b>Cashier</b>&nbsp;<span id="cashier"></span></div>
      <div class="chip" id="joinedPill">No order joined</div>
    </div>
  </div>

  <div class="grid">
    <!-- LEFT: Orders + Chat -->
    <div class="card">
      <div class="cardHeader">
        <div class="h">Orders & Chat</div>
        <div class="row tight" style="gap:8px;">
          <button class="btnGhost" onclick="refreshOrders()">Refresh</button>
          <button onclick="joinSelected()">Join</button>
        </div>
      </div>

      <div class="cardBody">
        <label>Orders</label>
        <select id="orderSelect"></select>

        <div class="summary">
          <div class="stat">
            <div class="k">Lane</div>
            <div class="v" id="sumLane">—</div>
          </div>
          <div class="stat">
            <div class="k">Status</div>
            <div class="v" id="sumStatus">—</div>
          </div>
          <div class="stat">
            <div class="k">Total</div>
            <div class="v" id="sumTotal">—</div>
          </div>
        </div>

        <label style="margin-top:12px;">Conversation</label>
        <div class="chat" id="chat"></div>

        <div class="row" style="margin-top:10px;">
          <input id="cashierMsg" placeholder="Type a message to the customer…" />
          <button class="btnPrimary" style="flex:0 0 auto;" onclick="sendCashierMsg()">Send</button>
        </div>

        <div class="helper">Tip: Join an order first, then chat + confirm total to trigger a payment request.</div>
      </div>
    </div>

    <!-- RIGHT: Checkout + Call -->
    <div class="card">
      <div class="cardHeader">
        <div class="h">Checkout & Call</div>
        <div class="chip"><b>Current</b>&nbsp;<span id="statusLine">—</span></div>
      </div>

      <div class="cardBody">
        <label>Items (optional)</label>
        <textarea id="items" rows="6" placeholder="e.g., 1x Burger, 1x Fries, 1x Coke"></textarea>

        <label>Set Total (USD)</label>
        <input id="total" placeholder="e.g., 13.84" />

        <div class="row tight" style="gap:8px; flex-wrap:wrap; margin-top:8px;">
          <button onclick="addAmount(1)">+ $1</button>
          <button onclick="addAmount(5)">+ $5</button>
          <button onclick="roundTotal()">Round</button>
          <button class="btnPrimary" onclick="confirmTotal()">Confirm Total & Send Payment</button>
        </div>

        <div style="margin-top:14px; border-top:1px solid var(--line); padding-top:14px;">
          <div class="h" style="font-size:13px; font-weight:900; margin-bottom:8px;">Voice Call (WebRTC)</div>

          <div id="incomingCall" class="callBanner">📞 Incoming call request…</div>
          <div id="liveCall" class="callLive">✅ Call connected (audio live)</div>

          <div class="row tight" style="gap:8px; flex-wrap:wrap;">
            <button id="btnAccept" class="btnPrimary" onclick="acceptCall()" disabled>Accept</button>
            <button id="btnReject" class="btnDanger" onclick="rejectCall()" disabled>Reject</button>
            <button id="btnQueue" onclick="queueCall()" disabled>Put in queue</button>
            <button id="btnHangup" onclick="hangupCall()" disabled>Hang up</button>
          </div>

          <audio id="remoteAudio" autoplay playsinline></audio>
          <div class="helper">Mic permission is requested when you press Accept.</div>
        </div>

        <div id="log"></div>
      </div>
    </div>
  </div>

<script>
const WS_PROTO = location.protocol === "https:" ? "wss" : "ws";

const wsStateEl = document.getElementById("wsState");
const wsDot = document.getElementById("wsDot");

const orderSelect = document.getElementById("orderSelect");
const chatEl = document.getElementById("chat");
const logEl = document.getElementById("log");
const joinedPill = document.getElementById("joinedPill");
const statusLine = document.getElementById("statusLine");

const sumLane = document.getElementById("sumLane");
const sumStatus = document.getElementById("sumStatus");
const sumTotal = document.getElementById("sumTotal");

const incomingCallEl = document.getElementById("incomingCall");
const liveCallEl = document.getElementById("liveCall");
const btnAccept = document.getElementById("btnAccept");
const btnReject = document.getElementById("btnReject");
const btnQueue = document.getElementById("btnQueue");
const btnHangup = document.getElementById("btnHangup");
const remoteAudio = document.getElementById("remoteAudio");
let callQueued = false;

function setWsState(label, level){
  wsStateEl.textContent = label;
  wsDot.className = "dot " + (level || "");
}
function log(line){ logEl.textContent += `[${new Date().toLocaleTimeString()}] ${line}\\n`; logEl.scrollTop = logEl.scrollHeight; }

function bubble(who, text){
  const wrap = document.createElement("div");
  wrap.className = "bubbleWrap";

  const b = document.createElement("div");
  b.className = "bubble";

  let cls = "";
  const w = (who || "").toUpperCase();
  if (w.includes("CASHIER")) cls = "me";
  else if (w.includes("SYSTEM")) cls = "sys";

  wrap.classList.add(cls);
  b.innerHTML = `<small>${who}</small>${escapeHtml(text)}`;
  wrap.appendChild(b);
  chatEl.appendChild(wrap);
  chatEl.scrollTop = chatEl.scrollHeight;
}

function escapeHtml(s){
  return (s ?? "").toString().replace(/[&<>"']/g, m => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
  }[m]));
}

// Ephemeral cashier id
const cashierId = "cashier_" + (crypto.randomUUID ? crypto.randomUUID().slice(0,8) : Math.random().toString(36).slice(2,10));
document.getElementById("cashier").textContent = cashierId;

let orderWs = null;
let callSigWs = null;
let pc = null;
let currentOrderId = null;

async function refreshOrders(){
  const res = await fetch("/cashier/orders");
  const data = await res.json();

  orderSelect.innerHTML = "";
  (data.orders || []).forEach(o => {
    const opt = document.createElement("option");
    opt.value = o.order_id;
    opt.textContent = `Order ${o.order_id} | lane=${o.lane_id} | status=${o.status} | total=$${(o.total_cents/100).toFixed(2)}`;
    opt.dataset.lane = o.lane_id ?? "";
    opt.dataset.status = o.status ?? "";
    opt.dataset.total = o.total_cents ?? 0;
    orderSelect.appendChild(opt);
  });

  if (!data.orders?.length){
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "No orders yet";
    orderSelect.appendChild(opt);
  }

  // preview selected summary
  updateSummaryFromSelected();
}
refreshOrders();

orderSelect.addEventListener("change", updateSummaryFromSelected);

function updateSummaryFromSelected(){
  const opt = orderSelect.selectedOptions?.[0];
  if (!opt || !opt.value){
    sumLane.textContent = "—";
    sumStatus.textContent = "—";
    sumTotal.textContent = "—";
    return;
  }
  sumLane.textContent = opt.dataset.lane || "—";
  sumStatus.textContent = opt.dataset.status || "—";
  const cents = parseInt(opt.dataset.total || "0", 10);
  sumTotal.textContent = `$${(cents/100).toFixed(2)}`;
}

function joinSelected(){
  const oid = orderSelect.value;
  if (!oid) return alert("No order selected");
  joinOrder(oid);
}

function joinOrder(oid){
  if (orderWs) { try { orderWs.close(); } catch(e){} }
  if (callSigWs) { try { callSigWs.close(); } catch(e){} }
  cleanupCallUI(true);

  currentOrderId = oid;
  chatEl.innerHTML = "";
  joinedPill.textContent = `Joined: ${oid}`;
  setWsState("WS: connecting…", "warn");
  log(`Joining order ${oid}...`);

  // Order chat WS
  orderWs = new WebSocket(`${WS_PROTO}://${location.host}/ws/order/${oid}/cashier?cashier_id=${encodeURIComponent(cashierId)}`);

  orderWs.onopen = () => { setWsState("WS: connected", "good"); log("Order WS connected"); };
  orderWs.onerror = () => { setWsState("WS: error", "bad"); log("Order WS error"); };
  orderWs.onclose = () => { setWsState("WS: closed", "bad"); log("Order WS closed"); };

  orderWs.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);

    if (msg.type === "chat") bubble(msg.from, msg.text);

    if (msg.type === "order_state") {
      statusLine.textContent = msg.status || "—";
      sumStatus.textContent = msg.status || "—";
      if (msg.lane_id != null) sumLane.textContent = msg.lane_id;

      if (msg.items_text != null) document.getElementById("items").value = msg.items_text;
      if (msg.total_cents != null){
        document.getElementById("total").value = (msg.total_cents/100).toFixed(2);
        sumTotal.textContent = `$${(msg.total_cents/100).toFixed(2)}`;
      }
      log(JSON.stringify(msg));
    }

    if (msg.type === "payment_status") {
      statusLine.textContent = `PAYMENT: ${msg.status} (${msg.payment_method || "n/a"})`;
      bubble("SYSTEM", `Payment ${msg.status}. Method: ${msg.payment_method || "n/a"}`);
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
      bubble("SYSTEM", "📞 Customer is requesting a voice call.");
      return;
    }

    if (msg.type === "webrtc_offer") {
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
      bubble("SYSTEM", "Call ended.");
      cleanupCallUI(false);
      return;
    }
  };
}

function sendCashierMsg(){
  if (!orderWs || !currentOrderId) return;
  const inp = document.getElementById("cashierMsg");
  const text = inp.value.trim();
  if (!text) return;
  orderWs.send(JSON.stringify({type:"chat", from:"CASHIER", text}));
  inp.value = "";
  bubble("CASHIER", text);
}

function addAmount(x){
  const el = document.getElementById("total");
  const v = parseFloat(el.value || "0");
  const next = (Number.isFinite(v) ? v : 0) + x;
  el.value = next.toFixed(2);
}
function roundTotal(){
  const el = document.getElementById("total");
  const v = parseFloat(el.value || "0");
  if (!Number.isFinite(v)) return;
  el.value = Math.round(v).toFixed(2);
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

  statusLine.textContent = "Payment request sent…";
  bubble("SYSTEM", "✅ Payment request sent to customer.");
  refreshOrders();
}

// --------------------
// WebRTC Voice Call (Cashier as callee)
// --------------------
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

  const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
  stream.getAudioTracks().forEach(t => pc.addTrack(t, stream));
}

function cleanupCallUI(){
  try { pc?.close(); } catch(e){}
  pc = null;

  incomingCallEl.style.display = "none";
  liveCallEl.style.display = "none";
  btnAccept.disabled = true;
  btnReject.disabled = true;
  btnHangup.disabled = true;
  remoteAudio.srcObject = null;
}

async function acceptCall(){
  if (!callSigWs || !currentOrderId) return;

  incomingCallEl.style.display = "none";
  liveCallEl.style.display = "block";
  btnHangup.disabled = false;
  btnAccept.disabled = true;
  btnReject.disabled = true;

  callSigWs.send(JSON.stringify({ type:"call_accept" }));
  bubble("SYSTEM", "✅ Call accepted. Connecting audio…");

  try {
    await ensurePeerConnection();
  } catch(e){
    bubble("SYSTEM", "❌ Microphone permission denied or unavailable.");
    cleanupCallUI();
    callSigWs.send(JSON.stringify({ type:"hangup" }));
  }
}

function queueCall(){
  if (!callSigWs) return;

  callQueued = true;

  incomingCallEl.style.display = "block";
  incomingCallEl.textContent = "⏳ Call queued — customer waiting…";

  btnAccept.disabled = false;   // accept later
  btnReject.disabled = false;   // reject later
  btnQueue.disabled  = true;    // already queued
  btnHangup.disabled = false;

  callSigWs.send(JSON.stringify({
    type: "call_queue",
    message: "Please wait — cashier will join shortly."
  }));

  chat("SYSTEM", "⏳ Call placed in queue. Customer asked to wait.");
}

function rejectCall(){
  if (!callSigWs) return;
  bubble("SYSTEM", "Call rejected.");
  callSigWs.send(JSON.stringify({ type:"call_reject" }));
  cleanupCallUI();
}

function hangupCall(){
  if (!callSigWs) return;
  callSigWs.send(JSON.stringify({ type:"hangup" }));
  bubble("SYSTEM", "Call ended.");
  cleanupCallUI();
}
</script>
</body>
</html>
"""


CUSTOMER_HTML = r"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Customer Portal</title>

  <style>
    :root{
      --bg:#070b14;
      --card: rgba(255,255,255,0.08);
      --card2: rgba(255,255,255,0.10);
      --stroke: rgba(255,255,255,0.14);
      --text: rgba(255,255,255,0.94);
      --muted: rgba(255,255,255,0.70);
      --shadow: 0 18px 60px rgba(0,0,0,.40);
      --shadow2: 0 10px 24px rgba(0,0,0,.30);
      --ok:#22c55e;
      --warn:#f59e0b;
      --err:#ef4444;
      --accent:#7c3aed;
      --accent2:#22d3ee;

      --r:18px;
      --r2:14px;
      --pad:16px;
      --pad2:12px;
      --max: 1080px;
    }

    *{ box-sizing:border-box; }
    html,body{ height:100%; margin:0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial; background:var(--bg); color:var(--text); }
    a{ color:inherit; }

    /* Background (brand-neutral; works for any restaurant) */
    body{
      background:
        radial-gradient(1200px 700px at 15% 5%, rgba(124,58,237,.35), transparent 55%),
        radial-gradient(900px 600px at 85% 15%, rgba(34,211,238,.28), transparent 55%),
        radial-gradient(900px 700px at 50% 110%, rgba(34,197,94,.18), transparent 60%),
        linear-gradient(180deg, rgba(255,255,255,.04), rgba(255,255,255,0)),
        var(--bg);
      background-attachment: fixed;
      overflow-x:hidden;
    }

    /* Optional: if you later add real background images */
    /* 
    body{
      background-image:
        linear-gradient(rgba(0,0,0,.55), rgba(0,0,0,.75)),
        url('/static/bg_desktop.jpg');
      background-size: cover;
      background-position: center;
      background-repeat:no-repeat;
    }
    @media (max-width: 640px){
      body{
        background-image:
          linear-gradient(rgba(0,0,0,.55), rgba(0,0,0,.80)),
          url('/static/bg_mobile.jpg');
      }
    }
    */

    .wrap{ max-width: var(--max); margin: 0 auto; padding: 18px 14px 86px; } /* extra bottom for mobile sticky bar */
    @media (min-width: 900px){
      .wrap{ padding: 26px 18px 26px; }
    }

    /* Top header */
    .topbar{
      display:flex; align-items:flex-start; justify-content:space-between;
      gap:12px; margin-bottom: 12px;
    }
    .brand{
      display:flex; flex-direction:column; gap:4px;
    }
    .brand h1{ margin:0; font-size: 18px; letter-spacing:.2px; }
    .brand .sub{ color:var(--muted); font-size: 12px; }
    @media (min-width: 700px){
      .brand h1{ font-size: 20px; }
    }

    .chips{ display:flex; flex-wrap:wrap; gap:8px; justify-content:flex-end; }
    .chip{
      display:inline-flex; align-items:center; gap:8px;
      padding: 8px 10px;
      border-radius: 999px;
      border: 1px solid var(--stroke);
      background: rgba(255,255,255,0.06);
      backdrop-filter: blur(10px);
      box-shadow: var(--shadow2);
      font-size: 12px;
      white-space: nowrap;
    }
    .dot{ width:8px; height:8px; border-radius:999px; background: var(--warn); box-shadow: 0 0 0 3px rgba(245,158,11,.20); }
    .dot.ok{ background: var(--ok); box-shadow: 0 0 0 3px rgba(34,197,94,.18); }
    .dot.err{ background: var(--err); box-shadow: 0 0 0 3px rgba(239,68,68,.20); }

    /* Main card */
    .card{
      border: 1px solid var(--stroke);
      background: linear-gradient(180deg, rgba(255,255,255,0.10), rgba(255,255,255,0.06));
      border-radius: var(--r);
      box-shadow: var(--shadow);
      overflow:hidden;
      backdrop-filter: blur(12px);
    }
    .cardInner{ padding: var(--pad); }

    /* Step blocks */
    .steps{
      display:grid;
      gap: 12px;
    }
    @media (min-width: 900px){
      .steps{ gap: 14px; }
    }

    .step{
      border: 1px solid var(--stroke);
      background: rgba(255,255,255,0.06);
      border-radius: var(--r2);
      overflow:hidden;
    }
    .stepHead{
      display:flex; align-items:center; justify-content:space-between;
      gap:10px;
      padding: 12px 12px;
      border-bottom: 1px solid rgba(255,255,255,0.10);
      background: rgba(0,0,0,0.18);
    }
    .stepTitle{
      display:flex; align-items:center; gap:10px;
      font-weight:800;
      letter-spacing:.2px;
    }
    .badge{
      width:26px; height:26px; border-radius:10px;
      display:grid; place-items:center;
      background: linear-gradient(135deg, rgba(124,58,237,.55), rgba(34,211,238,.45));
      border: 1px solid rgba(255,255,255,0.18);
      box-shadow: 0 10px 22px rgba(0,0,0,.25);
      font-size: 13px;
    }
    .stepBody{ padding: 12px; }

    /* Layout inside steps */
    .row{ display:flex; gap:12px; flex-wrap:wrap; }
    .col{ flex:1; min-width: 220px; }
    .col.tight{ flex:0 0 auto; }

    label{ display:block; color:var(--muted); font-size: 12px; margin-bottom: 6px; }
    input, select, textarea{
      width:100%;
      padding: 12px 12px;
      border-radius: 12px;
      border: 1px solid rgba(255,255,255,0.18);
      outline: none;
      background: rgba(10,14,24,0.55);
      color: var(--text);
      box-shadow: inset 0 0 0 1px rgba(0,0,0,.10);
    }
    input::placeholder, textarea::placeholder{ color: rgba(255,255,255,0.45); }
    textarea{ resize: vertical; min-height: 100px; }

    /* Buttons */
    .btn{
      appearance:none; border:none;
      padding: 11px 14px;
      border-radius: 12px;
      cursor:pointer;
      font-weight: 800;
      letter-spacing: .2px;
      color: rgba(255,255,255,.95);
      background: rgba(255,255,255,0.10);
      border: 1px solid rgba(255,255,255,0.18);
      box-shadow: 0 12px 24px rgba(0,0,0,.25);
      transition: transform .08s ease, filter .08s ease, background .08s ease;
      user-select:none;
      display:inline-flex; align-items:center; justify-content:center; gap:8px;
    }
    .btn:hover{ filter: brightness(1.08); }
    .btn:active{ transform: translateY(1px); }
    .btn[disabled]{ opacity:.55; cursor:not-allowed; }

    .btnPrimary{
      background: linear-gradient(135deg, rgba(124,58,237,.95), rgba(34,211,238,.80));
      border: 1px solid rgba(255,255,255,0.18);
    }
    .btnOk{ background: linear-gradient(135deg, rgba(34,197,94,.85), rgba(34,211,238,.55)); }
    .btnDanger{ background: linear-gradient(135deg, rgba(239,68,68,.90), rgba(245,158,11,.60)); }
    .btnGhost{ background: rgba(255,255,255,0.07); }

    .btnWide{ width: 100%; }

    .help{ color: var(--muted); font-size: 12px; margin-top: 10px; line-height: 1.35; }

    /* Banners */
    .banner{
      display:none;
      margin-top: 10px;
      padding: 12px 12px;
      border-radius: 14px;
      border: 1px solid rgba(255,255,255,0.18);
      background: rgba(0,0,0,0.22);
    }
    .banner.ok{ border-color: rgba(34,197,94,.45); background: rgba(34,197,94,.12); }
    .banner.err{ border-color: rgba(239,68,68,.45); background: rgba(239,68,68,.10); }

    /* Order + status grid */
    .grid2{
      display:grid;
      gap:12px;
      grid-template-columns: 1fr;
      align-items:start;
    }
    @media (min-width: 900px){
      .grid2{ grid-template-columns: 1.2fr 0.8fr; }
    }

    /* Chat */
    .chat{
      background: rgba(0,0,0,0.22);
      border: 1px solid rgba(255,255,255,0.14);
      border-radius: 14px;
      padding: 10px;
      height: 260px;
      overflow:auto;
    }
    .msg{ margin: 8px 0; display:flex; gap:10px; }
    .who{
      flex:0 0 auto;
      font-size: 11px;
      color: rgba(255,255,255,0.80);
      padding: 4px 8px;
      border-radius: 999px;
      border: 1px solid rgba(255,255,255,0.14);
      background: rgba(255,255,255,0.06);
      align-self:flex-start;
      max-width: 120px;
      white-space: nowrap;
      overflow:hidden;
      text-overflow: ellipsis;
    }
    .bubble{
      flex: 1;
      padding: 10px 10px;
      border-radius: 14px;
      border: 1px solid rgba(255,255,255,0.14);
      background: rgba(255,255,255,0.06);
      line-height: 1.35;
      font-size: 13px;
      word-break: break-word;
    }
    .msg.customer .bubble{ background: rgba(124,58,237,0.18); border-color: rgba(124,58,237,0.35); }
    .msg.cashier .bubble{ background: rgba(34,211,238,0.14); border-color: rgba(34,211,238,0.30); }
    .msg.system .bubble{ background: rgba(255,255,255,0.07); border-color: rgba(255,255,255,0.14); color: rgba(255,255,255,0.86); }

    .callLive{
      display:none;
      margin-top: 10px;
      padding: 10px 12px;
      border-radius: 14px;
      border: 1px solid rgba(34,197,94,.45);
      background: rgba(34,197,94,.12);
      font-weight:800;
    }

    /* Status card */
    .statusCard{
      border: 1px solid rgba(255,255,255,0.14);
      background: rgba(0,0,0,0.20);
      border-radius: 14px;
      padding: 12px;
    }
    .statusLabel{ color: var(--muted); font-size: 12px; }
    .statusValue{ margin-top: 6px; font-weight: 900; letter-spacing: .2px; }
    .statusHint{ margin-top: 10px; color: var(--muted); font-size: 12px; line-height: 1.35; }

    /* Payment area */
    .paymentArea{
      border: 1px solid rgba(255,255,255,0.14);
      background: rgba(0,0,0,0.20);
      border-radius: 14px;
      padding: 12px;
    }
    .payTitle{ font-weight: 900; margin: 0 0 8px 0; letter-spacing:.2px; }
    .method{
      padding: 12px;
      border: 1px solid rgba(255,255,255,0.14);
      border-radius: 14px;
      margin-top: 10px;
      background: rgba(255,255,255,0.06);
    }
    .method h4{ margin: 0 0 10px 0; font-size: 13px; letter-spacing:.2px; }
    .divider{ height:1px; background: rgba(255,255,255,0.12); margin: 12px 0; }

    /* Mobile sticky action bar */
    .stickyBar{
      position: fixed;
      left: 0; right: 0; bottom: 0;
      padding: 10px 12px calc(10px + env(safe-area-inset-bottom));
      background: rgba(0,0,0,0.60);
      backdrop-filter: blur(14px);
      border-top: 1px solid rgba(255,255,255,0.14);
      display:flex;
      gap:10px;
      z-index: 1000;
    }
    @media (min-width: 900px){
      .stickyBar{ display:none; }
      .wrap{ padding-bottom: 26px; }
    }

    /* Modals (kept, but styled to match) */
    .modal{
      display:none; position:fixed; inset:0;
      background: rgba(0,0,0,0.60);
      align-items:center; justify-content:center;
      z-index: 9998;
      padding: 14px;
    }
    .modalBox{
      width: min(560px, 100%);
      background: linear-gradient(180deg, rgba(255,255,255,0.10), rgba(255,255,255,0.06));
      border: 1px solid rgba(255,255,255,0.16);
      border-radius: 18px;
      padding: 16px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(14px);
    }
    .modalBox h3{ margin: 0 0 10px 0; }
    .modalBox .text{ color: rgba(255,255,255,0.86); margin-bottom: 12px; line-height:1.35; }
    .modalRow{ display:flex; gap:10px; flex-wrap:wrap; }
    .modalActions{ display:flex; justify-content:flex-end; margin-top: 12px; gap:10px; }

    /* Tiny helpers */
    .mono{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }
    .sp{ height: 8px; }

    /* =========================
       NEW: Progress + Toast + Confetti + Motion BG
       ========================= */

    /* Motion background layers */
    body::before{
      content:"";
      position:fixed; inset:-40%;
      background:
        radial-gradient(600px 420px at 20% 10%, rgba(124,58,237,.26), transparent 60%),
        radial-gradient(560px 420px at 85% 18%, rgba(34,211,238,.20), transparent 62%),
        radial-gradient(520px 520px at 48% 110%, rgba(34,197,94,.14), transparent 60%);
      filter: blur(18px);
      opacity:.9;
      animation: floatGlow 14s ease-in-out infinite alternate;
      pointer-events:none;
      z-index:-2;
    }
    body::after{
      content:"";
      position:fixed; inset:0;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='180' height='180'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='180' height='180' filter='url(%23n)' opacity='.18'/%3E%3C/svg%3E");
      mix-blend-mode: overlay;
      opacity:.12;
      pointer-events:none;
      z-index:-1;
    }
    @keyframes floatGlow{
      0%   { transform: translate3d(-2%, -1%, 0) scale(1.00); }
      100% { transform: translate3d(2%,  1%, 0) scale(1.04); }
    }

    /* Progress bar */
    .progressWrap{
      margin: 10px 0 14px 0;
      padding: 10px 12px;
      border: 1px solid rgba(255,255,255,0.14);
      background: rgba(0,0,0,0.20);
      border-radius: 14px;
      backdrop-filter: blur(12px);
    }
    .progressTop{
      display:flex; align-items:center; justify-content:space-between;
      gap:12px;
      font-size: 12px;
      color: rgba(255,255,255,0.78);
    }
    .progressBar{
      height: 10px;
      border-radius: 999px;
      background: rgba(255,255,255,0.10);
      border: 1px solid rgba(255,255,255,0.14);
      overflow:hidden;
      margin-top: 8px;
    }
    .progressFill{
      height:100%;
      width: 0%;
      border-radius: 999px;
      background: linear-gradient(90deg, rgba(124,58,237,.95), rgba(34,211,238,.85), rgba(34,197,94,.75));
      box-shadow: 0 0 0 1px rgba(255,255,255,0.12) inset, 0 10px 24px rgba(0,0,0,.30);
      transition: width .35s ease;
    }

    /* Step highlight when done */
    .step.done{
      border-color: rgba(34,197,94,.35);
      box-shadow: 0 0 0 1px rgba(34,197,94,.10) inset, 0 20px 60px rgba(0,0,0,.22);
    }
    .step.done .badge{
      background: linear-gradient(135deg, rgba(34,197,94,.88), rgba(34,211,238,.55));
    }

    /* Toast styling + pop */
    #toast{
      position: sticky;
      top: 10px;
      z-index: 5;
      padding: 12px 12px;
      border-radius: 14px;
      border: 1px solid rgba(255,255,255,0.14);
      background: rgba(0,0,0,0.28);
      backdrop-filter: blur(14px);
      box-shadow: 0 18px 50px rgba(0,0,0,.28);
      transform: translateY(0);
      transition: transform .18s ease, opacity .18s ease;
    }
    .toastPulse{
      animation: toastPop .24s ease-out;
    }
    @keyframes toastPop{
      0%{ transform: translateY(-6px); opacity: .6; }
      100%{ transform: translateY(0); opacity: 1; }
    }

    /* Confetti */
    .confetti{
      position:fixed; inset:0; pointer-events:none; z-index:99999;
      overflow:hidden;
    }
    .confetti i{
      position:absolute;
      width:10px; height:14px;
      background: rgba(255,255,255,0.85);
      border-radius: 3px;
      top:-20px;
      animation: fall 1.2s linear forwards;
    }
    @keyframes fall{
      to{ transform: translateY(110vh) rotate(420deg); opacity: 0.9; }
    }
  </style>
</head>

<body>
  <div class="wrap">
    <div class="topbar">
      <div class="brand">
        <h1>Customer Portal <span style="opacity:.8;">(Drive-Thru Mode)</span></h1>
        <div class="sub">Connect • Order • Call • Pay — without opening the window</div>
      </div>

      <div class="chips">
        <div class="chip"><span class="dot" id="wsDot"></span><span id="wsState">WS: connecting…</span></div>
        <div class="chip"><span style="opacity:.85;">Customer</span> <span class="mono" id="cust"></span></div>
      </div>
    </div>

    <!-- NEW: progress bar -->
    <div class="progressWrap">
      <div class="progressTop">
        <div id="progressText">Progress: 0/4</div>
        <div id="progressHint" style="opacity:.85;">Start with “I’m Here”.</div>
      </div>
      <div class="progressBar"><div class="progressFill" id="progressFill"></div></div>
    </div>

    <div class="card">
      <div class="cardInner">

        <div id="toast" style="font-weight:900; letter-spacing:.2px;">Loading…</div>
        <div id="okBanner" class="banner ok">✅ Connected to cashier. You can order now.</div>
        <div id="errBanner" class="banner err"></div>

        <div class="steps">

          <!-- Step 1 -->
          <div class="step" id="step1">
            <div class="stepHead">
              <div class="stepTitle"><div class="badge">1</div> I’m here</div>
              <div style="color:var(--muted); font-size:12px;">Check-in</div>
            </div>
            <div class="stepBody">
              <div class="row">
                <div class="col">
                  <label>Lane</label>
                  <select id="lane">
                    <option value="L1">Lane L1</option>
                    <option value="L2">Lane L2</option>
                  </select>
                </div>
                <div class="col tight" style="min-width: 160px;">
                  <label>&nbsp;</label>
                  <button class="btn btnPrimary btnWide" onclick="checkIn()">I’m Here</button>
                </div>
              </div>
              <div class="help">After check-in, you’ll enter the 4-digit station code shown at the lane display.</div>
            </div>
          </div>

          <!-- Step 2 -->
          <div class="step" id="step2">
            <div class="stepHead">
              <div class="stepTitle"><div class="badge">2</div> Connect</div>
              <div style="color:var(--muted); font-size:12px;">Station code</div>
            </div>
            <div class="stepBody">
              <div class="row">
                <div class="col">
                  <label>4-digit station code</label>
                  <input id="code" inputmode="numeric" placeholder="Enter 4-digit lane code" />
                </div>
                <div class="col tight" style="min-width: 160px;">
                  <label>&nbsp;</label>
                  <button class="btn btnOk btnWide" onclick="connect()">Connect</button>
                </div>
              </div>
              <div class="help">Lane display: <span class="mono">/lane/L1</span> or <span class="mono">/lane/L2</span> (code valid 10 minutes; rotates after successful connect)</div>
            </div>
          </div>

          <!-- Step 3 -->
          <div class="step" id="step3">
            <div class="stepHead">
              <div class="stepTitle"><div class="badge">3</div> Order + Voice</div>
              <div style="color:var(--muted); font-size:12px;">Chat / WebRTC</div>
            </div>

            <div class="stepBody">
              <div class="grid2">
                <div>
                  <div class="chat" id="chat"></div>
                  <div class="sp"></div>
                  <div class="row">
                    <div class="col">
                      <label>Message</label>
                      <input id="custMsg" placeholder="Type your order… (e.g., 2 spicy chicken sandwiches, no pickles)" />
                    </div>
                  </div>

                  <div class="row" style="margin-top:10px;">
                    <div class="col">
                      <button class="btn btnPrimary btnWide" onclick="sendText()">Send Text</button>
                    </div>
                    <div class="col">
                      <button class="btn btnGhost btnWide" onclick="requestCall()">📞 Call Agent</button>
                    </div>
                    <div class="col">
                      <button class="btn btnDanger btnWide" onclick="hangupCall()" id="btnHangup" disabled>Hang up</button>
                    </div>
                  </div>

                  <div id="callLive" class="callLive">✅ Call connected (audio live)</div>
                  <audio id="remoteAudio" autoplay playsinline></audio>
                  <div class="help">Voice call uses WebRTC (Chrome recommended). If mic permission is blocked, refresh and allow microphone.</div>
                </div>

                <div class="statusCard">
                  <div class="statusLabel">Status</div>
                  <div id="status" class="statusValue">Not connected</div>
                  <div class="statusHint">
                    Once cashier confirms total, payment options will appear in Step 4.
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Step 4 -->
          <div class="step" id="step4">
            <div class="stepHead">
              <div class="stepTitle"><div class="badge">4</div> Payment</div>
              <div style="color:var(--muted); font-size:12px;">Secure request</div>
            </div>
            <div class="stepBody">
              <div id="paymentArea" class="paymentArea" style="color:var(--muted);">
                Waiting for cashier to confirm total…
              </div>
            </div>
          </div>

        </div><!-- /steps -->
      </div><!-- /cardInner -->
    </div><!-- /card -->
  </div><!-- /wrap -->

  <!-- Mobile sticky quick actions (shows only on phone) -->
  <div class="stickyBar">
    <button class="btn btnGhost" style="flex:1;" onclick="openCodeModal()">Enter Code</button>
    <button class="btn btnPrimary" style="flex:1;" onclick="sendText()">Send</button>
    <button class="btn btnGhost" style="flex:1;" onclick="requestCall()">📞 Call</button>
  </div>

  <!-- Code modal (shown after check-in) -->
  <div id="codeModal" class="modal">
    <div class="modalBox">
      <h3 style="margin:0 0 8px 0;">Connect to Cashier</h3>
      <div class="text">✅ You’re checked in. Enter the <b>4-digit station code</b> shown at the lane display.</div>
      <div class="modalRow">
        <input id="codeModalInput" inputmode="numeric" placeholder="Enter 4-digit code" style="flex:1; min-width: 220px;" />
        <button class="btn btnOk" onclick="connectFromModal()">Connect</button>
      </div>
      <div class="modalActions">
        <button class="btn btnGhost" onclick="closeCodeModal()">Close</button>
      </div>
    </div>
  </div>

  <!-- Payment success modal -->
  <div id="paidModal" class="modal" style="z-index:9999;">
    <div class="modalBox" style="text-align:center;">
      <div style="font-size:44px;">✅</div>
      <h2 style="margin:10px 0 6px 0;">Payment Completed</h2>
      <div id="paidText" class="text" style="margin:10px 0 16px 0;">
        Move forward to the pickup window to collect your order.
      </div>
      <button class="btn btnPrimary" onclick="closePaidModal()">OK</button>
    </div>
  </div>

<script>
const WS_PROTO = location.protocol === "https:" ? "wss" : "ws";

const custEl = document.getElementById("cust");
const wsStateEl = document.getElementById("wsState");
const wsDot = document.getElementById("wsDot");

const toastEl = document.getElementById("toast");
const okBanner = document.getElementById("okBanner");
const errBanner = document.getElementById("errBanner");
const chatEl = document.getElementById("chat");
const statusEl = document.getElementById("status");
const paymentArea = document.getElementById("paymentArea");

const callLiveEl = document.getElementById("callLive");
const btnHangup = document.getElementById("btnHangup");
const remoteAudio = document.getElementById("remoteAudio");

/* ----------------------------
   NEW: UI helpers
-----------------------------*/
const progressFill = document.getElementById("progressFill");
const progressText = document.getElementById("progressText");
const progressHint = document.getElementById("progressHint");

const stepDone = { step1:false, step2:false, step3:false, step4:false };

function toast(text){
  toastEl.textContent = text;
  toastEl.classList.remove("toastPulse");
  void toastEl.offsetWidth; // restart animation
  toastEl.classList.add("toastPulse");
}

function setStepDone(stepId, hintText){
  const el = document.getElementById(stepId);
  if (!el) return;
  stepDone[stepId] = true;
  el.classList.add("done");
  updateProgress(hintText);
}

function updateProgress(hintText){
  const total = 4;
  const done = Object.values(stepDone).filter(Boolean).length;
  const pct = Math.round((done/total) * 100);
  if (progressFill) progressFill.style.width = pct + "%";
  if (progressText) progressText.textContent = `Progress: ${done}/${total}`;
  if (hintText && progressHint) progressHint.textContent = hintText;
}

function confettiBurst(){
  const wrap = document.createElement("div");
  wrap.className = "confetti";
  document.body.appendChild(wrap);

  const n = 38;
  for(let i=0;i<n;i++){
    const p = document.createElement("i");
    p.style.left = (Math.random()*100) + "vw";
    p.style.opacity = (0.7 + Math.random()*0.3);
    p.style.transform = `rotate(${Math.random()*180}deg)`;
    p.style.animationDelay = (Math.random()*0.15) + "s";
    p.style.width = (8 + Math.random()*8) + "px";
    p.style.height = (10 + Math.random()*12) + "px";
    wrap.appendChild(p);
  }
  setTimeout(()=>wrap.remove(), 1600);
}

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
  const row = document.createElement("div");
  const w = (who||"SYSTEM").toUpperCase();

  row.className = "msg " + (w.includes("CUSTOMER") ? "customer" : (w.includes("CASHIER") ? "cashier" : "system"));

  const whoEl = document.createElement("div");
  whoEl.className = "who";
  whoEl.textContent = w;

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;

  row.appendChild(whoEl);
  row.appendChild(bubble);

  chatEl.appendChild(row);
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
  wsDot.classList.add("ok");
  wsDot.classList.remove("err");
  toast("Connected. Step 1: Tap ‘I’m Here’.");
  updateProgress("Start with “I’m Here”.");
};
homeWs.onerror = () => {
  wsStateEl.textContent = "WS: error";
  wsDot.classList.add("err");
  wsDot.classList.remove("ok");
  toast("WebSocket error.");
};
homeWs.onclose = () => {
  wsStateEl.textContent = "WS: closed";
  wsDot.classList.remove("ok","err");
  toast("Disconnected. Refresh.");
};

homeWs.onmessage = (ev) => {
  const msg = JSON.parse(ev.data);
  if (msg.type === "info") toast(msg.text);

  if (msg.type === "payment_request") {
    paySessionId = msg.pay_session_id;
    toast("Payment request received — choose payment method.");
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

  toast(`Checked in to ${data.lane_id}. Enter the station code to connect.`);
  setStepDone("step1", "Enter the 4-digit station code.");
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
  toast("Connected. Start ordering.");
  setStepDone("step2", "You’re connected — place your order (text or call).");
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
  const box = document.getElementById("custMsg");
  const text = (box.value || "").trim();
  if (!text) return;
  orderWs.send(JSON.stringify({type:"chat", from:"CUSTOMER", text}));
  setStepDone("step3", "Waiting for cashier to confirm total...");
  box.value = "";
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
  paymentArea.style.color = "rgba(255,255,255,0.92)";
  paymentArea.innerHTML = `
    <div class="payTitle">${msg.merchant_name}</div>
    <div style="color:rgba(255,255,255,0.78); font-size:12px;">Order <span class="mono">${msg.order_id}</span> • Total <b>$${(msg.amount_cents/100).toFixed(2)} ${msg.currency}</b></div>

    <div class="method">
      <h4>Saved Card</h4>
      <select id="savedCardSelect"><option>Loading…</option></select>
      <div style="margin-top:10px;">
        <button class="btn btnOk btnWide" onclick="paySaved()">Pay</button>
      </div>
    </div>

    <div class="method">
      <h4>Add New Card</h4>
      <div style="color:rgba(255,255,255,0.70); font-size:12px; margin-bottom:10px;">Demo only (no real charge).</div>

      <div class="row">
        <div class="col"><input id="newCardNumber" placeholder="Card number (e.g., 4242…)" /></div>
        <div class="col"><input id="newCardExp" placeholder="MM/YY" /></div>
      </div>
      <div class="row">
        <div class="col"><input id="newCardName" placeholder="Name on card" /></div>
        <div class="col"><input id="newCardCvv" placeholder="CVV" /></div>
      </div>
      <button class="btn btnPrimary btnWide" onclick="payNew()">Add & Pay</button>
    </div>

    <div class="method"><h4>Google Pay</h4><button class="btn btnGhost btnWide" onclick="payWallet('google_pay')">Pay with Google Pay</button></div>
    <div class="method"><h4>PayPal</h4><button class="btn btnGhost btnWide" onclick="payWallet('paypal')">Pay with PayPal</button></div>
    <div class="method"><h4>Other Wallet</h4><button class="btn btnGhost btnWide" onclick="payWallet('other_wallet')">Pay with Other Wallet</button></div>

    <div class="divider"></div>
    <button class="btn btnDanger btnWide" onclick="declinePay()">Decline</button>
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
  toast("Declined: " + data.status);
}

async function doPay(payload){
  const res = await fetch(`/payment/${paySessionId}/pay`, {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body: JSON.stringify({ customer_id: customerId, ...payload })
  });
  const data = await res.json();
  if (data.error) return showError(data.error);

  toast(`Payment: ${data.status} (method: ${data.payment_method})`);

  if (data.status === "APPROVED"){
    confettiBurst();
    setStepDone("step4", "Done — proceed to pickup window.");
    showPaidModal("✅ Payment done — move forward to pickup window to pick up your order.");
  }
}

// Small UX: allow Enter to send message on desktop
document.getElementById("custMsg").addEventListener("keydown", (e)=>{
  if(e.key === "Enter"){ e.preventDefault(); sendText(); }
});
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
    expires_iso = rec["expires_at"].isoformat() + "Z"
    html = (
        LANE_HTML_TEMPLATE
        .replace("__LANE_ID__", lane_id)
        .replace("__EXPIRES_AT__", expires_iso)
        .replace("__CODE__", rec["code"])
    )

    return HTMLResponse(html)


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
