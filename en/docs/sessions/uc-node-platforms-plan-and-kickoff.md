---
title: Platforms for uc-node, Plan and Kickoff Prompt
description: The plan for letting uc-node build raw nodes on more than one platform, starting with Incus and hosts reached over SSH, and the Claude Code kickoff prompt that carries it out.
version: 0.1.1
status: provisional
date: 2026-11-23
language: en-CA
---

# Platforms for uc-node, Plan and Kickoff Prompt

## Where the repository stands

The repository was recreated on 2026-11-23 to remove secrets from its history. At tag `v0.1.0`, commit `19e3cb2`:

| Area | State |
| :-- | :-- |
| `group_vars/all/node.yml` | Defaults for `platform`, `node_label`, `ssh_port` and `ssh_sources`, with the override rule explained |
| `group_vars/all/names.yml` | `node_fqdn` and `node_hostname`, calculated from `client_domain` and `node_label`; a comment uses a client's domain as its example |
| `group_vars/all/incus.yml` | `incus_instance: "{{ node_name }}"`, but `node_name` is no longer defined anywhere |
| `group_vars/all/hostname.yml` | Does not set `hostname`, so `robertdebock.hostname` still reads the node definition's `hostname` field |
| `scripts/new-node` | Still writes `hostname: <client domain>`, no `client_domain`, `node_label` or `platform`, and names the file `<client domain>.yml` |
| `build.yml` | Incus only, reboots with `robertdebock.reboot` |
| README | Titled `uc-raw-node-creation`, links point to `en/guides/`, which moved to `en/docs/guides/`, naming section describes the old rule |
| ROADMAP | Lists the hostname and node definition check work this plan does, and the old design documents |
| CHANGELOG | Copied from the old repository: calls itself the changelog of the uc-radar repository, holds pasted `git status` lists naming files that were kept out of the new repository, and its new `0.1.0` section sits above the old `0.1.1` |
| Guides | Two copies of the platform guide that differ only in their titles |
| `en/docs/guides/setup-ex2-vps-node.md` | A pasted chat reply about running the build against a VPS, with an example address; not a guide yet |
| `en/docs/guides/secrets/handle-secrets-committed-to-a-repository.md` | Names two files that were kept out of the new repository, one of them by a client's name |
| VPS issues notes | Not in the repository. Their findings are listed below and in the kickoff prompt |

Because of the `incus.yml` and naming gaps, a build with an existing node definition now fails: `node_name` is undefined, and `client_domain` is missing from node definitions written by `scripts/new-node`. Fixing this is the first phase of the plan.

## Findings from the first VPS run

The notes from the first run against a VPS were kept out of the repository. These are the findings the plan must take in:

- `robertdebock.reboot` 3.4.1 reports `changed` without rebooting, because its async job is killed before `shutdown` runs. Incus builds may never have rebooted either.
- The reboot role's reconnect loop as root, plus the SSH agent offering every key, triggered OpenSSH 10's `PerSourcePenalties` and locked the controller out.
- `IdentitiesOnly=yes` is needed on the SSH connection.
- sshd logs `AuthorizedKeysCommand path is not absolute`, most likely from a `robertdebock.openssh` default.
- Changing `ssh_port` in the same run as first contact moves sshd and Foomuuri while Ansible is connected on 22.

`en/docs/guides/setup-ex2-vps-node.md` adds two more: after the OpenSSH role sets `PermitRootLogin no`, the reboot cannot reconnect as root, and a provider's cloud-init can reset the hostname on reboot.

## Is a registry still needed

Not as a component. The earlier design had a platform registry as a separate piece of machinery. With the new approach, a platform is a directory of plays, `platforms/<name>/`, chosen by the node definition's `platform` field.

What remains useful from the registry idea is a small data file that lists the platforms and the fields each one requires. It answers two questions that otherwise get scattered through the code:

- Is this `platform` value one the controller knows?
- Which fields must this node definition have?

It is the input for the node definition check already on the roadmap, and `scripts/new-node` can read it to know what to ask. It holds data only, no logic:

```yaml
---
# group_vars/all/platforms.yml
#
# The platforms uc-node can build on, and the node definition fields each
# one requires on top of the fields every platform requires.

node_required_fields:
  - client_domain
  - root_password_hash
  - initial_username
  - initial_password_hash
  - ssh_public_key

platforms:
  incus:
    required_fields: []
  ssh:
    required_fields:
      - node_address
```

Adding a platform is then three things: a directory under `platforms/`, an entry in this file, and a guide.

## Decisions to make first

### vps or ssh

`node.yml` says `incus or vps`. Nothing in the adoption path is specific to a VPS: it works the same for any Debian 13 host you can reach as root over SSH, including bare metal installed with uc-ventoy and VMs on another hypervisor. What differs between a VPS and those, such as cloud-init, is better handled by checking for it on the node than by the platform name.

The plan and prompt use `ssh`. If you prefer `vps`, replace it throughout the prompt before running it. A provider API, when it comes, would be its own platform, for example `hcloud`, reusing the `ssh` platform's prepare plays.

### The next version number

The recreated repository's tags are `v0.0.1`, `v0.0.2` and `v0.1.0`, while the old repository reached `0.1.1`. The prompt leaves `VERSION` alone. When you cut the release for this work, choosing a version above `0.1.1`, such as `0.2.0`, keeps any old reference to `0.1.1` from looking newer.

## The plan

### Before anything else

Done: the repository was recreated, the history scrubbed and `v0.1.0` moved to the scrubbed commit.

### Phase 1: make the Incus build work again with the new names

- `incus.yml`: `incus_instance: "{{ node_fqdn | replace('.', '-') }}"`.
- `hostname.yml`: `hostname: "{{ node_hostname }}"`, and write `node_fqdn` into `/etc/hosts` if `robertdebock.hostname` does not.
- `names.yml`: use `example.org` in its comment.
- `scripts/new-node`: ask for `node_label` (`raw`, `dev`, `stage`, `prod`, default `raw`), write `client_domain` and `node_label`, stop writing `hostname`, name the file `<node_fqdn>.yml`.
- `build.yml`: the inventory name becomes `node_fqdn`.
- A node definition check as the first play: required fields present, `client_domain` valid, `node_label` allowed, `platform` known, and the retired `hostname` field refused with a message saying to rename it to `client_domain`.
- Replace `robertdebock.reboot` with `ansible.builtin.reboot`, which waits for the node and fails if the boot ID did not change.

Stop for review. Check: an Incus build, `hostname` and `hostname -f` on the node, uptime after the build, and a second run.

### Phase 2: platforms as directories

- Move the Incus create play to `platforms/incus/create.yml`.
- Add `group_vars/all/platforms.yml` as above.
- `build.yml` imports every platform's plays, and each play carries `when: platform == '<name>'`, so the `platform` default in `node.yml` applies.
- The ownership marker values move to `group_vars/all/ownership.yml`.

Stop for review. The Incus build must behave exactly as at the end of phase 1.

### Phase 3: the ssh platform

- `platforms/ssh/create.yml`: try the contract connection first, fall back to first contact as root on 22, add the node to the inventory, wait for it, check or write the ownership marker file, with `uc_raw_node_adopt` required to write it.
- `platforms/ssh/prepare.yml`: remove sshd drop-ins that set options the contract controls, empty root's `authorized_keys`, and if cloud-init is installed, keep it away from the hostname.
- A play after configure that switches to the contract connection and resets it, so the reboot runs as the initial user.
- `IdentitiesOnly=yes` on every SSH connection.
- Handle a port change on first contact safely (see the prompt).
- Set `AuthorizedKeysCommand` explicitly once its source is known.

Stop for review. You test it against a VPS by hand, following the new guide.

### Phase 4: documents

- README: title, platforms, the override rule, naming, fixed links.
- Guides: one platform guide, brought in line with what was built; a guide for building on the ssh platform, taking in the findings and `setup-ex2-vps-node.md`, which is then deleted.
- Secrets guide: no file names from the old repository.
- ROADMAP: remove what was done, add what was found.
- CHANGELOG: rewritten for this repository, with an Unreleased entry for this work.

## Kickoff prompt

Copy everything inside the block into Claude Code, run from the repository root.

````text
You are working in the uc-node repository, the raw node controller. It builds a node that meets the raw node contract with Ansible. Today it builds only local Incus containers. Your job is to let it build on more than one platform, starting with `incus` (as now) and `ssh` (any Debian 13 host reached as root over SSH, such as a VPS), in four phases. Stop at the end of each phase, summarize what changed and what you checked, and wait for me before starting the next.

## Read first

- README.md, ROADMAP.md, CHANGELOG.md, build.yml, requirements.yml, ansible.cfg
- everything in group_vars/all/
- scripts/new-node
- en/docs/guides/1-setup-the-defaults-for-new-nodes.md and 2-build-and-check-a-raw-node.md
- en/docs/guides/add-a-new-platform.md (the design this work follows)
- en/docs/guides/setup-ex2-vps-node.md (notes from running the build against a VPS by hand)
- en/docs/guides/secrets/handle-secrets-committed-to-a-repository.md

## Findings from the first VPS run

Treat these as requirements. The notes they come from are not in the repository.

- robertdebock.reboot 3.4.1 reports changed without rebooting, because its async job is killed before shutdown runs. Incus builds may never have rebooted either.
- The reboot role's reconnect loop as root, plus the SSH agent offering every key, triggered OpenSSH 10's PerSourcePenalties and locked the controller out.
- IdentitiesOnly=yes is needed on the SSH connection.
- sshd logs "AuthorizedKeysCommand path is not absolute", most likely from a robertdebock.openssh default.
- Changing ssh_port in the same run as first contact moves sshd and Foomuuri while Ansible is connected on 22.
- After robertdebock.openssh sets PermitRootLogin no, the reboot cannot reconnect as root.
- A provider's cloud-init can reset the hostname on reboot.

## Rules

- Work on a branch named `platforms`. Commit at the end of each phase, with a clear message. Do not push, tag or release, and do not change VERSION: versioning is my call.
- Never write secrets, password hashes, real IP addresses, client names or real node definitions into the repository. Examples use 203.0.113.0/24, 198.51.100.0/24 and example.org. Never add files under en/docs/guides/blacklists/ or en/docs/guides/ex2/.
- Node definitions live in ~/.secrets/uc-raw/ and are passed with `-e @<file>`. Values passed with -e override group_vars. Keep `group_vars/all/node.yml` for defaults and `group_vars/all/names.yml` for calculated names, as their comments say.
- Never set ansible_host, ansible_user, ansible_port or other connection variables in group_vars/all: it also applies to localhost. Each platform's create play sets them with add_host.
- Keep configuration as data in group_vars/all/, one file per subject, with a comment saying what each value is for.
- Pin every new collection or role in requirements.yml. Prefer ansible.builtin modules.
- After each phase run: `yamllint .`, `ansible-playbook build.yml --syntax-check -e @<a throwaway node definition in /tmp>`, and `ansible-lint` if it is installed. Run an Incus build only if `incus list` works without sudo; otherwise say so. Never connect to a remote host.
- Documentation style: Markdown, commas instead of em dashes, no numbers in headings, no horizontal rules, no hard line wraps in prose, subsections as the next heading level rather than bold lead-ins, tables with `| :-- |` alignment, Canadian English. Documents with front matter get their version bumped when they change.

## Phase 1: make the Incus build work again with the new names

The repository moved naming to `client_domain` and `node_label`, but left the build broken: `group_vars/all/incus.yml` uses `node_name`, which no longer exists, and node definitions still carry `hostname` instead of `client_domain`.

1. `group_vars/all/incus.yml`: `incus_instance: "{{ node_fqdn | replace('.', '-') }}"`, with its comment updated.
2. `group_vars/all/hostname.yml`: set `hostname: "{{ node_hostname }}"`. Find out from the installed robertdebock.hostname role whether it writes the FQDN to /etc/hosts. If it does not, add the smallest task to the configure play that makes `hostname -f` return `node_fqdn`.
3. `group_vars/all/names.yml`: change the example in its comment to prod.example.org.
4. `build.yml`: add the node to the inventory under `node_fqdn`.
5. Add a first play, on localhost, that checks the node definition before anything is created, and stops with a message naming the field:
   - client_domain, root_password_hash, initial_username, initial_password_hash and ssh_public_key are present
   - `client_domain` is DNS labels of letters, digits and hyphens, separated by dots
   - `node_label` is one of raw, dev, stage, prod
   - a node definition that still has `hostname` is refused, with a message saying to rename it to `client_domain`
   For now keep the required fields in this play; phase 2 moves them to platforms.yml.
6. Replace robertdebock.reboot with ansible.builtin.reboot, which fails if the boot ID did not change (see the findings: the role reports changed without rebooting). Remove the role from requirements.yml and delete group_vars/all/reboot.yml if nothing else uses it.
7. `scripts/new-node`: ask for the node label (default raw, only the four allowed), write `client_domain` and `node_label` instead of `hostname`, and name the file `<node_label>.<client_domain>.yml`. Keep its existing checks and file permissions.

Check: syntax, lint, and if possible an Incus build, then `incus exec <instance> -- hostname`, `hostname -f` and `uptime` (uptime must show the node rebooted), then a second build with changed=1 for the node (the reboot) and nothing else.

## Phase 2: platforms as directories

1. Add `group_vars/all/platforms.yml` holding `node_required_fields` and a `platforms` mapping, where each platform lists its extra required fields: incus none, ssh `node_address`. Data only. Move the required-field check to read it, and add: `platform` must be a key of `platforms`.
2. Add `group_vars/all/ownership.yml`: `uc_raw_node_owner: uc-raw-node`, `uc_raw_node_owner_key: user.uc-raw-node.owner`, `uc_raw_node_owner_file: /etc/uc-raw-node/owner`. Use them instead of the literals in the Incus play.
3. Move the Incus create play to `platforms/incus/create.yml`.
4. `build.yml` imports every platform's plays, unconditionally, and every play inside carries `when: platform == '<name>'`. Do not use a templated import_playbook path: it is resolved before group_vars are loaded, so the `platform` default in node.yml would not apply.
5. `scripts/new-node`: ask for the platform, offering the keys of platforms.yml, default incus, and for ssh also the node address, checked with ipaddress.ip_address.

Check: the Incus build behaves exactly as at the end of phase 1.

## Phase 3: the ssh platform

Follow en/docs/guides/add-a-new-platform.md, adapted from `vps` to `ssh`, and the findings above.

1. `group_vars/all/ssh.yml` with: `ssh_first_contact_user: root`, `ssh_first_contact_port: 22`, `uc_raw_node_adopt: false`, the list of sshd options the contract controls (PasswordAuthentication, PermitRootLogin, Port), and the cloud-init settings (preserve_hostname: true, manage_etc_hosts: false).
2. `platforms/ssh/create.yml`, on localhost then on the node:
   - try the contract connection (initial user, ssh_port, BatchMode, IdentitiesOnly, short timeout); if it works use it, otherwise use first contact
   - add the node under `node_fqdn` with ansible_host `node_address` and the chosen user and port, and `-o IdentitiesOnly=yes` in ansible_ssh_common_args
   - wait_for_connection, then `systemctl is-system-running --wait`
   - read the ownership marker file; if it is missing and uc_raw_node_adopt is not true, stop before any change with a message that says to adopt only the host that was ordered; if adopting, write it
   - never retry a failed root login in a loop: OpenSSH 10's PerSourcePenalties locks the controller out
3. `platforms/ssh/prepare.yml`, after bootstrap and before configure:
   - remove files in /etc/ssh/sshd_config.d/ that set an option the contract controls
   - empty /root/.ssh/authorized_keys
   - only if cloud-init is installed, write /etc/cloud/cloud.cfg.d/99-uc-raw-node.cfg from the settings
4. After the configure play, a play for the ssh platform that sets ansible_user to the initial user and ansible_port to ssh_port, then meta: reset_connection, so the reboot runs over the contract connection with become. Document that builds need --ask-become-pass once the contract holds.
5. Port change on first contact: Foomuuri is applied before OpenSSH, so if ssh_port is not 22, new connections to 22 are dropped before sshd moves. Read the steelcj.foomuuri role (installed under ~/.ansible/roles/) and tell me whether it can allow more than one SSH port. Propose the smallest safe approach. Do not change the role itself; it lives in its own repository.
6. AuthorizedKeysCommand: find where robertdebock.openssh sets it, and set it explicitly in group_vars/all/openssh.yml so sshd stops logging that its path is not absolute.

Check: syntax and lint with an ssh node definition in /tmp, and the Incus build still unchanged. Do not connect to any remote host: I will test the ssh platform by hand.

## Phase 4: documents

1. README: title it uc-node, the raw node controller; describe the platforms, the rule that node definitions override group_vars, the naming table for the four labels, node definition file names by FQDN, and fix links to en/docs/guides/.
2. Keep one platform guide, en/docs/guides/add-a-new-platform.md, and delete add-a-new-platform-to-the-node-creation-controller.md (they differ only in title). Bring it in line with what was built: `ssh` instead of `vps`, platforms.yml, the when conditions, the reboot module, IdentitiesOnly, root keys, and PerSourcePenalties. Bump its version in its front matter and changelog table and mark it provisional.
3. Add en/docs/guides/3-build-a-node-on-an-ssh-host.md: preparing the host, the host key check, the first build with uc_raw_node_adopt, the checks, later builds, and what to do when locked out. Use the findings and setup-ex2-vps-node.md, with example addresses only, then delete setup-ex2-vps-node.md.
4. Update 1- and 2- guides for client_domain, node_label and the new file names.
5. Secrets guide: replace the list of specific file paths near the end with a general description, so it names no file from the old repository; bump its version.
6. ROADMAP: remove what is done, add what remains, including tagging steelcj.foomuuri, any port-change work from phase 3, and updating or retiring the old design documents.
7. CHANGELOG: rewrite it for this repository. Use the template's header (Keep a Changelog, Semantic Versioning, entries under Unreleased). Keep the 0.0.1, 0.0.2 and 0.1.0 sections in plain words: 0.0.1 created the repository from the uc-repo template, 0.0.2 added the controller's files, 0.1.0 added the build, configuration and guides from the earlier repository, which was retired. Remove the pasted git status lists and every section from the old repository. Add an Unreleased entry describing this work.

Finish with a summary of every file changed, the checks you ran and their results, and anything you could not do or decided against.
````
