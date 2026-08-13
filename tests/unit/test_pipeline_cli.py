"""Credential-free contracts for the live report-pipeline harness."""

from datetime import datetime, timezone
import importlib.util
from pathlib import Path

from backend.pipeline.config import FAST_MODEL, MODEL_LOCATION, PRO_MODEL


_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location("pipeline_harness", _ROOT / "tests" / "test_pipeline.py")
pipeline = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(pipeline)


def test_output_paths_are_rooted_under_the_requested_directory(tmp_path):
    paths = pipeline.output_paths(tmp_path, "case_one")

    assert paths.run_dir == tmp_path / "case_one"
    assert paths.snapshot_dir == tmp_path / "case_one_snapshot"


def test_parser_converts_output_directory_to_a_path(tmp_path):
    args = pipeline.build_parser().parse_args(["--demo", "all", "--output-dir", str(tmp_path)])

    assert args.demo == "all"
    assert args.output_dir == tmp_path


def test_demo_batch_runs_scenarios_in_declared_order(tmp_path):
    seen = []

    def fake_runner(**kwargs):
        seen.append((kwargs["scenario"]["id"], kwargs["output_root"]))
        return 0

    result = pipeline.run_demo_batch(output_root=tmp_path, runner=fake_runner)

    assert result == 0
    assert seen == [
        ("inmate_fight_dayroom", tmp_path),
        ("contraband_shakedown", tmp_path),
        ("use_of_force_oc", tmp_path),
    ]


def test_demo_batch_returns_failure_when_any_scenario_fails(tmp_path):
    def fake_runner(**kwargs):
        return 1 if kwargs["scenario"]["id"] == "contraband_shakedown" else 0

    assert pipeline.run_demo_batch(output_root=tmp_path, runner=fake_runner) == 1


def test_oc_demo_gap_resolution_retains_initial_gap_and_separate_answers():
    scenario = next(s for s in pipeline.load_demo_scenarios() if s["id"] == "use_of_force_oc")
    slots = {
        "force_type": "Chemical agent (OC/MK-3)",
        "chemical_agent": None,
        "decontamination": "Cool water and fresh air",
    }

    resolved, initial, final, answers = pipeline.resolve_demo_gaps("use_of_force", slots, scenario)

    assert any(g["slot"] == "chemical_agent" for g in initial["gaps"])
    assert not any(g["slot"] == "chemical_agent" for g in final["gaps"])
    assert answers == {
        **scenario["demo_answers"],
        **scenario["review_answers"],
    }
    assert resolved["chemical_agent"] == answers["chemical_agent"]
    assert slots["chemical_agent"] is None


def test_manifest_contains_literal_model_gap_path_and_artifact_metadata(tmp_path):
    started = datetime(2026, 8, 11, 1, 2, 3, tzinfo=timezone.utc)
    finished = datetime(2026, 8, 11, 1, 2, 9, tzinfo=timezone.utc)

    manifest = pipeline.build_manifest(
        run_id="run-1",
        name="use_of_force_oc",
        output_root=tmp_path,
        started_at=started,
        finished_at=finished,
        timing={"classify": 1.2, "total": 6.0},
        errors=[("generate", "blocked")],
        initial_blocking=1,
        final_blocking=0,
        artifacts=["03_gaps_initial.json", "01_classify.json"],
    )

    assert manifest == {
        "schema_version": 1,
        "run_id": "run-1",
        "name": "use_of_force_oc",
        "started_at": "2026-08-11T01:02:03Z",
        "finished_at": "2026-08-11T01:02:09Z",
        "output_root": str(tmp_path.resolve()),
        "models": {
            "classification": FAST_MODEL,
            "extraction": FAST_MODEL,
            "generation": PRO_MODEL,
            "location": MODEL_LOCATION,
        },
        "timing_seconds": {"classify": 1.2, "total": 6.0},
        "gaps": {"initial_blocking": 1, "final_blocking": 0},
        "errors": [{"step": "generate", "message": "blocked"}],
        "artifacts": ["01_classify.json", "03_gaps_initial.json"],
    }
