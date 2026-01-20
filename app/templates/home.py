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
      --muted2: rgba(255,255,255,0.72);
      --shadow: 0 22px 70px rgba(0,0,0,0.28);
      --stroke: rgba(255,255,255,0.16);
      --card: rgba(0,0,0,0.48);
      --card2: rgba(255,255,255,0.08);
      --accent: #22d3ee;
      --accent2:#a78bfa;
      --ok: #22c55e;
      --warn: #f59e0b;
    }

    *{ box-sizing:border-box; margin:0; padding:0; }
    html, body{ height:100%; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; }

    body{
      background-color:#0b1220;
      background-image:
        linear-gradient(rgba(0,0,0,0.12), rgba(0,0,0,0.24)),
        url('/static/BG-desktop.png');
      background-repeat:no-repeat;
      background-size: contain;
      background-position: center center;
    }

    /* Mobile background */
    @media (max-width: 768px){
      body{
        background-image:
          linear-gradient(rgba(0,0,0,0.14), rgba(0,0,0,0.30)),
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
      padding: 20px 16px 24px;
      text-align:center;
      position: relative;
      gap: 14px;
    }

    /* Top pitch card */
    .pitch{
      width: min(980px, 94vw);
      border-radius: 18px;
      background: var(--card);
      border: 1px solid var(--stroke);
      box-shadow: var(--shadow);
      backdrop-filter: blur(12px) saturate(140%);
      -webkit-backdrop-filter: blur(12px) saturate(140%);
      padding: 14px 16px;
      text-align:left;
    }

    .pitchTitle{
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:12px;
      flex-wrap: wrap;
    }
    .pitchTitle h1{
      font-size: clamp(16px, 2.2vw, 22px);
      margin:0;
      letter-spacing: .2px;
      font-weight: 950;
      color: var(--text);
    }
    .badgeRow{
      display:flex; gap:8px; flex-wrap:wrap;
    }
    .badge{
      display:inline-flex;
      align-items:center;
      gap:8px;
      padding: 7px 10px;
      border-radius: 999px;
      background: rgba(255,255,255,0.08);
      border: 1px solid rgba(255,255,255,0.14);
      color: rgba(255,255,255,0.88);
      font-size: 12px;
      font-weight: 800;
      white-space: nowrap;
    }
    .dot{
      width:10px; height:10px; border-radius:50%;
      background: rgba(148,163,184,0.9);
      box-shadow: 0 0 0 4px rgba(148,163,184,0.16);
    }
    .dot.ok{ background: var(--ok); box-shadow: 0 0 0 4px rgba(34,197,94,0.16); }
    .dot.warn{ background: var(--warn); box-shadow: 0 0 0 4px rgba(245,158,11,0.16); }

    .pitchCopy{
      margin-top: 10px;
      color: rgba(255,255,255,0.88);
      line-height: 1.45;
      font-size: 14px;
    }
    .pitchCopy b{ color: var(--text); }

    .kpiRow{
      margin-top: 10px;
      display:grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }
    @media (max-width: 720px){
      .kpiRow{ grid-template-columns: 1fr; }
    }
    .kpi{
      border-radius: 14px;
      background: rgba(255,255,255,0.07);
      border: 1px solid rgba(255,255,255,0.12);
      padding: 10px 12px;
      text-align:left;
    }
    .kpi .k{ font-size: 12px; color: var(--muted2); font-weight: 800; }
    .kpi .v{ margin-top: 6px; font-size: 13px; color: rgba(255,255,255,0.90); line-height:1.35; }

    /* Wrap buttons + popover together */
    .interactionArea{
      display:flex;
      flex-direction:column;
      align-items:center;
      justify-content:center;
      width: 100%;
      margin-top: 2px;
    }

    .circleRow{
      display:flex;
      gap: 28px;
      flex-wrap: wrap;
      align-items:center;
      justify-content:center;
      margin-top: 120px;
    }

    .circleBtn{
      width: 160px;
      height: 160px;
      border-radius: 999px;

      border: 2px solid rgba(255,255,255,0.20);
      background: rgba(90,110,130,0.48);
      backdrop-filter: blur(10px) saturate(140%);
      -webkit-backdrop-filter: blur(10px) saturate(140%);

      color: var(--text);
      font-size: 22px;
      font-weight: 950;
      cursor: pointer;

      box-shadow: var(--shadow);
      transition: transform .16s ease, background .16s ease, border .16s ease;
    }

    .circleBtn:hover{
      transform: translateY(-4px) scale(1.03);
      background: rgba(90,110,130,0.62);
      border-color: rgba(255,255,255,0.30);
    }

    .popover{
      display:none;
      margin-top: 16px;
      width: min(780px, 92vw);
      padding: 14px 16px;
      border-radius: 16px;
      background: rgba(0,0,0,0.55);
      border: 1px solid rgba(255,255,255,0.16);
      color: rgba(255,255,255,0.92);
      box-shadow: var(--shadow);
      backdrop-filter: blur(12px) saturate(140%);
      -webkit-backdrop-filter: blur(12px) saturate(140%);
      line-height: 1.4;
      font-size: 15px;
      text-align:left;
    }
    .popover.show{ display:block; }

    .actions{
      margin-top: 10px;
      display:flex;
      gap: 10px;
      flex-wrap: wrap;
      justify-content:flex-start;
    }

    .linkBtn{
      text-decoration:none;
      padding: 10px 14px;
      border-radius: 12px;
      font-weight: 900;
      color: rgba(255,255,255,0.92);
      background: rgba(255,255,255,0.10);
      border: 1px solid rgba(255,255,255,0.16);
      transition: transform .12s ease, background .12s ease;
      display:inline-flex;
      align-items:center;
      gap:8px;
    }
    .linkBtn:hover{
      transform: translateY(-1px);
      background: rgba(255,255,255,0.14);
    }

    /* Collapsible demo flow */
    .demoFlow{
      margin-top: 14px;
      width: min(980px, 94vw);
      border-radius: 18px;
      background: rgba(0,0,0,0.44);
      border: 1px solid rgba(255,255,255,0.14);
      box-shadow: 0 16px 40px rgba(0,0,0,0.22);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      overflow:hidden;
      text-align:left;
    }

    .demoToggle{
      width:100%;
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:12px;
      padding: 12px 14px;
      cursor:pointer;
      background: rgba(255,255,255,0.06);
      border: none;
      color: rgba(255,255,255,0.92);
      font-weight: 950;
      letter-spacing:.2px;
      font-size: 14px;
    }
    .demoToggle .right{
      color: rgba(255,255,255,0.70);
      font-weight: 800;
      font-size: 12px;
      white-space: nowrap;
    }

    .demoSteps{
      display:none;
      padding: 12px 16px 14px;
      color: rgba(255,255,255,0.88);
      font-size: 14px;
      line-height:1.45;
    }
    .demoSteps ol{
      padding-left: 18px;
      margin: 0;
    }
    .demoSteps li{ margin: 7px 0; }
    .demoSteps b{ color: var(--text); }

    /* Footer tip */
    .tip{
      width: min(980px, 94vw);
      padding: 10px 12px;
      border-radius: 14px;
      background: rgba(0,0,0,0.36);
      border: 1px solid rgba(255,255,255,0.12);
      color: var(--muted);
      font-size: 13px;
      text-shadow: 0 10px 24px rgba(0,0,0,0.45);
      backdrop-filter: blur(10px);
      -webkit-backdrop-filter: blur(10px);
      text-align:left;
      margin-top: 8px;
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

    @media (max-width: 520px){
      body{ overflow:auto; }
      .circleRow{ margin-top: 150px; gap: 18px; }
      .circleBtn{ width: 120px; height: 120px; font-size: 18px; }
      .actions{ justify-content:center; }
      .popover{ text-align:left; }
      .pitch{ text-align:left; }
    }
  </style>
</head>

<body>
  <div class="hero">


    <!-- Buttons + popover -->
    <div class="interactionArea">
      <div class="circleRow">
        <button type="button" class="circleBtn" data-role="lane">Lane</button>
        <button type="button" class="circleBtn" data-role="customer">Customer</button>
        <button type="button" class="circleBtn" data-role="cashier">Cashier</button>
      </div>

      <div class="popover" id="infoBox"></div>
    </div>

    <!-- Collapsible demo flow -->
    <div class="demoFlow">
      <button class="demoToggle" id="demoToggle" type="button">
        <span id="demoArrow">▶</span>
        <span>Live Demo Flow</span>
        <span class="right">~60 seconds</span>
      </button>
      <div class="demoSteps" id="demoSteps">
        <ol>
          <li><b>Open Lane UI</b> first and copy the rotating <b>4-digit code</b>.</li>
          <li><b>Open Customer</b>, click <b>I’m Here</b>, then paste the code to connect.</li>
          <li><b>Open Cashier</b>, click <b>Refresh</b>, select the order, and click <b>Join</b>.</li>
          <li>Customer clicks <b>Call</b> → Cashier can <b>Accept</b>, <b>Reject</b>, or <b>Queue</b>.</li>
          <li>Cashier confirms the order and sends a <b>payment request</b>.</li>
          <li>Customer approves payment → confirmation appears → proceed to <b>pickup window</b>.</li>
          <li>After success, the <b>lane code refreshes</b> for the next vehicle.</li>
        </ol>
      </div>
    </div>

    <div class="tip">
      <b>Recommended setup:</b> Customer on phone • Cashier on laptop. WebRTC mic requires HTTPS (or localhost).
    </div>
  </div>

  <script>
    document.addEventListener("DOMContentLoaded", () => {
      const box = document.getElementById("infoBox");
      const buttons = document.querySelectorAll(".circleBtn");
      const area = document.querySelector(".interactionArea");

      const demoToggle = document.getElementById("demoToggle");
      const demoSteps = document.getElementById("demoSteps");
      const demoArrow = document.getElementById("demoArrow");

      function render(role){
        box.classList.add("show");

        if(role === "lane"){
          box.innerHTML = `
            <b>Lane:</b> Shows a rotating 4-digit pairing code for a specific lane.
            <div class="actions">
              <a class="linkBtn" href="/lane/L1" target="_blank" rel="noopener">Open Lane L1 →</a>
              <a class="linkBtn" href="/lane/L2" target="_blank" rel="noopener">Open Lane L2 →</a>
            </div>
          `;
        } else if(role === "customer"){
          box.innerHTML = `
            <b>Customer:</b> Check-in, enter the lane code, chat/call the cashier, and pay on your phone.
            <div class="actions">
              <a class="linkBtn" href="/customer" target="_blank" rel="noopener">Open Customer Portal →</a>
            </div>
          `;
        } else if(role === "cashier"){
          box.innerHTML = `
            <b>Cashier:</b> Join incoming orders, chat/call the customer, confirm total, and send payment request.
            <div class="actions">
              <a class="linkBtn" href="/cashier" target="_blank" rel="noopener">Open Cashier Console →</a>
            </div>
          `;
        }
      }

      function openRole(role){
        if(role === "lane"){
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
        btn.addEventListener("focus", () => render(btn.dataset.role));
        btn.addEventListener("click", () => openRole(btn.dataset.role));
      });

      // Hide popover when cursor leaves BOTH buttons and popover area
      area.addEventListener("mouseleave", () => box.classList.remove("show"));

      // Hide popover if user taps elsewhere
      document.addEventListener("click", (e) => {
        if(!area.contains(e.target)){
          box.classList.remove("show");
        }
      });

      // Demo flow toggle
      demoToggle.addEventListener("click", () => {
        const isOpen = demoSteps.style.display === "block";
        demoSteps.style.display = isOpen ? "none" : "block";
        demoArrow.textContent = isOpen ? "▶" : "▼";
      });
    });
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
