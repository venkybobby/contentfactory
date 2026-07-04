import json
from pathlib import Path

import pytest

from content_factory.workflow import CaseSpec, Factory


@pytest.fixture
def case_spec() -> CaseSpec:
    return CaseSpec("AIC-TEST", "Test case", "Test angle", 8, [])


def test_run_stops_at_editorial_approval(tmp_path: Path, case_spec: CaseSpec):
    manifest = Factory(tmp_path).run(case_spec)
    assert manifest["stages"]["research"] == "complete"
    assert manifest["stages"]["editorial_approval"] == "waiting_for_human"
    assert manifest["stages"]["script"] == "pending"


def test_approval_is_auditable_and_run_resumes(tmp_path: Path, case_spec: CaseSpec):
    factory = Factory(tmp_path)
    factory.run(case_spec)
    factory.approve(case_spec.case_id, "editorial_approval", "Venky")
    manifest = factory.run(case_spec)
    approval_path = factory.run_dir(case_spec.case_id) / "editorial_approval.json"
    approval = json.loads(approval_path.read_text())
    assert approval["approved_by"] == "Venky"
    assert manifest["stages"]["script_approval"] == "waiting_for_human"


def test_cannot_approve_non_gate(tmp_path: Path, case_spec: CaseSpec):
    factory = Factory(tmp_path)
    factory.initialize(case_spec)
    with pytest.raises(ValueError):
        factory.approve(case_spec.case_id, "research", "Venky")
