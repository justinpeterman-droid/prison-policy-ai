"""Security contracts for report-template rendering."""

import json
from pathlib import Path
import re
import subprocess

from backend.reports.extraction import compute_provenance


TEMPLATE = Path(__file__).resolve().parents[2] / "backend" / "webapp" / "templates" / "reports.html"


def _render_provenance_in_node(provenance: list[dict]) -> str:
    """Execute the template's real renderer against a minimal DOM."""
    template = TEMPLATE.read_text(encoding="utf-8")
    esc_fn = re.search(r"function esc\(s\)\{[^\n]+\}", template).group(0)
    start = template.index("function renderProvenance(){")
    end = template.index("function setSourcesOpen(open){", start)
    render_fn = template[start:end]
    script = f"""
const elements = {{
  sourcesArea: {{style: {{}}}},
  sourcesCnt: {{textContent: ''}},
  tracePanel: {{innerHTML: ''}},
  sourcesToggle: {{}},
}};
global.document = {{
  getElementById: id => elements[id],
  createElement: () => ({{
    _value: '',
    set textContent(value) {{ this._value = String(value); }},
    get innerHTML() {{
      return this._value.replace(/&/g, '&amp;').replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    }},
  }}),
}};
const _extractedData = {{provenance: {json.dumps(provenance)}}};
function setSourcesOpen() {{}}
{esc_fn}
{render_fn}
renderProvenance();
process.stdout.write(elements.tracePanel.innerHTML);
"""
    result = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def test_raw_provenance_is_escaped_at_html_text_sink():
    """Note markup must remain literal text when the panel is rendered."""
    payload = '<img src=x onerror="alert(1)">'
    provenance = compute_provenance(
        f"Officer observed {payload}",
        {"narrative_facts": [payload]},
    )
    assert payload in provenance[0]["source"]

    rendered = _render_provenance_in_node(provenance)
    assert "<img" not in rendered
    assert "&lt;img" in rendered
