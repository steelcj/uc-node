"""uc_sudo_rules: read `sudo -l -U <user>`, for the confirmation's sudo field.

The raw node contract's sudo field says whether the initial user can use
sudo. Group membership misses a sudoers rule that names the user directly,
so tasks/confirmation.yml asks sudo itself, as root:

    sudo -l -U <user>

and gives this filter its standard output, its exit code and the user:

    {{ result.stdout | uc_sudo_rules(result.rc, initial_username) }}

It returns "yes" when sudo lists at least one rule the user may run, "no"
when sudo says the user may not run sudo, and "unknown" for anything else:
a non-zero exit, such as "sudo: unknown user", or output in neither form.
The confirmation task fails the build on "unknown" rather than guess.

sudo 1.9.16 on Debian 13 prints, with LC_ALL=C and exit code 0 in both cases:

    User initial may run the following commands on dev:
        (ALL : ALL) ALL

    User initial is not allowed to run sudo on dev.

Each rule is an indented line under the "may run" line. The "Matching
Defaults entries" block above it lists settings, not rules, and is skipped.
"""
from __future__ import annotations

import re


def uc_sudo_rules(stdout, rc, user):
    if int(rc) != 0:
        return "unknown"
    name = re.escape(str(user))
    allowed = re.compile(rf"^User {name} may run the following commands on \S+:$")
    refused = re.compile(rf"^User {name} is not allowed to run sudo on \S+\.$")
    lines = str(stdout).splitlines()
    for index, line in enumerate(lines):
        if refused.match(line):
            return "no"
        if allowed.match(line):
            rules = []
            for rule in lines[index + 1:]:
                if not rule.strip():
                    break
                if not rule[:1].isspace():
                    break
                rules.append(rule.strip())
            return "yes" if rules else "unknown"
    return "unknown"


class FilterModule:
    def filters(self):
        return {"uc_sudo_rules": uc_sudo_rules}
