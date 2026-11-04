"""Error types that carry a cause and a concrete repair step (Why/Fix triad)."""

from __future__ import annotations


class EngineError(Exception):
    """A user-facing failure with a reason and a repair step."""

    def __init__(self, message: str, why: str, fix: str) -> None:
        super().__init__(message)
        self.why = why
        self.fix = fix

    def render(self) -> str:
        return f"Error: {self}\nWhy: {self.why}\nFix: {self.fix}"


_CLI_VERBS = {
    "event": "events",
    "ai_artifact": "ai artifacts",
    "observation": "observation list CLAIM",
    "killtest": "test",
}


class NotFound(EngineError):
    """A referenced record does not exist."""

    def __init__(self, kind: str, ref: str) -> None:
        verb = _CLI_VERBS.get(kind, f"{kind} list")
        super().__init__(
            f"{kind} not found: {ref}",
            f"no {kind} with that identifier exists in this database.",
            f"run `python -m engine {verb}` to see the identifiers that exist.",
        )
