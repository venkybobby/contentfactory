from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from . import __version__
from .workflow import CaseSpec, Factory


class EpisodeRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    case_id: str = Field(pattern=r"^AIC-[A-Za-z0-9-]{1,40}$")
    title: str = Field(min_length=3, max_length=200)
    angle: str = Field(min_length=10, max_length=2_000)
    target_minutes: int = Field(default=8, ge=1, le=30)
    sources: list[str] = Field(default_factory=list, max_length=25)
    provider: str = Field(default="demo", pattern=r"^(demo|openai|nvidia)$")


class EpisodeAccepted(BaseModel):
    case_id: str
    status: str
    status_url: str


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)
    approved_by: str = Field(min_length=2, max_length=100)


class LoginRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)
    api_token: str = Field(min_length=16, max_length=512)


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str


def factory_root() -> Path:
    root = Path(os.environ.get("CONTENT_FACTORY_ROOT", Path.cwd()))
    root.mkdir(parents=True, exist_ok=True)
    return root


def _session_cookie(secret: str, expires_at: int) -> str:
    payload = str(expires_at)
    signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}.{signature}".encode()).decode()


def _valid_session(value: str | None, secret: str) -> bool:
    if not value:
        return False
    try:
        payload, signature = base64.urlsafe_b64decode(value.encode()).decode().split(".", 1)
        expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return int(payload) > int(time.time()) and hmac.compare_digest(signature, expected)
    except (ValueError, TypeError):
        return False


async def authorize(request: Request, authorization: str | None = Header(default=None)) -> None:
    expected = os.environ.get("API_TOKEN")
    if not expected:
        if os.environ.get("ENV") == "production":
            raise HTTPException(status_code=503, detail={"code": "API_NOT_CONFIGURED", "message": "API_TOKEN is not configured"})
        return
    supplied = authorization.removeprefix("Bearer ") if authorization else ""
    if not secrets.compare_digest(supplied, expected) and not _valid_session(request.cookies.get("cf_session"), expected):
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Valid bearer token required"})


def execute_episode(root: Path, spec: CaseSpec, provider: str) -> None:
    try:
        Factory(root, provider).run(spec, auto_approve=False, reset=True)
    except Exception as exc:
        run_dir = root / "runs" / spec.case_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "failure.json").write_text(json.dumps({"error": type(exc).__name__, "message": str(exc)}, indent=2), encoding="utf-8")
        raise


def resume_episode(root: Path, spec: CaseSpec, provider: str) -> None:
    failure = root / "runs" / spec.case_id / "failure.json"
    failure.unlink(missing_ok=True)
    execute_episode(root, spec, provider)


app = FastAPI(title="The AI Confession Content Factory", version=__version__)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Factory-Version"] = __version__
    return response


@app.get("/health")
async def health() -> dict[str, object]:
    return {"app": "contentfactory", "version": __version__, "status": "ok", "db_ok": True}


@app.post("/api/v1/auth/session", status_code=204)
async def create_session(payload: LoginRequest, response: Response) -> Response:
    expected = os.environ.get("API_TOKEN")
    if not expected:
        raise HTTPException(status_code=503, detail={"code": "API_NOT_CONFIGURED", "message": "API_TOKEN is not configured"})
    if not secrets.compare_digest(payload.api_token, expected):
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Invalid API token"})
    expires_at = int(time.time()) + 8 * 60 * 60
    response.status_code = 204
    response.set_cookie("cf_session", _session_cookie(expected, expires_at), max_age=8 * 60 * 60,
                        httponly=True, secure=os.environ.get("ENV") == "production", samesite="strict", path="/")
    return response


@app.delete("/api/v1/auth/session", status_code=204)
async def delete_session(response: Response) -> Response:
    response.status_code = 204
    response.delete_cookie("cf_session", path="/")
    return response


@app.get("/api/v1/auth/session", dependencies=[Depends(authorize)])
async def session_status() -> dict[str, bool]:
    return {"authenticated": True}


@app.post("/api/v1/episodes", response_model=EpisodeAccepted, status_code=202, dependencies=[Depends(authorize)])
async def create_episode(payload: EpisodeRequest, background_tasks: BackgroundTasks) -> EpisodeAccepted:
    root = factory_root()
    manifest = root / "runs" / payload.case_id / "manifest.json"
    if manifest.exists():
        raise HTTPException(status_code=409, detail={"code": "EPISODE_EXISTS", "message": "Use a new case_id"})
    spec = CaseSpec(payload.case_id, payload.title, payload.angle, payload.target_minutes, payload.sources)
    background_tasks.add_task(execute_episode, root, spec, payload.provider)
    return EpisodeAccepted(case_id=payload.case_id, status="accepted", status_url=f"/api/v1/episodes/{payload.case_id}")


def _episode_list(root: Path) -> list[dict]:
    runs = root / "runs"
    if not runs.exists():
        return []
    episodes = []
    for manifest_path in sorted(runs.glob("*/manifest.json"), key=lambda path: path.stat().st_mtime, reverse=True):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        failure_path = manifest_path.parent / "failure.json"
        manifest["failed"] = failure_path.exists()
        manifest["video_ready"] = (manifest_path.parent / f"{manifest['case']['case_id']}.mp4").exists()
        episodes.append(manifest)
    return episodes


@app.get("/api/v1/episodes", dependencies=[Depends(authorize)])
async def list_episodes() -> list[dict]:
    return await asyncio.to_thread(_episode_list, factory_root())


@app.get("/api/v1/episodes/{case_id}", dependencies=[Depends(authorize)])
async def episode_status(case_id: str) -> dict:
    root = factory_root()
    manifest = root / "runs" / case_id / "manifest.json"
    failure = root / "runs" / case_id / "failure.json"
    if failure.exists():
        return {"case_id": case_id, "status": "failed", "failure": json.loads(failure.read_text(encoding="utf-8"))}
    if not manifest.exists():
        raise HTTPException(status_code=404, detail={"code": "EPISODE_NOT_FOUND", "message": "Unknown case_id"})
    return json.loads(manifest.read_text(encoding="utf-8"))


@app.post("/api/v1/episodes/{case_id}/retry", status_code=202, dependencies=[Depends(authorize)])
async def retry_episode(case_id: str, background_tasks: BackgroundTasks) -> dict[str, str]:
    manifest_path = factory_root() / "runs" / case_id / "manifest.json"
    failure_path = manifest_path.parent / "failure.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail={"code": "EPISODE_NOT_FOUND", "message": "Unknown case_id"})
    if not failure_path.exists():
        raise HTTPException(status_code=409, detail={"code": "EPISODE_NOT_FAILED", "message": "Episode has no recorded failure"})
    manifest = await asyncio.to_thread(lambda: json.loads(manifest_path.read_text(encoding="utf-8")))
    spec = CaseSpec(**manifest["case"])
    background_tasks.add_task(resume_episode, factory_root(), spec, manifest.get("provider", "demo"))
    return {"case_id": case_id, "status": "retrying"}


@app.post("/api/v1/episodes/{case_id}/approvals/{stage}", status_code=202, dependencies=[Depends(authorize)])
async def approve_episode(case_id: str, stage: str, payload: ApprovalRequest,
                          background_tasks: BackgroundTasks) -> dict[str, str]:
    root = factory_root()
    factory = Factory(root)
    manifest_path = root / "runs" / case_id / "manifest.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail={"code": "EPISODE_NOT_FOUND", "message": "Unknown case_id"})
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    try:
        factory.approve(case_id, stage, payload.approved_by)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "APPROVAL_REJECTED", "message": str(exc)}) from exc
    spec = CaseSpec(**manifest["case"])
    provider = manifest.get("provider", "demo")
    background_tasks.add_task(Factory(root, provider).run, spec, False, False)
    return {"case_id": case_id, "stage": stage, "status": "approved"}


@app.get("/api/v1/episodes/{case_id}/video", dependencies=[Depends(authorize)])
async def episode_video(case_id: str) -> FileResponse:
    video = factory_root() / "runs" / case_id / f"{case_id}.mp4"
    if not video.exists():
        raise HTTPException(status_code=404, detail={"code": "VIDEO_NOT_READY", "message": "Video is not available"})
    return FileResponse(video, media_type="video/mp4", filename=video.name)


@app.get("/api/v1/episodes/{case_id}/artifacts/{artifact}", dependencies=[Depends(authorize)])
async def episode_artifact(case_id: str, artifact: str) -> dict:
    allowed = {"research", "script", "preproduction", "generation", "assembly", "qa", "distribution", "analytics"}
    if artifact not in allowed:
        raise HTTPException(status_code=404, detail={"code": "ARTIFACT_NOT_FOUND", "message": "Unknown artifact"})
    path = factory_root() / "runs" / case_id / f"{artifact}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail={"code": "ARTIFACT_NOT_READY", "message": "Artifact is not available"})
    return await asyncio.to_thread(lambda: json.loads(path.read_text(encoding="utf-8")))


static_dir = Path(os.environ.get("STATIC_DIR", Path(__file__).parent.parent / "frontend_dist"))
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
