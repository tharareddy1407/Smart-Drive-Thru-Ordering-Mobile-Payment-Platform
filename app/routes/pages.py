from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from ..helpers import current_lane_code
from ..templates.home import HOME_HTML
from ..templates.lane import LANE_HTML_TEMPLATE
from ..templates.cashier import CASHIER_HTML
from ..templates.customer import CUSTOMER_HTML

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    return HTMLResponse(HOME_HTML)

@router.get("/lane/{lane_id}", response_class=HTMLResponse)
def lane(lane_id: str) -> HTMLResponse:
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

@router.get("/cashier", response_class=HTMLResponse)
def cashier_page() -> HTMLResponse:
    return HTMLResponse(CASHIER_HTML)

@router.get("/customer", response_class=HTMLResponse)
def customer_page() -> HTMLResponse:
    return HTMLResponse(CUSTOMER_HTML)
