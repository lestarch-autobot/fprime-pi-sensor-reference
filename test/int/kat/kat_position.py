"""pytest plugin of the known-answer tests only: the bench position the synthetic record was made for."""
import sys


def pytest_collection_modifyitems(items):
    sys.modules["test_pisensor"].BENCH_POSITION = (34.2000, -118.1700)
