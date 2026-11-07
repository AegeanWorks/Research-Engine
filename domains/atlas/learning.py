"""Visual learning interactions — spatial recall distinct from flashcards.

Modes: spatial-recall, pathway-tracing, visual-identification, relationship-recall.
Deterministic (seeded) so tests and demos are reproducible. Operates purely on
the validated VisualAnalysis dict; never mutates it.
"""
from __future__ import annotations

import random


def _entities(analysis: dict) -> list[dict]:
    return list(analysis.get("entities", []))


def _relationships(analysis: dict) -> list[dict]:
    return list(analysis.get("relationships", []))


def spatial_recall_challenge(analysis: dict, seed: int = 0) -> dict:
    """Hide labels; ask the user to identify a highlighted structure."""
    ents = _entities(analysis)
    if not ents:
        raise ValueError("analysis has no entities")
    located = [e for e in ents if e.get("bbox")]
    if not located:
        raise ValueError("spatial-recall needs located entities with bbox: "
                         "this text-only model has none — use visual-identification")
    candidates = located
    target = random.Random(seed).choice(candidates)
    pool = [{"id": e["id"], "name": e["name"]} for e in ents]
    options = random.Random(seed + 1).sample(pool, k=min(4, len(pool)))
    if target["id"] not in {o["id"] for o in options}:
        options[0] = {"id": target["id"], "name": target["name"]}
    return {
        "mode": "spatial-recall",
        "target_id": target["id"],
        "highlight_bbox": target.get("bbox"),
        "prompt": "Which structure is highlighted on the figure?",
        "options": options,
        "answer_id": target["id"],
    }


def pathway_tracing_challenge(analysis: dict, seed: int = 0) -> dict:
    """Order a connected chain of entities; user traces the pathway."""
    rels = _relationships(analysis)
    ents = {e["id"]: e for e in _entities(analysis)}
    if not rels and not ents:
        raise ValueError("analysis has no entities or relationships to trace")
    if len(rels) < 2:
        # Degenerate but valid: single-hop trace.
        chain = []
        if rels:
            chain = [rels[0]["source_id"], rels[0]["target_id"]]
        elif ents:
            first = random.Random(seed).choice(list(ents))
            chain = [first]
        return {"mode": "pathway-tracing", "chain": chain,
                "prompt": "Trace the connected pathway in order.", "answer": chain}
    rng = random.Random(seed)
    start = rng.choice(rels)
    chain = [start["source_id"], start["target_id"]]
    by_src = {}
    for r in rels:
        by_src.setdefault(r["source_id"], []).append(r)
    for _ in range(len(rels)):
        nxt = by_src.get(chain[-1])
        if not nxt:
            break
        step = rng.choice(nxt)
        if step["target_id"] in chain:
            break
        chain.append(step["target_id"])
    names = [ents[i]["name"] if i in ents else i for i in chain]
    return {"mode": "pathway-tracing", "chain": chain, "chain_names": names,
            "prompt": f"Trace the pathway starting at {names[0]}.", "answer": chain}


def visual_identification_challenge(analysis: dict, seed: int = 0) -> dict:
    ents = _entities(analysis)
    if not ents:
        raise ValueError("analysis has no entities")
    rng = random.Random(seed)
    target = rng.choice(ents)
    distractors = [e for e in ents if e["id"] != target["id"]]
    options = [target] + rng.sample(distractors, k=min(3, len(distractors)))
    rng.shuffle(options)
    return {
        "mode": "visual-identification",
        "description": target.get("description", target["name"]),
        "options": [{"id": e["id"], "name": e["name"]} for e in options],
        "answer_id": target["id"],
        "prompt": "Which entity matches this description? The canvas highlights nothing.",
    }


def relationship_recall_challenge(analysis: dict, seed: int = 0) -> dict:
    rels = _relationships(analysis)
    if not rels:
        raise ValueError("analysis has no relationships")
    target = random.Random(seed).choice(rels)
    ents = {e["id"]: e["name"] for e in _entities(analysis)}
    return {
        "mode": "relationship-recall",
        "source": {"id": target["source_id"], "name": ents.get(target["source_id"], "?")},
        "target": {"id": target["target_id"], "name": ents.get(target["target_id"], "?")},
        "prompt": f"How are {ents.get(target['source_id'], '?')} and {ents.get(target['target_id'], '?')} connected?",
        "answer_rel_type": target["rel_type"],
        "explanation": target.get("explanation", ""),
    }


def grade(challenge: dict, user_answer: str) -> dict:
    key = {"spatial-recall": "answer_id", "visual-identification": "answer_id",
           "relationship-recall": "answer_rel_type"}.get(challenge.get("mode", ""))
    if challenge.get("mode") == "pathway-tracing":
        correct = list(user_answer) == list(challenge.get("answer", [])) if isinstance(user_answer, list) else False
        return {"correct": correct, "expected": challenge.get("answer")}
    if key is None:
        raise ValueError(f"unknown challenge mode {challenge.get('mode')!r}")
    return {"correct": user_answer == challenge.get(key), "expected": challenge.get(key)}
