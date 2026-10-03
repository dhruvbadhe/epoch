"""FastAPI app and routes only. Shapes: docs/api_contract.md.

Run from the repo root:  .venv/bin/python -m uvicorn backend.main:app --port 8000
(no --reload and one worker during the demo, or conversation memory is lost)
"""
import logging
import os
from typing import Annotated, Any, Literal

from dotenv import load_dotenv
from fastapi import FastAPI, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import data_loader

load_dotenv(data_loader.ROOT / "backend" / ".env")   # keys live here; before anything reads a key
load_dotenv(data_loader.ROOT / ".env")

from . import advice, conversation, db, engine_api, freshness, lookups, market, querylog, replies, speech, state, weather  # noqa: E402
from .errors import ApiError  # noqa: E402
from . import whatsapp_adapter  # noqa: E402  (reads WA_PROVIDER / D360_API_KEY at import)
from .whatsapp import cloud_api  # noqa: E402  (Meta Cloud API at /whatsapp/webhook; unused without its keys)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("sellsmart.api")

MAX_AUDIO_BYTES = 25 * 1024 * 1024               # upload limit of the speech-to-text services
ENGINE_HEADER = "X-SellSmart-Engine"             # "real" or "fake": where the numbers came from

app = FastAPI(title="SahiDaam API", version="1.0",
              description="SahiDaam (सही दाम): where and when to sell onion, tomato and soybean in Maharashtra for the most money in hand.")


# ---------- errors: always {"error": "...", "field": "..."}, never a stack trace ----------

def _error(message: str, field: str | None = None, status: int = 400) -> JSONResponse:
    return JSONResponse({"error": message, "field": field}, status_code=status)


@app.middleware("http")
async def _no_stack_traces(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception:
        log.exception("unhandled error on %s %s", request.method, request.url.path)
        return _error("Internal server error", status=500)


# Added after the catch-all so CORS wraps it: error responses carry CORS headers too.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"]
    + [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()],
    allow_methods=["*"], allow_headers=["*"], expose_headers=[ENGINE_HEADER])


@app.exception_handler(ApiError)
async def _api_error(request: Request, exc: ApiError):
    return _error(exc.message, exc.field, exc.status)


@app.exception_handler(RequestValidationError)
async def _validation_error(request: Request, exc: RequestValidationError):
    first = exc.errors()[0]
    if first["type"] == "json_invalid":
        return _error("Request body is not valid JSON")
    path = ".".join(str(part) for part in first["loc"] if part not in ("body", "query", "path"))
    return _error(f"{path}: {first['msg']}" if path else first["msg"], path or None)


@app.exception_handler(StarletteHTTPException)
async def _http_error(request: Request, exc: StarletteHTTPException):
    return _error(str(exc.detail), status=exc.status_code)


def _engine(call):
    """Run an engine call; its ValueError is the caller's bad input, so it becomes a 400."""
    try:
        return call()
    except ValueError as exc:
        raise ApiError(str(exc) or "Invalid input") from exc
    except engine_api.EngineUnavailable as exc:
        raise ApiError(str(exc), status=503) from exc


# ---------- request shapes ------------------------------------------------

Crop = Literal["onion", "tomato", "soybean"]
Quantity = Annotated[float, Field(gt=0, allow_inf_nan=False)]
CashDays = Annotated[int, Field(ge=0, strict=True)]


class AdviseRequest(BaseModel):
    crop: Crop
    quantity_qtl: Quantity
    village: str
    lot_condition: Any = None                    # checked per crop in advice.check_lot_condition
    cash_needed_in_days: CashDays | None = None
    blocked_mandis: list[str] = []
    overrides: dict | None = None
    lang: Literal["mr", "hi", "en"] = "mr"


class Lot(BaseModel):
    member: str | int
    crop: Crop
    quantity_qtl: Quantity
    village: str
    lot_condition: Any = None
    cash_needed_in_days: CashDays | None = None


class FpoPlanRequest(BaseModel):
    lots: list[Lot] = Field(min_length=1)
    blocked_mandis: list[str] = []
    mandi_cap_qtl_per_day: Annotated[float, Field(gt=0, allow_inf_nan=False)] | None = None
    collection_centre: Any = None                # null | village name | {name, lat, lon}
    overrides: dict | None = None


def _collection_centre(value) -> dict | None:
    """null = config default; a village name or {name, lat, lon} -> the config.yaml shape."""
    if value is None or value == "":
        return None
    if isinstance(value, str):
        village = advice.resolve_village(value, "collection_centre")
        return {"name": village["village"], "lat": village["lat"], "lon": village["lon"]}
    numbers_ok = isinstance(value, dict) and all(
        isinstance(value.get(k), (int, float)) and not isinstance(value.get(k), bool) for k in ("lat", "lon"))
    if not numbers_ok or not isinstance(value.get("name"), str) or not value["name"].strip():
        raise ApiError("collection_centre must be null, a village name, or {name, lat, lon}",
                       "collection_centre")
    return {"name": value["name"].strip(), "lat": value["lat"], "lon": value["lon"]}


# ---------- advice --------------------------------------------------------

@app.post("/advise")
def advise(req: AdviseRequest, response: Response):
    village = advice.resolve_village(req.village)
    advice.check_lot_condition(req.crop, req.lot_condition)
    blocked = advice.check_blocked(req.blocked_mandis)
    result = _engine(lambda: advice.get_advice(
        req.crop, req.quantity_qtl, village["village"], lot_condition=req.lot_condition,
        cash_needed_in_days=req.cash_needed_in_days, blocked_mandis=blocked,
        overrides=req.overrides, lang=req.lang))
    response.headers[ENGINE_HEADER] = "fake" if engine_api.using_fake("advise") else "real"
    db.log_query("api", None, req.lang, req.crop, req.quantity_qtl, village["village"], result)
    try:                                             # response layer only; never breaks the advice
        result["freshness"] = freshness.estimate(req.crop, req.lot_condition, req.lang)
    except Exception:
        log.exception("freshness estimate failed")
        result["freshness"] = None
    return result


@app.post("/fpo/plan")
def fpo_plan(req: FpoPlanRequest, response: Response):
    lots = []
    for i, lot in enumerate(req.lots):
        village = advice.resolve_village(lot.village, f"lots.{i}.village")
        advice.check_lot_condition(lot.crop, lot.lot_condition, f"lots.{i}.lot_condition")
        lots.append({"member": str(lot.member), "crop": lot.crop, "quantity_qtl": lot.quantity_qtl,
                     "village": village["village"], "lot_condition": lot.lot_condition,
                     "cash_needed_in_days": lot.cash_needed_in_days})
    blocked = advice.check_blocked(req.blocked_mandis)
    centre = _collection_centre(req.collection_centre)
    result = _engine(lambda: engine_api.fpo_plan(
        lots, blocked_mandis=blocked, mandi_cap_qtl_per_day=req.mandi_cap_qtl_per_day,
        collection_centre=centre, overrides=req.overrides))
    response.headers[ENGINE_HEADER] = "fake" if engine_api.using_fake("fpo_plan") else "real"
    return result


# ---------- WhatsApp ------------------------------------------------------

@app.post("/message")
async def message(request: Request):
    """JSON {sender, text}, or multipart with sender and an audio file (a voice note)."""
    if request.headers.get("content-type", "").startswith("multipart/form-data"):
        form = await request.form()
        sender, audio = _sender(form.get("sender")), form.get("audio")
        if audio is None or isinstance(audio, str):
            raise ApiError("audio file is required", "audio")
        data = await audio.read()
        if not data:
            raise ApiError("audio file is empty", "audio")
        if len(data) > MAX_AUDIO_BYTES:
            raise ApiError("audio file is too large", "audio")
        try:
            text = await run_in_threadpool(lambda: speech.transcribe(        # as on WhatsApp: no forced language
                data, audio.filename, audio.content_type, auto_language=True, prompt=whatsapp_adapter.VOICE_HINT))
        except speech.SpeechError as exc:
            log.error("voice note from %s not transcribed: %s", querylog.mask(sender), exc)
            querylog.append(sender, "🎤 (not understood)", replies.VOICE_FAILED)
            open_conversation = state.get(sender)
            return {"reply": replies.VOICE_FAILED, "transcript": None,
                    "state": open_conversation["state"] if open_conversation else conversation.DONE,
                    "parsed": {"crop": None, "quantity_qtl": None, "village": None}}
        result = await run_in_threadpool(conversation.handle_message, sender, text, True)
        return {**result, "transcript": text}

    try:
        body = await request.json()
    except Exception:
        raise ApiError("Request body is not valid JSON") from None
    if not isinstance(body, dict):
        raise ApiError("Request body must be a JSON object")
    sender, text = _sender(body.get("sender")), body.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ApiError("text is required", "text")
    return await run_in_threadpool(conversation.handle_message, sender, text)


def _sender(value) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)) or not str(value).strip():
        raise ApiError("sender is required", "sender")
    return str(value).strip()


@app.get("/queries")
def queries():
    return querylog.recent()


# ---------- evidence and lookups ------------------------------------------

@app.get("/backtest")
def backtest(crop: str = Query(...)):
    return lookups.backtest_view(crop)


@app.get("/market/snapshot")
def market_snapshot(crop: str = Query(...), village: str | None = None):
    """Yesterday's reported prices for the Info tab; with a village, money in hand from there."""
    crop = lookups.check_crop(crop)
    place = advice.resolve_village(village) if village else None
    try:
        return market.snapshot(crop, place)
    except Exception:                                # never a 500 for the Info tab
        log.exception("market snapshot failed for %s", crop)
        return {"crop": crop, "prices_as_of": data_loader.as_of_date(), "snapshot_date": None, "basis": "",
                "reporting": [], "highest_price": None, "lowest_price": None, "spread": None,
                "not_reporting": [], "series_dates": [], "series_7d": [], "village": village,
                "money_in_hand": None, "message": "The market snapshot is not available right now."}


@app.get("/weather")
def weather_now(village: str = Query(...)):
    """Display-only weather for the village (Open-Meteo); never used in any number."""
    return weather.current(advice.resolve_village(village))


@app.get("/forecast")
def forecast(crop: str = Query(...), mandi: str = Query(...),
             days: int = Query(lookups.HISTORY_DAYS, ge=1, le=730)):
    return lookups.forecast_view(crop, mandi, days)


@app.get("/mandis")
def mandis(crop: str | None = None):
    return lookups.mandis_view(crop)


@app.get("/villages")
def villages():
    return lookups.villages_view()


@app.get("/config")
def config():
    return lookups.config_view()


@app.get("/health")
def health():
    """For the integrator: which parts are real and which are still example data."""
    return {"status": "ok", "engine": engine_api.status(), "data": data_loader.sources(),
            "config_missing_keys": data_loader.config_missing_keys(),
            "speech_to_text": speech.provider()}


app.include_router(whatsapp_adapter.router)            # GET/POST /webhook, POST /wa-bridge
app.include_router(cloud_api.router)                   # /whatsapp/webhook (no clash with /webhook)

log.info("engine: %s", engine_api.status())
log.info("data: %s", data_loader.sources())

# Never serve example data: refuse to start unless the engine and every handoff file are real.
# (Only an explicit ENGINE_MODE=fake, which the backend self-tests set, skips this.)
_engine_status = engine_api.status()
_not_real = [k for k in ("advise", "fpo_plan") if _engine_status[k] != "real"] + \
    [k for k, v in data_loader.sources().items() if v != "real"]
if _not_real and _engine_status["mode"] != "fake":
    raise RuntimeError(f"not real, refusing to start: {_not_real} (engine: {_engine_status})")

db.ensure()                                          # data/sellsmart.db for inspection, if missing
