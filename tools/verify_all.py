"""G1-G9, all of them, on every book.

    uv run tools/verify_all.py

Each verifier reads the rendered tree it is pointed at, so it is run once per
book rather than trusting a default. The build check then compares all four
trees against each other, which no single-book verifier can do.

verify_navigation.py and build_book_nav.py --check cover the app, the book
hub, the shelf catalog and the 65 shelf pages, which live outside the manual
directory.
"""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

BOOKS = {
    "ds": "data_science",
    "fin": "finance",
    "geo": "geomatics",
    "or": "operations_research",
}
MANUAL = "single_source_of_truth mojo"

#: Verifiers that take the manual root as their first argument.
PER_BOOK = ["verify_text.py", "verify_structure.py", "verify_ids.py",
            "verify_css.py", "verify_tokens.py"]


def run(label: str, args: list[str]) -> int:
    # flush, or the child's output lands under the wrong heading
    print(f"=== {label} " + "=" * max(4, 58 - len(label)), flush=True)
    result = subprocess.run(args, cwd=HERE, text=True)
    print()
    return 1 if result.returncode else 0


def main() -> int:
    failures = 0

    for book, folder in BOOKS.items():
        root = str(HERE.parent / folder / MANUAL)
        for script in PER_BOOK:
            failures += run(f"{book}: {script}", [sys.executable, str(HERE / script), root])

    # The shelf repairs are one-off content migrations over archival files.
    # Re-running them must be a no-op, so a clean tree is evidence they ran.
    # They are also run before verify_navigation.py so the navigation gate is
    # never satisfied by a script's own in-flight edit.
    for script in ("fix_shelf_links.py", "fix_shelf_styles.py"):
        failures += run(f"{script} (idempotence)", [sys.executable, str(HERE / script)])
    failures += run("verify_navigation.py", [sys.executable, str(HERE / "verify_navigation.py")])
    failures += run(
        "build_book_nav.py --check",
        [sys.executable, str(HERE / "build_book_nav.py"), "--check"],
    )
    failures += run(
        "build_mojo_manual.py --check",
        [sys.executable, str(HERE / "build_mojo_manual.py"), "--check"],
    )

    if failures:
        print(f"{failures} verifier(s) failed.")
        return 1
    print("Every gate passed on every book.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
