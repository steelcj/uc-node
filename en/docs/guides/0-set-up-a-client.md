---
title: Set Up a Client
description: How to make a client's private folder, its client inventory and client log, the defaults for its node definitions, and a build batch, before uc-node builds its first node, and how to move node definitions out of ~/.secrets/uc-raw/.
version: 0.1.0
status: provisional
date: 2026-11-27
language: en-CA
---

# Set Up a Client

uc-node builds nodes for a client. Before the first build, the client needs four things:

- a private folder, `<private root>/uc/<client>/`, readable by you alone
- its client inventory, `<private root>/uc/<client>/uc-inventory`, made by uc-controller, with uc-node's `intake/` for node definitions and `candidates/` for built nodes
- its client log, `<private root>/uc/<client>/logs/rejected/`, beside the inventory, never in it
- a build batch: the root password and the batch password the nodes are built with, as hashes for uc-node and as the password itself for uc-controller

This guide makes them for the client `example-org`, whose domain is `example.org`, with `~/.private` as the private root. Every client is set up the same way, the lab's own client included: one folder per client under `<private root>/uc/`, with the same layout inside. Use your own client's name, domain and private root.

The layout follows the client inventory layout and the raw node handoff design in uc-contracts. Like them, it is an approach to try, and may change when it is tried.

## Contents

- [The layout](#the-layout)
- [Make the client's folder](#make-the-clients-folder)
- [Make the client inventory](#make-the-client-inventory)
- [Make the client log](#make-the-client-log)
- [Write the defaults for node definitions](#write-the-defaults-for-node-definitions)
- [Make a build batch](#make-a-build-batch)
- [Move node definitions from ~/.secrets/uc-raw/](#move-node-definitions-from-secretsuc-raw)
- [Retire ~/.secrets/uc-raw/ and ~/.secrets/uc-raw-node/](#retire-secretsuc-raw-and-secretsuc-raw-node)
- [Changelog](#changelog)

## The layout

```text
~/.private/                                  0700
  uc/                                        0700
    example-org/                             0700, the client's folder
      uc-inventory/                          the client inventory, a git repository
        intake/                              node definitions, written by uc-node's scripts/new-node
          defaults.yml                       the defaults scripts/new-node offers
          dev.example.org.yml                one node definition per node, no secrets
        candidates/                          one candidate per built node, written by uc-node's builds
        raw/ onboard/ normalized/ ssh/       uc-controller's
      logs/                                  0700
        rejected/                            0700, one file per rejected node, from both controllers

~/.secrets/                                  0700
  uc/                                        0700
    build/                                   0700, uc-node's secrets root
      batches/                               0700
        raw-1970-01-01-01.yml                0600, root_password_hash and initial_password_hash
    fleet/                                   0700, uc-controller's secrets root
      batches/                               0700
        raw-1970-01-01-01.yml                0600, initial_password, the batch password itself
```

| Path | Written by | Read by | Secret |
| :-- | :-- | :-- | :-- |
| `intake/` | You, through `scripts/new-node` | uc-node's `build.yml` | No: a node definition names its batch, and holds no hash |
| `candidates/` | uc-node, at the end of a build | You, then uc-controller's admission | No |
| `logs/rejected/` | uc-node, when it cannot secure a node, and uc-controller's admission | You | No, but private |
| `~/.secrets/uc/build/batches/` | uc-node's `scripts/new-batch` | uc-node, only through `uc_secret` | Yes: password hashes |
| `~/.secrets/uc/fleet/batches/` | You, by uc-controller's batch secrets recipe | uc-controller, only through its `uc_secret` | Yes: the batch password |

uc-node never holds the batch password, only its hash, as the raw node contract asks, and uc-controller never reads a hash.

The client's folder name is the client's short name, such as `example-org`. uc-node does not read it: `scripts/build` and `scripts/new-node` take the client inventory's path.

## Make the client's folder

```sh
install -d -m 0700 ~/.private ~/.private/uc ~/.private/uc/example-org
```

`install -d -m 0700` makes each directory with mode `0700`, and sets that mode on one that already exists. Check:

```sh
stat -c '%a %n' ~/.private ~/.private/uc ~/.private/uc/example-org
```

Output example:

```text
700 /home/operator/.private
700 /home/operator/.private/uc
700 /home/operator/.private/uc/example-org
```

## Make the client inventory

The client inventory is uc-controller's, made from its template. From the uc-controller checkout:

```sh
scripts/new-inventory ~/.private/uc/example-org/uc-inventory
```

It makes the repository, without a remote and without a commit, and says what to do next: replace the `CHANGE-ME` values under `onboard/`, and delete `raw/incus.yml` if the client has no Incus server. uc-controller's guide `en/docs/guides/client-inventories.md` describes the rest. Keep the repository private.

The template has no `intake/` or `candidates/` yet. Make `intake/` now. `scripts/new-node` makes it too when it is missing, and the build makes `candidates/`:

```sh
mkdir ~/.private/uc/example-org/uc-inventory/intake
```

The client inventory's pre-commit hook runs uc-controller's `scripts/check_inventory.py`, which refuses any file holding a crypt hash, a vault header, a private key or a lookup, `intake/` and `candidates/` included. Set `UC_CONTROLLER` to the uc-controller checkout before you commit there.

## Make the client log

```sh
install -d -m 0700 ~/.private/uc/example-org/logs ~/.private/uc/example-org/logs/rejected
```

uc-node writes a rejection here when it cannot secure a node, and makes the folder, mode `0700`, when it is missing. [Hand Over to the Fleet](4-hand-over-to-the-fleet.md#when-a-node-is-rejected) shows what a rejection looks like.

## Write the defaults for node definitions

`scripts/new-node` offers its defaults from `intake/defaults.yml`. Write it as [Set Up the Defaults for New Nodes](1-setup-the-defaults-for-new-nodes.md) describes. For `example-org`:

```yaml
---
# intake/defaults.yml: the defaults uc-node's scripts/new-node offers.
# No secrets: the password hashes are in the batch.
client_domain: example.org
initial_user: initial
ssh_public_key: ~/.ssh/example-org-raw-initial-id_ed25519.pub
ssh_port: 22
ssh_sources: []
```

It holds no hash. `scripts/new-node` refuses a defaults file that holds `root_password_hash`, `initial_password_hash` or any crypt hash.

## Make a build batch

A batch is the nodes built with one root password and one batch password, the password of the initial user. Its name is `raw-YYYY-MM-DD-NN`: the day you make it, and a number for that day. The examples use `raw-1970-01-01-01`, the Unix epoch, a date no real batch can have.

### Choose the passwords

The batch password must be at least 15 characters (RN-ACC-08). A passphrase of six or more words chosen with dice from a published word list meets it, and can be typed at a console. Keep both passwords in your password manager before you go on: the files below are working copies, not the backup.

### uc-node's file, the hashes

From the uc-node checkout:

```sh
scripts/new-batch raw-1970-01-01-01
```

Output example:

```text
Root password:
Batch password, for the initial user (at least 15 characters):
Batch password again:
Wrote ~/.secrets/uc/build/batches/raw-1970-01-01-01.yml, mode 0600, with root_password_hash and initial_password_hash.

The batch password itself goes to uc-controller, in its file
~/.secrets/uc/fleet/batches/raw-1970-01-01-01.yml, by en/docs/guides/batch-secrets.md in uc-controller.
uc-node never stores it. Keep both passwords where you keep secrets that must
survive the loss of this machine, such as a password manager.
```

The passwords are read from the terminal without echo, and given to `openssl passwd -6` on its standard input, so they never reach shell history or the process list. The script makes `~/.secrets/uc/build/batches/` with mode `0700` where it is missing, and refuses a batch whose file exists: a batch is never rewritten, only retired and replaced.

### uc-controller's file, the password

Write the same batch password to `~/.secrets/uc/fleet/batches/raw-1970-01-01-01.yml` with the recipe in uc-controller's guide, `en/docs/guides/batch-secrets.md`, section Creating a batch file. Type it exactly as you typed it for `scripts/new-batch`. If the two differ, the nodes build, and admission's become with the batch password fails.

### Check the batch

```sh
ls -ld ~/.secrets ~/.secrets/uc ~/.secrets/uc/build ~/.secrets/uc/build/batches
ls -l ~/.secrets/uc/build/batches/raw-1970-01-01-01.yml
```

Every directory must be `drwx------` and the file `-rw-------`, all owned by you. Then check that `uc_secret` reads it, from the uc-node checkout, without showing the hash:

```sh
ansible localhost -m ansible.builtin.debug \
  -a "msg={{ lookup('uc_secret', 'batches/raw-1970-01-01-01', key='initial_password_hash') is match('[$]6[$]') }}"
```

Output example:

```text
localhost | SUCCESS => {
    "msg": true
}
```

If `uc_secret` refuses the file, its message names the file and what to change, and never includes the value.

### Check that scripts/new-node accepts the defaults

```sh
scripts/new-node ~/.private/uc/example-org/uc-inventory
```

Answer `y` to "Use defaults?", press Enter for the node label and the platform, give the batch, then answer `n` to the write question. If the batch file is missing, the script says so, without opening it.

Next: [Build and Check a Raw Node](2-build-and-check-a-raw-node.md) on the local Incus host, or [Build a Node on an SSH Host](3-build-a-node-on-an-ssh-host.md).

## Move node definitions from ~/.secrets/uc-raw/

uc-node 0.2.0 kept each node definition, with its two password hashes, in `~/.secrets/uc-raw/<fqdn>.yml`. uc-node 0.3.0 reads node definitions only from a client inventory's `intake/`, without hashes, and refuses one that still holds a hash. Move each one in three steps.

### First, decide: move or rotate

A hash that was ever in a public repository's history, or in any file or session someone else could read, is not moved. Its password is treated as known: make a new batch with new passwords, as [Make a build batch](#make-a-build-batch) shows, rebuild the nodes with it, and give uc-controller the new batch password. Move only hashes that never left your machine and your password manager.

### Put the hashes in a batch

Node definitions with the same two hashes belong to one batch. For each set of hashes, choose a batch name for the day you make the file, and copy the hashes into uc-node's batch file without showing them. In bash, from any directory:

```sh
old=~/.secrets/uc-raw/dev.example.org.yml
batch=raw-1970-01-01-01
install -d -m 0700 ~/.secrets ~/.secrets/uc ~/.secrets/uc/build ~/.secrets/uc/build/batches
python3 - "$old" ~/.secrets/uc/build/batches/"$batch".yml <<'EOF'
import os, sys, yaml
old, new = sys.argv[1:]
data = yaml.safe_load(open(old, encoding="utf-8"))
descriptor = os.open(new, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(descriptor, "w", encoding="utf-8") as out:
    out.write("---\n")
    for key in ("root_password_hash", "initial_password_hash"):
        out.write(f"{key}: '{data[key]}'\n")
print(f"Wrote {new}")
EOF
```

The script refuses to write over a batch file that exists. Then write the batch password to uc-controller's file for the same batch, by its recipe, and [check the batch](#check-the-batch). The password is the one whose hash was `initial_password_hash`. If you are not sure which password that is, check it as [Check the password before the first build](3-build-a-node-on-an-ssh-host.md#check-the-password-before-the-first-build) shows, or rotate.

### Write the node definition into intake/

Copy the node definition into the client inventory without its hashes, and name its batch:

```sh
old=~/.secrets/uc-raw/dev.example.org.yml
batch=raw-1970-01-01-01
inventory=~/.private/uc/example-org/uc-inventory
python3 - "$old" "$batch" "$inventory"/intake <<'EOF'
import sys, yaml
from pathlib import Path
old, batch, intake = sys.argv[1], sys.argv[2], Path(sys.argv[3])
data = yaml.safe_load(open(old, encoding="utf-8"))
for key in ("root_password_hash", "initial_password_hash"):
    data.pop(key, None)
data["raw_node_batch"] = batch
intake.mkdir(exist_ok=True)
new = intake / Path(old).name
new.write_text("---\n# Moved from ~/.secrets/uc-raw/. No secrets.\n"
               + yaml.safe_dump(data, sort_keys=False, width=80), encoding="utf-8")
new.chmod(0o644)
print(f"Wrote {new}")
EOF
grep -c hash "$inventory"/intake/dev.example.org.yml
```

The last command must print `0`. Writing the node definition again with `scripts/new-node` works as well, and asks for every value. Do the same for `~/.secrets/uc-raw/defaults.yml`: write `intake/defaults.yml` without its two hashes, as [Write the defaults for node definitions](#write-the-defaults-for-node-definitions) shows.

Then build the node from the client inventory, as guide [2](2-build-and-check-a-raw-node.md) or [3](3-build-a-node-on-an-ssh-host.md) shows, with `scripts/build`. Commit `intake/` in the client inventory, with `UC_CONTROLLER` set, so its pre-commit hook checks it.

## Retire ~/.secrets/uc-raw/ and ~/.secrets/uc-raw-node/

`~/.secrets/uc-raw/` held uc-node 0.2.0's node definitions, and `~/.secrets/uc-raw-node/` those of the older uc-raw-node. Retire both once nothing uses them:

1. Every node definition in either is in a client inventory's `intake/`, and every node you still build has been built from there with `scripts/build`.
2. Every hash either held is in a batch under `~/.secrets/uc/build/batches/`, or, if it was ever in a public repository's history, has been rotated with a new batch and the nodes rebuilt with it. The old passwords open nothing any more.
3. Nothing else reads them. Search your own scripts and notes for the two paths:

   ```sh
   grep -rIl -e '.secrets/uc-raw' ~/bin <other places you keep scripts>
   ```

4. Your password manager holds every password still in use.

Then remove them:

```sh
rm -r ~/.secrets/uc-raw ~/.secrets/uc-raw-node
```

Afterwards, `~/.secrets/uc/` is the only project directory in `~/.secrets/`, with `build/` for uc-node and `fleet/` for uc-controller.

## Changelog

| Version | Date | Change |
| :-- | :-- | :-- |
| 0.1.0 | 2026-11-27 | First version, provisional: the client's folder, its inventory, log and intake defaults, a build batch for both controllers, moving node definitions out of `~/.secrets/uc-raw/`, and retiring `~/.secrets/uc-raw/` and `~/.secrets/uc-raw-node/` |
