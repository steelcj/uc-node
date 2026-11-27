"""Tests for egress: templates/confirmation.yml.j2 and templates/candidate.yml.j2.

Each template is rendered by Ansible's own template module, from a fixture in
tests/fixtures/, with values from the safe values register. The rendered
confirmation is read as a consumer must read it, every value a string, and,
when UC_CONTROLLER names a uc-controller checkout, checked with its
scripts/check_raw_confirmation.py. The rendered candidate is put into a
temporary client inventory and checked with its scripts/check_inventory.py.

    UC_CONTROLLER=<uc-controller checkout> python3 tests/run_tests.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

import helpers

PLAYBOOK = helpers.REPO / "tests" / "playbooks" / "render-template.yml"
CONFIRMATION = helpers.REPO / "templates" / "confirmation.yml.j2"
CANDIDATE = helpers.REPO / "templates" / "candidate.yml.j2"
CONTROLLER = os.environ.get("UC_CONTROLLER", "")
CONTRACT_FIELDS = ["contract", "baseline", "timestamp", "machine_id", "user", "sudo", "sudo_nopasswd",
                   "ssh_port", "ssh_password_auth", "ssh_host_keys", "firewall", "firewall_active",
                   "python", "interfaces"]
INTERFACE_FIELDS = ["name", "type", "mac", "state", "default_route4", "default_route6", "ip", "ip6"]
CANDIDATE_FIELDS = ["address", "ssh_port", "fingerprint", "raw_node_batch", "node_label", "platform",
                    "producer", "producer_version", "contract", "built"]
# The values that are not strings, in the contract and in the candidate.
NOT_STRINGS = {"sudo", "sudo_nopasswd", "ssh_port", "ssh_password_auth", "firewall_active",
               "default_route4", "default_route6"}


def render(template: Path, fixture: Path, output: Path) -> None:
    env = dict(os.environ, ANSIBLE_NOCOLOR="1")
    env.pop("ANSIBLE_CONFIG", None)
    result = subprocess.run(
        ["ansible-playbook", str(PLAYBOOK), "-e", f"@{fixture}",
         "-e", f"uc_test_template={template}", "-e", f"uc_test_output={output}"],
        cwd=helpers.REPO, env=env, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)


def lines_with_values(text: str):
    """(key, value text) for every 'key: value' line, and list items."""
    for line in text.splitlines():
        stripped = line.strip().removeprefix("- ")
        if stripped.startswith("#") or ":" not in stripped:
            continue
        key, _, value = stripped.partition(": ")
        if value:
            yield key, value


def checker_available():
    return bool(CONTROLLER) and (Path(CONTROLLER) / "scripts" / "check_raw_confirmation.py").is_file()


@unittest.skipUnless(shutil.which("ansible-playbook"), "ansible-playbook not on PATH")
class Confirmation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name) / "confirmation.yml"

    def tearDown(self):
        self.tmp.cleanup()

    def rendered(self, name):
        render(CONFIRMATION, helpers.FIXTURES / "confirmation" / f"{name}.yml", self.out)
        return self.out.read_text()

    def check(self, text):
        result = subprocess.run([sys.executable, str(Path(CONTROLLER) / "scripts" / "check_raw_confirmation.py"),
                                 "-", "--user", "initial", "--port", "22"],
                                input=text, capture_output=True, text=True)
        return json.loads(result.stdout)

    def test_fields_in_the_contract_order(self):
        for name in ("incus-node", "digits-only"):
            with self.subTest(fixture=name):
                data = yaml.load(self.rendered(name), Loader=yaml.BaseLoader)
                self.assertEqual(len(data), 1)
                body = next(iter(data.values()))
                self.assertEqual(list(body), CONTRACT_FIELDS)
                for interface in body["interfaces"]:
                    self.assertEqual(list(interface), INTERFACE_FIELDS)

    def test_every_string_is_double_quoted(self):
        for name in ("incus-node", "digits-only"):
            with self.subTest(fixture=name):
                for key, value in lines_with_values(self.rendered(name)):
                    if key in NOT_STRINGS:
                        self.assertRegex(value, r"^(true|false|[0-9]+)$", key)
                    elif value.startswith("["):
                        self.assertEqual(json.loads(value), [str(v) for v in json.loads(value)], key)
                    else:
                        self.assertRegex(value, r'^".*"$', key)

    def test_values_survive_a_yaml_1_1_reader(self):
        """The safe loader, as Ansible reads YAML, keeps the strings strings."""
        data = yaml.safe_load(self.rendered("digits-only"))["dev"]
        self.assertEqual(data["machine_id"], "19700101000000000000000000000022")
        self.assertEqual(data["baseline"], "1.0")
        self.assertEqual(data["contract"], "0.3.1")
        self.assertEqual(data["timestamp"], "1970-01-01T00:00:00-05:00")
        self.assertIs(data["sudo"], True)
        self.assertEqual(data["ssh_port"], 22)
        self.assertEqual(data["interfaces"][1]["ip"], [])
        self.assertEqual(data["python"], "")

    @unittest.skipUnless(checker_available(), "UC_CONTROLLER does not name a uc-controller checkout")
    def test_passes_check_raw_confirmation(self):
        for name in ("incus-node", "digits-only"):
            with self.subTest(fixture=name):
                result = self.check(self.rendered(name))
                self.assertEqual(result["result"], "pass", result["findings"])

    @unittest.skipUnless(checker_available(), "UC_CONTROLLER does not name a uc-controller checkout")
    def test_a_node_that_breaks_the_contract_fails_the_check(self):
        result = self.check(self.rendered("sudo-nopasswd"))
        self.assertEqual(result["result"], "fail")
        clauses = {f["clause"] for f in result["findings"] if f["severity"] == "fail"}
        self.assertEqual(clauses, {"RN-ACC-07", "RN-SSH-03"})


@unittest.skipUnless(shutil.which("ansible-playbook"), "ansible-playbook not on PATH")
class Candidate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.inventory = helpers.make_client_inventory(Path(self.tmp.name))
        self.out = self.inventory / "candidates" / "dev.example.org.yml"
        render(CANDIDATE, helpers.FIXTURES / "candidate" / "dev.example.org.yml", self.out)
        self.text = self.out.read_text()

    def tearDown(self):
        self.tmp.cleanup()

    def test_fields_in_the_design_order(self):
        data = yaml.load(self.text, Loader=yaml.BaseLoader)
        self.assertEqual(list(data), ["dev.example.org"])
        self.assertEqual(list(data["dev.example.org"]), CANDIDATE_FIELDS)

    def test_values_are_quoted(self):
        for key, value in lines_with_values(self.text):
            if key == "ssh_port":
                self.assertEqual(value, "22")
            else:
                self.assertRegex(value, r'^".*"$', key)
        data = yaml.safe_load(self.text)["dev.example.org"]
        self.assertEqual(data["contract"], "0.3.1")
        self.assertEqual(data["producer_version"], "0.3.0")
        self.assertEqual(data["built"], "1970-01-01T00:00:00-05:00")

    def test_meets_the_client_inventory_yamllint(self):
        if shutil.which("yamllint") is None:
            self.skipTest("yamllint not on PATH")
        config = ("{extends: default, rules: {document-start: disable, "
                  "indentation: {indent-sequences: consistent}, line-length: {max: 120}}}")
        lint = subprocess.run(["yamllint", "-d", config, str(self.out)], capture_output=True, text=True)
        self.assertEqual(lint.returncode, 0, lint.stdout)

    @unittest.skipUnless(CONTROLLER and (Path(CONTROLLER) / "scripts" / "check_inventory.py").is_file(),
                         "UC_CONTROLLER does not name a uc-controller checkout")
    def test_passes_check_inventory(self):
        result = subprocess.run([sys.executable, str(Path(CONTROLLER) / "scripts" / "check_inventory.py"),
                                 str(self.inventory)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
