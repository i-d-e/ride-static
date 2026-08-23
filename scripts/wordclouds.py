"""Generate a word cloud PNG for a RIDE review from its TEI source.

The site build calls this module automatically for review bundles. The
CLI remains available to regenerate a legacy review's committed thumbnail
under ``static/images/wordclouds/{review_id}.{png|jpg}``.

Ported from the legacy ``i-d-e/ride-scripts`` ``wordclouds/wordclouds.py``
(Ulrike Henny-Krahmer, GPLv3). The port keeps the legacy render
parameters (``background_color="white"``, ``prefer_horizontal=1.0``,
``collocations=False``, ``max_words=500``, ``min_font_size=4``,
``repeat=True``, silhouette mask) but adds a fixed ``random_state`` so
output is reproducible; the legacy output was stochastic.

The ``wordcloud`` library is an optional dependency, imported inside
``run()`` so the rest of the module (text extraction, stopword
selection) works and is testable without it.

Assets ship under ``scripts/wordcloud-assets/``:

    stopwords_{de,en,fr}.txt   fetched from the legacy repo
    cloud_mask.png             legacy silhouette mask (800x520)

Font: the repo ships no TTF, so the render falls back to the
``wordcloud`` library's bundled default font rather than introducing a
new font asset and its licence. Pass ``font_path`` to override.

Run:
    python scripts/wordclouds.py issues/1/reviews/carolingian_scholarship-tei.xml
    python scripts/wordclouds.py --review makingandknowing
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lxml import etree

try:
    from scripts._tei import TEI_NS, XML_ID_ATTR, normalize
except ModuleNotFoundError:  # Bare ``python scripts/wordclouds.py`` execution.
    from _tei import TEI_NS, XML_ID_ATTR, normalize

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = Path(__file__).resolve().parent / "wordcloud-assets"
FONTS_DIR = REPO_ROOT / "static" / "fonts"
DEFAULT_OUT_DIR = REPO_ROOT / "static" / "images" / "wordclouds"

# Fixed seed for a reproducible layout. The legacy script passed no
# random_state, so its output varied between runs; pinning it makes the
# committed image deterministic.
DEFAULT_SEED = 42

# Legacy default matplotlib colormap (see the legacy docstring example).
DEFAULT_COLORMAP = "hot"

_NS = {"tei": TEI_NS}


# --- pure extraction helpers (no wordcloud dependency) --------------------


def parse_tei(tei_path: Path) -> etree._ElementTree:
    """Parse a TEI review file into an lxml tree."""
    return etree.parse(str(tei_path))


def extract_review_id(tree: etree._ElementTree) -> str:
    """The review id is the root ``TEI/@xml:id`` (e.g. ``ride.1.1``)."""
    review_id = tree.getroot().get(XML_ID_ATTR)
    if not review_id:
        raise ValueError("TEI root carries no xml:id")
    return review_id


def extract_language(tree: etree._ElementTree) -> str:
    """First ``//tei:language/@ident`` (e.g. ``de``), '' if absent."""
    idents = tree.xpath("//tei:language/@ident", namespaces=_NS)
    return idents[0] if idents else ""


def extract_body_text(tree: etree._ElementTree) -> str:
    """All ``//tei:body//text()`` joined, lowercased, whitespace-collapsed.

    Mirrors the legacy extraction: newline-join the text nodes, lowercase,
    then collapse runs of whitespace to single spaces.
    """
    nodes = tree.xpath("//tei:body//text()", namespaces=_NS)
    return normalize("\n".join(nodes).lower())


def load_stopwords(lang: str, assets_dir: Path = ASSETS_DIR) -> set[str]:
    """Load the ``stopwords_{lang}.txt`` list bundled in ``assets_dir``.

    Returns an empty set for a language with no bundled list (e.g. ``it``,
    which the legacy repo never shipped). An empty custom set lets the
    ``wordcloud`` library apply its own built-in stopwords.
    """
    path = assets_dir / f"stopwords_{lang}.txt"
    if not path.exists():
        return set()
    lines = path.read_text(encoding="utf-8").splitlines()
    return {line.strip() for line in lines if line.strip()}


def _find_repo_font() -> str | None:
    """First TTF/OTF shipped under ``static/fonts/``, else None.

    None makes the ``wordcloud`` library use its bundled default font, so
    no new font asset or licence enters the repo. The repo currently
    ships no font; this hook picks one up automatically if one is added.
    """
    if not FONTS_DIR.is_dir():
        return None
    for pattern in ("*.ttf", "*.otf"):
        hits = sorted(FONTS_DIR.glob(pattern))
        if hits:
            return str(hits[0])
    return None


def _load_mask(assets_dir: Path):
    """Return the mask as a numpy array.

    Uses the bundled legacy ``cloud_mask.png`` when present; otherwise
    generates a simple elliptical silhouette so the render still works on
    a checkout without the asset. Imports numpy/PIL lazily (they arrive
    with the ``wordcloud`` dependency).
    """
    import numpy as np
    from PIL import Image

    mask_file = assets_dir / "cloud_mask.png"
    if mask_file.exists():
        return np.array(Image.open(mask_file))

    # Elliptical fallback: 255 = masked out (no words), 0 = fill area.
    width, height = 800, 520
    yy, xx = np.ogrid[:height, :width]
    cy, cx = height / 2, width / 2
    inside = ((xx - cx) / cx) ** 2 + ((yy - cy) / cy) ** 2 <= 1.0
    mask = np.full((height, width), 255, dtype=np.uint8)
    mask[inside] = 0
    return mask


# --- render ---------------------------------------------------------------


def run(
    tei_path: Path,
    out_dir: Path,
    *,
    seed: int = DEFAULT_SEED,
    colormap: str = DEFAULT_COLORMAP,
    assets_dir: Path = ASSETS_DIR,
    font_path: str | None = None,
) -> Path:
    """Render the word cloud for one review and write ``{review_id}.png``.

    Returns the written path. Raises ``RuntimeError`` with an actionable
    message when the optional ``wordcloud`` dependency is missing.
    """
    try:
        from wordcloud import WordCloud
    except ImportError as exc:  # pragma: no cover - exercised via skip
        raise RuntimeError(
            "The 'wordcloud' package is required to render word clouds. "
            "Install it with: pip install wordcloud"
        ) from exc

    tei_path = Path(tei_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    tree = parse_tei(tei_path)
    review_id = extract_review_id(tree)
    lang = extract_language(tree)
    text = extract_body_text(tree)
    stopwords = load_stopwords(lang, assets_dir)
    mask = _load_mask(assets_dir)

    if font_path is None:
        font_path = _find_repo_font()

    cloud = WordCloud(
        background_color="white",
        font_path=font_path,
        prefer_horizontal=1.0,
        colormap=colormap,
        mask=mask,
        stopwords=stopwords,
        collocations=False,
        max_words=500,
        min_font_size=4,
        repeat=True,
        random_state=seed,
    ).generate(text)

    out_path = out_dir / f"{review_id}.png"
    temp_path = out_path.with_suffix(".tmp.png")
    cloud.to_file(str(temp_path))
    temp_path.replace(out_path)
    return out_path


def _resolve_paths(args: argparse.Namespace) -> list[Path]:
    if args.review:
        from src._corpus import find_tei

        return [find_tei(args.review)]
    return [Path(p) for p in args.tei_paths]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate RIDE review word clouds.")
    parser.add_argument(
        "tei_paths",
        nargs="*",
        help="TEI review file paths to render.",
    )
    parser.add_argument(
        "--review",
        help="Review slug (e.g. 'makingandknowing') resolved via src._corpus.find_tei.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Output directory (default: static/images/wordclouds/).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"random_state for a reproducible layout (default: {DEFAULT_SEED}).",
    )
    parser.add_argument(
        "--colormap",
        default=DEFAULT_COLORMAP,
        help=f"matplotlib colormap (default: {DEFAULT_COLORMAP}).",
    )
    args = parser.parse_args(argv)

    # main() needs src._corpus for --review; add repo root to the path when
    # run as a bare script (scripts/ is already sys.path[0]).
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    paths = _resolve_paths(args)
    if not paths:
        parser.error("give at least one TEI path or --review SLUG")

    for tei_path in paths:
        out_path = run(
            tei_path,
            args.out_dir,
            seed=args.seed,
            colormap=args.colormap,
        )
        print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
