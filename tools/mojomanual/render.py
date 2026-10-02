"""Stage 3: lay the cleaned pages out as a book.

One template for a chapter, one for the cover, one shared shell. Everything is
relative-path based and self-contained: the rendered tree can be copied anywhere
and opened from disk.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .clean import esc
from .manifest import PART_TITLES

BOOK_TITLE = "Mojo v1"
BOOK_SUBTITLE = "The Language Manual"
BOOK_BLURB = (
    "Thirty-eight chapters of the Mojo manual, in reading order, rendered for "
    "reading. Ownership, traits, pointers, comptime, and the C foreign function "
    "interface — the whole language, once, offline."
)

THEME_COLOR = "#0c0906"


@dataclass
class PageMeta:
    index: int
    entry: object
    title: str
    dek: str
    part: str
    part_title: str
    prev: tuple[str, str] | None  # (label, href)
    next: tuple[str, str] | None


def part_title_for(roman: str) -> str:
    for num, title, _ in PART_TITLES:
        if num == roman:
            return title
    return roman


def _rel_href(from_file: str, to_file: str) -> str:
    """Relative href between two files in the rendered tree."""
    return "../" + to_file if from_file.startswith("pages/") else to_file


def _document(
    title: str,
    description: str,
    depth: str,
    body: str,
    body_class: str = "",
    extra_head: str = "",
) -> str:
    prefix = depth
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="{THEME_COLOR}">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="stylesheet" href="{prefix}assets/mojo.css">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='7' fill='%23ff7a1a'/%3E%3Cpath d='M7 22V10l5 7 5-7v12' fill='none' stroke='%230c0906' stroke-width='2.6' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E">
{extra_head}
</head>
<body class="{body_class}">
<a class="skip" href="#main">Skip to content</a>
<div class="progress" role="presentation"></div>
{body}
<script src="{prefix}assets/mojo.js" defer></script>
</body>
</html>
"""


def _header(page_meta: PageMeta | None, prefix: str) -> str:
    if page_meta:
        part_label = (
            f'<span class="head__part">Part {esc(page_meta.part)} '
            f"· {esc(page_meta.part_title)}</span>"
        )
        search_index = f"{prefix}assets/search-index.json"
    else:
        part_label = '<span class="head__part">The whole manual</span>'
        search_index = "assets/search-index.json"
    return f"""<header class="head">
<a class="brand" href="{prefix}index.html"><span class="brand__mark">Mojo</span> v1 <span class="brand__sub">· The Language Manual</span></a>
{part_label}
<span class="head__spacer"></span>
<div class="search" data-search-index="{search_index}">
  <label class="visually-hidden" for="search">Search the manual</label>
  <input class="search__input" id="search" type="search" placeholder="Search the manual" data-search autocomplete="off" spellcheck="false">
  <span class="search__hint">/</span>
  <div class="search__results" data-search-results role="listbox" aria-label="Search results"></div>
</div>
<button class="iconbtn" type="button" data-theme-toggle aria-label="Switch theme">☀</button>
</header>"""


def _footer(prefix: str) -> str:
    return f"""<footer class="foot"><div class="foot__inner">
<span>Rendered from the saved Mojo v1 documentation. Text and code belong to Modular.</span>
<span><a href="{prefix}index.html">Contents</a> · <a href="{prefix}raw/">Archives</a></span>
</div></footer>"""


def _rail(meta: PageMeta, headings: list[tuple[int, str, str]]) -> str:
    items = []
    for level, text, anchor in headings:
        if level < 2 or level > 4:
            continue
        items.append(
            f'<li class="rail__depth-{level}">'
            f'<a href="#{anchor}">{esc(text)}</a></li>'
        )
    if not items:
        return ""
    toc = (
        '<p class="rail__title">On this page</p><ol>' + "".join(items) + "</ol>"
    )
    return f"""<details class="rail rail--inline"><summary>On this page</summary>{toc}</details>
<nav class="rail" aria-label="On this page">{toc}
<p class="rail__meta">Chapter {meta.index:02d} of 38 · Part {esc(meta.part)}, {esc(meta.part_title)}.</p>
</nav>"""


def _pager(meta: PageMeta) -> str:
    left = ""
    right = ""
    if meta.prev:
        left = (
            '<a class="pager__link pager__link--prev" href="%s">'
            '<span class="pager__dir">← Previous</span>'
            '<span class="pager__title">%s</span></a>' % (meta.prev[1], esc(meta.prev[0]))
        )
    if meta.next:
        right = (
            '<a class="pager__link pager__link--next" href="%s">'
            '<span class="pager__dir">Next →</span>'
            '<span class="pager__title">%s</span></a>' % (meta.next[1], esc(meta.next[0]))
        )
    return f'<nav class="pager" aria-label="Chapter navigation">{left}{right}</nav>'


def render_page(meta: PageMeta, page, stats: dict[str, int]) -> str:
    """Render one chapter page."""
    file_name = f"pages/{meta.entry.slug}.html"
    crumb = (
        '<nav class="crumb" aria-label="Breadcrumb">'
        '<a href="../index.html">Manual</a><span class="sep">/</span>'
        f'<span>Part {esc(meta.part)}</span><span class="sep">/</span>'
        f'<span>{esc(meta.part_title)}</span><span class="sep">/</span>'
        f'<span class="num">{meta.index:02d}</span>'
        "</nav>"
    )

    dek = f'<p class="dek">{esc(meta.dek or page.dek)}</p>' if (meta.dek or page.dek) else ""

    byline_bits = [f"Chapter {meta.index:02d} · {stats['words']:,} words"]
    if stats["code_blocks"]:
        byline_bits.append(f"{stats['code_blocks']} code blocks")
    byline = '<p class="byline">' + " · ".join(esc(b) for b in byline_bits)
    if page.source_url:
        byline += (
            f' · <a class="ext" href="{esc(page.source_url)}"'
            ' rel="noopener noreferrer" data-external>docs source</a>'
        )
    byline += "</p>"

    colophon = ""
    if page.source_url:
        colophon = (
            '<p class="colophon">This chapter is a faithful rendering of the Mojo '
            f'documentation page <a class="ext" href="{esc(page.source_url)}"'
            ' rel="noopener noreferrer" data-external>'
            f"{esc(page.source_url)}</a>"
            + (f", saved {esc(page.source_date)}." if page.source_date else ".")
            + "</p>"
        )

    article = f"""<article class="article">
{crumb}<h1>{esc(meta.title)}</h1>
{dek}{byline}
{page.body_html}
{colophon}
{_pager(meta)}
</article>"""

    body = f"""{_header(meta, "../")}
<main class="shell" id="main">
{article}
{_rail(meta, page.headings)}
</main>
{_footer("../")}"""

    description = (meta.dek or page.dek or meta.title)[:180]
    return _document(
        f"{meta.title} · {BOOK_TITLE} {BOOK_SUBTITLE}",
        description,
        "../",
        body,
        body_class="page",
    )


def render_cover(entries, descriptions: dict[str, str], totals: dict[str, int]) -> str:
    """Render index.html: hero, part map, full contents."""
    parts_html = []
    for roman, title, blurb in PART_TITLES:
        members = [e for e in entries if e.part == roman]
        rows = []
        for entry in members:
            desc = descriptions.get(entry.slug, entry.blurb)
            rows.append(
                f'<li class="toc__item"><a class="toc__link" href="pages/{entry.slug}.html">'
                f'<span class="toc__num">{entry.order:02d}</span>'
                f'<span><span class="toc__title">{esc(entry.title)}</span>'
                f'<span class="toc__blurb">{esc(desc)}</span></span>'
                f'<span class="toc__go" aria-hidden="true">→</span></a></li>'
            )
        parts_html.append(
            f"""<section class="part" id="part-{roman.lower()}">
<div class="part__head">
<span class="part__num">PART {roman}</span>
<div><h2 class="part__title">{esc(title)}</h2><p class="part__blurb">{esc(blurb)}</p></div>
<span class="part__count">{len(members)} chapter{'s' if len(members) != 1 else ''}</span>
</div>
<ul class="toc">{''.join(rows)}</ul>
</section>"""
        )

    body = f"""{_header(None, "")}
<main class="shell shell--single" id="main">
<div class="hero">
<div class="hero__eyebrow">Single source of truth</div>
<h1>The Mojo language, <em>end to end</em>.</h1>
<p class="hero__lede">{esc(BOOK_BLURB)}</p>
<div class="stats">
<div class="stat"><b>{totals['chapters']}</b><span>Chapters</span></div>
<div class="stat"><b>{totals['words']:,}</b><span>Words</span></div>
<div class="stat"><b>{totals['code_blocks']:,}</b><span>Code blocks</span></div>
<div class="stat"><b>{totals['languages']}</b><span>Languages</span></div>
<div class="stat"><b>{len(PART_TITLES)}</b><span>Parts</span></div>
</div>
</div>
<div class="cover">
<h2 class="h h--2" id="contents">Contents</h2>
<p class="cover__lede">Seven parts, thirty-eight chapters, in reading order. Every chapter carries its own
table of contents, copyable code, and links back to the manual it came from.</p>
{''.join(parts_html)}
</div>
</main>
{_footer("")}"""

    return _document(
        f"{BOOK_TITLE} {BOOK_SUBTITLE} · Contents",
        BOOK_BLURB[:180],
        "",
        body,
        body_class="cover",
    )


def render_search_index(records: list[dict]) -> str:
    return json.dumps(records, ensure_ascii=False, separators=(",", ":")) + "\n"


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))