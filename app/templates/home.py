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