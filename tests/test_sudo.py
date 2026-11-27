"""Tests for plugins/filter/uc_sudo.py, which reads `sudo -l -U <user>` for the
confirmation's sudo field.

The fixtures in tests/fixtures/sudo/ are the output of sudo 1.9.16p2 on
Debian 13, with LC_ALL=C, the host renamed dev and the user initial:

    allowed-by-group.txt   initial in the group sudo, allowed by %sudo
    allowed-by-rule.txt    initial in no sudo group, allowed by a rule in
                           /etc/sudoers.d naming initial. sudo prints the
                           same as for the group, which is the point: the
                           old measure, the user's groups, said false here
    no-rule.txt            initial with no rule at all

sudo exits 0 for all three, and 1 for an unknown user.
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import unittest

import helpers

SPEC = importlib.util.spec_from_file_location("uc_sudo", helpers.REPO / "plugins" / "filter" / "uc_sudo.py")
uc_sudo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(uc_sudo)

FIXTURES = helpers.FIXTURES / "sudo"


def fixture(name):
    return (FIXTURES / f"{name}.txt").read_text()


class SudoRules(unittest.TestCase):
    def test_a_user_allowed_by_group(self):
        self.assertEqual(uc_sudo.uc_sudo_rules(fixture("allowed-by-group"), 0, "initial"), "yes")

    def test_a_user_allowed_by_a_rule_naming_the_user(self):
        self.assertEqual(uc_sudo.uc_sudo_rules(fixture("allowed-by-rule"), 0, "initial"), "yes")

    def test_a_user_with_no_rule(self):
        self.assertEqual(uc_sudo.uc_sudo_rules(fixture("no-rule"), 0, "initial"), "no")

    def test_an_unknown_user_is_unknown(self):
        self.assertEqual(uc_sudo.uc_sudo_rules("", 1, "initial"), "unknown")

    def test_a_non_zero_exit_is_unknown_whatever_the_output(self):
        self.assertEqual(uc_sudo.uc_sudo_rules(fixture("allowed-by-group"), 1, "initial"), "unknown")

    def test_another_users_answer_is_unknown(self):
        self.assertEqual(uc_sudo.uc_sudo_rules(fixture("allowed-by-group"), 0, "operator"), "unknown")

    def test_a_may_run_line_without_rules_is_unknown(self):
        self.assertEqual(uc_sudo.uc_sudo_rules("User initial may run the following commands on dev:\n", 0, "initial"),
                         "unknown")

    def test_output_in_another_form_is_unknown(self):
        for text in ("", "sudo: a terminal is required to read the password\n",
                     "Matching Defaults entries for initial on dev:\n    env_reset\n"):
            with self.subTest(text=text):
                self.assertEqual(uc_sudo.uc_sudo_rules(text, 0, "initial"), "unknown")

    def test_a_user_name_is_matched_whole(self):
        # "init" must not match the line for "initial", nor a regex wildcard.
        self.assertEqual(uc_sudo.uc_sudo_rules(fixture("allowed-by-group"), 0, "init"), "unknown")
        self.assertEqual(uc_sudo.uc_sudo_rules(fixture("allowed-by-group"), 0, "in.tial"), "unknown")


@unittest.skipUnless(shutil.which("ansible"), "ansible not on PATH")
class SudoRulesInAnsible(unittest.TestCase):
    """The filter loads through ansible.cfg's filter_plugins, as the build
    uses it."""

    def test_the_filter_loads_from_ansible_cfg(self):
        env = dict(os.environ, ANSIBLE_NOCOLOR="1")
        env.pop("ANSIBLE_CONFIG", None)
        for name, expected in (("allowed-by-rule", "yes"), ("no-rule", "no")):
            with self.subTest(name=name):
                result = subprocess.run(
                    ["ansible", "localhost", "-m", "ansible.builtin.debug", "-a",
                     f"msg={{{{ lookup('ansible.builtin.file', '{FIXTURES / name}.txt') | uc_sudo_rules(0, 'initial') }}}}"],
                    cwd=helpers.REPO, env=env, capture_output=True, text=True, timeout=120)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(f'"msg": "{expected}"', result.stdout)


if __name__ == "__main__":
    unittest.main()
