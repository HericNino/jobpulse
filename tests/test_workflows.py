"""Guards against API spend from automation: only a hand-started workflow may see the API key."""

from pathlib import Path

WORKFLOWS = Path(__file__).parents[1] / ".github" / "workflows"


def test_only_the_manual_eval_workflow_gets_the_api_key():
    with_key = sorted(p.name for p in WORKFLOWS.glob("*.yml") if "ANTHROPIC_API_KEY" in p.read_text())
    assert with_key == ["eval.yml"]


def test_eval_workflow_only_runs_when_started_by_hand():
    text = (WORKFLOWS / "eval.yml").read_text()
    on_block = text.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
    triggers = {line.strip().rstrip(":") for line in on_block.splitlines() if line.startswith("  ") and not line.startswith("    ")}
    assert triggers == {"workflow_dispatch"}


def test_scheduled_collection_uses_no_model_calls():
    assert "--max-model-calls 0" in (WORKFLOWS / "collect.yml").read_text()
