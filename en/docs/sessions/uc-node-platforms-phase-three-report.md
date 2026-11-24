---
title: Platforms for uc-node, Phase Three Report
description: What phase three of the platforms work changed, the checks it passed, what it found about cloud-init and Foomuuri, and what to know before phase four.
version: 0.1.0
status: provisional
date: 2026-11-23
language: en-CA
---

# Platforms for uc-node, Phase Three Report

Phase three is done and committed on the `platforms` branch as `fbb2efa`. uc-node now builds on the `ssh` platform as well as `incus`, and the Incus build behaves exactly as it did at the end of phase two. Nothing was pushed and `VERSION` is unchanged.

The ssh platform was tested end to end against throwaway Incus instances on this machine, reached over SSH on the local Incus bridge: a Debian 13 cloud container and a Debian 13 cloud VM. No remote host was contacted. The test against a real VPS is still yours to run.

## Before phase three

| Change | Commit |
| :-- | :-- |
| `en/docs/sessions/README.md` committed as it was found | `f651ee9` |
| `group_vars/` moved to `inventory/group_vars/`, the `platforms/incus/group_vars` link and its explanation removed, and the paths in `build.yml`, `scripts/new-node`, the comments and the README's layout table updated. `.yamllint` named no `group_vars` path, so it needed no change | `8fea7a7` |
| The check play's first task asserts that `platforms` is defined, and says to run from the repository directory with its inventory. Run from `/tmp`, the build stops with that message | `8fea7a7` |

Group_vars next to the inventory are loaded for every playbook, including the imported platform playbooks, and for hosts added with `add_host`. Two Incus builds after the move gave the same counts as at the end of phase two.

The first attempt at these two commits put the renames into the README commit, because `git mv` had already staged them. Neither was pushed, so they were redone as described above.

## What changed

| File | Change |
| :-- | :-- |
| `inventory/group_vars/all/ssh.yml` | New: the first-contact user and port, `uc_raw_node_adopt`, `ssh_client_options`, `ssh_probe_timeout`, `ssh_contract_options`, `ssh_cloud_init_settings` and `ssh_cloud_init_disabled_file` |
| `inventory/group_vars/all/boot.yml` | New: `boot_timeout` and `boot_cycle_pattern`, for every platform |
| `inventory/group_vars/all/openssh.yml` | `openssh_authorized_keys_command: /usr/bin/true` |
| `platforms/ssh/create.yml` | New: the probes, the host key and port checks, `add_host`, and the ownership check |
| `platforms/ssh/prepare.yml` | New: removes sshd drop-ins, writes the cloud-init settings and disables cloud-init after the first boot |
| `platforms/ssh/switch.yml` | New: moves to the contract connection, then empties root's `authorized_keys` |
| `tasks/wait-for-boot.yml` | New: the boot wait with a timeout, shared by every platform |
| `platforms/incus/create.yml` | Its boot wait moved to the shared play |
| `build.yml` | Imports the ssh plays, a shared boot wait after the create plays, and a boot wait and ordering-cycle check after the reboot |
| `scripts/new-node` | Asks for confirmation when an ssh node limits `ssh_sources`, and accepts `any` to clear the list |
| `ROADMAP.md` | Four items from this phase, listed under the ordering cycle below. The rest of the ROADMAP is rewritten in phase four |

### The play order

| Play | Hosts | Runs on |
| :-- | :-- | :-- |
| Check the node definition | localhost | every platform |
| Create the node on Incus | localhost, tasks under `when: platform == 'incus'` | incus |
| Connect to the node over SSH | localhost, tasks under `when: platform == 'ssh'` | ssh |
| Check that uc-raw-node owns the node | `platform_ssh` | ssh |
| Wait for the node to finish booting | `raw_node` | every platform |
| Bootstrap | `raw_node` | every platform |
| Prepare the node for the contract | `platform_ssh` | ssh |
| Configure the node to contract | `raw_node` | every platform |
| Switch to the contract connection | `platform_ssh` | ssh |
| Reboot, wait, and check for ordering cycles | `raw_node` | every platform |

### Connecting

Every connection to an ssh node, the probes and Ansible's own, uses the options in `ssh_client_options`: `IdentitiesOnly=yes`, `StrictHostKeyChecking=yes` and `HostKeyAlias=<node_address>`. With the alias, the host key is looked up under the address whatever the port, so one known_hosts line covers first contact on 22 and a contract port such as 2222. Only identities named in `ssh_config`, or the default identity files, are offered, never every key in the agent.

The play on localhost:

- asserts that Ansible's SSH host key checking is on, since `ANSIBLE_HOST_KEY_CHECKING=False` would add `StrictHostKeyChecking=no` ahead of the options above
- tries the contract connection once: the initial user on `ssh_port`, with `BatchMode=yes`, `ConnectTimeout=10` and `ConnectionAttempts=1`
- stops if the host key is unknown or has changed, with a message saying to check the key against the provider's console and add it to known_hosts under the address
- if the contract connection did not work, tries root on port 22 once, with the same host key check
- stops if neither works, quoting both errors, without retrying
- refuses a first contact whose `ssh_port` is not 22, explained under the port change below
- adds the node under `node_fqdn` to `raw_node` and `platform_ssh`, with `ansible_host`, `ansible_user`, `ansible_port`, `ansible_ssh_common_args`, `ansible_ssh_host_key_checking: true`, and `ansible_become` true only on the contract connection, since root needs no become and `sudo` may not be installed yet

The ssh host key check stops the build before any login is attempted: the test node's sshd logged no login at all for those runs.

### Ownership

The play on `platform_ssh` reads `/etc/uc-raw-node/owner` with `raw`. It refuses a file that holds anything other than `uc-raw-node`. It refuses a missing file unless `uc_raw_node_adopt` is true, with a message that says to adopt only the host that was ordered. When adopting, it writes the file. Nothing is changed on a refused node.

### Preparing

`prepare.yml` finds files in `/etc/ssh/sshd_config.d/` with a line setting `PasswordAuthentication`, `PermitRootLogin` or `Port`, and removes them. On the test nodes it removed a planted `PasswordAuthentication yes` drop-in and kept an unrelated one.

`robertdebock.openssh` writes a whole `sshd_config` without an `Include` line, so drop-ins stop being read once it has run. They are removed all the same, so a later `Include` cannot bring them back.

When `/usr/bin/cloud-init` exists, it writes `/etc/cloud/cloud.cfg.d/99-uc-raw-node.cfg` from `ssh_cloud_init_settings`, and creates `/etc/cloud/cloud-init.disabled`, as described under the ordering cycle.

### Switching to the contract connection

`switch.yml` sets `ansible_user` to the initial user, `ansible_port` to `ssh_port` and `ansible_become` to true, then runs `meta: reset_connection`. The reboot runs over the contract connection, so every build of an ssh node needs `--ask-become-pass`, the first build included. Ansible cannot see from inside the playbook whether a become password was given, so the build cannot check it in advance. The ssh guide in phase four will say so.

### The boot wait on every platform

`tasks/wait-for-boot.yml` runs `timeout 300 systemctl is-system-running --wait` with `raw`. If the node is not `running` or `degraded` by then, it shows the output of `systemctl list-jobs` and any ordering cycle lines from `journalctl -b`, and stops. It runs once the node is in the inventory, and again after the reboot. It replaces the Incus play's own wait, which had no timeout.

After the reboot, the build reads systemd's ordering cycle lines from `journalctl -b` and, on Incus, from `incus console --show-log`. It fails if there are any.

- The journal is filtered on `SYSLOG_IDENTIFIER=systemd`. Ansible logs each task's arguments to the journal, so an unfiltered search finds the search itself. systemd's early messages reach the journal from the kernel log without `_PID=1`, so that filter missed them on the VM.
- In an Incus container there is no `/dev/kmsg`, so systemd's early messages, ordering cycles among them, go only to the console and never reach the journal. The console log is read from the controller, and holds the boot that just happened, after an in-guest reboot too. Reading it empties it.

### AuthorizedKeysCommand

The line comes from `robertdebock.openssh`'s default `openssh_authorized_keys_command: none`, which every template writes as `AuthorizedKeysCommand none`. sshd 10 does not read `none` as unset for this option. It was reproduced on an Incus node: a login with a key not in `authorized_keys` logged `error: AuthorizedKeysCommand path is not absolute`. With `/usr/bin/true`, an absolute path that prints no keys, the same login logs only `Connection closed by authenticating user`, and `sshd -T` shows `authorizedkeyscommand /usr/bin/true`.

### scripts/new-node

When the platform is `ssh` and `ssh_sources` is not empty, it says the list must include the controller's own public address, and asks for confirmation. A no asks for the list again, where `any` clears it. `ask_sources` could not clear a non-empty default before, since blank keeps the default.

## The cloud-init and Foomuuri ordering cycle

On Debian 13, cloud-init 25 and Foomuuri form a systemd ordering cycle. systemd logged this chain on the cloud image with Foomuuri installed:

```text
sysinit.target: Found ordering cycle on cloud-init-network.service/start
sysinit.target: Found dependency on systemd-networkd-wait-online.service/start
sysinit.target: Found dependency on systemd-networkd.service/start
sysinit.target: Found dependency on network-pre.target/start
sysinit.target: Found dependency on foomuuri.service/start
sysinit.target: Found dependency on foomuuri-boot.service/start
sysinit.target: Found dependency on sysinit.target/start
sysinit.target: Job cloud-init-network.service/start deleted to break ordering cycle starting with sysinit.target/start
```

`cloud-init-network.service` is ordered before `sysinit.target` and after the network wait. `foomuuri.service` and `foomuuri-boot.service` keep systemd's default dependencies, so they are ordered after `sysinit.target`, and `foomuuri.service` is ordered before `network-pre.target`.

systemd deletes a job to break the cycle. On the cloud image it deleted `cloud-init-network.service`, so cloud-init's single process waited for its network stage forever, `cloud-config.service` never finished, and the node stayed in `starting`. On the VM, systemd reported the same cycle as starting from `dbus.socket`, and again deleted `cloud-init-network.service`. Network and SSH still came up, from the configuration cloud-init wrote at first boot. systemd may choose either side of a cycle, so another boot could instead drop a Foomuuri unit and leave the node without its firewall.

How it was found and narrowed down:

- the second ssh build hung in the boot wait, which then had no timeout
- an untouched cloud container rebooted cleanly, with openssh-server added too, and after a reboot from inside the guest
- the built node hung again after `incus restart`, so the cause was persistent
- the untouched cloud container with only Foomuuri installed hung the same way, and its console log held the lines above
- a Debian 13 cloud VM with Foomuuri hung the same way, and its journal held the cycle

The build:

- creates `/etc/cloud/cloud-init.disabled` when cloud-init is installed, the option you chose, so cloud-init does not run after the first boot and the cycle never forms. On the VM, the node was `running` after the reboot, with no cycle in the journal. Network changes the provider makes later are not picked up, and the ssh guide in phase four will say so
- still writes `99-uc-raw-node.cfg`, in case cloud-init is turned back on
- fails after `boot_timeout` with the waiting jobs and the cycle, instead of hanging, if a node does not finish booting
- fails after the reboot if `journalctl -b`, or on Incus the console log, holds an ordering cycle

The ROADMAP now has these items:

- raise the cycle with Foomuuri upstream and in steelcj.foomuuri, with the chain above
- check whether Ubuntu Server installs from uc-ventoy, which keep cloud-init, hit the same cycle
- change the SSH port after first contact, below
- raise `AuthorizedKeysCommand none` with robertdebock.openssh

## The port change

steelcj.foomuuri allows one SSH port, `foomuuri_ssh_port`, rendered as the `ssh` macro for 22 and `tcp <port>` otherwise. It can still open a second port through `foomuuri_services`, which accepts a port number with `sources`. robertdebock.openssh writes a single `Port` line.

A port change is unsafe in two ways:

- **First contact:** Foomuuri is applied before OpenSSH, so with a new port the firewall drops new connections to 22 while sshd still listens there.
- **Later builds:** the contract probe tries the new port while sshd still listens on the old one, and root can no longer log in, so the build cannot connect.

What the build does now: `create.yml` refuses a first contact whose `ssh_port` is not the first-contact port, before any change, with a message saying to build first with port 22. On the test node this refusal came after one successful root probe and nothing else.

The smallest safe approach found, without changing the role:

- for the build that moves the port, add the port in use as an extra `foomuuri_services` entry, with `ssh_sources`, so the firewall accepts both ports until sshd has moved
- the existing connection survives the sshd restart, and the switch play reconnects on the new port
- the next build leaves the extra entry out, which closes the old port
- for later builds, the create play also needs to probe the old port when the new one does not answer

This is in the ROADMAP rather than built.

## Departures from the instructions

| Instruction | What was done | Why |
| :-- | :-- | :-- |
| `wait_for_connection` before the boot wait | One `ssh` probe per connection, then `raw` tasks | `wait_for_connection` retries until it times out, which as root after a failed login is the loop that triggers PerSourcePenalties, and it needs Python, which bootstrap installs later |
| Boot wait before the ownership check | Ownership first, then the shared boot wait | The boot wait is now shared by every platform. Reading the marker changes nothing, so a refused node is still left untouched |
| Empty root's `authorized_keys` in `prepare.yml` | In `switch.yml`, after the contract connection has worked | Until then root's key is the only way back in over SSH. If the configure play failed after `prepare.yml` had emptied it, the next build could not connect, and the provider's console would be the only way back |

## Checks

| Check | Result |
| :-- | :-- |
| `yamllint .` | Clean |
| `--syntax-check` with an Incus and an ssh node definition in `/tmp` | Both pass |
| `ansible-lint` | Passes, production profile |
| Incus, two builds from a fresh instance | `changed=15` then `changed=1` (only the reboot), `running`, `hostname -f` is `raw.example.org`, one `127.0.1.1` line, no ordering cycle |
| ssh, unknown host key | Stops before any login with the host key message |
| ssh, host key checking off | Stops with a message, before any login |
| ssh, no marker, no adopt | Stops with the adoption message, nothing changed |
| ssh, adopt with `ssh_port: 2222` | Stops with the port change message, nothing changed |
| ssh on the VM, first build with adopt | Succeeded, `changed=18`, rebooted over the contract connection |
| ssh on the VM, after the first build | `running`, `stage` and `stage.example.org` after the reboot, marker written, drop-in removed, cloud-init disabled, root's `authorized_keys` empty, `permitrootlogin no`, `passwordauthentication no`, Foomuuri active, no ordering cycle |
| ssh on the VM, second build without adopt | Contract connection, first contact skipped, `changed=1` (only the reboot), no root login and no failed login in the node's log |
| ssh on the VM, root login and password-only login | Both refused |
| ssh on the VM with cloud-init left on, `boot_timeout=60` | Fails after the reboot with the waiting cloud-init jobs and the cycle lines, instead of hanging |
| ssh on a node that was already stuck, `boot_timeout=20` | The first boot wait fails the same way, before bootstrap |
| `scripts/new-node` | Warns and asks only for ssh with `ssh_sources`, a no asks again, `any` clears the list |

The ssh tests ran with test-only overrides passed with `-e`: `ssh_client_options` with a scratch known_hosts file and the throwaway key, so `~/.ssh` was never touched, and the throwaway initial password as `ansible_become_password`.

Each known_hosts entry was taken from the test node's own host key through `incus exec`, standing in for the provider's console. On first contact the node logged one failed login per build, the contract probe for an initial user that did not exist yet, followed by root's key login.

All test instances, `/tmp/uc-node-check/`, and the test keys, known_hosts and home directory in the scratchpad directory are deleted.

## Things to know

### Every ssh build needs --ask-become-pass

The first build switches to the initial user before the reboot, so it needs the become password too, not only later builds.

### The key must be one ssh offers with IdentitiesOnly

With `IdentitiesOnly=yes`, ssh offers only the identity files named in `ssh_config` for the address, or the default ones such as `~/.ssh/id_ed25519`. A key held only in the agent is not offered.

### known_hosts is read under the address

Because of `HostKeyAlias`, uc-node looks the host key up under `node_address`, for example the line `ssh-keyscan -t ed25519 203.0.113.10` prints. A manual `ssh -p 2222` to the node looks it up under `[203.0.113.10]:2222` instead, unless given the same alias.

### node_address is not checked as an address

The check play confirms only that `node_address` is present. A wrong value fails at the first probe, which stops the build before any change.

### Connection variables in a node definition

A node definition could set connection variables such as `ansible_user` or `ansible_ssh_common_args`, and `-e` would override what the create play sets. The check play does not refuse them yet.

### For phase four

The ssh guide should cover:

- `--ask-become-pass`, needed on every ssh build
- the host key under the address
- adopting only the host that was ordered
- the port change limit
- that cloud-init is disabled after the first boot, why, and that network changes the provider makes later are not picked up

## Changelog

| Version | Date | Change |
| :-- | :-- | :-- |
| 0.1.0 | 2026-11-23 | First version, from the end of phase three |
