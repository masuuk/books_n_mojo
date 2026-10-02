"""Generate the per-book root hub (index.html) and the mixed_shelf catalog.

The hub is the entry point that the app's brand link already pointed at
(`../index.html`). It links the three parts of each book:

  - the interactive app          <book>_mojo/index.html
  - the single source of truth   single_source_of_truth mojo/index.html
  - the standalone mixed shelf   mixed_shelf/index.html

Run with --check to verify the generated files match what is on disk.
"""

import argparse
import html
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(r"C:\Users\user\Desktop\the_books")
SST_DIR = "single_source_of_truth mojo"
BOOKS = ["data_science", "finance", "geomatics", "operations_research"]

TITLES = {
    "data_science": "Data Science",
    "finance": "Finance",
    "geomatics": "Geomatics",
    "operations_research": "Operations Research",
}

# Standalone pages that belong to each book's own domain. The mixed shelf holds
# all 65 files in every book; these are the ones worth surfacing per book.
DOMAIN_PAGES = {
    "data_science": [
        "ai_agents_python_vs_mojo.html",
        "data_science.html",
        "decision_aware_ml.html",
        "ds_ml_textbook_09_syntax_tour.html",
        "ds_textbook_00_cover.html",
        "ds_tools.html",
        "fine_tuning_llms.html",
        "linear_regression.html",
        "mlp_xor.html",
        "neural_network.html",
        "nn_mojo.html",
        "numerical_python_to_mojo.html",
        "numoj.html",
        "perceptrons_and_activation.html",
        "time_series_analytics.html",
    ],
    "finance": [
        "future_value_and_annuities.html",
        "npv_amortisation.html",
        "the_annuity_codex.html",
    ],
    "geomatics": [
        "geo_computations.html",
        "gnss_surveying.html",
        "karney_krueger_equations.html",
    ],
    "operations_research": [
        "operations_research.html",
        "simplex_algorithm.html",
    ],
}

LANDING = {
    "data_science": "ds_advanced_00_cover.html",
    "finance": "future_value_and_annuities.html",
    "geomatics": "geo_computations.html",
    "operations_research": "simplex_algorithm.html",
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

LEDE = {
    "data_science": "Data science in Mojo: the interactive tutorial, the single source of truth manual, and the standalone reference pages.",
    "finance": "Quantitative finance in Mojo: the interactive tutorial, the single source of truth manual, and the standalone reference pages.",
    "geomatics": "Geodesy, projections, and adjustment in Mojo: the interactive tutorial, the single source of truth manual, and the standalone reference pages.",
    "operations_research": "Linear programming, networks, and queues in Mojo: the interactive tutorial, the single source of truth manual, and the standalone reference pages.",
}

SST_BLURB = {
    "data_science": "38 chapters covering the language, its ownership model, and tensor work.",
    "finance": "38 chapters covering the language, its ownership model, and numeric work.",
    "geomatics": "38 chapters covering the language, its ownership model, and numeric work.",
    "operations_research": "38 chapters covering the language, its ownership model, and numeric work.",
}


def sst_href(from_dir: Path, book_root: Path) -> str:
    rel = (book_root / SST_DIR / "index.html").relative_to(from_dir)
    return urllib.parse.quote(rel.as_posix())


def build_hub(book: str) -> str:
    root = ROOT / book
    title = TITLES[book]
    sst = urllib.parse.quote(f"{SST_DIR}/index.html")
    pages = "\n".join(
        f'        <li><a href="mixed_shelf/{urllib.parse.quote(p)}">'
        f"{html.escape(p[:-5].replace('_', ' '))}</a></li>"
        for p in DOMAIN_PAGES[book]
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} Mojo</title>
<meta name="description" content="{html.escape(LEDE[book])}">
<style>{CSS}</style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1>{title} Mojo</h1>
      <p class="lede">{html.escape(LEDE[book])}</p>
    </header>

    <div class="cards">
      <div class="card">
        <h2>Interactive tutorial</h2>
        <p>Hands-on modules with live widgets, a lab, and a quiz. Works offline.</p>
        <a class="big" href="{book}_mojo/index.html">Open the app</a>
      </div>
      <div class="card">
        <h2>Single source of truth</h2>
        <p>{html.escape(SST_BLURB[book])}</p>
        <a class="big" href="{sst}">Read the manual</a>
      </div>
      <div class="card">
        <h2>Standalone shelf</h2>
        <p>Reference pages you can open directly, no app required.</p>
        <a class="big" href="mixed_shelf/index.html">Browse the shelf</a>
      </div>
    </div>

    <h2 class="sec">Reference pages</h2>
    <ul>
{pages}
    </ul>
    <p><a href="mixed_shelf/index.html">See all 65 standalone pages in the shelf</a></p>

    <footer>
      <p>This book is self-contained. Nothing here links to another book.</p>
    </footer>
  </div>
</body>
</html>
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
        for rel, content in (
            (Path("index.html"), build_hub(book)),
            (Path("mixed_shelf") / "index.html", build_shelf(book)),
        ):
            p = ROOT / book / rel
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
        print("Book hubs and shelf catalogs match their generator.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
