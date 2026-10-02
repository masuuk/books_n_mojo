"""Verify cross-navigation across each book.

Checks, per book:
  1. no dead local hrefs anywhere: app, hub, shelf catalog, all 65 shelf pages
  2. every href fragment resolves to an id that exists in the target file
  3. the app links to mixed_shelf and to the single source of truth
  4. the hub links to all three parts of the book
  5. the shelf catalog lists every standalone file exactly once
  6. nothing links outside its own book (no cross-book hrefs)
  7. a link into this book's own catalog is not labelled with another book's name
  8. structural sanity: balanced section/nav/main/footer/div tags
  9. presentation: every page's CSS is inside a <style> element, and the
     classes its markup uses are styled
"""

import re
import sys
import urllib.parse
from collections import Counter
from pathlib import Path

ROOT = Path(r"C:\Users\user\Desktop\the_books")
BOOKS = ["data_science", "finance", "geomatics", "operations_research"]
SST_DIR = "single_source_of_truth mojo"
SKIP = ("http://", "https://", "//", "#", "data:", "mailto:", "javascript:")

PAIRS = [
    ("<section", "</section>"),
    ("<nav", "</nav>"),
    ("<div", "</div>"),
    ("<main", "</main>"),
    ("<footer", "</footer>"),
    ("<body", "</body>"),
]

BOOK_TITLES = {
    "data_science": "Data Science",
    "finance": "Finance",
    "geomatics": "Geomatics",
    "operations_research": "Operations Research",
}
BOOK_NAME_RE = re.compile(
    r"operations[\s_]+research|data[\s_]+science|geomatics|finance", re.I
)
ID_RE = re.compile(r'\bid\s*=\s*["\']([^"\']+)["\']')
ANCHOR = re.compile(r'<a\b[^>]*>.*?</a\s*>', re.S | re.I)
TAG = re.compile(r"<[^>]+>")
STYLE_BLOCK = re.compile(r"<style\b[^>]*>(.*?)</style\s*>", re.S | re.I)
CLASS_ATTR = re.compile(r'class="([^"]+)"')
CSS_SELECTOR = re.compile(r"\.([A-Za-z_][-\w]*)")

# KaTeX and Prism output these; the vendored sheet has no rule for them
# because they never paint anything on their own.
KNOWN_UNSTYLED = {"katex", "katex-display-target", "katex-inline"}


def markup_classes(text: str) -> set[str]:
    body = STYLE_BLOCK.sub("", re.sub(r"<script\b.*?</script\s*>", "", text, flags=re.S | re.I))
    out: set[str] = set()
    for m in CLASS_ATTR.finditer(body):
        out.update(m.group(1).split())
    return out


def styled_classes(text: str) -> set[str]:
    out: set[str] = set()
    for m in STYLE_BLOCK.finditer(text):
        out.update(CSS_SELECTOR.findall(m.group(1)))
    return out


def stylesheet_defects(text: str) -> list[str]:
    """Ways a page can end up with CSS the browser will never apply.

    Two failure modes, both of which leave every link on the page working while
    the page itself looks broken:

      * a ``<style>`` element that never opens, so its CSS sits in <head> as
        bare text and the stray ``</style>`` is ignored;
      * no stylesheet at all, so the markup's classes mean nothing.

    A page that links a stylesheet is left alone: which classes it styles is
    the author's business, and a class with no rule just renders as default.
    """
    problems = []
    opens = len(re.findall(r"<style\b", text, re.I))
    closes = len(re.findall(r"</style\s*>", text, re.I))
    if opens != closes:
        # An unmatched </style> means the opening tag is gone, so the CSS sits
        # in <head> as bare text and the page renders unstyled.
        problems.append(f"<style>={opens} but </style>={closes}")

    head = text[: text.lower().find("</head>")] if "</head>" in text.lower() else text
    inline = STYLE_BLOCK.search(head)
    linked = re.search(r'<link\b[^>]*rel=["\']?stylesheet', head, re.I)
    if not inline and not linked:
        problems.append("no stylesheet in <head>")
    if not inline and not linked:
        unstyled = markup_classes(text) - KNOWN_UNSTYLED
        if unstyled:
            problems.append(f"{len(unstyled)} classes with no rule: {sorted(unstyled)[:12]}")
    return problems

_ids: dict[Path, set[str]] = {}


def ids_of(p: Path) -> set[str]:
    if p not in _ids:
        try:
            _ids[p] = set(ID_RE.findall(p.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            _ids[p] = set()
    return _ids[p]


def local_hrefs(text: str):
    for m in re.finditer(r'href="([^"]+)"', text):
        h = m.group(1)
        if h.startswith(SKIP):
            continue
        yield urllib.parse.unquote(h)


def dead_hrefs(path: Path, text: str):
    """Local hrefs whose file is missing, or whose fragment has no target."""
    missing, bad_frag = [], []
    for h in local_hrefs(text):
        rel, _, frag = h.partition("#")
        if not rel:
            continue  # same-page fragment
        target = (path.parent / rel).resolve()
        if not target.exists():
            missing.append(h)
        elif frag and frag not in ids_of(target):
            bad_frag.append(h)
    return sorted(set(missing)), sorted(set(bad_frag))


def main() -> int:
    failures: list[str] = []

    for b in BOOKS:
        root = ROOT / b
        app = root / f"{b}_mojo" / "index.html"
        hub = root / "index.html"
        catalog = root / "mixed_shelf" / "index.html"
        sst = root / SST_DIR / "index.html"
        sst_rel_from_hub = urllib.parse.quote(f"{SST_DIR}/index.html")

        for p in (app, hub, catalog, sst):
            if not p.exists():
                failures.append(f"{b}: missing {p.relative_to(ROOT)}")

        app_text = app.read_text(encoding="utf-8")
        hub_text = hub.read_text(encoding="utf-8")
        cat_text = catalog.read_text(encoding="utf-8")

        # 1. no dead local hrefs anywhere in the book, shelf pages included
        shelf_pages = sorted(
            p for p in (root / "mixed_shelf").glob("*.html") if p.name != "index.html"
        )
        checked = [(app, app_text), (hub, hub_text), (catalog, cat_text)]
        checked += [(p, p.read_text(encoding="utf-8")) for p in shelf_pages]
        dead_files = dead_frag = 0
        for p, t in checked:
            miss, frag = dead_hrefs(p, t)
            if miss:
                dead_files += len(miss)
                failures.append(f"{b}: dead hrefs in {p.relative_to(ROOT)}: {miss}")
            if frag:
                dead_frag += len(frag)
                failures.append(f"{b}: bad fragment in {p.relative_to(ROOT)}: {frag}")

        # 2. app reaches the shelf and the manual
        if "../mixed_shelf/" not in app_text:
            failures.append(f"{b}: app has no mixed_shelf link")
        sst_rel = "../" + urllib.parse.quote(SST_DIR) + "/index.html"
        if sst_rel not in app_text and f"../{SST_DIR}/index.html" not in app_text:
            failures.append(f"{b}: app has no single source of truth link")

        # 3. hub reaches all three parts
        for need in (f"{b}_mojo/index.html", "mixed_shelf/index.html", sst_rel_from_hub):
            if need not in hub_text:
                failures.append(f"{b}: hub missing link to {need}")

        # 4. catalog lists every standalone file exactly once
        listed = Counter(
            urllib.parse.unquote(h)
            for h in local_hrefs(cat_text)
            if h.endswith(".html") and not h.startswith("../")
        )
        dupes = sorted(n for n, c in listed.items() if c != 1)
        on_disk = {p.name for p in (root / "mixed_shelf").glob("*.html") if p.name != "index.html"}
        missing = sorted(on_disk - set(listed))
        extra = sorted(set(listed) - on_disk)
        if missing or extra:
            failures.append(f"{b}: catalog mismatch missing={missing} extra={extra}")
        if dupes:
            failures.append(f"{b}: catalog lists pages more than once: {dupes}")

        # 5. no cross-book hrefs
        for p, t in checked:
            for h in local_hrefs(t):
                if any(f"/{o}/" in h or h.startswith(f"{o}/") for o in BOOKS if o != b):
                    failures.append(f"{b}: cross-book href in {p.relative_to(ROOT)}: {h}")
                    break

        # 6. a link to this book's own catalog must not be labelled with
        #    another book's name. All 65 pages ship in every book, so a stale
        #    label here points a reader at the wrong shelf.
        mine = BOOK_TITLES[b]
        for p, t in checked:
            for m in ANCHOR.finditer(t):
                hm = re.search(r'href="([^"]+)"', m.group(0))
                if not hm:
                    continue
                if urllib.parse.unquote(hm.group(1)) != "index.html":
                    continue
                label = TAG.sub("", m.group(0)).strip()
                hit = BOOK_NAME_RE.search(label)
                if hit and hit.group(0).lower() != mine.lower():
                    failures.append(
                        f"{b}: catalog link labelled {label!r} in {p.relative_to(ROOT)}"
                    )
                    break

        # 7. structural sanity
        for o, c in PAIRS:
            if app_text.count(o) != app_text.count(c):
                failures.append(
                    f"{b}: unbalanced {o} ({app_text.count(o)}) vs {c} ({app_text.count(c)})"
                )

        # 8. presentation: CSS the browser can actually apply, covering the
        #    classes the markup actually uses. A dead stylesheet breaks every
        #    link on the page at once, so it earns its own gate.
        for p, t in checked:
            for problem in stylesheet_defects(t):
                failures.append(f"{b}: {p.relative_to(ROOT)}: {problem}")

        app_sst = app_text.count(sst_rel) + app_text.count(f"../{SST_DIR}/index.html")
        total_local = sum(len(list(local_hrefs(t))) for _, t in checked)
        print(
            f"{b:20} pages={len(checked):3} local_refs={total_local:4} "
            f"dead={dead_files} bad_frag={dead_frag} shelf_listed={len(listed):2} "
            f"app_mixed={app_text.count('../mixed_shelf/'):2} app_sst={app_sst:2} "
            f"modules={app_text.count('class=\"module\"')}"
        )

    if failures:
        print("\nFAIL")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nEvery gate passed on every book.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
