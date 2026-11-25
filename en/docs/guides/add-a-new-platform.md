---
title: Add a New Platform to the Raw Node Controller
description: How to teach uc-node to build raw nodes on a new platform, with the ssh platform as the worked example.
version: 0.2.1
status: provisional
date: 2026-11-24
language: en-CA
---

# Add a New Platform to the Raw Node Controller

uc-node builds a node that meets the raw node contract. It builds on two platforms: `incus`, a container on the local Incus host, and `ssh`, any Debian 13 host reached as root over SSH. This guide explains what a platform has to provide and how one is wired in, using the ssh platform as the worked example.

## Who this is for

You maintain uc-node and want it to build raw nodes somewhere else: another hypervisor, a provider's API, or bare metal. You know `build.yml`, node definitions in `~/.secrets/uc-raw/`, and the guides [Build and Check a Raw Node](2-build-and-check-a-raw-node.md) and [Build a Node on an SSH Host](3-build-a-node-on-an-ssh-host.md).

## What stays the same

Most of the controller does not care where the node runs. These plays are shared by every platform:

| Stage | Plays and roles |
| :-- | :-- |
| Check the node definition | The first play in `build.yml`, on localhost |
| Wait for the node to boot | `tasks/wait-for-boot.yml`, with `boot_timeout` |
| Bootstrap | `robertdebock.bootstrap` |
| Configure to contract | `robertdebock.hostname`, `robertdebock.users`, `steelcj.foomuuri`, `robertdebock.openssh`, and the `/etc/hosts` line for `hostname -f` |
| Reboot | `ansible.builtin.reboot`, which fails if the boot ID did not change, then the boot wait again and the ordering cycle check |

The contract is the same on every platform. A platform only changes how the node comes to exist, how the controller reaches it, and what must be removed before the contract can hold.

## What a platform must provide

A platform is a small set of answers. Write them down before writing any YAML.

| Responsibility | Question it answers | incus | ssh |
| :-- | :-- | :-- | :-- |
| Create or adopt | How does the node come to exist? | `incus launch` | Ordered by hand, then adopted with `-e uc_raw_node_adopt=true` |
| Ownership | How does the controller know it built this node, and refuse one it did not? | The `user.uc-raw-node.owner` configuration key | The file `/etc/uc-raw-node/owner` |
| Connect | How does Ansible reach the node, before and after the contract holds? | `community.general.incus`, always | Root on port 22 at first contact, then the initial user on `ssh_port` with `sudo` |
| Wait | How does the controller know the node has booted? | The shared boot wait | The shared boot wait |
| Prepare | What does the platform put on the node that would break the contract? | Nothing, the image is clean | sshd drop-ins, cloud-init, root's keys |
| Recover | How do you get in if the network configuration goes wrong? | `incus exec`, which ignores the network | The provider's web console, with root's password |
| Confirm | Which addresses does the orchestration controller use? | The instance's addresses on the Incus network | `node_address` |

Incus answers the connect and recover questions so easily that they are invisible. On most other platforms they are the hard part.

## How a platform is wired in

### The data

`inventory/group_vars/all/platforms.yml` lists every platform, and the node definition fields each one requires on top of `node_required_fields`:

```yaml
platforms:
  incus:
    required_fields: []
  ssh:
    required_fields:
      - node_address
```

The check play refuses a `platform` that is not a key of `platforms`, and a node definition without the platform's required fields. `scripts/new-node` offers the keys as the platform question, then asks for each required field. A new field needs a question in `PLATFORM_QUESTIONS` in `scripts/new-node`, with a check.

The platform's own settings go in a file of their own in `inventory/group_vars/all/`, named after it, such as `ssh.yml`. The group_vars live next to the inventory rather than next to `build.yml`, because Ansible loads group_vars next to a playbook from the directory of the playbook whose plays are running, and the platform plays are imported from `platforms/`.

### The plays

Each platform has a directory under `platforms/`:

```text
platforms/
  incus/create.yml
  ssh/create.yml
  ssh/prepare.yml
  ssh/switch.yml
```

`build.yml` imports every platform's plays, whatever the node's platform, each at its stage:

| Stage in build.yml | incus | ssh |
| :-- | :-- | :-- |
| After the check play | `platforms/incus/create.yml` | `platforms/ssh/create.yml` |
| After bootstrap | | `platforms/ssh/prepare.yml` |
| After the configure play | | `platforms/ssh/switch.yml` |

A play cannot carry `when`, so a platform's plays run only for its own nodes in one of two ways:

- A play on localhost keeps all its tasks in one block with `when: platform == '<name>'`. The condition is evaluated after group_vars are loaded, so the `platform` default in `node.yml` applies.
- A play on the node targets the platform's own group, such as `platform_ssh`. Only that platform's create play adds the node to it, so the group is empty for every other platform.

Do not use a templated path such as `platforms/{{ platform }}/create.yml`: `import_playbook` resolves it when the playbook is parsed, before group_vars are loaded, so the `platform` default would not apply.

### The create play's contract

Whatever else it does, a create play must:

- refuse a node the controller does not own, before any change
- add the node to Ansible's inventory under `node_fqdn`, in the `raw_node` group and the platform's own group
- set the connection variables there, with `add_host`, never in `inventory/group_vars/all/`, which also applies to localhost. The check play refuses a node definition that sets one of `node_connection_variables` in `platforms.yml`, since `-e` would override `add_host`. Add any new connection variable the create play sets to that list

## Worked example: the ssh platform

### Adopt, rather than order through an API

There are two ways a host can come to exist:

| Approach | How it works | When to use it |
| :-- | :-- | :-- |
| Adopt | You order a Debian 13 host by hand, with your SSH key installed for root, and give the controller its address | First. It works with any provider and ties the controller to none |
| Provider API | The controller orders the host itself, for example with the `hetzner.hcloud` collection | Later, as a platform of its own, after the provider passes the Universal Cake metrics |

The ssh platform adopts. A provider API would change only how the node comes to exist. Everything after that would be the same.

### Ownership as a deliberate act

A host reached over SSH has no instance configuration key, so the marker is a file on the node, `/etc/uc-raw-node/owner`, holding the single line `uc-raw-node`. The settings are in `inventory/group_vars/all/ownership.yml`.

A freshly ordered host has no marker, so the controller cannot tell it apart from someone else's server at the same address. The first build is made explicit:

- The first build is run with `-e uc_raw_node_adopt=true`. If the marker is absent, it is written. If the marker is present, the flag changes nothing.
- Every other build requires the marker, and stops before any change without it, with a message that says to adopt only the host that was ordered.
- A marker holding anything else is always refused.

A wrong address in a node definition then fails safely, instead of reconfiguring a live server. The marker is read with `raw` before the shared boot wait, since reading it changes nothing.

### Two connections, and knowing which to use

A host is reached in two ways over its life:

| State | User | Port | Authentication |
| :-- | :-- | :-- | :-- |
| First contact | `root` | 22 | The key the provider installed |
| Meets the contract | `initial_username` | `ssh_port` | The key, plus the initial user's password for `sudo` |

Root login is off once the contract holds, so a second build cannot use the first-contact connection. `platforms/ssh/create.yml` finds out which state the node is in by trying the contract connection first, once, with `ssh` itself:

```yaml
- name: Try the contract connection
  ansible.builtin.command:
    argv: "{{ ssh_probe_command + ['-p', ssh_port | string, '-l', initial_username, node_address, 'true'] }}"
  register: contract_probe
  changed_when: false
  failed_when: false
```

If it fails, it tries root on port 22, once. If both fail, it stops, quoting both errors.

#### Never retry a failed login

OpenSSH 10's PerSourcePenalties blocks an address that keeps failing to log in. A reconnect loop as root, with the agent offering every key, locked the controller out of a host in an early test. So: See [OpenSSH PerSourcePenalties Lockouts](../known-issues/openssh-per-source-penalties-lockout.md).

- each login is tried once, and a failed one is never retried
- the probes are plain `ssh` commands, not `wait_for_connection`, which retries until it times out, and needs Python, which bootstrap installs later
- every connection uses `IdentitiesOnly=yes`, so ssh offers only the default key files and the keys `~/.ssh/config` names for the address, never every key in the agent

With `IdentitiesOnly=yes`, a key kept outside the default files needs an entry in `~/.ssh/config`. Its `Host` line must be the address, since Ansible connects to `node_address`. `scripts/new-node` prints the entry, and the create play prints it when both logins are refused with `Permission denied`.

#### Check the host key, always

Every connection uses `StrictHostKeyChecking=yes`, first contact included, and the create play stops if Ansible's own host key checking is turned off. An unknown or changed host key stops the build before any login, with a message saying to check the key against the provider's console and add it to known_hosts.

The connections also use `HostKeyAlias=<node_address>`, so the key is looked up under the bare address whatever the port, and one known_hosts line covers first contact and the contract port. These options are `ssh_client_options` in `inventory/group_vars/all/ssh.yml`.

#### Become

On the contract connection the create play sets `ansible_become: true`. As root it leaves become off, since `sudo` may not be installed yet. Every ssh build is run with `--ask-become-pass`, the first included, because the build switches to the contract connection before the reboot.

### Prepare: remove what the provider brings

`platforms/ssh/prepare.yml` runs after bootstrap and before the configure play.

| What the provider's image does | Why it matters | What the build does |
| :-- | :-- | :-- |
| Writes a file in `/etc/ssh/sshd_config.d/`, often with `PasswordAuthentication yes` | sshd keeps the first value it reads for each setting, and drop-ins are read first | Removes every drop-in that sets an option in `ssh_contract_options`. `robertdebock.openssh` writes an `sshd_config` without an `Include` line, so drop-ins stop being read anyway, but a later `Include` cannot bring them back |
| Runs cloud-init, which resets the hostname and `/etc/hosts` at boot | Undoes `robertdebock.hostname` after the reboot | Writes `/etc/cloud/cloud.cfg.d/99-uc-raw-node.cfg` with `preserve_hostname: true` and `manage_etc_hosts: false` |
| Runs cloud-init 25, which forms a systemd ordering cycle with Foomuuri | systemd skips a unit to break the cycle: cloud-init's network stage, which leaves the node in `starting` forever, or possibly the firewall | Creates `/etc/cloud/cloud-init.disabled`, so cloud-init does not run after the first boot |
| Installs your key for root | Root cannot log in under the contract, but a key left there would work if that changed | Empties root's `authorized_keys`, in `switch.yml`, once the contract connection has worked |

Root's keys are emptied after the switch rather than in the prepare play. Until the contract connection has worked, root's key is the only way back in over SSH, and a configure play that failed after the keys were gone would leave only the console.

The ordering cycle runs from `cloud-init-network.service` through `systemd-networkd-wait-online.service`, `systemd-networkd.service`, `network-pre.target`, `foomuuri.service` and `foomuuri-boot.service` to `sysinit.target`, which `cloud-init-network.service` is ordered before. The ROADMAP has the item to raise it upstream. See [Foomuuri and cloud-init Ordering Cycle](../known-issues/foomuuri-cloud-init-ordering-cycle.md).

### Avoid locking yourself out

On Incus, a bad firewall or SSH setting is harmless, because `incus exec` does not use the network. On an SSH host, the build changes the firewall and SSH over the very connection it is using.

#### Keep the order: firewall, then SSH

`build.yml` applies `steelcj.foomuuri` before `robertdebock.openssh`. With a new port, the firewall would drop new connections to the old port before sshd moves. So the create play refuses a first contact whose `ssh_port` is not the first-contact port. Changing the port later is not supported yet, and is in the ROADMAP.

#### Switch connections after SSH changes

Once `robertdebock.openssh` has set `PermitRootLogin no`, root cannot log back in after the reboot. `platforms/ssh/switch.yml` runs between the configure play and the reboot:

```yaml
- name: Use the initial user on the contract port, with become
  ansible.builtin.set_fact:
    ansible_user: "{{ initial_username }}"
    ansible_port: "{{ ssh_port }}"
    ansible_become: true

- name: Reconnect
  ansible.builtin.meta: reset_connection
```

The reboot then runs over the contract connection, which also proves that the contract connection works.

#### Mind ssh_sources

If `ssh_sources` is set, the controller's own public address must be in it, or the firewall shuts the controller out. `scripts/new-node` asks you to confirm it for an ssh node.

#### Know your way back in

The provider's web console, with root's password, is the way back in when SSH is unreachable. This is one reason the contract keeps a root password although root cannot log in over SSH. Test the console login once on every new provider, before you need it.

### Reboot, and check the boot

`robertdebock.reboot` reported changed without rebooting, because its job was killed before the shutdown ran. The build uses `ansible.builtin.reboot`, which fails if the boot ID did not change within `reboot_timeout`. After the reboot, every platform: See [robertdebock.reboot Reports Changed Without Rebooting](../known-issues/robertdebock-reboot-reports-changed-without-rebooting.md).

- waits for the node to report `running` or `degraded`, for at most `boot_timeout` seconds, and otherwise stops with the jobs it is waiting for and any ordering cycle
- reads systemd's ordering cycle lines from `journalctl -b`, filtered on `SYSLOG_IDENTIFIER=systemd`, and on Incus from `incus console --show-log`, since a container's early boot messages never reach its journal
- fails if there are any

A provider's cloud-init can reset the hostname at the reboot, so check `hostname -f` after it, as the ssh guide does.

### Network and confirmation

#### Firewall zones

An Incus container has one interface. A VPS may have a public interface, a private network, and IPv6. Check that the Foomuuri zones match the interfaces the host really has, and that rules cover IPv6. A firewall offered by the provider is separate from the node, and outside the contract.

#### DNS

Decide whether the A and AAAA records for the node's fully qualified domain name are part of the contract or a step for the orchestration controller. Either answer works. Write it down.

#### confirmation.yml

The orchestration controller needs the node's addresses. For the ssh platform, that is `node_address`, and any IPv6 address the host has. uc-node does not write `confirmation.yml` yet.

## Check the new platform

Run the checks from the platform's guide, then these, which matter most for a remote platform:

| Check | How | Expected |
| :-- | :-- | :-- |
| A second build is quiet | Build again, without `uc_raw_node_adopt` | `changed=1` for the node, the reboot, and nothing else |
| A node without the marker is refused | Build a host without the marker, without `uc_raw_node_adopt` | Stops before any change, with the ownership message |
| An unknown host key is refused | Build with the host key missing from known_hosts | Stops before any login, with the host key message |
| Root cannot log in | `ssh root@<address>` | Refused |
| Passwords are refused | `ssh -o PubkeyAuthentication=no initial@<address>` | Refused |
| The boot is clean | `sudo journalctl -b SYSLOG_IDENTIFIER=systemd \| grep -ci "ordering cycle"` | `0` |
| The way back in works | The provider's console, as root | Works |

## Checklist for any new platform

- [ ] The platform answers every question in [What a platform must provide](#what-a-platform-must-provide)
- [ ] It is a key in `inventory/group_vars/all/platforms.yml`, with its required fields, and `scripts/new-node` can ask for each of them
- [ ] Its settings are in `inventory/group_vars/all/<platform>.yml`, each with a comment saying what it is for
- [ ] `platforms/<platform>/create.yml` creates or adopts the node, refuses one it does not own before any change, and adds it to `raw_node` and `platform_<platform>` with `add_host`
- [ ] Its plays on localhost run their tasks under `when: platform == '<platform>'`, and its plays on the node target `platform_<platform>`
- [ ] `build.yml` imports them at their stage, with fixed paths
- [ ] A second build finds the right connection without being told
- [ ] A failed login is never retried in a loop, and host key checking stays on
- [ ] Anything the platform puts on the node that breaks the contract is removed
- [ ] There is a way back in that does not depend on the node's network configuration, and it has been tested
- [ ] The checks in this guide pass, and a guide for the platform is in `en/docs/guides/`

## Changelog

| Version | Date | Change |
| :-- | :-- | :-- |
| 0.2.1 | 2026-11-24 | Linked the known issues, and added `node_connection_variables` to the create play's contract |
| 0.2.0 | 2026-11-24 | Brought in line with what was built, still provisional: `ssh` instead of `vps`, `platforms.yml`, the `when` blocks and platform groups, group_vars under the inventory, `ansible.builtin.reboot` and the boot checks, `IdentitiesOnly`, the host key, root's keys, PerSourcePenalties, and the cloud-init ordering cycle |
| 0.1.0 | 2026-11-23 | First draft, provisional: the platform model, and a VPS adopted over SSH as the worked example |
