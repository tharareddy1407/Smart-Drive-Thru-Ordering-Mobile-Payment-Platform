from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .routes.pages import router as pages_router
from .routes.customer_api import router as customer_router
from .routes.cashier_api import router as cashier_router
from .routes.payment_api import router as payment_router

from .websockets.customer_ws import router as customer_ws_router
from .websockets.order_ws import router as order_ws_router
from .websockets.call_ws import router as call_ws_router

app = FastAPI(
    title="Smart Drive-Thru Ordering Platform (Real-Time Voice Ordering, Secure Lane Connection & Mobile Payment)"
)

# Static
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Routers
app.include_router(pages_router)
app.include_router(customer_router)
app.include_router(cashier_router)
app.include_router(payment_router)

# WebSocket routers
app.include_router(customer_ws_router)
app.include_router(order_ws_router)
app.include_router(call_ws_router)
