---
title: Hand Over to the Fleet
description: What connected securely means, where a built node's confirmation and candidate are, how to compare its fingerprint at the console, review and commit the candidate, and admit it with uc-controller's 05_admit.yml, and what a rejection looks like and what to do with it.
version: 0.1.1
status: provisional
date: 2026-11-27
language: en-CA
---

# Hand Over to the Fleet

uc-node takes a node from raw to connected securely, and uc-controller takes it from there. This guide covers the handover: what uc-node leaves behind when a build passes, what you check before admission, how to admit the node with uc-controller as admission works today, and what uc-node leaves behind when a build fails.

It assumes a node built as [Build and Check a Raw Node](2-build-and-check-a-raw-node.md) or [Build a Node on an SSH Host](3-build-a-node-on-an-ssh-host.md) describes. The examples use the client `example-org`, whose inventory is `~/.private/uc/example-org/uc-inventory`, the node `dev.example.org` on Incus, the batch `raw-1970-01-01-01`, and a uc-controller checkout at `~/uc-controller`.

## Contents

- [Connected securely](#connected-securely)
- [What a passing build leaves](#what-a-passing-build-leaves)
- [Compare the fingerprint at the console](#compare-the-fingerprint-at-the-console)
- [Review and commit the candidate](#review-and-commit-the-candidate)
- [Admit the node](#admit-the-node)
- [When a node is rejected](#when-a-node-is-rejected)
- [Changelog](#changelog)

## Connected securely

uc-node's job ends at connected securely: the node meets the raw node contract, its confirmation is on the node, and its candidate is in the client inventory. The node lifecycle overview in uc-contracts says what connected securely means: the controller can reach the node, and others cannot, over an encrypted channel where each side has verified the other. Today, with SSH:

| Part | Today, with SSH |
| :-- | :-- |
| Encrypted | Traffic between controller and node goes over SSH |
| The node is verified | Its host key fingerprint arrives by a separate channel, the console or uc-node's platform connection, and is checked at admission |
| The controller is verified | The initial user logs in with the controller's key, not a password over the network |
| Reachable by the controller | The firewall admits the management port from the controller's sources, and little else inbound beyond what networking needs |
| Least privilege | The initial user becomes root with the batch password, which the controller holds |

A node that can be reached but falls short of these is still raw, and still uc-node's to finish. A node uc-node cannot secure never reaches admission: it is rejected, and recorded in the client log.

## What a passing build leaves

### The confirmation, on the node

`/var/lib/raw-node/confirmation.yml`, owned by root, mode `0644`, so the initial user can read it (RN-REP-01). The build measures it on the node after the reboot, reads it back through the platform, `incus exec` on Incus or the pinned SSH connection on the ssh platform, and checks it with uc-controller's `scripts/check_raw_confirmation.py` when `UC_CONTROLLER` is set. A build that fails the check is rejected, and leaves no candidate.

```yaml
# /var/lib/raw-node/confirmation.yml
dev:
  contract: "0.3.1"
  baseline: "0.3.0"
  timestamp: "1970-01-01T00:00:00+00:00"
  machine_id: "1970010100000000000000000000ab21"
  user: "initial"
  sudo: true
  sudo_nopasswd: false
  ssh_port: 22
  ssh_password_auth: false
  ssh_host_keys:
    - type: "ecdsa-sha2-nistp256"
      fingerprint: "SHA256:EXAMPLEexampleEXAMPLEexampleEXAMPLEexample1"
    - type: "ssh-ed25519"
      fingerprint: "SHA256:EXAMPLEexampleEXAMPLEexampleEXAMPLEexample0"
  firewall: "foomuuri"
  firewall_active: true
  python: "/usr/bin/python3"
  interfaces:
    - name: "eth0"
      type: "ethernet"
      mac: "02:00:00:ab:00:21"
      state: "up"
      default_route4: true
      default_route6: true
      ip: ["10.0.0.21"]
      ip6: ["2001:db8::21"]
```

Every value is measured on the node, and every string is in double quotes, so no YAML reader turns a machine ID, address or version into a number.

### The candidate, in the client inventory

`~/.private/uc/example-org/uc-inventory/candidates/dev.example.org.yml`, written from the controller host at the end of the build. A rebuild overwrites it.

```yaml
# candidates/dev.example.org.yml
dev.example.org:
  address: "10.0.0.21"
  ssh_port: 22
  fingerprint: "SHA256:EXAMPLEexampleEXAMPLEexampleEXAMPLEexample0"
  raw_node_batch: "raw-1970-01-01-01"
  node_label: "dev"
  platform: "incus"
  producer: "uc-node"
  producer_version: "0.3.0"
  contract: "0.3.1"
  built: "1970-01-01T00:00:00-05:00"
```

| Field | What it holds |
| :-- | :-- |
| `address`, `ssh_port` | Where admission connects: `node_address` on the ssh platform, and on Incus the address on the node's IPv4 default route, from the confirmation |
| `fingerprint` | The node's ED25519 host key, from the confirmation read back through the platform |
| `raw_node_batch` | The batch the node was built with, so admission knows which batch password to use |
| `node_label`, `platform`, `producer`, `producer_version` | Where the node came from |
| `contract` | The contract version the build targets. Admission reads the version the node reports in its confirmation |
| `built` | When the build finished, on the controller host's clock |

The build's last task prints the node's name, its address and the fingerprint.

## Compare the fingerprint at the console

Admission trusts a host key only when its fingerprint arrives by a channel other than the SSH connection that reads the confirmation. Before admission, read the ED25519 fingerprint at the node's console and compare it with the candidate's.

On Incus, `incus exec` does not go through SSH:

```sh
incus exec dev-example-org -- ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

Output example:

```text
256 SHA256:EXAMPLEexampleEXAMPLEexampleEXAMPLEexample0 root@dev (ED25519)
```

On the ssh platform, log in at the provider's web console as root, and run the same `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub`. The build read its fingerprint over SSH, pinned to the host key you checked against the console before the first build, so the console check now confirms that nothing changed in between.

If the two differ, do not admit the node. Something other than the node you built answered: a reinstalled host at a reused address, or someone in between. Remove the candidate, find out why, and rebuild.

## Review and commit the candidate

uc-node writes the candidate and never commits it. Look at what changed in the client inventory, then commit it yourself, with `UC_CONTROLLER` set so the pre-commit hook can run uc-controller's `check_inventory.py`:

```sh
cd ~/.private/uc/example-org/uc-inventory
git status --short
git diff candidates/
UC_CONTROLLER=~/uc-controller git add candidates/dev.example.org.yml intake/dev.example.org.yml
UC_CONTROLLER=~/uc-controller git commit -m "Candidate dev.example.org, batch raw-YYYY-MM-DD-NN"
cd -
```

The hook refuses a candidate that holds a crypt hash, a vault header, a private key or a lookup. A candidate holds none of them.

## Admit the node

uc-controller's admission, `ingress/playbooks/05_admit.yml`, does not read `candidates/` yet. It takes its candidates as `admit_candidates`, a list of `{address, fingerprint}` in a file given with `-e @`, each fingerprint one read at the node's console, and the batch as `admit_batch_id`. Until admission reads `candidates/` directly, turn the candidates of one batch into that file.

### Turn the candidates into admit_candidates

The file is not a secret, but it is not part of the inventory either, so make it outside the inventory:

```sh
inventory=~/.private/uc/example-org/uc-inventory
batch=raw-YYYY-MM-DD-NN   # the batch the node definitions name
candidates=$(mktemp --suffix=.yml)
python3 - "$batch" "$inventory"/candidates/*.yml > "$candidates" <<'EOF'
import sys, yaml
batch, paths = sys.argv[1], sys.argv[2:]
chosen = []
for path in paths:
    with open(path, encoding="utf-8") as handle:
        for fqdn, candidate in yaml.load(handle, Loader=yaml.BaseLoader).items():
            if candidate["raw_node_batch"] == batch:
                chosen.append({"address": candidate["address"], "fingerprint": candidate["fingerprint"]})
                print(f"# {fqdn}", file=sys.stderr)
print(yaml.safe_dump({"admit_candidates": chosen}, sort_keys=False), end="")
EOF
cat "$candidates"
```

Output example:

```text
# dev.example.org
admit_candidates:
- address: 10.0.0.21
  fingerprint: SHA256:EXAMPLEexampleEXAMPLEexampleEXAMPLEexample0
```

Admit only candidates whose fingerprint you compared at the console. Remove any other from the file first.

### Run admission

From the uc-controller checkout, with the client inventory's raw stage and its onboard stage, and the batch password in `~/.secrets/uc/fleet/batches/raw-YYYY-MM-DD-NN.yml`, in the same shell as the step above, so `$batch` and `$candidates` are set. Admission logs in as the initial user with the client's key, so load it into the agent first, as [Set Up a Client](0-set-up-a-client.md#make-the-clients-ssh-key) shows:

```sh
ssh-add -t 1h ~/.ssh/example-org-raw-initial-id_ed25519
cd ~/uc-controller
ansible-playbook $(scripts/inventory-args ~/.private/uc/example-org/uc-inventory raw onboard/dev) \
  ingress/playbooks/05_admit.yml -e admit_batch_id="$batch" -e @"$candidates"
rm "$candidates"
cd -
```

Admission scans the node's host keys, reads its confirmation as the initial user with the controller's key, checks it, admits it only when the keys and the console fingerprint agree, writes it to `raw/admitted.yml` and `ssh/known_hosts`, and confirms a become with the batch password. Commit those in the client inventory afterwards, as uc-controller's guides describe. A candidate admission refuses is uc-controller's rejection, which its own log entry records.

### This will change

The raw node handoff design has admission read the candidates of one batch from `candidates/` itself, refuse a candidate whose `node_label` does not belong to the run's environment, and never change `candidates/`. When it does, the conversion above goes away, and this section changes with it.

## When a node is rejected

When a task fails, or the node is unreachable, after the node is in the build's inventory, uc-node rejects it: it writes one file to the client log, and removes the node's candidate, if there is one. The build says so at the end:

```text
[WARNING]: uc_reject: dev.example.org could not be secured. Rejection written to /home/operator/.private/uc/example-org/logs/rejected/1970-01-01--00-00-00-rejected-uc-node-cannot-be-secured.yml
[WARNING]: uc_reject: removed the candidate /home/operator/.private/uc/example-org/uc-inventory/candidates/dev.example.org.yml, since a rejected build leaves none.
```

A failure before the node exists, such as a node definition the check play refuses or an Incus instance uc-node does not own, is not a rejection: there is no node, and the build's message says what to fix.

### What a rejection looks like

```yaml
# 1970-01-01--00-00-00-rejected-uc-node-cannot-be-secured.yml
# Written by uc-node's uc_reject callback: a node uc-node could not secure.
node: "dev.example.org"
rejected: "1970-01-01T00:00:00-05:00"
controller: "uc-node"
step: "Confirm the node meets the contract: Stop if the confirmation does not meet the contract"
reason: "cannot-be-secured"
clauses: ["RN-ACC-07"]
fingerprint: "SHA256:EXAMPLEexampleEXAMPLEexampleEXAMPLEexample0"
raw_node_batch: "raw-1970-01-01-01"
```

| Field | What it holds |
| :-- | :-- |
| `node` | The node's fully qualified domain name |
| `rejected` | When, in ISO 8601 with offset, as in the file's name |
| `controller`, `reason` | `uc-node` and `cannot-be-secured`, always, for uc-node's rejections |
| `step` | The play and the task that failed |
| `clauses` | The contract clauses that failed: those the failed task names, and those uc-controller's checker found, or an empty list |
| `fingerprint` | The ED25519 fingerprint, when the confirmation was read before the failure, or empty |
| `raw_node_batch` | The batch the build used |

The entry never holds the task's error message, which may hold output from the node. The full message is in the build's output.

### What to do with it

Read the build's output for the failed task's message, then decide, as the lifecycle overview leaves it to whoever started the build:

- Fix and rebuild. A wrong setting in the node definition, a batch whose password does not match, or a firewall setting that left the controller out: fix it, and build again. A build that passes writes the candidate again.
- Rebuild from scratch. On Incus, `incus delete --force dev-example-org`, then build. On the ssh platform, reinstall the host at the provider, check its new host key, and adopt it again.
- Leave it. A node you no longer want: delete it, and its node definition in `intake/`.

Leave the rejection files where they are. They are the record of what happened, one file per rejection, written once. `logs/` sits beside the client inventory, not in it, so nothing there is committed with the inventory, and `uc lock` covers it with the client's folder.

## Changelog

| Version | Date | Change |
| :-- | :-- | :-- |
| 0.1.1 | 2026-11-27 | Batch names in commands are `raw-YYYY-MM-DD-NN`, since `raw-1970-01-01-01` is reserved for documents and tests, and admission takes the batch from `$batch`. Load the client's key before admission |
| 0.1.0 | 2026-11-27 | First version, provisional: connected securely, the confirmation and the candidate, comparing the fingerprint at the console, reviewing and committing the candidate, admission with `05_admit.yml` through `admit_candidates` until it reads `candidates/`, and rejections |
