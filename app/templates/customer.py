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
