"""Pre-apply guardrails: blast-radius cap and protected path prefixes.

The differ is deliberately read-only, but a clean-looking patch can still be
too wide for the window. Guards turn that judgement into a reviewable failure
instead of a verbal rule.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from .model import Change

# Paths that need a second pair of eyes even when the change count is small.
DEFAULT_PROTECTED = ("/system/aaa", "/system/radius", "/system/config/hostname")


@dataclass(frozen=True)
class Guardrails:
    max_changes: int = 25
    protected: Sequence[str] = field(default=DEFAULT_PROTECTED)

    def check(self, changes: Sequence[Change], allow_protected: bool = False) -> list[str]:
        """Return human-readable violations; an empty list means the patch may go."""
        violations: list[str] = []
        if len(changes) > self.max_changes:
            violations.append(
                f"{len(changes)} changes exceed the cap of {self.max_changes}; split the window"
            )
        if not allow_protected:
            for change in changes:
                hits = [prefix for prefix in self.protected if change.path.startswith(prefix)]
                if hits:
                    violations.append(f"{change.path} is under protected {hits[0]}")
        return violations
