"""Snapshot model: load and flatten gNMI-style nested state.

A snapshot is a nested mapping whose keys are gNMI path segments, for example::

    {"interfaces": {"ethernet-1/1": {"config": {"description": "uplink"}}}}

Flattening turns that into ``/interfaces/ethernet-1/1/config/description``.
Sequences are indexed so a reordered leaf does not silently overwrite a sibling.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, Mapping, Tuple

# Impact tiers, most severe first. Matching is on the flattened path.
_HIGH_PREFIXES = ("/system", "/network-instances")
_HIGH_SEGMENTS = ("enabled", "admin-state", "oper-state", "mtu", "address", "vlan")
_MEDIUM_SEGMENTS = ("routing-policy", "policy-statement", "bgp", "as-path", "prefix-list")

_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


@dataclass(frozen=True)
class Change:
    """One leaf-level difference between running and intended state."""

    path: str
    kind: str  # add | remove | modify
    before: Any = None
    after: Any = None
    severity: str = "low"

    def as_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "kind": self.kind,
            "before": self.before,
            "after": self.after,
            "severity": self.severity,
        }


def severity_for(path: str) -> str:
    """Classify blast radius from the path; defaults to low."""
    if path.startswith(_HIGH_PREFIXES):
        return "high"
    segments = path.strip("/").split("/")
    if any(segment in _HIGH_SEGMENTS for segment in segments):
        return "high"
    if any(segment in _MEDIUM_SEGMENTS for segment in segments):
        return "medium"
    return "low"


def load_snapshot(path: str | Path) -> Dict[str, Any]:
    """Read a JSON snapshot and insist on a mapping at the root."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: snapshot root must be an object")
    return data


def flatten(state: Mapping[str, Any], prefix: str = "") -> Iterator[Tuple[str, Any]]:
    """Yield ``(path, scalar)`` for every leaf, depth first, sorted by key."""
    for key in sorted(state):
        value = state[key]
        path = f"{prefix}/{key}"
        if isinstance(value, Mapping):
            yield from flatten(value, path)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                item_path = f"{path}/{index}"
                if isinstance(item, Mapping):
                    yield from flatten(item, item_path)
                else:
                    yield item_path, item
        else:
            yield path, value


def by_severity(changes: list[Change]) -> list[Change]:
    """Sort changes high impact first, then by path."""
    return sorted(changes, key=lambda c: (_SEVERITY_ORDER.get(c.severity, 9), c.path))
