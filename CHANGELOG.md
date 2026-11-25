# Changelog

All notable changes to uc-node are recorded here. This is the repository-level changelog: it records what each tagged release contained and why. Documents with front matter also carry their own changelog, for changes inside that document.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this repository follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Versions track the `VERSION` file and the git tags. Dates are ISO 8601. Changes not yet released are listed under Unreleased, and `scripts/cut-release.py` turns that section into the next version's.

## [Unreleased]

## [0.2.0] - 2026-11-24

### Added

- The `ssh` platform: uc-node builds a raw node on any Debian 13 host reached over SSH, such as a VPS, as well as on the local Incus host. A host is adopted on its first build with `-e uc_raw_node_adopt=true`, which writes the ownership marker `/etc/uc-raw-node/owner`. Every other build refuses a host without the marker, before any change.
- Platforms as data and directories: `inventory/group_vars/all/platforms.yml` lists each platform and the node definition fields it requires, and each platform's plays are in `platforms/<platform>/`.
- A check of the node definition before anything is created or changed: required fields, `client_domain`, `node_label`, `platform`, `node_address`, the length of the Incus instance name, and node definitions that still use `hostname`, set a calculated name, or set a connection variable the create play sets.
- On the ssh platform, every login is tried once and never retried, with `IdentitiesOnly=yes` and strict host key checking, since repeated failed logins make OpenSSH 10 block the controller's address. When both logins are refused, the build shows the `~/.ssh/config` entry the node needs.
- On the ssh platform, sshd drop-ins that set an option the contract controls are removed, cloud-init is kept away from the hostname and disabled after the first boot, and root's `authorized_keys` is emptied once the contract connection has worked.
- A boot wait with a timeout on every platform, which shows the jobs the node is waiting for instead of hanging, and a check after the reboot that fails if systemd found an ordering cycle.
- `scripts/new-node` asks for the node label and the platform, and for the ssh platform the node's address, asks for confirmation when `ssh_sources` limits SSH, and prints the `~/.ssh/config` entry the node needs.
- The guide Build a Node on an SSH Host, for a fresh install and for an existing node, with troubleshooting by error message.

### Changed

- Nodes are named from `client_domain` and `node_label`: the hostname is the label, the fully qualified domain name is `<node_label>.<client_domain>`, and the node definition is named `<node_label>.<client_domain>.yml`. `hostname -f` on the node returns the fully qualified domain name.
- The configuration moved from `group_vars/` to `inventory/group_vars/`, so the platform plays `build.yml` imports load it too.
- The reboot uses `ansible.builtin.reboot`, which fails if the boot ID did not change, instead of `robertdebock.reboot`, which reported changed without rebooting.
- `AuthorizedKeysCommand` is set to `/usr/bin/true`, so sshd stops logging that its path is not absolute.
- The README, the guides and the ROADMAP describe the controller as it is now, and the guide to adding a platform uses the ssh platform as its worked example.

### Removed

- `robertdebock.reboot`, and `group_vars/all/reboot.yml`.
- The notes from running the build against a VPS by hand, now part of the ssh guide, and a second copy of the guide to adding a platform.

### Fixed

- The Incus build, which still used `node_name` after naming moved to `client_domain` and `node_label`.

## [0.1.0] - 2026-11-23

### Added

- The build, its configuration and its guides, brought over from the earlier repository, which was retired.

## [0.0.2] - 2026-11-23

### Added

- The controller's files.

## [0.0.1] - 2026-11-23

### Added

- The repository, created from the uc-repo template.
