"""Auto study material: summaries generated from the validated model.

Two tiers, same source of truth:
- Extractive (offline, always): overview, per-entity bullets with evidence,
  directional pathway chains, and coverage stats — deterministic, no key.
- Polished (Muse, needs key): the extractive brief rewritten as a flowing
  study summary. If the key is missing the API returns extractive-only with
  an explicit flag — never a fake polish.
"""
from __future__ import annotations


def _names(analysis: dict) -> dict:
    return {e["id"]: e.get("name", e["id"]) for e in analysis.get("entities", [])}


def pathway_chains(analysis: dict, max_depth: int = 6) -> list[list[str]]:
    """Maximal directional chains (no revisits) over the relationship graph."""
    names = _names(analysis)
    outgoing: dict[str, list[str]] = {}
    for r in analysis.get("relationships", []):
        outgoing.setdefault(r["source_id"], []).append(r["target_id"])
    chains: list[list[str]] = []

    def walk(node: str, path: list[str]) -> None:
        extended = False
        for nxt in outgoing.get(node, []):
            if nxt not in path and len(path) < max_depth:
                extended = True
                walk(nxt, path + [nxt])
        if not extended and len(path) > 1:
            chains.append(path)

    starts = [e["id"] for e in analysis.get("entities", [])]
    targets = {r["target_id"] for r in analysis.get("relationships", [])}
    # Prefer true sources, but cycles mean every node can be targeted: any node
    # with outgoing edges is a valid start (no-revisit walk always terminates).
    roots = ([s for s in starts if s not in targets and outgoing.get(s)]
             or [s for s in starts if outgoing.get(s)] or starts)
    for root in roots:
        walk(root, [root])
    seen, unique = set(), []
    for chain in chains:
        key = tuple(chain)
        if key not in seen:
            seen.add(key)
            unique.append(chain)
    named = [[names.get(n, n) for n in chain] for chain in unique]
    named.sort(key=lambda c: (-len(c), c))
    return named


def extractive_summary(analysis: dict) -> dict:
    """Deterministic study brief: overview, entities, pathways, stats."""
    entities = list(analysis.get("entities", []))
    relationships = list(analysis.get("relationships", []))
    names = _names(analysis)
    located = sum(1 for e in entities if e.get("bbox"))
    overview = (f"This model holds {len(entities)} structures and "
                f"{len(relationships)} relationships "
                f"({located} visually located).")
    bullets = []
    for e in entities:
        outs = [r for r in relationships if r["source_id"] == e["id"]]
        ins = [r for r in relationships if r["target_id"] == e["id"]]
        links = ([f"{names.get(r['source_id'], '?')} —{r['rel_type']}→ {e.get('name', e['id'])}" for r in ins]
                 + [f"{e.get('name', e['id'])} —{r['rel_type']}→ {names.get(r['target_id'], '?')}" for r in outs])
        if len(links) > 5:
            links = links[:5] + [f"+{len(links) - 5} more relations"]
        line = f"{e.get('name', e['id'])} [{e.get('category', 'other')}]"
        if e.get("description"):
            line += f" — {e['description']}"
        if links:
            line += f" ({'; '.join(links)})"
        if e.get("source_evidence"):
            line += f" [evidence: {e['source_evidence']}]"
        bullets.append(line)
    chains = [" → ".join(chain) for chain in pathway_chains(analysis)]
    return {
        "figure_id": analysis.get("figure_id", ""),
        "title": f"Study summary: {analysis.get('figure_id', 'model')}",
        "overview": overview,
        "entities": bullets,
        "pathways": chains[:12],
        "pathways_total": len(chains),
        "pathways_truncated": len(chains) > 12,
        "stats": {"entities": len(entities), "relationships": len(relationships),
                  "located": located,
                  "categories": sorted({e.get("category", "other") for e in entities})},
    }
