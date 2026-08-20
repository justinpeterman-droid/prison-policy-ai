import json

from backend.paperwork.templates import load_print_template


def test_monthly_templates_are_sanitized_and_contraband_schedules_differ():
    standard = load_print_template("monthly_contraband_standard")
    expanded = load_print_template("monthly_contraband_expanded")
    serialized = json.dumps(
        [
            load_print_template("monthly_windows_bars_doors").definition,
            load_print_template("monthly_chemical_agents").definition,
            standard.definition,
            expanded.definition,
        ],
        ensure_ascii=False,
    ).lower()

    assert standard.title != expanded.title
    assert standard.definition["schedule"] != expanded.definition["schedule"]
    assert "<script" not in serialized
    assert "/users/" not in serialized
    assert "adc#" not in serialized
    assert "historical" not in serialized
