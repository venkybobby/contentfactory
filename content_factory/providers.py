from __future__ import annotations

import json
import ipaddress
import os
import socket
import urllib.request
import urllib.parse
from html.parser import HTMLParser
from typing import Any

from .workflow import CaseSpec


SECTIONS = ("Cold Open", "Background", "Conflict", "Investigation",
            "Technical Breakdown", "Human Impact", "Venky's Verdict", "Closing")


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if value:
            self.parts.append(value)


def source_excerpts(urls: list[str]) -> list[dict[str, str]]:
    excerpts = []
    for index, url in enumerate(urls, 1):
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("Source URLs must use HTTPS")
        addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                raise ValueError("Source URLs cannot resolve to private or reserved networks")
        request = urllib.request.Request(url, headers={"User-Agent": "ContentFactory/0.2 source-verifier"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                content_type = response.headers.get_content_type()
                raw = response.read(500_000)
            if content_type not in {"text/html", "text/plain", "application/xhtml+xml"}:
                text = f"Unsupported source type: {content_type}. Human review required."
            elif content_type == "text/html":
                parser = _TextExtractor()
                parser.feed(raw.decode("utf-8", errors="replace"))
                text = " ".join(parser.parts)
            else:
                text = raw.decode("utf-8", errors="replace")
        except (OSError, ValueError) as exc:
            text = f"Source retrieval failed: {type(exc).__name__}. Human review required."
        excerpts.append({"source_id": f"S{index:03}", "url": url, "title": url, "excerpt": text[:20_000]})
    return excerpts


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


class NvidiaEditorialProvider:
    def __init__(self) -> None:
        self.key = os.environ.get("NVIDIA_API_KEY")
        if not self.key:
            raise RuntimeError("NVIDIA_API_KEY is required for provider=nvidia")
        self.model = os.environ.get("NVIDIA_MODEL", "z-ai/glm-5.2")
        self.base_url = os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")

    def create_package(self, spec: CaseSpec) -> dict[str, Any]:
        sources = source_excerpts(spec.sources or [])
        prompt = f"""You are an evidence-first investigative documentary editor.
Create JSON only, with keys sections, sources, and claims.
sections must contain exactly these eight names in order: {json.dumps(SECTIONS)}.
Each section object has section and narration. claims is an array of objects with claim_id, text, classification, and source_id.
Use only the supplied source excerpts. Do not invent facts, quotations, people, dates, or citations. If evidence is insufficient, state that explicitly in narration.
Case: {spec.title}
Angle: {spec.angle}
Target minutes: {spec.target_minutes}
Sources: {json.dumps(sources, ensure_ascii=False)}"""
        payload = {"model": self.model, "messages": [{"role": "user", "content": prompt}],
                   "temperature": 0.2, "top_p": 1, "max_tokens": 8192, "seed": 42, "stream": False}
        request = urllib.request.Request(f"{self.base_url.rstrip('/')}/chat/completions",
                                         data=json.dumps(payload).encode("utf-8"),
                                         headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json", "Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=300) as response:
            body = json.load(response)
        content = body["choices"][0]["message"]["content"]
        start, end = content.find("{"), content.rfind("}")
        if start < 0 or end <= start:
            raise RuntimeError("NVIDIA response did not contain a JSON object")
        package = json.loads(content[start:end + 1])
        package["sources"] = [{k: source[k] for k in ("source_id", "url", "title")} for source in sources]
        if len(package.get("sections", [])) != len(SECTIONS):
            raise RuntimeError("NVIDIA response must contain exactly eight sections")
        return package


def editorial_provider(name: str):
    if name == "openai":
        return OpenAIEditorialProvider()
    if name == "demo":
        return DemoEditorialProvider()
    if name == "nvidia":
        return NvidiaEditorialProvider()
    raise ValueError(f"Unknown provider: {name}")
