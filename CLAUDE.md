# CLAUDE.md

Notes for Claude Code working in uc-node, the raw node controller.

## Known issues

### Foomuuri and cloud-init ordering cycle

On Debian 13, cloud-init 25 and Foomuuri form a systemd ordering cycle, and systemd skips a unit at boot to break it: cloud-init's network stage, which leaves the node in `starting` forever, or possibly the firewall. The ssh platform disables cloud-init before the first reboot, every boot wait has a timeout, and the build fails if the boot after the reboot holds an ordering cycle. Confirm it with `sudo journalctl -b SYSLOG_IDENTIFIER=systemd | grep -i "ordering cycle"`. In an Incus container the cycle reaches only `incus console --show-log`, not the journal. See [Foomuuri and cloud-init Ordering Cycle](en/docs/known-issues/foomuuri-cloud-init-ordering-cycle.md).

### PerSourcePenalties lockouts

OpenSSH 10 blocks an address that keeps failing to log in, for up to ten minutes by default, even with the right key afterwards. Never retry a failed SSH login in a loop, never use `wait_for_connection` against a host that may refuse the login, and never let the agent offer every key. To recover, stop trying and wait, or use another address or the provider's console. See [OpenSSH PerSourcePenalties Lockouts](en/docs/known-issues/openssh-per-source-penalties-lockout.md).

### Keys not offered because of IdentitiesOnly

Every connection to an ssh node uses `IdentitiesOnly=yes`, so ssh offers only the default key files and the keys `~/.ssh/config` names for the node's address. A key kept elsewhere is not offered, and both logins fail with `Permission denied (publickey)` although `ssh -i` works. The fix is an entry in `~/.ssh/config` whose `Host` line is the address, not an alias with `HostName`, placed before any `Host *` block. `scripts/new-node` prints it, and so does the build when both logins are refused. Do not add an identity file field to node definitions for this. See [OpenSSH PerSourcePenalties Lockouts](en/docs/known-issues/openssh-per-source-penalties-lockout.md#how-uc-node-avoids-it) and [Add the node to ~/.ssh/config](en/docs/guides/3-build-a-node-on-an-ssh-host.md#add-the-node-to-sshconfig).
