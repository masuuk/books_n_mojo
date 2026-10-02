"""Structural checks that a link audit cannot make.

Confirms the shell is well formed, the page has exactly one title, the search
index and pager are coherent, and the script parses.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mojomanual.manifest import BY_PATH, ORDER, canonical_path
from mojomanual.extract import read_archive


#: The structures the fidelity gate compares, and how to spot each one on
#: either side of the build. The archive uses Docusaurus/Mantine markup; the
#: render uses ours. A table the docs wrapped in a `<figure>` is one table, not
#: a diagram, so "diagram" means a figure with an image on both sides.
SOURCE_SIGNS = {
    "code blocks": "pre",
    "tables": "table",
    "callouts": "[data-admonition-type]",
    "disclosures": "details",
}
RENDER_SIGNS = {
    "code blocks": "figure.cb",
    "tables": "table",
    "callouts": "aside.callout",
    "disclosures": "details.disc",
}
NAMES = list(SOURCE_SIGNS) + ["diagrams", "images"]


def _diagrams(soup: BeautifulSoup, figures: str) -> int:
    return sum(1 for figure in soup.select(figures) if figure.find("img") is not None)


def count_source(soup: BeautifulSoup) -> Counter:
    counts = Counter(**{name: len(soup.select(sign)) for name, sign in SOURCE_SIGNS.items()})
    counts["diagrams"] = _diagrams(soup, "figure")
    counts["images"] = len({
        (img.get("src") or "").split("#", 1)[0]
        for img in soup.find_all("img")
        if (img.get("src") or "").strip()
    })
    return counts


def count_render(soup: BeautifulSoup) -> Counter:
    counts = Counter(**{name: len(soup.select(sign)) for name, sign in RENDER_SIGNS.items()})
    counts["diagrams"] = _diagrams(soup, "figure.fig")
    # one vendored file per archive image, however many variants render it
    counts["images"] = len({
        (img.get("src") or "").split("#", 1)[0]
        for img in soup.find_all("img")
        if (img.get("src") or "").strip()
    })
    return counts


def main() -> int:
    root = Path(
        sys.argv[1]
        if len(sys.argv) > 1
        else r"C:\Users\user\Desktop\the_books\data_science\single_source_of_truth mojo"
    )
    problems: list[str] = []

    # ---- the script must parse ------------------------------------------- #
    script = root / "assets" / "mojo.js"
    runner = next(
        (name for name in ("bun", "deno", "node") if shutil.which(name)), None
    )
    if runner is None:
        print("no JS runtime found; skipping script parse")
    else:
        check = subprocess.run(
            [runner, "build", "--no-bundle", str(script), "--outfile", os.devnull]
            if runner == "deno"
            else [runner, "build", str(script), "--outfile", os.devnull],
            capture_output=True,
            text=True,
        )
        if check.returncode == 0:
            print(f"mojo.js parses ({runner})")
        else:
            problems.append(f"mojo.js: {check.stderr.strip()[:200]}")

    css = (root / "assets" / "mojo.css").read_text(encoding="utf-8")
    if css.count("{") == css.count("}"):
        print(f"mojo.css braces balance ({css.count('{')} rules)")
    else:
        problems.append("mojo.css: unbalanced braces")

    # ---- the search index must match the pages -------------------------- #
    index = json.loads((root / "assets" / "search-index.json").read_text(encoding="utf-8"))
    urls = [record["url"] for record in index]
    if len(urls) != len(ORDER):
        problems.append(f"search index has {len(urls)} records, expected {len(ORDER)}")
    if len(set(urls)) != len(urls):
        problems.append("search index has duplicate urls")
    for record in index:
        if not (root / record["url"]).exists():
            problems.append(f"search index points at missing {record['url']}")
        if not record["title"] or not record["text"]:
            problems.append(f"search record {record['url']} is empty")
    if not any(problem.startswith("search") for problem in problems):
        print(f"search index: {len(index)} records, all resolvable")

    # ---- every page ------------------------------------------------------ #
    lang_histogram = Counter()
    for position, entry in enumerate(ORDER, start=1):
        path = root / "pages" / f"{entry.slug}.html"
        if not path.exists():
            problems.append(f"missing {path.name}")
            continue
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "lxml")

        if soup.find("html") is None or soup.find("head") is None:
            problems.append(f"{entry.slug}: no html/head")
        if len(soup.find_all("h1")) != 1:
            problems.append(f"{entry.slug}: {len(soup.find_all('h1'))} h1 elements")
        if soup.find("title") is None:
            problems.append(f"{entry.slug}: no <title>")
        if soup.find("main") is None:
            problems.append(f"{entry.slug}: no <main>")
        if soup.find("a", class_="skip") is None:
            problems.append(f"{entry.slug}: no skip link")
        if soup.body.get("class") != ["page"]:
            problems.append(f"{entry.slug}: body class is {soup.body.get('class')}")

        article = soup.find("article")
        if article is None:
            problems.append(f"{entry.slug}: no article")
            continue
        if not article.get_text(strip=True):
            problems.append(f"{entry.slug}: article is empty")

        for block in article.select("figure.cb"):
            lang_histogram[block.get("data-lang")] += 1
            if block.select_one("pre code") is None:
                problems.append(f"{entry.slug}: code block with no code")
            if block.select_one(".cb__copy") is None:
                problems.append(f"{entry.slug}: code block with no copy button")

        for table in article.find_all("table"):
            if table.find("thead") is None and table.find("th") is None:
                problems.append(f"{entry.slug}: table with no header row")

        # ids must be unique within a page
        ids = re.findall(r'\sid="([^"]+)"', path.read_text(encoding="utf-8"))
        repeated = [name for name, count in Counter(ids).items() if count > 1]
        for name in repeated:
            problems.append(f"{entry.slug}: id {name!r} appears more than once")

        for figure in article.select("figure.fig"):
            images = figure.find_all("img")
            if not images:
                # a table Docusaurus wrapped in <figure>; it has its own caption
                if figure.find("table") is None:
                    problems.append(f"{entry.slug}: figure with neither image nor table")
                continue
            for image in images:
                if image.get("aria-hidden") == "true":
                    continue  # the dark twin of a diagram already described
                if not (image.get("alt") or "").strip():
                    problems.append(f"{entry.slug}: figure image with no alt text")

        # pager must be the walk order of the book
        pager = [a.get("href") for a in soup.select(".pager__link")]
        if position == 1:
            if any("prev" in str(a.get("class")) for a in soup.select(".pager__link")):
                problems.append(f"{entry.slug}: first chapter has a previous link")
        if position == len(ORDER):
            if any("next" in str(a.get("class")) for a in soup.select(".pager__link")):
                problems.append(f"{entry.slug}: last chapter has a next link")
        if not 1 <= len(pager) <= 2:
            problems.append(f"{entry.slug}: pager has {len(pager)} links")

    if not any(problem.endswith(".html") for problem in problems):
        print(f"{len(ORDER)} chapter pages structurally sound")
    print("languages in code blocks:", dict(lang_histogram))

    # ---- G2: nothing the archives held has gone missing -------------------- #
    archived = Counter()
    rendered = Counter()
    for archive_file in sorted((root / "raw").glob("*.mhtml")):
        archive = read_archive(archive_file)
        entry = BY_PATH.get(canonical_path(archive.url))
        if entry is None:
            problems.append(f"{archive_file.name}: no manifest entry")
            continue
        archived.update(count_source(BeautifulSoup(str(archive.article), "lxml")))
        page = root / "pages" / f"{entry.slug}.html"
        if page.exists():
            rendered.update(count_render(BeautifulSoup(page.read_text(encoding="utf-8"), "lxml")))

    print()
    print(f"{'structure':16} {'archive':>8} {'render':>8}")
    for name in NAMES:
        mark = "" if archived[name] == rendered[name] else "   <-- MISMATCH"
        print(f"  {name:14} {archived[name]:>8} {rendered[name]:>8}{mark}")
        if archived[name] != rendered[name]:
            problems.append(
                f"{name}: {archived[name]} in the archives, {rendered[name]} in the render"
            )

    # ---- the cover ------------------------------------------------------- #
    cover = BeautifulSoup((root / "index.html").read_text(encoding="utf-8"), "lxml")
    links = cover.select("a.toc__link")
    if len(links) != len(ORDER):
        problems.append(f"cover lists {len(links)} chapters, expected {len(ORDER)}")
    if [a["href"] for a in links] != [f"pages/{e.slug}.html" for e in ORDER]:
        problems.append("cover contents are not in reading order")
    if cover.body.get("class") != ["cover"]:
        problems.append("cover: wrong body class")
    if not any(p.startswith("cover") for p in problems):
        print(f"cover lists all {len(ORDER)} chapters in order")

    print()
    if problems:
        print(f"{len(problems)} structural problem(s):")
        for problem in problems[:40]:
            print("  -", problem)
        return 1
    print("Structure OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
