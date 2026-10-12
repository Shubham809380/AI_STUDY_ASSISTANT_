import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.testdata import VALID_STUDY_TEXT, INVALID_STUDY_TEXT, make_valid_quiz


@pytest.fixture
def valid_study_text():
    return VALID_STUDY_TEXT


@pytest.fixture
def invalid_study_text():
    return INVALID_STUDY_TEXT


@pytest.fixture
def valid_quiz():
    return make_valid_quiz(5)