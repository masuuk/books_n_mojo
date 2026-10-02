"""Build the Mojo v1 language manual from saved .mhtml archives.

    uv run tools/build_mojo_manual.py            # build every book
    uv run tools/build_mojo_manual.py --book ds  # build one book
    uv run tools/build_mojo_manual.py --check    # verify only, change nothing

Each book gets its own complete tree. Nothing is shared at runtime and nothing is
fetched by the reader: every page, stylesheet, script and diagram is local.
"""

from __future__ import annotations

import argparse
import filecmp
import re
import shutil
import sys
from pathlib import Path

from mojomanual import images as image_tools
from mojomanual.clean import ImagePlan, clean_article
from mojomanual.extract import page_title, read_archive
from mojomanual.manifest import ORDER, canonical_path
from mojomanual.render import (
    PageMeta,
    part_title_for,
    render_cover,
    render_page,
    render_search_index,
    word_count,
)

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
ASSETS = HERE / "mojomanual" / "assets"
CACHE = HERE / ".cache"

BOOKS = {
    "ds": REPO / "data_science",
    "fin": REPO / "finance",
    "geo": REPO / "geomatics",
    "or": REPO / "operations_research",
}

MANUAL_DIRNAME = "single_source_of_truth mojo"
EXCLUDED_DIRS = {"pages", "assets", "raw", "__pycache__"}


# --------------------------------------------------------------------------- #
# locating the archives
# --------------------------------------------------------------------------- #


def archives_in(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    found = [
        p
        for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() == ".mhtml"
    ]
    return sorted(found, key=lambda p: p.name.lower())


def resolve_source(folder: Path) -> Path:
    """Archives may sit at the top of the folder or already be filed under raw/."""
    if archives_in(folder):
        return folder
    raw = folder / "raw"
    if archives_in(raw):
        return raw
    raise FileNotFoundError(f"no .mhtml archives found in {folder} or {folder / 'raw'}")


# --------------------------------------------------------------------------- #
# building
# --------------------------------------------------------------------------- #


def build(book_key: str, offline: bool = False, move_raw: bool = True) -> dict:
    book_root = BOOKS[book_key]
    folder = book_root / MANUAL_DIRNAME
    source = resolve_source(folder)

    entries_by_path = {e.path: e for e in ORDER}
    page_paths = {
        e.path: f"../pages/{e.slug}.html" for e in ORDER
    }

    # ---- pass 1: read + clean every archive, to learn every anchor ---------- #
    image_plan = ImagePlan()
    missing: list[str] = []
    cleaned = []

    for archive_file in archives_in(source):
        archive = read_archive(archive_file)
        key = canonical_path(archive.url)
        entry = entries_by_path.get(key or "")
        if entry is None:
            missing.append(f"{archive_file.name} -> {key}")
            continue
        # images embedded in this archive
        for name, payload in archive.assets.items():
            image_plan.files.setdefault(
                f"https://mojolang.org/assets/images/{name}", payload
            )
        page = clean_article(
            archive.article,
            page_title(archive),
            archive.url,
            archive.date,
            page_paths,
            here=page_paths[entry.path],
            images=image_plan,
        )
        cleaned.append((entry, page, archive_file))

    if missing:
        raise SystemExit(
            "archives with no place in the reading order:\n  " + "\n  ".join(missing)
        )

    cleaned.sort(key=lambda item: item[0].order)
    if len(cleaned) != len(ORDER):
        raise SystemExit(f"expected {len(ORDER)} chapters, matched {len(cleaned)}")

    # every id any page can be jumped to
    fragments = {entry.path: page.anchors for entry, page, _ in cleaned}

    # ---- pass 2: clean again, now able to drop cross-page dead fragments --- #
    # Modular's own docs carry a few anchors that resolve nowhere; rather than
    # ship a broken jump, a cross-page link falls back to the top of its target.
    for index, (entry, _, archive_file) in enumerate(cleaned):
        archive = read_archive(archive_file)
        cleaned[index] = (
            entry,
            clean_article(
                archive.article,
                page_title(archive),
                archive.url,
                archive.date,
                page_paths,
                here=page_paths[entry.path],
                images=image_plan,
                fragments=fragments,
            ),
            archive_file,
        )

    # ---- diagrams -------------------------------------------------------- #
    resolved_images = image_tools.fetch(image_plan.files, CACHE / "images", offline)

    # ---- render ---------------------------------------------------------- #
    out_pages = folder / "pages"
    out_assets = folder / "assets"
    for target in (out_pages, out_assets):
        if target.exists():
            shutil.rmtree(target)
    out_pages.mkdir(parents=True, exist_ok=True)
    (out_assets / "images").mkdir(parents=True, exist_ok=True)

    shutil.copyfile(ASSETS / "mojo.css", out_assets / "mojo.css")
    shutil.copyfile(ASSETS / "mojo.js", out_assets / "mojo.js")

    written_images: set[str] = set()
    for url, payload in resolved_images.items():
        name = url.rsplit("/", 1)[-1]
        if name in written_images:
            continue
        (out_assets / "images" / name).write_bytes(payload)
        written_images.add(name)

    search_records: list[dict] = []
    totals = {"chapters": 0, "words": 0, "code_blocks": 0, "languages": 0}
    languages: set[str] = set()
    descriptions: dict[str, str] = {}

    by_order = {entry.order: (entry, page) for entry, page, _ in cleaned}

    for position, (entry, page, _) in enumerate(cleaned):
        prev_entry = by_order.get(entry.order - 1)
        next_entry = by_order.get(entry.order + 1)
        meta = PageMeta(
            index=entry.order,
            entry=entry,
            title=entry.title,
            dek=entry.blurb,
            part=entry.part,
            part_title=part_title_for(entry.part),
            prev=(
                (prev_entry[0].title, f"../pages/{prev_entry[0].slug}.html")
                if prev_entry
                else None
            ),
            next=(
                (next_entry[0].title, f"../pages/{next_entry[0].slug}.html")
                if next_entry
                else None
            ),
        )

        words = word_count(page.plain_text)
        stats = {"words": words, "code_blocks": page.stats["code_blocks"]}
        html = render_page(meta, page, stats)
        (out_pages / f"{entry.slug}.html").write_text(html, encoding="utf-8")

        descriptions[entry.slug] = entry.blurb or page.dek
        totals["chapters"] += 1
        totals["words"] += words
        totals["code_blocks"] += page.stats["code_blocks"]
        languages.update(page.stats["languages"])
        search_records.append(
            {
                "url": f"pages/{entry.slug}.html",
                "title": entry.title,
                "part": f"Part {entry.part} · {part_title_for(entry.part)}",
                "headings": [text for level, text, _ in page.headings if level >= 2],
                "text": page.plain_text,
            }
        )

    # language inventory straight from the rendered pages
    totals["languages"] = len(languages)

    (out_assets / "search-index.json").write_text(
        render_search_index(search_records), encoding="utf-8"
    )
    (folder / "index.html").write_text(
        render_cover(ORDER, descriptions, totals), encoding="utf-8"
    )

    # ---- archive the raw material ---------------------------------------- #
    raw_dir = folder / "raw"
    if move_raw and source != raw_dir:
        raw_dir.mkdir(exist_ok=True)
        for archive_file in archives_in(source):
            shutil.move(str(archive_file), str(raw_dir / archive_file.name))

    return {
        "book": book_key,
        "chapters": totals["chapters"],
        "words": totals["words"],
        "code_blocks": totals["code_blocks"],
        "images": len(written_images),
        "code_blocks_missing_images": len(image_plan.files) - len(resolved_images),
    }


# --------------------------------------------------------------------------- #
# verification
# --------------------------------------------------------------------------- #

#: Substrings that betray the site generator or a browser extension.
FORBIDDEN = [
    "cid:",
    "chrome-extension",
    "googletagmanager",
    "cookiebot",
    "mantine-",
    "docusaurus",
    "mcafee",
    "admonitionAlert",
    "codeBlockLines",
    "codeBlockContainer",
    "hash-link",
    "theme-code-block",
    "buttonGroup",
    'style="',
]

#: The documentation's own provenance link, allowed to point off-book.
PROVENANCE = "https://mojolang.org/docs/"

#: Attributes that *load* something. A book must never reach the network for any
#: of these; hyperlinks are a separate, deliberate thing.
SUBRESOURCE_ATTRS = ("src", "srcset", "data-src", "poster")


def _refs(text: str, attr: str) -> list[str]:
    return re.findall(attr + r'="([^"]+)"', text)


def _local_refs(text: str) -> list[str]:
    """Every src/srcset reference in a document."""
    refs = []
    for attr in SUBRESOURCE_ATTRS:
        refs.extend(_refs(text, attr))
    refs.extend(re.findall(r'<link[^>]+href="([^"]+)"', text))
    return refs


def _anchor_tags(text: str) -> list[tuple[str, str]]:
    """[(href, full opening tag)] for every anchor that has an href."""
    out = []
    for tag in re.findall(r"<a\b[^>]*>", text):
        match = re.search(r'href="([^"]+)"', tag)
        if match:
            out.append((match.group(1), tag))
    return out


def check(book_key: str) -> list[str]:
    folder = BOOKS[book_key] / MANUAL_DIRNAME
    problems: list[str] = []

    if not (folder / "index.html").exists():
        return [f"{book_key}: no index.html"]

    html_files = sorted(folder.glob("*.html")) + sorted((folder / "pages").glob("*.html"))
    if len(html_files) != len(ORDER) + 1:
        problems.append(f"{book_key}: expected {len(ORDER) + 1} pages, found {len(html_files)}")

    for path in html_files:
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(folder).as_posix()

        for needle in FORBIDDEN:
            if needle in text:
                problems.append(f"{book_key}/{rel}: contains {needle!r}")

        # nothing may be loaded from the network
        for ref in _local_refs(text):
            if ref.startswith(("http://", "https://", "//", "cid:")):
                problems.append(f"{book_key}/{rel}: remote subresource {ref}")
                continue
            if ref.startswith("data:"):
                continue
            if not (path.parent / ref.split("#", 1)[0]).exists():
                problems.append(f"{book_key}/{rel}: dead subresource {ref}")

        # the search index the page claims to load must be there
        claimed = re.search(r'data-search-index="([^"]+)"', text)
        if claimed and not (path.parent / claimed.group(1)).exists():
            problems.append(f"{book_key}/{rel}: search index {claimed.group(1)} not found")

        # hyperlinks: local ones must resolve; remote ones must be marked external
        for ref, tag in _anchor_tags(text):
            if ref.startswith(("http://", "https://", "//")):
                if "ext" not in tag:
                    problems.append(f"{book_key}/{rel}: undeclared external link {ref}")
                continue
            if ref.startswith(("#", "mailto:", "data:")):
                continue
            target = ref.split("#", 1)[0]
            if target and not (path.parent / target).exists():
                problems.append(f"{book_key}/{rel}: dead link {ref}")
            if "#" in ref:
                fragment = ref.split("#", 1)[1]
                anchor_host = (path.parent / target) if target else path
                if fragment and anchor_host.suffix == ".html":
                    target_text = anchor_host.read_text(encoding="utf-8")
                    if f'id="{fragment}"' not in target_text:
                        problems.append(
                            f"{book_key}/{rel}: no anchor #{fragment} in {target}"
                        )

    for asset in ("assets/mojo.css", "assets/mojo.js", "assets/search-index.json"):
        if not (folder / asset).exists():
            problems.append(f"{book_key}: missing {asset}")

    # the stylesheet must not pull anything in
    css = folder / "assets" / "mojo.css"
    if css.exists():
        for ref in re.findall(r'url\(\s*["\']?([^"\')]+)', css.read_text(encoding="utf-8")):
            if ref.startswith(("http", "//", "data:")):
                continue
            if not (css.parent / ref.split("#", 1)[0]).exists():
                problems.append(f"{book_key}: css references missing {ref}")

    return problems


def independence() -> list[str]:
    """No rendered file may reach outside its own book."""
    problems: list[str] = []
    for key, root in BOOKS.items():
        folder = root / MANUAL_DIRNAME
        if not folder.exists():
            continue
        boundary = folder.resolve()
        for path in list(folder.rglob("*.html")) + list(folder.rglob("*.css")):
            if path.suffix == ".html":
                refs = re.findall(r'(?:src|href)="([^"]+)"', path.read_text(encoding="utf-8"))
            else:
                refs = re.findall(r'url\("?([^")]+)', path.read_text(encoding="utf-8"))
            for ref in refs:
                if ref.startswith(("http", "//", "#", "data:", "mailto:")):
                    continue
                target = (path.parent / ref.split("#", 1)[0].split("?", 1)[0]).resolve()
                if boundary not in target.parents and target != boundary:
                    problems.append(
                        f"{key}/{path.relative_to(boundary).as_posix()}: escapes the book ({ref})"
                    )
    return problems


def parity() -> list[str]:
    """The four rendered trees should be identical, book for book."""
    problems: list[str] = []
    reference = BOOKS["ds"] / MANUAL_DIRNAME
    if not reference.exists():
        return problems
    for key in ("fin", "geo", "or"):
        other = BOOKS[key] / MANUAL_DIRNAME
        if not other.exists():
            continue
        for path in sorted(reference.rglob("*")):
            if path.is_dir() or "raw" in path.parts:
                continue
            mirror = other / path.relative_to(reference)
            if not mirror.exists():
                problems.append(f"{key}: missing {path.relative_to(reference).as_posix()}")
            elif not filecmp.cmp(path, mirror, shallow=False):
                problems.append(f"{key}: differs at {path.relative_to(reference).as_posix()}")
    return problems


# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--book",
        choices=sorted(BOOKS) + ["all"],
        default="all",
        help="which book to build (default: all)",
    )
    parser.add_argument(
        "--check", action="store_true", help="verify the rendered trees without building"
    )
    parser.add_argument(
        "--offline", action="store_true", help="never fetch missing diagrams"
    )
    args = parser.parse_args(argv)

    targets = sorted(BOOKS) if args.book == "all" else [args.book]

    if not args.check:
        for key in targets:
            result = build(key, offline=args.offline)
            print(
                f"  {key:>4}  {result['chapters']:>2} chapters  "
                f"{result['words']:>6,} words  {result['code_blocks']:>3} code blocks  "
                f"{result['images']:>2} diagrams"
            )

    problems: list[str] = []
    for key in targets:
        problems.extend(check(key))
    problems.extend(independence())
    problems.extend(parity())

    if problems:
        print(f"\n{len(problems)} problem(s):", file=sys.stderr)
        for problem in problems[:60]:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    print("\nAll gates passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())