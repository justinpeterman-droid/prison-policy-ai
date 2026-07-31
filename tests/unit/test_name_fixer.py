"""Unit tests for deterministic name enforcement (no AI, no GCP).

name_fixer guarantees the first mention of each person is the full form and
later mentions are short — regardless of what the LLM wrote.
"""
from backend.reports.name_fixer import enforce_naming


def _inmate(last, first=None, adc=None):
    return {"role": "inmate", "last": last, "first": first, "adc_number": adc}


def _staff(rank, first, last):
    return {"role": "security_staff", "rank": rank, "first": first, "last": last}


def test_empty_inputs_are_safe():
    assert enforce_naming("", {"persons": []}) == ""
    assert enforce_naming("text", {}) == "text"
    assert enforce_naming("text", {"persons": []}) == "text"


def test_inmate_first_mention_expands_to_full_form():
    slots = {"persons": [_inmate("Garcia", "Luis", "448291")]}
    out = enforce_naming("Inmate Garcia was placed in restraints.", slots)
    assert "Inmate Garcia, Luis ADC#448291" in out


def test_inmate_subsequent_mentions_stay_short():
    slots = {"persons": [_inmate("Garcia", "Luis", "448291")]}
    text = "Inmate Garcia swung first. Inmate Garcia was then restrained."
    out = enforce_naming(text, slots)
    # First mention full, second mention short.
    assert out.index("ADC#448291") < out.index("Inmate Garcia was then")
    assert out.count("ADC#448291") == 1


def test_staff_first_mention_uses_rank_first_last():
    slots = {"persons": [_staff("Sgt.", "Miguel", "Delgado")],
             "officer_last": "Delgado"}
    out = enforce_naming("Sgt. Delgado applied hand restraints.", slots)
    assert "Sgt. Miguel Delgado" in out


def test_person_without_last_name_is_skipped():
    slots = {"persons": [_inmate(None, "Luis", "448291")]}
    text = "Something happened."
    assert enforce_naming(text, slots) == text


def test_never_raises_returns_original_on_bad_person():
    # A malformed person dict must not blow up report generation.
    slots = {"persons": [{"role": "inmate"}]}  # no last name
    text = "Inmate did a thing."
    assert enforce_naming(text, slots) == text
