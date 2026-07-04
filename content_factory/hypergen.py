from __future__ import annotations

import json
from pathlib import Path


SECTION_DIRECTION = {
    "Cold Open": ("Immediate high-stakes human consequence; unanswered question in the first image", "slow push-in, macro evidence insert, hard cut to host", "low sub-bass pulse, distant room tone, one impact hit"),
    "Background": ("Grounded location, period context, institutions and people before the conflict", "wide establishing shot, measured dolly, restrained archival-style inserts", "subtle ambient bed, office or city texture"),
    "Conflict": ("The moment an automated assumption becomes a real-world accusation", "over-the-shoulder evidence view, rack focus to human reaction, controlled handheld", "tension pulse, paper and keyboard detail"),
    "Investigation": ("Primary documents, dates, correspondence and testimony arranged as verifiable evidence", "top-down document inserts, timeline moves, courtroom or hearing coverage", "quiet investigative rhythm, page turns, room ambience"),
    "Technical Breakdown": ("Simple professional visualization explaining the system without futuristic CGI", "clean 2D data animation, diagram close-ups, deliberate screen movement", "minimal electronic texture, precise UI ticks"),
    "Human Impact": ("Dignified, non-exploitative human consequences in believable everyday spaces", "eye-level portrait, slow lateral move, shallow depth of field", "minimal piano, natural room tone, no melodrama"),
    "Venky's Verdict": ("Host directly to camera in the established dark investigative studio", "locked eye-level medium close-up, no cutaways during final principle", "no music; clean intimate voice and room silence"),
    "Closing": ("Case file closes with evidence retained and the lesson unresolved in the viewer's mind", "slow pull-back, file closure insert, fade to black and logo", "single resolved note, subtle typing sound, fade to silence"),
}

NEGATIVE_PROMPT = "cartoon, anime, glossy science-fiction interface, cyberpunk, humanoid robot, fake readable legal document, invented newspaper headline, distorted hands, extra fingers, warped face, lip-sync mismatch, floating text, logos, watermarks, sensational suffering, fast flashy transition"
VOICE_PROFILE = "Calm, intelligent, authoritative and warm documentary narrator. Measured pace around 140 words per minute. Use deliberate pauses after consequential claims. Show empathy without melodrama, clarity during technical explanations, and conviction in the verdict. Never sound like advertising, a trailer announcer, or synthetic customer service."


def build_hypergen_export(case: dict, script: dict) -> dict:
    scenes = []
    cursor = 0.0
    for index, section in enumerate(script["sections"], 1):
        narration = section["narration"].strip()
        duration = max(12.0, len(narration.split()) / 140 * 60 + 2.0)
        visual, camera, sound = SECTION_DIRECTION.get(section["section"], SECTION_DIRECTION["Background"])
        prompt = (
            f"Create scene {index:02} of a premium 16:9 investigative documentary titled '{case['title']}'. "
            f"Section: {section['section']}. Story context: {case['angle']} "
            f"Visual objective: {visual}. Use photorealistic practical locations, dark modern grade, blue shadows, "
            f"warm natural skin tones, soft highlights, shallow depth of field and restrained film grain. "
            f"Camera: {camera}. Evidence must be visually plausible but never fabricate readable quotations, court records, "
            f"headlines or official findings. Clearly treat any illustrative imagery as reconstruction. "
            f"Sound design: {sound}. Narration voice: {VOICE_PROFILE} "
            f"Exact voice-over: {json.dumps(narration, ensure_ascii=False)} "
            f"Target duration: {duration:.1f} seconds. Negative prompt: {NEGATIVE_PROMPT}."
        )
        scenes.append({
            "scene_id": f"SC-{index:02}", "section": section["section"],
            "start_seconds": round(cursor, 1), "duration_seconds": round(duration, 1),
            "exact_voice_over": narration, "audio_voice_prompt": VOICE_PROFILE,
            "visual_prompt": visual, "camera_direction": camera, "sound_design": sound,
            "graphics": "Use restrained lower thirds, dates, maps or timelines only when supported by a source. Keep all generated documents unreadable unless supplied as authentic assets.",
            "negative_prompt": NEGATIVE_PROMPT, "hypergen_copy_paste_prompt": prompt,
        })
        cursor += duration
    return {
        "case_id": case["case_id"], "title": case["title"], "format": "1920x1080, 16:9, 30fps",
        "master_continuity": "Keep the uploaded host reference identical across every host scene: face, age, hair, beard, skin tone, wardrobe and proportions. Premium evidence-first documentary; no fabricated evidence and no unlabelled reconstruction.",
        "voice_profile": VOICE_PROFILE, "estimated_duration_seconds": round(cursor, 1), "scenes": scenes,
    }


def hypergen_markdown(export: dict) -> str:
    lines = [f"# HyperGen Production Pack — {export['title']}", "", f"**Format:** {export['format']}", "", "## Master continuity", "", export["master_continuity"], "", "## Master voice", "", export["voice_profile"], ""]
    for scene in export["scenes"]:
        lines.extend([f"## {scene['scene_id']} — {scene['section']}", "", f"**Timing:** {scene['start_seconds']}s · {scene['duration_seconds']}s", "", "### Copy/paste HyperGen prompt", "", scene["hypergen_copy_paste_prompt"], "", "### Exact voice-over", "", scene["exact_voice_over"], ""])
    return "\n".join(lines)


def write_hypergen_export(run_dir: Path, case: dict, script: dict) -> tuple[Path, Path]:
    export = build_hypergen_export(case, script)
    json_path = run_dir / "hypergen_export.json"
    md_path = run_dir / "hypergen_prompt_pack.md"
    json_path.write_text(json.dumps(export, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(hypergen_markdown(export), encoding="utf-8")
    return json_path, md_path
