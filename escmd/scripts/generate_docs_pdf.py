#!/usr/bin/env python3
"""
Merge selected Markdown and write a single PDF.

Default config: docs/pdf-config.yaml (full docs/ tree). For the short user
manual, pass -c escmd_docs/pdf-config.yaml.

Dependencies (use a virtual environment):
    pip install -r requirements-docs-pdf.txt

A Unicode-capable sans font is required (Arial Unicode on macOS, DejaVu on
many Linux distros). Override paths in the YAML config under fonts:.
"""

from __future__ import annotations

import argparse
import posixpath
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

import markdown
import yaml
from bs4 import BeautifulSoup, NavigableString
from fpdf import FPDF
from fpdf.fonts import FontFace, TextStyle
from fpdf.html import HTML2FPDF

PDF_INTERNAL_HREF_PREFIX = "escmd-pdf:"
# fpdf2 runs full <a> start/end logic; we only override the resolved link id afterward.
_DECOY_EXTERNAL_HREF = "https://example.com/.escmd-pdf-internal-placeholder"
_PRE_T_MARGIN = 4 + 7 / 30
_PRE_B_MARGIN = 2 + 7 / 30

DEFAULT_CONFIG = "docs/pdf-config.yaml"  # escmd_docs/pdf-config.yaml for the user manual

# Broad emoji / pictograph ranges (reduces missing-glyph warnings in PDF).
_EMOJI_RE = re.compile(
    "["
    "\ufe0f"
    "\u2139"
    "\U00002300-\U000023FF"
    "\U0001F100-\U0001F2FF"
    "\U0001F300-\U0001FAFF"
    "\U00002700-\U000027BF"
    "\U00002600-\U000026FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "]",
    flags=re.UNICODE,
)


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parent.parent


def load_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def default_font_candidates() -> list[Path]:
    return [
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
        Path("/Library/Fonts/Arial Unicode.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/TTF/DejaVuSans.ttf"),
        Path("/usr/share/fonts/dejavu/DejaVuSans.ttf"),
    ]


def resolve_font(config: dict[str, Any], key: str, fallback: Path | None) -> Path:
    fonts = config.get("fonts") or {}
    override = fonts.get(key)
    if override:
        p = Path(override)
        if not p.is_absolute():
            p = repo_root_from_script() / p
        if p.is_file():
            return p
        sys.exit(f"Configured font not found ({key}): {p}")
    if fallback and fallback.is_file():
        return fallback
    for c in default_font_candidates():
        if c.is_file():
            return c
    sys.exit(
        "No Unicode TTF font found. Install DejaVu Sans or set "
        "fonts.sans (and optionally fonts.mono) in docs/pdf-config.yaml."
    )


def excluded(rel_docs: str, patterns: Iterable[str]) -> bool:
    p = PurePosixPath(rel_docs)
    for pat in patterns:
        if p.match(pat):
            return True
    return False


def collect_markdown_files(
    docs_dir: Path,
    include_globs: list[str],
    exclude_globs: list[str],
) -> list[Path]:
    seen: set[str] = set()
    out: list[Path] = []
    for pattern in include_globs:
        if any(ch in pattern for ch in "*?["):
            matches = sorted(docs_dir.glob(pattern))
        else:
            p = docs_dir / pattern
            matches = [p] if p.is_file() else []
        for path in matches:
            if path.suffix.lower() != ".md":
                continue
            rel = path.relative_to(docs_dir).as_posix()
            if excluded(rel, exclude_globs):
                continue
            if rel not in seen:
                seen.add(rel)
                out.append(path)
    return out


def strip_emoji_text(text: str) -> str:
    return _EMOJI_RE.sub("", text)


def render_title_page(
    pdf: FPDF,
    title: str,
    subtitle: str,
    source_count: int,
) -> None:
    pdf.add_page()
    pdf.set_font("DocSans", size=22)
    pdf.multi_cell(0, 12, title, align="C")
    pdf.ln(6)
    pdf.set_font("DocSans", size=12)
    pdf.multi_cell(0, 8, subtitle, align="C")
    pdf.ln(16)
    pdf.set_font("DocSans", size=10)
    pdf.multi_cell(
        0,
        6,
        f"This PDF combines {source_count} Markdown files from the docs/ tree.",
        align="C",
    )


def markdown_to_html(md_text: str, extensions: list[str]) -> str:
    return markdown.markdown(md_text, extensions=extensions)


class EscmdHTML2FPDF(HTML2FPDF):
    """
    fpdf2 treats <a href="123"> as a *page number*, not an existing link id.
    We encode internal targets as escmd-pdf:{id} and substitute the real link id
    after the normal <a> start handling (early return breaks the tag stack).
    """

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            attrs_dict = dict(attrs)
            href = (attrs_dict.get("href") or "").strip()
            if href.startswith(PDF_INTERNAL_HREF_PREFIX):
                lid = int(href[len(PDF_INTERNAL_HREF_PREFIX) :])
                decoy = [(k, v) for k, v in attrs if k != "href"]
                decoy.append(("href", _DECOY_EXTERNAL_HREF))
                super().handle_starttag(tag, decoy)
                self.href = lid
                return
        super().handle_starttag(tag, attrs)


class EscmdFPDF(FPDF):
    HTML2FPDF_CLASS = EscmdHTML2FPDF


def leading_spaces_to_nbsp(text: str) -> str:
    """
    fpdf2's HTML layout strips leading U+0020 at each wrapped line
    (skip_leading_spaces on TextColumns). YAML/JSON indentation must survive;
    NBSP is not stripped, so preserve each logical line's leading spaces that way.
    """
    lines = text.split("\n")
    out: list[str] = []
    for line in lines:
        n = len(line) - len(line.lstrip(" "))
        if n:
            out.append("\u00a0" * n + line[n:])
        else:
            out.append(line)
    return "\n".join(out)


def flatten_pre_code_blocks(soup: BeautifulSoup) -> None:
    """
    Markdown fenced blocks become <pre><code>...</code></pre>. Nested <code>
    confuses fpdf2's preformatted path; keep a single <pre> with plain text.
    """
    for pre in soup.find_all("pre"):
        code = pre.find("code", recursive=False)
        if not code:
            continue
        text = code.string
        if text is None:
            text = code.get_text()
        text = leading_spaces_to_nbsp(text)
        pre.clear()
        pre.append(NavigableString(text))


def rewrite_doc_links(
    soup: BeautifulSoup,
    source_rel: str,
    link_by_rel: dict[str, int],
) -> None:
    """Turn relative .md links into internal PDF links; keep http(s)/mailto."""
    for tag in soup.find_all("a"):
        href = (tag.get("href") or "").strip()
        if not href:
            tag.unwrap()
            continue
        if href.startswith("#"):
            tag.unwrap()
            continue
        if href.startswith(("http://", "https://", "mailto:")):
            continue
        path_only = href.split("#", 1)[0].strip()
        if not path_only:
            tag.unwrap()
            continue
        if not path_only.lower().endswith(".md"):
            continue
        base = posixpath.dirname(source_rel) or "."
        target = posixpath.normpath(posixpath.join(base, path_only))
        if target.startswith("../"):
            tag.unwrap()
            continue
        lid = link_by_rel.get(target)
        if lid is None:
            tag.unwrap()
            continue
        tag["href"] = f"{PDF_INTERNAL_HREF_PREFIX}{lid}"


def flatten_table_cells(soup: BeautifulSoup) -> None:
    """
    fpdf2 only allows a single text pass per <td>/<th>; nested <code>, <a>, etc.
    trigger NotImplementedError. Replace cell contents with plain text so real
    <table> layout is preserved.
    """
    for cell in soup.find_all(["td", "th"]):
        text = cell.get_text(separator=" ", strip=True)
        cell.clear()
        if text:
            cell.append(NavigableString(text))


def simplify_html_for_fpdf(
    html: str,
    source_rel: str,
    link_by_rel: dict[str, int],
) -> str:
    """
    - Flatten <pre><code> for reliable monospace blocks (configs, samples).
    - Flatten table cell markup to plain text so fpdf2 can render Markdown tables.
    - Map sibling .md links to internal PDF link ids; drop pure #fragments.
    """
    soup = BeautifulSoup(html, "html.parser")
    flatten_pre_code_blocks(soup)
    rewrite_doc_links(soup, source_rel, link_by_rel)
    flatten_table_cells(soup)
    return str(soup)


def build_pdf(
    config_path: Path,
    max_files: int | None,
    verbose: bool,
) -> Path:
    root = repo_root_from_script()
    cfg = load_config(config_path)

    docs_rel = cfg.get("docs_directory", "docs")
    docs_dir = (root / docs_rel).resolve()
    if not docs_dir.is_dir():
        sys.exit(f"docs directory not found: {docs_dir}")

    include_globs = cfg.get("include_globs") or []
    exclude_globs = cfg.get("exclude_globs") or []
    files = collect_markdown_files(docs_dir, include_globs, exclude_globs)
    if max_files is not None:
        files = files[: max(0, max_files)]

    if not files:
        sys.exit("No Markdown files matched include_globs / exclude_globs.")

    out_rel = cfg.get("output_path", "docs/build/escmd-documentation.pdf")
    out_path = (root / out_rel).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    sans_path = resolve_font(cfg, "sans", None)
    mono_path = resolve_font(cfg, "mono", sans_path)

    title = str(cfg.get("document_title") or "Documentation")
    subtitle = str(cfg.get("document_subtitle") or "")
    extensions = list(cfg.get("markdown_extensions") or ["fenced_code", "tables"])
    do_strip = bool(cfg.get("strip_emoji", False))

    pdf = EscmdFPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    for style in ("", "B", "I", "BI"):
        pdf.add_font("DocSans", style, str(sans_path))
        pdf.add_font("DocMono", style, str(mono_path))

    render_title_page(pdf, title, subtitle, len(files))

    link_by_rel: dict[str, int] = {}
    for path in files:
        rel_key = path.relative_to(docs_dir).as_posix()
        link_by_rel[rel_key] = pdf.add_link()

    mono_face = FontFace(family="DocMono", size_pt=9)
    tag_styles: dict[str, Any] = {
        "pre": TextStyle(
            t_margin=_PRE_T_MARGIN,
            b_margin=_PRE_B_MARGIN,
            font_family="DocMono",
            font_size_pt=9,
        ),
        "code": mono_face,
        "a": FontFace(color="#0000b0", emphasis="UNDERLINE"),
    }

    for i, path in enumerate(files):
        if verbose:
            print(path.relative_to(root), file=sys.stderr)
        raw = path.read_text(encoding="utf-8")
        if do_strip:
            raw = strip_emoji_text(raw)
        rel = path.relative_to(docs_dir).as_posix()
        pdf.add_page()
        pdf.set_link(link=link_by_rel[rel], y=0, x=0, page=-1)
        pdf.set_font("DocSans", size=11)
        pdf.set_font("DocSans", "B", 14)
        pdf.multi_cell(0, 10, rel)
        pdf.ln(2)
        pdf.set_font("DocSans", size=11)
        body = simplify_html_for_fpdf(
            markdown_to_html(raw, extensions),
            rel,
            link_by_rel,
        )
        pdf.write_html(body, tag_styles=tag_styles)

    pdf.output(str(out_path))
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a single PDF from docs/.")
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=None,
        help=f"path to YAML config (default: {DEFAULT_CONFIG} under repo root)",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="only process the first N files after ordering (for debugging)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="print each source path while building",
    )
    args = parser.parse_args()

    root = repo_root_from_script()
    cfg_path = args.config or (root / DEFAULT_CONFIG)
    if not cfg_path.is_file():
        sys.exit(f"Config not found: {cfg_path}")

    out = build_pdf(cfg_path, args.max_files, args.verbose)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
