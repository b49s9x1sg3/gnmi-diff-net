import unittest

from gnmi_diff.guards import Guardrails
from gnmi_diff.model import Change


def change(path, severity="low"):
    return Change(path=path, kind="modify", before="a", after="b", severity=severity)


class GuardrailsTest(unittest.TestCase):
    def test_small_patch_passes(self):
        rails = Guardrails(max_changes=2, protected=("/system/aaa",))
        self.assertEqual(rails.check([change("/interfaces/ethernet-1/1/config/mtu")]), [])

    def test_cap_is_inclusive(self):
        rails = Guardrails(max_changes=1, protected=())
        self.assertEqual(rails.check([change("/interfaces/ethernet-1/1/config/mtu")]), [])

    def test_over_cap_reported(self):
        rails = Guardrails(max_changes=1, protected=())
        violations = rails.check([change("/a"), change("/b")])
        self.assertEqual(len(violations), 1)
        self.assertIn("exceed the cap of 1", violations[0])

    def test_protected_prefix_blocks(self):
        rails = Guardrails(max_changes=10)
        violations = rails.check([change("/system/aaa/config/servers")])
        self.assertEqual(len(violations), 1)
        self.assertIn("is under protected /system/aaa", violations[0])

    def test_allow_protected_bypass(self):
        rails = Guardrails(max_changes=10)
        self.assertEqual(rails.check([change("/system/aaa/config/servers")], allow_protected=True), [])

    def test_custom_protected_replaces_defaults(self):
        rails = Guardrails(max_changes=10, protected=("/routing-policy",))
        self.assertEqual(rails.check([change("/system/aaa/config/servers")]), [])
        self.assertEqual(len(rails.check([change("/routing-policy/IMPORT/config/action")])), 1)


if __name__ == "__main__":
    unittest.main()


class CliGuardTest(unittest.TestCase):
    def test_protected_path_blocks_with_exit_3(self):
        import json
        import tempfile
        from pathlib import Path

        from gnmi_diff.cli import main

        with tempfile.TemporaryDirectory() as tmp:
            running = Path(tmp, "running.json")
            intended = Path(tmp, "intended.json")
            running.write_text(json.dumps({"system": {"config": {"hostname": "leaf-01"}}}))
            intended.write_text(json.dumps({"system": {"config": {"hostname": "leaf-02"}}}))
            argv = ["--running", str(running), "--intended", str(intended)]
            self.assertEqual(main(argv), 3)
            self.assertEqual(main([*argv, "--force-protected"]), 0)
