---
title: Platforms for uc-node, Phase Four Report
description: What phase four of the platforms work changed, the checks it passed, and a summary of the whole piece of work, with what was not done or was decided against.
version: 0.1.0
status: provisional
date: 2026-11-24
language: en-CA
---

# Platforms for uc-node, Phase Four Report

Phase four is done and committed on the `platforms` branch as `69c0ca7`. The documents describe uc-node as it is now. `scripts/new-node` and the create play show the `~/.ssh/config` entry an ssh node needs, and the check play refuses a `node_address` that is not an address. Nothing was pushed or tagged, and `VERSION` is unchanged.

This is the last phase, so the report ends with a summary of the whole piece of work.

## Before phase four

| Change | Commit |
| :-- | :-- |
| The blank line before the closing `---` of `en/docs/sessions/README.md` removed, its version bumped to 0.1.4 with a changelog line, and committed with your `.gitignore` change | `9d90cdc` |
| The check play refuses a `node_address` that is not an IPv4 or IPv6 address | `55ef0c1` |

The first attempt at `9d90cdc` committed the README before the fix: the script that edited it stopped partway, and the commit after it still ran. It was not pushed, so the commit was amended.

### The address pattern

`scripts/new-node` did not check the address with a regular expression. It used Python's `ipaddress.ip_address`. So the rule is now one pattern, `node_address_pattern` in `inventory/group_vars/all/ssh.yml`, and both use it:

- the check play matches `node_address` against it, whenever a node definition sets one
- `scripts/new-node` matches the address against it, then writes it as `ipaddress` writes it, so an IPv6 address is in its short, lowercase form

The pattern agreed with `ipaddress` on 106,072 test addresses, random and hand-picked, valid and not. The one difference is a zone, as in `fe80::1%eth0`: `ipaddress` accepts it, and the pattern refuses it, since it is no use as a node's address.

In the check play, `<vps-address>`, `203.0.113.999`, `example.org`, `01.2.3.4` and `fe80::1%eth0` were refused. `203.0.113.10`, `2001:db8::10`, `::ffff:192.0.2.1` and `2001:DB8::A` were accepted. `scripts/new-node` refused and accepted the same.

## What changed in phase four

| File | Change |
| :-- | :-- |
| `scripts/new-node` | Prints the `~/.ssh/config` entry for an ssh node after writing its definition |
| `platforms/ssh/create.yml` | Prints the same entry when both logins are refused with `Permission denied`, before it stops |
| `README.md` | Rewritten |
| `en/docs/guides/3-build-a-node-on-an-ssh-host.md` | New |
| `en/docs/guides/add-a-new-platform.md` | Brought in line with what was built, version 0.2.0, provisional |
| `en/docs/guides/add-a-new-platform-to-the-node-creation-controller.md` | Deleted, a second copy of the platform guide |
| `en/docs/guides/setup-ex2-vps-node.md` | Deleted, its content is in the ssh guide |
| `en/docs/guides/1-setup-the-defaults-for-new-nodes.md` | `example.org`, the questions `scripts/new-node` always asks, and the heading without its number |
| `en/docs/guides/2-build-and-check-a-raw-node.md` | `raw.example.org.yml`, `raw-example-org`, the new checks, the refusal test with a `dev` node, and the heading without its number |
| `en/docs/guides/secrets/handle-secrets-committed-to-a-repository.md` | The worked example describes the leaked notes in general terms, and no example holds a literal value, version 0.1.2 |
| `ROADMAP.md` | Rewritten |
| `CHANGELOG.md` | Rewritten |

### The ~/.ssh/config entry

```text
# uc-node: raw.example.org
Host 203.0.113.10
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    # Optional, only for manual ssh/scp; the build passes the user itself
    User initial
```

The `IdentityFile` is the private key of `ssh_public_key`:

- in `scripts/new-node`, the `.pub` file the key was read from, or the matching `.pub` file in `~/.ssh/`, without `.pub`
- in the create play, the matching `.pub` file in `~/.ssh/` on the controller, without `.pub`
- in both, a placeholder when no file matches, `<path to the private key of ssh_public_key>`

`scripts/new-node` prints the entry only for the ssh platform, with a line saying to put it before any `Host *` block. The create play prints it when both probes failed and either was refused with `Permission denied`, and the message that stops the build points to it.

### The ssh guide

`3-build-a-node-on-an-ssh-host.md` takes its steps, the `~/.ssh/config` entry, the node checks and the `sudo` workaround from the adoption test, generalised to any node, with `raw.example.org` at `203.0.113.10`. It covers:

- what the build does on an SSH host, and why cloud-init is disabled, including that later network changes by the provider are not picked up
- a fresh install and an existing node, as two paths that meet at the adoption build
- checking an existing node by hand with `ssh -t`, and updating its old-format node definition and file name
- the `~/.ssh/config` entry: why it is needed, that the `Host` line must be the address since an alias with `HostName` does not match, that it goes before any `Host *` block, and that a new address needs a new entry and a new known_hosts line
- the host key check against the provider's console, including a node on another port, whose key is written under the bare address
- the adoption build with `--ask-become-pass`, the checks with `sudo journalctl -b SYSLOG_IDENTIFIER=systemd`, the remote checks, and later builds
- rebuilding a node made by an earlier version, including one stuck in `starting`
- what the ssh platform does not do yet, and getting back in when locked out
- troubleshooting by error message: each message the build or the tools print, as the heading or in a block under it, with its cause and fix

The `AuthorizedKeysCommand` check is left out, as you asked. The ROADMAP item about raising `none` with robertdebock.openssh is kept, because your instruction left keep or remove open, and the problem is still in the role.

### Documents

- The README is titled uc-node, the raw node controller. It describes the two platforms, what a build does, the layout, node definitions and the rule that values passed with `-e` override `inventory/group_vars/all/`, the naming table for the four labels, the requirements per platform, secrets, how to run it, and links to every guide under `en/docs/guides/`.
- The platform guide uses the ssh platform as its worked example: `platforms.yml`, the `when` blocks on localhost and the platform groups on the node, why group_vars are under the inventory, the create play's contract, adoption, the two connections, PerSourcePenalties and `IdentitiesOnly`, the host key, root's keys, the reboot module and boot checks, and the cloud-init ordering cycle.
- In the secrets guide, the search example now uses the `SECRET` variable, like the example above it, so it cannot be mistaken for a real secret. Its replacements example uses `EXAMPLE-NOT-A-SECRET`, and the sentence before the search matches the `read -rs SECRET` commands, in version 0.1.2.
- The ROADMAP keeps tagging steelcj.foomuuri, the four items from phase three, and the design documents, and adds refusing connection variables in a node definition, `confirmation.yml`, provider agents, DNS, firewall zones on hosts with more than one interface, and ordering hosts through a provider's API.
- The CHANGELOG has the Keep a Changelog and Semantic Versioning header, an Unreleased section for this work, and 0.1.0, 0.0.2 and 0.0.1 in plain words. Its headings keep `## [Unreleased]` and `## [X.Y.Z] - YYYY-MM-DD`, since `scripts/cut-release.py` and `scripts/publish-release.py` look for them.

## Checks in phase four

| Check | Result |
| :-- | :-- |
| `yamllint .` | Clean |
| `--syntax-check` with an Incus and an ssh node definition in `/tmp` | Both pass |
| `ansible-lint` | Passes, production profile |
| Incus, two builds from a fresh instance | `changed=15` then `changed=1` (only the reboot), `running`, `hostname -f` is `raw.example.org` |
| The create play against a local container that refuses the key | Prints the entry with the matching private key, then stops, each login tried once |
| `scripts/new-node`, with the default key, a key outside `~/.ssh`, a key line with no file, and an Incus node | The entry with `~/.ssh/id_ed25519`, with `~/keys/client`, with the placeholder, and no entry |
| Links and anchors in the README, ROADMAP, CHANGELOG and guides | All resolve |
| Em dashes, horizontal rules, tables without `\| :-- \|` | None |
| Numbers in headings | Only the CHANGELOG's version headings, which its format and the release scripts require |
| Client names, real addresses, secret fragments in the files in the repository | None |

The test container, `/tmp/uc-node-check/` and the test keys in the scratchpad directory are deleted.

## The VPS adoption test

After phase three, the ssh platform was tested on a real host, by hand. The test adopted an existing VPS that the old version, uc-raw-node, had built, and then ran a second build. It is written here with `raw.example.org` at `203.0.113.10`. The real address, domain and key file names are not recorded in the repository.

### Before the build

| Step | What happened | What changed in uc-node |
| :-- | :-- | :-- |
| The node by hand | `sudo` over `ssh` failed with `sudo: a terminal is required to read the password`. `ssh -t`, or logging in and running the commands on the node, worked | The ssh guide uses `ssh -t`, with logging in as the fallback |
| The old node definition | The check play refused it: "The node definition sets hostname, which is no longer used. Rename hostname to client_domain in the node definition." It was updated to `client_domain`, `node_label`, `platform` and `node_address`, keeping the secret values, and renamed to `raw.example.org.yml` | The ssh guide shows the update and the rename |
| A placeholder address | `node_address` still held the placeholder `<vps-address>`. The check play passed it, and both probes failed with `hostname contains invalid characters`, before anything reached the host | Fixed in `55ef0c1`: the check play refuses a `node_address` that is not an address |
| A key not offered | Both probes failed with `Permission denied (publickey)`, although `ssh -i` with the same key worked. The key was outside the default key files, and the build connects with `IdentitiesOnly=yes`. An entry in `~/.ssh/config` with `Host 203.0.113.10` fixed it. An entry for an alias, with `HostName 203.0.113.10`, did not | `scripts/new-node` and the create play print the entry, and the ssh guide documents it |

### The builds

The adoption build, with `-e uc_raw_node_adopt=true --ask-become-pass`:

```text
localhost                  : ok=14   changed=0    unreachable=0    failed=0    skipped=7    rescued=0    ignored=0
raw.example.org            : ok=139  changed=14   unreachable=0    failed=0    skipped=56   rescued=0    ignored=0
```

The reboot was real, since `ansible.builtin.reboot` fails if the boot ID does not change. After it the node was `running`, and the build found no ordering cycle. It was the first reboot of the host since Foomuuri was installed, and the build disables cloud-init before it.

The second build, without `uc_raw_node_adopt`:

```text
localhost                  : ok=14   changed=0    unreachable=0    failed=0    skipped=7    rescued=0    ignored=0
raw.example.org            : ok=132  changed=1    unreachable=0    failed=0    skipped=59   rescued=0    ignored=0
```

`changed=1` is the reboot, and nothing else.

### The node checks

| Check | Expected | Result |
| :-- | :-- | :-- |
| `hostname`, `hostname -f` | `raw`, `raw.example.org` | As expected |
| `systemctl is-system-running` | `running` | As expected |
| Ownership marker | `uc-raw-node` | As expected |
| `/etc/cloud/cloud-init.disabled` | Exists | As expected |
| Root's `authorized_keys` | `0` bytes | As expected |
| `sshd -T` | `port 22`, `permitrootlogin no`, `passwordauthentication no` | As expected |
| `sshd -T` AuthorizedKeysCommand | `/usr/bin/true`, run as a safe user | `/usr/bin/true`, as `nobody` |
| Foomuuri | `active` | As expected |
| Ordering cycles from systemd | `0` | `0` |

The first journal check ran without `sudo`, and printed `0` without meaning it: `journalctl` showed the initial user only its own messages. Run as root without a filter, it counted `1`, most likely the build's own logged command line, which holds the search text. Filtered on `SYSLOG_IDENTIFIER=systemd` it counted `0`. The ssh guide's checks use `sudo journalctl -b SYSLOG_IDENTIFIER=systemd`.

## The whole piece of work

### Commits

| Commit | What |
| :-- | :-- |
| `6debf5d` | Phase one: the Incus build with `client_domain` and `node_label`, the node definition check, `ansible.builtin.reboot` |
| `28ff0cb` | Phase one report |
| `7565d6c` | Phase two: platforms as data and directories |
| `d35f9be` | Phase two report |
| `f651ee9` | The naming rules for session records |
| `8fea7a7` | `group_vars/` moved under `inventory/` |
| `fbb2efa` | Phase three: the ssh platform |
| `1242739` | Phase three report |
| `9d90cdc` | Timestamps in session file names, and `resume.txt` ignored |
| `55ef0c1` | `node_address` must be an address |
| `69c0ca7` | Phase four: documents, and the `~/.ssh/config` entry |

### Every file changed

| File | Change |
| :-- | :-- |
| `.gitignore` | `resume.txt`, your change |
| `.yamllint` | Skips what `.gitignore` lists |
| `build.yml` | The node definition check, the platform imports, the shared boot wait, `/etc/hosts`, the reboot and the ordering cycle check |
| `requirements.yml` | `robertdebock.reboot` removed |
| `inventory/group_vars/all/` | Moved from `group_vars/all/`. New: `boot.yml`, `labels.yml`, `ownership.yml`, `platforms.yml`, `ssh.yml`. Changed: `hostname.yml`, `incus.yml`, `names.yml`, `node.yml`, `openssh.yml`, `software.yml`. Removed: `reboot.yml` |
| `platforms/incus/create.yml` | New, the Incus create play |
| `platforms/ssh/create.yml`, `prepare.yml`, `switch.yml` | New, the ssh platform |
| `tasks/wait-for-boot.yml` | New, the shared boot wait |
| `scripts/new-node` | Node label, platform, node address, the `ssh_sources` confirmation, and the `~/.ssh/config` entry |
| `README.md`, `ROADMAP.md`, `CHANGELOG.md` | Rewritten |
| `en/docs/guides/` | Guide 3 new, guides 1 and 2 updated, the platform guide rewritten, the secrets guide generalised, two documents deleted |
| `en/docs/sessions/` | The README, your changes, and the four phase reports |

### Checks over the whole work

Every phase ran `yamllint`, `--syntax-check` with throwaway node definitions in `/tmp`, `ansible-lint`, and two Incus builds from a fresh instance. Every phase ended with the same Incus result: `changed=1` on the second build, the reboot and nothing else. The ssh platform was tested end to end against local Incus containers and a local VM in phase three, and against a real host by you after it.

### Not done, or decided against

- No `ssh_identity_file` field, as you decided: the `~/.ssh/config` entry does that job.
- No port change after first contact. A first contact on another port is refused, and the proposal is in the ROADMAP.
- `wait_for_connection` is not used on the ssh platform, root's keys are emptied after the switch rather than in the prepare play, and the ownership check runs before the shared boot wait. Phase three's report gives the reasons.
- The fix for the ordering cycle disables cloud-init. Changing the ordering of the Foomuuri units was decided against, and raising the cycle upstream is in the ROADMAP.
- On Incus, the ordering cycle check also reads `incus console --show-log`, which empties the console log it reads.
- The steelcj.foomuuri and robertdebock.openssh roles were not changed.
- Two files in `en/docs/sessions/` are yours and not committed: `vps-adoption-test.md`, used as the ssh guide's source, and `2026-11-24--18-22-41-uc-node-platforms-phase4-prompt.md`. The earlier phase reports keep their names, as the sessions README says for older files.
- The secrets guide's "Quick scrub for non secrets" section, with an empty output block and commands for a tag of the old repository, and its example output naming an old commit, were left as they are, since phase four asked only for the file list. They may be worth a look.

## Changelog

| Version | Date | Change |
| :-- | :-- | :-- |
| 0.1.0 | 2026-11-24 | First version, from the end of phase four |
