"""Every id is unique, and captions are preserved rather than invented.

A table keeps the caption the docs gave it. A table the docs left bare is left
bare: writing a caption would be us making claims about someone else's content.
"""

import collections
import glob
import os
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mojomanual.extract import read_archive
from mojomanual.manifest import BY_PATH, canonical_path

ID = re.compile(r'\sid="([^"]+)"')


def main() -> int:
    root = Path(
        sys.argv[1]
        if len(sys.argv) > 1
        else Path(__file__).resolve().parent.parent / "data_science" / "single_source_of_truth mojo"
    )
    problems: list[str] = []
    pages = 0
    kept = invented = 0

    for path in sorted((root / "pages").glob("*.html")):
        pages += 1
        text = path.read_text(encoding="utf-8")
        for name, count in collections.Counter(ID.findall(text)).items():
            if count > 1:
                problems.append(f"{path.name}: id {name!r} appears {count}x")

        soup = BeautifulSoup(text, "lxml")
        for table in soup.find_all("table"):
            if table.find("caption") is not None:
                kept += 1
            else:
                invented += 1

    # a caption in the render must correspond to one in the source
    for archive_file in sorted((root / "raw").glob("*.mhtml")):
        archive = read_archive(archive_file)
        entry = BY_PATH.get(canonical_path(archive.url))
        if entry is None:
            problems.append(f"{archive_file.name}: no manifest entry")
            continue
        source = BeautifulSoup(str(archive.article), "lxml")
        captioned = 0
        for table in source.find_all("table"):
            figure = table.find_parent("figure")
            if table.find("caption") is not None or (
                figure is not None and figure.find("figcaption") is not None
            ):
                captioned += 1
        rendered = BeautifulSoup(
            (root / "pages" / f"{entry.slug}.html").read_text(encoding="utf-8"), "lxml"
        ).find_all("table")
        got = sum(1 for t in rendered if t.find("caption") is not None)
        if got != captioned:
            problems.append(
                f"{entry.slug}: {captioned} captioned tables in the archive, {got} in the render"
            )

    print(f"pages checked:            {pages}")
    print(f"tables with a caption:    {kept}")
    print(f"tables left bare:         {invented}  (the docs gave them no caption)")
    print(f"problems:                 {len(problems)}")
    for problem in problems[:30]:
        print("  -", problem)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
