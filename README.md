# uc-raw-node-creation

The raw node controller. For now it:

- creates the Incus instance for a raw node, with uc-raw-node's ownership marker, and refuses an instance with the same name that uc-raw-node did not create,
- adds the node to the inventory with an `incus exec` connection, and waits for it to boot,
- bootstraps the node with `robertdebock.bootstrap`, which installs `python3`, `sudo`, `gnupg` and `python3-apt` on Debian, so Ansible modules can run on it,
- configures the node to contract: the hostname, the packages, root's password and the initial user, the Foomuuri firewall and key-only SSH,
- reboots it.

## Layout

| Path | What it holds |
| :-- | :-- |
| `ansible.cfg` | Ansible settings for this controller, read when you run from this directory |
| `inventory/localhost.yml` | The controller host itself, where the Incus client runs |
| `inventory/group_vars/all/` | Configuration as data, one file per subject: `incus.yml` holds the image, `node.yml` the defaults for the node definition's optional fields, and one file per role, named after it |
| `requirements.yml` | Collections and roles, each pinned to a version |
| `build.yml` | The playbook |
| `scripts/new-node` | Writes a node definition to `~/.secrets/uc-raw/` |
| `en/guides/` | Step-by-step guides |

## Requirements

On the controller host:

- ansible-core, for example in a virtual environment:

  ```sh
  . ~/.venvs/ansible/current/bin/activate
  ansible --version
  ```

- the `incus` client, usable by your user without `sudo`. If `incus list` needs `sudo`, add your user to the `incus-admin` group.

- the collections and roles in `requirements.yml`:

  ```sh
  ansible-galaxy install -r requirements.yml
  ```

  Collections are installed to `~/.ansible/collections/` and roles to `~/.ansible/roles/`, never into this repository.

- Python 3 with PyYAML, `openssl` and `ssh-keygen`, for `scripts/new-node`. The Ansible virtual environment already has PyYAML.

## Secrets

Node definitions and the defaults for `scripts/new-node` hold password hashes, so they live outside the repository, in `~/.secrets/uc-raw/`, with mode `0600` in a directory of mode `0700`:

| File | What it holds |
| :-- | :-- |
| `~/.secrets/uc-raw/defaults.yml` | The defaults `scripts/new-node` offers: client domain, initial user, SSH key, port and sources, and the default password hashes |
| `~/.secrets/uc-raw/<client domain>.yml` | One node definition, written by `scripts/new-node` and read by `build.yml` |

## Naming

For now, a raw node is named after the client domain:

| Name | Rule | For `vishpala.com` |
| :-- | :-- | :-- |
| Node definition | `<client domain>.yml` | `vishpala.com.yml` |
| Fully qualified domain name | `raw.<client domain>` | `raw.vishpala.com` |
| Incus instance | the fully qualified domain name, with dots replaced by hyphens, since Incus allows only letters, digits and hyphens | `raw-vishpala-com` |

The hostname set on the node does not follow this yet: it is still the client domain.

## Run it

From this directory, so Ansible reads `ansible.cfg`:

```sh
scripts/new-node
ansible-playbook build.yml -e @$HOME/.secrets/uc-raw/vishpala.com.yml
```

## Guides

1. [Setup the Defaults For New Nodes](en/guides/1-setup-the-defaults-for-new-nodes.md): create `~/.secrets/uc-raw/defaults.yml`, with the right permissions and the password hashes.
2. [Build and Check a Raw Node](en/guides/2-build-and-check-a-raw-node.md): write a node definition, build the node, check it, run it again, and check that an instance uc-raw-node does not own is refused.
