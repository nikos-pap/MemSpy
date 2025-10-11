# tests/conftest.py
import io
import logging
import pytest
from contextlib import redirect_stdout, redirect_stderr

@pytest.fixture(autouse=True, scope="session")
def _disable_all_logging():
    """
    Disable all logging calls from libraries/app code.
    """
    logging.disable(logging.CRITICAL)   # blocks everything <= CRITICAL
    # make basicConfig a no-op if app tries to enable logging
    logging.basicConfig = lambda *a, **k: None
    yield
    logging.disable(logging.NOTSET)

@pytest.fixture(autouse=True)
def _silence_stdout_stderr():
    """
    Redirect any Python-level prints to nowhere for every test.
    (PyTest still prints its own progress because it's written outside this context.)
    """
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        yield
