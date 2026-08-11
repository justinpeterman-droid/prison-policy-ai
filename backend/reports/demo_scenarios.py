"""Canonical fictional demo scenarios used by web and CLI review flows."""
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path


DEMO_NOTES_PATH = Path(__file__).parents[2] / "templates" / "demo_notes.json"


@lru_cache(maxsize=1)
def _cached_scenarios() -> tuple[dict, ...]:
    payload = json.loads(DEMO_NOTES_PATH.read_text(encoding="utf-8"))
    return tuple(payload.get("scenarios", []))


def load_demo_scenarios() -> tuple[dict, ...]:
    """Return caller-owned copies of every declared scenario."""
    return tuple(deepcopy(item) for item in _cached_scenarios())


def get_demo_scenario(scenario_id: str) -> dict | None:
    """Return a caller-owned scenario copy, or ``None`` for an unknown ID."""
    match = next(
        (item for item in _cached_scenarios() if item.get("id") == scenario_id),
        None,
    )
    return deepcopy(match) if match else None
