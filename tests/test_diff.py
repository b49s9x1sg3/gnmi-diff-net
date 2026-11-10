import json
import tempfile
import unittest
from pathlib import Path

from gnmi_diff.cli import main
from gnmi_diff.diff import diff_states
from gnmi_diff.model import by_severity, load_snapshot, severity_for

RUNNING = {
    "interfaces": {
        "ethernet-1/1": {"config": {"description": "uplink-a", "enabled": True}},
        "ethernet-1/2": {"config": {"description": "spare"}},
    },
    "routing-policy": {"policy-statement": {"IMPORT-LAB": {"config": {"default-action": "reject"}}}},
}
INTENDED = {
    "interfaces": {
        "ethernet-1/1": {"config": {"description": "uplink-to-spine1", "enabled": True}},
        "ethernet-1/3": {"config": {"description": "new-member"}},
    },
    "routing-policy": {"policy-statement": {"IMPORT-LAB": {"config": {"default-action": "reject"}}}},
    "system": {"config": {"hostname": "leaf-01"}},
}


class DiffTest(unittest.TestCase):
    def test_reports_add_remove_and_modify(self):
        changes = {change.path: change.kind for change in diff_states(RUNNING, INTENDED)}
        self.assertEqual(changes["/interfaces/ethernet-1/1/config/description"], "modify")
        self.assertEqual(changes["/interfaces/ethernet-1/2/config/description"], "remove")
        self.assertEqual(changes["/interfaces/ethernet-1/3/config/description"], "add")
        self.assertEqual(changes["/system/config/hostname"], "add")
        self.assertNotIn("/interfaces/ethernet-1/1/config/enabled", changes)

    def test_unchanged_subtree_is_silent(self):
        paths = {change.path for change in diff_states(RUNNING, INTENDED)}
        self.assertFalse(any(path.startswith("/routing-policy") for path in paths))

    def test_severity_tiers(self):
        self.assertEqual(severity_for("/system/config/hostname"), "high")
        self.assertEqual(severity_for("/network-instances/red/protocols/bgp/global/config/as"), "high")
        self.assertEqual(severity_for("/interfaces/ethernet-1/1/config/enabled"), "high")
        self.assertEqual(severity_for("/routing-policy/policy-statement/IMPORT-LAB/config/default-action"), "medium")
        self.assertEqual(severity_for("/interfaces/ethernet-1/1/config/description"), "low")

    def test_high_impact_sorted_first(self):
        ordered = by_severity(diff_states(RUNNING, INTENDED))
        self.assertEqual(ordered[0].severity, "high")

    def test_sequence_index_is_kept(self):
        changes = diff_states({"ntp": {"server": ["a", "b"]}}, {"ntp": {"server": ["a", "c"]}})
        self.assertEqual([change.path for change in changes], ["/ntp/server/1"])

    def test_root_must_be_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "state.json")
            path.write_text(json.dumps([1, 2]))
            with self.assertRaises(ValueError):
                load_snapshot(path)


class CliTest(unittest.TestCase):
    def _run(self, running, intended, *extra):
        with tempfile.TemporaryDirectory() as tmp:
            running_path = Path(tmp, "running.json")
            intended_path = Path(tmp, "intended.json")
            running_path.write_text(json.dumps(running))
            intended_path.write_text(json.dumps(intended))
            return main(
                ["--running", str(running_path), "--intended", str(intended_path), *extra]
            )

    def test_check_exits_nonzero_on_drift(self):
        self.assertEqual(self._run(RUNNING, INTENDED, "--check"), 1)

    def test_check_exits_zero_without_drift(self):
        self.assertEqual(self._run(RUNNING, RUNNING, "--check"), 0)


if __name__ == "__main__":
    unittest.main()
