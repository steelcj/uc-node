---
title: Platforms for uc-node, Phase Five Prompt
description: The prompt for phase five of the platforms work, which finishes the items phase four missed and corrects its report.
version: 0.1.0
status: provisional
date: 2026-11-24
language: en-CA
---

# Platforms for uc-node, Phase Five Prompt

Phase four ran from an earlier draft of its prompt, so some items in the final draft were not done. This phase finishes them.

## Prompt

```text
Phase four is good. Phase five finishes what it missed. Work on the platforms branch, in this order:

1. Correct the phase four report first, while fb69992 is still the last commit, and amend fb69992 rather than adding a commit:
   - The value in the secrets guide's old search example was made up, not part of a real password. Reword that paragraph: say the example now uses the SECRET variable, like the example above it, so it can't be mistaken for a real secret. Don't quote the old value, and drop the advice to rotate a password. If the secrets guide still has a literal example value anywhere, use EXAMPLE-NOT-A-SECRET, and include that change in the amend.
   - Add a section on the VPS adoption test, using en/docs/sessions/vps-adoption-test.md as the source: the old node definition refused, the placeholder address passing the check play (since fixed in 55ef0c1), the key not offered under IdentitiesOnly, the adoption build, the second build (changed=1, only the reboot), and the node checks. Use 203.0.113.10 and example.org, never the real address, domain or key file names. Don't commit vps-adoption-test.md.

2. Build the check play's refusal of connection variables, instead of leaving it in the ROADMAP: refuse a node definition that sets ansible_host, ansible_user, ansible_port, ansible_ssh_common_args or ansible_ssh_host_key_checking, with a message saying the platform's create play sets them. Allow ansible_become_password. Remove the ROADMAP item. Run yamllint, ansible-lint, the ssh syntax check and two Incus builds, and commit.

3. Add en/docs/known-issues/, with one document each:
   - foomuuri-cloud-init-ordering-cycle.md: the symptom, how to confirm it (sudo journalctl -b SYSLOG_IDENTIFIER=systemd), and what uc-node does (cloud-init disabled before the first reboot, the boot timeout, the cycle check), linking to https://github.com/steelcj/ansible-role-foomuuri/blob/main/en/docs/known-issues/cloud-init-ordering-cycle.md
   - robertdebock.reboot reporting changed without rebooting
   - PerSourcePenalties lockouts and how to recover
   - AuthorizedKeysCommand none: the /usr/bin/true workaround, which sshd runs as nobody (confirmed on the VPS)
   Link them from the ssh guide, the platform guide, the README and the ROADMAP, where those already discuss the issue. Commit.

4. Add a "Known issues" section to CLAUDE.md (create it if needed), with a few lines each on the ordering cycle, PerSourcePenalties lockouts and keys not offered because of IdentitiesOnly, each linking to its note. Commit.

5. In en/docs/sessions/README.md, add the kind phase-<number>-prompt ("The prompt that starts one phase, with the decisions taken since the last report", written by Claude, in chat, before the phase starts), version 0.1.5 with a changelog row. Rename 2026-11-24--18-22-41-uc-node-platforms-phase4-prompt.md to 2026-11-24--18-22-41-uc-node-platforms-phase-four-prompt.md and add front matter as the README describes, keeping its prompt text as it was sent. Commit both, together with this file, 2026-11-24--19-15-15-uc-node-platforms-phase-five-prompt.md.

6. Write the phase five report, named by the sessions README:
   touch "en/docs/sessions/$(date +%Y-%m-%d--%H-%M-%S)-uc-node-platforms-phase-five-report.md"
   with the README's front matter, version 0.1.0, status provisional. Cover each item above, its commit and its checks, and commit it.

Nothing is pushed or tagged.
```

## Changelog

| Version | Date       | Change        |
| :------ | :--------- | :------------ |
| 0.1.0   | 2026-11-24 | First version |
