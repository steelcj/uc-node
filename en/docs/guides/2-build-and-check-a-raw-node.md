---
title: Build and Check a Raw Node
description: How to write a node definition into a client inventory, build the raw node on the local Incus host with scripts/build, check the node, its confirmation and its candidate, build it again, and check that an instance uc-node does not own is refused.
version: 0.2.0
status: provisional
date: 2026-11-27
language: en-CA
---

# Build and Check a Raw Node

This guide writes a node definition with `scripts/new-node`, builds the raw node on the local Incus host with `scripts/build`, and checks the result. It assumes the client is set up as [Set Up a Client](0-set-up-a-client.md) describes, with a build batch and the defaults from [Set Up the Defaults for New Nodes](1-setup-the-defaults-for-new-nodes.md), and that the requirements in the [README](../../../README.md#requirements) are installed. To build on a host reached over SSH instead, see [Build a Node on an SSH Host](3-build-a-node-on-an-ssh-host.md).

Run every command from the repository directory. The examples use the client `example-org`, whose inventory is `~/.private/uc/example-org/uc-inventory`, the domain `example.org`, and the batch `raw-1970-01-01-01`.

## Write the node definition

```sh
scripts/new-node ~/.private/uc/example-org/uc-inventory
```

With the defaults, this is five answers:

```text
Use defaults from ~/.private/uc/example-org/uc-inventory/intake/defaults.yml? [Y/n]: y
Node label (raw, dev, stage, prod) [raw]:
Platform (incus, ssh) [incus]:
Batch (raw-YYYY-MM-DD-NN) []: raw-1970-01-01-01
Write ~/.private/uc/example-org/uc-inventory/intake/raw.example.org.yml? [y/N]: y
Wrote ~/.private/uc/example-org/uc-inventory/intake/raw.example.org.yml

Build it with:

  scripts/build ~/.private/uc/example-org/uc-inventory raw.example.org
```

The node definition is named after the node's fully qualified domain name, `<node label>.<client domain>`, and written with mode `0644`. It holds no secret: it names its batch in `raw_node_batch`, and the build reads the batch's password hashes through `uc_secret`.

## Build the node

```sh
scripts/build ~/.private/uc/example-org/uc-inventory raw.example.org
```

`scripts/build` prints the command it runs, `ansible-playbook build.yml` with the node definition and `uc_client_inventory`, and runs it from the repository, so Ansible reads `ansible.cfg` and the inventory.

To check the confirmation with uc-controller's checker as the build writes it, set `UC_CONTROLLER` to the uc-controller checkout first:

```sh
UC_CONTROLLER=~/uc-controller scripts/build ~/.private/uc/example-org/uc-inventory raw.example.org
```

Without it, the build says that the confirmation was not checked.

The build first checks the node definition, the client inventory and the batch, and stops before anything is created if a field is missing or breaks its rule, or the batch file is missing or badly protected, with a message saying what to fix.

The Incus instance is named after the node's fully qualified domain name, with dots replaced by hyphens, since Incus allows only letters, digits and hyphens: `raw-example-org`.

The first run downloads `images:debian/13` if it is not cached yet. The bootstrap step shows a red "Test connection" error on a new node: the role tries Ansible's `ping` before Python is installed, catches the failure and installs Python. The recap counts it as `rescued=1`, not as a failure.

The build reboots the node, waits for it to finish booting, and fails if systemd found an ordering cycle during the boot. It then measures the confirmation on the node, writes it to `/var/lib/raw-node/confirmation.yml`, reads it back, checks it, and writes the candidate to `candidates/raw.example.org.yml`. It ends with what to compare at the console:

```text
TASK [Show the node, and what to compare at its console before admission] ******
ok: [raw.example.org] => {
    "msg": [
        "raw.example.org is connected securely. Its candidate is /home/operator/.private/uc/example-org/uc-inventory/candidates/raw.example.org.yml.",
        "Address: 10.0.0.21, SSH port 22",
        "ED25519 host key: SHA256:EXAMPLEexampleEXAMPLEexampleEXAMPLEexample0",
        "Before admission, compare this fingerprint with the one the node's console shows:",
        "  incus exec raw-example-org -- ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub",
        "The confirmation passed check_raw_confirmation.py."
    ]
}
```

[Hand Over to the Fleet](4-hand-over-to-the-fleet.md) takes it from there.

## Check the node

```sh
incus config get raw-example-org user.uc-raw-node.owner
incus exec raw-example-org -- hostname
incus exec raw-example-org -- hostname -f
incus exec raw-example-org -- systemctl is-system-running
incus exec raw-example-org -- python3 --version
incus exec raw-example-org -- sudo --version
incus exec raw-example-org -- sshd -T | grep -E '^(port|permitrootlogin|passwordauthentication) '
incus exec raw-example-org -- systemctl is-active foomuuri
incus exec raw-example-org -- ls /etc/foomuuri
incus exec raw-example-org -- journalctl --list-boots
incus exec raw-example-org -- ls -l /var/lib/raw-node/confirmation.yml
incus exec raw-example-org -- ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

Expected:

| Check | Expected |
| :-- | :-- |
| Ownership marker | `uc-raw-node` |
| `hostname`, `hostname -f` | `raw`, `raw.example.org` |
| `systemctl is-system-running` | `running` |
| Python and `sudo` | Their versions |
| `sshd -T` | `port 22`, `permitrootlogin no`, `passwordauthentication no` |
| Foomuuri | `active`, with `10-base.conf` its only file |
| `journalctl --list-boots` | Two boots, the second starting at the build's reboot |
| The confirmation | `-rw-r--r-- 1 root root` |
| The ED25519 fingerprint | The one the build printed, and the one in the candidate |

Then the candidate, in the client inventory:

```sh
cat ~/.private/uc/example-org/uc-inventory/candidates/raw.example.org.yml
```

It holds the node's address on the Incus network, port 22, the same fingerprint, the batch, the label and platform, uc-node's version, the contract version and when the build finished.

## Run it again

```sh
scripts/build ~/.private/uc/example-org/uc-inventory raw.example.org
```

Expected: `changed=0` for localhost, and `changed=3` for `raw.example.org`: the reboot, the confirmation, whose timestamp changes, and the candidate, whose build time changes. The build reboots on every run, on purpose. No second instance is created.

## Check that an instance uc-node does not own is refused

Launch an instance without the ownership marker, under the name a `dev` node for `example.org` would use:

```sh
incus launch images:debian/13 dev-example-org
```

Write a node definition for it. Answer `y` to "Use defaults?", `dev` to the node label, press Enter for the platform, and give the batch:

```sh
scripts/new-node ~/.private/uc/example-org/uc-inventory
```

Then build it, and check the instance was left alone:

```sh
scripts/build ~/.private/uc/example-org/uc-inventory dev.example.org
incus config get dev-example-org user.uc-raw-node.owner
```

Expected: the build fails with "dev-example-org exists but was not created by uc-raw-node, so it is left alone", before anything runs on the instance, and the last command prints nothing. The refusal comes before the node is in the build's inventory, so it is not a rejection, and nothing is written to `logs/rejected/`.

## Clean up

```sh
incus delete --force raw-example-org dev-example-org
rm ~/.private/uc/example-org/uc-inventory/intake/dev.example.org.yml
rm ~/.private/uc/example-org/uc-inventory/candidates/raw.example.org.yml
```

Keep `intake/raw.example.org.yml` if you want to build the node again.

## Changelog

| Version | Date | Change |
| :-- | :-- | :-- |
| 0.2.0 | 2026-11-27 | Node definitions in the client inventory's `intake/`, written with `scripts/new-node <client inventory>` and built with `scripts/build`. The batch, the confirmation, the candidate and the fingerprint printed at the end. A second build changes three things. Front matter added |
| 0.1.0 | 2026-11-24 | First version, with node definitions in `~/.secrets/uc-raw/` |
