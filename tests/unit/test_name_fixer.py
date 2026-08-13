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
    assert "Inmate Garcia, Luis ADC# 448291" in out  # sentence start -> capitalized


def test_inmate_subsequent_mentions_stay_short():
    slots = {"persons": [_inmate("Garcia", "Luis", "448291")]}
    text = "Inmate Garcia swung first. Inmate Garcia was then restrained."
    out = enforce_naming(text, slots)
    # First mention full, second mention short. Both start a sentence here, so
    # both are capitalized (ruling 6 lowercases only mid-sentence).
    assert out.index("ADC# 448291") < out.index("Inmate Garcia was then")
    assert out.count("ADC# 448291") == 1


def test_staff_first_mention_uses_rank_first_last():
    slots = {"persons": [_staff("Sgt.", "Lee", "Quintero")], "officer_last": "Quintero"}
    out = enforce_naming("Sgt. Quintero applied hand restraints.", slots)
    assert "Sgt. Lee Quintero" in out


def test_person_without_last_name_is_skipped():
    slots = {"persons": [_inmate(None, "Luis", "448291")]}
    text = "Something happened."
    assert enforce_naming(text, slots) == text


def test_never_raises_returns_original_on_bad_person():
    # A malformed person dict must not blow up report generation.
    slots = {"persons": [{"role": "inmate"}]}  # no last name
    text = "Inmate did a thing."
    assert enforce_naming(text, slots) == text


# ── RG-5 regressions ────────────────────────────────────────────────────────
# Both of these produced corrupted narratives before the rewrite.


def test_shared_surname_does_not_cross_contaminate():
    """An inmate and an officer with the same last name must stay distinct.
    Previously produced 'Inmate Sgt Robert Smith, John ADC#123456'."""
    slots = {
        "persons": [
            _inmate("Smith", "John", "123456"),
            _staff("Sgt", "Robert", "Smith"),
        ],
        "officer_last": "Smith",
    }
    out = enforce_naming("I observed Inmate Smith fighting. Sgt Smith responded.", slots)
    assert "inmate Smith, John ADC# 123456" in out  # mid-sentence -> lowercase
    assert "Sgt Robert Smith" in out
    assert "Inmate Sgt" not in out
    assert "Sgt Robert Smith, John" not in out


def test_replacement_never_destroys_surrounding_text():
    """Stale match offsets used to shred the text, turning
    'applied restraints. Inmate Jones' into 'applied restraintCpl Jonesmate Jones'."""
    slots = {
        "persons": [
            _inmate("Jones", "Marcus", "998877"),
            _staff("Cpl", "Alice", "Jones"),
        ],
        "officer_last": "Jones",
    }
    text = "Inmate Jones refused orders. Cpl Jones applied restraints. Inmate Jones complied."
    out = enforce_naming(text, slots)
    # Every word of the original narrative survives.
    for fragment in ("refused orders", "applied restraints", "complied"):
        assert fragment in out
    assert "restraintCpl" not in out


def test_reporter_self_reference_is_left_intact():
    slots = {
        "persons": [_staff("Sgt", "Dana", "Halvorsen")],
        "officer_last": "Halvorsen",
    }
    text = "I, Sgt Dana Halvorsen, was assigned to 8 Barracks. I applied restraints."
    assert enforce_naming(text, slots) == text


def test_already_full_form_is_not_re_expanded():
    slots = {"persons": [_inmate("Garcia", "Luis", "448291")]}
    text = "Inmate Garcia, Luis ADC# 448291 was restrained."
    out = enforce_naming(text, slots)
    assert out.count("ADC# 448291") == 1
    assert "Inmate Inmate" not in out


def test_rank_period_mismatch_still_matches():
    # Roster says 'Sgt.'; the model wrote 'Sgt'.
    slots = {"persons": [_staff("Sgt.", "Lee", "Quintero")]}
    out = enforce_naming("Sgt Quintero applied hand restraints.", slots)
    assert "Lee" in out


def test_shared_surname_leaves_bare_mentions_alone():
    """With two people named Smith, a bare 'Smith' is genuinely ambiguous —
    guessing would attribute an action to the wrong person."""
    slots = {
        "persons": [
            _inmate("Smith", "John", "123456"),
            _staff("Sgt", "Robert", "Smith"),
        ]
    }
    out = enforce_naming("Smith was uncooperative.", slots)
    assert out == "Smith was uncooperative."


def test_multiple_inmates_each_get_their_own_first_mention():
    slots = {
        "persons": [
            _inmate("Garcia", "Luis", "448291"),
            _inmate("Okonkwo", "Trevor", "551002"),
        ]
    }
    out = enforce_naming("Inmate Garcia and Inmate Okonkwo were separated.", slots)
    assert "Inmate Garcia, Luis ADC# 448291" in out  # sentence start -> capitalized
    assert "inmate Okonkwo, Trevor ADC# 551002" in out  # mid-sentence -> lowercase


# ── STYLE_RULINGS.md conformance ────────────────────────────────────────────


def test_ruling_4_adc_number_has_a_space_after_the_hash():
    slots = {"persons": [_inmate("Garcia", "Luis", "448291")]}
    out = enforce_naming("Inmate Garcia was restrained.", slots)
    assert "ADC# 448291" in out
    assert "ADC#448291" not in out


def test_ruling_6_inmate_is_lowercase_mid_sentence():
    slots = {"persons": [_inmate("Garcia", "Luis", "448291")]}
    out = enforce_naming("I escorted Inmate Garcia to the infirmary.", slots)
    assert "escorted inmate Garcia" in out


def test_ruling_6_inmate_is_capitalized_at_sentence_start():
    slots = {"persons": [_inmate("Garcia", "Luis", "448291")]}
    out = enforce_naming("Inmate Garcia refused. I escorted Inmate Garcia out.", slots)
    assert out.startswith("Inmate Garcia")
    assert "escorted inmate Garcia" in out


def test_ruling_6_matches_either_capitalization_in_the_source():
    # The model may write either; both must be normalized.
    slots = {"persons": [_inmate("Garcia", "Luis", "448291")]}
    out = enforce_naming("I saw inmate Garcia there.", slots)
    assert "saw inmate Garcia, Luis ADC# 448291" in out


def test_ruling_2_staff_rank_period_survives():
    slots = {"persons": [_staff("Sgt.", "John", "Miller")]}
    out = enforce_naming("Sgt. Miller responded.", slots)
    assert "Sgt. John Miller" in out
