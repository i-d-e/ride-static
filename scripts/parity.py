"""Parity check: does the static site carry what the running RIDE site offers?

Regime: script pipeline (`scripts/`, run with ``uv run python scripts/parity.py``).

Data flow
---------
1. The live inventory comes from the running site itself: its sitemap index
   (``/sitemap.xml``) lists every WordPress page. Review pages
   (``/issues/issue-{N}/{slug}/``) are fetched and reduced to a
   :class:`ReviewRecord`; so are the static review pages, located through the
   static corpus dump (``/api/corpus.json``). Live and static reviews are
   joined by DOI, the one identifier both sides print and the persistent
   address external services use.
2. Each joined pair is compared per category: title, DOI, issue, citation
   (authors, year, issue, DOI), paragraph count and text after normalisation,
   figures (count and image file), notes, bibliography, tags, licence,
   downloads, factsheet answers.
3. Every live sitemap URL, every legacy tag URL seen on a live review, and
   the persistent addresses printed in the live OAI records are resolved on
   the static site, following its meta-refresh stubs.
4. One contract test per machine interface: OAI-PMH (live endpoint harvested
   over all resumption tokens against the static snapshot), the three feeds
   and their legacy paths, the sitemap, the corpus dump. Interfaces the static
   site deliberately or necessarily lacks are recorded with their live status.
5. ``report.json`` (machine-readable, every finding) and ``summary.md``
   (coverage and deviations per category) are written to ``--out``.

Courtesy and reproducibility: all requests go through
:class:`parity_fetch.CachedFetcher` (one request per second to the live site,
cache under ``inventory/_cache/parity/``, outside Git). ``--offline`` re-runs
from the cache alone. The static side is either the deployed site
(``--static-url``) or a local build directory (``--static-root``).

Sample: ``--sample`` checks the reviews in :data:`SAMPLE`, chosen so that each
feature the comparison measures occurs at least once (see the reasons there);
``--full`` checks every review the live sitemap lists.

Every number in the report is counted by this script from the fetched pages.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

from lxml import etree, html

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parity_fetch import CachedFetcher, Response  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
LIVE_BASE = "https://ride.i-d-e.de"
STATIC_BASE = "https://i-d-e.github.io/ride-static"
CACHE_DIR = REPO_ROOT / "inventory" / "_cache" / "parity"
OUT_DIR = REPO_ROOT / "inventory" / "parity"

# The fixed sample, keyed by DOI. Each review is in the sample for a feature
# the comparison has to see at least once; together they cover all of them.
SAMPLE: dict[str, str] = {
    "10.18716/ride.a.1.4": "figures in running text, English, single reviewer (nietzschesource)",
    "10.18716/ride.a.1.1": "footnotes, German text, TEI file stem differs from WordPress slug",
    "10.18716/ride.a.3.1": "post-publication amendment (melville)",
    "10.18716/ride.a.9.5": "figure files spelled .PNG in the picture checkout (corlec)",
    "10.18716/ride.a.6.9": "text-collection criteria, figure preserved from the old host",
    "10.18716/ride.a.14.5": "compound review with two questionnaires (carlyle-addams)",
    "10.18716/ride.a.19.1": "tools questionnaire, many notes, rolling issue (tei-publisher)",
    "10.18716/ride.a.13.5": "picture directory alias (patrick-confessio)",
    "10.18716/ride.a.22.1": "newest review, current rolling issue (arendt)",
}

OAI_NS = {"o": "http://www.openarchives.org/OAI/2.0/", "dc": "http://purl.org/dc/elements/1.1/"}
MONTHS = {
    m: i
    for i, m in enumerate(
        ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1
    )
}


# Normalisation


def tokens(text: str) -> list[str]:
    """Word tokens after Unicode compatibility folding and case folding.

    Punctuation, quotes, dashes and whitespace drop out, so typographic
    variants (curly versus straight quotes, en dash versus hyphen) compare
    equal, while a lost space between two words ("theNietzsche") does not.
    """
    folded = unicodedata.normalize("NFKC", text).casefold()
    return re.findall(r"\w+", folded)


def same_text(a: str, b: str) -> bool:
    return tokens(a) == tokens(b)


def first_difference(a: str, b: str, width: int = 6) -> str:
    """Short token context around the first divergence, for the report."""
    ta, tb = tokens(a), tokens(b)
    i = 0
    while i < min(len(ta), len(tb)) and ta[i] == tb[i]:
        i += 1
    lo = max(0, i - width)
    return f"live: {' '.join(ta[lo : i + width])!r} | static: {' '.join(tb[lo : i + width])!r}"


def norm_url(url: str) -> str:
    """Scheme-, slash- and case-insensitive form of a URL for equality checks."""
    parts = urlsplit(url.strip())
    path = unquote(parts.path).rstrip("/")
    return f"{parts.netloc.lower()}{path}".lower()


def norm_date(text: str) -> str:
    """'Jun 2014' or '2014-06' or '2014-06-01' -> '2014-06'."""
    text = text.strip()
    m = re.match(r"(\d{4})-(\d{2})", text)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m = re.match(r"([A-Za-z]{3})[a-z]*\.? (\d{4})", text)
    if m and m.group(1).lower() in MONTHS:
        return f"{m.group(2)}-{MONTHS[m.group(1).lower()]:02d}"
    return text


def text_of(el: html.HtmlElement | None) -> str:
    return " ".join(el.text_content().split()) if el is not None else ""


# Extraction


@dataclass
class ReviewRecord:
    """What one review page shows, reduced to comparable fields."""

    url: str
    title: str = ""
    doi: str = ""
    published: str = ""
    citation: str = ""
    paragraphs: dict[str, str] = field(default_factory=dict)
    figures: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    bibliography: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    tag_urls: list[str] = field(default_factory=list)
    licence: str = ""
    downloads: dict[str, str] = field(default_factory=dict)
    head: dict[str, bool] = field(default_factory=dict)


def _parse(body: bytes) -> html.HtmlElement:
    return html.fromstring(body or b"<html/>")


def _strip(root: html.HtmlElement, xpath: str) -> None:
    for el in root.xpath(xpath):
        el.drop_tree()


def _head_features(root: html.HtmlElement) -> dict[str, bool]:
    """Machine-facing metadata in the page head, recorded as presence flags."""
    head = root.find("head")
    if head is None:
        return {}

    def has(xpath: str) -> bool:
        return bool(head.xpath(xpath))

    return {
        "title": bool(text_of(head.find("title"))),
        "canonical": has("link[@rel='canonical']"),
        "feed_autodiscovery": has(
            "link[@rel='alternate'][contains(@type,'rss') or contains(@type,'atom')]"
        ),
        "description": has("meta[@name='description']"),
        "open_graph": has("meta[starts-with(@property,'og:')]"),
        "json_ld": bool(root.xpath("//script[@type='application/ld+json']")),
        "highwire_citation": has("meta[starts-with(@name,'citation_')]"),
        "dublin_core": has("meta[starts-with(@name,'DC.') or starts-with(@name,'dc.')]"),
    }


def extract_live_review(url: str, body: bytes) -> ReviewRecord:
    """Read a WordPress review page of ride.i-d-e.de."""
    root = _parse(body)
    rec = ReviewRecord(url=url, head=_head_features(root))
    rec.title = text_of(next(iter(root.xpath("//h1[contains(@class,'post-title')]")), None))
    aside = next(iter(root.xpath("//aside[@id='secondary']")), None)
    aside_text = text_of(aside)
    m = re.search(r"DOI:\s*(10\.\S+?)(?:\s|<|$)", aside_text + " ")
    rec.doi = m.group(1).rstrip(".") if m else ""
    m = re.search(r"Published:\s*([A-Za-z]+\.? \d{4}|\d{4}(?:-\d{2})?)", aside_text)
    rec.published = norm_date(m.group(1)) if m else ""
    cit = root.xpath("//*[@id='cit_suggestion']")
    rec.citation = text_of(cit[0]) if cit else ""
    entry = next(iter(root.xpath("//div[contains(@class,'post-entry')]")), None)
    if entry is None:
        return rec
    # Figures appear as <img> or, on some pages, only as a lightbox link onto
    # the picture file; both point into a ``pictures/`` directory.
    refs = entry.xpath(".//div[@class='text']//img/@src | .//div[@class='text']//a/@href")
    rec.figures = list(
        dict.fromkeys(Path(urlsplit(r).path).name for r in refs if "/pictures/" in r)
    )
    notes_div = entry.xpath(".//div[@class='notes']")
    rec.notes = live_notes(notes_div[0]) if notes_div else []
    rec.bibliography = [
        text_of(p) for p in entry.xpath(".//div[@class='bibl']/p | .//div[@class='bibl']//li")
    ]
    # Note calls, inline figures and paragraph numbers are apparatus, not
    # paragraph text. Some WordPress pages nest a figure inside a paragraph.
    _strip(entry, ".//sup[a[starts-with(@href,'#ftn')]]")
    _strip(entry, ".//div[@class='text']//figure")
    for span in entry.xpath(".//span[@class='paracount']"):
        anchor = span.xpath("./a/@href")
        number = text_of(span)
        par = span.getparent()
        span.drop_tree()
        if par is None:
            continue
        if anchor:
            key = anchor[0].lstrip("#")
        elif (par.get("id") or "").startswith("p"):
            key = par.get("id")
        else:
            key = f"p{number}"
        rec.paragraphs[key] = text_of(par)
    if aside is not None:
        rec.tags = [text_of(a) for a in aside.xpath(".//a[@rel='tag']")]
        rec.tag_urls = [a.get("href") for a in aside.xpath(".//a[@rel='tag']")]
        lic = aside.xpath(".//a[contains(@href,'creativecommons.org')]/@href")
        rec.licence = lic[0] if lic else ""
        for href in aside.xpath(".//a/@href"):
            low = href.lower()
            if low.endswith(".xml") and "github" in low:
                rec.downloads["xml"] = href
            elif low.endswith(".pdf"):
                rec.downloads["pdf"] = href
    return rec


def live_notes(notes_div: html.HtmlElement) -> list[str]:
    """Split the live notes block at each ``id="ftnN"`` marker.

    WordPress renders notes in two shapes (one paragraph per note, or all
    notes in one paragraph separated by ``<br>``); the note markers carry
    ``id="ftnN"`` in both, so splitting the serialised block there yields one
    chunk per note either way.
    """
    raw = html.tostring(notes_div, encoding="unicode")
    starts = [m.start() for m in re.finditer(r'<[a-z]+\b[^>]*\bid="ftn\d+"', raw)]
    chunks = [raw[a:b] for a, b in zip(starts, starts[1:] + [len(raw)])]
    return [text_of(html.fragment_fromstring(c, create_parent="div")) for c in chunks]


def extract_static_review(url: str, body: bytes) -> ReviewRecord:
    """Read a review page of the static build."""
    root = _parse(body)
    rec = ReviewRecord(url=url, head=_head_features(root))
    rec.title = text_of(next(iter(root.xpath("//h1[contains(@class,'ride-review__title')]")), None))
    doi = root.xpath("//dl[contains(@class,'ride-meta')]//a[starts-with(@href,'https://doi.org/')]")
    rec.doi = text_of(doi[0]) if doi else ""
    meta = root.xpath("//dl[contains(@class,'ride-meta')]/dt[normalize-space()='Published']")
    if meta:
        dd = meta[0].getnext()
        rec.published = norm_date(text_of(dd))
    cit = root.xpath(
        "//*[contains(@class,'ride-cite__suggestion') and not(contains(@class,'note'))]"
    )
    rec.citation = text_of(cit[0]) if cit else ""
    body_el = next(iter(root.xpath("//div[contains(@class,'ride-review__body')]")), None)
    if body_el is not None:
        rec.figures = [
            Path(urlsplit(src).path).name for src in body_el.xpath(".//figure//img/@src")
        ]
        _strip(body_el, ".//sup[contains(@class,'ride-note')]")
        _strip(
            body_el, ".//*[contains(@class,'ride-paragraph__num') or contains(@class,'ride-copy')]"
        )
        # A TEI paragraph split by a figure renders as a numbered chunk plus an
        # unnumbered continuation; WordPress keeps the figure inside one
        # paragraph, so the continuation is joined back. Text after a list
        # stays apart, because WordPress ends the numbered paragraph there too.
        last = None
        for p in body_el.xpath(".//p[contains(concat(' ', @class, ' '), ' ride-paragraph ')]"):
            prev = p.getprevious()
            if p.get("id"):
                last = p.get("id")
                rec.paragraphs[last] = text_of(p)
            elif last is not None and prev is not None and prev.tag == "figure":
                rec.paragraphs[last] = f"{rec.paragraphs[last]} {text_of(p)}".strip()
    for li in root.xpath("//section[contains(@class,'ride-apparate__panel--notes')]//li"):
        _strip(li, ".//*[contains(@class,'ride-note__back')]")
        rec.notes.append(text_of(li))
    rec.bibliography = [
        text_of(li)
        for li in root.xpath("//section[contains(@class,'ride-apparate__panel--refs')]//li")
    ]
    tag_links = [
        a
        for a in root.xpath(
            "//a[contains(@href,'/tags/') and not(substring-after(@href,'/tags/')='')]"
        )
        if urlsplit(a.get("href")).netloc in ("", urlsplit(url).netloc)
    ]
    rec.tags = [text_of(a) for a in tag_links]
    rec.tag_urls = [a.get("href") for a in tag_links]
    lic = root.xpath("//*[contains(@class,'ride-review__licence')]//a/@href")
    rec.licence = lic[0] if lic else ""
    return rec


def extract_live_factsheet(body: bytes) -> list[tuple[str, str]]:
    """(criterion id from the K-ref, answer) for every row that cites a criterion.

    A list, because several questions can cite the same criterion.
    """
    root = _parse(body)
    out: list[tuple[str, str]] = []
    for row in root.xpath("//table[contains(@class,'factsheet')]//tr[.//a[contains(@href,'#K')]]"):
        cells = row.xpath("./td")
        last = cells[-1] if cells else None
        answer = ""
        if last is not None:
            alts = last.xpath(".//img/@alt")
            answer = " ".join(alts) if alts else text_of(last)
        out.extend((kid, answer) for kid in _criteria_ids(row))
    return out


def extract_static_factsheet(body: bytes) -> list[tuple[str, str]]:
    root = _parse(body)
    out: list[tuple[str, str]] = []
    for q in root.xpath(
        "//div[contains(concat(' ', @class, ' '), ' ride-question ')][.//a[contains(@href,'#K')]]"
    ):
        ans = q.xpath(".//*[contains(@class,'ride-question__answer')]")
        answer = text_of(ans[0]) if ans else ""
        out.extend((kid, answer) for kid in _criteria_ids(q))
    return out


def _criteria_ids(el: html.HtmlElement) -> list[str]:
    """Criterion ids (K1.2 …) cited by the links of one question."""
    ids: list[str] = []
    for href in el.xpath(".//a[contains(@href,'#K')]/@href"):
        ids.extend(re.findall(r"#(K[\w.]*\w)", href))
    return ids


def answer_key(answer: str) -> str:
    """Comparable answer: yes/no/n.a. and free text folded to tokens."""
    toks = tokens(answer)
    if toks[:1] == ["answer"]:  # visually hidden label in the static markup
        toks = toks[1:]
    if toks[:1] in (["yes"], ["no"]):
        return toks[0]
    if toks[:2] == ["not", "applicable"]:
        return "not applicable"
    return " ".join(toks)


# Static site access


class StaticSite:
    """The static site, either deployed (fetched) or a local build directory."""

    def __init__(self, base_url: str, fetcher: CachedFetcher, root: Path | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.base_path = urlsplit(self.base_url).path.rstrip("/")
        self.fetcher = fetcher
        self.root = root

    def path_of(self, url: str) -> str:
        """Site-relative path ('/issues/1/x/') for an absolute or prefixed URL."""
        parts = urlsplit(url)
        path = parts.path
        if self.base_path and path.startswith(self.base_path + "/"):
            path = path[len(self.base_path) :]
        elif self.base_path and path == self.base_path:
            path = "/"
        return path or "/"

    def url_of(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def get(self, path: str) -> Response:
        if self.root is None:
            return self.fetcher.get(self.url_of(path))
        rel = unquote(path).lstrip("/")
        target = self.root / rel
        if path.endswith("/") or target.is_dir():
            target = target / "index.html"
        if not target.is_file():
            return Response(self.url_of(path), 404, {}, b"", True)
        ctype = {".xml": "application/xml", ".json": "application/json", ".pdf": "application/pdf"}
        return Response(
            self.url_of(path),
            200,
            {"content-type": ctype.get(target.suffix, "text/html")},
            target.read_bytes(),
            True,
        )

    def status(self, path: str) -> int:
        """Existence check without keeping the body (downloads such as PDFs)."""
        if self.root is None:
            return self.fetcher.head(self.url_of(path))
        return self.get(path).status

    def resolve(self, path: str, max_hops: int = 4) -> tuple[Response, list[str]]:
        """Follow meta-refresh stubs; return the final response and visited paths."""
        hops: list[str] = []
        resp = self.get(path)
        while resp.status == 200 and len(hops) < max_hops:
            target = meta_refresh_target(resp.body)
            if not target:
                break
            target_path = self.path_of(urljoin(self.url_of(path), target))
            hops.append(target_path)
            path = target_path.split("#", 1)[0]
            resp = self.get(path)
        return resp, hops


def meta_refresh_target(body: bytes) -> str | None:
    if b"http-equiv" not in body[:4000]:
        return None
    m = re.search(
        rb'<meta[^>]+http-equiv=["\']refresh["\'][^>]+content=["\']\s*\d+\s*;\s*url=([^"\']+)',
        body[:4000],
        re.I,
    )
    return m.group(1).decode("utf-8").strip() if m else None


# Comparison


@dataclass
class Finding:
    category: str
    subject: str
    status: str  # equal | differs | missing_static | missing_live | deliberate | info
    detail: str = ""


def compare_reviews(
    live: ReviewRecord, static: ReviewRecord, issue_live: str, issue_static: str
) -> list[Finding]:
    """All field comparisons for one DOI-joined review pair."""
    s = live.doi
    out: list[Finding] = []

    def add(cat: str, ok: bool, detail: str = "") -> None:
        out.append(Finding(cat, s, "equal" if ok else "differs", "" if ok else detail))

    add("title", same_text(live.title, static.title), first_difference(live.title, static.title))
    add("doi", live.doi.lower() == static.doi.lower(), f"{live.doi} | {static.doi}")
    add("issue", issue_live == issue_static, f"{issue_live} | {issue_static}")
    add("published", live.published == static.published, f"{live.published} | {static.published}")
    la, sa = citation_authors(live.citation), citation_authors(static.citation)
    add("authors", la == sa, f"{la} | {sa}")
    # Paragraphs: same set of numbered paragraphs, same text per paragraph.
    lp, sp = live.paragraphs, static.paragraphs
    add(
        "paragraph_count",
        len(lp) == len(sp),
        f"{len(lp)} | {len(sp)}; only live: {sorted(set(lp) - set(sp))[:8]}, "
        f"only static: {sorted(set(sp) - set(lp))[:8]}",
    )
    differing = [pid for pid in lp if pid in sp and not same_text(lp[pid], sp[pid])]
    add(
        "paragraph_text",
        not differing,
        f"{len(differing)} of {len(set(lp) & set(sp))} paragraphs differ; first {differing[:1]}: "
        + (first_difference(lp[differing[0]], sp[differing[0]]) if differing else ""),
    )
    lf = Counter(f.lower() for f in live.figures)
    sf = Counter(f.lower() for f in static.figures)
    add("figures", lf == sf, f"live {sorted(lf.elements())} | static {sorted(sf.elements())}")
    add(
        "notes_count",
        len(live.notes) == len(static.notes),
        f"{len(live.notes)} | {len(static.notes)}",
    )
    if live.notes and len(live.notes) == len(static.notes):
        diff = [i for i, (a, b) in enumerate(zip(live.notes, static.notes)) if not same_note(a, b)]
        add(
            "notes_text",
            not diff,
            f"{len(diff)} differ; first: "
            + (first_difference(live.notes[diff[0]], static.notes[diff[0]]) if diff else ""),
        )
    add(
        "bibliography_count",
        len(live.bibliography) == len(static.bibliography),
        f"{len(live.bibliography)} | {len(static.bibliography)}",
    )
    if live.bibliography and len(live.bibliography) == len(static.bibliography):
        lb = sorted(" ".join(tokens(b)) for b in live.bibliography)
        sb = sorted(" ".join(tokens(b)) for b in static.bibliography)
        diff = [i for i, (a, b) in enumerate(zip(lb, sb)) if a != b]
        add(
            "bibliography_text",
            not diff,
            f"{len(diff)} differ; first: "
            + (f"live {lb[diff[0]][:90]!r} | static {sb[diff[0]][:90]!r}" if diff else ""),
        )
    lt = sorted({" ".join(tokens(t)) for t in live.tags})
    st = sorted({" ".join(tokens(t)) for t in static.tags})
    add(
        "tags",
        lt == st,
        f"only live {sorted(set(lt) - set(st))} | only static {sorted(set(st) - set(lt))}",
    )
    add(
        "licence",
        norm_url(live.licence) == norm_url(static.licence),
        f"{live.licence} | {static.licence}",
    )
    return out


def same_note(live: str, static: str) -> bool:
    """Live notes start with their number; the static list numbers by position."""
    lt = tokens(live)
    if lt and lt[0].isdigit():
        lt = lt[1:]
    return lt == tokens(static)


def citation_authors(citation: str) -> list[str]:
    """Author part of a citation suggestion ('Surname, Forename (Year).')."""
    m = re.match(r"\s*(.+?)\s*\(\d{4}\)", citation)
    if not m:
        return []
    # A bag of name tokens: the live box writes later authors forename first
    # ("Crawford, Kendal and Michelle Levy"), the static one surname first.
    return sorted(t for t in tokens(m.group(1)) if t != "and")


# Live inventory


REVIEW_RE = re.compile(r"^/issues/issue-(\d+)/([^/]+)/$")
FACTSHEET_RE = re.compile(r"^/issues/issue-(\d+)/([^/]+)/factsheet/$")


def live_sitemap_urls(fetcher: CachedFetcher) -> list[str]:
    index = fetcher.get(f"{LIVE_BASE}/sitemap.xml")
    urls: list[str] = []
    for loc in re.findall(rb"<loc>(.*?)</loc>", index.body):
        child = fetcher.get(loc.decode())
        urls.extend(u.decode() for u in re.findall(rb"<loc>(.*?)</loc>", child.body))
    return urls


def harvest_oai(fetcher: CachedFetcher, verb: str, prefix: str) -> tuple[list[etree._Element], int]:
    """All records or headers of a live list verb, following resumption tokens."""
    items: list[etree._Element] = []
    url = f"{LIVE_BASE}/apis/oai?verb={verb}&metadataPrefix={prefix}"
    pages = 0
    while url and pages < 100:
        pages += 1
        resp = fetcher.get(url)
        if resp.status != 200:
            break
        root = etree.fromstring(resp.body)
        tag = "o:record" if verb == "ListRecords" else "o:header"
        items.extend(root.findall(f".//o:{verb}/{tag}", OAI_NS))
        token = root.findtext(f".//o:{verb}/o:resumptionToken", namespaces=OAI_NS)
        url = f"{LIVE_BASE}/apis/oai?verb={verb}&resumptionToken={token}" if token else ""
    return items, pages


# Runner


@dataclass
class Report:
    started: str
    mode: str
    static_source: str
    findings: list[Finding] = field(default_factory=list)
    inventory: dict = field(default_factory=dict)
    legacy_paths: dict[str, list[str]] = field(default_factory=dict)
    legacy_tags: dict[str, str] = field(default_factory=dict)

    def add(self, *items: Finding) -> None:
        self.findings.extend(items)


def run(
    fetcher: CachedFetcher,
    static: StaticSite,
    sample: bool,
    static_fetch_label: str,
) -> Report:
    report = Report(
        started=datetime.now(UTC).isoformat(timespec="seconds"),
        mode="sample" if sample else "full",
        static_source=static_fetch_label,
    )
    urls = live_sitemap_urls(fetcher)
    paths = [urlsplit(u).path for u in urls]
    review_paths = [p for p in paths if REVIEW_RE.match(p)]
    report.inventory["live_sitemap_urls"] = len(urls)
    report.inventory["live_review_pages"] = len(review_paths)
    report.inventory["live_factsheet_pages"] = sum(1 for p in paths if FACTSHEET_RE.match(p))

    corpus_resp = static.get("/api/corpus.json")
    corpus = json.loads(corpus_resp.body) if corpus_resp.status == 200 else {"reviews": []}
    by_doi = {r["doi"].lower(): r for r in corpus["reviews"] if r.get("doi")}
    report.inventory["static_reviews_in_corpus_dump"] = len(by_doi)

    # Reviews: fetch live pages, join by DOI, compare.
    live_records: dict[str, tuple[str, ReviewRecord]] = {}
    for path in review_paths:
        issue = REVIEW_RE.match(path).group(1)
        resp = fetcher.get(f"{LIVE_BASE}{path}")
        rec = extract_live_review(f"{LIVE_BASE}{path}", resp.body)
        if not rec.doi:
            report.add(Finding("review_join", path, "info", "live page carries no DOI"))
            continue
        if sample and rec.doi.lower() not in {d.lower() for d in SAMPLE}:
            continue
        live_records[rec.doi.lower()] = (issue, rec)
        for label, href in zip(rec.tags, rec.tag_urls):
            report.legacy_tags[urlsplit(href).path.strip("/")] = label
    expected = {}  # legacy path -> expected static path, for the URL check
    head_live: Counter = Counter()
    head_static: Counter = Counter()
    for doi, (issue, rec) in sorted(live_records.items()):
        entry = by_doi.get(doi)
        legacy = urlsplit(rec.url).path
        if entry is None:
            report.add(Finding("review_join", doi, "missing_static", f"{rec.title} ({legacy})"))
            continue
        target = f"/issues/{entry['issue']}/{entry['id']}/"
        report.legacy_paths.setdefault(doi, []).append(legacy)
        expected[legacy] = target
        expected[f"{legacy}factsheet/"] = f"{target}factsheet/"
        sresp = static.get(target)
        if sresp.status != 200:
            report.add(Finding("review_join", doi, "missing_static", f"{target} -> {sresp.status}"))
            continue
        srec = extract_static_review(static.url_of(target), sresp.body)
        report.add(Finding("review_join", doi, "equal", f"{legacy} -> {target}"))
        report.add(*compare_reviews(rec, srec, issue, str(entry["issue"])))
        head_live.update(k for k, v in rec.head.items() if v)
        head_static.update(k for k, v in srec.head.items() if v)
        # Downloads: the static TEI and PDF must be reachable.
        for kind in ("xml", "pdf"):
            want = f"{target}{entry['id']}.{kind}"
            status = static.status(want)
            ok = status == 200
            report.add(
                Finding(
                    f"download_{kind}",
                    doi,
                    "equal" if ok else "missing_static",
                    f"{want} -> {status}",
                )
            )
        # Factsheet answers.
        lfs = extract_live_factsheet(fetcher.get(f"{LIVE_BASE}{legacy}factsheet/").body)
        sfs = extract_static_factsheet(static.get(f"{target}factsheet/").body)
        if lfs or sfs:
            lc = Counter((k, answer_key(v)) for k, v in lfs)
            sc = Counter((k, answer_key(v)) for k, v in sfs)
            only_live, only_static = sorted((lc - sc).elements()), sorted((sc - lc).elements())
            report.add(
                Finding(
                    "factsheet",
                    doi,
                    "equal" if lc == sc else "differs",
                    f"{len(lfs)} live answers, {len(sfs)} static; only live {only_live[:5]}; "
                    f"only static {only_static[:5]}"
                    if lc != sc
                    else "",
                )
            )
        for url in rec.tag_urls:
            expected.setdefault(urlsplit(url).path, "")
    static_dois = set(by_doi)
    if not sample:
        for doi in sorted(static_dois - set(live_records)):
            entry = by_doi[doi]
            report.add(
                Finding("review_join", doi, "missing_live", f"{entry['id']} {entry['title'][:60]}")
            )
    report.inventory["head_metadata_live"] = dict(head_live)
    report.inventory["head_metadata_static"] = dict(head_static)
    report.inventory["reviews_compared"] = sum(
        1 for f in report.findings if f.category == "review_join" and f.status == "equal"
    )

    # URLs: every live sitemap URL (full mode) or the sample's URLs, plus tag URLs.
    check_paths = paths if not sample else sorted(expected)
    for path in sorted(set(check_paths) | set(expected)):
        report.add(check_url(static, path, expected.get(path, "")))

    report.add(*check_interfaces(fetcher, static, sample))
    return report


def check_url(static: StaticSite, legacy_path: str, expected: str) -> Finding:
    cat = "url_tag" if legacy_path.startswith("/tag/") else "url"
    resp, hops = static.resolve(legacy_path)
    final = hops[-1] if hops else legacy_path
    final_path = final.split("#", 1)[0]
    if resp.status != 200:
        return Finding(cat, legacy_path, "missing_static", f"{resp.status} via {hops}")
    if expected and final_path != expected:
        return Finding(cat, legacy_path, "differs", f"lands on {final}, expected {expected}")
    how = "same path" if not hops else f"redirect -> {final}"
    return Finding(cat, legacy_path, "equal", how)


def check_interfaces(fetcher: CachedFetcher, static: StaticSite, sample: bool) -> list[Finding]:
    out: list[Finding] = []
    # OAI-PMH: identifiers, formats, records.
    live_headers, pages = harvest_oai(fetcher, "ListIdentifiers", "oai_dc")
    live_ids = {h.findtext("o:identifier", namespaces=OAI_NS) for h in live_headers}
    sresp = static.get("/oai/list-identifiers.xml")
    static_ids_raw: set[str] = set()
    if sresp.status == 200:
        sroot = etree.fromstring(sresp.body)
        static_ids_raw = {
            h.findtext("o:identifier", namespaces=OAI_NS)
            for h in sroot.iter(f"{{{OAI_NS['o']}}}header")
        }
    strip = {i.rsplit(":", 1)[-1]: i for i in static_ids_raw}
    out.append(
        Finding(
            "oai_identifiers",
            "ListIdentifiers oai_dc",
            "equal" if live_ids == static_ids_raw else "differs",
            f"live {len(live_ids)} ids over {pages} pages; static {len(static_ids_raw)}; "
            f"same local part {len(live_ids & set(strip))}; only live {sorted(live_ids - set(strip))[:10]}; "
            f"only static {sorted(set(strip) - live_ids)[:10]}; identifier form live "
            f"{next(iter(sorted(live_ids)), '')!r} static {next(iter(sorted(static_ids_raw)), '')!r}",
        )
    )
    for local in sorted(live_ids & set(strip))[: (3 if sample else None)]:
        status = static.get(f"/oai/records/{local}.xml").status
        out.append(
            Finding(
                "oai_getrecord", local, "equal" if status == 200 else "missing_static", str(status)
            )
        )
    fmt_live = fetcher.get(f"{LIVE_BASE}/apis/oai?verb=ListMetadataFormats")
    fmt_static = static.get("/oai/list-metadata-formats.xml")
    lf = set(re.findall(rb"<metadataPrefix>([^<]+)<", fmt_live.body))
    sf = set(re.findall(rb"<metadataPrefix>([^<]+)<", fmt_static.body))
    out.append(
        Finding(
            "oai_formats",
            "ListMetadataFormats",
            "equal" if lf == sf else "differs",
            f"live {sorted(x.decode() for x in lf)} | static {sorted(x.decode() for x in sf)}",
        )
    )
    # Records: the persistent address printed in each live record must resolve statically.
    live_records, _ = harvest_oai(fetcher, "ListRecords", "oai_dc")
    for rec in live_records[: (5 if sample else None)]:
        ident = rec.findtext(".//o:header/o:identifier", namespaces=OAI_NS)
        for dc_id in rec.findall(".//dc:identifier", OAI_NS):
            value = (dc_id.text or "").strip()
            if "ride.i-d-e.de/issues/" in value:
                path = urlsplit(value).path
                path = path if path.endswith("/") else path + "/"
                f = check_url(static, path, "")
                out.append(Finding("oai_record_url", ident, f.status, f"{value}: {f.detail}"))
    # Verb-routed protocol requests cannot be served from files.
    out.append(
        Finding(
            "oai_protocol",
            "/apis/oai?verb=…",
            "missing_static",
            "query-string requests need a request-handling component (knowledge/oai-pmh-statisch.md)",
        )
    )
    # Feeds: legacy paths and .xml endpoints parse and point at existing pages.
    for legacy, xml_path, kind in (
        ("/feed/", "/feed/rss.xml", "rss"),
        ("/feed/atom/", "/feed/atom.xml", "feed"),
        ("/feed/rdf/", "/feed/rdf.xml", "RDF"),
    ):
        live = fetcher.get(f"{LIVE_BASE}{legacy}")
        for path in (legacy, xml_path):
            resp = static.get(path)
            if resp.status != 200:
                out.append(Finding("feed", path, "missing_static", str(resp.status)))
                continue
            try:
                root = etree.fromstring(resp.body)
            except etree.XMLSyntaxError as err:
                out.append(Finding("feed", path, "differs", f"not XML: {err}"))
                continue
            links = [
                el.get("href") or (el.text or "")
                for el in root.iter()
                if isinstance(el.tag, str) and etree.QName(el).localname == "link"
            ]
            entry_links = [lk for lk in links if "/issues/" in lk]
            broken = [
                lk for lk in entry_links if static.resolve(static.path_of(lk))[0].status != 200
            ]
            ok = etree.QName(root).localname == kind and entry_links and not broken
            out.append(
                Finding(
                    "feed",
                    path,
                    "equal" if ok else "differs",
                    f"root {etree.QName(root).localname}, {len(entry_links)} entry links, broken {broken[:3]}; "
                    f"live {legacy} status {live.status} {live.content_type}",
                )
            )
    # Sitemap: present, every location resolves on the static site.
    sm = static.get("/sitemap.xml")
    locs = [x.decode() for x in re.findall(rb"<loc>(.*?)</loc>", sm.body)]
    broken = [loc for loc in locs if static.get(static.path_of(loc)).status != 200]
    out.append(
        Finding(
            "sitemap",
            "/sitemap.xml",
            "equal" if sm.status == 200 and locs and not broken else "differs",
            f"{len(locs)} locations, unresolved {broken[:5]}",
        )
    )
    out.extend(check_aggregations(fetcher, static))
    # Interfaces the static site does not reproduce, with live evidence.
    for path, reason in (
        ("/comments/feed/", "comments are not part of the journal; no static counterpart"),
        (
            "/wp-json/",
            "WordPress REST API; corpus dump /api/corpus.json is the static data interface",
        ),
        ("/?s=nietzsche", "WordPress search by query string; static search is Pagefind"),
        (
            "/?p=19",
            "WordPress shortlink by post id; query strings are not routable on GitHub Pages",
        ),
        ("/apis/oai?verb=ListRecords&metadataPrefix=oai_marcxml", "MARCXML records"),
        ("/apis/oai?verb=ListRecords&metadataPrefix=oai_doajxml", "DOAJ article XML records"),
    ):
        live = fetcher.get(f"{LIVE_BASE}{path}")
        out.append(Finding("interface_not_static", path, "info", f"live {live.status}: {reason}"))
    return out


def check_aggregations(fetcher: CachedFetcher, static: StaticSite) -> list[Finding]:
    """Entry counts of the listing pages the live site embeds from eXist.

    The WordPress pages for reviewed resources, the reviewer list and the
    charts carry an ``<iframe>`` onto an XQuery app on exist.i-d-e.de; the
    iframe source is read from the WordPress page, then its entries counted.
    """
    out: list[Finding] = []
    pairs = (
        (
            "/data/reviewed-resources/",
            "/resources/",
            "//p[a[@target='_parent']]",
            "//tr[td]",
        ),
        (
            "/reviewers/list-of-reviewers/",
            "/reviewers/",
            "//p[.//a[@target='_parent']]",
            "//li[contains(@class,'ride-reviewer-list__entry')]",
        ),
    )
    for live_path, static_path, live_xpath, static_xpath in pairs:
        page = _parse(fetcher.get(f"{LIVE_BASE}{live_path}").body)
        srcs = page.xpath("//iframe/@src")
        live_n = None
        if srcs:
            frame = fetcher.get(srcs[0])
            live_n = len(_parse(frame.body).xpath(live_xpath))
        static_n = len(_parse(static.get(static_path).body).xpath(static_xpath))
        out.append(
            Finding(
                "aggregation",
                static_path,
                "equal" if live_n == static_n else "differs",
                f"live {live_n} entries via {srcs[:1]} | static {static_n}",
            )
        )
    for live_path in ("/data/charts-scholarly-editions/", "/data/charts-text-collections/"):
        page = _parse(fetcher.get(f"{LIVE_BASE}{live_path}").body)
        srcs = page.xpath("//iframe/@src")
        text = text_of(_parse(fetcher.get(srcs[0]).body)) if srcs else ""
        m = re.search(r"there (?:are|is) (\d+) reviews? with (\d+) filled", text)
        live_counts = f"{m.group(1)} reviews, {m.group(2)} questionnaires" if m else "n/a"
        charts = text_of(_parse(static.get("/data/charts/").body))
        static_counts = re.findall(r"(\d+) reviews?", charts)[:4]
        out.append(
            Finding(
                "aggregation_charts",
                live_path,
                "info",
                f"live iframe {srcs[:1]}: {live_counts} | static /data/charts/ counts {static_counts}",
            )
        )
    return out


def summarise(report: Report) -> dict[str, Counter]:
    per: dict[str, Counter] = {}
    for f in report.findings:
        per.setdefault(f.category, Counter())[f.status] += 1
    return per


def write_outputs(report: Report, out_dir: Path, network_requests: int) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    per = summarise(report)
    payload = {
        "started": report.started,
        "mode": report.mode,
        "static_source": report.static_source,
        "live_base": LIVE_BASE,
        "network_requests_this_run": network_requests,
        "inventory": report.inventory,
        "summary": {k: dict(v) for k, v in sorted(per.items())},
        "findings": [asdict(f) for f in report.findings],
    }
    (out_dir / "report.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        f"# Parity check, {report.mode} run",
        "",
        f"Started {report.started}. Live site {LIVE_BASE}, static site {report.static_source}.",
        f"Network requests in this run: {network_requests} (the rest came from the cache).",
        "",
        "## Inventory",
        "",
    ]
    lines += [f"- {k}: {v}" for k, v in report.inventory.items()]
    lines += ["", "## Coverage per category", ""]
    for cat, counts in sorted(per.items()):
        total = sum(counts.values())
        parts = ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))
        lines.append(f"- {cat}: {total} checked; {parts}")
    lines += ["", "## Deviations (first five per category)", ""]
    shown: Counter = Counter()
    for f in report.findings:
        if f.status in ("equal", "info") or shown[f.category] >= 5:
            continue
        shown[f.category] += 1
        lines.append(f"- {f.category} {f.status} {f.subject}: {f.detail[:300]}")
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_legacy_table(report: Report, path: Path) -> None:
    """Persist the live review addresses so redirects survive the old host.

    The table is evidence recorded from the live sitemap, keyed by DOI;
    ``src/render/redirects.py`` reads it at build time.
    """
    payload = {
        "source": f"{LIVE_BASE}/sitemap.xml, review pages joined to the corpus by DOI",
        "recorded": report.started[:10],
        "generator": "scripts/parity.py --full --write-legacy-urls",
        "reviews": {doi: sorted(set(p)) for doi, p in sorted(report.legacy_paths.items())},
        "tags": dict(sorted(report.legacy_tags.items())),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--sample", action="store_true", help="check the fixed sample (SAMPLE)")
    mode.add_argument("--full", action="store_true", help="check every live review")
    parser.add_argument("--static-url", default=STATIC_BASE, help="deployed static site")
    parser.add_argument("--static-root", type=Path, help="local build directory instead")
    parser.add_argument("--cache", type=Path, default=CACHE_DIR)
    parser.add_argument("--out", type=Path, default=OUT_DIR)
    parser.add_argument("--offline", action="store_true", help="use cached responses only")
    parser.add_argument("--interval", type=float, default=1.0, help="seconds between requests")
    parser.add_argument(
        "--write-legacy-urls",
        type=Path,
        metavar="JSON",
        help="full run only: record DOI -> live WordPress path (config/legacy-urls.json)",
    )
    args = parser.parse_args(argv)
    if args.write_legacy_urls and not args.full:
        parser.error("--write-legacy-urls needs --full, a sample would drop reviews")

    fetcher = CachedFetcher(args.cache, min_interval=args.interval, offline=args.offline)
    # GitHub Pages is a CDN; a shorter interval there keeps the run short.
    static_fetcher = CachedFetcher(args.cache, min_interval=0.25, offline=args.offline)
    static = StaticSite(args.static_url, static_fetcher, args.static_root)
    label = str(args.static_root) if args.static_root else args.static_url
    report = run(fetcher, static, sample=args.sample, static_fetch_label=label)
    write_outputs(report, args.out, fetcher.network_requests + static_fetcher.network_requests)
    if args.write_legacy_urls:
        write_legacy_table(report, args.write_legacy_urls)
    per = summarise(report)
    for cat, counts in sorted(per.items()):
        print(f"{cat:22} {dict(counts)}")
    print(f"Report: {args.out / 'report.json'}; summary: {args.out / 'summary.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
