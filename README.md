# uc-node, the raw node controller

uc-node builds a node that meets the raw node contract, with Ansible, and hands it over to uc-controller connected securely: the node meets the contract, its confirmation is on the node, and its candidate is in the client inventory. It builds on one of two platforms:

| Platform | What it builds on | How the controller reaches the node |
| :-- | :-- | :-- |
| `incus` | A container on the local Incus host, which uc-node launches | `incus exec`, through the `community.general.incus` connection |
| `ssh` | Any Debian 13 host reached as root over SSH, such as a VPS, which uc-node adopts | SSH: root on port 22 for the first build, then the initial user on `ssh_port` with `sudo` |

On every platform, a build:

- checks the node definition, the client inventory and the batch before anything is created or changed
- creates the Incus instance, or reaches the ssh host and checks that uc-node owns it, with an ownership marker
- waits for the node to finish booting, for at most `boot_timeout` seconds
- bootstraps it with `robertdebock.bootstrap`, so Ansible modules can run
- on the ssh platform, removes what the provider's image puts on the node that would break the contract
- configures the node to contract: the hostname and fully qualified domain name, root's password and the initial user, the Foomuuri firewall and key-only SSH
- reboots it with `ansible.builtin.reboot`, which fails if the boot ID did not change, then checks that the node finished booting without a systemd ordering cycle. See the known issues [robertdebock.reboot Reports Changed Without Rebooting](en/docs/known-issues/robertdebock-reboot-reports-changed-without-rebooting.md) and [Foomuuri and cloud-init Ordering Cycle](en/docs/known-issues/foomuuri-cloud-init-ordering-cycle.md)
- measures the confirmation on the node, writes it to `/var/lib/raw-node/confirmation.yml` (RN-REP-01), reads it back through the platform, and checks it with uc-controller's `check_raw_confirmation.py` when `UC_CONTROLLER` names a uc-controller checkout
- writes the node's candidate to the client inventory's `candidates/`, and prints the ED25519 fingerprint to compare at the console before admission
- when it cannot secure the node, records a rejection in the client log, `logs/rejected/` beside the client inventory, and removes the node's candidate

A second build of the same node changes three things: the reboot, the confirmation's timestamp and the candidate's build time.

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
| `tasks/confirmation.yml` | Measures, writes, reads back and checks the confirmation |
| `templates/` | The confirmation and the candidate |
| `plugins/lookup/uc_secret.py` | The only way the build reads a secret, a copy of uc-controller's lookup rooted at `~/.secrets/uc/build` |
| `plugins/callback/uc_reject.py` | Records a node the build cannot secure in the client log |
| `requirements.yml` | Collections and roles, each pinned to a version |
| `scripts/build` | Builds one node from a client inventory |
| `scripts/new-node` | Writes a node definition to a client inventory's `intake/` |
| `scripts/new-batch` | Writes a build batch, the hashes of its passwords, to `~/.secrets/uc/build/batches/` |
| `tests/` | The tests, run with `python3 tests/run_tests.py` |
| `scripts/*-release.py`, `scripts/bump-version.py` | Release tools, see [Cut and Publish a Release](en/docs/guides/releases/cut-and-publish-a-release.md) |
| `en/docs/guides/` | Step-by-step guides |
| `en/docs/known-issues/` | Problems found in the tools uc-node uses, and what uc-node does about them |
| `en/docs/sessions/` | Records of working sessions |

The files in `inventory/group_vars/all/` live next to the inventory, so Ansible loads them for every play, including the platform plays `build.yml` imports.

## Node definitions

A node definition is a YAML file that describes one node. It lives in the client inventory, `<client inventory>/intake/<fqdn>.yml`, mode `0644` like any file there, and holds no secret: it names its build batch in `raw_node_batch`, and the build reads the batch's password hashes through `uc_secret`. `scripts/new-node` writes it, and `scripts/build` passes it to `build.yml` with `-e @<file>`, with the client inventory as `uc_client_inventory`. The build refuses a node definition that is not in the client inventory's `intake/`, or that still holds a password hash.

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
| `initial_username` | yes | The initial user, who logs in with the key and uses `sudo` |
| `ssh_public_key` | yes | The initial user's public key |
| `ssh_port` | no, default `22` | The port SSH listens on |
| `ssh_sources` | no, default any | Addresses or networks allowed to reach SSH |
| `raw_node_batch` | yes | The build batch, `raw-YYYY-MM-DD-NN`, whose root password and batch password the node is built with |

`root_password_hash` and `initial_password_hash` are no longer fields: they are in the batch.

## Naming

A node is named after its label and the client's domain. For `example.org`:

| Label | Hostname | Fully qualified domain name | Node definition and candidate | Incus instance |
| :-- | :-- | :-- | :-- | :-- |
| `raw` | `raw` | `raw.example.org` | `raw.example.org.yml` | `raw-example-org` |
| `dev` | `dev` | `dev.example.org` | `dev.example.org.yml` | `dev-example-org` |
| `stage` | `stage` | `stage.example.org` | `stage.example.org.yml` | `stage-example-org` |
| `prod` | `prod` | `prod.example.org` | `prod.example.org.yml` | `prod-example-org` |

- The node definition, in `intake/`, and the candidate, in `candidates/`, are named after the fully qualified domain name, `<node_label>.<client_domain>.yml`.
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

- Python 3 with PyYAML, `openssl` and `ssh-keygen`, for the scripts. The Ansible virtual environment already has PyYAML.

- a client inventory, made with uc-controller's `scripts/new-inventory`, and a build batch, as [Set Up a Client](en/docs/guides/0-set-up-a-client.md) describes.

- to check the confirmation as the build writes it, a uc-controller checkout, named by `UC_CONTROLLER`. Without it, the build warns that the confirmation was not checked.

## Secrets

uc-node's only secrets are the password hashes of each build batch. It never holds a password.

| File | What it holds |
| :-- | :-- |
| `~/.secrets/uc/build/batches/<batch>.yml` | `root_password_hash` and `initial_password_hash`, written by `scripts/new-batch`, mode `0600` in directories of mode `0700`, and read only through `uc_secret`, which refuses a file whose modes or owner are wrong |
| `~/.secrets/uc/fleet/batches/<batch>.yml` | uc-controller's: the batch password itself. uc-node never reads it |

`UC_NODE_SECRETS_DIR` names another secrets root in place of `~/.secrets/uc/build`, for the tests. The client inventory holds no secret: its pre-commit hook runs uc-controller's `check_inventory.py`, which refuses a crypt hash in any file. [Set Up a Client](en/docs/guides/0-set-up-a-client.md) moves node definitions out of `~/.secrets/uc-raw/`, where uc-node 0.2.0 kept them with their hashes.

Never commit a node definition, a password hash, a real address or a client's name to this repository. Examples use the safe values register in uc-contracts: `example.org`, `example-org`, `203.0.113.0/24`, `198.51.100.0/24` and batches `raw-1970-01-01-NN`. See [Handle Secrets Committed to a Repository](en/docs/guides/secrets/handle-secrets-committed-to-a-repository.md) if one slips through.

## Run it

From this directory, with a client inventory and a batch set up as [Set Up a Client](en/docs/guides/0-set-up-a-client.md) describes:

```sh
scripts/new-node ~/.private/uc/example-org/uc-inventory
UC_CONTROLLER=~/uc-controller scripts/build ~/.private/uc/example-org/uc-inventory raw.example.org
```

`scripts/build` runs `ansible-playbook build.yml` from this directory, so Ansible reads `ansible.cfg` and the inventory, and passes any further arguments through. On the `ssh` platform, the first build of a host adopts it, and every build asks for the batch password for `sudo`:

```sh
scripts/build ~/.private/uc/example-org/uc-inventory raw.example.org -e uc_raw_node_adopt=true --ask-become-pass
```

The tests:

```sh
UC_CONTROLLER=~/uc-controller python3 tests/run_tests.py
```

## Guides

- [Set Up a Client](en/docs/guides/0-set-up-a-client.md): the client's private folder, its inventory and log, the intake defaults and a build batch, and moving node definitions out of `~/.secrets/uc-raw/`.
- [Set Up the Defaults for New Nodes](en/docs/guides/1-setup-the-defaults-for-new-nodes.md): write the client inventory's `intake/defaults.yml`, without hashes.
- [Build and Check a Raw Node](en/docs/guides/2-build-and-check-a-raw-node.md): build a node on the local Incus host, check it, its confirmation and its candidate, run it again, and check that an instance uc-node does not own is refused.
- [Build a Node on an SSH Host](en/docs/guides/3-build-a-node-on-an-ssh-host.md): adopt a fresh Debian 13 host or an existing node over SSH, check it, build it again, and get back in when locked out.
- [Hand Over to the Fleet](en/docs/guides/4-hand-over-to-the-fleet.md): what connected securely means, the confirmation and the candidate, the fingerprint at the console, admission with uc-controller, and rejections.
- [Add a New Platform to the Raw Node Controller](en/docs/guides/add-a-new-platform.md): what a platform must provide, with the ssh platform as the worked example.
- [Handle Secrets Committed to a Repository](en/docs/guides/secrets/handle-secrets-committed-to-a-repository.md): what to do when a secret reaches a repository.
- [Cut and Publish a Release](en/docs/guides/releases/cut-and-publish-a-release.md): release this repository.
