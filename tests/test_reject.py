"""Tests for plugins/callback/uc_reject.py.

Each test runs tests/playbooks/reject.yml from the repository, so ansible.cfg
enables the callback, against a client inventory in a temporary directory,
and checks which rejection files are written in the client log beside it.
The node is dev.example.org, from the safe values register, reached with the
local connection. The unreachable case uses ssh to a closed port on
127.0.0.1, which is refused before any login is tried.

    python3 tests/run_tests.py
"""
from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import yaml

import helpers

PLAYBOOK = helpers.REPO / "tests" / "playbooks" / "reject.yml"
NAME = re.compile(r"^\d{4}-\d{2}-\d{2}--\d{2}-\d{2}-\d{2}-rejected-uc-node-cannot-be-secured\.yml$")
ENTRY_FIELDS = ["node", "rejected", "controller", "step", "reason", "clauses", "fingerprint", "raw_node_batch"]


@unittest.skipUnless(shutil.which("ansible-playbook"), "ansible-playbook not on PATH")
class Reject(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.inventory = helpers.make_client_inventory(Path(self.tmp.name))
        self.log = self.inventory.parent / "logs" / "rejected"
        self.candidate = self.inventory / "candidates" / "dev.example.org.yml"
        self.candidate.write_text("dev.example.org:\n  address: \"203.0.113.21\"\n")

    def tearDown(self):
        self.tmp.cleanup()

    def run_case(self, case, inventory="default"):
        env = dict(os.environ, ANSIBLE_NOCOLOR="1")
        env.pop("ANSIBLE_CONFIG", None)
        argv = ["ansible-playbook", str(PLAYBOOK), "-e", f"uc_test_case={case}",
                "-e", f"raw_node_batch={helpers.BATCH}"]
        if inventory == "default":
            argv += ["-e", f"uc_client_inventory={self.inventory}"]
        elif inventory is not None:
            argv += ["-e", f"uc_client_inventory={inventory}"]
        result = subprocess.run(argv, cwd=helpers.REPO, env=env, capture_output=True, text=True, timeout=120)
        return result.returncode, result.stdout + result.stderr

    def entries(self):
        return sorted(self.log.iterdir()) if self.log.is_dir() else []

    def one_entry(self):
        files = self.entries()
        self.assertEqual(len(files), 1, files)
        self.assertRegex(files[0].name, NAME)
        text = files[0].read_text()
        self.assertNotIn("made-up node output", text)
        data = yaml.load(text, Loader=yaml.BaseLoader)
        self.assertEqual(list(data), ENTRY_FIELDS)
        return files[0], data

    def test_failure_in_raw_node(self):
        status, output = self.run_case("raw-node-fails")
        self.assertNotEqual(status, 0)
        path, data = self.one_entry()
        self.assertEqual(data["node"], "dev.example.org")
        self.assertEqual(data["controller"], "uc-node")
        self.assertEqual(data["reason"], "cannot-be-secured")
        self.assertEqual(data["step"], "Secure the node: Stop if a sudoers rule has NOPASSWD (RN-ACC-07)")
        # The task's clause, and the clause the confirmation's check set; not
        # "Host keys", which is not a clause identifier.
        self.assertEqual(data["clauses"], ["RN-ACC-07", "RN-SSH-03"])
        self.assertEqual(data["fingerprint"], "SHA256:EXAMPLEexampleEXAMPLEexampleEXAMPLEexample0")
        self.assertEqual(data["raw_node_batch"], helpers.BATCH)
        rejected = datetime.fromisoformat(data["rejected"])
        self.assertIsNotNone(rejected.tzinfo)
        self.assertEqual(path.name[:20], f"{rejected:%Y-%m-%d--%H-%M-%S}")
        self.assertIn("Rejection written to", output)

    def test_rejected_build_removes_the_candidate(self):
        status, output = self.run_case("raw-node-fails")
        self.assertNotEqual(status, 0)
        self.assertFalse(self.candidate.exists())
        self.assertIn("removed the candidate", output)

    def test_log_is_made_private(self):
        self.run_case("raw-node-fails")
        for directory in (self.log.parent, self.log):
            self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o700, directory)

    def test_unreachable(self):
        status, output = self.run_case("unreachable")
        self.assertNotEqual(status, 0)
        self.assertIn("UNREACHABLE", output)
        _, data = self.one_entry()
        self.assertEqual(data["step"], "Secure the node: Reach the node")
        self.assertEqual(data["clauses"], [])
        self.assertEqual(data["fingerprint"], "")
        self.assertFalse(self.candidate.exists())

    def test_failure_on_localhost_writes_nothing(self):
        status, _ = self.run_case("localhost-fails")
        self.assertNotEqual(status, 0)
        self.assertEqual(self.entries(), [])
        self.assertFalse(self.log.parent.exists())
        self.assertTrue(self.candidate.exists())

    def test_rescued_failure_writes_nothing(self):
        status, output = self.run_case("rescued")
        self.assertEqual(status, 0, output)
        self.assertEqual(self.entries(), [])
        self.assertTrue(self.candidate.exists())

    def test_ignored_failure_writes_nothing(self):
        status, output = self.run_case("ignored")
        self.assertEqual(status, 0, output)
        self.assertEqual(self.entries(), [])

    def test_a_good_run_writes_nothing(self):
        status, output = self.run_case("passes")
        self.assertEqual(status, 0, output)
        self.assertEqual(self.entries(), [])
        self.assertTrue(self.candidate.exists())

    def test_no_client_inventory_writes_nothing(self):
        status, output = self.run_case("raw-node-fails", inventory=None)
        self.assertNotEqual(status, 0)
        self.assertIn("no rejection was written", output)
        self.assertEqual(self.entries(), [])

    def test_two_rejections_never_share_a_file(self):
        self.run_case("raw-node-fails")
        self.run_case("raw-node-fails")
        self.assertEqual(len(self.entries()), 2)


if __name__ == "__main__":
    unittest.main()
