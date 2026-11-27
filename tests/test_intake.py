"""Tests for intake: build.yml's check play, scripts/build and scripts/new-node.

Every test makes its own secrets root and client inventory in a temporary
directory, with values from the safe values register.

The check play tests run ansible-playbook build.yml with a fake incus first
on PATH, which answers every query with "not found" and refuses every
launch. A build that passes the check play therefore stops at the launch,
and nothing is ever created.

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

FAKE_INCUS = """#!/bin/sh
# A stand-in for incus in the tests: nothing exists, and nothing is made.
echo "fake incus: $*" >&2
exit 1
"""


class Setup:
    """A secrets root with a batch, a client inventory and a node definition."""

    def __init__(self, base: Path):
        self.base = base
        self.root = helpers.make_secrets_root(base)
        self.batch = helpers.make_batch(self.root)
        self.inventory = helpers.make_client_inventory(base)
        self.public_key = helpers.make_ssh_key(base).read_text().strip()
        self.definition = helpers.write_node_definition(
            self.inventory, helpers.node_definition(self.public_key))
        self.bin = base / "bin"
        self.bin.mkdir()
        (self.bin / "incus").write_text(FAKE_INCUS)
        (self.bin / "incus").chmod(0o755)
        self.env = dict(os.environ, UC_NODE_SECRETS_DIR=str(self.root), ANSIBLE_NOCOLOR="1",
                        ANSIBLE_FORCE_COLOR="0", PATH=f"{self.bin}{os.pathsep}{os.environ['PATH']}")
        self.env.pop("ANSIBLE_CONFIG", None)

    def playbook(self, *extra, definition=None, inventory="default"):
        definition = definition or self.definition
        argv = ["ansible-playbook", "build.yml", "-e", f"@{definition}"]
        if inventory == "default":
            argv += ["-e", f"uc_client_inventory={self.inventory}"]
        elif inventory is not None:
            argv += ["-e", f"uc_client_inventory={inventory}"]
        argv += list(extra)
        result = subprocess.run(argv, cwd=helpers.REPO, env=self.env, capture_output=True, text=True, timeout=300)
        return result.returncode, result.stdout + result.stderr


@unittest.skipUnless(shutil.which("ansible-playbook"), "ansible-playbook not on PATH")
class CheckPlay(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.s = Setup(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def refused(self, expected, *extra, **kwargs):
        status, output = self.s.playbook(*extra, **kwargs)
        self.assertNotEqual(status, 0, output)
        self.assertIn(expected, output)
        self.assertNotIn("fake incus: launch", output, "the check play let the build through")
        self.assertNotIn("$6$", output)
        self.assertNotIn(helpers.ROOT_PASSWORD, output)
        return output

    def rewrite_definition(self, **changes):
        data = yaml.safe_load(self.s.definition.read_text())
        for key, value in changes.items():
            if value is None:
                data.pop(key, None)
            else:
                data[key] = value
        self.s.definition.write_text(yaml.safe_dump(data, sort_keys=False, width=1000))

    def test_a_good_node_definition_passes_the_check_play(self):
        status, output = self.s.playbook()
        self.assertNotEqual(status, 0)
        self.assertIn("fake incus: launch", output)
        self.assertNotIn("$6$", output)

    def test_no_client_inventory(self):
        self.refused("uc_client_inventory must be the absolute path", inventory=None)

    def test_relative_client_inventory(self):
        self.refused("uc_client_inventory must be the absolute path", inventory="uc/example-org/uc-inventory")

    def test_client_inventory_without_intake(self):
        other = self.s.base / "other"
        other.mkdir()
        self.refused("uc_client_inventory must be the absolute path", inventory=str(other))

    def test_node_definition_not_in_the_client_inventory(self):
        outside = self.s.base / "raw.example.org.yml"
        shutil.move(self.s.definition, outside)
        self.refused("has no node definition for raw.example.org in intake/", definition=outside)

    def test_intake_file_describes_another_node(self):
        # The node definition passed says raw.example.org, but the file of
        # that name in intake/ is for another domain.
        outside = self.s.base / "raw.example.org.yml"
        shutil.copy(self.s.definition, outside)
        self.rewrite_definition(client_domain="example.net")
        self.refused("or the one there describes another node", definition=outside)

    def test_a_field_the_build_does_not_know(self):
        self.rewrite_definition(foomuuri_ssh_port=2222)
        output = self.refused("sets foomuuri_ssh_port, which is not a node definition field")
        self.assertIn("Remove it", output)

    def test_several_fields_the_build_does_not_know(self):
        self.rewrite_definition(users=[{"name": "root"}], ssh_client_options="-o StrictHostKeyChecking=no")
        self.refused("sets users, ssh_client_options, which are not node definition fields")

    def test_another_platforms_field(self):
        # node_address is the ssh platform's, so an Incus node definition
        # may not set it.
        self.rewrite_definition(node_address="203.0.113.10")
        self.refused("sets node_address, which is not a node definition field")

    def test_only_known_fields_pass(self):
        self.rewrite_definition(node_label="raw", platform="incus", ssh_port=22, ssh_sources=["198.51.100.10/32"])
        status, output = self.s.playbook()
        self.assertIn("fake incus: launch", output)
        self.assertNotIn("not a node definition field", output)

    def test_an_extra_variable_on_the_command_line_is_allowed(self):
        status, output = self.s.playbook("-e", "uc_raw_node_adopt=true")
        self.assertIn("fake incus: launch", output)
        self.assertNotIn("not a node definition field", output)

    def test_hash_in_the_node_definition(self):
        for key in ("root_password_hash", "initial_password_hash"):
            with self.subTest(key=key):
                self.rewrite_definition(**{key: "made-up, not a hash"})
                output = self.refused("Make a batch with scripts/new-batch")
                self.assertNotIn("made-up, not a hash", output)
                self.rewrite_definition(**{key: None})

    def test_no_batch_named(self):
        self.rewrite_definition(raw_node_batch=None)
        self.refused("The node definition has no raw_node_batch")

    def test_bad_batch_name(self):
        self.rewrite_definition(raw_node_batch="raw-EXAMPLE-01")
        self.refused("raw_node_batch must be a batch name")

    def test_missing_batch_file(self):
        self.rewrite_definition(raw_node_batch="raw-1970-01-01-99")
        output = self.refused("there is no file")
        self.assertIn("scripts/new-batch raw-1970-01-01-99", output)

    def test_badly_protected_batch_file(self):
        self.s.batch.chmod(0o644)
        self.refused("is mode 0644, not 0600")

    def test_badly_protected_secrets_root(self):
        self.s.root.chmod(0o755)
        self.refused("is mode 0755, not 0700")

    def test_batch_without_hashes(self):
        self.s.batch.write_text("root_password_hash: 'made-up'\ninitial_password_hash: 'made-up'\n")
        self.s.batch.chmod(0o600)
        self.refused("they are not SHA-512 or yescrypt crypt hashes")


class Build(unittest.TestCase):
    """scripts/build, with a fake ansible-playbook that records its call."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.inventory = helpers.make_client_inventory(base)
        (self.inventory / "intake" / "raw.example.org.yml").write_text("client_domain: example.org\n")
        self.bin = base / "bin"
        self.bin.mkdir()
        self.record = base / "record"
        fake = self.bin / "ansible-playbook"
        fake.write_text(f'#!/bin/sh\npwd > {self.record}\nfor a in "$@"; do echo "$a" >> {self.record}; done\n')
        fake.chmod(0o755)
        self.env = dict(os.environ, PATH=f"{self.bin}{os.pathsep}{os.environ['PATH']}")

    def tearDown(self):
        self.tmp.cleanup()

    def run_build(self, *argv, cwd=None):
        return subprocess.run([sys.executable, str(helpers.REPO / "scripts" / "build"), *argv],
                              env=self.env, cwd=cwd or self.tmp.name, capture_output=True, text=True)

    def test_runs_the_playbook_from_the_repository(self):
        relative = os.path.relpath(self.inventory, self.tmp.name)
        result = self.run_build(relative, "raw.example.org", "--ask-become-pass", "-e", "uc_raw_node_adopt=true")
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = self.record.read_text().splitlines()
        self.assertEqual(lines[0], str(helpers.REPO))
        self.assertEqual(lines[1:], [
            "build.yml",
            "-e", f"@{self.inventory}/intake/raw.example.org.yml",
            "-e", f"uc_client_inventory={self.inventory}",
            "--ask-become-pass", "-e", "uc_raw_node_adopt=true",
        ])
        self.assertIn(f"uc_client_inventory={self.inventory}", result.stdout)

    def test_refuses_a_node_not_in_intake(self):
        result = self.run_build(str(self.inventory), "dev.example.org")
        self.assertEqual(result.returncode, 2)
        self.assertIn("has no intake/dev.example.org.yml", result.stderr)
        self.assertFalse(self.record.exists())

    def test_refuses_a_missing_inventory(self):
        result = self.run_build(str(self.inventory.parent / "nowhere"), "raw.example.org")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.record.exists())

    def test_refuses_a_path_as_fqdn(self):
        result = self.run_build(str(self.inventory), "../raw.example.org")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.record.exists())


class NewNode(unittest.TestCase):
    """scripts/new-node, answering its questions on standard input."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.inventory = helpers.make_client_inventory(self.base)
        self.root = helpers.make_secrets_root(self.base)
        self.key = helpers.make_ssh_key(self.base)
        self.defaults = self.inventory / "intake" / "defaults.yml"
        self.defaults.write_text(yaml.safe_dump({
            "client_domain": "example.org",
            "initial_username": "initial",
            "ssh_public_key": str(self.key),
            "ssh_port": 22,
            "ssh_sources": ["198.51.100.10/32"],
        }, sort_keys=False))
        self.env = dict(os.environ, HOME=str(self.base), UC_NODE_SECRETS_DIR=str(self.root))

    def tearDown(self):
        self.tmp.cleanup()

    def run_new_node(self, answers):
        return subprocess.run([sys.executable, str(helpers.REPO / "scripts" / "new-node"), str(self.inventory)],
                              input="".join(a + "\n" for a in answers), env=self.env,
                              capture_output=True, text=True, timeout=60)

    # Use the defaults, node label, platform, batch, then write.
    GOOD = ["y", "dev", "incus", helpers.BATCH, "y"]

    def test_writes_intake_without_hashes(self):
        helpers.make_batch(self.root)
        result = self.run_new_node(self.GOOD)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        path = self.inventory / "intake" / "dev.example.org.yml"
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o644)
        text = path.read_text()
        self.assertNotIn("hash", text.split("No secrets")[1].split("\n", 2)[2])
        self.assertNotIn("$6$", text)
        data = yaml.safe_load(text)
        self.assertEqual(data["raw_node_batch"], helpers.BATCH)
        self.assertEqual(list(data), ["client_domain", "node_label", "platform", "initial_username",
                                      "ssh_public_key", "ssh_port", "ssh_sources", "raw_node_batch"])
        self.assertEqual(data["ssh_public_key"], self.key.read_text().strip())
        self.assertNotIn("does not exist", result.stdout)
        self.assertNotIn("No defaults file", result.stdout)
        # Building is a later step of the guides, so no build command is shown.
        self.assertNotIn("scripts/build", result.stdout)

    def test_the_file_meets_the_client_inventory_yamllint(self):
        if shutil.which("yamllint") is None:
            self.skipTest("yamllint not on PATH")
        result = self.run_new_node(self.GOOD)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        config = ("{extends: default, rules: {document-start: disable, "
                  "indentation: {indent-sequences: consistent}, line-length: {max: 120}}}")
        lint = subprocess.run(["yamllint", "-d", config, str(self.inventory / "intake")],
                              capture_output=True, text=True)
        self.assertEqual(lint.returncode, 0, lint.stdout)

    def test_warns_when_the_batch_file_is_missing(self):
        result = self.run_new_node(self.GOOD)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("does not exist", result.stdout)
        self.assertIn(f"scripts/new-batch {helpers.BATCH}", result.stdout)

    def test_refuses_a_bad_batch_name_then_asks_again(self):
        result = self.run_new_node(["y", "dev", "incus", "raw-1970-02-30-01", helpers.BATCH, "y"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("real date", result.stdout)

    def test_refuses_defaults_with_a_hash(self):
        for text in ("root_password_hash: x\n", "initial_password_hash: x\n",
                     "note: '$6$abcdefgh$ijklmnopqrstuvwxyz0123456789'\n"):
            with self.subTest(text=text):
                self.defaults.write_text("client_domain: example.org\n" + text)
                result = self.run_new_node(self.GOOD)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("holds a password hash", result.stderr)
                self.assertFalse((self.inventory / "intake" / "dev.example.org.yml").exists())

    def without_defaults(self, domain_answers):
        """Every question answered, with no defaults file: the client domain
        answers, the node label, the platform, the initial user, the key
        (Enter first, which has no default), the port, the sources, the
        batch, and the write question."""
        self.defaults.unlink()
        return self.run_new_node([*domain_answers, "dev", "incus", "", "", str(self.key), "", "", helpers.BATCH, "y"])

    def test_says_when_there_is_no_defaults_file(self):
        result = self.without_defaults(["example.org"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("No defaults file", result.stdout)
        self.assertIn("defaults.yml does not exist", result.stdout)
        # No key is offered: Enter asks again.
        self.assertIn("(a key line, or the path to a .pub file) []", result.stdout)
        self.assertIn("A value is needed", result.stdout)
        self.assertNotIn("id_ed25519.pub]", result.stdout)
        data = yaml.safe_load((self.inventory / "intake" / "dev.example.org.yml").read_text())
        self.assertEqual(data["ssh_public_key"], self.key.read_text().strip())

    def test_the_client_domain_prompt_gives_an_example(self):
        result = self.without_defaults(["example.org"])
        self.assertIn("Client domain, the node is named <node label>.<client domain> (for example example.org) []",
                      result.stdout)

    def test_asks_again_when_the_domain_does_not_match_the_client(self):
        result = self.without_defaults(["example.com", "n", "example.org"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("client example-org, and example.com does not match it", result.stdout)
        self.assertTrue((self.inventory / "intake" / "dev.example.org.yml").exists())
        self.assertFalse((self.inventory / "intake" / "dev.example.com.yml").exists())

    def test_keeps_a_domain_that_does_not_match_when_confirmed(self):
        result = self.without_defaults(["example.com", "y"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.inventory / "intake" / "dev.example.com.yml").exists())

    def test_refuses_a_defaults_setting_it_does_not_offer(self):
        # initial_user was the setting's name before it took the node
        # definition's, initial_username.
        for key in ("initial_user", "foomuuri_ssh_port", "node_address"):
            with self.subTest(key=key):
                self.defaults.write_text(f"client_domain: example.org\n{key}: x\n")
                result = self.run_new_node(self.GOOD)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f"sets {key}, which new-node does not offer", result.stderr)
                self.assertFalse((self.inventory / "intake" / "dev.example.org.yml").exists())

    def test_the_initial_user_setting_is_the_node_definitions_name(self):
        self.defaults.write_text(self.defaults.read_text().replace("initial_username: initial", "initial_username: admin"))
        result = self.run_new_node(self.GOOD)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = yaml.safe_load((self.inventory / "intake" / "dev.example.org.yml").read_text())
        self.assertEqual(data["initial_username"], "admin")

    def test_writes_only_fields_the_build_allows(self):
        platforms = yaml.safe_load((helpers.REPO / "inventory" / "group_vars" / "all" / "platforms.yml").read_text())
        result = self.run_new_node(self.GOOD)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = yaml.safe_load((self.inventory / "intake" / "dev.example.org.yml").read_text())
        allowed = (platforms["node_required_fields"] + platforms["node_optional_fields"]
                   + platforms["platforms"]["incus"]["required_fields"])
        self.assertEqual([field for field in data if field not in allowed], [])

    def test_never_asks_for_a_password(self):
        result = self.run_new_node(self.GOOD)
        self.assertNotIn("assword", result.stdout)


if __name__ == "__main__":
    unittest.main()
