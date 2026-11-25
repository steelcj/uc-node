---
title: Platforms for uc-node, Phase Five Report
description: What phase five of the platforms work changed, each item's commit and checks, and what to know after it.
version: 0.1.0
status: provisional
date: 2026-11-24
language: en-CA
---

# Platforms for uc-node, Phase Five Report

Phase five finishes the items phase four missed, since phase four ran from an earlier draft of its prompt. Everything is committed on the `platforms` branch. Nothing was pushed or tagged, and `VERSION` is unchanged.

| Item | Commit |
| :-- | :-- |
| The phase four report corrected | `911b6af`, amending `fb69992` |
| Connection variables refused in a node definition | `1dd752e` |
| Known issues in `en/docs/known-issues/` | `e95fdf0` |
| `CLAUDE.md` with the known issues | `5a5034a` |
| Phase prompts in the session records | `844ffec` |
| This report | The commit after `844ffec` |

## The phase four report

`fb69992` was still the last commit, so it was amended rather than followed by a new one. The amend became `911b6af` once its message said what it holds.

- The secrets guide paragraph now says its search example uses the `SECRET` variable, like the example above it, so it cannot be mistaken for a real secret. It does not quote the old value, and the advice to rotate a password is gone.
- The secrets guide had two more literal values, and the amend includes both fixes, in version 0.1.2. The replacements example became `EXAMPLE-NOT-A-SECRET==>REDACTED`. The sentence before the search said to replace `THE-SECRET`, which no command used, so it now matches the `read -rs SECRET` commands.
- A new section, The VPS adoption test, covers the old node definition refused, the placeholder address that passed the check play and was fixed in `55ef0c1`, the key not offered under `IdentitiesOnly`, the adoption build, the second build with `changed=1`, and the node checks. It uses `203.0.113.10` and `example.org`. The real address, domain and key file names do not appear, and `vps-adoption-test.md` is not committed.

## Connection variables in a node definition

The check play refuses a node definition that sets `ansible_host`, `ansible_user`, `ansible_port`, `ansible_ssh_common_args` or `ansible_ssh_host_key_checking`, with "The node definition sets ansible_user. The platform's create play sets the connection variables, so remove ansible_user from the node definition." `ansible_become_password` is allowed.

- The list is data, `node_connection_variables` in `inventory/group_vars/all/platforms.yml`, with a comment saying why.
- A node definition is passed with `-e`, so it applies to localhost too. In the check play, a connection variable can only have a value if the node definition gave it one, because nothing in the inventory sets these for localhost.
- One exception: Ansible gives localhost `ansible_host: localhost`, its inventory name. The first version of the check refused every node definition because of it, so `ansible_host` is compared with `inventory_hostname`.
- The ROADMAP item is removed. The README's node definition rules, the CHANGELOG's Unreleased entry and the platform guide's create play contract mention the refusal.

### Checks

| Check | Result |
| :-- | :-- |
| Each of the five variables in an ssh node definition | Each refused, by name |
| `ansible_become_password` in an ssh node definition | Passed this check, and stopped at the next one, an invalid label set on purpose so that nothing connected |
| `yamllint .` | Clean |
| `ansible-lint` | Passes, production profile |
| `--syntax-check` with an ssh node definition in `/tmp` | Passes |
| Incus, two builds from a fresh instance | `changed=15` then `changed=1` (only the reboot), `running`, `hostname -f` is `raw.example.org` |

## Known issues

`en/docs/known-issues/` holds four notes, each with front matter, version 0.1.0, provisional:

| Note | What it covers |
| :-- | :-- |
| `foomuuri-cloud-init-ordering-cycle.md` | The symptom, the cycle with its full chain of units, how to confirm it with `sudo journalctl -b SYSLOG_IDENTIFIER=systemd`, why the filter matters, the Incus console log, and what uc-node does: cloud-init disabled before the first reboot, the boot timeout, and the cycle check. Links to the note in steelcj.foomuuri |
| `robertdebock-reboot-reports-changed-without-rebooting.md` | Why the role reports a reboot that did not happen, from its tasks: a backgrounded `sleep` and shutdown under `async: 1, poll: 0`, with `failed_when: false`, then a wait that succeeds if the host never went down. How to confirm it, and `ansible.builtin.reboot`'s boot ID check |
| `openssh-per-source-penalties-lockout.md` | What the lockout looks like, the cause, how to recover, and how uc-node avoids it: one try per login, `IdentitiesOnly=yes`, and the `~/.ssh/config` entry |
| `robertdebock-openssh-authorized-keys-command-none.md` | The log line, why sshd tries to run `none`, and the `/usr/bin/true` workaround, which sshd runs as `nobody`, as confirmed on the VPS |

The notes are linked where each issue was already discussed:

| Document | Links |
| :-- | :-- |
| `en/docs/guides/3-build-a-node-on-an-ssh-host.md`, version 0.1.1 | The cycle, from Why cloud-init is disabled and the ordering cycle error. The reboot, from the adoption build. PerSourcePenalties, from the lockout section |
| `en/docs/guides/add-a-new-platform.md`, version 0.2.1 | PerSourcePenalties, the cycle and the reboot, from their paragraphs |
| `README.md` | The reboot and the cycle, from the list of what a build does, and `en/docs/known-issues/` in the layout table |
| `ROADMAP.md` | The cycle and AuthorizedKeysCommand, from their items |

The ssh guide does not discuss AuthorizedKeysCommand, as phase four decided, so it has no link to that note.

### Checks

Every link and anchor in the README, ROADMAP, CHANGELOG, both guides and the four notes resolves. None has an em dash, a table without `| :-- |`, or a number in a heading. No file in the repository names a client, a real address or a secret fragment. The link to the note in steelcj.foomuuri was not fetched, since this phase contacted no remote service.

## CLAUDE.md

There was no `CLAUDE.md`, so it was created with a one-line introduction and a Known issues section. It has a few lines each on the ordering cycle, PerSourcePenalties lockouts, and keys not offered because of `IdentitiesOnly`, each linking to its note. Keys not offered have no note of their own, so that entry links to the PerSourcePenalties note's section on how uc-node avoids lockouts, and to the ssh guide's `~/.ssh/config` section.

## Phase prompts in the session records

- The sessions README adds the kind `phase-<number>-prompt`, "The prompt that starts one phase, with the decisions taken since the last report", written by Claude, in chat, before the phase starts. Version 0.1.5, with a changelog row.
- The rename target, `2026-11-24--18-22-41-uc-node-platforms-phase-four-prompt.md`, already existed. It held a later draft of the phase four prompt, different from the sent one in `...-phase4-prompt.md`, so a rename would have overwritten it. You chose to keep the sent prompt. The file now holds the front matter, the title, a line saying what was attached, the sent text from `## Prompt` to its end, unchanged, and a changelog. `...-phase4-prompt.md` is removed. Neither had been committed, so the later draft is gone. The items it added are the ones this phase finished.
- The phase five prompt is committed as it was written.

The sent text is recorded as the file held it. It differs in places from the message Claude Code received for phase four. In the file, step one says the README's blank line was "already removed". The message said to remove it, which phase four did.

## Things to know

- `vps-adoption-test.md` is still in `en/docs/sessions/`, untracked, as asked.
- The test instance, `/tmp/uc-node-check/` and the test files in the scratchpad directory are deleted.
- The rest of the earlier notes still applies: every ssh build needs `--ask-become-pass`, the first build of a host keeps `ssh_port: 22`, and the remaining work is in the ROADMAP.

## Changelog

| Version | Date | Change |
| :-- | :-- | :-- |
| 0.1.0 | 2026-11-24 | First version, from the end of phase five |
