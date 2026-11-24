# 2. Build and Check a Raw Node

This guide writes a node definition with `scripts/new-node`, builds the raw node on the local Incus host, and checks the result. It assumes the defaults from [Setup the Defaults For New Nodes](1-setup-the-defaults-for-new-nodes.md) are in place, and that the requirements in the [README](../../README.md#requirements) are installed.

Run every command from the repository directory, so Ansible reads `ansible.cfg`.

## Write the node definition

```sh
scripts/new-node
```

With the defaults, this is two answers:

```
Use defaults from ~/.secrets/uc-raw/defaults.yml? [Y/n]: y
Write ~/.secrets/uc-raw/vishpala.com.yml? [y/N]: y
Wrote ~/.secrets/uc-raw/vishpala.com.yml
```

The node definition is named after the client domain, and written with mode `0600`.

## Build the node

```sh
ansible-playbook build.yml -e @$HOME/.secrets/uc-raw/vishpala.com.yml
```

The Incus instance is named after the node's fully qualified domain name, `raw.<client domain>`, with dots replaced by hyphens, since Incus allows only letters, digits and hyphens: `raw-vishpala-com`.

The first run downloads `images:debian/13` if it is not cached yet. The bootstrap step shows a red "Test connection" error on a new node: the role tries Ansible's `ping` before Python is installed, catches the failure and installs Python. The recap counts it as `rescued=1`, not as a failure.

## Check the node

```sh
incus config get raw-vishpala-com user.uc-raw-node.owner
incus exec raw-vishpala-com -- python3 --version
incus exec raw-vishpala-com -- sudo --version
incus exec raw-vishpala-com -- sshd -T | grep -E '^(port|permitrootlogin|passwordauthentication) '
incus exec raw-vishpala-com -- systemctl is-enabled foomuuri
```

Expected: `uc-raw-node`, the versions of Python and sudo, `port 22`, `permitrootlogin no` and `passwordauthentication no`, and `enabled`.

## Run it again

```sh
ansible-playbook build.yml -e @$HOME/.secrets/uc-raw/vishpala.com.yml
```

Expected: `changed=0` for localhost, and `changed=1` for `raw-vishpala-com`, which is the reboot. The build reboots on every run, on purpose. No second instance is created.

## Check that an instance uc-raw-node does not own is refused

Launch an instance without the ownership marker, under the name a build for `example.org` would use:

```sh
incus launch images:debian/13 raw-example-org
```

Write a node definition for `example.org`. Answer `n` to "Use defaults?", give `example.org` as the client domain, and accept the other defaults:

```sh
scripts/new-node
```

Then build it, and check the instance was left alone:

```sh
ansible-playbook build.yml -e @$HOME/.secrets/uc-raw/example.org.yml
incus config get raw-example-org user.uc-raw-node.owner
```

Expected: the play fails with "raw-example-org exists but was not created by uc-raw-node, so it is left alone", before anything runs on the instance, and the last command prints nothing.

## Clean up

```sh
incus delete --force raw-vishpala-com raw-example-org
rm ~/.secrets/uc-raw/example.org.yml
```

Keep `~/.secrets/uc-raw/vishpala.com.yml` if you want to build the node again.
