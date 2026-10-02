"""Generate each book's mixed_shelf catalog.

The root index pages are custom-authored landing pages. Their local navigation
is checked by verify_navigation.py; this script owns only the generated shelf
catalogs, so running it cannot replace the custom designs.

One design serves all four books. It is a printed-book cover: a serif hero, a
run of counts, three doors out of the shelf, then every page grouped into its
series. Light and dark are equal citizens and nothing is fetched from the
network, so a catalog opened from a thumb drive looks the same as one served.

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
/* ==========================================================================
   {shelf} shelf — styled to match the Mojo manual cover.
   A single stylesheet. Light and dark are equal citizens; nothing is loaded
   from the network; nothing depends on a webfont arriving.
   ========================================================================== */

/* ---------------------------------------------------------------- tokens -- */

:root {
  color-scheme: dark;

  --bg-0: #0c0906;
  --bg-1: #120c08;
  --bg-2: #1a1109;
  --bg-3: #241809;
  --paper: #fdf8ea;
  --paper-2: #e8dcc0;
  --paper-3: #8d7c66;
  --muted: #b6a486;
  --faint: #7d6d58;

  --ember-1: #ff7a1a;
  --ember-2: #ffb238;
  --ember-3: #c2360c;

  --line: rgba(244, 234, 215, 0.14);
  --line-2: rgba(244, 234, 215, 0.26);
  --line-3: rgba(244, 234, 215, 0.42);

  --good: #9fe6a8;
  --info: #8fc7ff;
  --warn: #ffc46b;
  --bad: #ff9a8b;
  --flask: #d7b3ff;

  --measure: 70ch;
  --rail: 15.5rem;
  --head-h: 3.5rem;
  --radius: 0.7rem;
  --radius-sm: 0.4rem;

  --serif: ui-serif, "Iowan Old Style", "Palatino Linotype", Palatino, Georgia,
    "Times New Roman", serif;
  --sans: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue",
    Arial, sans-serif;
  --mono: ui-monospace, "Cascadia Code", "JetBrains Mono", "SF Mono", Menlo,
    Consolas, "Liberation Mono", monospace;

  --shadow-1: 0 1px 2px rgba(0, 0, 0, 0.4), 0 8px 24px rgba(0, 0, 0, 0.28);
  --shadow-2: 0 2px 6px rgba(0, 0, 0, 0.45), 0 18px 50px rgba(0, 0, 0, 0.35);
  --ease: cubic-bezier(0.2, 0.7, 0.3, 1);
}

:root[data-theme="light"] {
  color-scheme: light;

  --bg-0: #fbf7f0;
  --bg-1: #ffffff;
  --bg-2: #f5eee2;
  --bg-3: #ece1cf;
  --paper: #241a12;
  --paper-2: #4a3a2c;
  --muted: #6d5b48;
  --faint: #93826e;

  --ember-1: #d95b00;
  --ember-2: #a97a00;
  --ember-3: #9c2c06;

  --line: rgba(60, 42, 26, 0.14);
  --line-2: rgba(60, 42, 26, 0.24);
  --line-3: rgba(60, 42, 26, 0.4);

  --good: #1f7a34;
  --info: #0b64a8;
  --warn: #8a5a00;
  --bad: #a83218;
  --flask: #6b3fa0;

  --shadow-1: 0 1px 2px rgba(80, 56, 30, 0.08), 0 8px 20px rgba(80, 56, 30, 0.07);
  --shadow-2: 0 2px 6px rgba(80, 56, 30, 0.1), 0 18px 44px rgba(80, 56, 30, 0.12);
}

/* ----------------------------------------------------------------- reset -- */

*,
*::before,
*::after {
  box-sizing: border-box;
}

html {
  -webkit-text-size-adjust: 100%;
  scroll-behavior: smooth;
  scroll-padding-top: calc(var(--head-h) + 1.5rem);
}

body {
  margin: 0;
  background: var(--bg-0);
  color: var(--paper);
  font-family: var(--serif);
  font-size: 19px;
  line-height: 1.72;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
  overflow-wrap: break-word;
}

img,
picture,
svg {
  max-width: 100%;
  height: auto;
  display: block;
}

::selection {
  background: var(--ember-1);
  color: var(--bg-0);
}

a {
  color: var(--ember-2);
  text-decoration-color: color-mix(in srgb, var(--ember-2) 45%, transparent);
  text-underline-offset: 0.18em;
  transition: color 0.15s var(--ease);
}

a:hover {
  color: var(--ember-1);
}

/* A link that leaves this book. Said plainly, so no one expects to stay. */
.ext::after {
  content: "\\2197";
  margin-left: 0.15em;
  font-size: 0.78em;
  vertical-align: 0.2em;
  color: var(--faint);
}

:focus-visible {
  outline: 2px solid var(--ember-1);
  outline-offset: 3px;
  border-radius: 2px;
}

.skip {
  position: absolute;
  left: -9999px;
  top: 0;
  z-index: 200;
  padding: 0.7rem 1.1rem;
  background: var(--ember-1);
  color: #1a0d04;
  font-family: var(--sans);
  font-size: 0.85rem;
  font-weight: 600;
  border-radius: 0 0 var(--radius-sm) 0;
}

.skip:focus {
  left: 0;
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

/* ---------------------------------------------------------------- header -- */

.head {
  position: sticky;
  top: 0;
  z-index: 60;
  display: flex;
  align-items: center;
  gap: 1rem;
  height: var(--head-h);
  padding: 0 clamp(1rem, 4vw, 2.4rem);
  background: color-mix(in srgb, var(--bg-0) 84%, transparent);
  backdrop-filter: blur(14px) saturate(1.4);
  border-bottom: 1px solid var(--line);
}

.brand {
  display: inline-flex;
  align-items: baseline;
  gap: 0.55rem;
  font-family: var(--sans);
  font-weight: 700;
  font-size: 0.95rem;
  letter-spacing: -0.01em;
  color: var(--paper);
  text-decoration: none;
  white-space: nowrap;
}

.brand__mark {
  color: var(--ember-1);
  font-weight: 900;
}

.brand__sub {
  font-weight: 500;
  font-size: 0.78rem;
  color: var(--muted);
  letter-spacing: 0.02em;
}

.head__spacer {
  flex: 1 1 auto;
}

.head__part {
  font-family: var(--sans);
  font-size: 0.7rem;
  letter-spacing: 0.13em;
  text-transform: uppercase;
  color: var(--faint);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 30ch;
}

.head__part b {
  color: var(--ember-2);
  font-weight: 700;
}

.iconbtn {
  display: inline-grid;
  place-items: center;
  width: 2.1rem;
  height: 2.1rem;
  flex: none;
  border: 1px solid var(--line-2);
  border-radius: 50%;
  background: transparent;
  color: var(--paper-2);
  font-family: var(--sans);
  font-size: 0.85rem;
  cursor: pointer;
  transition: border-color 0.15s var(--ease), color 0.15s var(--ease),
    background 0.15s var(--ease);
}

.iconbtn:hover {
  color: var(--ember-2);
  border-color: var(--ember-1);
  background: color-mix(in srgb, var(--ember-1) 10%, transparent);
}

/* ----------------------------------------------------------------- shell -- */

.shell {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  max-width: 66rem;
  min-height: calc(100vh - var(--head-h) - 4rem);
  margin: 0 auto;
  padding: 0 clamp(1rem, 4vw, 2.4rem) 6rem;
  align-items: start;
}

/* ------------------------------------------------------------------ cover -- */

.hero {
  position: relative;
  padding: clamp(3.5rem, 9vw, 7rem) clamp(1rem, 4vw, 2.4rem) clamp(2rem, 5vw, 3.5rem);
  border-bottom: 1px solid var(--line);
  overflow: hidden;
}

.hero::before {
  content: "";
  position: absolute;
  inset: -40% -10% auto -10%;
  height: 130%;
  background:
    radial-gradient(ellipse 45% 40% at 78% 12%, color-mix(in srgb, var(--ember-1) 30%, transparent), transparent 62%),
    radial-gradient(ellipse 40% 45% at 8% 88%, color-mix(in srgb, var(--ember-3) 26%, transparent), transparent 66%);
  pointer-events: none;
  z-index: 0;
}

.hero > * {
  position: relative;
  z-index: 1;
  max-width: 82rem;
  margin-inline: auto;
}

.hero__eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  font-family: var(--sans);
  font-size: 0.74rem;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--ember-2);
  margin-bottom: 1.2rem;
}

.hero__eyebrow::before {
  content: "";
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--ember-1);
  box-shadow: 0 0 10px var(--ember-1);
}

.hero h1 {
  margin: 0;
  font-size: clamp(2.7rem, 8vw, 5.6rem);
  line-height: 0.98;
  letter-spacing: -0.03em;
  font-weight: 800;
  max-width: 16ch;
}

.hero h1 em {
  font-style: normal;
  color: var(--ember-1);
}

.hero__lede {
  margin: 1.6rem 0 0;
  max-width: 58ch;
  font-size: clamp(1.05rem, 2.2vw, 1.32rem);
  line-height: 1.6;
  font-style: italic;
  color: var(--paper-2);
}

.stats {
  display: flex;
  flex-wrap: wrap;
  gap: 2.4rem;
  margin: 2.6rem 0 0;
  padding: 1.4rem 0 0;
  border-top: 1px solid var(--line);
}

.stat b {
  display: block;
  font-family: var(--sans);
  font-size: 1.9rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: var(--ember-2);
  line-height: 1;
}

.stat span {
  display: block;
  margin-top: 0.35rem;
  font-family: var(--sans);
  font-size: 0.72rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--faint);
}

.cover {
  max-width: 82rem;
  margin: 0 auto;
  padding: clamp(2.5rem, 6vw, 4.5rem) 0 6rem;
}

.cover h2 {
  font-size: clamp(1.7rem, 4vw, 2.4rem);
  line-height: 1.1;
  margin: 0 0 0.5rem;
  letter-spacing: -0.02em;
}

.cover__lede {
  margin: 0 0 2.6rem;
  font-family: var(--sans);
  font-size: 0.92rem;
  color: var(--muted);
  max-width: 62ch;
}

.h--2 {
  position: relative;
  font-weight: 700;
  letter-spacing: -0.012em;
  scroll-margin-top: calc(var(--head-h) + 1.5rem);
  font-size: clamp(1.55rem, 3.4vw, 2rem);
  line-height: 1.15;
  margin: 3.4rem 0 1.1rem;
  padding-top: 1.6rem;
  border-top: 1px solid var(--line);
}

.cover > .h--2:first-child {
  margin-top: 0;
  padding-top: 0;
  border-top: 0;
}

/* ----------------------------------------------------------------- gates -- */

.gates {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr));
  gap: 1rem;
  margin: 0 0 1rem;
}

.gate {
  display: block;
  padding: 1.2rem 1.3rem 1.3rem;
  border: 1px solid var(--line-2);
  border-radius: var(--radius);
  background: var(--bg-1);
  text-decoration: none;
  color: inherit;
  transition: border-color 0.15s var(--ease), background 0.15s var(--ease),
    transform 0.15s var(--ease);
}

.gate:hover {
  border-color: var(--ember-1);
  background: var(--bg-2);
  transform: translateY(-2px);
}

.gate__dir {
  font-family: var(--sans);
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--faint);
  transition: color 0.15s var(--ease);
}

.gate:hover .gate__dir {
  color: var(--ember-2);
}

.gate__title {
  display: block;
  margin-top: 0.45rem;
  font-size: 1.2rem;
  font-weight: 700;
  line-height: 1.25;
  color: var(--paper);
}

.gate__blurb {
  display: block;
  margin-top: 0.35rem;
  font-family: var(--sans);
  font-size: 0.83rem;
  color: var(--muted);
  line-height: 1.45;
}

/* ----------------------------------------------------------------- parts -- */

.part {
  margin: 0 0 2.8rem;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--bg-1);
  overflow: hidden;
}

.part[hidden] {
  display: none;
}

.part__head {
  display: flex;
  align-items: baseline;
  gap: 1rem;
  padding: 1.15rem 1.4rem;
  border-bottom: 1px solid var(--line);
  background: linear-gradient(90deg, color-mix(in srgb, var(--ember-1) 8%, transparent), transparent 60%);
}

.part__num {
  font-family: var(--sans);
  font-size: 0.74rem;
  font-weight: 800;
  letter-spacing: 0.16em;
  color: var(--ember-1);
  border: 1px solid color-mix(in srgb, var(--ember-1) 45%, transparent);
  border-radius: 0.3rem;
  padding: 0.12rem 0.45rem;
  flex: none;
}

.part__title {
  margin: 0;
  font-size: 1.35rem;
  letter-spacing: -0.01em;
}

.part__blurb {
  margin: 0.15rem 0 0;
  font-family: var(--sans);
  font-size: 0.82rem;
  color: var(--muted);
}

.part__count {
  margin-left: auto;
  font-family: var(--sans);
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  color: var(--faint);
  flex: none;
}

/* ------------------------------------------------------------------- toc -- */

.toc {
  list-style: none;
  margin: 0;
  padding: 0;
}

.toc__item {
  border-bottom: 1px solid var(--line);
}

.toc__item:last-child {
  border-bottom: 0;
}

.toc__item[hidden] {
  display: none;
}

.toc__link {
  display: grid;
  grid-template-columns: 3.4rem minmax(0, 1fr) auto;
  align-items: baseline;
  gap: 1rem;
  padding: 0.85rem 1.4rem;
  text-decoration: none;
  color: inherit;
  transition: background 0.15s var(--ease);
}

.toc__link:hover {
  background: color-mix(in srgb, var(--ember-1) 8%, transparent);
}

.toc__num {
  font-family: var(--mono);
  font-size: 0.8rem;
  color: var(--faint);
}

.toc__title {
  font-size: 1.06rem;
  font-weight: 650;
  color: var(--paper);
  line-height: 1.3;
}

.toc__blurb {
  display: block;
  margin-top: 0.2rem;
  font-family: var(--sans);
  font-size: 0.8rem;
  font-weight: 400;
  color: var(--muted);
  line-height: 1.45;
}

.toc__go {
  font-family: var(--mono);
  color: var(--ember-1);
  opacity: 0;
  transition: opacity 0.15s var(--ease), transform 0.15s var(--ease);
  transform: translateX(-4px);
}

.toc__link:hover .toc__go {
  opacity: 1;
  transform: translateX(0);
}

mark {
  background: color-mix(in srgb, var(--ember-2) 30%, transparent);
  color: var(--ember-2);
  border-radius: 2px;
}

.empty {
  display: none;
  padding: 3rem 1.2rem;
  text-align: center;
  border: 1px dashed var(--line-2);
  border-radius: var(--radius);
  background: var(--bg-1);
  font-family: var(--sans);
  font-size: 0.92rem;
  color: var(--muted);
}

.empty.show {
  display: block;
}

/* --------------------------------------------------------------- footer --- */

.foot {
  border-top: 1px solid var(--line);
  padding: 2.2rem clamp(1rem, 4vw, 2.4rem) 3.5rem;
  font-family: var(--sans);
  font-size: 0.76rem;
  color: var(--faint);
}

.foot__inner {
  max-width: 82rem;
  margin: 0 auto;
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem 1.6rem;
  align-items: baseline;
  justify-content: space-between;
}

.foot b {
  color: var(--ember-2);
  font-weight: 700;
}

.foot a {
  color: var(--muted);
  text-decoration: none;
  border-bottom: 1px solid var(--line-2);
}

.foot a:hover {
  color: var(--ember-2);
}

/* ------------------------------------------------------------ responsive -- */

@media (max-width: 760px) {
  body {
    font-size: 17.5px;
  }

  .head {
    gap: 0.5rem;
  }

  .brand__sub,
  .head__part {
    display: none;
  }

  .toc__link {
    grid-template-columns: 2.6rem minmax(0, 1fr);
  }

  .toc__go {
    display: none;
  }

  .part__head {
    flex-wrap: wrap;
    gap: 0.5rem 1rem;
  }

  .part__count {
    margin-left: 0;
  }
}

/* ----------------------------------------------------------------- print -- */

@media print {
  :root {
    --bg-0: #fff;
    --bg-1: #fff;
    --bg-2: #fff;
    --paper: #000;
    --paper-2: #222;
    --muted: #444;
    --faint: #666;
    --line: #ccc;
    --line-2: #bbb;
  }

  .head,
  .progress,
  .hero::before {
    display: none !important;
  }

  .shell {
    display: block;
    max-width: none;
    padding: 0;
  }

  body {
    font-size: 11pt;
  }

  .part,
  .gate {
    break-inside: avoid;
  }

  .h--2 {
    break-after: avoid;
  }

  a {
    color: #000;
    text-decoration: underline;
  }
}

/* --------------------------------------------------------- reduced motion -- */

@media (prefers-reduced-motion: reduce) {
  html {
    scroll-behavior: auto;
  }

  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
"""

FAVICON = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
    "%3Crect width='32' height='32' rx='7' fill='%23ff7a1a'/%3E"
    "%3Cpath d='M7 22V10l5 7 5-7v12' fill='none' stroke='%230c0906' stroke-width='2.6'"
    " stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E"
)

# Titles are written out rather than derived from the filename: a shelf reads
# as a contents list, so "Karney&ndash;Kr&uuml;ger equations" beats
# "karney krueger equations". The filename is still shown beside it.
PAGE_TITLES = {
    "ds_ml_textbook_01_intro": "Introduction",
    "ds_ml_textbook_04_numerical": "Numerical computing",
    "ds_ml_textbook_08_advanced": "Advanced topics",
    "ds_textbook_12_pytorch": "PyTorch",
    "ai_agents_python_vs_mojo": "AI agents: Python vs Mojo",
    "data_science": "Data science",
    "decision_aware_ml": "Decision-aware ML",
    "ds_tools": "Data science tools",
    "fine_tuning_llms": "Fine-tuning LLMs",
    "future_value_and_annuities": "Future value and annuities",
    "geo_computations": "Geo computations",
    "gnss_surveying": "GNSS surveying",
    "karney_krueger_equations": "Karney&ndash;Kr&uuml;ger equations",
    "linear_regression": "Linear regression",
    "linear_regression_detailed": "Linear regression, in detail",
    "mlp_xor": "MLP and XOR",
    "neural_network": "Neural network",
    "nn_mojo": "Neural network in Mojo",
    "npv_amortisation": "NPV and amortisation",
    "numerical_python_to_mojo": "Numerical Python to Mojo",
    "numoj": "Numoj",
    "operations_research": "Operations research",
    "perceptrons_and_activation": "Perceptrons and activation",
    "simplex_algorithm": "Simplex algorithm",
    "the_annuity_codex": "The annuity codex",
    "time_series_analytics": "Time series analytics",
}

# The numbered series. Each ships in every book, so each names itself.
SERIES = [
    {
        "prefix": "ds_advanced_",
        "num": "PART I",
        "key": "advanced",
        "group": "adv",
        "title": "Advanced series",
        "blurb": "Mojo for experienced data scientists: from zero-copy interop to MLIR.",
    },
    {
        "prefix": "ds_ml_textbook_",
        "num": "PART II",
        "key": "ml",
        "group": "ml",
        "title": "Machine learning textbook",
        "blurb": "Mojo from first principles through to building and tuning models.",
    },
    {
        "prefix": "ds_textbook_",
        "num": "PART III",
        "key": "ds",
        "group": "ds",
        "title": "Data science textbook",
        "blurb": "The language, the type system and ownership, then tensors, pipelines and GPUs.",
    },
]

STANDALONE = {
    "num": "PART IV",
    "key": "standalone",
    "anchor": "solo",
    "group": "solo",
    "title": "Standalone pages",
    "blurb": "Single-topic references: finance, surveying, optimisation and neural networks.",
}

# The run of counts under the hero: what the shelf is, in six numbers.
STAT_LABELS = [
    ("Pages", "pages"),
    ("Series", "series"),
    ("Advanced", "advanced"),
    ("ML textbook", "ml"),
    ("DS textbook", "ds"),
    ("Standalone", "standalone"),
]


def humanise(name: str) -> str:
    """Title Case for a filename, dropping the series and chapter numbers."""
    stem = name[: -len(".html")]
    for s in SERIES:
        if stem.startswith(s["prefix"]):
            stem = stem[len(s["prefix"]):]
            break
    if "_" in stem and stem[:2].isdigit():
        stem = stem.split("_", 1)[1]
    words = stem.replace("_", " ").split()
    special = {
        "ai": "AI",
        "cd": "CD",
        "cicd": "CI/CD",
        "ci/cd": "CI/CD",
        "gpu": "GPU",
        "llms": "LLMs",
        "ml": "ML",
        "mlir": "MLIR",
        "mlp": "MLP",
        "mojo": "Mojo",
        "nn": "NN",
        "npv": "NPV",
        "xor": "XOR",
    }
    out = []
    for i, w in enumerate(words):
        low = w.lower()
        if low in special:
            out.append(special[low])
        elif i == 0 or low in {"and", "vs", "to", "in", "of", "for"}:
            out.append(w[:1].upper() + w[1:])
        else:
            out.append(low)
    return " ".join(out) or "Cover"


def page_title(name: str) -> str:
    stem = name[: -len(".html")]
    if stem in PAGE_TITLES:
        return PAGE_TITLES[stem]
    title = humanise(name)
    return html.escape(title)


def search_key(name: str, title: str) -> str:
    """Terms a reader might type, over the title and the filename."""
    spoken = html.unescape(title).lower()
    raw = name[: -len(".html")].replace("_", " ")
    return f"{spoken} {raw}"


def series_of(name: str) -> dict | None:
    for s in SERIES:
        if name.startswith(s["prefix"]):
            return s
    return None


def toc_item(name: str, series: dict, num: str) -> str:
    title = page_title(name)
    href = urllib.parse.quote(name)
    return (
        f'<li class="toc__item" data-g="{series["group"]}"'
        f' data-q="{search_key(name, title)}">'
        f'<a class="toc__link" href="{href}">'
        f'<span class="toc__num">{num}</span>'
        f"<span>"
        f'<span class="toc__title">{title}</span>'
        f'<span class="toc__blurb">{name}</span>'
        f"</span>"
        f'<span class="toc__go" aria-hidden="true">&rarr;</span>'
        f"</a></li>"
    )


def render_part(series: dict, files: list[str]) -> str:
    items = "\n".join(
        toc_item(name, series, name[len(series["prefix"]):].split("_", 1)[0])
        for name in files
    )
    return f"""
  <section class="part" id="series-{series["key"]}" aria-labelledby="t-{series["key"]}">
    <div class="part__head">
      <span class="part__num">{series["num"]}</span>
      <div><h2 class="part__title" id="t-{series["key"]}">{series["title"]}</h2><p class="part__blurb">{series["blurb"]}</p></div>
      <span class="part__count">{len(files)} pages</span>
    </div>
    <ul class="toc">
{items}
    </ul>
  </section>
"""


def render_standalone(files: list[str]) -> str:
    key = STANDALONE["anchor"]
    items = "\n".join(
        toc_item(name, STANDALONE, f"{i:02d}") for i, name in enumerate(files, 1)
    )
    return f"""
  <section class="part" id="series-{STANDALONE["key"]}" aria-labelledby="t-{key}">
    <div class="part__head">
      <span class="part__num">{STANDALONE["num"]}</span>
      <div><h2 class="part__title" id="t-{key}">{STANDALONE["title"]}</h2><p class="part__blurb">{STANDALONE["blurb"]}</p></div>
      <span class="part__count">{len(files)} pages</span>
    </div>
    <ul class="toc">
{items}
    </ul>
  </section>
"""


def build_shelf(book: str) -> str:
    root = ROOT / book / "mixed_shelf"
    title = TITLES[book]
    store = f"{book}-shelf-theme.index"
    shelf = f"{title} shelf"
    up = "../index.html"
    sst = urllib.parse.quote(f"../{SST_DIR}/index.html")
    app = f"../{book}_mojo/index.html"

    files = sorted(p.name for p in root.glob("*.html") if p.name != "index.html")
    grouped = {s["key"]: [n for n in files if series_of(n) is s] for s in SERIES}
    solo = [n for n in files if series_of(n) is None]

    parts = [render_part(s, grouped[s["key"]]) for s in SERIES]
    parts.append(render_standalone(solo))
    listing = "".join(parts)

    counts = {
        "pages": len(files),
        "series": len(SERIES) + 1,
        "advanced": len(grouped["advanced"]),
        "ml": len(grouped["ml"]),
        "ds": len(grouped["ds"]),
        "standalone": len(solo),
    }
    stats = "\n".join(
        f'    <div class="stat"><b>{counts[key]}</b><span>{label}</span></div>'
        for label, key in STAT_LABELS
    )
    tally = " &middot; ".join(
        f'{s["title"]} <b>{len(grouped[s["key"]])}</b>' for s in SERIES
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#0c0906">
<title>{shelf}</title>
<meta name="description" content="Standalone {html.escape(title)} Mojo reference pages.">
<link rel="icon" href="{FAVICON}">
<script>
/* Set the theme before first paint, so the page never flashes the wrong one. */
(function(){{
  try{{
    var saved = localStorage.getItem("{store}");
    if(!saved) saved = matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", saved);
    var m = document.querySelector('meta[name="theme-color"]');
    if(m) m.setAttribute("content", saved === "light" ? "#fbf7f0" : "#0c0906");
  }}catch(e){{}}
}})();
</script>
<style>{CSS.replace("{shelf}", title)}</style>
</head>
<body class="cover">
<a class="skip" href="#main">Skip to content</a>

<header class="head">
  <span class="brand"><span class="brand__mark">Mojo</span> {title} <span class="brand__sub">&middot; Standalone shelf</span></span>
  <span class="head__part">The whole shelf &middot; <b>{len(files)}</b> pages</span>
  <span class="head__spacer"></span>
  <button class="iconbtn" type="button" data-theme-toggle aria-label="Switch theme">&#9728;</button>
</header>

<main class="shell" id="main">
<div class="hero">
  <div class="hero__eyebrow">Single source of truth</div>
  <h1>{shelf}, <em>all in one place</em>.</h1>
  <p class="hero__lede">{len(files)} standalone reference pages. Each one is self-contained and opens without the app.</p>
  <div class="stats">
{stats}
  </div>
</div>

<div class="cover">
  <h2 class="h h--2" id="elsewhere">Elsewhere in the book</h2>
  <p class="cover__lede">Three doors out of the shelf. Everything below is self-contained and opens on its own.</p>
  <div class="gates">
    <a class="gate ext" href="{up}"><span class="gate__dir">Back to the book</span><span class="gate__title">{title} home</span><span class="gate__blurb">All three parts of this book in one place.</span></a>
    <a class="gate ext" href="{app}"><span class="gate__dir">Interactive tutorial</span><span class="gate__title">Open the app</span><span class="gate__blurb">Hands-on modules with live widgets.</span></a>
    <a class="gate ext" href="{sst}"><span class="gate__dir">Single source of truth</span><span class="gate__title">Read the manual</span><span class="gate__blurb">The full manual.</span></a>
  </div>

  <h2 class="h h--2" id="contents">All pages</h2>
  <p class="cover__lede">Four series, {words(len(files))}, in reading order. Every page carries its own contents and links back to the manual it came from.</p>
{listing}</div>
</main>

<footer class="foot"><div class="foot__inner">
  <span>{tally} &middot; Standalone pages <b>{len(solo)}</b></span>
  <span>{len(files)} standalone reference pages, self-contained and offline.</span>
</div></footer>

<script>
(function () {{
  "use strict";
  var STORE_THEME = "{store}";

  function applyTheme(theme) {{
    document.documentElement.setAttribute("data-theme", theme);
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", theme === "light" ? "#fbf7f0" : "#0c0906");
    var btn = document.querySelector("[data-theme-toggle]");
    if (btn) {{
      btn.textContent = theme === "light" ? "\\u263E" : "\\u2600";
      btn.setAttribute("aria-label", theme === "light" ? "Switch to dark theme" : "Switch to light theme");
    }}
  }}

  var saved = null;
  try {{ saved = localStorage.getItem(STORE_THEME); }} catch (e) {{ saved = null; }}
  var start = saved ||
    (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
  applyTheme(start);

  document.addEventListener("click", function (event) {{
    var btn = event.target.closest("[data-theme-toggle]");
    if (!btn) return;
    var next = document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light";
    applyTheme(next);
    try {{ localStorage.setItem(STORE_THEME, next); }} catch (e) {{ /* private mode */ }}
  }});
}})();
</script>
</body>
</html>"""


def words(n: int) -> str:
    """A count the way a contents page writes one."""
    if n < 20:
        name = [
            "zero", "one", "two", "three", "four", "five", "six", "seven",
            "eight", "nine", "ten", "eleven", "twelve", "thirteen",
            "fourteen", "fifteen", "sixteen", "seventeen", "eighteen",
            "nineteen",
        ][n]
        return f"{name} pages"
    tens = {
        20: "twenty", 30: "thirty", 40: "forty", 50: "fifty", 60: "sixty",
        70: "seventy", 80: "eighty", 90: "ninety",
    }
    if n < 100:
        high, low = divmod(n, 10)
        word = tens[high * 10]
        if low:
            word += f"-{['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine'][low]}"
        return f"{word} pages"
    return f"{n} pages"


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