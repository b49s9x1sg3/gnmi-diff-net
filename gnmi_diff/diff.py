"""Pure difference between a running snapshot and the intended state.

No device I/O happens here: the caller hands in two snapshots, so the same code
path runs in CI against an exported state and in a change window against a
freshly collected one.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

from .model import Change, flatten, severity_for

MISSING = object()


def _scalars(state: Mapping[str, Any]) -> Dict[str, Any]:
    return dict(flatten(state))


def diff_states(running: Mapping[str, Any], intended: Mapping[str, Any]) -> List[Change]:
    """Return every leaf that differs; intended state is authoritative."""
    before = _scalars(running)
    after = _scalars(intended)
    changes: List[Change] = []

    for path in sorted(set(before) | set(after)):
        old = before.get(path, MISSING)
        new = after.get(path, MISSING)
        severity = severity_for(path)
        if old is MISSING:
            changes.append(Change(path, "add", before=None, after=new, severity=severity))
        elif new is MISSING:
            changes.append(Change(path, "remove", before=old, after=None, severity=severity))
        elif old != new:
            changes.append(Change(path, "modify", before=old, after=new, severity=severity))
    return changes


def render(path_prefix: str, changes: List[Change]) -> str:
    """Human-readable, patch-like report used for review before apply."""
    markers = {"add": "+", "remove": "-", "modify": "~"}
    lines = [
        f"{path_prefix} {len(changes)} change(s)",
        "marker  severity  path",
    ]
    for change in changes:
        marker = markers[change.kind]
        if change.kind == "modify":
            value = f"{change.before!r} -> {change.after!r}"
        elif change.kind == "add":
            value = repr(change.after)
        else:
            value = repr(change.before)
        lines.append(f"{marker:<7} {change.severity:<9} {change.path}  {value}")
    return "\n".join(lines)
