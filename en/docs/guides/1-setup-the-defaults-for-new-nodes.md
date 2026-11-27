---
title: Set Up the Defaults for New Nodes
description: How to write a client inventory's intake/defaults.yml, the values scripts/new-node offers for each new node definition, and check that the script accepts them.
version: 0.2.0
status: provisional
date: 2026-11-27
language: en-CA
---

# Set Up the Defaults for New Nodes

`scripts/new-node <client inventory>` reads its defaults from `<client inventory>/intake/defaults.yml`. The defaults are the values most of the client's nodes share. The node's label, its platform, its batch and, on the `ssh` platform, its address differ from node to node, so `scripts/new-node` always asks for them.

The file holds no secret, like every file in the client inventory. The password hashes are in the build batch the node definition names, which `scripts/new-batch` writes. `scripts/new-node` refuses a defaults file that holds `root_password_hash`, `initial_password_hash` or any crypt hash.

This guide assumes the client is set up as [Set Up a Client](0-set-up-a-client.md) describes. The examples use the client `example-org`, whose inventory is `~/.private/uc/example-org/uc-inventory`.

## Write the file

```sh
mkdir -p ~/.private/uc/example-org/uc-inventory/intake
"${EDITOR:-nano}" ~/.private/uc/example-org/uc-inventory/intake/defaults.yml
```

Then paste:

```yaml
---
# intake/defaults.yml: the defaults uc-node's scripts/new-node offers.
# No secrets: the password hashes are in the batch the node names.

# The client's domain. A node is named <node label>.<client domain>,
# for example dev.example.org.
client_domain: example.org

# The initial user of a raw node.
initial_user: initial

# The public key the initial user logs in with: the key line itself, or the
# path to a .pub file. The node definition holds the key line.
ssh_public_key: ~/.ssh/example-org-raw-initial-id_ed25519.pub

# The port SSH listens on. Keep 22: the client inventory layout fixes it there.
ssh_port: 22

# Addresses or networks allowed to reach SSH. Empty means any. On the ssh
# platform, the list must include the controller's own public address.
ssh_sources: []

# Optional: the batch offered when scripts/new-node asks for one. It is
# asked for every node all the same.
# raw_node_batch: raw-1970-01-01-01
```

The file is written like any other in the client inventory, mode `0644`, and committed with it.

| Setting | Rule |
| :-- | :-- |
| `client_domain` | DNS labels of lowercase letters, digits and hyphens, separated by dots |
| `initial_user` | Lowercase letters, digits, `-` and `_`, starting with a letter or `_`, at most 32 characters, never `root` |
| `ssh_public_key` | An OpenSSH public key line, or the path to a `.pub` file, that `ssh-keygen` accepts |
| `ssh_port` | A number from 1 to 65535 |
| `ssh_sources` | IPv4 or IPv6 addresses or networks, without host bits set |
| `raw_node_batch` | `raw-YYYY-MM-DD-NN`, on a real date |

## Check that the script accepts it

```sh
scripts/new-node ~/.private/uc/example-org/uc-inventory
```

Answer `y` to "Use defaults?", press Enter for the node label and the platform, give a batch such as `raw-1970-01-01-01`, then answer `n` to the write question. If a value does not meet its rule, the script names the setting and says why. If the batch has no file in `~/.secrets/uc/build/batches/` yet, it says so, without opening anything there.

Next: [Build and Check a Raw Node](2-build-and-check-a-raw-node.md) on the local Incus host, or [Build a Node on an SSH Host](3-build-a-node-on-an-ssh-host.md).

## Changelog

| Version | Date | Change |
| :-- | :-- | :-- |
| 0.2.0 | 2026-11-27 | The defaults move from `~/.secrets/uc-raw/defaults.yml` to the client inventory's `intake/defaults.yml`, without the password hashes, which are in the build batch. Front matter, a table of the rules, and the optional `raw_node_batch` added |
| 0.1.0 | 2026-11-24 | First version, for `~/.secrets/uc-raw/defaults.yml` with the default password hashes |
