from pathlib import Path

import pytest

from content_factory.workflow import CaseSpec, Factory


@pytest.mark.integration
def test_demo_flow_renders_video(tmp_path: Path):
    spec = CaseSpec("AIC-E2E", "An AI Case", "Humans must verify important AI output.", 1, [])
    manifest = Factory(tmp_path, "demo").run(spec, auto_approve=True)
    assert all(value == "complete" for value in manifest["stages"].values())
    assert (tmp_path / "runs" / "AIC-E2E" / "AIC-E2E.mp4").stat().st_size > 1_000
    qa = Factory(tmp_path).run_dir("AIC-E2E") / "qa.json"
    assert '"passed_for_preview": true' in qa.read_text()
