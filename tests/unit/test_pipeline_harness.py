import sys

import pytest

from tests import test_pipeline


def test_main_requires_a_fixture_when_not_running_a_demo_or_batch(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["test_pipeline.py"])

    with pytest.raises(SystemExit) as error:
        test_pipeline.main()

    assert error.value.code == 2
