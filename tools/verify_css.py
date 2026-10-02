"""CSS coverage: every class the pages use has a rule, and every rule is used.

A class with no rule is invisible to the reader, and a rule with no class is
dead weight. Both are reported.
"""

import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mojomanual.clean import CALLOUTS, TOKEN_NAMES


def class_tokens(markup: str) -> Counter:
    found = Counter()
    for value in re.findall(r'class="([^"]+)"', markup):
        for name in value.split():
            found[name] += 1
    return found


def main() -> int:
    root = Path(
        sys.argv[1]
        if len(sys.argv) > 1
        else r"C:\Users\user\Desktop\the_books\data_science\single_source_of_truth mojo"
    )

    css = (root / "assets" / "mojo.css").read_text(encoding="utf-8")
    script = (root / "assets" / "mojo.js").read_text(encoding="utf-8")

    # class names used by the rendered documents and the script
    used = Counter()
    for path in sorted(root.glob("pages/*.html")) + [root / "index.html"]:
        used.update(class_tokens(path.read_text(encoding="utf-8")))
    # the script builds markup at runtime: class="a b", class="a" + class="b",
    # and the same with escaped quotes inside its own string literals
    for name in re.findall(r'class=\\?"([^"\\{]+)', script):
        for token in re.findall(r"[a-zA-Z][\w-]*", name):
            used[token] += 1

    # class names the stylesheet can select
    selectors = re.findall(r"\.(-?[_a-zA-Z][\w-]*)", css)

    # A vocabulary the cleaner can emit but these 38 pages happen not to use is
    # not dead code: a danger callout simply may not appear in this corpus.
    vocabulary = {f"callout--{k}" for k in CALLOUTS} | {f"tk-{n}" for n in TOKEN_NAMES}

    styled = {name for name in selectors}
    unstyled = sorted(name for name in used if name not in styled)
    unused = sorted({name for name in selectors} - set(used) - vocabulary)

    print(f"class names used:        {len(used):>4}")
    print(f"class names with a rule: {len(styled):>4}")
    print()

    if unstyled:
        print(f"used but unstyled ({len(unstyled)}):")
        for name in unstyled:
            print(f"  .{name}  (x{used[name]})")
    else:
        print("every class the pages use has a rule")

    print()
    if unused:
        print(f"styled but unused ({len(unused)}):")
        for name in unused:
            print(f"  .{name}")
    else:
        print("every rule in the stylesheet is used")

    return 1 if (unstyled or unused) else 0


if __name__ == "__main__":
    raise SystemExit(main())
