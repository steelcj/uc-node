"""Tests for scripts/new-batch.

Each test runs the script with UC_NODE_SECRETS_DIR naming a secrets root in
a temporary directory, so ~/.secrets/ is never read or written, and types
the passwords into a pseudo-terminal, as the operator would. The passwords
are made up in tests/helpers.py.

    python3 tests/run_tests.py
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

import helpers

SCRIPT = helpers.REPO / "scripts" / "new-batch"
ROOT_PROMPT = "Root password: "
BATCH_PROMPT = "Batch password, for the initial user"
AGAIN_PROMPT = "Batch password again: "


@unittest.skipUnless(shutil.which("openssl"), "openssl not on PATH")
class NewBatch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.root = self.base / "secrets"
        self.env = dict(os.environ, UC_NODE_SECRETS_DIR=str(self.root))

    def tearDown(self):
        self.tmp.cleanup()

    def run_batch(self, batch, root=helpers.ROOT_PASSWORD, password=helpers.BATCH_PASSWORD, again=None):
        answers = [(ROOT_PROMPT, root), (BATCH_PROMPT, password), (AGAIN_PROMPT, password if again is None else again)]
        status, output = helpers.run_on_terminal([sys.executable, str(SCRIPT), batch], answers, env=self.env)
        self.assertNotIn(helpers.ROOT_PASSWORD, output)
        self.assertNotIn(helpers.BATCH_PASSWORD, output)
        self.assertNotIn("$6$", output)
        return status, output

    def batch_file(self, batch=helpers.BATCH):
        return self.root / "batches" / f"{batch}.yml"

    def test_writes_the_batch(self):
        status, output = self.run_batch(helpers.BATCH)
        self.assertEqual(status, 0, output)
        path = self.batch_file()
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        for directory in (self.root, self.root / "batches"):
            self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o700, directory)
        self.assertIn("batch-secrets.md", output)
        self.assertIn("uc-node never stores it", output)

    def test_hashes_verify_and_no_password_in_the_file(self):
        status, output = self.run_batch(helpers.BATCH)
        self.assertEqual(status, 0, output)
        text = self.batch_file().read_text()
        self.assertNotIn(helpers.ROOT_PASSWORD, text)
        self.assertNotIn(helpers.BATCH_PASSWORD, text)
        data = yaml.safe_load(text)
        self.assertEqual(sorted(data), ["initial_password_hash", "root_password_hash"])
        self.assertTrue(helpers.hash_matches(helpers.ROOT_PASSWORD, data["root_password_hash"]))
        self.assertTrue(helpers.hash_matches(helpers.BATCH_PASSWORD, data["initial_password_hash"]))
        self.assertFalse(helpers.hash_matches(helpers.ROOT_PASSWORD, data["initial_password_hash"]))

    def test_the_lookup_reads_what_it_writes(self):
        """The file passes uc_secret's mode and owner checks."""
        try:
            import ansible  # noqa: F401
        except ImportError:
            self.skipTest("Ansible is not importable")
        from ansible.plugins.loader import lookup_loader
        status, output = self.run_batch(helpers.BATCH)
        self.assertEqual(status, 0, output)
        lookup_loader.add_directory(str(helpers.REPO / "plugins" / "lookup"))
        plugin = lookup_loader.get("uc_secret")
        old = os.environ.get("UC_NODE_SECRETS_DIR")
        os.environ["UC_NODE_SECRETS_DIR"] = str(self.root)
        try:
            value = plugin.run([f"batches/{helpers.BATCH}"], variables={}, key="initial_password_hash")[0]
        finally:
            if old is None:
                os.environ.pop("UC_NODE_SECRETS_DIR")
            else:
                os.environ["UC_NODE_SECRETS_DIR"] = old
        self.assertTrue(helpers.hash_matches(helpers.BATCH_PASSWORD, str(value)))

    def test_name_rule(self):
        for name in ("raw-1970-1-01-01", "raw-1970-01-01-1", "batch-1970-01-01-01", "raw-1970-01-01-01.yml",
                     "raw-1970-13-01-01", "raw-1970-02-30-01", "../raw-1970-01-01-01", "raw-1970-01-01-01/x"):
            with self.subTest(name=name):
                status, output = helpers.run_on_terminal([sys.executable, str(SCRIPT), name], [], env=self.env)
                self.assertEqual(status, 2, output)
                self.assertNotIn("Root password", output)
        self.assertFalse(self.root.exists())

    def test_existing_batch_is_refused(self):
        helpers.make_secrets_root(self.base)
        path = self.batch_file()
        path.write_text("root_password_hash: 'kept'\n")
        path.chmod(0o600)
        status, output = helpers.run_on_terminal([sys.executable, str(SCRIPT), helpers.BATCH], [], env=self.env)
        self.assertEqual(status, 1, output)
        self.assertIn("exists", output)
        self.assertNotIn("Root password", output)
        self.assertEqual(path.read_text(), "root_password_hash: 'kept'\n")

    def test_short_batch_password(self):
        # 14 characters: one short of RN-ACC-08.
        status, output = self.run_batch(helpers.BATCH, password="fourteen-chars")
        self.assertEqual(status, 1, output)
        self.assertIn("RN-ACC-08", output)
        self.assertFalse(self.batch_file().exists())

    def test_entries_differ(self):
        status, output = self.run_batch(helpers.BATCH, again=helpers.BATCH_PASSWORD + "x")
        self.assertEqual(status, 1, output)
        self.assertIn("differ", output)
        self.assertFalse(self.batch_file().exists())

    def test_empty_root_password(self):
        status, output = helpers.run_on_terminal(
            [sys.executable, str(SCRIPT), helpers.BATCH], [(ROOT_PROMPT, "")], env=self.env)
        self.assertEqual(status, 1, output)
        self.assertFalse(self.batch_file().exists())

    def test_directory_not_0700_is_refused(self):
        helpers.make_secrets_root(self.base)
        (self.root / "batches").chmod(0o755)
        status, output = helpers.run_on_terminal([sys.executable, str(SCRIPT), helpers.BATCH], [], env=self.env)
        self.assertEqual(status, 1, output)
        self.assertIn("is mode 0755, not 0700", output)
        self.assertFalse(self.batch_file().exists())

    def test_no_terminal_is_refused(self):
        """Without a terminal getpass would echo, so nothing is read."""
        result = subprocess.run([sys.executable, str(SCRIPT), helpers.BATCH], env=self.env,
                                input=f"{helpers.ROOT_PASSWORD}\n{helpers.BATCH_PASSWORD}\n{helpers.BATCH_PASSWORD}\n",
                                capture_output=True, text=True, start_new_session=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("from a terminal", result.stderr)
        self.assertFalse(self.batch_file().exists())

    def test_password_is_never_an_argument(self):
        """openssl is given the password on standard input: the script never
        puts it in an argument list."""
        text = SCRIPT.read_text()
        self.assertIn('["openssl", "passwd", "-6", "-stdin"]', text)
        self.assertNotIn("shell=True", text)


if __name__ == "__main__":
    unittest.main()
