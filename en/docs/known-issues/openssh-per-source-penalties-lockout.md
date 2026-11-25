---
title: OpenSSH PerSourcePenalties Lockouts
description: OpenSSH 10 blocks an address that keeps failing to log in, which can lock the controller out of a node. How it happens, how to recognize it, how to recover, and how uc-node avoids it.
version: 0.1.0
status: provisional
date: 2026-11-24
language: en-CA
---

# OpenSSH PerSourcePenalties Lockouts

## Symptom

After a few failed logins, every connection from the controller's address to the node is closed before login, even with the right key. The client typically says:

```text
kex_exchange_identification: Connection closed by remote host
```

or `Connection reset by peer`. Other addresses can still log in.

## Cause

OpenSSH 9.8 added `PerSourcePenalties`, on by default, and Debian 13 ships OpenSSH 10. sshd adds a penalty to an address for each failed authentication, each connection that does not authenticate, and each crash it causes, and refuses connections from that address while its penalty lasts. By default a failed login adds a few seconds, and penalties add up to at most ten minutes. The values on a node are in:

```sh
sudo sshd -T | grep -i persourcepenalt
```

Two things made it lock a controller out:

- the reconnect loop of `robertdebock.reboot`'s `wait_for_connection`, which kept trying to log in as root after root login had been turned off
- the SSH agent offering every key it holds, each a failed attempt

## How to recover

- Stop trying. Every new attempt adds to the penalty.
- Wait. The penalty ends on its own, after at most ten minutes with the default settings.
- Find the cause before trying again, then try once with a plain `ssh`, as the troubleshooting section of [Build a Node on an SSH Host](../guides/3-build-a-node-on-an-ssh-host.md#troubleshooting-by-error-message) shows.
- If you cannot wait, log in from another address, or as root through the provider's web console.

To confirm it on the node, look for sshd's penalty lines:

```sh
sudo journalctl -u ssh -b | grep -i penalty
```

## How uc-node avoids it

- Each login is tried once, and a failed one is never retried. The create play on the ssh platform probes the contract connection once, then root on port 22 once, with plain `ssh` commands rather than `wait_for_connection`, and stops if neither works.
- Every connection uses `IdentitiesOnly=yes`, so ssh offers only the default key files and the keys `~/.ssh/config` names for the node's address, never every key in the agent. A key kept elsewhere needs an entry in `~/.ssh/config`, which `scripts/new-node` prints, and the build prints when both logins are refused.
- The reboot uses `ansible.builtin.reboot`, over the contract connection, as the initial user.

A first build costs one failed login, the contract probe for an initial user that does not exist yet, which stays well within the penalty's threshold.

## Changelog

| Version | Date | Change |
| :-- | :-- | :-- |
| 0.1.0 | 2026-11-24 | First version |
