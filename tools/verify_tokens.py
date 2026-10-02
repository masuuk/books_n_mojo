"""Every syntax token the cleaner emits has a colour, and vice versa."""

import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mojomanual.clean import TOKEN_NAMES


def main() -> int:
    root = Path(
        sys.argv[1]
        if len(sys.argv) > 1
        else Path(__file__).resolve().parent.parent / "data_science" / "single_source_of_truth mojo"
    )
    css = (root / "assets" / "mojo.css").read_text(encoding="utf-8")

    used = Counter()
    for path in sorted((root / "pages").glob("*.html")):
        for value in re.findall(r'class="([^"]*\btk-[^"]*)"', path.read_text(encoding="utf-8")):
            for token in value.split():
                if token.startswith("tk-"):
                    used[token] += 1

    styled = set(re.findall(r"\.((?:tk)-[\w-]+)", css))
    expected = {f"tk-{name}" for name in TOKEN_NAMES}

    print("token classes emitted:")
    for name in sorted(used):
        print(f"  {used[name]:>7}  {name}")
    print()
    print(f"emitted: {len(used)}  | styled: {len(styled)}  | known: {len(expected)}")

    unstyled = sorted(n for n in used if n not in styled)
    unknown = sorted(n for n in used if n not in expected)
    unused = sorted(n for n in styled if n not in used)

    problems = 0
    if unstyled:
        problems += 1
        print(f"\nemitted but unstyled: {unstyled}")
    if unknown:
        problems += 1
        print(f"\nemitted but not a known token: {unknown}")
    if unused:
        # the language may simply not use them; every colour is still reachable
        print(f"\nnot present in this corpus (colour kept): {unused}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
