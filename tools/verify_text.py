"""G2: prove the rendered text says what the archives said.

Word-by-word, per page, as multisets: every word the archive carried should still be
there, unless it is a code-block line number or a fragment of chrome we deliberately
dropped. Anything else is real content loss and gets reported.
"""

import re
import sys
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mojomanual.clean import ImagePlan, clean_article
from mojomanual.extract import page_title, read_archive
from mojomanual.manifest import BY_PATH, canonical_path

#: A bare number in the source is a line number in a code gutter, not prose.
NUMBER = re.compile(r"^\d+$")


def words(text: str) -> list[str]:
    text = text.replace("\u200b", "").replace("\u00a0", " ")
    return re.findall(r"[a-z_][a-z_0-9]*", text.lower())


def main() -> int:
    root = Path(
        sys.argv[1]
        if len(sys.argv) > 1
        else Path(__file__).resolve().parent.parent / "data_science" / "single_source_of_truth mojo"
    )
    page_paths = {e.path: f"../pages/{e.slug}.html" for e in BY_PATH.values()}

    total_source = total_kept = 0
    losses: list[tuple[str, str, int, int]] = []
    pages = 0

    for archive_file in sorted((root / "raw").glob("*.mhtml")):
        archive = read_archive(archive_file)
        entry = BY_PATH.get(canonical_path(archive.url))
        if entry is None:
            print(f"  ?? no manifest entry for {archive_file.name}")
            continue
        pages += 1

        source = BeautifulSoup(str(archive.article), "lxml")
        for heading in source.find_all("h1"):
            heading.decompose()  # the shell renders the title instead
        source_words = words(source.get_text(" "))
        total_source += len(source_words)

        page = clean_article(
            archive.article,
            page_title(archive),
            archive.url,
            archive.date,
            page_paths,
            here=page_paths[entry.path],
            images=ImagePlan(),
        )
        kept_words = words(page.plain_text)
        total_kept += len(kept_words)

        before = Counter(source_words)
        after = Counter(kept_words)
        for word, count in before.items():
            dropped = count - after.get(word, 0)
            if dropped > 0:
                losses.append((entry.slug, word, dropped, count))

    print(f"pages:                  {pages}")
    print(f"source words:           {total_source:,}")
    print(f"rendered words:         {total_kept:,}")
    print(f"distinct source words:  {len({w for _, w, _, _ in losses}):,}")
    print()
    if not losses:
        print("No source word was lost.")
        return 0

    losses.sort(key=lambda item: -item[2])
    lost_words = sum(item[2] for item in losses)
    print(f"{len(losses)} distinct words lost, {lost_words:,} occurrences total")
    for slug, word, dropped, count in losses[:30]:
        print(f"  {slug:<34} {word!r:<22} -{dropped} of {count}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
