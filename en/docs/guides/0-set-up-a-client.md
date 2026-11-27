---
title: Set Up a Client
description: How to make a client's private folder, its client inventory and its first commit, its client log, the client's SSH key, the defaults for its node definitions, and a build batch, before uc-node builds its first node.
version: 0.2.1
status: provisional
date: 2026-11-27
language: en-CA
---

# Set Up a Client

uc-node builds nodes for a client. Before the first build, the client needs five things:

- a private folder, `<private root>/uc/<client>/`, readable by you alone
- its client inventory, `<private root>/uc/<client>/uc-inventory`, made by uc-controller, with uc-node's `intake/` for node definitions and `candidates/` for built nodes
- its client log, `<private root>/uc/<client>/logs/rejected/`, beside the inventory, never in it
- the client's SSH key, which the initial user of every raw node logs in with
- a build batch: the root password and the batch password the nodes are built with, as hashes for uc-node and as the password itself for uc-controller

This guide makes them for the client `example-org`, whose domain is `example.org`, with `~/.private` as the private root. Every client is set up the same way, the lab's own client included: one folder per client under `<private root>/uc/`, with the same layout inside. Use your own client's name, domain and private root.

The commands use two checkouts. Each section says which one to run from: `~/uc-node` for uc-node, and `~/uc-controller` for uc-controller. Use your own paths.

The layout follows the client inventory layout and the raw node handoff design in uc-contracts. Like them, it is an approach to try, and may change when it is tried.

## Contents

- [The layout](#the-layout)
- [Make the client's folder](#make-the-clients-folder)
- [Make the client inventory](#make-the-client-inventory)
- [Make the client log](#make-the-client-log)
- [Make the client's SSH key](#make-the-clients-ssh-key)
- [Write the defaults for node definitions](#write-the-defaults-for-node-definitions)
- [Make the first commit](#make-the-first-commit)
- [Make a build batch](#make-a-build-batch)
- [Changelog](#changelog)

## The layout

```text
~/.private/                                  0700
  uc/                                        0700
    example-org/                             0700, the client's folder
      uc-inventory/                          the client inventory, a git repository on the branch main
        intake/                              node definitions, written by uc-node's scripts/new-node
          defaults.yml                       the defaults scripts/new-node offers
          dev.example.org.yml                one node definition per node, no secrets
        candidates/                          one candidate per built node, written by uc-node's builds
        raw/ onboard/ normalized/ ssh/       uc-controller's
      logs/                                  0700
        rejected/                            0700, one file per rejected node, from both controllers

~/.ssh/
  example-org-raw-initial-id_ed25519         0600, the client's key for the initial user
  example-org-raw-initial-id_ed25519.pub     its public key, which every node definition holds

~/.secrets/                                  0700
  uc/                                        0700
    build/                                   0700, uc-node's secrets root
      batches/                               0700
        raw-YYYY-MM-DD-NN.yml                0600, root_password_hash and initial_password_hash
    fleet/                                   0700, uc-controller's secrets root
      batches/                               0700
        raw-YYYY-MM-DD-NN.yml                0600, initial_password, the batch password itself
```

| Path | Written by | Read by | Secret |
| :-- | :-- | :-- | :-- |
| `intake/` | You, through `scripts/new-node` | uc-node's `build.yml` | No: a node definition names its batch, and holds no hash |
| `candidates/` | uc-node, at the end of a build | You, then uc-controller's admission | No |
| `logs/rejected/` | uc-node, when it cannot secure a node, and uc-controller's admission | You | No, but private |
| `~/.ssh/example-org-raw-initial-id_ed25519` | You, with `ssh-keygen` | ssh, for the build on the ssh platform and for uc-controller's admission | Yes: the private key |
| `~/.secrets/uc/build/batches/` | uc-node's `scripts/new-batch` | uc-node, only through `uc_secret` | Yes: password hashes |
| `~/.secrets/uc/fleet/batches/` | You, by uc-controller's batch secrets recipe | uc-controller, only through its `uc_secret` | Yes: the batch password |

uc-node never holds the batch password, only its hash, as the raw node contract asks, and uc-controller never reads a hash.

The client's folder name is the client's short name, such as `example-org`. `scripts/build` and `scripts/new-node` take the client inventory's path. `scripts/new-node` compares the folder name with the client domain, and asks again when they do not match, such as `example.com` for `example-org`.

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

The client inventory is uc-controller's, made from its template by `scripts/new-inventory`. That script is in uc-controller, not uc-node. From the uc-controller checkout:

```sh
cd ~/uc-controller
scripts/new-inventory ~/.private/uc/example-org/uc-inventory
```

Output example:

```text
Made a client inventory in /home/operator/.private/uc/example-org/uc-inventory. Next:
  replace every CHANGE-ME value under /home/operator/.private/uc/example-org/uc-inventory/onboard/,
  delete raw/incus.yml if this client has no Incus server,
  then commit with UC_CONTROLLER=/home/operator/uc-controller set, and keep the repository private.
```

Run it once. A second run refuses, because the folder is no longer empty. If you are not sure the first worked, list the folder instead:

```sh
ls -A ~/.private/uc/example-org/uc-inventory
```

Output example:

```text
.git  .githooks  normalized  onboard  raw  README.md  ssh  .yamllint
```

The repository has no remote and no commit yet. Its branch is the one `git init` makes, which is `master` unless your git configuration says otherwise. Name it `main` now, before the first commit:

```sh
git -C ~/.private/uc/example-org/uc-inventory branch -m main
```

Then do what the script says, and leave the commit for later: [Make the first commit](#make-the-first-commit) makes it once the defaults are written.

- Replace every `CHANGE-ME` value under `onboard/`, by uc-controller's guide `en/docs/guides/client-inventories.md`. `onboard_ssh_private_key_file` is the client's key, `~/.ssh/example-org-raw-initial-id_ed25519`, which [Make the client's SSH key](#make-the-clients-ssh-key) makes: uc-controller's admission logs in as the initial user with it.
- Delete `raw/incus.yml` if the client has no Incus server.

The template has no `intake/` or `candidates/` yet. Make `intake/` now. `scripts/new-node` makes it too when it is missing, and the build makes `candidates/`:

```sh
mkdir ~/.private/uc/example-org/uc-inventory/intake
```

The client inventory's pre-commit hook runs uc-controller's `scripts/check_inventory.py`, which refuses any file holding a crypt hash, a vault header, a private key or a lookup, `intake/` and `candidates/` included. It refuses every commit until `UC_CONTROLLER` is set to the uc-controller checkout. Keep the repository private.

## Make the client log

```sh
install -d -m 0700 ~/.private/uc/example-org/logs ~/.private/uc/example-org/logs/rejected
```

uc-node writes a rejection here when it cannot secure a node, and makes the folder, mode `0700`, when it is missing. [Hand Over to the Fleet](4-hand-over-to-the-fleet.md#when-a-node-is-rejected) shows what a rejection looks like.

## Make the client's SSH key

Each client has its own key for the initial user of its raw nodes. Every node definition holds its public key, the build installs it for the initial user, and uc-controller's admission logs in with its private key. Name it `<client>-raw-initial-id_ed25519`:

```sh
ssh-keygen -t ed25519 -f ~/.ssh/example-org-raw-initial-id_ed25519 -C example-org-raw-initial-id_ed25519
```

Give it a passphrase, and keep the passphrase in your password manager. Ansible cannot type a passphrase, so load the key into the agent before a build on the ssh platform and before admission, as uc-controller's `en/docs/ssh-key-loading-for-controller-activities-v0.1.0.md` shows:

```sh
ssh-add -t 1h ~/.ssh/example-org-raw-initial-id_ed25519
```

Check:

```sh
ls -l ~/.ssh/example-org-raw-initial-id_ed25519 ~/.ssh/example-org-raw-initial-id_ed25519.pub
ssh-keygen -lf ~/.ssh/example-org-raw-initial-id_ed25519.pub
```

The private key must be `-rw-------`. The second command prints the key's fingerprint, ending in `example-org-raw-initial-id_ed25519 (ED25519)`.

## Write the defaults for node definitions

`scripts/new-node` offers its defaults from `intake/defaults.yml`. Write it as [Set Up the Defaults for New Nodes](1-setup-the-defaults-for-new-nodes.md) describes, at exactly that path in the client inventory. For `example-org`:

```yaml
---
# intake/defaults.yml: the defaults uc-node's scripts/new-node offers.
# No secrets: the password hashes are in the batch.
client_domain: example.org
initial_username: initial
ssh_public_key: ~/.ssh/example-org-raw-initial-id_ed25519.pub
ssh_port: 22
ssh_sources: []
```

`ssh_public_key` names the client's key from [Make the client's SSH key](#make-the-clients-ssh-key), as the path to its `.pub` file. A path keeps the line short: the key line itself, with the client's comment, is about 130 characters, past the client inventory's yamllint limit of 120. `scripts/new-node` writes the key line into each node definition folded before its comment, which fits, so leave the fold as it is. Then the limit can stay an error in `.yamllint`.

The file holds no hash, and only the settings `scripts/new-node` offers, named as in a node definition, such as `initial_username`. `scripts/new-node` refuses a defaults file that holds `root_password_hash`, `initial_password_hash` or any crypt hash, or a setting it does not offer, and names it.

When `scripts/new-node` finds the file, it asks "Use defaults from ~/.private/uc/example-org/uc-inventory/intake/defaults.yml?". When it does not, it says "No defaults file", and offers no client domain and no key. If you see that, stop with Ctrl-C and check the path.

## Make the first commit

Make the first commit once the `CHANGE-ME` values are replaced and `intake/defaults.yml` is written, on the branch `main`, with `UC_CONTROLLER` set so the pre-commit hook can run:

```sh
cd ~/.private/uc/example-org/uc-inventory
git branch --show-current
git add -A
UC_CONTROLLER=~/uc-controller git commit -m "Start the example-org inventory"
```

`git branch --show-current` must print `main`. If the hook refuses the commit, its message names the file and the rule. The hook shows yamllint's warnings as well, and they do not stop the commit.

The first commit holds the template and `intake/defaults.yml`. A node definition is committed later, with its candidate, after its build, as [Hand Over to the Fleet](4-hand-over-to-the-fleet.md#review-and-commit-the-candidate) says, so the history records a node when it was built and handed over. If a node definition is already in `intake/`, committing it now does no harm: guide 4's `git add` then finds nothing new in it. Candidates and admission are committed later too.

## Make a build batch

A batch is the nodes built with one root password and one batch password, the password of the initial user. Its name is `raw-YYYY-MM-DD-NN`: the day you make it, and a number for that day, starting at `01`, such as `raw-2026-11-27-01`. In the commands below, put the day's date in place of `YYYY-MM-DD`, and the number in place of `NN`. Never use a date in 1970: `raw-1970-01-01-NN` is reserved for documents and tests.

### Choose the passwords

The batch password must be at least 15 characters (RN-ACC-08). A passphrase of six or more words chosen with dice from a published word list meets it, and can be typed at a console. Keep both passwords in your password manager before you go on: the files below are working copies, not the backup.

### uc-node's file, the hashes

From the uc-node checkout:

```sh
cd ~/uc-node
scripts/new-batch raw-YYYY-MM-DD-NN
```

Output example:

```text
Root password:
Batch password, for the initial user (at least 15 characters):
Batch password again:
Wrote ~/.secrets/uc/build/batches/raw-YYYY-MM-DD-NN.yml, mode 0600, with root_password_hash and initial_password_hash.

The batch password itself goes to uc-controller, in its file
~/.secrets/uc/fleet/batches/raw-YYYY-MM-DD-NN.yml, by en/docs/guides/batch-secrets.md in uc-controller.
uc-node never stores it. Keep both passwords where you keep secrets that must
survive the loss of this machine, such as a password manager.
```

The passwords are read from the terminal without echo, and given to `openssl passwd -6` on its standard input, so they never reach shell history or the process list. The script makes `~/.secrets/uc/build/batches/` with mode `0700` where it is missing, and refuses a batch whose file exists: a batch is never rewritten, only retired and replaced.

### uc-controller's file, the password

Write the same batch password to `~/.secrets/uc/fleet/batches/raw-YYYY-MM-DD-NN.yml` with the recipe in uc-controller's guide, `en/docs/guides/batch-secrets.md`, section Creating a batch file. Type it exactly as you typed it for `scripts/new-batch`. If the two differ, the nodes build, and admission's become with the batch password fails.

### Check the batch

```sh
ls -ld ~/.secrets ~/.secrets/uc ~/.secrets/uc/build ~/.secrets/uc/build/batches
ls -l ~/.secrets/uc/build/batches/raw-YYYY-MM-DD-NN.yml
```

Every directory must be `drwx------` and the file `-rw-------`, all owned by you. Then check that `uc_secret` reads it, from the uc-node checkout, without showing the hash:

```sh
ansible localhost -m ansible.builtin.debug \
  -a "msg={{ lookup('uc_secret', 'batches/raw-YYYY-MM-DD-NN', key='initial_password_hash') is match('[$]6[$]') }}"
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

It must ask "Use defaults from ~/.private/uc/example-org/uc-inventory/intake/defaults.yml?". Answer `y`, press Enter for the node label and the platform, give the batch, then answer `n` to the write question. If the batch file is missing, the script says so, without opening it.

The client is set up. Write the first node definition, and build it, as [Build and Check a Raw Node](2-build-and-check-a-raw-node.md) shows on the local Incus host, or [Build a Node on an SSH Host](3-build-a-node-on-an-ssh-host.md).

## Changelog

| Version | Date | Change |
| :-- | :-- | :-- |
| 0.2.1 | 2026-11-27 | From phase two's run: the defaults setting is `initial_username`, as in a node definition, and `scripts/new-node` refuses one it does not offer; the key as a path keeps `intake/` within the yamllint limit, so the limit can stay an error; the first commit holds the template and the defaults, and a node definition is committed with its candidate |
| 0.2.0 | 2026-11-27 | From the operator's notes on setting up `example-org`: `scripts/new-inventory` is uc-controller's, with its output and what a second run does; the branch `main` and the first commit; the client's SSH key, named by `intake/defaults.yml` and `onboard_ssh_private_key_file`; what `scripts/new-node` says without a defaults file; batch names as `raw-YYYY-MM-DD-NN` with the day's date, since `raw-1970-01-01-NN` is reserved for documents and tests. Moving node definitions out of `~/.secrets/uc-raw/` and retiring it removed: nothing runs 0.2.0 |
| 0.1.0 | 2026-11-27 | First version, provisional: the client's folder, its inventory, log and intake defaults, a build batch for both controllers, moving node definitions out of `~/.secrets/uc-raw/`, and retiring `~/.secrets/uc-raw/` and `~/.secrets/uc-raw-node/` |
