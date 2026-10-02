"""Repair the dead local links inside the mixed_shelf pages.

The 65 shelf pages were written for a site layout that no longer exists. They
still point at a two-volume `mojo_v1/` manual, an `applications/` index, a
`praxis/` drill tree, a site root above the book, and sibling books. This script
rewrites those references onto the three parts each book actually has now.

The mapping is deliberately explicit rather than clever. Each old target has
one decided replacement, and targets with no honest replacement are unwrapped to
plain text instead of being pointed at something arbitrary.

    uv run tools/fix_shelf_links.py          # rewrite
    uv run tools/fix_shelf_links.py --dry    # report only

Idempotent: a second run finds nothing to do.
"""

import argparse
import re
import sys
import urllib.parse
from collections import Counter
from pathlib import Path

ROOT = Path(r"C:\Users\user\Desktop\the_books")
BOOKS = ["data_science", "finance", "geomatics", "operations_research"]
SST = "single_source_of_truth mojo"

# Old two-volume manual -> the one manual that replaced it.
MANUAL_INDEX = f"../{urllib.parse.quote(SST)}/index.html"
# The two old volumes covered the language and the applied work; both are now
# the same book, so both land on its cover page.
OLD_MANUAL_TO_MANUAL = {
    "../mojo_v1/index.html": MANUAL_INDEX,
    "../../mojo_v1/index.html": MANUAL_INDEX,
    "../mojo_v1/mojo_book_1.html": MANUAL_INDEX,
    "../mojo_v1/mojo_book_2.html": MANUAL_INDEX,
    # These two named real chapters. Point them at the chapter that covers the
    # same ground rather than dropping the specificity.
    "../mojo_v1/mojo_11_interop.html":
        f"../{urllib.parse.quote(SST)}/pages/24_python-interoperability.html",
    "../mojo_v1/mojo_09_syntax_tour.html":
        f"../{urllib.parse.quote(SST)}/pages/03_mojo-language-basics.html",
}

# The old applications index is the interactive app.
APPLICATIONS_TO_APP = {"../applications/index.html", "../../applications/index.html"}

# Praxis was a separate drill tree with no counterpart in these books, so its
# links are unwrapped rather than pointed at something unrelated. An anchor
# whose text is only a directional arrow carries no information once the link
# is gone, so those elements are dropped instead of leaving a dangling arrow.
PRAXIS = {
    "../praxis/index.html",
    "../../praxis/index.html",
    "../../praxis/drill_21.html",
    "../../praxis/drill_22.html",
    "../../praxis/progressive/prog_03_dms.html",
    "../../praxis/progressive/prog_09_bearing.html",
    "../../praxis/progressive/prog_12_ecef.html",
}
ARROW_ONLY = re.compile(r'^[\s\u2190-\u21ff\u2b00-\u2bff]+$')
TAG = re.compile(r"<[^>]+>")

# The nav's domain pill pointed at the book's own root. Every book carries all
# 65 shelf pages, so from inside a shelf page the useful target is that book's
# shelf catalog, not a second route to the hub the Home pill already offers.
BOOK_ROOT = re.compile(
    r"^\.\./(?P<book>data_science|finance|geomatics|operations_research)/index\.html$"
)

# Links into a sibling book. Each book is independent, and every shelf page
# already exists inside every book's own shelf, so these collapse to the local
# copy. That also removes the cross-book dependency.
CROSS_BOOK = {
    "../../data_science/decision_aware_ml.html": "decision_aware_ml.html",
    "../data_science/decision_aware_ml.html": "decision_aware_ml.html",
    "../operations_research/operations_research.html": "operations_research.html",
    "../finance/the_annuity_codex.html": "the_annuity_codex.html",
    "../geomatics/gnss_surveying.html": "gnss_surveying.html",
    # Sibling book roots collapse to this book's own hub.
    "../data_science/index.html": "../index.html",
    "../finance/index.html": "../index.html",
    "../geomatics/index.html": "../index.html",
    "../operations_research/index.html": "../index.html",
    "../../data_science/index.html": "../index.html",
    "../../finance/index.html": "../index.html",
    "../../geomatics/index.html": "../index.html",
    "../../operations_research/index.html": "../index.html",
}

# The old site root sat above the book. Each book now has its own hub.
SITE_ROOT = {"../../index.html"}

HREF = re.compile(r'''(?P<pre>\bhref\s*=\s*)(?P<q>["'])(?P<url>[^"']*)(?P=q)''')
UNWRAP = re.compile(
    r'''<a\b(?P<attrs>[^>]*?)\bhref\s*=\s*(?P<q>["'])(?P<url>[^"']*)(?P=q)(?P<rest>[^>]*)>'''
    r'''(?P<body>.*?)</a\s*>''',
    re.S | re.I,
)
STYLESHEET = re.compile(r'<link\s+rel="stylesheet"\s+href="\.\./styles\.css"\s*>', re.I)

# The two shelf pages that linked a shared stylesheet the book does not have.
# The other 63 carry their CSS inline; these get the same treatment so the page
# is self-contained rather than depending on an asset that was never shipped.
SHARED_CSS = """
<style>
:root{--bg:#05070f;--panel:#0d1220;--line:#1e2740;--fg:#e9edf7;--dim:#98a2bd;--accent:#5bd4ff}
@media (prefers-color-scheme:light){:root{--bg:#f6f8fc;--panel:#fff;--line:#dde3f0;--fg:#111827;--dim:#5a6280;--accent:#2f8fe0}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.65 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--accent)}
.wrap{max-width:60rem;margin:0 auto;padding:0 1.25rem}
nav{border-bottom:1px solid var(--line);background:rgba(13,18,32,.75);position:sticky;top:0;backdrop-filter:blur(8px)}
.navin{display:flex;align-items:center;gap:1rem;flex-wrap:wrap;padding:.8rem 1.25rem}
.brand{display:flex;align-items:center;gap:.5rem;font-weight:700;text-decoration:none;color:var(--fg)}
.logo{display:grid;place-items:center;width:22px;height:22px;color:var(--accent)}
.navlinks{display:flex;gap:.4rem;flex-wrap:wrap;margin-left:auto}
.pill{border:1px solid var(--line);border-radius:999px;padding:.28rem .75rem;font-size:.82rem;text-decoration:none;color:var(--dim)}
.pill:hover{color:var(--fg);border-color:var(--accent)}
.hero{padding:3.5rem 1.25rem 2rem;max-width:60rem;margin:0 auto}
.eyebrow{font-size:.74rem;letter-spacing:.14em;text-transform:uppercase;color:var(--accent)}
h1{margin:.4rem 0 .6rem;font-size:2.2rem;letter-spacing:-.02em}
.lead{margin:0;color:var(--dim);font-size:1.05rem}
.card{background:var(--panel);border:1px solid var(--line);border-radius:.8rem;padding:1.2rem 1.3rem}
.card.big{margin:1.8rem 0}
.code{background:#060a16;border:1px solid var(--line);border-radius:.55rem;padding:.9rem 1rem;overflow:auto;
  font:13.5px/1.6 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;white-space:pre-wrap}
.card p{margin:.9rem 0 0;color:var(--dim)}
.actions{display:flex;gap:.7rem;flex-wrap:wrap;margin-top:1.6rem}
.btn{display:inline-block;border:1px solid var(--line);border-radius:.5rem;padding:.5rem 1rem;text-decoration:none;color:var(--fg)}
.btn.primary{background:var(--accent);border-color:var(--accent);color:#05070f;font-weight:600}
footer{border-top:1px solid var(--line);margin-top:3rem;padding:1.2rem 1.25rem;color:var(--dim);font-size:.85rem}
</style>
"""


BOOK_TITLES = {
    "data_science": "Data Science",
    "finance": "Finance",
    "geomatics": "Geomatics",
    "operations_research": "Operations Research",
}
# Longest first so "Operations Research" is not shadowed by a shorter match.
BOOK_NAME_RE = re.compile(
    r"operations[\s_]+research|operations[\s_]+research|data[\s_]+science|geomatics|finance",
    re.I,
)
# A subject emoji immediately before a book name belonged to the page's own
# domain; once the name is corrected the emoji no longer fits.
LEADING_EMOJI = re.compile(r"^[\U0001f300-\U0001faff\u2600-\u27bf]+\s*")


def rewrite(book: str, url: str) -> str | None:
    """Return the replacement for a dead href, or None to leave it alone."""
    if url in OLD_MANUAL_TO_MANUAL:
        return OLD_MANUAL_TO_MANUAL[url]
    if url in APPLICATIONS_TO_APP:
        return f"../{book}_mojo/index.html"
    if url in CROSS_BOOK:
        return CROSS_BOOK[url]
    if url in SITE_ROOT:
        return "../index.html"
    return None


def is_book_root(url: str) -> bool:
    return bool(BOOK_ROOT.match(url))


PROSE_PARENTS = {"p", "li", "td", "dd", "blockquote", "section"}


def enclosing_tags(text: str, offsets: list[int]) -> list[str]:
    """For each offset, the innermost enclosing element name.

    A tag-stack walk, which is enough here because these are archived pages with
    balanced markup. Self-closing and void elements are skipped so they never
    sit on the stack.
    """
    VOID = {
        "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr",
    }
    stack: list[str] = []
    out: list[str] = []
    pos = 0
    idx = 0
    for m in re.finditer(r"<(/?)([a-zA-Z][-\w]*)((?:\"[^\"]*\"|'[^']*'|[^>\"'])*)(/?)>", text):
        closing, name, _attrs, selfclose = m.group(1), m.group(2).lower(), m.group(3), m.group(4)
        # Answer every offset that falls at or before this tag, so an offset
        # pointing at an element's own opening tag reports that element's
        # parent rather than the element itself.
        while idx < len(offsets) and offsets[idx] <= m.start():
            out.append(stack[-1] if stack else "")
            idx += 1
        if selfclose or name in VOID:
            continue
        if closing:
            if name in stack:
                while stack and stack.pop() != name:
                    pass
        else:
            stack.append(name)
        pos = m.end()
    while idx < len(offsets):
        out.append(stack[-1] if stack else "")
        idx += 1
    return out


def has_block_children(anchor: str) -> bool:
    """True when the anchor wraps block markup, which makes it a card not prose.

    A card link looks like <a><span class="tag">..</span><strong>..</strong>
    <small>..</small></a>. Unwrapping one leaves the fragments behind as loose
    text with no way to click them, so the whole card goes instead.
    """
    inner = anchor[anchor.find(">") + 1: anchor.rfind("</a")]
    return bool(re.search(r"<(span|strong|small|div|p|h[1-6])\b", inner, re.I))


def open_tag(m: re.Match, href: str, label: str) -> str:
    """Rebuild an anchor with a new href and label, keeping every other attribute.

    attrs and rest are the two attribute runs either side of href, so anything
    like class, style, or aria-current has to be carried across untouched.
    """
    before = re.sub(r"\s+", " ", m.group("attrs")).rstrip()
    after = re.sub(r"\s+", " ", m.group("rest")).strip()
    parts = [p for p in (before, f'href="{href}"', after) if p]
    return f'<a {" ".join(parts)}>{label}</a>'


def retitle(label: str, book: str) -> str:
    """Rewrite a book name in a link label to this book's name."""
    mine = BOOK_TITLES[book]
    out = BOOK_NAME_RE.sub(mine, label)
    # "Browse the Geomatics shelf" reads oddly once corrected only in the name;
    # strip an emoji that belonged to the old domain.
    return LEADING_EMOJI.sub("", out)


def fix_text(book: str, text: str) -> tuple[str, Counter]:
    counts: Counter = Counter()

    # 1. inline the stylesheet that was never shipped
    new, n = STYLESHEET.subn(SHARED_CSS, text)
    if n:
        counts["inlined-css"] += n
        text = new

    # 2. decide per Praxis link whether it is a menu entry or a mention in prose.
    #    A <p> that merely names Praxis keeps its words with the link stripped; a
    #    link that is a row in a nav strip, or a whole card, is a dead control
    #    and is removed outright.
    parents = enclosing_tags(text, [m.start() for m in UNWRAP.finditer(text)])
    for m, parent in zip(UNWRAP.finditer(text), parents):
        if urllib.parse.unquote(m.group("url")) not in PRAXIS:
            continue
        if has_block_children(m.group(0)):
            counts["drop-praxis-card"] += 1
        elif parent in PROSE_PARENTS:
            counts["unwrap-praxis-mention"] += 1
        else:
            counts["drop-praxis-menu"] += 1

    def element(m: re.Match) -> str:
        url = urllib.parse.unquote(m.group("url"))
        body = m.group("body")
        label = TAG.sub("", body).strip()

        if url in PRAXIS:
            if has_block_children(m.group(0)) or any(
                f'class="{c}' in m.group("attrs") for c in ("pill", "btn")
            ):
                return ""  # counted above
            if ARROW_ONLY.match(body):
                return ""
            # A trailing arrow promised navigation that no longer exists.
            return re.sub(r"\s*[\u2190-\u21ff\u2b00-\u2bff]+\s*$", "", body).strip()

        if is_book_root(url):
            counts["retargeted-book-root"] += 1
            return open_tag(m, "index.html", BOOK_TITLES[book])

        # Every book carries all 65 shelf pages, so a link to this book's own
        # catalog is correct but a label naming a different book is not.
        if url == "index.html":
            body = m.group("body")
            stripped = TAG.sub("", body)
            if BOOK_NAME_RE.search(stripped):
                fixed = retitle(stripped, book)
                if fixed != stripped:
                    counts["retitled-catalog-link"] += 1
                    return open_tag(m, "index.html", fixed)

        return m.group(0)

    text = UNWRAP.sub(element, text)

    # 3. rewrite the remaining dead hrefs
    def sub(m: re.Match) -> str:
        raw = m.group("url")
        dec = urllib.parse.unquote(raw)
        if is_book_root(dec):
            return m.group(0)  # already handled element-wise
        new = rewrite(book, dec)
        if new is None:
            return m.group(0)
        counts[f"rewrote:{dec}"] += 1
        # The replacements are plain relative paths, one segment deep, with a
        # single space at most. Quote only the space; double-encoding an already
        # quoted path would produce %2520 and break the link.
        encoded = new.replace(" ", "%20")
        return f'{m.group("pre")}{m.group("q")}{encoded}{m.group("q")}'

    text = HREF.sub(sub, text)
    return text, counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="report without writing")
    args = ap.parse_args()

    total: Counter = Counter()
    files_changed = 0

    for book in BOOKS:
        shelf = ROOT / book / "mixed_shelf"
        book_counts: Counter = Counter()
        for p in sorted(shelf.glob("*.html")):
            if p.name == "index.html":
                continue  # generated by build_book_nav.py
            text = p.read_text(encoding="utf-8")
            new, counts = fix_text(book, text)
            if new != text:
                files_changed += 1
                book_counts.update(counts)
                if not args.dry:
                    p.write_text(new, encoding="utf-8")
        total.update(book_counts)
        print(f"{book:20} {'would change' if args.dry else 'changed'} {files_changed:3} file(s) so far")

    print()
    if not total:
        print("Nothing to do; every dead link is already repaired.")
        return 0
    for k, v in total.most_common():
        label = "unwrapped praxis link" if k == "unwrapped-praxis" else k
        print(f"  {v:5}  {label}")
    print()
    print(("DRY RUN. " if args.dry else "") + f"{total.total()} edits across {files_changed} files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
