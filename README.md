# uc-node, the raw node controller

uc-node builds a node that meets the raw node contract, with Ansible, on one of two platforms:

| Platform | What it builds on | How the controller reaches the node |
| :-- | :-- | :-- |
| `incus` | A container on the local Incus host, which uc-node launches | `incus exec`, through the `community.general.incus` connection |
| `ssh` | Any Debian 13 host reached as root over SSH, such as a VPS, which uc-node adopts | SSH: root on port 22 for the first build, then the initial user on `ssh_port` with `sudo` |

On every platform, a build:

- checks the node definition before anything is created or changed
- creates the Incus instance, or reaches the ssh host and checks that uc-node owns it, with an ownership marker
- waits for the node to finish booting, for at most `boot_timeout` seconds
- bootstraps it with `robertdebock.bootstrap`, so Ansible modules can run
- on the ssh platform, removes what the provider's image puts on the node that would break the contract
- configures the node to contract: the hostname and fully qualified domain name, root's password and the initial user, the Foomuuri firewall and key-only SSH
- reboots it with `ansible.builtin.reboot`, which fails if the boot ID did not change, then checks that the node finished booting without a systemd ordering cycle. See the known issues [robertdebock.reboot Reports Changed Without Rebooting](en/docs/known-issues/robertdebock-reboot-reports-changed-without-rebooting.md) and [Foomuuri and cloud-init Ordering Cycle](en/docs/known-issues/foomuuri-cloud-init-ordering-cycle.md)

A second build of the same node changes nothing but the reboot.

## Layout

| Path | What it holds |
| :-- | :-- |
| `ansible.cfg` | Ansible settings for this controller, read when you run from this directory |
| `inventory/localhost.yml` | The controller host itself |
| `inventory/group_vars/all/` | Configuration as data, one file per subject, each value with a comment saying what it is for |
| `build.yml` | The playbook |
| `platforms/incus/` | The play that creates an Incus node |
| `platforms/ssh/` | The plays that reach, prepare and switch the connection of an ssh node |
| `tasks/wait-for-boot.yml` | The boot wait every platform shares |
| `requirements.yml` | Collections and roles, each pinned to a version |
| `scripts/new-node` | Writes a node definition to `~/.secrets/uc-raw/` |
| `scripts/*-release.py`, `scripts/bump-version.py` | Release tools, see [Cut and Publish a Release](en/docs/guides/releases/cut-and-publish-a-release.md) |
| `en/docs/guides/` | Step-by-step guides |
| `en/docs/known-issues/` | Problems found in the tools uc-node uses, and what uc-node does about them |
| `en/docs/sessions/` | Records of working sessions |

The files in `inventory/group_vars/all/` live next to the inventory, so Ansible loads them for every play, including the platform plays `build.yml` imports.

## Node definitions

A node definition is a YAML file that describes one node. It holds password hashes, so it lives outside the repository, in `~/.secrets/uc-raw/`, with mode `0600` in a directory of mode `0700`. `scripts/new-node` writes it, and `build.yml` reads it with `-e @<file>`.

Values passed with `-e` override every value in `inventory/group_vars/all/`. So:

- `inventory/group_vars/all/node.yml` holds the defaults for the optional fields, such as `platform: incus`, `node_label: raw` and `ssh_port: 22`, used only when the node definition does not set them
- `inventory/group_vars/all/names.yml` holds the names calculated from `client_domain` and `node_label`, which a node definition must not set, and the build refuses one that does
- the platform's create play sets the connection variables, such as `ansible_host`, `ansible_user` and `ansible_port`, so the build refuses a node definition that sets one. `ansible_become_password` is allowed

| Field | Required | What it holds |
| :-- | :-- | :-- |
| `client_domain` | yes | The client's domain, for example `example.org` |
| `node_label` | no, default `raw` | One of `raw`, `dev`, `stage` or `prod` |
| `platform` | no, default `incus` | One of the platforms in `inventory/group_vars/all/platforms.yml` |
| `node_address` | for `ssh` | The node's IPv4 or IPv6 address |
| `root_password_hash` | yes | SHA-512 crypt hash of root's password |
| `initial_username` | yes | The initial user, who logs in with the key and uses `sudo` |
| `initial_password_hash` | yes | SHA-512 crypt hash of the initial user's password |
| `ssh_public_key` | yes | The initial user's public key |
| `ssh_port` | no, default `22` | The port SSH listens on |
| `ssh_sources` | no, default any | Addresses or networks allowed to reach SSH |

## Naming

A node is named after its label and the client's domain. For `example.org`:

| Label | Hostname | Fully qualified domain name | Node definition | Incus instance |
| :-- | :-- | :-- | :-- | :-- |
| `raw` | `raw` | `raw.example.org` | `raw.example.org.yml` | `raw-example-org` |
| `dev` | `dev` | `dev.example.org` | `dev.example.org.yml` | `dev-example-org` |
| `stage` | `stage` | `stage.example.org` | `stage.example.org.yml` | `stage-example-org` |
| `prod` | `prod` | `prod.example.org` | `prod.example.org.yml` | `prod-example-org` |

- The node definition file is named after the fully qualified domain name, `<node_label>.<client_domain>.yml`.
- The Incus instance name is the fully qualified domain name with dots replaced by hyphens, since Incus allows only letters, digits and hyphens, and at most 63 characters.
- The node is added to Ansible's inventory under its fully qualified domain name, and `hostname -f` on the node returns it.

## Requirements

On the controller host:

- ansible-core, for example in a virtual environment:

  ```sh
  . ~/.venvs/ansible/current/bin/activate
  ansible --version
  ```

- the collections and roles in `requirements.yml`:

  ```sh
  ansible-galaxy install -r requirements.yml
  ```

  Collections are installed to `~/.ansible/collections/` and roles to `~/.ansible/roles/`, never into this repository.

- for the `incus` platform, the `incus` client, usable by your user without `sudo`. If `incus list` needs `sudo`, add your user to the `incus-admin` group.

- for the `ssh` platform, the OpenSSH client, the node's host key in `~/.ssh/known_hosts`, and the node's entry in `~/.ssh/config`, as [Build a Node on an SSH Host](en/docs/guides/3-build-a-node-on-an-ssh-host.md) describes.

- Python 3 with PyYAML, `openssl` and `ssh-keygen`, for `scripts/new-node`. The Ansible virtual environment already has PyYAML.

## Secrets

| File | What it holds |
| :-- | :-- |
| `~/.secrets/uc-raw/defaults.yml` | The defaults `scripts/new-node` offers: client domain, initial user, SSH key, port and sources, and the default password hashes |
| `~/.secrets/uc-raw/<node_label>.<client_domain>.yml` | One node definition, written by `scripts/new-node` and read by `build.yml` |

Never commit a node definition, a password hash, a real address or a client's name to this repository. Examples use `203.0.113.0/24`, `198.51.100.0/24` and `example.org`. See [Handle Secrets Committed to a Repository](en/docs/guides/secrets/handle-secrets-committed-to-a-repository.md) if one slips through.

## Run it

From this directory, so Ansible reads `ansible.cfg` and the inventory:

```sh
scripts/new-node
ansible-playbook build.yml -e @$HOME/.secrets/uc-raw/raw.example.org.yml
```

On the `ssh` platform, the first build of a host adopts it, and every build asks for the initial user's password for `sudo`:

```sh
ansible-playbook build.yml -e @$HOME/.secrets/uc-raw/raw.example.org.yml -e uc_raw_node_adopt=true --ask-become-pass
```

## Guides

- [Set Up the Defaults for New Nodes](en/docs/guides/1-setup-the-defaults-for-new-nodes.md): create `~/.secrets/uc-raw/defaults.yml`, with the right permissions and the password hashes.
- [Build and Check a Raw Node](en/docs/guides/2-build-and-check-a-raw-node.md): build a node on the local Incus host, check it, run it again, and check that an instance uc-node does not own is refused.
- [Build a Node on an SSH Host](en/docs/guides/3-build-a-node-on-an-ssh-host.md): adopt a fresh Debian 13 host or an existing node over SSH, check it, build it again, and get back in when locked out.
- [Add a New Platform to the Raw Node Controller](en/docs/guides/add-a-new-platform.md): what a platform must provide, with the ssh platform as the worked example.
- [Handle Secrets Committed to a Repository](en/docs/guides/secrets/handle-secrets-committed-to-a-repository.md): what to do when a secret reaches a repository.
- [Cut and Publish a Release](en/docs/guides/releases/cut-and-publish-a-release.md): release this repository.
