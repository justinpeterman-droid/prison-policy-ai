"""Unit tests for the 005/409 form-designation boxes (STYLE_RULINGS.md ruling 9).

No AI, no GCP — this fills the real DOCX template and reads the result back, so
it also guards the template itself: if the two {{box_*}} placeholders are ever
lost from 005_template_v3.docx, these fail.
"""

import re
import zipfile

import pytest

from backend.reports.filler import (
    TICK,
    TEMPLATE_PATH,
    designation_boxes,
    fill_template,
)


def _boxes(docx_path) -> dict:
    """Read what actually landed in the two header checkbox cells."""
    with zipfile.ZipFile(docx_path) as z:
        doc = z.read("word/document.xml").decode()
    out = {}
    for label in ("005", "409"):
        seg = doc[doc.find(f">{label}</w:t>") :][:2500]
        after_label_cell = seg[seg.find("</w:tc>") :]
        m = re.search(r"<w:t[^>]*>([^<]*)</w:t>", after_label_cell)
        out[label] = m.group(1) if m else None
    return out


@pytest.fixture
def filled(tmp_path):
    made = []

    def _fill(metadata):
        out = fill_template(dict(metadata), output_path=tmp_path / f"f{len(made)}.docx")
        made.append(out)
        return out

    return _fill


class TestDesignationBoxes:
    def test_every_incident_ticks_the_005_box(self):
        for category in (
            "inmate_fight",
            "contraband",
            "prea",
            "medical_emergency",
            "other_rule_violation",
        ):
            assert designation_boxes(category)["box_005"] == TICK

    def test_use_of_force_ticks_both(self):
        """Ruling 9: a use of force is filed as a 005 that ALSO carries the
        409 — not as a 409 on its own."""
        boxes = designation_boxes("use_of_force")
        assert boxes["box_005"] == TICK
        assert boxes["box_409"] == TICK

    def test_other_categories_leave_409_blank(self):
        # Blank, never a stray mark.
        assert designation_boxes("inmate_fight")["box_409"] == ""

    def test_unknown_category_still_ticks_005_only(self):
        assert designation_boxes("") == {"box_005": TICK, "box_409": ""}


class TestTemplateFilling:
    def test_the_template_carries_both_placeholders(self):
        with zipfile.ZipFile(TEMPLATE_PATH) as z:
            doc = z.read("word/document.xml").decode()
        assert "{{box_005}}" in doc
        assert "{{box_409}}" in doc

    def test_use_of_force_document_shows_both_marks(self, filled):
        out = filled({"narrative": "x", **designation_boxes("use_of_force")})
        assert _boxes(out["path"]) == {"005": TICK, "409": TICK}

    def test_ordinary_incident_document_shows_only_the_005_mark(self, filled):
        out = filled({"narrative": "x", **designation_boxes("inmate_fight")})
        assert _boxes(out["path"]) == {"005": TICK, "409": ""}

    def test_metadata_without_the_keys_still_ticks_005(self, filled):
        """A caller that never heard of these boxes (or an older client payload)
        must still produce a correctly designated 005, not a blank one."""
        out = filled({"narrative": "x"})
        assert _boxes(out["path"]) == {"005": TICK, "409": ""}

    def test_no_placeholder_survives_into_the_filled_document(self, filled):
        out = filled({"narrative": "x", **designation_boxes("use_of_force")})
        with zipfile.ZipFile(out["path"]) as z:
            doc = z.read("word/document.xml").decode()
        assert not re.findall(r"\{\{\w+\}\}", doc)

    def test_an_explicitly_unticked_box_stays_unticked(self, filled):
        """The download fills from the reviewed on-screen form, so "" is a
        meaningful value — an unticked box — not "caller forgot to set this".
        The generic defaults loop treats empty as unset and would re-tick it."""
        out = filled({"narrative": "x", "box_005": "", "box_409": TICK})
        assert _boxes(out["path"]) == {"005": "", "409": TICK}
