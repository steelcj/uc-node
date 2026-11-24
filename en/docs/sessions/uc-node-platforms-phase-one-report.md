---
title: Platforms for uc-node, Phase One Report
description: What phase one of the platforms work changed, the checks it passed, and what to know before phase two.
version: 0.1.0
status: provisional
date: 2026-11-23
language: en-CA
---

# Platforms for uc-node, Phase One Report

Phase one is done and committed on the `platforms` branch as `6debf5d`. The Incus build works again with the new names, and a real build reboots the node. Nothing was pushed and `VERSION` is unchanged.

## What changed

| File | Change |
| :-- | :-- |
| `group_vars/all/incus.yml` | `incus_instance` is now `node_fqdn` with dots replaced by hyphens, and its comment says so |
| `group_vars/all/hostname.yml` | Sets `hostname: "{{ node_hostname }}"` |
| `group_vars/all/names.yml` | The example in the comment is now `prod.example.org` |
| `group_vars/all/labels.yml` | New: `node_labels: [raw, dev, stage, prod]`. The check play and `scripts/new-node` both read this list, so it lives in one place |
| `group_vars/all/reboot.yml` | Deleted, since nothing else used it |
| `requirements.yml` | `robertdebock.reboot` removed |
| `build.yml` | A new first play checks the node definition, the node is added to the inventory under `node_fqdn`, `/etc/hosts` names the fully qualified domain name, and `ansible.builtin.reboot` replaces the reboot role |
| `scripts/new-node` | Asks for the node label, writes `client_domain` and `node_label`, and names the file by the fully qualified domain name |
| `.yamllint` | Skips what `.gitignore` lists |
| `group_vars/all/software.yml` | The commented-out list has a space after each `#` |

### The hostname role and /etc/hosts

The installed `robertdebock.hostname` only runs `ansible.builtin.hostname`. It never writes `/etc/hosts`, and the Debian image has `127.0.1.1 <instance>`. One `lineinfile` task in the configure play writes `127.0.1.1 <node_fqdn> <node_hostname>`, so `hostname -f` returns `node_fqdn`.

### build.yml

The node is added to the inventory under `node_fqdn`. It is reached with `ansible_incus_host: incus_instance`, which the Incus connection plugin prefers over the inventory name.

A new first play on localhost checks the node definition before anything is created:

- it refuses a definition that still has `hostname`, and says to rename it to `client_domain`
- the required fields are present and not empty
- `client_domain` is DNS labels of lowercase letters, digits and hyphens, separated by dots
- `node_label` is one of the allowed labels

`ansible.builtin.reboot` replaces the `robertdebock.reboot` role. It fails if the boot ID has not changed, so a reboot that did not happen is never reported as done.

### scripts/new-node

- It always asks for the node label, even when the defaults file is used, because the label is what tells two nodes of one client apart. The default is `raw`, and only the four labels are accepted.
- It writes `client_domain` and `node_label`, and names the file `<node_label>.<client_domain>.yml`.
- Its example domain is now `example.org`. Its other checks and the `0600` and `0700` permissions are unchanged.

### Lint fixes

ansible-lint creates `.ansible/` in the repository, and yamllint was linting the roles' files in it. `.yamllint` now skips what `.gitignore` lists.

The missing space after `#` in `group_vars/all/software.yml` was already there, and it made ansible-lint fail.

## Checks

| Check | Result |
| :-- | :-- |
| `yamllint .` | Clean |
| `--syntax-check` with `/tmp/uc-node-check/raw.example.org.yml` | Passes |
| `ansible-lint` | Passes, production profile |
| Bad node definitions: one with `hostname`, one missing a field, one with an empty field, one with `Bad_Domain.example.org`, one with label `test` | Each stops in the first play with a message naming the field |
| `scripts/new-node`, run with a throwaway home directory | Refuses a wrong label, writes `prod.example.org.yml` with mode `0600` |
| First Incus build | Succeeded: localhost `changed=1`, the node `changed=15` |
| `hostname`, `hostname -f`, `uptime` | `raw`, `raw.example.org`, up 0 min. The journal shows a second boot starting at the reboot |
| Second build | localhost `changed=0`, the node `changed=1` (only the reboot), with a new boot ID. Still one instance |
| Instance without the ownership marker (`dev-example-org`) | Refused, and left alone |

`ansible.builtin.reboot` can see a reboot in an Incus container because the container's boot ID changes when it restarts. This was confirmed before relying on it.

The test instances `raw-example-org` and `dev-example-org` were deleted afterwards. Existing instances were not touched.

## Things to know

### Existing node definitions are refused

A node definition in `~/.secrets/uc-raw/` that still uses `hostname` is stopped by the new check. Rename the field to `client_domain` (and add `node_label` if it should not be `raw`), or write a new one with `scripts/new-node`. No file in `~/.secrets` was opened or changed.

### Uppercase domains are refused

The `client_domain` check accepts lowercase letters only, to match `scripts/new-node`, which lowercases what is typed.

### Two checks not added

Incus instance names can be at most 63 characters, and a node definition could set `node_fqdn` or `node_hostname` directly. Phase two is a natural place to check either.

### Documents are out of date until phase four

The README and the guides still mention `robertdebock.reboot` and the old file names.

### Leftover test files

The throwaway node definition and the build logs are in `/tmp/uc-node-check/`. The test key and home directory are in the session's scratchpad directory.

## Changelog

| Version | Date | Change |
| :-- | :-- | :-- |
| 0.1.0 | 2026-11-23 | First version, from the end of phase one |
