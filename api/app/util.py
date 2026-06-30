"""Tiny dependency-free helpers used across the API runtime.

IMPORTANT: this module (and the whole `app` package) must NOT import pandas or the
pipeline's `core.py` (which imports pandas). The web process stays lightweight and
only reads JSON. `slugify` mirrors the spirit of `core.fn` (lowercase, strip
name suffixes + punctuation) but produces a URL-safe, hyphenated id.
"""
from __future__ import annotations

import re

# Name suffixes that should never be part of a stable player id.
_SUFFIX_RE = re.compile(r"\b(jr|sr|ii|iii|iv|v)\b\.?", re.IGNORECASE)
_NONALNUM_RE = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    """Return a stable, URL-safe id for a player name.

    Lowercases, removes generational suffixes (Jr/Sr/II/III/IV/V), strips
    punctuation, and hyphenates whitespace runs.

    >>> slugify("Ja'Marr Chase")
    'jamarr-chase'
    >>> slugify("Amon-Ra St. Brown")
    'amon-ra-st-brown'
    >>> slugify("Marvin Harrison Jr.")
    'marvin-harrison'
    """
    s = (str(name) if name is not None else "").strip().lower()
    s = s.replace("'", "").replace("’", "")  # drop apostrophes before tokenizing
    s = _SUFFIX_RE.sub(" ", s)
    s = _NONALNUM_RE.sub("-", s)
    return s.strip("-")
