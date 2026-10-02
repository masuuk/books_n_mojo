"""Generate each book's mixed_shelf catalog.

The root index pages are custom-authored landing pages. Their local navigation
is checked by verify_navigation.py; this script owns only the generated shelf
catalogs, so running it cannot replace the custom designs.

Run with --check to verify the generated catalogs match what is on disk.
"""

import argparse
import html
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SST_DIR = "single_source_of_truth mojo"
BOOKS = ["data_science", "finance", "geomatics", "operations_research"]

TITLES = {
    "data_science": "Data Science",
    "finance": "Finance",
    "geomatics": "Geomatics",
    "operations_research": "Operations Research",
}

CSS = """
:root { color-scheme: dark; --bg:#0b1020; --panel:#131a2e; --line:#26304a;
        --fg:#e8ecf6; --dim:#98a2bd; --accent:#7aa2ff; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg);
       font:16px/1.6 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }
.wrap { max-width: 62rem; margin: 0 auto; padding: 3rem 1.25rem 4rem; }
header { border-bottom:1px solid var(--line); padding-bottom:1.5rem; margin-bottom:2rem; }
h1 { margin:0 0 .4rem; font-size:1.9rem; letter-spacing:-.01em; }
.lede { margin:0; color:var(--dim); max-width: 46rem; }
.cards { display:grid; gap:1rem; grid-template-columns:repeat(auto-fit,minmax(17rem,1fr)); }
.card { background:var(--panel); border:1px solid var(--line); border-radius:.7rem;
        padding:1.1rem 1.2rem; }
.card h2 { margin:0 0 .35rem; font-size:1.05rem; }
.card p { margin:0 0 .8rem; color:var(--dim); font-size:.9rem; }
a { color:var(--accent); }
a.big { display:inline-block; font-weight:600; text-decoration:none; }
a.big::after { content:" \2192"; }
ul { margin:.4rem 0 0; padding-left:1.1rem; color:var(--dim); font-size:.9rem; }
li { margin:.15rem 0; }
h2.sec { margin:2.5rem 0 1rem; font-size:1.15rem; }
footer { margin-top:3rem; padding-top:1.2rem; border-top:1px solid var(--line);
         color:var(--dim); font-size:.85rem; }
@media (prefers-color-scheme: light) {
  :root { color-scheme: light; --bg:#f7f8fc; --panel:#fff; --line:#dfe3ee;
          --fg:#141a2b; --dim:#5a6280; --accent:#2f5bd8; }
}
"""

def build_shelf(book: str) -> str:
    root = ROOT / book / "mixed_shelf"
    title = TITLES[book]
    up = "../index.html"
    sst = urllib.parse.quote(f"../{SST_DIR}/index.html")
    app = f"../{book}_mojo/index.html"

    files = sorted(p.name for p in root.glob("*.html") if p.name != "index.html")
    rows = []
    for name in files:
        label = name[:-5].replace("_", " ")
        rows.append(f'      <li><a href="{urllib.parse.quote(name)}">{html.escape(label)}</a></li>')
    listing = "\n".join(rows)

    groups = []
    for gname, pred in [
        ("Advanced series", lambda n: n.startswith("ds_advanced_")),
        ("Machine learning textbook", lambda n: n.startswith("ds_ml_textbook_")),
        ("Data science textbook", lambda n: n.startswith("ds_textbook_")),
    ]:
        sel = [n for n in files if pred(n)]
        if sel:
            groups.append(f"      <li><strong>{gname}</strong> ({len(sel)} pages)</li>")
    series = "\n".join(groups)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} shelf</title>
<meta name="description" content="Standalone {html.escape(title)} Mojo reference pages.">
<style>{CSS}</style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1>{title} shelf</h1>
      <p class="lede">{len(files)} standalone reference pages. Each one is self-contained and opens without the app.</p>
    </header>

    <div class="cards">
      <div class="card">
        <h2>Back to the book</h2>
        <p>All three parts of this book in one place.</p>
        <a class="big" href="{up}">{title} home</a>
      </div>
      <div class="card">
        <h2>Interactive tutorial</h2>
        <p>Hands-on modules with live widgets.</p>
        <a class="big" href="{app}">Open the app</a>
      </div>
      <div class="card">
        <h2>Single source of truth</h2>
        <p>The full manual.</p>
        <a class="big" href="{sst}">Read the manual</a>
      </div>
    </div>

    <h2 class="sec">All pages</h2>
    <ul>
{listing}
    </ul>

    <footer>
      <p>Series counts:</p>
      <ul>
{series}
      </ul>
    </footer>
  </div>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    bad = []
    for book in BOOKS:
        p = ROOT / book / "mixed_shelf" / "index.html"
        content = build_shelf(book)
        if args.check:
            if not p.exists():
                bad.append(f"missing {p}")
            elif p.read_text(encoding="utf-8") != content:
                bad.append(f"stale {p}")
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            print(f"wrote {p.relative_to(ROOT)}")

    if args.check:
        if bad:
            print("FAIL")
            for b in bad:
                print("  - " + b)
            return 1
        print("Shelf catalogs match their generator.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
