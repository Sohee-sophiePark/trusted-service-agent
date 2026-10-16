"""Answers only from approved policy sections: BM25 retrieval, then a quote checked by code."""

import re
from dataclasses import dataclass
from functools import lru_cache

from pydantic import BaseModel
from rank_bm25 import BM25Okapi

from trusted_service_agent.llm.gateway import Gateway
from trusted_service_agent.paths import DATA, ROOT

POLICIES = DATA / "policies"
HEADING = re.compile(r"^## (.+?) \{#([a-z0-9-]+)\}\s*$", re.M)


@dataclass(frozen=True)
class Section:
    id: str  # "policies/<file>.md#<anchor>"
    title: str
    heading: str
    effective: str
    text: str


class Draft(BaseModel):
    supported: bool
    answer: str
    quote: str
    section_id: str


@dataclass(frozen=True)
class Grounded:
    answer: str
    quote: str
    section: Section


STOP = set(
    "a an and are as at be by can do does for from how i if in is it its me my of on or the "
    "this to what when where which who why will with you your".split()
)
SYNONYMS = {
    "us": ["united", "states"],
    "usa": ["united", "states"],
    "america": ["united", "states"],
    "pay": ["payment"],
    "paid": ["payment"],
    "paying": ["payment"],
}


def words(text: str) -> list[str]:
    """Lowercase tokens without stopwords, plural 's' stripped, a few location synonyms expanded."""
    out = []
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        if w in STOP:
            continue
        for t in SYNONYMS.get(w, [w]):
            out.append(t[:-1] if len(t) > 3 and t.endswith("s") and not t.endswith("ss") else t)
    return out


@lru_cache
def sections() -> tuple[Section, ...]:
    out = []
    for f in sorted(POLICIES.glob("*.md")):
        raw = f.read_text(encoding="utf-8")
        meta = dict(re.findall(r"^(\w+): (.+)$", raw.split("---")[1], re.M))
        parts = HEADING.split(raw)
        for heading, anchor, body in zip(parts[1::3], parts[2::3], parts[3::3], strict=True):
            sid = f"policies/{f.name}#{anchor}"
            out.append(Section(sid, meta["title"], heading, meta["effective"], body.strip()))
    return tuple(out)


@lru_cache
def index() -> BM25Okapi:
    return BM25Okapi([words(f"{s.title} {s.heading} {s.text}") for s in sections()])


def retrieve(question: str, k: int = 3) -> list[Section]:
    scores = index().get_scores(words(question))
    ranked = sorted(zip(scores, sections(), strict=True), key=lambda p: -p[0])
    return [s for score, s in ranked[:k] if score > 0]


def verified(quote: str, section: Section) -> bool:
    """The quote must appear word for word in the cited section (whitespace-insensitive)."""
    return bool(quote.strip()) and " ".join(quote.split()) in " ".join(section.text.split())


async def answer(question: str, gw: Gateway) -> Grounded | None:
    """A cited answer, or None when no approved source supports it (the caller hands off)."""
    found = retrieve(question)
    if not found:
        return None
    context = "\n\n".join(f'<section id="{s.id}">\n{s.text}\n</section>' for s in found)
    system = (ROOT / "prompts" / "grounding.md").read_text(encoding="utf-8")
    d = await gw.ask("writer", system, f"<question>{question}</question>\n{context}", Draft)
    cited = next((s for s in found if s.id == d.section_id), None)
    if not d.supported or cited is None or not verified(d.quote, cited):
        return None
    return Grounded(d.answer, d.quote, cited)
