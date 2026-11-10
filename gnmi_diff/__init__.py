"""gnmi-diff-net: dry-run gNMI state differ for change windows and CI."""

from .diff import diff_states, render
from .model import Change, by_severity, flatten, load_snapshot, severity_for

__all__ = [
    "Change",
    "by_severity",
    "diff_states",
    "flatten",
    "load_snapshot",
    "render",
    "severity_for",
]
