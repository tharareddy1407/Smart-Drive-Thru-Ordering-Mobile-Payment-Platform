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
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:12px;
      padding:14px 16px;
      background:linear-gradient(135deg, rgba(255,255,255,.06), rgba(255,255,255,.03));
      border:1px solid var(--line);
      border-radius:var(--radius);
      box-shadow:var(--shadow);
      position:sticky;
      top:12px;
      z-index:10;
      backdrop-filter: blur(10px);
    }

    .brand{display:flex; align-items:center; gap:10px;}
    .logo{
      width:38px; height:38px; border-radius:12px;
      background: linear-gradient(135deg, var(--accent), var(--accent2));
      box-shadow: 0 8px 24px rgba(124,58,237,.35);
    }
    .title{line-height:1.1;}
    .title h2{margin:0; font-size:16px; font-weight:900; letter-spacing:.2px;}
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

    /* =========================
       NEW: Cashier Progress Bar
       ========================= */
    .progressWrap{
      margin-top: 14px;
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
      background: linear-gradient(90deg, rgba(124,58,237,.95), rgba(6,182,212,.85), rgba(34,197,94,.75));
      box-shadow: 0 0 0 1px rgba(255,255,255,0.12) inset, 0 10px 24px rgba(0,0,0,.30);
      transition: width .35s ease;
    }

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
    .cardHeader .h{ font-size:13px; font-weight:900; letter-spacing:.2px; }
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
      font-weight:800;
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
    .btnGhost{ background: transparent; }
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
    .bubbleWrap{ display:flex; margin:8px 0; }
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
      font-weight:900;
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
        .footerCopyright{
  position: fixed;
  bottom: 10px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 12px;
  color: rgba(255,255,255,0.55);
  letter-spacing: .2px;
  z-index: 999;
  pointer-events: none;
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

  <!-- NEW: progress bar -->
  <div class="progressWrap">
    <div class="progressTop">
      <div id="progressText">Progress: 0/3</div>
      <div id="progressHint" style="opacity:.85;">Start with “Refresh”.</div>
    </div>
    <div class="progressBar"><div class="progressFill" id="progressFill"></div></div>
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

        <div class="helper">Tip: Refresh → Join an order → Confirm total to send payment request.</div>
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

/* ----------------------------
   NEW: Cashier Progress
   Steps: 1) Refresh  2) Join  3) Send Payment
-----------------------------*/
const progressFill = document.getElementById("progressFill");
const progressText = document.getElementById("progressText");
const progressHint = document.getElementById("progressHint");

const stepDone = { refresh:false, join:false, pay:false };

function updateProgress(hint){
  const total = 3;
  const done = Object.values(stepDone).filter(Boolean).length;
  const pct = Math.round((done/total) * 100);
  if (progressFill) progressFill.style.width = pct + "%";
  if (progressText) progressText.textContent = `Progress: ${done}/${total}`;
  if (hint && progressHint) progressHint.textContent = hint;
}
function setStepDone(step, hint){
  if (!stepDone[step]) stepDone[step] = true;
  updateProgress(hint);
}
updateProgress("Start with “Refresh”.");

function setWsState(label, level){
  wsStateEl.textContent = label;
  wsDot.className = "dot " + (level || "");
}
function log(line){
  logEl.textContent += `[${new Date().toLocaleTimeString()}] ${line}\\n`;
  logEl.scrollTop = logEl.scrollHeight;
}

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

  updateSummaryFromSelected();

  // ✅ progress
  setStepDone("refresh", "Click Refresh, select an order, and then click ‘Join”.");
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

  // ✅ progress
  setStepDone("join", "Connected. Confirm total to send payment.");

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
      btnQueue.disabled = false;
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

  // ✅ progress
  setStepDone("pay", "Payment request sent. Wait for customer approval.");

  refreshOrders();
}

/* --------------------
   WebRTC Voice Call (Cashier as callee)
---------------------*/
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
  btnQueue.disabled = true;
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
  btnQueue.disabled = true;

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

  btnAccept.disabled = false;
  btnReject.disabled = false;
  btnQueue.disabled  = true;
  btnHangup.disabled = false;

  callSigWs.send(JSON.stringify({
    type: "call_queue",
    message: "Please wait — cashier will join shortly."
  }));

  bubble("SYSTEM", "⏳ Call placed in queue. Customer asked to wait.");
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
<footer class="footerCopyright">
  © <span id="year"></span> Thara Reddy Kankanala. All rights reserved.
</footer>
<script>
  document.getElementById("year").textContent = new Date().getFullYear();
</script>
</body>
</html>
"""