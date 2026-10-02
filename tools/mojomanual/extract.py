"""Stage 1: read a saved .mhtml archive and isolate the page's real content.

An archive is a `multipart/related` MIME message whose payload is a fully
hydrated Docusaurus page wrapped in browser-extension detritus. This stage
throws the detritus away and hands back a parsed article region plus the page's
provenance and its embedded binary assets.
"""

from __future__ import annotations

import email
import email.policy
import re
from dataclasses import dataclass, field
from pathlib import Path
from bs4 import BeautifulSoup, Tag, NavigableString


ARTICLE_MARKER = "theme-doc-markdown"
_FOOTER_MARKER = "theme-doc-footer"
_H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S | re.I)


@dataclass
class Archive:
    """One saved docs page."""

    file: Path
    url: str
    subject: str
    date: str
    soup: BeautifulSoup
    article: Tag
    assets: dict[str, bytes] = field(default_factory=dict)


def _decode(part) -> str:
    payload = part.get_payload(decode=True)
    if payload is None:
        return ""
    return payload.decode("utf-8", "replace")


def read_archive(path: Path) -> Archive:
    """Parse one .mhtml into an :class:`Archive`."""
    raw = path.read_bytes()
    message = email.message_from_bytes(raw)
    subject = (message.get("Subject") or "").strip()

    html = ""
    url = ""
    assets: dict[str, bytes] = {}
    for part in message.walk():
        if part.is_multipart():
            continue
        location = part.get("Content-Location") or ""
        content_type = part.get_content_type()
        if content_type == "text/html" and not html:
            html = _decode(part)
            url = location
        elif content_type == "image/png":
            payload = part.get_payload(decode=True)
            if payload:
                name = location.split("#", 1)[0].rsplit("/", 1)[-1]
                if name:
                    assets[name] = payload

    if not html:
        raise ValueError(f"{path.name}: no text/html part")

    soup = BeautifulSoup(html, "lxml")
    article = soup.find("div", class_=lambda c: c and ARTICLE_MARKER in c)
    if article is None:
        raise ValueError(f"{path.name}: no article region")

    date = (message.get("Date") or "").strip()
    return Archive(
        file=path,
        url=url,
        subject=subject,
        date=date,
        soup=soup,
        article=article,
        assets=assets,
    )


def page_title(archive: Archive) -> str:
    """Prefer the article's own <h1>; fall back to the archive subject."""
    heading = archive.article.find("h1")
    if heading:
        text = heading.get_text(" ", strip=True)
        if text:
            return text
    if archive.subject:
        return archive.subject.rsplit("|", 1)[0].strip()
    return archive.file.stem


def article_text_length(archive: Archive) -> int:
    """Character count of the isolated region, used by the fidelity gate."""
    return len(archive.article.get_text())