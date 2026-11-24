---
title: Platforms for uc-node, Phase Two Report
description: What phase two of the platforms work changed, the checks it passed, and what to know before phase three.
version: 0.1.0
status: provisional
date: 2026-11-23
language: en-CA
---

# Platforms for uc-node, Phase Two Report

Phase two is done and committed on the `platforms` branch as `7565d6c`. Platforms are now data in `group_vars/all/platforms.yml` and directories under `platforms/`, and the Incus build behaves exactly as it did at the end of phase one. Nothing was pushed and `VERSION` is unchanged.

Before phase two, the phase one report was saved as `uc-node-platforms-phase-one-report.md` and committed as `28ff0cb`.

## The /etc/hosts task

The task uses `lineinfile` with `regexp: '^127\.0\.1\.1\s'`, which replaces the matching line rather than adding one. `insertafter` applies only when no line matches. After a first and a second build, `/etc/hosts` holds exactly one 127.0.1.1 line, `127.0.1.1 raw.example.org raw`, in the place where the image's line was. No fix was needed.

## What changed

| File | Change |
| :-- | :-- |
| `group_vars/all/platforms.yml` | New: `node_required_fields`, and a `platforms` mapping where each platform lists its `required_fields`: none for `incus`, `node_address` for `ssh`. Data only |
| `group_vars/all/ownership.yml` | New: `uc_raw_node_owner`, `uc_raw_node_owner_key` and `uc_raw_node_owner_file` |
| `platforms/incus/create.yml` | New: the Incus create play, moved from `build.yml`, using the ownership variables instead of literals |
| `platforms/incus/group_vars` | New: a link to `../../group_vars` |
| `build.yml` | The check play reads `platforms.yml` and has the new checks, and the Incus create play is imported |
| `scripts/new-node` | Asks for the platform, and for the fields the platform requires |
| `group_vars/all/node.yml` | The comments name `ssh` instead of `vps`, and point to `platforms.yml` and `labels.yml` |

### The node definition check

The check play on localhost runs in this order, and each refusal names the field:

- refuse a definition that still has `hostname`
- `platform` is a key of `platforms`
- the fields in `node_required_fields`, and the platform's `required_fields`, are present and not empty
- refuse a definition that sets `node_fqdn`, `node_hostname` or `incus_instance`, with a message saying these are calculated from `client_domain` and `node_label`
- `client_domain` is at least two DNS labels of lowercase letters, digits and hyphens, each at most 63 characters, at most 253 in all, the same rule as `scripts/new-node`
- `node_label` is one of `node_labels`
- for the `incus` platform, `incus_instance` is at most 63 characters

A calculated name is detected by comparing it with the rule it should follow, since Ansible cannot tell a value passed with `-e` apart from the group_vars value it overrides. The check therefore restates the rules in `names.yml` and `incus.yml`, and a comment says to change them together. The check runs after the required fields, because `node_fqdn` cannot be calculated without `client_domain`.

### Plays cannot carry when

Ansible refuses `when` on a play: "'when' is not a valid attribute for a Play". So every play in a platform's file keeps all its tasks in one block with `when: platform == 'incus'`. The condition is evaluated per host after group_vars are loaded, so the `platform` default in `node.yml` applies. `build.yml` imports the file with a fixed path, whatever the node's platform.

### The group_vars link

While it runs the plays of an imported playbook, ansible-core sets its base directory to the imported playbook's own directory (`playbook_executor.py`, at `self._loader.set_basedir(play._included_path)`). It does this in the default `playbook_vars_root = top` mode as well. So `group_vars/` next to `build.yml` was not loaded for `platforms/incus/create.yml`, and the first build stopped with "'incus_instance' is undefined".

`playbook_vars_root = all` was tried and does not help: its search path follows role dependencies and the task file's directory, not the playbook that did the import.

The fix is `platforms/incus/group_vars`, a link to `../../group_vars`, explained in the header of `create.yml`. Every new platform directory needs the same link. The alternative is to move `group_vars/` to `inventory/group_vars/`, which Ansible loads for any playbook. That moves every file the phase three instructions name, so the link was chosen as the smaller change. It can be reversed if you prefer the move.

### scripts/new-node

- It always asks for the platform, even when the defaults file is used, offering the keys of `platforms.yml`, with `incus` as the default.
- It then asks for each field in that platform's `required_fields`. For `ssh` that is `node_address`, checked with `ipaddress.ip_address`. The question for each field is kept in the script by field name, so a platform that requires a field the script does not know how to ask for stops it with a message naming the field.
- It writes `platform`, and `node_address` when there is one, to the node definition.
- It reads the allowed labels and the platforms from `group_vars/all/`, in both cases with a message if the file does not hold what it should.

## Checks

| Check | Result |
| :-- | :-- |
| `yamllint .` | Clean |
| `--syntax-check` with an Incus and an ssh node definition in `/tmp` | Both pass |
| `ansible-lint` | Passes, production profile |
| `platform: vps` | Refused: "platform must be one of incus, ssh" |
| `platform: ssh` without `node_address` | Refused: "has no node_address, which the ssh platform requires" |
| A definition setting `node_fqdn`, `node_hostname` or `incus_instance` | Each refused, with the calculated-names message |
| A label of 64 characters, and a domain of 255 characters | Both refused by the `client_domain` check |
| A valid domain that makes an instance name of 79 characters | Refused by the instance name check |
| A valid ssh definition | Passes the check, every Incus task is skipped, and the node plays match no hosts. Nothing ran outside localhost |
| `scripts/new-node`, with a throwaway home directory | Refuses `vps` and `203.0.113.999`, writes an ssh definition with `node_address: 203.0.113.10` and an Incus one with `platform: incus` |
| First Incus build | Succeeded: localhost `changed=1`, the node `changed=15`, as in phase one |
| `hostname`, `hostname -f`, `uptime` | `raw`, `raw.example.org`, up 0 min, and the journal shows a second boot starting at the reboot |
| Second build | localhost `changed=0`, the node `changed=1` (only the reboot), with a new boot ID |
| Instance without the ownership marker (`dev-example-org`) | Refused, and left alone |

The test instances were deleted afterwards, and existing instances were not touched. `/tmp/uc-node-check/` and the test key and home directory in the scratchpad directory are deleted. Phase three will make a new throwaway ssh definition for its syntax checks.

## Things to know

### An ssh node definition does nothing yet

It passes the check and then every play is skipped or matches no hosts, until phase three adds the ssh plays.

### node_address is checked only by scripts/new-node

The check play confirms that `node_address` is present, not that it is an IP address. Checking it in Ansible needs `ansible.utils` and `netaddr`, which are not installed. Phase three can check the address with a regular expression, or rely on the connection failing.

### The warning about ssh_sources

The platform guide suggests that `scripts/new-node` warns when the platform is `ssh` and `ssh_sources` is not empty, since the controller's own address must be in it. Phase two as written does not include this, so it was left for phase three or four.

### A file not written in this session

An untracked `en/docs/sessions/README.md` appeared during the phase. It was read for the naming rules this report follows, and left uncommitted.

## Changelog

| Version | Date | Change |
| :-- | :-- | :-- |
| 0.1.0 | 2026-11-23 | First version, from the end of phase two |
