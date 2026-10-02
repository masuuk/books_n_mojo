"""Authored reading order for the Mojo v1 manual.

The archives on disk are alphabetical; a book needs a curriculum. Each entry maps a
canonical docs path to its place in the manual, its part, and the filename it is
rendered to. The pipeline matches archives to entries by canonical path, so the
order below *is* the book.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Entry:
    path: str  # canonical docs path, e.g. "/docs/manual/structs/"
    slug: str  # filename stem, e.g. "13_mojo-structs"
    part: str
    title: str
    blurb: str = ""
    order: int = 0  # 1-based position in the book, filled in below


PART_TITLES: list[tuple[str, str, str]] = [
    ("I", "Orientation", "What Mojo is, and how to hold it in your head."),
    ("II", "The Language", "Variables, types, functions, and the shape of control flow."),
    ("III", "Abstraction & Values", "Structs, traits, generics, and the ownership model."),
    ("IV", "Memory & Interop", "Pointers, Python, and the C foreign function interface."),
    ("V", "Compile-Time Programming", "Metaprogramming, comptime evaluation, and reflection."),
    ("VI", "Projects & Tooling", "Packages, distribution, notebooks, and agent skills."),
    ("VII", "Reference", "One-page tables to keep open while you work."),
]

ORDER: list[Entry] = [
    # I — Orientation
    Entry("/docs/manual/quickstart/", "01_mojo-quickstart", "I", "Mojo quickstart",
          "A guided first program: install, build, run."),
    Entry("/docs/manual/get-started/", "02_get-started-with-mojo", "I", "Get started with Mojo",
          "Toolchain, first project, and the full source of two samples."),
    Entry("/docs/manual/basics/", "03_mojo-language-basics", "I", "Mojo language basics",
          "The small set of ideas the rest of the manual depends on."),
    Entry("/docs/manual/python-to-mojo/", "04_mojo-tips-for-python-devs", "I",
          "Mojo tips for Python devs", "A translation table for people who already code Python."),
    # II — The Language
    Entry("/docs/manual/variables/", "05_variables", "II", "Variables",
          "Declaration, mutation, aliasing, and scopes."),
    Entry("/docs/manual/types/", "06_types", "II", "Types",
          "The type system: integers, floats, strings, collections, SIMD, and Tensor."),
    Entry("/docs/manual/operators/", "07_operators", "II", "Operators",
          "Arithmetic, comparison, bitwise, and boolean logic."),
    Entry("/docs/manual/functions/", "08_functions", "II", "Functions",
          "Parameters, returns, default and keyword arguments, raising and yielding."),
    Entry("/docs/manual/functions/lambda/", "09_lambda-expressions", "II", "Lambda expressions",
          "Anonymous functions and closures over surrounding scope."),
    Entry("/docs/manual/functions/closures/", "10_closures", "II", "Closures",
          "Capturing state, reference semantics, and escaping values."),
    Entry("/docs/manual/control-flow/", "11_control-flow", "II", "Control flow",
          "Branching, looping, and the Mojo equivalents of Python's statements."),
    Entry("/docs/manual/errors/", "12_errors-and-context-managers", "II",
          "Errors, error handling, and context managers", "Failable types, raises, and cleanup."),
    # III — Abstraction & Values
    Entry("/docs/manual/structs/", "13_mojo-structs", "III", "Mojo structs",
          "Methods, constructors, overloading, and generic fields."),
    Entry("/docs/manual/structs/operator-support/", "14_operator-support", "III",
          "Add operator support to custom types",
          "Implementing dunder methods and the full protocol."),
    Entry("/docs/manual/structs/reference/", "15_self-referential-structs", "III",
          "Self-referential structs", "Lists, sets, and graphs built out of Mojo itself."),
    Entry("/docs/manual/traits/", "16_traits", "III", "Traits",
          "Contracts between types and the code that uses them."),
    Entry("/docs/manual/generics/", "17_parameterized-declarations", "III",
          "Parameterized declarations", "Generic types and functions, and how they specialise."),
    Entry("/docs/manual/values/value-semantics/", "18_value-semantics", "III", "Value semantics",
          "What it means for a type to behave like a value."),
    Entry("/docs/manual/values/", "19_intro-to-value-ownership", "III", "Intro to value ownership",
          "Copying, moving, borrowing: the three ways a value reaches a function."),
    Entry("/docs/manual/values/ownership/", "20_ownership", "III", "Ownership",
          "Affine types, single ownership, and the borrow checker."),
    Entry("/docs/manual/values/lifetimes/", "21_lifetimes-origins-and-references", "III",
          "Lifetimes, origins, and references", "Reading the origin lattice and writing safe borrows."),
    # IV — Memory & Interop
    Entry("/docs/manual/pointers/", "22_intro-to-pointers", "IV", "Intro to pointers",
          "Raw and owned pointers, and the mental model behind them."),
    Entry("/docs/manual/pointers/using-pointers/", "23_using-pointers", "IV", "Using pointers",
          "Allocation, offsets, strided loads, and the pointer lifecycle."),
    Entry("/docs/manual/python/", "24_python-interoperability", "IV", "Python interoperability",
          "The shape of the boundary between Mojo and Python."),
    Entry("/docs/manual/python/types/", "25_python-types", "IV", "Python types",
          "Using Python objects, and what crosses the boundary."),
    Entry("/docs/manual/python/python-from-mojo/", "26_calling-python-from-mojo", "IV",
          "Calling Python from Mojo", "Importing modules and invoking Python at run time."),
    Entry("/docs/manual/python/mojo-from-python/", "27_calling-mojo-from-python", "IV",
          "Calling Mojo from Python", "Exposing Mojo functions as Python extension types."),
    Entry("/docs/manual/c-ffi/", "28_c-foreign-function-interface", "IV",
          "Using Mojo's C FFI to call C libraries", "Declaring externs, linking, and calling C."),
    # V — Compile-Time Programming
    Entry("/docs/manual/metaprogramming/", "29_intro-to-metaprogramming", "V",
          "Intro to metaprogramming", "Why Mojo runs part of your program before you do."),
    Entry("/docs/manual/metaprogramming/comptime-evaluation/", "30_compile-time-evaluation", "V",
          "Compile-time evaluation", "Compiling code as a value, with alias and let."),
    Entry("/docs/manual/metaprogramming/constraints/", "31_comptime-constraints-and-assertions", "V",
          "Comptime constraints and assertions", "Rejecting types and values the compiler cannot accept."),
    Entry("/docs/manual/metaprogramming/materialization/", "32_materializing-comptime-values", "V",
          "Materializing compile-time values at run time",
          "Turning parameters and comptime values into run-time data."),
    Entry("/docs/manual/metaprogramming/reflection/", "33_reflection", "V", "Reflection",
          "Introspecting types, functions, and their parameters."),
    # VI — Projects & Tooling
    Entry("/docs/manual/packages/", "34_modules-and-packages", "VI", "Modules and packages",
          "Splitting a codebase across modules and packages."),
    Entry("/docs/tools/packaging/", "35_packaging", "VI", "Packaging",
          "Publishing a Mojo package to a package index."),
    Entry("/docs/tools/notebooks/", "36_jupyter-notebooks", "VI", "Jupyter notebooks",
          "Writing, running, and publishing .ipynb Mojo notebooks."),
    Entry("/docs/tools/skills/", "37_mojo-ai-skills", "VI", "Mojo AI skills",
          "Teaching an agent the Mojo toolchain."),
    # VII — Reference
    Entry("/docs/reference/cheat-sheets/types-and-literals/", "38_types-and-literals-cheat-sheet",
          "VII", "Mojo types & literals cheat sheet",
          "Every builtin type and literal form, on one page."),
]

BY_PATH: dict[str, Entry] = {e.path: e for e in ORDER}

ORDER = [
    Entry(e.path, e.slug, e.part, e.title, e.blurb, index)
    for index, e in enumerate(ORDER, start=1)
]
BY_PATH = {e.path: e for e in ORDER}


def canonical_path(url: str) -> str | None:
    """Reduce a docs URL to the canonical path used for manifest lookup."""
    if not url:
        return None
    without_scheme = url.split("://", 1)[-1]
    slash = without_scheme.find("/")
    if slash < 0:
        return None
    path = without_scheme[slash:]
    for prefix in ("/nightly", "/v24-6", "/latest"):
        if path.startswith(prefix + "/"):
            path = path[len(prefix):]
            break
    if not path.endswith("/"):
        path += "/"
    return path