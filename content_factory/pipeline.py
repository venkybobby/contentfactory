from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from .providers import editorial_provider
from .hypergen import write_hypergen_export
from .render import ffmpeg_path, render_video, scene_cards, subtitles, synthesize_voice, wav_duration
from .workflow import ArtifactStore, CaseSpec, utc_now


@dataclass
class PipelineContext:
    root: Path
    spec: CaseSpec
    store: ArtifactStore
    provider: str


def intake(ctx: PipelineContext) -> None:
    ctx.store.write("intake", {"case": asdict(ctx.spec), "accepted_at": utc_now(),
                               "checks": {"case_id": True, "title": bool(ctx.spec.title), "angle": bool(ctx.spec.angle)}})


def research(ctx: PipelineContext) -> None:
    package = editorial_provider(ctx.provider).create_package(ctx.spec)
    sources = package.get("sources", [])
    source_ids = {item["source_id"] for item in sources}
    orphan_claims = [item["claim_id"] for item in package.get("claims", []) if item["source_id"] not in source_ids]
    ctx.store.write("research", {"sources": sources, "claims": package.get("claims", []),
                                 "provider": ctx.provider, "created_at": utc_now(),
                                 "orphan_claims": orphan_claims,
                                 "publication_blocked": ctx.provider == "demo"})
    ctx.store.write("editorial_package", package)


def script(ctx: PipelineContext) -> None:
    package = ctx.store.read("editorial_package")
    research_data = ctx.store.read("research")
    sections = package["sections"]
    words = sum(len(x["narration"].split()) for x in sections)
    ctx.store.write("script", {"title": ctx.spec.title, "sections": sections, "word_count": words,
                               "estimated_minutes": round(words / 145, 1), "claim_ids": [x["claim_id"] for x in package.get("claims", [])],
                               "publication_blocked": ctx.provider == "demo" or any(source.get("retrieval_status") == "failed" for source in research_data["sources"])})


def preproduction(ctx: PipelineContext) -> None:
    script_data = ctx.store.read("script")
    scenes = []
    for i, item in enumerate(script_data["sections"], 1):
        scenes.append({"scene": i, "section": item["section"], "narration": item["narration"],
                       "visual_prompt": f"Premium investigative documentary, photorealistic, dark blue shadows, warm skin tones. {item['section']}. Evidence-led visual, no visible trademarks, no fabricated documents.",
                       "asset_type": "generated scene card", "hypergen_prompt": f"16:9 cinematic documentary shot for {item['section']}; slow dolly; realistic practical location; restrained motion; no on-screen text."})
    ctx.store.write("preproduction", {"scenes": scenes, "aspect_ratio": "16:9", "resolution": "1920x1080"})
    write_hypergen_export(ctx.store.path, asdict(ctx.spec), script_data)


def generation(ctx: PipelineContext) -> None:
    scenes = ctx.store.read("preproduction")["scenes"]
    assets = ctx.store.path / "assets"
    cards = scene_cards(scenes, assets / "scenes")
    narration = "\n\n".join(x["narration"] for x in scenes)
    audio = assets / "narration.wav"
    synthesize_voice(narration, audio)
    srt = assets / "captions.srt"
    subtitles(scenes, wav_duration(audio), srt)
    ctx.store.write("generation", {"voice": str(audio), "captions": str(srt),
                                   "scene_assets": [str(x) for x in cards],
                                   "asset_labels": {str(x): "generated" for x in cards}})


def assembly(ctx: PipelineContext) -> None:
    assets = ctx.store.read("generation")
    output = ctx.store.path / f"{ctx.spec.case_id}.mp4"
    render_video([Path(x) for x in assets["scene_assets"]], Path(assets["voice"]), output, ffmpeg_path())
    ctx.store.write("assembly", {"video": str(output), "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                                 "bytes": output.stat().st_size})


def qa(ctx: PipelineContext) -> None:
    assembly_data = ctx.store.read("assembly")
    video = Path(assembly_data["video"])
    generation_data = ctx.store.read("generation")
    research_data = ctx.store.read("research")
    checks = {"video_exists": video.exists() and video.stat().st_size > 1000,
              "captions_exist": Path(generation_data["captions"]).exists(),
              "audio_exists": Path(generation_data["voice"]).exists(),
              "all_assets_labeled": len(generation_data["asset_labels"]) == len(generation_data["scene_assets"]),
              "claims_have_sources": not research_data["orphan_claims"],
              "sources_retrieved": bool(research_data["sources"]) and all(source.get("retrieval_status", "retrieved") == "retrieved" for source in research_data["sources"]),
              "facts_publishable": ctx.provider != "demo" and bool(research_data["sources"]) and all(source.get("retrieval_status", "retrieved") == "retrieved" for source in research_data["sources"])}
    ctx.store.write("qa", {"checks": checks, "passed_for_preview": all(v for k, v in checks.items() if k not in {"facts_publishable", "sources_retrieved"}),
                           "passed_for_publication": all(checks.values()), "review_required": True})


def distribution(ctx: PipelineContext) -> None:
    script_data = ctx.store.read("script")
    sections = script_data["sections"]
    description = f"{ctx.spec.angle}\n\n" + "\n".join(f"{i}. {x['section']}" for i, x in enumerate(sections, 1))
    package = {"youtube": {"title": ctx.spec.title, "description": description,
                            "tags": ["AI", "AI responsibility", "AI documentary", "The AI Confession"],
                            "upload_state": "draft_only"},
               "reel": {"hook": sections[0]["narration"], "cta": "Watch the full investigation."},
               "x_thread": [x["narration"] for x in sections],
               "linkedin": {"title": ctx.spec.title, "body": "\n\n".join(x["narration"] for x in sections)},
               "thumbnail": {"text": "VERIFY AI", "prompt": "One concerned professional, one evidence document, dark blue cinematic background, three words maximum."},
               "publishing_blocked": ctx.provider == "demo"}
    ctx.store.write("distribution", package)


def analytics(ctx: PipelineContext) -> None:
    ctx.store.write("analytics", {"status": "awaiting publication", "metrics": ["impressions", "ctr", "average_view_duration", "retention_30s", "comments"]})


HANDLERS: dict[str, Callable[[PipelineContext], None]] = {
    "intake": intake, "research": research, "script": script, "preproduction": preproduction,
    "generation": generation, "assembly": assembly, "qa": qa, "distribution": distribution,
    "analytics": analytics,
}
