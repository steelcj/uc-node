---
title: Add a New Platform to the Node Creation Controller
description: How to teach uc-raw-node to build raw nodes on a new platform, with a VPS as the worked example.
version: 0.1.0
status: provisional
date: 2026-11-23
language: en-CA
---

# Add a New Platform to the Node Creation Controller

The raw node controller builds a node that meets the raw node contract and writes `confirmation.yml`, so the orchestration controller can take it from there. Today it builds on one platform, a local Incus host. This guide explains what a new platform has to provide, and walks through adding a VPS as the example.

## Who this is for

You maintain uc-raw-node and want it to build raw nodes somewhere other than the local Incus host: a VPS, bare metal reached over SSH, or another hypervisor. You know `build.yml`, the node definition in `~/.secrets/uc-raw/`, and the guides [Setup the Defaults For New Nodes](1-setup-the-defaults-for-new-nodes.md) and [Build and Check a Raw Node](2-build-and-check-a-raw-node.md).

## What stays the same

Most of the controller does not care where the node runs. These plays are shared by every platform and should not change:

| Stage | Plays and roles |
| :-- | :-- |
| Bootstrap | `robertdebock.bootstrap` |
| Configure to contract | `robertdebock.hostname`, `robertdebock.users`, `steelcj.foomuuri`, `robertdebock.openssh` |
| Reboot | `robertdebock.reboot` |

The contract is the same on every platform. A platform only changes how the node comes to exist, how the controller reaches it, and which quirks must be removed before the contract can hold.

## What a platform must provide

A platform is a small set of answers. Write them down before writing any YAML.

| Responsibility | Question it answers | Incus today |
| :-- | :-- | :-- |
| Create or adopt | How does the node come to exist? | `incus launch` |
| Ownership | How does the controller know it built this node, and refuse one it did not? | `user.uc-raw-node.owner` config key |
| Connect | How does Ansible reach the node, before and after the contract is applied? | `community.general.incus`, always |
| Wait | How does the controller know the node has booted? | `incus exec ... systemctl is-system-running --wait` |
| Prepare | What does the platform put on the node that would break the contract? | Nothing, the image is clean |
| Recover | How do you get in if the network configuration goes wrong? | `incus exec`, which ignores the network |
| Confirm | Which addresses go in `confirmation.yml`? | The instance's addresses on the Incus network |

Incus answers the connect and recover questions so easily that they are invisible. On most other platforms they are the hard part.

## Prepare the controller for more than one platform

Do this once, before the first new platform.

### Add a platform field to the node definition

A node definition names its platform, and carries what that platform needs:

```yaml
---
# ~/.secrets/uc-raw/vishpala.com.yml
platform: vps
node_address: 203.0.113.10
hostname: vishpala.com
root_password_hash: "$6$..."
initial_username: initial
initial_password_hash: "$6$..."
ssh_public_key: ssh-ed25519 AAAA... you@laptop
ssh_port: 2222
ssh_sources: []
```

A node definition without `platform` is read as `incus`, so existing definitions keep working.

### Name the node without reference to a platform

`incus_instance` is used today as the node's name in the inventory. Replace it with a name calculated from the fully qualified domain name, and calculate each platform's own name from that:

```yaml
---
# group_vars/all/node.yml
platform: incus
ssh_port: 22
ssh_sources: []

node_fqdn: "raw.{{ hostname }}"
node_name: "{{ node_fqdn | replace('.', '-') }}"
```

```yaml
---
# group_vars/all/incus.yml
incus_image: images:debian/13
incus_instance: "{{ node_name }}"
```

This is the same change as the roadmap's hostname and fully qualified domain name item, so do them together.

### Split the create play by platform

Move the first play of `build.yml` into its own file per platform, and import the right one:

```text
build.yml
platforms/
  incus/create.yml
  vps/create.yml
  vps/prepare.yml
```

```yaml
#!/usr/bin/env ansible-playbook
---
- name: Create or adopt the node
  ansible.builtin.import_playbook: "platforms/{{ platform }}/create.yml"

- name: Bootstrap
  hosts: raw_node
  gather_facts: false
  roles:
    - role: robertdebock.bootstrap

# The prepare play, configure play and reboot play follow, as below.
```

`import_playbook` is resolved when the playbook is parsed, so `platform` must be given on the command line with the node definition (`-e @...`), which it already is. A platform with nothing to prepare simply has no `prepare.yml`, and the import for it is guarded with a `when` on the plays inside.

### Teach scripts/new-node about platforms

Add two questions, asked in this order:

1. Platform, `incus` or `vps`, default `incus`.
2. For `vps` only, the node's address, checked with `ipaddress.ip_address`.

When the platform is `vps` and `ssh_sources` is not empty, print a warning that the controller's own public address must be in the list, or the build will lock itself out.

## Worked example: a VPS

### Start with adoption, not a provider API

There are two ways a VPS can come to exist:

| Approach | How it works | When to use it |
| :-- | :-- | :-- |
| Adopt | You order a Debian 13 VPS by hand, with your SSH key installed for root, and give the controller its address | First. It works with any provider and ties the controller to none |
| Provider API | The controller orders the VPS itself through the provider's API, for example with the `hetzner.hcloud` collection | Later, one optional `create` file per provider, after the provider passes the Universal Cake metrics |

The rest of this example uses adoption. A provider API changes only how the node comes to exist. Everything after that is the same.

### Ownership: make adoption a deliberate act

A VPS has no `user.uc-raw-node.owner` key, so the marker moves onto the node, as a file:

```text
/etc/uc-raw-node/owner
```

It holds the single line `uc-raw-node`.

A freshly ordered VPS has no marker yet, so the controller cannot tell it apart from someone else's server at the same address. Make the first run explicit instead:

- The first build is run with `-e uc_raw_node_adopt=true`. If the marker is absent, it writes it. If the marker is present, the flag changes nothing.
- Every other build requires the marker, and stops before changing anything if it is missing, with a message that says so.

A wrong address in a node definition then fails safely, instead of reconfiguring a live server.

Where a provider API supports labels, set a label as well. The file stays the authority, because it works everywhere.

### Connect: two connections, and knowing which to use

A VPS is reached in two different ways over its life:

| State | User | Port | Authentication |
| :-- | :-- | :-- | :-- |
| First contact | `root` | 22 | The key the provider installed |
| Meets the contract | `initial_username` | `ssh_port` | The key, plus the become password for `sudo` |

Root login and password authentication are off once the contract holds, so a second run cannot use the first-contact connection. The create play finds out which state the node is in, by trying the contract connection first:

```yaml
---
# platforms/vps/create.yml (sketch)
- name: Adopt the node
  hosts: localhost
  gather_facts: false

  tasks:
    - name: Try the contract connection
      ansible.builtin.command:
        cmd: >-
          ssh -o BatchMode=yes -o ConnectTimeout=10
          -p {{ ssh_port }} {{ initial_username }}@{{ node_address }} true
      register: contract_login
      changed_when: false
      failed_when: false

    - name: Add the node to the inventory
      ansible.builtin.add_host:
        name: "{{ node_name }}"
        groups: raw_node
        ansible_host: "{{ node_address }}"
        ansible_user: "{{ initial_username if contract_login.rc == 0 else 'root' }}"
        ansible_port: "{{ ssh_port if contract_login.rc == 0 else 22 }}"
      changed_when: false

- name: Check ownership
  hosts: raw_node
  gather_facts: false

  tasks:
    - name: Wait for the node to answer
      ansible.builtin.wait_for_connection:
        timeout: 300

    - name: Wait for the node to finish booting
      ansible.builtin.command:
        cmd: systemctl is-system-running --wait
      register: boot
      changed_when: false
      failed_when: boot.stdout not in ['running', 'degraded']

    - name: Read the ownership marker
      ansible.builtin.slurp:
        src: /etc/uc-raw-node/owner
      register: owner
      failed_when: false

    - name: Refuse a node uc-raw-node does not own
      ansible.builtin.assert:
        that:
          - (owner.content | default('') | b64decode | trim) == 'uc-raw-node'
            or (uc_raw_node_adopt | default(false) | bool)
        fail_msg: "{{ inventory_hostname }} has no uc-raw-node marker. Run with -e uc_raw_node_adopt=true only if this is the VPS you ordered."
        quiet: true

    - name: Write the ownership marker
      ansible.builtin.copy:
        dest: /etc/uc-raw-node/owner
        content: "uc-raw-node\n"
        owner: root
        group: root
        mode: "0644"
      become: true
```

The `copy` task needs `/etc/uc-raw-node/` to exist, so create it with `ansible.builtin.file` first. With the contract connection, `become` needs the initial user's password: give it with `--ask-become-pass`, or from an Ansible Vault file kept in `~/.secrets/uc-raw/`.

### Check the host key on first contact

The first SSH connection to a new VPS trusts whatever host key answers. Before the first build:

```sh
ssh-keyscan -t ed25519 203.0.113.10
```

Compare the fingerprint with the one shown in the provider's web console, then add it to `~/.ssh/known_hosts`. Do not turn off host key checking in `ansible.cfg` to save this step.

### Prepare: remove what cloud-init brings

VPS images usually run cloud-init, which the Incus image does not. Three of the things it does work against the contract:

| What cloud-init does | Why it matters | What to do |
| :-- | :-- | :-- |
| Writes a file in `/etc/ssh/sshd_config.d/`, often setting `PasswordAuthentication yes` | sshd keeps the first value it reads for each setting, and the drop-ins are read before the main file, so this overrides `robertdebock.openssh` | Remove any drop-in that sets an SSH option the contract controls |
| Resets the hostname and `/etc/hosts` at boot | Undoes `robertdebock.hostname` after the reboot | Set `preserve_hostname: true` and `manage_etc_hosts: false` |
| Can rewrite network configuration at boot | Can undo network changes the contract may make later | Leave it for now, and decide in the contract whether cloud-init may stay |

Put this in `platforms/vps/prepare.yml`, a play on `raw_node` that runs after bootstrap and before the configure play:

```yaml
---
# platforms/vps/prepare.yml (sketch)
- name: Prepare the node
  hosts: raw_node
  gather_facts: false
  become: true

  tasks:
    - name: Find SSH drop-ins that set options the contract controls
      ansible.builtin.find:
        paths: /etc/ssh/sshd_config.d
        patterns: "*.conf"
        contains: '(?i)^\s*(PasswordAuthentication|PermitRootLogin|Port)\s'
      register: ssh_dropins

    - name: Remove them
      ansible.builtin.file:
        path: "{{ item.path }}"
        state: absent
      loop: "{{ ssh_dropins.files }}"

    - name: Keep cloud-init away from the hostname
      ansible.builtin.copy:
        dest: /etc/cloud/cloud.cfg.d/99-uc-raw-node.cfg
        content: |
          preserve_hostname: true
          manage_etc_hosts: false
        mode: "0644"
```

If you would rather not have cloud-init at all after the first boot, create `/etc/cloud/cloud-init.disabled` instead. Either way, record the choice as a contract clause that says which provider agents may remain on a raw node, such as cloud-init and `qemu-guest-agent`.

### Avoid locking yourself out

On Incus, a bad firewall or SSH setting is harmless, because `incus exec` does not use the network. On a VPS, the build changes the firewall and SSH over the very connection it is using.

#### Keep the order: firewall, then SSH

`build.yml` already applies `steelcj.foomuuri` before `robertdebock.openssh`. Keep it that way, so the firewall allows `ssh_port` before sshd moves to it.

#### Switch connections after SSH changes

Once `robertdebock.openssh` has restarted sshd, the first-contact connection no longer works. Between the configure play and the reboot play, point the inventory at the contract connection and reset it:

```yaml
- name: Switch to the contract connection
  hosts: raw_node
  gather_facts: false

  tasks:
    - name: Use the initial user on the contract port
      ansible.builtin.set_fact:
        ansible_user: "{{ initial_username }}"
        ansible_port: "{{ ssh_port }}"

    - name: Reconnect
      ansible.builtin.meta: reset_connection
```

The reboot then runs over the contract connection, which also proves that the contract connection works.

#### Mind ssh_sources

If `ssh_sources` is set, the controller's own public address must be in it, or the firewall shuts the controller out before SSH is reconfigured. Check this before the first build. `scripts/new-node` warns about it, as described above.

#### Know your way back in

The provider's web console, with the root password, is the way back in when SSH is unreachable. This is one reason the contract keeps a root password even though root cannot log in over SSH. Test the console login once on every new provider, before you need it.

### Network and confirmation

#### Firewall zones

On Incus the node has one interface. A VPS may have a public interface and a private network, and usually IPv6. Check that the Foomuuri zones match the interfaces the VPS really has, and that rules cover IPv6. A firewall offered by the provider is separate from the node, and outside the contract.

#### DNS

Decide whether the A and AAAA records for `raw.<client domain>` are part of the contract or a step for the orchestration controller. Either answer works. Write it down.

#### confirmation.yml

For a VPS, the `ip` and `ip6` fields hold the node's public addresses, since those are what the orchestration controller will use. Check that the first-boot unit that writes `confirmation.yml` exists in the repository and runs on the VPS image, since the reboot relies on it.

## Check the new platform

Run the checks from [Build and Check a Raw Node](2-build-and-check-a-raw-node.md) over SSH instead of `incus exec`:

```sh
ssh -p 2222 initial@203.0.113.10 'cat /etc/uc-raw-node/owner'
ssh -p 2222 initial@203.0.113.10 'python3 --version; sudo --version | head -n 1'
ssh -p 2222 initial@203.0.113.10 'sudo sshd -T | grep -E "^(port|permitrootlogin|passwordauthentication) "'
ssh -p 2222 initial@203.0.113.10 'systemctl is-enabled foomuuri'
ssh -p 2222 initial@203.0.113.10 'hostname; hostname -f'
```

Expected: `uc-raw-node`, the versions of Python and sudo, `port 2222`, `permitrootlogin no` and `passwordauthentication no`, `enabled`, and the hostname and fully qualified domain name from the node definition, still in place after the reboot.

Then the checks that matter most for a remote platform:

| Check | How | Expected |
| :-- | :-- | :-- |
| Root cannot log in | `ssh -p 2222 root@203.0.113.10` | Refused |
| Passwords are refused | `ssh -o PubkeyAuthentication=no -p 2222 initial@203.0.113.10` | Refused |
| The old port is closed | `ssh -p 22 initial@203.0.113.10` | Times out or is refused |
| A second run is quiet | Run `build.yml` again, without `uc_raw_node_adopt` | `changed=1` for the node, the reboot, and nothing else |
| A server without the marker is refused | Point a node definition at a VPS without the marker, and build without `uc_raw_node_adopt` | Stops before any change, with the ownership message |
| The console works | Log in as root through the provider's web console | Works |

## Checklist for any new platform

- [ ] The platform answers every question in [What a platform must provide](#what-a-platform-must-provide)
- [ ] `platforms/<platform>/create.yml` creates or adopts the node, and adds it to the `raw_node` group
- [ ] Ownership is checked before any change, and a node the controller did not build is refused
- [ ] A second run finds the right connection without being told
- [ ] Anything the platform puts on the node that breaks the contract is removed in `platforms/<platform>/prepare.yml`
- [ ] There is a way back in that does not depend on the node's network configuration, and it has been tested
- [ ] `confirmation.yml` carries the addresses the orchestration controller will use
- [ ] `scripts/new-node` asks for what the platform needs, and checks it
- [ ] The checks in this guide pass, and a guide for the platform is added to `en/guides/`

## Changelog

| Version | Date | Change |
| :-- | :-- | :-- |
| 0.1.0 | 2026-11-23 | First draft, provisional: the platform model, and a VPS adopted over SSH as the worked example |
