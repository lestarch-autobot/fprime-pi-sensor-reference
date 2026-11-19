"""Known answers of the check functions of test_picam.py: `python -m pytest checks_kat.py` (no bench).

Not named test_*.py: fth refuses a stimulus directory that holds a test outside the plan.
"""
from test_picam import PICTURE_MAX_SIZE, picture_sizes_ok, response_times


def test_picture_sizes():
    assert picture_sizes_ok([24000])
    assert picture_sizes_ok([PICTURE_MAX_SIZE])
    assert not picture_sizes_ok([])
    assert not picture_sizes_ok([0])
    assert not picture_sizes_ok([PICTURE_MAX_SIZE + 1])


def test_response_times():
    assert response_times([10.0], [10.8]) == [pytest_approx(0.8)]
    assert response_times([10.0, 20.0], [10.5, 21.0]) == [pytest_approx(0.5), pytest_approx(1.0)]
    assert response_times([10.0], []) == [None]
    assert response_times([10.0], [9.0]) == [None]


def pytest_approx(value):
    import pytest
    return pytest.approx(value)
