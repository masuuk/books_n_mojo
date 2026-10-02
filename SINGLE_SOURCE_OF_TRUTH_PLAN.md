# The Mojo v1 Single Source of Truth — Rebuild Plan

> **Deliverable.** Turn 38 raw, unopenable `.mhtml` browser archives into a *beautiful*, offline,
> self-contained HTML edition of the Mojo v1 language manual, and ship it identically into all four
> books (Data Science, Finance, Geomatics, Operations Research).

---

## 1. Current state (audited, not assumed)

| Fact | Value |
|---|---|
| Archives | 38 × `.mhtml`, one per manual page, per book folder |
| Total size | ~33 MB per book folder, ~132 MB across four (four identical copies) |
| Origin | `mojolang.org/docs/manual/**` + `docs/tools/**` + `docs/reference/cheat-sheets/**`, Docusaurus 3.10, saved via Chrome "Save page as" |
| Encoding | `multipart/related`, main part `text/html`, `quoted-printable`, ~280 KB decoded |
| Usable content | the single region `<div class="theme-doc-markdown markdown">` … `<footer>` — 3.7 KB … 303 KB per page |
| Everything else | dead weight: McAfee WebAdvisor extension SVG/CSS, cookie-consent iframe, GTM noscript, `cid:` CSS, announcement bar, announcement ribbons |
| Content inventory | 875 code blocks · 13 languages · 1 216 styled syntax tokens · 78 tables · 46 callouts · 12 disclosures · 15 `<img>` · 0 KaTeX · 0 tabs · 0 mermaid |
| Code token classes | `plain, punctuation, keyword, operator, number, comment, string, function, special-vars, builtin, class-name, boolean, property` |
| Languages in code | `mojo (629), output (97), python (25), sh (18), text (14), bash (12), shell (3), ini (3), json (1), yaml (1), toml (1)` |
| Embedded images | only 4 PNGs; the other 11 are remote URLs |
| Cross-page links | absolute `https://mojolang.org/...` — all dead once offline |
| Existing asset precedent | `*/vendor/katex/` (already vendored, offline-first) |
| Git | `the_books/` is untracked; commits only on explicit request |

### Why it must be rewritten
1. **Unopenable in spirit** — a reader cannot navigate, search, or read these files comfortably.
2. **No design** — Docusaurus + Mantine + browser-extension CSS; nothing matches the books' craft.
3. **Dead offline** — remote images, remote CSS, absolute links, no KaTeX/math (not needed: 0 matches).
4. **Four copies of one thing** — 132 MB of quadruplicated source of truth.

---

## 2. Design principles

1. **One source, four copies of the *rendered* book.** The `.mhtml` files are *raw material*, not the
   single source of truth. The pipeline is the source of truth; the `.mhtml` files are archived once
   in `raw/`, and the beautiful output is regenerated from them.
2. **Offline-first.** Zero network dependencies. System font stacks only (no Google Fonts — the
   existing pages *link* Google Fonts but the archives carry no usable subset).
3. **Content fidelity above decoration.** Every sentence, code block, table and callout survives.
   Only chrome is removed.
4. **Syntax highlighting is preserved, then re-themed.** Prism already tokenised the code; we keep the
   token classes and drop the inline `style="color: rgb(...)"` so the theme owns the palette.
5. **A real book's furniture** — cover, part structure, per-page table of contents, prev/next,
   scrollspy, search, keyboard navigation, light/dark, reading progress.
6. **Its own identity.** The Mojo manual is the common ancestor of four differently-palette'd books.
   It gets Mojo's own ember signature, not a copy of Data Science's.
7. **Regenerable.** `uv run tools/build_mojo_manual.py` reproduces everything from `raw/`.

---

## 3. Target information architecture

38 pages in seven parts, ordered pedagogically (the archives are alphabetical on disk; order is
authored, not inherited).

**Part I — Orientation**
1 Mojo quickstart · 2 Get started with Mojo · 3 Mojo language basics · 4 Mojo tips for Python devs

**Part II — The Language**
5 Variables · 6 Types · 7 Operators · 8 Functions · 9 Lambda expressions · 10 Closures ·
11 Control flow · 12 Errors, error handling, and context managers

**Part III — Abstraction & Values**
13 Mojo structs · 14 Add operator support to custom types · 15 Self-referential structs · 16 Traits ·
17 Parameterized declarations · 18 Value semantics · 19 Intro to value ownership · 20 Ownership ·
21 Lifetimes, origins, and references

**Part IV — Memory & Interop**
22 Intro to pointers · 23 Using pointers · 24 Python interoperability · 25 Python types ·
26 Calling Python from Mojo · 27 Calling Mojo from Python ·
28 Using Mojo's C foreign function interface to call C libraries

**Part V — Compile-Time Programming**
29 Intro to metaprogramming · 30 Compile-time evaluation · 31 Comptime constraints and assertions ·
32 Materializing compile-time values at run time · 33 Reflection

**Part VI — Projects & Tooling**
34 Modules and packages · 35 Packaging · 36 Jupyter notebooks · 37 Mojo AI skills

**Part VII — Reference**
38 Mojo types & literals cheat sheet

### Output tree (per book)

```
index.html                        # book hub: the three parts in one page
data_science_mojo/                # (named per book) the interactive app
mixed_shelf/                      # 65 standalone reference pages, interiors repaired
├── index.html                    #   generated catalog of all 65
single_source_of_truth mojo/
├── index.html                    # cover + part map + full table of contents
├── assets/
│   ├── mojo.css                  # the whole design system (light + dark)
│   ├── mojo.js                   # theme, scrollspy, copy, search, keyboard nav
│   └── search-index.json          # title/part/headings/plain-text per page
├── pages/                        # 38 rendered pages, NN_slug.html
└── raw/                          # the 38 .mhtml archives, untouched provenance
```

`index.html` and `mixed_shelf/index.html` are generated by
`tools/build_book_nav.py`; the app's brand link already pointed at the book
root, so the hub is what that link was always meant to reach. Both the app and
the shelf catalog link to the manual, and the hub links to all three parts, so
a reader who lands in any one part can reach the other two.

The 65 shelf pages were written against a site layout that no longer exists —
`../mojo_v1/…`, `../applications/…`, `../../praxis/…` — and all four books
carried byte-identical copies naming a single book in the chrome. Their
interiors are repaired by two deterministic tools:

- `tools/fix_shelf_links.py` is book-aware. The manual and app links are
  retargeted at the book that owns the page, a book-root link becomes the shelf
  catalog, and a cross-book link becomes the local shelf copy of the same
  title, since all 65 pages exist in every book. Text and structure are never
  rewritten; only link targets and the labels of links that named a book.
- `tools/fix_shelf_styles.py` repairs the presentation layer. One page per book
  had lost the opening `<style>` tag, so its 22 KB stylesheet sat in `<head>` as
  bare text and was never applied — every `class` in the markup was inert. The
  CSS is re-wrapped exactly as written, and a heading emoji that an encoding
  round-trip turned into two literal `?` characters is restored from the glyph
  its sibling headings agree on.

Both are idempotent and both support `--dry`.

---

## 4. The visual system

Ember-on-graphite, Mojo's own brand temperature, harmonising with Data Science's warm dark book
while standing alone.

- **Type** — display/serif: `ui-serif, Georgia, 'Iowan Old Style', 'Times New Roman', serif`;
  UI/sans: `system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif`;
  code: `ui-monospace, 'Cascadia Code', 'JetBrains Mono', Consolas, monospace`.
- **Ember scale** — `--ember-1:#ff7a1a`, `--ember-2:#ffb238`, `--ember-3:#c2360c`, plus
  signature accents used only for structure (rivers, part numerals).
- **Light theme** is a first-class citizen (`#fbf7f0` paper, `#241a12` ink), not an afterthought.
- **Layout** — 3 zones: sticky header (brand · part · search · theme), centred measure
  (`--measure: 74ch`), sticky right-hand *On this page* rail with scrollspy.
- **Callouts** — 5 flavours (note, tip, caution, danger, experiment) each with a hairline accent,
  a glyph, and a label; not yellow boxes.
- **Code** — every block gets a language chip, a copy button that confirms, and a themed
  Mojo/Python/bash/output palette; `output` blocks are visually demoted as transcripts.
- **Tables** — sticky header row, zebra hairlines, horizontal scroll on narrow screens.
- **Figures** — images get a framed `<figure>` with the original `alt` rendered as a real caption
  (the diagrams ship with descriptive alt text worth keeping); light/dark pairs resolved via `<picture>`.
- **Motion** — 150 ms ease transitions, `prefers-reduced-motion` respected, no decorative animation
  competing with reading.

---

## 5. Pipeline

`tools/build_mojo_manual.py` (Python 3.12+, `uv`-managed, deps `beautifulsoup4` + `lxml`).

```
raw/*.mhtml
   │  1. parse MIME (email.message_from_bytes) → first text/html part
   │  2. quoted-printable decode → UTF-8
   ▼
isolate  <div class="theme-doc-markdown markdown"> … matching <footer>  (depth-counted, not regex)
   │
   │  3. clean (BeautifulSoup/lxml tree surgery)
   ▼
document model: {slug, part, order, title, dek, body, headings, prev, next}
   │
   │  4. render page shell + cover + search index
   ▼
pages/*.html · index.html · assets/* · then mirror to the four books
```

### 5.1 Extraction rules

| # | Rule |
|---|---|
| E1 | Walk the MIME tree; take the `text/html` part whose `Content-Location` is the page URL. |
| E2 | Locate the markdown root by class match, then walk the tree depth-first to its true closing tag. |
| E3 | Read the real `<h1>` and the page's `Subject`/URL for title, part and canonical slug. |
| E4 | Harvest `<pre>` payloads as raw text for the copy button, independent of the DOM. |
| E5 | Harvest embedded PNG parts to `assets/` keyed by content hash; resolve remote URLs to them. |

### 5.2 Cleaning rules (the substance of "beautiful")

| # | Rule |
|---|---|
| C1 | Delete every `style` attribute site-wide; delete Docusaurus/Mantine hashed classes (`*_XXXX`). |
| C2 | Delete `buttonGroup_*` copy buttons, `hash-link` permalink glyphs, the `llms-directive` banner. |
| C3 | Normalise inline code `<pre><code><div class="token-line">` → `<pre class="code"><code>` with `data-lang`, one `data-line` div per line, tokens reduced to `<span class="tk tk-keyword">…`. |
| C4 | Rebuild callouts: `data-admonition-type` + Mantine `Alert-*` → `<aside class="callout callout--note">` with glyph + label + body. |
| C5 | Keep `<details>` disclosures as first-class collapsible panels. |
| C6 | Tables → `<div class="table-wrap"><table>`; drop Docusaurus wrapper classes; keep `<code>` cells. |
| C7 | Images → `<figure class="fig"><img loading="lazy">` + `<figcaption>` from `alt`; `…#light`/`…#dark` pairs collapse into one `<picture>`-style element. |
| C8 | Links: `mojolang.org/docs/manual/...` → local `pages/NN_slug.html#anchor`; anchors preserved as page-local `#id`; remaining external links get `rel="noopener"` + an external glyph. |
| C9 | Headings get stable `id`s from the original anchors; `<h2>` becomes a numbered section break. |
| C10 | Guarantee well-formed output: balanced tags, escaped entities, no empty paragraphs. |
| C11 | Emit a per-page `dek` (first paragraph) for the cover and search index. |

### 5.3 Rendering rules

| # | Rule |
|---|---|
| R1 | Every page: header, article (`<main>`), on-this-page rail, prev/next, footer with the canonical source URL. |
| R2 | `index.html`: hero, part map (7 parts, counts, entry links), full numbered contents, provenance note. |
| R3 | `assets/mojo.css`: tokens, reset, layout, typography scale, prose, code, callouts, tables, figures, rail, cover, print styles, reduced-motion. |
| R4 | `assets/mojo.js`: theme persistence + `prefers-color-scheme`, TOC scrollspy, copy-to-clipboard, in-page search over `search-index.json`, `/` and `←`/`→` keyboard nav, progress bar. No dependencies. |
| R5 | `assets/search-index.json`: `[{file,title,part,headings[],text}]` — plain text only, ~200 KB total. |
| R6 | Accessibility: skip link, landmarks, `:focus-visible` rings, `aria-expanded` on disclosures, sufficient contrast in both themes, `lang="en"`. |
| R7 | Print stylesheet: drop chrome, keep code blocks intact, page-break control. |

---

## 6. Fan-out and provenance — four independent books

**Each of the four books is independent.** The manual is therefore not a shared
subsystem: there is no common asset directory, no symlink, no cross-book link, no
`../../` reach into a sibling book. Each book's `single_source_of_truth mojo/` is a
complete, self-sufficient tree that would still work if the other three were deleted.

1. Build from one book (`data_science/`) — the build is deterministic, so the result
   is identical everywhere.
2. Verify against G1–G7.
3. For each of `finance/`, `geomatics/`, `operations_research/`: write its own copy of
   the tree — real files, no references outside its own folder — and move that book's
   own 38 `.mhtml` archives into its own `raw/` (kept byte-identical; nothing deleted).
4. The four `raw/` directories are 38 identical archives each, and that is accepted:
   each book owns its own provenance rather than borrowing another book's.

Independence is a *build-time* property, not a runtime one. Nothing in a book's output
may point outside that book; G4 and G5 exist to prove it.

The same rule governs the parts outside the manual. The book hub, the app, the shelf
catalog and all 65 shelf pages are each repaired to resolve only inside their own book;
`verify_navigation.py` reads all four books × 68 pages and fails on any path that would
leave the book or land on a file that is not there. Nothing reaches into a sibling book,
so deleting three of the four books leaves the fourth complete.

---

## 7. Quality gates

| Gate | Criterion |
|---|---|
| G1 Extraction | 38/38 pages render; every page's `<h1>` present; text length within 1% of the raw region. |
| G2 Fidelity | Every structure the archives hold survives the build, counted on both sides and matched one for one: 805 code blocks, 13 tables, 67 callouts, 3 disclosures, 8 diagrams, 16 images. `verify_structure.py` prints the two columns side by side. |
| G3 Purity | Zero occurrences of `cid:`, `chrome-extension`, `googletagmanager`, `cookiebot`, `mantine-`, `docusaurus`, `mcafee` in output. |
| G4 Links | Zero dead internal links; every `mojolang.org/docs/**` link resolved locally or deliberately external. |
| G5 Offline | Zero external `src`/`href` subresources (except declared source links). |
| G6 Aesthetics | No inline `style=`; hashed classes gone; both themes legible; every class the pages use has a rule and every rule is used; every syntax token the cleaner emits has a colour. |
| G7 Independence | No output path in any book points outside that book's own folder; the four trees are byte-identical. |
| G8 Anchors | Every rendered `id` is unique per page; a table keeps its caption only if the archive gave it one. |
| G9 Navigation | Zero dead local `href` and zero bad fragments across all 68 pages of a book (app, hub, shelf catalog, 65 shelf pages); each book reaches its own `mixed_shelf` and its own manual; no href crosses a book boundary; the catalog lists all 65 shelf pages exactly once; no link in a shelf page still carries a foreign book's name. Every page also carries a stylesheet the browser will actually apply: `<style>` tags balance, and a page with no inline CSS has no markup whose classes are inert. |

G9 covers the parts of a book that live outside `single_source_of_truth mojo/`.
G4 and G7 constrain the manual; the app and the shelf are separate artefacts
with their own entry points, so they get their own gate.
`verify_navigation.py` runs it, `build_book_nav.py --check` proves the two
generated files are not hand-edited, and the two `fix_shelf_*.py` scripts run
first in idempotence mode so the gate is never satisfied by a script's own
in-flight edit.

The presentation half of G9 exists because a page can satisfy every link check
and still be unreadable. A dead stylesheet does exactly that: the links resolve,
the navigation is perfect, and the page renders unstyled with every `class` in
the markup inert. The check reports the two ways that happens — a `<style>` that
never opens, and a page with no stylesheet at all — and a class with no rule on
a page that does have CSS is left to the author, since that only ever renders as
the default.

The shelf originally carried 203 missing-file links per book across 22 distinct
targets. A naive count reads 516 because it also treats valid `#fragment`
references as missing files; the fragment-aware count is the honest one. A
missing destination is repaired rather than removed, with two exceptions: a
`praxis` link was the whole reason a menu row or a card existed, so those
elements are deleted instead of left stranded, and prose that merely named
Praxis keeps its words with the link stripped. Two pages referenced a
`../styles.css` that does not exist in the shelf; the shared rule set is inlined
instead of leaving a dead subresource.

Gate G8 exists because the archives label their tables `Table 1.`, `Table 2.`, and
so on, and those labels are the only way a cross-page link can name a table.
Inventing a caption for an unlabelled table would be fabricating a fact; dropping a
real label would break a link the docs rely on. So the render keeps the label when
there is one and stays silent when there is not: 6 of the 13 tables arrive
labelled. `verify_ids.py` holds the render to exactly that.

---

## 8. Milestones

| # | Milestone | State |
|---|---|---|
| M0 | Audit + this plan | done |
| M1 | `tools/` scaffold (uv, pyproject, deps) | done |
| M2 | Extractor: MIME → isolated article region → document model | done |
| M3 | Cleaner: chrome removal, code/callout/table/figure/link rewriting | done |
| M4 | `mojo.css` design system | done |
| M5 | `mojo.js` behaviour + search index | done |
| M6 | Reading order manifest (7 parts, 38 pages) + cover | done |
| M7 | Build, verify against G1–G7, mirror to four books, archive `raw/` | done |
| M8 | G8 anchors, CSS-coverage and token-colour gates | done |
| M9 | G9 cross-navigation: book hub, shelf catalog, app ↔ shelf ↔ manual | done |
| M10 | Shelf link repair: `fix_shelf_links.py`, book-aware and idempotent; 881 edits over 247 files | done |
| M11 | Shelf presentation repair: `fix_shelf_styles.py`; restored a 22 KB orphaned stylesheet and one mangled glyph in each book | done |

## 9. Running it

```
cd tools
uv sync                                            # beautifulsoup4 + lxml
uv run --no-project python build_mojo_manual.py     # build all four books
uv run --no-project python build_mojo_manual.py --check   # manual gates only
uv run --no-project python build_book_nav.py        # write hub + shelf catalog
uv run --no-project python build_book_nav.py --check
uv run --no-project python fix_shelf_links.py        # repair shelf link targets
uv run --no-project python fix_shelf_links.py --dry  # report without writing
uv run --no-project python fix_shelf_styles.py       # repair shelf stylesheets
uv run --no-project python fix_shelf_styles.py --dry
uv run --no-project python verify_all.py            # G1-G9, every book
```

Both `fix_shelf_*.py` scripts are idempotent and safe to re-run: with the shelf
already repaired each reports `Nothing to do`. Both are deterministic, so a book
can be repaired on its own without touching the other three.

`verify_all.py` runs each verifier against each of the four trees, then the
build check that compares the trees to one another. The verifiers take the
manual root as an argument, so a single book can be checked on its own:

```
uv run --no-project python verify_structure.py "../data_science/single_source_of_truth mojo"
```

## 10. Out of scope

- Editing Mojo's prose (fidelity is the contract).
- The API reference (`docs/api/**`) — not present in the archives.
- Rewriting the prose of the 65 `mixed_shelf` pages. Their link targets are
  repaired and they are navigable, but their *content* is archival and was left
  as found — only `href` values, link labels that named a book, and two dead
  stylesheet references were touched.
- A Mojo WASM runner / live execution (the playground is widget-based; out of scope here).