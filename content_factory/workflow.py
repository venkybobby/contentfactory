from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STAGES = ("intake", "research", "editorial_approval", "script", "script_approval",
          "preproduction", "generation", "assembly", "qa", "final_approval",
          "distribution", "analytics")
APPROVAL_STAGES = {"editorial_approval", "script_approval", "final_approval"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class CaseSpec:
    case_id: str
    title: str
    angle: str
    target_minutes: int = 8
    sources: list[str] | None = None
    status: str = "draft"

    def __post_init__(self) -> None:
        if not self.case_id.startswith("AIC-"):
            raise ValueError("case_id must start with AIC-")
        if not 1 <= self.target_minutes <= 30:
            raise ValueError("target_minutes must be between 1 and 30")

    @classmethod
    def load(cls, path: Path) -> "CaseSpec":
        return cls(**json.loads(path.read_text(encoding="utf-8")))


class ArtifactStore:
    def __init__(self, root: Path, case_id: str):
        self.path = root / "runs" / case_id
        self.path.mkdir(parents=True, exist_ok=True)

    def read(self, name: str) -> dict[str, Any]:
        return json.loads((self.path / f"{name}.json").read_text(encoding="utf-8"))

    def write(self, name: str, value: dict[str, Any]) -> None:
        (self.path / f"{name}.json").write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


class Factory:
    def __init__(self, root: Path, provider: str = "demo"):
        self.root = root
        self.provider = provider

    def run_dir(self, case_id: str) -> Path:
        return self.root / "runs" / case_id

    def initialize(self, spec: CaseSpec, reset: bool = False) -> Path:
        store = ArtifactStore(self.root, spec.case_id)
        path = store.path / "manifest.json"
        if reset or not path.exists():
            store.write("manifest", {"case": asdict(spec), "provider": self.provider,
                        "created_at": utc_now(), "stages": {x: "pending" for x in STAGES}})
        return path

    def run(self, spec: CaseSpec, auto_approve: bool = False, reset: bool = False) -> dict[str, Any]:
        from .pipeline import HANDLERS, PipelineContext
        self.initialize(spec, reset=reset)
        store = ArtifactStore(self.root, spec.case_id)
        manifest = store.read("manifest")
        context = PipelineContext(self.root, spec, store, self.provider)
        for stage in STAGES:
            state = manifest["stages"][stage]
            if state == "complete":
                continue
            if stage in APPROVAL_STAGES:
                if not auto_approve:
                    manifest["stages"][stage] = "waiting_for_human"
                    break
                store.write(stage, {"stage": stage, "approved_by": "auto-approve",
                                    "approved_at": utc_now(), "warning": "Use named human approval in production."})
            else:
                manifest["stages"][stage] = "running"
                store.write("manifest", manifest)
                HANDLERS[stage](context)
            manifest["stages"][stage] = "complete"
        manifest["updated_at"] = utc_now()
        store.write("manifest", manifest)
        return manifest

    def approve(self, case_id: str, stage: str, approved_by: str) -> dict[str, Any]:
        if stage not in APPROVAL_STAGES:
            raise ValueError(f"{stage} is not an approval stage")
        store = ArtifactStore(self.root, case_id)
        manifest = store.read("manifest")
        if manifest["stages"][stage] != "waiting_for_human":
            raise ValueError(f"{stage} is not waiting for approval")
        store.write(stage, {"stage": stage, "approved_by": approved_by, "approved_at": utc_now()})
        manifest["stages"][stage] = "complete"
        store.write("manifest", manifest)
        return manifest

    def status(self, case_id: str) -> dict[str, Any]:
        return ArtifactStore(self.root, case_id).read("manifest")
