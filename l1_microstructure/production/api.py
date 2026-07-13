"""Authenticated localhost control API for the production daemon."""

from __future__ import annotations

import asyncio
import hmac
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .runtime import ProductionRuntime


class ControlRequest(BaseModel):
    reason: str = "operator request"
    confirmation: str | None = None


class ModelPromotionRequest(BaseModel):
    symbol: str
    run_id: str
    confirmation: str


def create_app(runtime: ProductionRuntime, api_token: str) -> FastAPI:
    if not api_token:
        raise ValueError("production control API requires a non-empty token")
    app = FastAPI(title="StatArb Gemini Trading Daemon", docs_url=None, redoc_url=None)

    @app.exception_handler(ValueError)
    async def invalid_operation(_, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    def authorize(authorization: Annotated[str | None, Header()] = None) -> None:
        expected = f"Bearer {api_token}"
        if authorization is None or not hmac.compare_digest(authorization, expected):
            raise HTTPException(status_code=401, detail="invalid control token")

    @app.get("/health")
    def health(_: None = Depends(authorize)) -> dict:
        return runtime.health_report().to_dict()

    @app.get("/ready")
    def ready(_: None = Depends(authorize)) -> JSONResponse:
        report = runtime.readiness_report()
        return JSONResponse(status_code=200 if report.ready else 503, content=report.to_dict())

    @app.get("/status")
    def status(_: None = Depends(authorize)) -> dict:
        return runtime.status()

    @app.get("/events")
    def events(limit: int = 100, _: None = Depends(authorize)) -> list[dict]:
        return runtime.ledger.recent_events(min(max(limit, 1), 500))

    @app.get("/alerts")
    def alerts(limit: int = 100, _: None = Depends(authorize)) -> list[dict]:
        return runtime.recent_alerts(min(max(limit, 1), 500))

    @app.post("/control/pause")
    def pause(request: ControlRequest, _: None = Depends(authorize)) -> dict:
        runtime.pause(request.reason)
        return runtime.status()

    @app.post("/control/resume")
    def resume(request: ControlRequest, _: None = Depends(authorize)) -> dict:
        runtime.resume()
        return runtime.status()

    @app.post("/control/halt")
    def halt(request: ControlRequest, _: None = Depends(authorize)) -> dict:
        _require_confirmation(request.confirmation, "HALT")
        runtime.halt(request.reason)
        return runtime.status()

    @app.post("/control/clear-kill-switch")
    def clear_kill_switch(request: ControlRequest, _: None = Depends(authorize)) -> dict:
        _require_confirmation(request.confirmation, "CLEAR KILL SWITCH")
        runtime.clear_kill_switch()
        return runtime.status()

    @app.post("/control/flatten")
    def flatten(request: ControlRequest, _: None = Depends(authorize)) -> dict:
        _require_confirmation(request.confirmation, "FLATTEN")
        runtime.flatten()
        return runtime.status()

    @app.post("/models/promote")
    def promote_model(request: ModelPromotionRequest, _: None = Depends(authorize)) -> dict:
        _require_confirmation(request.confirmation, f"PROMOTE {request.symbol.upper()}")
        runtime.promote_model(request.symbol, request.run_id)
        return runtime.status()

    @app.websocket("/stream")
    async def stream(websocket: WebSocket) -> None:
        authorization = websocket.headers.get("authorization", "")
        if not hmac.compare_digest(authorization, f"Bearer {api_token}"):
            await websocket.close(code=1008)
            return
        await websocket.accept()
        try:
            while True:
                await websocket.send_json(runtime.status())
                await asyncio.sleep(1.0)
        except WebSocketDisconnect:
            return

    return app


def _require_confirmation(actual: str | None, expected: str) -> None:
    if actual != expected:
        raise HTTPException(status_code=400, detail=f"confirmation must equal {expected!r}")
