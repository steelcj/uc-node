---
title: Platforms for uc-node, Phase Four Prompt
description: The prompt that started phase four of the platforms work, with the decisions taken after the VPS adoption test.
version: 0.1.0
status: provisional
date: 2026-11-24
language: en-CA
---

# Platforms for uc-node, Phase Four Prompt

Sent to Claude Code with `vps-adoption-test.md` attached, after the VPS adoption test at the end of phase three.

## Prompt

```bash
Go ahead with phase 4, in this order:

1. Commit en/docs/sessions/README.md (now 0.1.4, with the blank line in the front matter already removed) together with the .gitignore change.

2. Make a separate fix commit: the check play refuses any node_address that isn't an IPv4 or IPv6 address, using the same regular expression as scripts/new-node.

3. Check git log. If it isn't already done: the check play refuses a node definition that sets ansible_host, ansible_user, ansible_port, ansible_ssh_common_args or ansible_ssh_host_key_checking, with a message saying the platform's create play sets them. Allow ansible_become_password. Run the Incus build twice and the ssh syntax check, and commit.

4. Phase 4:
   - Prerequisites include checking the OS with cat /etc/os-release, since Debian 13 is the only tested target, and whether the provider runs cloud-init.
   SSH keys
   - Don't add an ssh_identity_file field. scripts/new-node prints this block for ~/.ssh/config, with the node's values filled in:

     # uc-node: <node-name>
     Host <ip-address>
         IdentityFile <private-key-path>
         IdentitiesOnly yes
         # Optional, only for manual ssh/scp; the build passes the user itself
         User <initial-user>

     The Host line must be the IP address, because Ansible connects to node_address. A test showed that an alias with HostName did not match. When the probe fails with permission denied, the check play prints the same block.

   The ssh guide, 3-build-a-node-on-an-ssh-host.md
   - Use the attached vps-adoption-test.md as source material. Don't commit it as its own document.
   - Cover both paths, adopting an existing node and a fresh install: the adoption build, the host key check, and rebuilding a node made by the old version, including updating an old-style node definition.
   - Cover the config block and where to put it (before any Host * block), and that a new IP means a new config entry and a new known_hosts entry. Also cover HostKeyAlias and manual ssh to a port other than 22, testing with a plain ssh before rerunning a failed build, what to do when locked out by PerSourcePenalties, and everything under "For phase four" in the phase three report.
   - The checks use ssh -t, with logging in as the fallback, and sudo journalctl -b filtered on SYSLOG_IDENTIFIER=systemd. Leave the AuthorizedKeysCommand check out.
   - Turn the errors in the attached notes into a troubleshooting section, organized by error message.
   - Follow the sessions README's rule on private information here too: use 203.0.113.10 and example.org, not the real address, domain or key file names in the attached notes.

   Known issues
   - Add en/docs/known-issues/foomuuri-cloud-init-ordering-cycle.md: a short note on the symptom, how to confirm it (sudo, filtered on SYSLOG_IDENTIFIER=systemd), and what uc-node does about it (cloud-init disabled before the first reboot, the boot timeout, the cycle check). Link it to https://github.com/steelcj/ansible-role-foomuuri/blob/main/en/docs/known-issues/cloud-init-ordering-cycle.md, and link it from the ssh guide and the ROADMAP.
   - Add one document each to en/docs/known-issues/ for robertdebock.reboot reporting changed without rebooting, PerSourcePenalties lockouts and how to recover, and AuthorizedKeysCommand none (the /usr/bin/true workaround, which the VPS test showed sshd runs as nobody).
   - Add a "Known issues" section to CLAUDE.md (create the file if there isn't one) with a few lines each on the ordering cycle, PerSourcePenalties lockouts and keys not offered because of IdentitiesOnly, each linking to its note.
   - [Keep / Remove] the ROADMAP item about raising none with robertdebock.openssh.

   Phase four report
   - Name it by en/docs/sessions/README.md: create it with
     touch "en/docs/sessions/$(date +%Y-%m-%d--%H-%M-%S)-uc-node-platforms-phase-four-report.md"
     and give it the front matter the README describes, starting at version 0.1.0 with status provisional.
   - Include a section on the VPS test from the attached notes, covering the adoption build, the second build (changed=1, only the reboot) and the node checks, with the private details removed as above.
   - Write it when you stop.
   

```


## Changelog

| Version | Date | Change |
| :-- | :-- | :-- |
| 0.1.0 | 2026-11-24 | First version, the prompt as it was sent |
