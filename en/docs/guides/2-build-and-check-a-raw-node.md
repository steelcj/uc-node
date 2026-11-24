# Build and Check a Raw Node

This guide writes a node definition with `scripts/new-node`, builds the raw node on the local Incus host, and checks the result. It assumes the defaults from [Set Up the Defaults for New Nodes](1-setup-the-defaults-for-new-nodes.md) are in place, and that the requirements in the [README](../../../README.md#requirements) are installed. To build on a host reached over SSH instead, see [Build a Node on an SSH Host](3-build-a-node-on-an-ssh-host.md).

Run every command from the repository directory, so Ansible reads `ansible.cfg` and the inventory. The examples use the client domain `example.org`.

## Write the node definition

```sh
scripts/new-node
```

With the defaults, this is four answers:

```text
Use defaults from ~/.secrets/uc-raw/defaults.yml? [Y/n]: y
Node label (raw, dev, stage, prod) [raw]:
Platform (incus, ssh) [incus]:
Write ~/.secrets/uc-raw/raw.example.org.yml? [y/N]: y
Wrote ~/.secrets/uc-raw/raw.example.org.yml
```

The node definition is named after the node's fully qualified domain name, `<node label>.<client domain>`, and written with mode `0600`.

## Build the node

```sh
ansible-playbook build.yml -e @$HOME/.secrets/uc-raw/raw.example.org.yml
```

The build first checks the node definition, and stops before anything is created if a field is missing or breaks its rule, with a message naming the field.

The Incus instance is named after the node's fully qualified domain name, with dots replaced by hyphens, since Incus allows only letters, digits and hyphens: `raw-example-org`.

The first run downloads `images:debian/13` if it is not cached yet. The bootstrap step shows a red "Test connection" error on a new node: the role tries Ansible's `ping` before Python is installed, catches the failure and installs Python. The recap counts it as `rescued=1`, not as a failure.

The build ends with a reboot, then waits for the node to finish booting, and fails if systemd found an ordering cycle during the boot.

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
incus exec raw-example-org -- journalctl --list-boots
```

Expected:

| Check | Expected |
| :-- | :-- |
| Ownership marker | `uc-raw-node` |
| `hostname`, `hostname -f` | `raw`, `raw.example.org` |
| `systemctl is-system-running` | `running` |
| Python and `sudo` | Their versions |
| `sshd -T` | `port 22`, `permitrootlogin no`, `passwordauthentication no` |
| Foomuuri | `active` |
| `journalctl --list-boots` | Two boots, the second starting at the build's reboot |

## Run it again

```sh
ansible-playbook build.yml -e @$HOME/.secrets/uc-raw/raw.example.org.yml
```

Expected: `changed=0` for localhost, and `changed=1` for `raw.example.org`, which is the reboot. The build reboots on every run, on purpose. No second instance is created.

## Check that an instance uc-node does not own is refused

Launch an instance without the ownership marker, under the name a `dev` node for `example.org` would use:

```sh
incus launch images:debian/13 dev-example-org
```

Write a node definition for it. Answer `y` to "Use defaults?", `dev` to the node label, and press Enter for the platform:

```sh
scripts/new-node
```

Then build it, and check the instance was left alone:

```sh
ansible-playbook build.yml -e @$HOME/.secrets/uc-raw/dev.example.org.yml
incus config get dev-example-org user.uc-raw-node.owner
```

Expected: the build fails with "dev-example-org exists but was not created by uc-raw-node, so it is left alone", before anything runs on the instance, and the last command prints nothing.

## Clean up

```sh
incus delete --force raw-example-org dev-example-org
rm ~/.secrets/uc-raw/dev.example.org.yml
```

Keep `~/.secrets/uc-raw/raw.example.org.yml` if you want to build the node again.
