"""Ad-hoc inspection of a rendered book. Not part of the build."""

import glob
import json
import os
import sys

from bs4 import BeautifulSoup

root = sys.argv[1] if len(sys.argv) > 1 else "."


def read(rel):
    return open(os.path.join(root, rel), encoding="utf-8").read()


idx = json.loads(read("assets/search-index.json"))
print("index records:", len(idx), "| fields:", sorted(idx[0]))
print("total indexed chars:", sum(len(d["text"]) for d in idx))
print("empty texts:", [d["url"] for d in idx if len(d["text"]) < 200])

cover = BeautifulSoup(read("index.html"), "lxml")
print()
print("cover h1:", cover.h1.get_text(" ", strip=True))
print("toc links:", len(cover.select("a.toc__link")), "| parts:", len(cover.select("section.part")))
print("hero stats:", [s.get_text(" ", strip=True) for s in cover.select(".stat")])

for rel in ("pages/23_using-pointers.html", "pages/02_get-started-with-mojo.html"):
    p = BeautifulSoup(read(rel), "lxml")
    dek = p.select_one(".dek")
    print()
    print("==", rel)
    print("  h1 count:", len(p.find_all("h1")), "|", p.h1.get_text(" ", strip=True))
    print("  dek:", dek.get_text(" ", strip=True)[:90] if dek else None)
    print("  crumb:", [c.get_text(" ", strip=True) for c in p.select(".crumb span")])
    print("  rail items:", len(p.select(".rail:not(.rail--inline) li")))
    print(
        "  code:", len(p.select("figure.cb")),
        "| callouts:", len(p.select("aside.callout")),
        "| tables:", len(p.select(".table-wrap")),
        "| figures:", len(p.select("figure.fig")),
        "| discs:", len(p.select("details.disc")),
    )
    print("  pager:", [a.get_text(" ", strip=True) for a in p.select(".pager__link")])
    print("  body class:", p.body.get("class"))
    print("  search index:", p.select_one("[data-search-index]").get("data-search-index"))
    print("  byline:", p.select_one(".byline").get_text(" ", strip=True)[:110])

print()
print("empty pages:", [f for f in sorted(glob.glob(os.path.join(root, "pages/*.html"))) if os.path.getsize(f) < 4000])
