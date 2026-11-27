---
title: Build a Node on an SSH Host
description: How to build a raw node on a Debian 13 host reached over SSH, such as a VPS, from a fresh install, how to check it, build it again, and what to do when something goes wrong.
version: 0.3.1
status: provisional
date: 2026-11-27
language: en-CA
---

# Build a Node on an SSH Host

This guide builds a raw node on the `ssh` platform: a Debian 13 host that uc-node reaches over SSH, such as a VPS. It starts from a fresh install, a newly ordered Debian 13 host with your key installed for root, where root logs in on port 22 for the first build. Later builds log in as the initial user.

It assumes the client is set up as [Set Up a Client](0-set-up-a-client.md) describes, with a build batch and the defaults from [Set Up the Defaults for New Nodes](1-setup-the-defaults-for-new-nodes.md), and that the requirements in the [README](../../../README.md#requirements) are installed. Run every command from the repository directory.

The examples use the client `example-org`, whose inventory is `~/.private/uc/example-org/uc-inventory`, the node `raw.example.org` at `203.0.113.10`, the initial user `initial`, the batch `raw-YYYY-MM-DD-NN`, with the date your batch was made, and the key `~/.ssh/example-org-raw-initial-id_ed25519`. Use your own values.

## What the build does on an SSH host

| Step | What happens |
| :-- | :-- |
| Connect | Tries the initial user on `ssh_port` once, then root on port 22 once. A failed login is never retried |
| Check ownership | Reads `/etc/uc-raw-node/owner`. Without it, the build stops before any change, unless you adopt the host |
| Wait | Waits for systemd to report `running` or `degraded`, for at most five minutes |
| Bootstrap | Installs Python, `sudo` and the other packages Ansible needs |
| Prepare | Removes files in `/etc/ssh/sshd_config.d/` that set `PasswordAuthentication`, `PermitRootLogin` or `Port`, and, if cloud-init is installed, keeps it away from the hostname and disables it |
| Configure | Hostname, root's password, the initial user, the Foomuuri firewall and key-only SSH |
| Switch | Moves to the initial user on `ssh_port`, with `sudo`, and empties root's `authorized_keys` |
| Reboot | Reboots, checks that the boot ID changed, waits for the node, and fails if systemd found an ordering cycle |
| Confirm | Measures the confirmation on the node, writes `/var/lib/raw-node/confirmation.yml`, reads it back over the same pinned connection, and checks it with uc-controller's checker when `UC_CONTROLLER` is set |
| Hand over | Writes the candidate, `candidates/raw.example.org.yml`, in the client inventory, and prints the ED25519 fingerprint to compare at the provider's console |

### Why cloud-init is disabled

On Debian 13, cloud-init 25 and Foomuuri form a systemd ordering cycle. At the next boot, systemd breaks the cycle by skipping one unit. On the Debian 13 cloud image it skipped cloud-init's network stage, so the rest of cloud-init waited forever and the node never left `starting`. systemd may skip either side of a cycle, so another boot could skip the firewall instead. See [Foomuuri and cloud-init Ordering Cycle](../known-issues/foomuuri-cloud-init-ordering-cycle.md).

So when cloud-init is installed, the build creates `/etc/cloud/cloud-init.disabled` before the reboot, and cloud-init does not run again. It also writes `/etc/cloud/cloud.cfg.d/99-uc-raw-node.cfg`, with `preserve_hostname: true` and `manage_etc_hosts: false`, in case cloud-init is ever turned back on.

The network configuration cloud-init wrote at the first boot stays in place. Changes the provider makes to the network later, such as a new address, an added IPv6 address or a new private network, are not picked up. Apply them by hand, through the provider's console if the change cuts SSH off.

## Prepare a fresh install

### Order the host

Order Debian 13 with your SSH key installed for root. If the provider only sets a root password, install the key while password login still works, once:

```sh
ssh-copy-id -i ~/.ssh/id_ed25519.pub root@203.0.113.10
```

Check the system is Debian 13, and whether the provider runs cloud-init:

```sh
ssh root@203.0.113.10 'cat /etc/os-release | head -n 2; ls /usr/bin/cloud-init'
```

### Test the console

Log in as root through the provider's web console once, before the first build. It is the way back in when SSH is unreachable, and it works without the network configuration.

### Write the node definition

```sh
scripts/new-node ~/.private/uc/example-org/uc-inventory
```

Answer `ssh` for the platform, then the node's address and the batch. Keep `ssh_port: 22` for the first build: moving the port in the same build as first contact is refused. If you give `ssh_sources`, the script asks you to confirm that the list includes your controller's own public address, since the firewall only lets those addresses reach SSH.

The script writes `~/.private/uc/example-org/uc-inventory/intake/raw.example.org.yml`, then prints the entry to add to `~/.ssh/config`, described next.

## Add the node to ~/.ssh/config

Every connection the build makes uses `IdentitiesOnly=yes`, so ssh offers only the default key files, such as `~/.ssh/id_ed25519`, and the keys `~/.ssh/config` names for the node's address. It never offers every key in the agent, which would count as failed logins on the node. A key kept anywhere else must be named in `~/.ssh/config`:

```text
# uc-node: raw.example.org
Host 203.0.113.10
    IdentityFile ~/.ssh/example-org-raw-initial-id_ed25519
    IdentitiesOnly yes
    # Optional, only for manual ssh/scp; the build passes the user itself
    User initial
```

`scripts/new-node` prints this entry with the node's values filled in, and so does the build when both of its logins are refused with `Permission denied`.

- The `Host` line must be the address. Ansible connects to `node_address`, so ssh matches the entry against the address. An entry for an alias, such as `Host raw.example.org` with `HostName 203.0.113.10`, does not match.
- Put the entry before any `Host *` block. ssh uses the first value it finds for each option, so a `Host *` block above it would win.
- A new address means a new entry here, and a new known_hosts line, described next.

Test the entry with one plain login before the build. For a fresh install, the key is root's:

```sh
ssh root@203.0.113.10 true && echo ok
```

For a node uc-node has already built, the key is the initial user's:

```sh
ssh initial@203.0.113.10 true && echo ok
```

Run each test once. If it fails, fix the cause before trying again: each failed login counts towards OpenSSH 10's PerSourcePenalties, which blocks your address for a while after repeated failures.

## Check the host key

The build checks the host key on every connection, first contact included, and never accepts an unknown one. Add it to `~/.ssh/known_hosts` once, after checking it.

Read the key over the network and show its fingerprint:

```sh
ssh-keyscan -t ed25519 203.0.113.10 > /tmp/raw-example-org.key
ssh-keygen -lf /tmp/raw-example-org.key
```

In the provider's web console, show the fingerprint the host itself has:

```sh
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

If the two fingerprints match, add the key and remove the temporary file:

```sh
cat /tmp/raw-example-org.key >> ~/.ssh/known_hosts
rm /tmp/raw-example-org.key
```

uc-node looks the host key up under the bare address, which is how ssh records a key on port 22, so the one line serves both the build and a manual `ssh`.

Never turn host key checking off to save this step, with `StrictHostKeyChecking=no`, `accept-new` or `ANSIBLE_HOST_KEY_CHECKING=False`. The build refuses to run with Ansible's host key checking off.

## Adopt the node

The first build of a host adopts it: it writes the ownership marker `/etc/uc-raw-node/owner`. Give `-e uc_raw_node_adopt=true` only for the host you ordered. A wrong address in a node definition then fails safely, instead of reconfiguring someone else's server.

```sh
UC_CONTROLLER=~/uc-controller scripts/build ~/.private/uc/example-org/uc-inventory raw.example.org -e uc_raw_node_adopt=true --ask-become-pass
```

`scripts/build` passes every argument after the node's name to `ansible-playbook`. `UC_CONTROLLER` names the uc-controller checkout, whose checker the build runs on the confirmation. Without it, the build says that the confirmation was not checked.

`--ask-become-pass` asks for the initial user's password: the batch password of the batch the node definition names, whose hash is `initial_password_hash` in `~/.secrets/uc/build/batches/raw-YYYY-MM-DD-NN.yml`. Every ssh build needs it, the first included: after the configure play, the build switches to the initial user, and the reboot runs with `sudo`.

### Give the initial user's password, not the provider's

Ansible's prompt only says `BECOME password:`, and on a fresh host the only password you have is the root password the provider gave you. Do not give that one. The first build logs in as root with your key, and root needs no `sudo`, so the build does not use the password you typed until it switches to the initial user. By then the configure play has set both root's and the initial user's passwords from the batch, and root can no longer log in over SSH. A wrong password is only found at that point, and the build fails on its first `sudo` task with [Incorrect sudo password](#incorrect-sudo-password).

The provider's root password is not used anywhere in the build. After the first build, root's password is the batch's root password, whose hash is `root_password_hash`.

### Check the password before the first build

The build does not compare the password you type with `initial_password_hash`, so check it by hand before an adoption build. This hashes the password you type with the salt of the batch's hash, and says whether the two match, without showing either. In bash:

```sh
batch=raw-YYYY-MM-DD-NN   # the batch the node definition names
hash=$(python3 -c 'import sys, yaml; print(yaml.safe_load(open(sys.argv[1]))["initial_password_hash"])' \
  ~/.secrets/uc/build/batches/"$batch".yml)
IFS= read -rs -p 'Batch password: ' pw; echo
if [ "$(printf '%s\n' "$pw" | openssl passwd -6 -salt "$(printf '%s' "$hash" | cut -d'$' -f3)" -stdin)" = "$hash" ]
then echo 'It matches.'; else echo 'It does not match.'; fi
unset pw hash
```

If it matches, that is the password to give `--ask-become-pass`. If it does not, find the right password, or make a new batch with `scripts/new-batch` and name it in the node definition, before you build. The same check works for `root_password_hash`.

Expected, at the end, the node's address and its ED25519 fingerprint, and then:

```text
localhost                  : ok=<n>  changed=0    unreachable=0    failed=0    skipped=<n>  rescued=0    ignored=0
raw.example.org            : ok=<n>  changed=<n>  unreachable=0    failed=0    skipped=<n>  rescued=0    ignored=0
```

The counts vary with the host. What matters is `failed=0`. Compare the fingerprint with the one the provider's console shows before admission, as [Hand Over to the Fleet](4-hand-over-to-the-fleet.md#compare-the-fingerprint-at-the-console) describes. The reboot can be very fast, but it is real: the build fails if the boot ID did not change. See [robertdebock.reboot Reports Changed Without Rebooting](../known-issues/robertdebock-reboot-reports-changed-without-rebooting.md) for why that check matters.

## Check the node

`sudo` over `ssh` needs a terminal, so use `ssh -t`, and give the initial user's password when `sudo` asks:

```sh
ssh -t initial@203.0.113.10 '
  hostname; hostname -f
  systemctl is-system-running
  cat /etc/uc-raw-node/owner
  ls /etc/cloud/cloud-init.disabled
  sudo wc -c /root/.ssh/authorized_keys
  sudo sshd -T | grep -E "^(port|permitrootlogin|passwordauthentication) "
  systemctl is-active foomuuri
  sudo journalctl -b SYSLOG_IDENTIFIER=systemd | grep -ci "ordering cycle"
  ls -l /var/lib/raw-node/confirmation.yml
'
```

| Check | Expected |
| :-- | :-- |
| `hostname`, `hostname -f` | `raw`, `raw.example.org` |
| `systemctl is-system-running` | `running` |
| Ownership marker | `uc-raw-node` |
| `/etc/cloud/cloud-init.disabled` | Exists, on a host with cloud-init |
| Root's `authorized_keys` | `0` bytes |
| `sshd -T` | `port` is `ssh_port`, `permitrootlogin no`, `passwordauthentication no` |
| Foomuuri | `active` |
| Ordering cycles from systemd | `0` |
| The confirmation | `-rw-r--r-- 1 root root`, readable by the initial user |

The journal check needs `sudo`. Without it, `journalctl` shows the initial user only its own messages, hides systemd's, and prints `0` whatever happened. It is filtered on `SYSLOG_IDENTIFIER=systemd`, because the build's own check logs a command line that holds the search text. A real cycle is a line from systemd that starts with `Found ordering cycle`.

Then the checks that matter most on a remote host:

| Check | How | Expected |
| :-- | :-- | :-- |
| Root cannot log in | `ssh root@203.0.113.10 true` | `Permission denied` |
| Passwords are refused | `ssh -o PubkeyAuthentication=no initial@203.0.113.10 true` | `Permission denied` |
| Root's password is set | `ssh -t initial@203.0.113.10 'su - root -c "id -un"'` | `root` |
| The console works | Log in as root through the provider's web console |  |

Each refused login counts towards PerSourcePenalties, so run these once.

## Build it again

Later builds find the contract connection without being told, and do not need `uc_raw_node_adopt`:

```sh
UC_CONTROLLER=~/uc-controller scripts/build ~/.private/uc/example-org/uc-inventory raw.example.org --ask-become-pass
```

Expected: `changed=0` for localhost and `changed=3` for the node, with `failed=0`: the reboot, the confirmation, whose timestamp changes, and the candidate, whose build time changes. The build reboots on every run, on purpose.

## What the ssh platform does not do yet

- Move SSH to another port after the first build. Build first with `ssh_port: 22`. A later change of `ssh_port` makes the build look for the node on the new port while sshd still listens on the old one.
- Pick up network changes the provider makes after the first boot, since cloud-init is disabled.
- Order a host through a provider's API. The host is ordered by hand, and adopted.

## When you are locked out

### After repeated failed logins

OpenSSH 10's PerSourcePenalties blocks an address that keeps failing to log in, for up to ten minutes by default. While it lasts, every connection from your address is closed before login, even with the right key. Stop trying, find the cause from the troubleshooting section below, wait, then try once. The build itself tries each login only once. See [OpenSSH PerSourcePenalties Lockouts](../known-issues/openssh-per-source-penalties-lockout.md).

### After a firewall or SSH change

If `ssh_sources` leaves out your address, or SSH moved to a port the firewall does not allow, log in as root through the provider's web console, with root's password. Then fix the setting by hand, for example in `/etc/foomuuri/`, and the node definition, before the next build.

### After losing the initial user's password

Make a new batch with `scripts/new-batch`, with a new batch password, and write that password to uc-controller's file for the batch. Log in as root through the console, set the new password with `passwd initial`, name the new batch in the node definition's `raw_node_batch`, and build again. Retire the old batch once no node uses it.

## Troubleshooting by error message

### The node definition holds a password hash

```text
The node definition holds root_password_hash or initial_password_hash, which are no longer used. Make a batch with scripts/new-batch, ...
```

A node definition never holds a password hash: the hashes are in the batch its `raw_node_batch` names. Remove both from the node definition, or write it again with `scripts/new-node`, and make the batch with `scripts/new-batch` if it has no file. Nothing was changed on the node.

### uc_client_inventory must be the absolute path of a client inventory

The build was run with `ansible-playbook` directly, without `-e uc_client_inventory=...`, or the path has no `intake/`. Build with `scripts/build <client inventory> <fqdn>`, which passes it.

### The client inventory has no node definition for the node in intake/

The node definition passed with `-e @` is not the one in the client inventory's `intake/`, or the one there names another node. Build with `scripts/build`, which takes the node definition from `intake/`.

### uc_secret: there is no file, or a mode is wrong

```text
uc_secret: batches/raw-1970-01-01-01: there is no file /home/operator/.secrets/uc/build/batches/raw-1970-01-01-01.yml. Create it, as en/docs/guides/0-set-up-a-client.md describes.
```

The batch the node definition names has no file, or its file or a directory above it is not private. Make the batch with `scripts/new-batch`, or fix the mode the message names. The message never includes a value. Nothing was created or changed.

### The confirmation does not meet the contract

```text
check_raw_confirmation.py found that the confirmation on raw.example.org does not meet the contract: fail. The task above shows its findings.
```

The node was built, but uc-controller's checker found that the confirmation breaks a clause. The task above lists each finding with its clause. The build is rejected: see [When a node is rejected](4-hand-over-to-the-fleet.md#when-a-node-is-rejected).

### The node definition sets hostname, which is no longer used

```text
The node definition sets hostname, which is no longer used. Rename hostname to client_domain in the node definition.
```

`hostname` is not a node definition field. The node's names come from `client_domain` and `node_label`. Write the node definition again with `scripts/new-node`. Nothing was changed on the node.

### node_address must be an address

```text
node_address must be an IPv4 or IPv6 address, for example 203.0.113.10. It is <vps-address>.
```

`node_address` holds something other than an address, often a placeholder left from an example. Put the node's address in. Before this check existed, the same mistake reached the probes and failed there with `hostname contains invalid characters`.

### The host key is not in known_hosts

```text
The host key of 203.0.113.10 is not in known_hosts, or does not match the one there, so nothing was changed.
```

Either the key was never added, or the host has a new key: reinstalled, a new host at a reused address, or someone in between. Check the key against the console as [Check the host key](#check-the-host-key) shows. If the host was reinstalled, remove the old line first with `ssh-keygen -R 203.0.113.10`.

### Could not log in, with Permission denied

```text
Could not log in to 203.0.113.10 as initial on port 22 (initial@203.0.113.10: Permission denied (publickey).), or as root on port 22 (root@203.0.113.10: Permission denied (publickey).).
```

Neither the initial user nor root accepted the key ssh offered. The task above the message shows the `~/.ssh/config` entry the node needs.

- If the key is outside the default key files, add the entry, as [Add the node to ~/.ssh/config](#add-the-node-to-sshconfig) shows. A manual `ssh -i <key>` working is the sign of this: the build does not use `-i`.
- If the entry is there, check that its `Host` line is the address, and that it comes before any `Host *` block.
- On a fresh install, check that the key is in root's `authorized_keys`.
- On a node uc-node has already built, check `ssh_port`: the build looks for the initial user on `ssh_port`, and for root on port 22.

Test with one plain `ssh` before running the build again.

### Could not log in, with Connection refused or timed out

The node is not listening on that port, the firewall drops your address, or the address is wrong. On a node uc-node has already built, check `ssh_port` against the port the node really uses. If you tried several times in a row, PerSourcePenalties may be closing your connections, see [After repeated failed logins](#after-repeated-failed-logins).

### Connection closed by remote host

Typically `kex_exchange_identification: Connection closed by remote host`, before any login. sshd is refusing your address for a while after repeated failed logins. See [After repeated failed logins](#after-repeated-failed-logins).

### Ansible's SSH host key checking is turned off

```text
Ansible's SSH host key checking is turned off, for example by ANSIBLE_HOST_KEY_CHECKING=False. uc-raw-node builds only with it on.
```

Unset `ANSIBLE_HOST_KEY_CHECKING`, and remove `host_key_checking = False` from any Ansible configuration that applies.

### The host has no ownership marker

```text
203.0.113.10 has no /etc/uc-raw-node/owner, so nothing was changed. Adopt only the host that was ordered for raw.example.org: if this is that host, run again with -e uc_raw_node_adopt=true.
```

This is the first build of this host with uc-node, or the address is wrong. If it is the host you ordered, run again with `-e uc_raw_node_adopt=true`.

### The ownership marker holds something else

```text
/etc/uc-raw-node/owner on 203.0.113.10 does not hold uc-raw-node, so the host is left alone.
```

Another tool claims the host. Find out who, before changing anything.

### The node answers only on the first-contact port

```text
203.0.113.10 answers only on the first-contact port 22, and the node definition sets ssh_port 2222.
```

The first build of a fresh install must keep `ssh_port: 22`. Set it, build, and leave it.

### Missing sudo password

The build was run without `--ask-become-pass`. Every ssh build needs it, the first included. Run it again with the flag.

### Incorrect sudo password

The password given to `--ask-become-pass` is not the initial user's. It is the batch password, whose hash is `initial_password_hash` in the batch the node definition names, not root's, and not the root password the provider gave you. See [Give the initial user's password, not the provider's](#give-the-initial-users-password-not-the-providers).

On a first build this error comes from the task `Look for root's authorized_keys`, after the configure play has run. The node is then part way to contract: root cannot log in over SSH, the initial user logs in with the key on `ssh_port`, and the ownership marker is written. Check the password as [Check the password before the first build](#check-the-password-before-the-first-build) shows, then run the build again with the right one. It finds the contract connection, and `uc_raw_node_adopt` is no longer needed. If the hash in the batch is wrong and you do not know the password behind it, see [After losing the initial user's password](#after-losing-the-initial-users-password).

The failed build is recorded as a rejection, and any earlier candidate of the node is removed. A later build that passes writes the candidate again.

### sudo: a terminal is required to read the password

A command run through `ssh` gets no terminal, so `sudo` cannot ask for the password. Use `ssh -t`. If it still fails, a `RequestTTY no` line in `~/.ssh/config`, or a shell that is not a real terminal, such as an editor's or an assistant's built-in shell, may be the cause. Log in, and run the commands on the node:

```sh
ssh initial@203.0.113.10
sudo sshd -T | grep -E '^(port|permitrootlogin|passwordauthentication) '
exit
```

### You are currently not seeing messages from other users and the system

`journalctl` run as the initial user shows only its own messages, so a check for ordering cycles prints `0` whatever happened. Run it with `sudo`, as [Check the node](#check-the-node) shows.

### The node has not finished booting

```text
raw.example.org has not finished booting within 300 seconds, so the build stops.
```

The task above it shows `systemctl is-system-running`, the jobs systemd is waiting for, and any ordering cycle. If the jobs are cloud-init's and there is a cycle, the node is stuck in `starting`, as [Foomuuri and cloud-init Ordering Cycle](../known-issues/foomuuri-cloud-init-ordering-cycle.md) describes. Disable cloud-init by hand and reboot, then run the build again:

```sh
ssh -t initial@203.0.113.10 'sudo touch /etc/cloud/cloud-init.disabled && sudo systemctl reboot'
```

If SSH does not answer, run `touch /etc/cloud/cloud-init.disabled` and `systemctl reboot` as root at the provider's console. Otherwise, look at the units the task names with `sudo systemctl status <unit>` on the node.

### systemd found an ordering cycle

```text
systemd found an ordering cycle while booting raw.example.org, and skipped a unit to break it. The skipped unit may be the firewall.
```

The node booted, but systemd skipped a unit to break a cycle, and the task above shows which. Check that Foomuuri is active with `systemctl is-active foomuuri` before anything else. Then find the units in the cycle and report it, since the build does not fix cycles other than cloud-init's. See [Foomuuri and cloud-init Ordering Cycle](../known-issues/foomuuri-cloud-init-ordering-cycle.md) for the cycle uc-node knows.

## Changelog

| Version | Date | Change |
| :-- | :-- | :-- |
| 0.3.1 | 2026-11-27 | The remaining `-p 2222` examples removed, since SSH stays on 22, with the note on a manual `ssh` to another port. The fix for a node stuck in `starting`, which was in the removed section on earlier versions, moved to The node has not finished booting |
| 0.3.0 | 2026-11-27 | Preparing an existing node and rebuilding a node made by an earlier version removed, with the other text on moving from uc-node 0.2.0 or uc-raw-node: nothing runs 0.2.0. Batch names in commands are `raw-YYYY-MM-DD-NN`, since `raw-1970-01-01-01` is reserved for documents and tests |
| 0.2.0 | 2026-11-27 | Node definitions in the client inventory's `intake/`, built with `scripts/build`, with the hashes in a build batch: the password check reads the batch without showing the hash, a lost password means a new batch, and an old node definition is moved by guide 0. The confirmation and the candidate added to what the build does and checks, a second build changes three things, and troubleshooting for a hash in the node definition, the client inventory, `uc_secret` and the checker |
| 0.1.3 | 2026-11-24 | Explained that `--ask-become-pass` wants the initial user's password, not the provider's root password, showed how to check it against `initial_password_hash` before the first build, and how to recover from Incorrect sudo password |
| 0.1.2 | 2026-11-24 | updated root password test so VPS console is not required |
| 0.1.1 | 2026-11-24 | Linked the known issues on the ordering cycle, the reboot role and PerSourcePenalties |
| 0.1.0 | 2026-11-24 | First version, provisional: a fresh install and an existing node, the `~/.ssh/config` entry, the host key, adoption, the checks, later builds, rebuilding a node made by an earlier version, lockouts, and troubleshooting by error message |
