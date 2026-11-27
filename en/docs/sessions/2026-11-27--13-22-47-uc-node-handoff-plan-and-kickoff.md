---
title: Handoff for uc-node, Plan and Kickoff Prompt
description: The plan for bringing uc-node into line with the node lifecycle, the client inventory layout and the raw node handoff design, so its job ends at connected securely, and the Claude Code kickoff prompt that carries it out.
version: 0.1.1
status: provisional
date: 2026-11-27
language: en-CA
---

# Handoff for uc-node, Plan and Kickoff Prompt

## Where the repository stands

This plan was written against release 0.2.0, commit `7a96243`, the latest on GitHub on 2026-11-27. If the workstation's checkout has unpushed work beyond it, that work is the truth, and the kickoff starts by saying what differs.

| Area | State at 0.2.0 |
| :-- | :-- |
| Node definitions | One file per node in `~/.secrets/uc-raw/`, with `root_password_hash` and `initial_password_hash`, passed with `-e @<file>` |
| `scripts/new-node` | Reads `~/.secrets/uc-raw/defaults.yml`, asks for the passwords, writes their hashes into the node definition |
| `inventory/group_vars/all/users.yml` | Takes both hashes from the node definition |
| `inventory/group_vars/all/platforms.yml` | `node_required_fields` holds both hashes |
| Confirmation | Not written. The ROADMAP lists it under Later |
| Candidates | Not written. Nothing tells uc-controller a node is ready |
| Rejections | A failed build stops with Ansible's error, and nothing is recorded |
| Firewall | `steelcj.foomuuri` with `foomuuri_ssh_port` and `foomuuri_ssh_sources`, and nothing else |
| Tests | None in the repository. The checks are yamllint, ansible-lint, the syntax checks and real builds |
| Guides | `1-setup-the-defaults-for-new-nodes.md`, `2-build-and-check-a-raw-node.md`, `3-build-a-node-on-an-ssh-host.md`, all written for `~/.secrets/uc-raw/` |

## What uc-node comes into line with

The design documents in uc-contracts, all on `main` at `80c6e16`. They are evolving designs, not rules: where building uc-node shows that one of them does not fit, the design changes, with Christopher, rather than the code bending to it or the document being edited by the session.

- Node lifecycle overview 0.1.5: uc-node takes a node from raw to connected securely. Its job ends when the node meets the contract, its confirmation is on the node, and its candidate is in the client inventory's `candidates/`. A node uc-node cannot secure is rejected and logged, and never reaches admission.
- Client inventory layout 0.1.0: the client inventory lives at `<private root>/uc/<client>/uc-inventory`, with `intake/` and `candidates/` for uc-node, and the client log beside it at `<private root>/uc/<client>/logs/rejected/`.
- Raw node handoff, inventories and secrets 0.1.1: node definitions in `intake/` without hashes, each naming its `raw_node_batch`; the hashes in `~/.secrets/uc/build/batches/<batch>.yml`, read through `uc_secret`; the candidate's fields; and why uc-node may supply the fingerprint.
- Safe values and substitutions 0.1.2: the values every example and test uses.
- Raw node contract 0.3.1: the confirmation's fields and value types, RN-REP-01.

On the uc-controller side, `scripts/check_raw_confirmation.py` already checks a confirmation against contract 0.3.x, and `scripts/match_raw_identity.py` matches it against the fleet. Admission, `05_admit.yml`, still takes its candidates as `admit_candidates`, a list of `{address, fingerprint}` given with `-e @<file>`. Reading `candidates/` directly is uc-controller's next piece of work, not this one.

## Decisions

Each is taken as recommended in the kickoff prompt below. Change any of them before starting, and the prompt with them.

| Decision | Recommended | Why |
| :-- | :-- | :-- |
| How a build names its client | `scripts/build <client inventory> <fqdn>`, which runs `ansible-playbook build.yml -e @<client inventory>/intake/<fqdn>.yml -e uc_client_inventory=<client inventory>` and passes any further arguments through | The client's folder name is not derived from its domain (`vishpala` for the lab), so the path is given. The node definition stays an extra variable, so the node plays still see it and the override rules in `node.yml` and `names.yml` hold. It mirrors uc-controller's `scripts/inventory-args` |
| Where `uc_secret` comes from | A copy of uc-controller's lookup in `plugins/lookup/uc_secret.py`, rooted at `~/.secrets/uc/build`, overridden for tests by `UC_NODE_SECRETS_DIR` | One shared collection is an open decision in the handoff design. A copy works now. A different variable name from uc-controller's `UC_SECRETS_DIR` keeps a test of one controller from pointing the other at its secrets |
| Who writes the build batch file | A new `scripts/new-batch <batch>`, which reads the root password and the batch password from the terminal and writes their hashes, refusing a batch that exists | uc-controller's batch guide leaves this to uc-node. The batch password itself goes to uc-controller's `fleet/` file by its own recipe, so uc-node never holds it. The two can disagree if typed differently, which admission catches when sudo fails |
| Where the confirmation is measured | On the node, after the reboot and the cycle check, by tasks that read `/etc/machine-id`, `sshd -T`, `ssh-keygen -lf` on each host key, the sudoers files, `systemctl is-active foomuuri` and `ip -j addr` and `ip -j route` | The contract wants values measured on the node, not copied from the input. Measuring after the reboot reports the node as uc-controller will find it |
| How a confirmation is checked | With uc-controller's `check_raw_confirmation.py`, when `UC_CONTROLLER` names a checkout, and the build fails if it does not pass. Without it, the build warns that the confirmation was not checked | The checker is the contract's reference consumer. uc-node does not vendor it |
| Where the fingerprint comes from | The node's ED25519 host key, read through the platform: `incus exec` on Incus, the pinned SSH connection on the ssh platform. The build prints it at the end, for comparison at the console | The handoff design's trust argument. Printing it gives the operator the out-of-band check |
| How rejections are written | A callback plugin, `plugins/callback/uc_reject.py`, enabled in `ansible.cfg`, that writes one rejection file when a task fails or the node is unreachable once the node is in the `raw_node` group | A failure can happen in any play after the node exists, and Ansible has no rescue across plays. A failure before the node exists, such as a refused node definition, is not a rejection: there is no node |
| Whether uc-node commits to the client inventory | No. It writes the candidate and the rejection, and the operator reviews and commits | The client inventory's pre-commit hook runs `check_inventory.py`, and a person sees what goes in |
| The SSH port | Stays 22. `ssh_port` keeps its default and its current rules | The client inventory layout fixes it at 22 for now. Changing the port after first contact stays in the ROADMAP |
| The release | 0.3.0 | Node definitions move and change shape, which breaks every existing one |
| The batch for the end-to-end run | A test batch named for the day of the run, such as `raw-2026-11-27-01`, for the client `example-org` only, retired afterwards | The register's `raw-1970-01-01-NN` names are for documents and tests. A batch with real files on disk is not an example, even for a test client |

## The plan

The kickoff runs phase one, then stops. Phase two starts with the operator setting up `example-org` by following the new guide `0-set-up-a-client.md`, which tests that guide, and then runs the end-to-end build and admission.

### Phase one: uc-node to connected securely

1. Secrets. Add `uc_secret`, `scripts/new-batch`, and a `tests/` directory with `run_tests.py`. `users.yml` reads both hashes through the lookup.
2. Intake. `uc_client_inventory`, `scripts/build`, `scripts/new-node` writing `intake/`, and the check play's new refusals.
3. Egress. The confirmation on the node, the candidate in `candidates/`, and the fingerprint printed at the end.
4. Rejections. The callback plugin and its file.
5. Firewall. Confirm that uc-node writes only the bootstrap `10-base` fragment.
6. Documents. The new guides 0 and 4, the others revised, the README, ROADMAP and CHANGELOG.

### Phase two: the end-to-end run

The operator creates `~/.private/uc/example-org/`, its inventory with uc-controller's `scripts/new-inventory`, its `logs/rejected/`, `intake/defaults.yml` and the test batch, following guide 0. The session then builds `dev.example.org` on Incus with `scripts/build`, checks the confirmation and the candidate, admits it with uc-controller's `05_admit.yml` as guide 4 describes, forces one rejection, and reports what in the guides was wrong or missing. The release follows once the run passes.

## Kickoff prompt

```text
Read en/docs/sessions/2026-11-27--13-22-47-uc-node-handoff-plan-and-kickoff.md first: it holds the reasons and decisions behind this prompt. Then read, in uc-contracts, en/docs/design/node-lifecycle-overview-v0.1.5.md, client-inventory-layout-v0.1.0.md, raw-node-handoff-inventories-and-secrets-v0.1.1.md and safe-values-and-substitutions-v0.1.2.md, and en/docs/node-onboarding-pipeline/1-raw-node-egress/uc-raw-node-contract.md. In uc-controller, read shared/plugins/lookup/uc_secret.py, scripts/check_raw_confirmation.py, scripts/check_inventory.py, ingress/playbooks/05_admit.yml and en/docs/guides/batch-secrets.md.

The plan was written against 7a96243, release 0.2.0. Before changing anything, compare the checkout with it, and if main has moved, list what differs and stop if any of it touches the files below.

Work on the branch handoff, which holds this plan, and commit after each step. This is phase one. Stop after step 6 and write the phase one report.

Ground rules for the whole phase:
- The design documents in uc-contracts are evolving designs, not rules. Where one does not fit what you find, or a step here cannot follow it without a choice the documents do not make, stop and ask, saying what does not fit and the options you see. Never edit a uc-contracts document yourself.
- Never read anything under ~/.secrets/ or ~/.private/, and never print a secret or a hash. Tests make their own secrets root and client inventory in a temporary directory, with values from the safe values register, and point UC_NODE_SECRETS_DIR and uc_client_inventory at them.
- Every example, test value and document uses the register: example.org, example-org, raw-1970-01-01-NN, 203.0.113.0/24 and 198.51.100.0/24, SHA256:EXAMPLEexampleEXAMPLEexampleEXAMPLEexample0 and up, example-org-raw-initial-id_ed25519, operator and /home/operator.
- Follow CLAUDE.md's known issues: no SSH login retried in a loop, no wait_for_connection against a host that may refuse the login.
- Run yamllint, ansible-lint, the syntax checks for both platforms and tests/run_tests.py before each commit. Run an Incus build of a test node where a step changes the build, using a node definition and batch made by the tests' helpers in a temporary client inventory, and remove the instance afterwards.
- Never push, never merge, and never commit to a client inventory.

1. Secrets.
   - Copy uc-controller's shared/plugins/lookup/uc_secret.py to plugins/lookup/uc_secret.py, with the root ~/.secrets/uc/build and the override UC_NODE_SECRETS_DIR. Keep its mode and owner checks and its rule that a refusal never includes the value. Say at the top which file it was copied from, at which uc-controller commit, and that the two must change together. Add lookup_plugins = plugins/lookup to ansible.cfg.
   - inventory/group_vars/all/users.yml reads root_password_hash and initial_password_hash with lookup('uc_secret', 'batches/' ~ raw_node_batch, key=...). Remove both hashes from node_required_fields in platforms.yml and add raw_node_batch.
   - scripts/new-batch <batch>: checks the name against raw-YYYY-MM-DD-NN, refuses a batch whose file exists, reads the root password once and the batch password twice from the terminal without echo, refuses a batch password under 15 characters (RN-ACC-08), and writes ~/.secrets/uc/build/batches/<batch>.yml, 0600 in directories of 0700, with root_password_hash and initial_password_hash made with openssl passwd -6 fed on standard input, never as an argument. It says at the end that the batch password goes to uc-controller's file by en/docs/guides/batch-secrets.md in uc-controller, and that uc-node never stores it.
   - Add tests/run_tests.py, discovering unittest tests in tests/, in the style of uc-controller's. Test the lookup (good file, wrong modes, wrong owner where testable, missing key, value never in an error), and new-batch (name rule, existing batch, short password, file modes, hashes verify, password never in the file).

2. Intake.
   - build.yml's check play requires uc_client_inventory, an absolute path to a directory with intake/, and refuses a run where <uc_client_inventory>/intake/<node_fqdn>.yml does not exist, so the node definition and the client inventory cannot disagree. It refuses a node definition that still holds root_password_hash or initial_password_hash, in the way it refuses hostname, with a message saying to move them to a batch with scripts/new-batch. It checks raw_node_batch against the batch name rule. It reads the batch through uc_secret once, so a missing or badly protected batch file fails before anything is created, with no_log.
   - scripts/build <client inventory> <fqdn> [ansible-playbook arguments]: resolves the path, refuses one without intake/<fqdn>.yml, and runs ansible-playbook build.yml -e @<client inventory>/intake/<fqdn>.yml -e uc_client_inventory=<client inventory> with the rest passed through. It prints the command it runs.
   - scripts/new-node takes the client inventory as its first argument, reads its defaults from <client inventory>/intake/defaults.yml, writes <client inventory>/intake/<fqdn>.yml, asks for raw_node_batch, and no longer asks for passwords or writes hashes. It refuses a defaults file that holds a hash. It warns, without reading the file, when ~/.secrets/uc/build/batches/<batch>.yml does not exist. The node definition is not a secret, so it is written 0644 like any file in the client inventory, and the old mode checks go.
   - Remove every use of ~/.secrets/uc-raw/ from the code. The documents are changed in step 6.

3. Egress.
   - After the reboot play, a new play measures the confirmation on the node and writes /var/lib/raw-node/confirmation.yml, owned by root, mode 0644, keyed by node_hostname, with every field of contract 0.3.1 in its order, every string in double quotes, contract "0.3.1" and baseline the repository's VERSION. Put the tasks in tasks/confirmation.yml and the template in templates/confirmation.yml.j2. Every value is measured: machine_id from /etc/machine-id, sudo from the initial user's groups, sudo_nopasswd from the sudoers files ignoring comment lines, ssh_port and ssh_password_auth from sshd -T, ssh_host_keys from ssh-keygen -lf on each /etc/ssh/ssh_host_*_key.pub, firewall and firewall_active from systemctl, python from the interpreter path, interfaces from ip -j addr, ip -j route and ip -j -6 route, with the permanent MAC from ethtool -P or /sys when ip reports a randomised one.
   - Read the written file back and, when UC_CONTROLLER is set, run "$UC_CONTROLLER/scripts/check_raw_confirmation.py" on it from the controller host. Fail the build when its result is not pass, showing its findings. When UC_CONTROLLER is not set, warn that the confirmation was not checked.
   - Write <uc_client_inventory>/candidates/<node_fqdn>.yml from localhost, with the fields and order of the handoff design's candidate: address (node_address on ssh, the address on the default IPv4 route on Incus, from the confirmation), ssh_port, fingerprint (the ED25519 key's, from the confirmation, which was read through the platform), raw_node_batch, node_label, platform, producer "uc-node", producer_version from VERSION, contract "0.3.1", built with offset. Quote the values. A rebuild overwrites the node's candidate.
   - The last task prints the node's name, its address and the ED25519 fingerprint, and says to compare the fingerprint at the console (incus exec <instance> -- ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub, or the provider's console) before admission.
   - Tests: render the template from fixtures and check the result with check_raw_confirmation.py when UC_CONTROLLER is set, skipping otherwise. Check that a candidate from fixtures passes check_inventory.py run on a temporary client inventory, when UC_CONTROLLER is set.
   - Remove "Write confirmation.yml" from the ROADMAP.

4. Rejections.
   - plugins/callback/uc_reject.py, enabled with callbacks_enabled in ansible.cfg, a notification callback that never changes output. When a task fails, or a host is unreachable, and the host is in raw_node, it writes one file to <parent of uc_client_inventory>/logs/rejected/<YYYY-MM-DD--HH-MM-SS>-rejected-uc-node-cannot-be-secured.yml, creating logs/rejected/ when missing, with the entry fields of the node lifecycle overview: node, rejected (ISO 8601 with offset), controller uc-node, step (the play and task that failed), reason cannot-be-secured, clauses (the contract clauses the failed task names, if any, else an empty list), fingerprint when the confirmation was read, else empty, and raw_node_batch. It takes uc_client_inventory and the node's fields from the extra variables. A failure before the node is in raw_node writes nothing. The task's error message is not copied into the file, since it may hold output from the node.
   - A failed build leaves no candidate: a rejected rebuild removes the node's existing candidate, and says so.
   - Tests: run the callback against fixtures for a failure in raw_node, a failure on localhost, and an unreachable host, and check the files written and not written.

5. Firewall.
   - Check what steelcj.foomuuri, at the pin in requirements.yml, writes on the node, and confirm that the build leaves only the bootstrap fragment that uc-controller's onboarding replaces as 10-base, accepting SSH on 22 from ssh_sources. If the role writes the fragment under another name or writes more, stop and report, rather than changing the role.
   - Say in a comment in inventory/group_vars/all/foomuuri.yml that the fragment is a bootstrap rule, that onboarding replaces it, and where the design says so.

6. Documents.
   - en/docs/guides/0-set-up-a-client.md: make <private root>/uc/<client>/ with mode 0700, the inventory with uc-controller's scripts/new-inventory at <private root>/uc/<client>/uc-inventory, logs/rejected/, intake/defaults.yml without hashes, and the batch with scripts/new-batch and uc-controller's batch-secrets recipe, using example-org throughout, and saying the lab's client is named the same way. Say how to move an existing node definition from ~/.secrets/uc-raw/ into intake/ without its hashes, and its hashes into a batch under ~/.secrets/uc/build/batches/. Say how to retire ~/.secrets/uc-raw/ and the older ~/.secrets/uc-raw-node/ once nothing uses them, and that anything either held that was ever in a public repository's history is rotated with a new batch, not moved. After the move, ~/.secrets/uc/ is the only project directory in ~/.secrets/, with build/ for uc-node and fleet/ for uc-controller.
   - en/docs/guides/4-hand-over-to-the-fleet.md: what connected securely means, from the lifecycle overview; where the confirmation and the candidate are; comparing the fingerprint at the console; reviewing and committing the candidate; admitting it with uc-controller's 05_admit.yml as it reads candidates today, by turning the candidate into admit_candidates, and that this will change when admission reads candidates/; and what a rejection looks like and what to do with it.
   - Revise guides 1 to 3 for intake/, scripts/build and the batch. Rename 1-setup-the-defaults-for-new-nodes.md only if its subject changes, and fix every link if it does.
   - README: the layout table, node definitions, the field table, secrets, run it and guides. ROADMAP: remove what this phase did, and add reading out-of-band fingerprints on the ssh platform from the provider's API where one exists. CHANGELOG: an Unreleased section for 0.3.0, saying node definitions must be moved.
   - Write the phase one report, en/docs/sessions/<timestamp>-uc-node-handoff-phase-one-report.md, by the sessions README: what changed, the checks run and their results, anything in this prompt or the design documents that did not fit what you found, with the design changes you would suggest, and what the operator must do before phase two.
```

## Changelog

| Version | Date | Change |
| :-- | :-- | :-- |
| 0.1.1 | 2026-11-27 | Guide 0 also retires ~/.secrets/uc-raw-node/, says that secrets once in a public history are rotated rather than moved, and names ~/.secrets/uc/build/ and fleet/ as the only project directories afterwards |
| 0.1.0 | 2026-11-27 | First version |
