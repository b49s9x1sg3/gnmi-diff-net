"""Command line front end: dry-run differ for one device."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

from .diff import diff_states, render
from .guards import DEFAULT_PROTECTED, Guardrails
from .model import by_severity, load_snapshot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gnmi-diff",
        description="Diff intended gNMI state against a running snapshot. Read-only.",
    )
    parser.add_argument("--running", required=True, help="JSON snapshot collected from the device")
    parser.add_argument("--intended", required=True, help="JSON state rendered from the source of truth")
    parser.add_argument("--json", action="store_true", help="emit machine-readable changes")
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 when drift exists (CI mode); last-reviewed snapshot as intended",
    )
    parser.add_argument(
        "--max-changes",
        type=int,
        default=25,
        help="block patches wider than this many leaves (default: 25)",
    )
    parser.add_argument(
        "--protected",
        action="append",
        metavar="PREFIX",
        help=f"add a path prefix that needs --force-protected (defaults: {', '.join(DEFAULT_PROTECTED)})",
    )
    parser.add_argument(
        "--force-protected",
        action="store_true",
        help="accept changes under protected prefixes, e.g. inside an approved AAA window",
    )
    return parser


def _summary(changes) -> str:
    if not changes:
        return "no drift: running state matches intended state"
    counts: dict[str, int] = {}
    for change in changes:
        counts[change.severity] = counts.get(change.severity, 0) + 1
    parts = ", ".join(f"{counts[level]} {level}" for level in ("high", "medium", "low") if level in counts)
    return f"drift detected: {len(changes)} change(s) ({parts})"


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        running = load_snapshot(args.running)
        intended = load_snapshot(args.intended)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    changes = by_severity(diff_states(running, intended))
    if args.json:
        json.dump([change.as_dict() for change in changes], sys.stdout, indent=2)
        print()
    elif changes:
        print(render(f"{Path(args.intended).name}:", changes))
    print(_summary(changes), file=sys.stderr)

    rails = Guardrails(
        max_changes=args.max_changes,
        protected=tuple(args.protected) if args.protected else DEFAULT_PROTECTED,
    )
    violations = rails.check(changes, allow_protected=args.force_protected)
    for violation in violations:
        print(f"guard: {violation}", file=sys.stderr)
    if violations:
        print(f"blocked by {len(violations)} guard(s); split the window or pass --force-protected", file=sys.stderr)
        return 3

    if changes and args.check:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
