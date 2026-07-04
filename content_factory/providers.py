from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

from .workflow import CaseSpec


SECTIONS = ("Cold Open", "Background", "Conflict", "Investigation",
            "Technical Breakdown", "Human Impact", "Venky's Verdict", "Closing")


class DemoEditorialProvider:
    def create_package(self, spec: CaseSpec) -> dict[str, Any]:
        source_note = f"The investigation begins with {len(spec.sources or [])} supplied source(s)."
        lines = [
            f"What happens when a confident machine answer enters a place where facts carry consequences? This is {spec.title}.",
            f"This case matters because {spec.angle} {source_note}",
            "The conflict begins when fluent output is mistaken for verified evidence. Confidence and accuracy are not the same thing.",
            "Investigators reconstruct the timeline, compare each material claim with primary records, and preserve contradictions instead of hiding them.",
            "A language model predicts plausible sequences of words. It can assist research, but plausibility is not proof and a citation is not verified merely because it looks authentic.",
            "The impact reaches the people relying on the decision, the professionals accountable for it, and organizations that must build review into their workflows.",
            f"Venky's verdict: {spec.angle} Use AI to accelerate the work, never to outsource responsibility.",
            "Case closed. I'm Venky, and this is The AI Confession. Real Stories. Real Evidence. Real Lessons."
        ]
        claims = [{"claim_id": f"C{i:03}", "text": url, "classification": "source supplied", "source_id": f"S{i:03}"}
                  for i, url in enumerate(spec.sources or [], 1)]
        sources = [{"source_id": f"S{i:03}", "url": url, "title": "Supplied source"}
                   for i, url in enumerate(spec.sources or [], 1)]
        return {"sections": [{"section": section, "narration": line} for section, line in zip(SECTIONS, lines)],
                "sources": sources,
                "claims": claims, "mode_notice": "Demo copy: replace with sourced OpenAI output before publication."}


class OpenAIEditorialProvider:
    def __init__(self) -> None:
        self.key = os.environ.get("OPENAI_API_KEY")
        if not self.key:
            raise RuntimeError("OPENAI_API_KEY is required for provider=openai")
        self.model = os.environ.get("CONTENT_FACTORY_MODEL", "gpt-5.4-mini")

    def create_package(self, spec: CaseSpec) -> dict[str, Any]:
        schema = {"type": "object", "required": ["sections", "sources", "claims"], "additionalProperties": False,
                  "properties": {"sections": {"type": "array", "minItems": 8, "maxItems": 8,
                  "items": {"type": "object", "required": ["section", "narration"], "additionalProperties": False,
                  "properties": {"section": {"type": "string"}, "narration": {"type": "string"}}}},
                  "sources": {"type": "array", "items": {"type": "object", "required": ["source_id", "url", "title"], "additionalProperties": False,
                  "properties": {"source_id": {"type": "string"}, "url": {"type": "string"}, "title": {"type": "string"}}}},
                  "claims": {"type": "array", "items": {"type": "object", "required": ["claim_id", "text", "classification", "source_id"], "additionalProperties": False,
                  "properties": {"claim_id": {"type": "string"}, "text": {"type": "string"}, "classification": {"type": "string"}, "source_id": {"type": "string"}}}}}}
        prompt = f"""Create an evidence-first investigative documentary package.
Case: {spec.title}\nAngle: {spec.angle}\nTarget: {spec.target_minutes} minutes\nSources: {json.dumps(spec.sources or [])}
Use exactly these sections: {json.dumps(SECTIONS)}. Use web search to verify facts. Every material factual claim must map to a supplied or discovered source. Never fabricate quotations, citations, or scene details. Mark analysis and reconstruction clearly. Return JSON only."""
        payload = {"model": self.model, "input": prompt, "tools": [{"type": "web_search"}],
                   "text": {"format": {"type": "json_schema", "name": "episode", "strict": True, "schema": schema}}}
        req = urllib.request.Request("https://api.openai.com/v1/responses", data=json.dumps(payload).encode(),
                                     headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as response:
            body = json.load(response)
        for item in body.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    return json.loads(content["text"])
        raise RuntimeError("OpenAI response did not contain output_text")


def editorial_provider(name: str):
    if name == "openai":
        return OpenAIEditorialProvider()
    if name == "demo":
        return DemoEditorialProvider()
    raise ValueError(f"Unknown provider: {name}")
