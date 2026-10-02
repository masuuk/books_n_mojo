"""Vendoring for the manual's diagrams.

The archives embed four of the sixteen diagram images and point at the network for
the rest. A book that has to work from a file:// URL needs all of them local, so we
fetch the missing ones once into a cache and write every image into each book's own
`assets/images/`. No build output ever references the network.
"""

from __future__ import annotations

import hashlib
import urllib.error
import urllib.request
from pathlib import Path

USER_AGENT = "mojo-manual-builder/1.0"
TIMEOUT = 20


def _cache_path(cache: Path, url: str) -> Path:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    name = url.split("#", 1)[0].rsplit("/", 1)[-1] or "image"
    return cache / f"{digest}-{name}"


def fetch(urls: dict[str, bytes], cache: Path, offline: bool = False) -> dict[str, bytes]:
    """Return {url: bytes} for every diagram, fetching what is not already embedded."""
    cache.mkdir(parents=True, exist_ok=True)
    resolved: dict[str, bytes] = {}

    for url, embedded in sorted(urls.items()):
        clean = url.split("#", 1)[0]
        if embedded:
            resolved[clean] = embedded
            continue

        target = _cache_path(cache, clean)
        if target.exists():
            resolved[clean] = target.read_bytes()
            continue

        if offline:
            continue

        try:
            request = urllib.request.Request(clean, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                payload = response.read()
        except (urllib.error.URLError, OSError, TimeoutError):
            continue

        if payload:
            target.write_bytes(payload)
            resolved[clean] = payload

    return resolved