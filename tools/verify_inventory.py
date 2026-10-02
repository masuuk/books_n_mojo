"""Inventory of every Docusaurus construct still in the archives, so nothing is
lost silently. Reports the class prefixes and data attributes the cleaner sees."""

import re
import sys
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup, Tag

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mojomanual.extract import read_archive


def classes_of(node: Tag) -> list[str]:
    value = node.get("class") or []
    return value if isinstance(value, list) else [value]


def main() -> int:
    root = Path(
        sys.argv[1]
        if len(sys.argv) > 1
        else r"C:\Users\user\Desktop\the_books\data_science\single_source_of_truth mojo\raw"
    )
    tokens = Counter()
    attributes = Counter()
    titles = []

    for archive_file in sorted(root.glob("*.mhtml")):
        archive = read_archive(archive_file)
        soup = BeautifulSoup(str(archive.article), "lxml")
        for node in soup.find_all(True):
            for name in classes_of(node):
                stem = re.sub(r"_[A-Za-z0-9]{4,}$", "", name)
                tokens[stem] += 1
            for key in node.attrs:
                if key.startswith("data-"):
                    attributes[key] += 1
        for node in soup.find_all(class_=lambda c: c and "codeBlockTitle" in str(c)):
            titles.append((archive_file.name, node.get_text(" ", strip=True)))

    print("=== class stems (generator vocabulary) ===")
    for name, count in tokens.most_common(40):
        print(f"  {count:>6}  {name}")
    print()
    print("=== data-* attributes ===")
    for name, count in attributes.most_common(30):
        print(f"  {count:>6}  {name}")
    print()
    print("=== code block titles (dropped today) ===")
    for name, title in titles[:25]:
        print(f"  {name[:38]:40} {title[:40]!r}")
    print(f"  total: {len(titles)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
