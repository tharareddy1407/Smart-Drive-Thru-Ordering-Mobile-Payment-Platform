LANE_HTML_TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Lane __LANE_ID__</title>

  <style>
    :root{
      /* Brand-neutral premium QSR look */
      --bgTop:#0b1220;
      --bgBottom:#0a0f1e;

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

      /* allow scrolling on small screens */
      overflow-x:hidden;
      overflow-y:auto;

      background:
        radial-gradient(900px 520px at 15% 20%, rgba(255,183,3,.18), transparent 60%),
        radial-gradient(900px 520px at 85% 25%, rgba(34,197,94,.14), transparent 60%),
        radial-gradient(900px 520px at 55% 95%, rgba(255,77,109,.12), transparent 60%),
        linear-gradient(180deg, var(--bgTop), var(--bgBottom));
    }

    /* Subtle premium texture */
    .texture{
      position:fixed; inset:0;
      background-image: radial-gradient(rgba(255,255,255,.10) 1px, transparent 1px);
      background-size: 28px 28px;
      opacity:.12;
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

    /* Top bar */
    .topbar{
      position:fixed;
      top: 16px; left: 16px; right: 16px;
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:12px;
      z-index: 5;
      pointer-events:none; /* so card remains primary focus */
    }
    .topbar > *{ pointer-events:auto; }

    .brandMark{
      display:flex;
      align-items:center;
      gap:10px;
      font-weight: 950;
      letter-spacing:.2px;
      opacity:.98;
      user-select:none;
    }

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
      white-space:nowrap;
      user-select:none;
    }

    .laneBadge{
      font-weight: 950;
      letter-spacing: .9px;
      padding: 6px 10px;
      border-radius: 999px;
      color: #111;
      background: linear-gradient(135deg, var(--gold), var(--green));
    }

    /* Main card */
    .card{
      width: min(920px, 100%);
      border-radius: var(--radius);
      background: var(--card);
      border: 1px solid var(--stroke);
      box-shadow: var(--shadow);
      backdrop-filter: blur(16px);
      overflow:hidden;
      position:relative;
      margin-top: 58px; /* give space under fixed topbar */
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
      margin:0 0 6px 0;
      font-size: 30px;
      letter-spacing:.2px;
    }

    .subtitle{
      margin:0 0 16px 0;
      color: var(--muted);
      line-height:1.5;
      font-size: 16px;
    }

    /* Code box (high-contrast, outdoor readable) */
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
      font-size: clamp(46px, 7vw, 98px);
      word-break: break-word;
      text-align:center;
    }

    /* Tap-to-copy */
    .copyRow{
      display:flex;
      gap:10px;
      flex-wrap:wrap;
      align-items:center;
      justify-content:center;
      margin-top: 12px;
    }

    .btn{
      appearance:none;
      border:none;
      cursor:pointer;
      font-weight: 900;
      padding: 10px 14px;
      border-radius: 12px;
      background: rgba(0,0,0,.10);
      border: 1px solid rgba(0,0,0,.10);
      color: rgba(0,0,0,.82);
      transition: transform .12s ease, filter .12s ease, background .12s ease;
      user-select:none;
    }
    .btn:hover{ transform: translateY(-1px); filter: brightness(1.03); background: rgba(0,0,0,.12); }
    .btn:active{ transform: translateY(0); }
    .btnPrimary{
      background: linear-gradient(135deg, rgba(34,197,94,.22), rgba(0,0,0,.10));
      border-color: rgba(34,197,94,.35);
    }

    .hintBox{
      margin-top: 12px;
      padding: 10px 12px;
      border-radius: 12px;
      background: rgba(0,0,0,.06);
      border: 1px solid rgba(0,0,0,.08);
      text-align:center;
      font-size: 13px;
      font-weight: 900;
      color: rgba(0,0,0,.74);
    }

    .meta{
      margin-top: 14px;
      display:flex;
      flex-wrap:wrap;
      gap: 10px;
      color: rgba(0,0,0,.68);
      font-size: 14px;
      justify-content:center;
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

    /* prevents “big clock icon” issue */
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

    /* -------------------------
       Mobile optimization
    -------------------------- */
    @media (max-width: 520px){
      .wrap{ padding: 14px; place-items: start; }
      .topbar{
        position: sticky;
        top: 10px;
        left: 10px; right: 10px;
        flex-direction: column;
        align-items: flex-start;
        gap: 10px;
      }
      .pill{ font-size: 12px; padding: 8px 12px; }
      .card{ margin-top: 10px; border-radius: 16px; }
      .inner{ padding: 18px; gap: 14px; }
      .title{ font-size: 22px; }
      .subtitle{ font-size: 14px; }
      .codeBox{ padding: 14px; border-radius: 16px; }
      .code{ font-size: 48px; letter-spacing: 6px; }
      .meta{ font-size: 13px; }
      .footer{ padding: 12px 16px; }
    }

    /* Make it even tighter on very small screens */
    @media (max-width: 360px){
      .code{ font-size: 44px; letter-spacing: 5px; }
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
          <p class="subtitle">
            📱 <b>Copy this 4-digit code</b> and enter it in the <b>Customer UI</b> to connect to <b>Lane __LANE_ID__</b>.
          </p>

          <div class="codeBox">
            <div class="codeLabel"><span class="pulse"></span> Active code</div>
            <p class="code" id="codeText">__CODE__</p>

            <div class="copyRow">
              <button class="btn btnPrimary" id="copyBtn" type="button">Copy Code</button>
              <button class="btn" type="button" onclick="openCustomer()">Open Customer UI</button>
            </div>

            <div class="hintBox" id="copyHint">
              👉 Copy this code → Open Customer UI → Paste & Connect
            </div>

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

            <div style="margin-top:10px; color:rgba(0,0,0,.62); font-weight:800; text-align:center;">
              Code rotates after a successful connect (order created).
            </div>
          </div>
        </div>

        <div class="right">
          <div class="panel">
            <h4>How it works</h4>
            <p>Customer enters the code in the Customer UI to securely pair with this lane and start ordering.</p>
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

    // Open customer UI
    function openCustomer(){
      window.open("/customer", "_blank", "noopener,noreferrer");
    }

    // Copy code (clipboard API)
    const copyBtn = document.getElementById("copyBtn");
    const codeText = document.getElementById("codeText");
    const copyHint = document.getElementById("copyHint");

    async function copyCode(){
      const code = (codeText?.textContent || "").trim();
      if (!code) return;

      try{
        await navigator.clipboard.writeText(code);
        copyHint.textContent = "✅ Copied! Now paste it in Customer UI to connect.";
      }catch(e){
        // Fallback
        const ta = document.createElement("textarea");
        ta.value = code;
        ta.style.position = "fixed";
        ta.style.left = "-9999px";
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        ta.remove();
        copyHint.textContent = "✅ Copied! Now paste it in Customer UI to connect.";
      }

      setTimeout(()=> {
        copyHint.textContent = "👉 Copy this code → Open Customer UI → Paste & Connect";
      }, 2200);
    }

    copyBtn?.addEventListener("click", copyCode);
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
