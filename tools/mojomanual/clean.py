"""Stage 2: turn a hydrated Docusaurus article region into clean, semantic HTML.

Nothing is written from the vocabulary of the site generator. Every construct the
manual uses -- code, callouts, tables, disclosures, panels, figures -- is rebuilt
from first principles, and every trace of the generator (hashed CSS-module class
names, inline colours, copy buttons, permalink glyphs, extension cruft) is removed.

The output of this module is deliberately generator-agnostic: a flat semantic tree
whose class names belong to :mod:`mojomanual.render` and its stylesheet, and nobody
else's.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urldefrag, urlsplit

from bs4 import BeautifulSoup, NavigableString, Tag

from .manifest import canonical_path

# --------------------------------------------------------------------------- #
# vocabulary
# --------------------------------------------------------------------------- #

#: Docusaurus tag set -> semantics we keep. Everything else is unwrapped.
DROP_TAGS = {
    "script", "style", "noscript", "iframe", "svg", "g", "defs", "clippath",
    "path", "button", "form", "input", "link", "meta", "title", "use", "symbol",
}

#: Classes that mark copy buttons, permalink glyphs and word-wrap toggles.
CHROME_CLASSES = (
    "buttonGroup", "copyButton", "wordWrapButton", "hash-link", "clean-btn",
    "llms-directive", "theme-edit-this-page", "markdown-copy-button",
)

TOKEN_PREFIX = "tk"

#: The 13 token classes the Prism grammars emit, kept verbatim as `tk-*`.
TOKEN_NAMES = (
    "keyword", "boolean", "builtin", "class-name", "decorator", "annotation",
    "property", "number", "operator", "punctuation", "string", "comment",
    "function", "special-vars", "atrule", "key", "plain",
)

#: Two admonition types are the same idea wearing a different name. Fold them
#: onto one class so the stylesheet never has to colour the same thing twice.
CALLOUT_ALIASES = {"warning": "caution", "info": "note"}

CALLOUTS: dict[str, tuple[str, str]] = {
    # type -> (default label, glyph)
    "note": ("Note", "◆"),
    "tip": ("Tip", "✦"),
    "caution": ("Caution", "▲"),
    "danger": ("Danger", "✖"),
    "warning": ("Warning", "▲"),
    "experiment": ("Experiment", "◈"),
    "deprecated": ("Deprecated", "⊘"),
    "info": ("Note", "◆"),
}

LANG_LABEL = {
    "mojo": "Mojo", "python": "Python", "py": "Python", "bash": "Bash",
    "sh": "Shell", "shell": "Shell", "output": "Output", "text": "Text",
    "console": "Terminal", "ini": "INI", "toml": "TOML", "yaml": "YAML",
    "yml": "YAML", "json": "JSON", "cpp": "C++", "c": "C", "rust": "Rust",
    "sql": "SQL", "diff": "Diff", "makefile": "Make",
}

#: Languages whose blocks are transcripts rather than source.
TRANSCRIPT_LANGS = {"output", "console", "text"}

_ID_SAFE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    slug = _ID_SAFE.sub("-", text.strip().lower()).strip("-")
    return slug or "section"


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# --------------------------------------------------------------------------- #
# result type
# --------------------------------------------------------------------------- #


@dataclass
class CleanedPage:
    """Semantic article ready for the renderer."""

    body_html: str
    title: str
    dek: str = ""
    headings: list[tuple[int, str, str]] = field(default_factory=list)  # (level, text, id)
    plain_text: str = ""
    source_url: str = ""
    source_date: str = ""
    stats: dict[str, int] = field(default_factory=dict)
    #: every id this page can be linked to, so neighbours can drop dead fragments
    anchors: set[str] = field(default_factory=set)


# --------------------------------------------------------------------------- #
# inline rendering (used inside code blocks)
# --------------------------------------------------------------------------- #


def _token_class(name: str) -> str | None:
    return name if name in TOKEN_NAMES else None


def render_code_inline(node) -> str:
    """Serialise one node inside a code block to token-annotated HTML."""
    if isinstance(node, NavigableString):
        return esc(str(node))
    if not isinstance(node, Tag):
        return ""
    if node.name == "br":
        return ""
    classes = [c for c in (node.get("class") or []) if _token_class(c)]
    inner = "".join(render_code_inline(child) for child in node.contents)
    if not classes:
        return inner
    out = []
    for cls in classes:
        if cls == "plain":
            continue
        out.append(f'class="{TOKEN_PREFIX}-{cls}"')
    if not out:
        return inner
    return "<span " + " ".join(out) + f">{inner}</span>"


# --------------------------------------------------------------------------- #
# code blocks
# --------------------------------------------------------------------------- #


def _code_lines(code: Tag) -> list[tuple[str, bool]]:
    """Return [(inner_html, is_highlighted)] for a `<code>` element."""
    children = [c for c in code.contents if not _is_blank(c)]
    divs = [c for c in children if isinstance(c, Tag) and c.name == "div"]
    if divs and len(divs) == len(children):
        lines = []
        for div in divs:
            classes = div.get("class") or []
            highlighted = any("highlighted-line" in c for c in classes)
            lines.append(("".join(render_code_inline(ch) for ch in div.contents), highlighted))
        if lines:
            return lines
    text = code.get_text()
    return [(esc(line), False) for line in text.split("\n")]


def _is_blank(node) -> bool:
    return isinstance(node, NavigableString) and not str(node).strip()


def _language_of(pre: Tag) -> str:
    classes = pre.get("class") or []
    for cls in classes:
        if cls.startswith("language-"):
            return cls[len("language-"):].lower()
    for cls in classes:
        if cls in LANG_LABEL:
            return cls
    parent_classes = []
    node = pre.parent
    while isinstance(node, Tag) and len(parent_classes) < 3:
        parent_classes.extend(node.get("class") or [])
        node = node.parent
    for cls in parent_classes:
        if cls.startswith("language-"):
            return cls[len("language-"):].lower()
    return "mojo"


#: ``codeBlockTitle_OeMC`` and friends: the module hash is not stable.
_CODE_BLOCK_TITLE = re.compile(r"codeBlockTitle(?:_\w+)?$")
_CODE_BLOCK_CONTAINER = re.compile(r"(?:theme-code-block|codeBlockContainer)(?:_\w+)?$")


def _class_names(value) -> list[str]:
    if value is None:
        return []
    names = value if isinstance(value, (list, tuple, set)) else [value]
    return [name for name in names if isinstance(name, str)]


#: Matches the "Table 3." label a docs caption leads with.
TABLE_LABEL = re.compile(r"^\s*(Figure|Table)\s+(\d+)\s*[.:]?\s*", re.I)


def _table_caption_text(text: str, soup: BeautifulSoup) -> Tag:
    """Turn a caption's text into a <caption> for the table it labels."""

    text = " ".join(text.split())
    match = TABLE_LABEL.match(text)
    label = f"{match.group(1)} {match.group(2)}." if match else ""
    body = TABLE_LABEL.sub("", text, count=1)

    node = soup.new_tag("caption")
    node["class"] = ["table__caption"]
    if label:
        strong = soup.new_tag("b")
        strong.string = label
        node.append(strong)
        node.append(soup.new_string(f" {body}"))
    else:
        node.string = body
    return node


def _is_code_block_title(value) -> bool:
    return any(_CODE_BLOCK_TITLE.fullmatch(name) for name in _class_names(value))


def _is_code_block_container(value) -> bool:
    return any(_CODE_BLOCK_CONTAINER.fullmatch(name) for name in _class_names(value))


def rebuild_code_block(pre: Tag, soup: BeautifulSoup) -> Tag:
    """Replace a Docusaurus code block with a self-describing `<figure>`."""
    lang = _language_of(pre)
    code = pre.find("code")
    lines = _code_lines(code) if isinstance(code, Tag) else [
        (esc(l), False) for l in pre.get_text().split("\n")
    ]

    figure = soup.new_tag("figure")
    figure["class"] = ["cb"]
    figure["data-lang"] = lang
    if lang in TRANSCRIPT_LANGS:
        figure["class"].append("cb--transcript")

    bar = soup.new_tag("figcaption")
    bar["class"] = ["cb__bar"]

    # Docusaurus names the file a snippet came from ("main.py", "recipe.yaml").
    # That is real information, so it leads the bar. The title is a sibling of
    # the <pre>'s wrapper, not an ancestor, so look inside the block container.
    file_label = ""
    block = pre.find_parent("div", class_=_is_code_block_container)
    if isinstance(block, Tag):
        for candidate in block.find_all(class_=_is_code_block_title):
            if isinstance(candidate, Tag):
                file_label = " ".join(candidate.get_text(" ", strip=True).split())
                break
    if file_label:
        name = soup.new_tag("span")
        name["class"] = ["cb__file"]
        name.string = file_label
        bar.append(name)

    label = soup.new_tag("span")
    label["class"] = ["cb__lang"]
    label.string = LANG_LABEL.get(lang, lang)
    bar.append(label)

    spacer = soup.new_tag("span")
    spacer["class"] = ["cb__spacer"]
    bar.append(spacer)

    button = soup.new_tag("button")
    button["class"] = ["cb__copy"]
    button["type"] = "button"
    button["data-copy"] = ""
    button["aria-label"] = f"Copy {LANG_LABEL.get(lang, lang)} code to clipboard"
    button.string = "Copy"
    bar.append(button)
    figure.append(bar)

    pre_new = soup.new_tag("pre")
    pre_new["class"] = ["cb__pre"]
    code_new = soup.new_tag("code")
    code_new["class"] = ["cb__code"]
    for index, (inner, highlighted) in enumerate(lines, start=1):
        line = soup.new_tag("span")
        line["class"] = ["cl", "hl"] if highlighted else ["cl"]
        line["data-line"] = str(index)
        line.append(BeautifulSoup(inner, "html.parser"))
        code_new.append(line)
        code_new.append("\n")
    pre_new.append(code_new)
    figure.append(pre_new)

    container = pre.find_parent("div", class_=_is_code_block_container)
    target = container if isinstance(container, Tag) else pre
    target.replace_with(figure)
    return figure


# --------------------------------------------------------------------------- #
# callouts
# --------------------------------------------------------------------------- #


def rebuild_callout(node: Tag, soup: BeautifulSoup) -> Tag:
    """Replace a Mantine-flavoured admonition with a `<aside class="callout">`."""
    if node.decomposed or node.attrs is None:
        return node
    kind = (node.get("data-admonition-type") or "note").lower()
    label_default, glyph = CALLOUTS.get(kind, CALLOUTS["note"])
    class_kind = CALLOUT_ALIASES.get(kind, kind)

    label_node = node.find(class_=lambda c: c and "mantine-Alert-label" in c)
    label = label_node.get_text(" ", strip=True) if label_node else label_default

    message = node.find(class_=lambda c: c and "mantine-Alert-message" in c)
    content = node.find(class_=lambda c: c and "admonitionAlertContent" in c)
    source = content if isinstance(content, Tag) else message
    if not isinstance(source, Tag):
        source = node

    aside = soup.new_tag("aside")
    aside["class"] = ["callout", f"callout--{class_kind}"]

    head = soup.new_tag("p")
    head["class"] = ["callout__label"]
    mark = soup.new_tag("span")
    mark["class"] = ["callout__glyph"]
    mark["aria-hidden"] = "true"
    mark.string = glyph
    head.append(mark)
    head.append(soup.new_string(label))
    aside.append(head)

    body = soup.new_tag("div")
    body["class"] = ["callout__body"]
    for child in list(source.contents):
        body.append(child.extract())
    aside.append(body)

    node.replace_with(aside)
    return aside


# --------------------------------------------------------------------------- #
# disclosures and panels
# --------------------------------------------------------------------------- #


def rebuild_disclosure(node: Tag, soup: BeautifulSoup) -> Tag:
    """Normalise a `<details>` block into a first-class collapsible."""
    node["class"] = ["disc"]
    node.attrs.pop("data-collapsed", None)
    for attr in ("role", "aria-describedby", "aria-labelledby"):
        node.attrs.pop(attr, None)
    summary = node.find("summary")
    if isinstance(summary, Tag):
        summary["class"] = ["disc__summary"]
    return node


#: The cheat-sheet panels mark their title and body with hashed class names.
_PANEL_TITLE = re.compile(r"panelTitle(?:_\w+)?$")
_PANEL_BODY = re.compile(r"body_\w+$")


def _is_panel_title(value) -> bool:
    return any(_PANEL_TITLE.fullmatch(name) for name in _class_names(value))


def _is_panel_body(value) -> bool:
    return any(_PANEL_BODY.fullmatch(name) for name in _class_names(value))


def rebuild_panel(node: Tag, soup: BeautifulSoup) -> Tag:
    """Turn the cheat-sheet panel component into a titled section."""
    node["class"] = ["panel"]

    # Two shapes: a div.panelTitle, or a heading as the section's first child.
    title = node.find(class_=_is_panel_title)
    if not isinstance(title, Tag):
        first = node.find(["h2", "h3", "h4"], recursive=False)
        if isinstance(first, Tag):
            title = first
    if isinstance(title, Tag):
        if title.name.startswith("h"):
            # the heading keeps its level and id; the title is just its span
            for span in title.find_all("span", recursive=False):
                if "h__link" not in (span.get("class") or []):
                    span["class"] = ["panel__title"]
                    break
            else:
                title["class"] = list(title.get("class") or []) + ["panel__title"]
        else:
            title.name = "h3"
            title["class"] = ["panel__title"]

    body = node.find(class_=_is_panel_body)
    if isinstance(body, Tag):
        body["class"] = ["panel__body"]
    return node


# --------------------------------------------------------------------------- #
# figures and images
# --------------------------------------------------------------------------- #


@dataclass
class ImagePlan:
    """Where every diagram lives once it is local to the book."""

    files: dict[str, bytes] = field(default_factory=dict)  # url -> bytes

    def local_name(self, url: str) -> str:
        """Return the in-book relative path for a remote diagram URL."""
        name = url.rsplit("/", 1)[-1]
        if not name:
            return ""
        self.files.setdefault(url, b"")
        return f"../assets/images/{name}"


def _variant(img: Tag) -> str:
    """Which theme a diagram variant belongs to.

    Docusaurus marks the variant three ways depending on where the markup came
    from: a fragment on the src, a class, or "-dark" in Modular's own filename.
    """
    src = (img.get("src") or "").split("#", 1)[0]
    classes = img.get("class") or []
    if src.endswith("#dark") or "dark" in classes:
        return "dark"
    if src.endswith("#light") or "light" in classes:
        return "light"
    name = src.rsplit("/", 1)[-1].lower()
    if "-dark" in name or name.startswith("dark-"):
        return "dark"
    return "light"


def _clean_src(src: str) -> str:
    return src.split("#", 1)[0]


def rebuild_figure(node: Tag, soup: BeautifulSoup, images: ImagePlan) -> Tag:
    """Rebuild a figure, pairing light/dark diagram variants into a `<picture>`."""
    imgs = [i for i in node.find_all("img") if not i.decomposed and i.attrs is not None]
    caption = node.find("figcaption")

    light = next((i for i in imgs if _variant(i) == "light"), None)
    dark = next((i for i in imgs if _variant(i) == "dark"), None)
    alt = ""
    for candidate in (light, dark):
        if candidate is not None and (candidate.get("alt") or "").strip():
            alt = " ".join(candidate.get("alt").split())
            break
    if not alt and isinstance(caption, Tag):
        # A caption already describes the diagram; it is the honest alt text.
        text = caption.get_text(" ", strip=True)
        alt = " ".join(re.sub(r"^(Figure|Table)\s+\d+\.\s*", "", text).split())

    # read every attribute we need before the nodes go away
    light_src = _clean_src(light.get("src") or "") if light is not None else ""
    dark_src = _clean_src(dark.get("src") or "") if dark is not None else ""
    width = (light or dark).get("width") if (light is not None or dark is not None) else None

    node["class"] = ["fig"]
    for img in imgs:
        img.decompose()
    for stale in node.find_all("p", recursive=False):
        if not stale.get_text(strip=True) and not stale.find("img"):
            stale.decompose()

    # Two stacked images, switched by this book's own theme rather than by the
    # operating system, so the toggle on the page is the one that decides.
    picture = soup.new_tag("div")
    picture["class"] = ["fig__media"]
    primary = light_src or dark_src
    if primary:
        shown = soup.new_tag("img")
        shown["class"] = ["fig__img", "fig__img--light"]
        shown["src"] = images.local_name(primary)
        shown["alt"] = alt
        shown["loading"] = "lazy"
        shown["decoding"] = "async"
        if width:
            shown["width"] = width
        picture.append(shown)
    if dark_src and dark_src != primary:
        hidden = soup.new_tag("img")
        hidden["class"] = ["fig__img", "fig__img--dark"]
        hidden["src"] = images.local_name(dark_src)
        hidden["alt"] = ""
        hidden["loading"] = "lazy"
        hidden["decoding"] = "async"
        hidden["aria-hidden"] = "true"
        if width:
            hidden["width"] = width
        picture.append(hidden)

    # A figure with no image is a table Docusaurus wrapped in <figure>. The
    # table step below gives that its own scroll container, so leave it alone.
    if primary:
        media = soup.new_tag("div")
        media["class"] = ["fig__frame"]
        media.append(picture)
        node.insert(0, media)

    if isinstance(caption, Tag):
        caption["class"] = ["fig__caption"]
    elif alt:
        caption = soup.new_tag("figcaption")
        caption["class"] = ["fig__caption"]
        caption.string = alt
        node.append(caption)

    if isinstance(node.get("style"), str):
        del node["style"]
    return node


# --------------------------------------------------------------------------- #
# links
# --------------------------------------------------------------------------- #


class LinkRewriter:
    """Point docs links at the pages this book actually renders."""

    def __init__(
        self,
        page_paths: dict[str, str],
        here: str,
        source_host: str,
        fragments: dict[str, set[str]] | None = None,
    ):
        self.page_paths = page_paths
        self.here = here
        self.source_host = source_host
        #: when supplied, a cross-page fragment that matches nothing is dropped
        self.fragments = fragments

    def __call__(self, anchor: Tag) -> Tag:
        href = anchor.get("href") or ""
        anchor.attrs.pop("class", None)
        anchor.attrs.pop("title", None)
        anchor.attrs.pop("translate", None)
        anchor.attrs.pop("target", None)
        if not href or href.startswith(("mailto:", "tel:")):
            return anchor
        if href.startswith("#"):
            # same-page anchor: keep the fragment
            anchor.attrs.pop("translate", None)
            return anchor

        url, fragment = urldefrag(href)
        host = urlsplit(url).netloc
        if host and host != self.source_host:
            return self._external(anchor)

        key = self._local_key(url)
        if key is None:
            if urlsplit(href).scheme:
                return self._external(anchor)
            return anchor
        target = self.page_paths.get(key)
        if target is None:
            # a docs page this book does not carry: keep the canonical source URL,
            # but say plainly that it leaves the book
            return self._external(anchor)
        if (
            fragment
            and self.fragments is not None
            and fragment not in self.fragments.get(key, frozenset())
        ):
            # the source points at an anchor that no longer exists anywhere;
            # fall back to the top of the page rather than a broken jump
            fragment = ""
        anchor["href"] = target + (f"#{fragment}" if fragment else "")
        return anchor

    def _external(self, anchor: Tag) -> Tag:
        anchor["class"] = ["ext"]
        anchor["rel"] = ["noopener", "noreferrer"]
        anchor["data-external"] = ""
        return anchor

    def _local_key(self, url: str) -> str | None:
        """Canonical manifest key for a docs URL, or None if unresolvable."""
        split = urlsplit(url)
        path = split.path or "/"
        for prefix in ("/nightly", "/v24-6", "/latest"):
            if path.startswith(prefix + "/"):
                path = path[len(prefix):]
                break
        if not path.endswith("/"):
            path += "/"
        return canonical_path("https://mojolang.org" + path)


# --------------------------------------------------------------------------- #
# headings
# --------------------------------------------------------------------------- #


def _clean_headings(root: Tag, used: set[str]) -> list[tuple[int, str, str]]:
    headings: list[tuple[int, str, str]] = []
    for level in (1, 2, 3, 4):
        for heading in root.find_all(f"h{level}"):
            for glyph in heading.find_all("a", class_="hash-link"):
                glyph.decompose()
            text = " ".join(heading.get_text(" ", strip=True).split())
            anchor_id = heading.get("id") or ""
            anchor_id = re.sub(r"^user-content-", "", anchor_id)
            if not anchor_id:
                anchor_id = slugify(text)
            candidate, suffix = anchor_id, 2
            while candidate in used:
                candidate = f"{anchor_id}-{suffix}"
                suffix += 1
            used.add(candidate)
            heading["id"] = candidate
            heading["class"] = ["h", f"h--{level}"]
            heading["data-level"] = str(level)
            if level >= 2:
                link = BeautifulSoup(
                    f'<a class="h__link" href="#{candidate}" aria-label="Link to '
                    f'{esc(text)}"></a>', "html.parser"
                )
                heading.append(link)
            headings.append((level, text, candidate))
    return headings


# --------------------------------------------------------------------------- #
# entry point
# --------------------------------------------------------------------------- #


#: `data-*` attributes this book owns; every other one is generator noise.
KEEP_DATA = {"data-lang", "data-line", "data-copy", "data-external", "data-level"}

#: The only class names allowed to survive the rewrite. Everything else belongs to
#: the site generator and is dropped.
KEEP_CLASSES = frozenset(
    {
        # code blocks
        "cb", "cb--transcript", "cb__bar", "cb__file", "cb__lang", "cb__spacer",
        "cb__copy", "cb__pre", "cb__code", "cl", "hl",
        # callout variants: a note is not a warning, and the colour says which.
        # Every name in CALLOUTS, so no admonition can arrive uncoloured.
        *{f"callout--{k}" for k in CALLOUTS},
        # callouts
        "callout", "callout__label", "callout__glyph", "callout__body",
        # disclosures, panels, figures, tables
        "disc", "disc__summary", "panel", "panel__title", "panel__body",
        "fig", "fig__frame", "fig__media", "fig__img", "fig__img--light",
        "fig__img--dark", "fig__caption", "table-wrap", "table__caption",
        # headings and links
        "h", "h--1", "h--2", "h--3", "h--4", "h__link", "ext",
    }
)


def _keep_class(name: str) -> bool:
    return name in KEEP_CLASSES or name.startswith(TOKEN_PREFIX + "-")


def _strip_chrome(root: Tag) -> None:
    """Remove generator chrome, inline styling and CSS-module class names."""
    for node in list(root.find_all(True)):
        if not isinstance(node, Tag) or node.decomposed or node.attrs is None:
            continue
        classes = node.get("class") or []
        joined = " ".join(classes)
        kept = [c for c in classes if _keep_class(c)]
        if any(marker in joined for marker in CHROME_CLASSES):
            node.decompose()
            continue
        if node.name in DROP_TAGS and not kept:
            node.decompose()
            continue
        if "theme-code-block" in joined or "codeBlockContainer" in joined:
            continue
        if node.get("id", "").startswith("mantine-"):
            del node["id"]
        for attr in list(node.attrs):
            if attr == "style" or attr == "role":
                del node[attr]
            elif attr.startswith("aria-") and not (
                (attr == "aria-label" and kept) or (attr == "aria-hidden" and kept)
            ):
                del node[attr]
            elif attr.startswith("data-") and attr not in KEEP_DATA:
                del node[attr]
        if classes:
            del node["class"]
        if kept:
            node["class"] = kept


def _strip_content_wrapper(root: Tag) -> None:
    for node in list(root.find_all(True)):
        if not isinstance(node, Tag) or node.decomposed or node.attrs is None:
            continue
        classes = node.get("class") or []
        if node.name in ("header", "footer"):
            node.unwrap()
        elif any("admonitionAlertContent" in c for c in classes):
            node.unwrap()
        elif any(c in classes for c in ("tableWrapper", "tableContainer")) or any(
            c.startswith("table_") for c in classes
        ):
            node.unwrap()


def clean_article(
    article: Tag,
    title: str,
    source_url: str,
    source_date: str,
    page_paths: dict[str, str],
    here: str,
    images: ImagePlan,
    source_host: str = "mojolang.org",
    fragments: dict[str, set[str]] | None = None,
) -> CleanedPage:
    """Turn one archive's article region into a :class:`CleanedPage`."""
    soup = BeautifulSoup("", "html.parser")
    root = Tag(soup, name="div")
    for child in list(article.contents):
        root.append(child.extract())

    # 0. the article's own h1 is the page title; the shell renders it, so the body
    #    starts at the first real section
    for heading in root.find_all("h1"):
        text = " ".join(heading.get_text(" ", strip=True).split())
        if text and not title:
            title = text
        heading.decompose()

    # 1. code blocks first: they carry the most generator markup
    for pre in list(root.find_all("pre")):
        rebuild_code_block(pre, soup)

    # 2. callouts
    for node in list(root.find_all(attrs={"data-admonition-type": True})):
        rebuild_callout(node, soup)

    # 3. structural components
    for node in list(root.find_all("details")):
        rebuild_disclosure(node, soup)
    for node in list(root.find_all("section")):
        rebuild_panel(node, soup)
    for node in list(root.find_all("figure")):
        if "cb" in (node.get("class") or []):
            continue  # a code block, already rebuilt in step 1
        rebuild_figure(node, soup, images)

    # 4. bare images that were never wrapped in a figure
    for img in list(root.find_all("img")):
        if img.find_parent("figure") is not None:
            continue
        wrapper = soup.new_tag("figure")
        wrapper["class"] = ["fig"]
        media = soup.new_tag("div")
        media["class"] = ["fig__frame"]
        media.append(img.extract())
        wrapper.append(media)
        alt = " ".join((img.get("alt") or "").split())
        img["src"] = images.local_name(_clean_src(img.get("src") or ""))
        if alt:
            caption = soup.new_tag("figcaption")
            caption["class"] = ["fig__caption"]
            caption.string = alt
            wrapper.append(caption)
        img.replace_with(wrapper)

    # 5. chrome and inline styling
    _strip_content_wrapper(root)
    _strip_chrome(root)

    # 6. tables. Two shapes arrive here: a bare <table>, and a Docusaurus
    #    <figure id="table-3"><figcaption>Table 3. ...</figcaption><table>.
    #    Both become one scroll container carrying the anchor the prose links to.
    used_ids: set[str] = set()
    for table in list(root.find_all("table")):
        figure = table.find_parent("figure", class_="fig")
        if isinstance(figure, Tag):
            # Reuse the figure as the scroll container so the id and the caption
            # stay with the table they describe.
            wrapper = figure
            wrapper["class"] = ["table-wrap"]
            for frame in wrapper.find_all("div", class_="fig__frame"):
                frame.decompose()
            caption = wrapper.find("figcaption")
        else:
            wrapper = soup.new_tag("div")
            wrapper["class"] = ["table-wrap"]
            table.replace_with(wrapper)
            caption = table.find("caption")

        wrapper.append(table)

        anchor = None
        if isinstance(caption, Tag):
            text = caption.get_text(" ", strip=True)
            caption.replace_with(soup.new_string(""))
            caption.decompose()
            # a caption belongs to the table it labels, not the scroll container,
            # and it has to be the table's first child
            table.insert(0, _table_caption_text(text, soup))
            match = re.match(r"\s*Table\s+(\d+)", text)
            if match:
                anchor = f"table-{match.group(1)}"
        if anchor is None or anchor in used_ids:
            number = len(used_ids) + 1
            while f"table-{number}" in used_ids:
                number += 1
            anchor = f"table-{number}"
        used_ids.add(anchor)
        wrapper["id"] = anchor

    # 7. links
    rewriter = LinkRewriter(page_paths, here, source_host, fragments)
    for anchor in root.find_all("a"):
        rewriter(anchor)

    # 8. headings
    headings = _clean_headings(root, set())

    # 9. empty paragraphs
    for para in list(root.find_all("p")):
        if not para.get_text(strip=True) and not para.find(("img", "picture", "table")):
            para.decompose()

    body_html = root.decode_contents()
    body_html = re.sub(r"\n{3,}", "\n\n", body_html).strip()

    dek = ""
    for para in root.find_all("p"):
        if not para.find_parent("figure") and not para.find_parent("aside"):
            dek = " ".join(para.get_text(" ", strip=True).split())
            break

    code_blocks = root.find_all("figure", class_="cb")
    stats = {
        "code_blocks": len(code_blocks),
        "callouts": len(root.find_all("aside", class_="callout")),
        "tables": len(root.find_all("table")),
        "figures": len(root.find_all("figure", class_="fig")),
        "disclosures": len(root.find_all("details")),
        "languages": sorted({b.get("data-lang", "") for b in code_blocks} - {""}),
    }

    return CleanedPage(
        body_html=body_html,
        title=title,
        dek=dek,
        headings=headings,
        plain_text=" ".join(root.get_text(" ", strip=True).split()),
        source_url=source_url,
        source_date=source_date,
        stats=stats,
        anchors={
            node["id"]
            for node in root.find_all(id=True)
            if isinstance(node.get("id"), str) and node["id"]
        },
    )