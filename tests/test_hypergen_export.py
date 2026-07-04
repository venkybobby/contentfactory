from content_factory.hypergen import build_hypergen_export, hypergen_markdown


def test_export_contains_copy_paste_video_and_audio_prompts():
    case = {"case_id": "AIC-TEST", "title": "A case", "angle": "A verified accountability story."}
    script = {"sections": [{"section": "Cold Open", "narration": "A consequential opening line."}]}
    export = build_hypergen_export(case, script)
    scene = export["scenes"][0]
    assert scene["exact_voice_over"] in scene["hypergen_copy_paste_prompt"]
    assert scene["camera_direction"]
    assert scene["audio_voice_prompt"]
    assert "Copy/paste HyperGen prompt" in hypergen_markdown(export)
