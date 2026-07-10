"""Shared corpus-path constants and skip markers for the test suite.

Single source for the bootstrap that used to be copied into every test
module (a local ``REPO_ROOT``, a corpus dir under three different names,
and a hand-rolled ``skipif``). Paths come from ``src._corpus`` so the
tests skip and iterate exactly the way the build does.
"""
from __future__ import annotations

import pytest

from src._corpus import (  # noqa: F401  (re-exports for test modules)
    CORPUS_ROOT as CORPUS_DIR,
    REPO_ROOT,
    SCHEMA_RNG,
    iter_tei_files,
)

needs_corpus = pytest.mark.skipif(
    not CORPUS_DIR.is_dir(), reason="in-repo corpus not present"
)

needs_schema = pytest.mark.skipif(
    not SCHEMA_RNG.exists(), reason="compiled RelaxNG schema not present"
)
