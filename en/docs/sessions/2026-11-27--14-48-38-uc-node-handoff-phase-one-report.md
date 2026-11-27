---
title: Handoff for uc-node, Phase One Report
description: What phase one of the handoff work changed so uc-node's job ends at connected securely, the checks it ran and their results, what in the prompt and the design documents did not fit, and what the operator must do before phase two.
version: 0.1.0
status: provisional
date: 2026-11-27
language: en-CA
---

# Handoff for uc-node, Phase One Report

## Summary

Phase one is done, on the branch `handoff`, in six commits after the plan, none pushed. A build now reads its node definition from a client inventory's `intake/`, takes its password hashes from a build batch through `uc_secret`, measures and writes the confirmation on the node, checks it with uc-controller's checker, writes the candidate to `candidates/`, and prints the fingerprint to compare at the console. When it cannot secure a node, it writes a rejection to the client log and removes the node's candidate. The guides, the README, the ROADMAP and the CHANGELOG describe it. Every check passed, and a fresh Incus build of the final tree passed end to end.

Nothing in the design documents blocked a step, so I did not stop. Several points did not fit exactly, and are listed under [What did not fit](#what-did-not-fit) with the changes I would suggest. Two are worth deciding before phase two: how a node definition's hash is kept from overriding the batch, and how the client's folder is named.

## Before starting

| Item | Found |
| :-- | :-- |
| `main` | At `7a96243`, release 0.2.0, as the plan expects. Nothing to stop for |
| `handoff` | On GitHub only, holding the plan at 0.1.1, one commit beyond the 0.1.0 copy that was untracked in the working tree. The untracked copy was identical to the 0.1.0 commit, `1bcd8c5`, so I removed it and checked out `handoff` from `origin/handoff`. The work follows the plan's 0.1.1, which adds `~/.secrets/uc-raw-node/` and rotation to guide 0 |
| uc-contracts | At `80c6e16`, as the plan expects |
| uc-controller | At `8799481`. `uc_secret.py` is copied from there; its last change was in `6e99884` |

No file under `~/.secrets/` or `~/.private/` was read. Every test and every build used a secrets root and a client inventory in a temporary directory, with register values and made-up passwords, through `UC_NODE_SECRETS_DIR` and `uc_client_inventory`. No hash was printed: each build's output was searched for `$6$`, and none held one.

## What changed

| Step | Commit | What |
| :-- | :-- | :-- |
| 1. Secrets | `a1fcdd4` | `plugins/lookup/uc_secret.py`, copied from uc-controller at `8799481`, rooted at `~/.secrets/uc/build` with the override `UC_NODE_SECRETS_DIR`, its checks and its rule that a refusal never holds the value unchanged. `ansible.cfg` names `plugins/lookup`. `users.yml` reads both hashes through the lookup, written inline in `users` (see [below](#a-hash-in-a-node-definition-and-the-batch)). `node_required_fields` loses the hashes and gains `raw_node_batch`. `batches.yml` holds the batch name rule and RN-ACC-08's minimum, shared by the scripts and the check play. `scripts/new-batch`. `tests/` with `run_tests.py`, helpers, and tests of the lookup and `new-batch` |
| 2. Intake | `4adef9a` | The check play refuses a hash in the node definition, requires `uc_client_inventory`, refuses a node definition that is not in its `intake/` or names another node, checks `raw_node_batch`, and reads the batch once with `no_log`. `scripts/build`. `scripts/new-node <client inventory>`, without passwords, at `0644`, with the batch question and the missing-batch warning. Tests of the check play, `scripts/build` and `scripts/new-node` |
| 3. Egress | `8587c50` | `tasks/confirmation.yml` and `templates/confirmation.yml.j2`: every field of contract 0.3.1 measured on the node after the reboot, written root `0644`, read back through the platform, and checked with `check_raw_confirmation.py` when `UC_CONTROLLER` is set. A handover play writes `candidates/<fqdn>.yml` from `templates/candidate.yml.j2` and prints the address and fingerprint with the console command. `handoff.yml` holds the contract version, VERSION and the paths. Tests render both templates from fixtures and check them with uc-controller's checkers. "Write confirmation.yml" removed from the ROADMAP |
| 4. Rejections | `e5d38b3` | `plugins/callback/uc_reject.py`, enabled in `ansible.cfg`. It writes one entry to `<parent of uc_client_inventory>/logs/rejected/`, never copying the error message, and removes the node's candidate. Tests for a failure in `raw_node`, on localhost, an unreachable host, rescued and ignored failures, a good run, a run without `uc_client_inventory`, and two rejections in a row |
| 5. Firewall | `615aabe` | A comment in `foomuuri.yml`: the fragment is a bootstrap rule that onboarding replaces as `10-base`, with where the handoff design says so. No code change |
| 6. Documents | `791f087` | New guides 0, Set Up a Client, and 4, Hand Over to the Fleet. Guides 1 to 3 and the platform guide revised. Guide 1 keeps its name, since its subject, the defaults for new nodes, is unchanged. README, ROADMAP and CHANGELOG |

### Choices made along the way

- The check play's batch read has no second read in its rescue. ansible-core 2.21 prints a lookup's error above the censored result even with `no_log`, so uc_secret's refusal, which never holds the value, reaches the operator. The rescue only adds a pointer to `scripts/new-batch`.
- The check play also checks that the file `intake/<node_fqdn>.yml` names the same `client_domain` and `node_label` as the node definition passed, so a node definition from elsewhere cannot borrow another node's file.
- The confirmation and handover tasks that write on the controller run in the node's plays with `delegate_to: localhost` and `become: false`. That way a failure in the checker or the candidate is the node's failure, and becomes a rejection.
- The rejection callback writes at the end of the run, for hosts the stats still count as failed or unreachable. A rescued failure, such as `robertdebock.bootstrap`'s ping before Python is installed, which every first build has, is not a rejection.
- A task names a contract clause only where its failure breaks that clause. When the checker fails the confirmation, its failing clause identifiers are passed to the callback as `uc_reject_clauses`. A first version also named clauses on the measuring tasks, and the end-to-end rejection test listed RN-REP-01 for a node that broke only RN-ACC-07. Those names were removed.
- `scripts/new-node` writes at a width of 80, so PyYAML folds the ed25519 key line before its comment, and the file meets the client inventory's yamllint limit of 120 characters.
- `scripts/new-batch` refuses to read passwords from anything but a terminal, since `getpass` would echo them.

## Checks

Before every commit: `yamllint .`, `ansible-lint` (production profile), `ansible-playbook build.yml --syntax-check` with an Incus and an ssh node definition in a temporary client inventory, and `tests/run_tests.py`.

| Check | Result |
| :-- | :-- |
| `yamllint .` | Clean, every step |
| `ansible-lint` | Passes, production profile, every step |
| Syntax checks, Incus and ssh | Both pass, every step |
| `tests/run_tests.py` with `UC_CONTROLLER` set | 75 tests, all pass |
| `tests/run_tests.py` without `UC_CONTROLLER` | 75 tests, all pass, 3 skipped: the checker tests |

Incus builds, each with a node definition and batch from `tests/helpers.py setup` in a temporary client inventory. Each instance, `raw-example-org`, was removed afterwards, and none is left:

| Step | Build | Result |
| :-- | :-- | :-- |
| 1 | Fresh, with `ansible-playbook` directly | Passes. root's and initial's shadow entries equal the batch's hashes (compared without printing them) |
| 2 | Fresh, with `scripts/build` | Passes |
| 3 | Fresh, with `UC_CONTROLLER` | Passes. The confirmation passes the checker. The ED25519 fingerprint in the confirmation, the candidate and the printed line equals `ssh-keygen -lf` through `incus exec`. The candidate passes `check_inventory.py` and the client inventory's yamllint |
| 3 | Rebuild | Changes only the reboot, the confirmation and the candidate, after the temporary copy's tasks were marked unchanged |
| 3 | Rebuild without `UC_CONTROLLER` | Passes, and warns twice that the confirmation was not checked |
| 4 | Build, then a rebuild with `UC_CONTROLLER` naming a stand-in checker that fails RN-ACC-07 | The rebuild exits 2, writes one rejection with the step, `clauses: ["RN-ACC-07"]`, the node's real fingerprint and the batch, without the checker's message, and removes the candidate, saying so |
| 5 | Fresh, with `ssh_sources: [198.51.100.10/32]` | `/etc/foomuuri/` holds only `10-base.conf`, which accepts SSH from that source only, with DHCP, DHCPv6 and ping, and accepts everything outgoing. One nftables table, `inet foomuuri`. `nftables.service` masked, neither ufw nor firewalld installed |
| Final | Fresh, final tree, with `UC_CONTROLLER` | Passes. The checker passes, `check_inventory.py` and the client yamllint pass, no rejection, and the candidate, console and printed fingerprints match |

The guides' new shell recipes were run against temporary files: the `uc_secret` check in guide 0, the two migration scripts (the hashes moved still verify against their passwords, and the node definition holds no hash), the password check in guide 3 (matches the right password, refuses a wrong one), and the conversion to `admit_candidates` in guide 4 (only the batch asked for). A link check found no broken link or anchor in any Markdown file.

Not run: any ssh platform build, since no remote host was in scope, and admission, which is phase two.

## What did not fit

None of these stopped a step. Each says what I found, what I did, and the change I would suggest. I did not edit any uc-contracts document.

### A hash in a node definition and the batch

The handoff design shows uc-node defining `root_password_hash` and `initial_password_hash` as variables whose value is the lookup. A node definition is passed with `-e`, which overrides every group variable. So an old node definition that still holds a hash would silently replace the batch's, and the check play could not tell the two apart. I wrote the lookups inline in `users`, so neither name is defined unless a node definition sets it, and the check play refuses it as it refuses `hostname`.

Suggested: the handoff design shows the lookups inline in the users list, or says why the variables must not be defined in group variables.

### How the client's folder is named

The client inventory layout names the folder "for its main domain: example-org". The plan says the lab's folder is not derived from its domain. uc-node takes the client inventory's path, so nothing depends on the name. Guide 0 calls it the client's short name, and says the lab's client is set up the same way, in its own folder under `<private root>/uc/`, without naming it.

Suggested: the layout design says a short name, often taken from the main domain.

### The rejection entry

- `step`: the lifecycle example is `05_admit`, a playbook. uc-node has one playbook, so `step` is the play and the task, as `"<play>: <task>"`. Suggested: the overview defines `step` as free text naming where the failure was, or gives each controller a list of step names.
- `clauses`: uc-controller's checker reports some findings against names that are not clause identifiers, such as `Versioning`, `Host keys`, `Firewall` and `Firewall manager`. uc-node keeps only `RN-` identifiers. Suggested: the contract gives those checks identifiers, or the overview allows names beside identifiers, as it already does for the identity check.
- When it is written: at the end of the run, for failures the build did not recover from. An interrupted run writes nothing. Suggested: the overview says a rejection is a failure the producer did not recover from.
- Names by the second: two rejections in the same second would share a name. The callback waits for the next second rather than write over a file. Suggested: the overview says names are unique by the second, or allows a suffix.
- A candidate the operator has already committed is deleted from the working tree by a rejection, so `git status` shows the deletion, which needs a commit too. Guide 4 does not say so yet.

### The confirmation's measurements

- `sudo` is measured from the initial user's groups, `sudo` or `wheel`, as the prompt asks. That misses a sudoers rule naming the user directly. `sudo -l -U <user>` would measure the field as the contract defines it. Suggested: decide which, and say so in the contract or the plan.
- `interfaces[].mac`: an interface without a hardware address, such as WireGuard or a tunnel, gets an empty `mac`, and the checker refuses it, while the contract lists every interface except loopback. Raw nodes have none today. Suggested: the contract allows an empty `mac` for interfaces without one.
- `interfaces[].type`: `ethernet` when `ip` reports `link_type ether`, so a container's veth reports `ethernet`, as does a bridge. Suggested: the contract says what virtual interfaces are.
- `ssh_port`: `sshd -T` lists one line per port. The first is reported, since the contract has one port.
- `python`: `/usr/bin/python3.13` on Debian 13, the interpreter Ansible ran, where the contract's example shows `/usr/bin/python3`. Both meet the field's definition.
- `timestamp` is the node's clock, `+00:00` in an Incus container, while the candidate's `built` is the controller's, with its own offset. Both are valid.

### The candidate and the confirmation as YAML

The top-level keys, the hostname and the fully qualified domain name, are unquoted, as in the contract's and the design's examples. Every value that is a string is quoted. The `baseline` and `producer_version` come from `VERSION`, which says 0.2.0 until 0.3.0 is cut. Nodes built in phase two before the release will report 0.2.0.

Suggested: cut 0.3.0 before the end-to-end run, or accept that the run's nodes report 0.2.0.

### The client inventory template and its checks

- uc-controller's `inventory-template/` has no `intake/` or `candidates/`. Guide 0 makes `intake/`, and the build makes `candidates/`. Suggested, for uc-controller: add both to the template, each with a line in its README.
- `check_inventory.py` passes a candidate because it reads it as a hosts file with a group and no variables. Suggested, for uc-controller: check the candidate's shape there when admission reads `candidates/`.
- The client inventory's yamllint limit of 120 characters cannot be met by an RSA key line, whose base64 is one long word on a line with other words. ed25519 keys fit once folded. Suggested: `allow-non-breakable-inline-mappings`, or a higher limit, for `intake/`.

### uc-controller's batch secrets guide

It still says uc-node does not read `~/.secrets/uc/build/` yet, and that uc-node's own guide will say how to make the file. Guide 0 and `scripts/new-batch` now do. Suggested, for uc-controller: point that section at uc-node's guide 0.

### The firewall role

`steelcj.foomuuri` writes one fragment, `10-base`, under the name onboarding uses, so I did not stop. Besides the fragment, it removes ufw and firewalld and masks `nftables.service`, which RN-FW-01 and RN-FW-02 call for, and which are not firewall configuration. Foomuuri on Debian 13 is older than 0.33, so the public zone is `eth* en* wl*`. An interface named otherwise would be outside it, which the ROADMAP's item on hosts with more than one interface covers.

### A second build

The README and the guides said a second build changes only the reboot. It now changes three things: the reboot, the confirmation, whose timestamp changes, and the candidate, whose build time changes. The documents say so.

## Before phase two

1. Review the branch `handoff`. Nothing is pushed or merged.
2. Decide the two points above, the hash in a node definition and the client's folder name, and any others you want settled before the run.
3. Set up `example-org` by following guide 0, which tests it: `~/.private/uc/example-org/` at `0700`, the inventory with uc-controller's `scripts/new-inventory`, its `CHANGE-ME` values (among them `onboard_ssh_private_key_file`), `raw/incus.yml` kept since the run is on Incus, `logs/rejected/`, `intake/` with `defaults.yml`, and the test batch for the day of the run, such as `raw-2026-11-27-01`, with `scripts/new-batch` and uc-controller's batch-secrets recipe.
4. Make the key the defaults name, `~/.ssh/example-org-raw-initial-id_ed25519`, so `scripts/new-node` and admission can use it.
5. Check that no Incus instance named `dev-example-org` exists.
6. Set `UC_CONTROLLER` to the uc-controller checkout for the run.
7. Keep `~/.secrets/uc-raw/` until its node definitions are moved: uc-node 0.3.0 refuses them as they are.

## Changelog

| Version | Date | Change |
| :-- | :-- | :-- |
| 0.1.0 | 2026-11-27 | First version |
