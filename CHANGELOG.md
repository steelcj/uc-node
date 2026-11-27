# Changelog

All notable changes to uc-node are recorded here. This is the repository-level changelog: it records what each tagged release contained and why. Documents with front matter also carry their own changelog, for changes inside that document.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this repository follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Versions track the `VERSION` file and the git tags. Dates are ISO 8601. Changes not yet released are listed under Unreleased, and `scripts/cut-release.py` turns that section into the next version's.

## [Unreleased]

To be released as 0.3.0. 0.3.0 cannot read 0.2.0's node definitions, and has no upgrade path from it: start from [Set Up a Client](en/docs/guides/0-set-up-a-client.md).

### Added

- Build batches: `scripts/new-batch <batch>` writes `~/.secrets/uc/build/batches/<batch>.yml`, mode `0600`, with the hashes of the root password and the batch password, from passwords typed at the terminal and hashed by `openssl` on its standard input. The batch password itself goes to uc-controller, and uc-node never holds it.
- `plugins/lookup/uc_secret.py`, a copy of uc-controller's lookup rooted at `~/.secrets/uc/build`, with the override `UC_NODE_SECRETS_DIR`. It is the only way the build reads a secret.
- `scripts/build <client inventory> <fqdn>`, which runs `build.yml` with the node definition from `intake/` and `uc_client_inventory`.
- The confirmation: after the reboot, the build measures every field of raw node contract 0.3.1 on the node, writes `/var/lib/raw-node/confirmation.yml` (RN-REP-01), reads it back through the platform, and checks it with uc-controller's `check_raw_confirmation.py` when `UC_CONTROLLER` is set, failing on anything but pass.
- The candidate: the build writes `<client inventory>/candidates/<fqdn>.yml`, with the fields of the raw node handoff design, and prints the ED25519 fingerprint and the command to compare it at the console.
- Rejections: `plugins/callback/uc_reject.py` writes one entry to the client log, `logs/rejected/` beside the client inventory, when the build cannot secure a node, and removes the node's candidate.
- `tests/`, run with `python3 tests/run_tests.py`: the lookup, `new-batch`, `new-node`, `scripts/build`, the check play, the templates, and the rejection callback.
- The guides Set Up a Client and Hand Over to the Fleet.

### Changed

- Node definitions live in the client inventory's `intake/`, mode `0644`, without secrets, and name their batch in the new required field `raw_node_batch`. `root_password_hash` and `initial_password_hash` are read from the batch, and the build refuses a node definition that still holds either.
- The check play requires `uc_client_inventory`, refuses a node definition that is not in its `intake/`, checks `raw_node_batch`, and reads the batch once, so a missing or badly protected batch file stops the build before anything is created.
- `scripts/new-node <client inventory>` reads `intake/defaults.yml`, refuses one that holds a hash, asks for the batch, and no longer asks for passwords.
- `scripts/new-node` says when `intake/defaults.yml` is missing, and offers no key then instead of `~/.ssh/id_ed25519.pub`. Its client domain question gives an example, and asks again when the domain does not match the client's folder. Its key question says it takes a key line or a path. It no longer prints the build command.
- Batch names in messages and guides are `raw-YYYY-MM-DD-NN` with the day's date: `raw-1970-01-01-NN` is reserved for documents and tests.
- A second build changes the reboot, the confirmation and the candidate.
- The guides 1 to 3, the guide to adding a platform, and the README describe the client inventory, `scripts/build` and batches.

### Removed

- Every use of `~/.secrets/uc-raw/` from the code.
- The ssh guide's paths for an existing node and a node made by an earlier version: nothing runs 0.2.0.

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
