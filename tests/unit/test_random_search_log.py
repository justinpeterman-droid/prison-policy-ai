from copy import deepcopy
from datetime import date, time
from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.paperwork.daily import RandomSearchLogV1


SECTION_CODES = ("north_1", "north_2", "south_1", "south_2")


def _blank_block():
    return {
        "officer": None,
        "search_date": None,
        "search_time": None,
        "individual_last_name": "",
        "individual_number": "",
        "barracks_rack": "",
        "contraband_disposition": "",
    }


def _payload():
    return {
        "schema_version": 1,
        "work_date": "2026-08-20",
        "shift": "D",
        "sections": [
            {"section_code": code, "blocks": [_blank_block() for _ in range(4)]}
            for code in SECTION_CODES
        ],
    }


def test_random_search_requires_four_approved_sections_with_four_blocks_each():
    model = RandomSearchLogV1.model_validate(_payload())
    assert [section.section_code for section in model.sections] == list(SECTION_CODES)

    payload = _payload()
    payload["sections"][0]["blocks"].pop()
    with pytest.raises(ValidationError):
        RandomSearchLogV1.model_validate(payload)

    payload = _payload()
    payload["sections"][1] = deepcopy(payload["sections"][0])
    with pytest.raises(ValidationError):
        RandomSearchLogV1.model_validate(payload)


def test_random_search_parses_nullable_date_time_and_rejects_long_or_unknown_values():
    payload = _payload()
    block = payload["sections"][0]["blocks"][0]
    block["officer"] = {
        "staff_id": str(uuid4()),
        "display_name_snapshot": "Officer Morgan Lee",
    }
    block["search_date"] = "2026-08-20"
    block["search_time"] = "14:30:00"
    model = RandomSearchLogV1.model_validate(payload)
    assert model.sections[0].blocks[0].search_date == date(2026, 8, 20)
    assert model.sections[0].blocks[0].search_time == time(14, 30)

    payload = _payload()
    payload["sections"][0]["blocks"][0]["contraband_disposition"] = "x" * 2001
    with pytest.raises(ValidationError):
        RandomSearchLogV1.model_validate(payload)

    payload = _payload()
    payload["sections"][0]["blocks"][0]["unexpected"] = True
    with pytest.raises(ValidationError):
        RandomSearchLogV1.model_validate(payload)

