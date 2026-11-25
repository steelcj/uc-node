---
title: AuthorizedKeysCommand none in robertdebock.openssh
description: robertdebock.openssh writes AuthorizedKeysCommand none, which sshd 10 tries to run. What it logs, why, and the workaround uc-node uses.
version: 0.1.0
status: provisional
date: 2026-11-24
language: en-CA
---

# AuthorizedKeysCommand none in robertdebock.openssh

## Symptom

sshd logs this whenever a login offers a key that is not in the user's `authorized_keys`:

```text
error: AuthorizedKeysCommand path is not absolute
```

Logins with the right key work, so the error shows only in the log.

## Cause

`robertdebock.openssh` 5.1.0 writes every setting of its template, including:

```text
AuthorizedKeysCommand {{ openssh_authorized_keys_command }}
AuthorizedKeysCommandUser {{ openssh_authorized_keys_command_user }}
```

with the defaults `none` and `nobody`. sshd 10 does not read `none` as unset for `AuthorizedKeysCommand`. When no key in `authorized_keys` matches, it tries to run the command `none`, which is not an absolute path, and logs the error. `sshd -T` shows `authorizedkeyscommand none` either way, so it does not tell the two apart.

It was reproduced on an Incus node: a login with a key not in `authorized_keys` logged the error.

## What uc-node does

`inventory/group_vars/all/openssh.yml` sets:

```yaml
openssh_authorized_keys_command: /usr/bin/true
```

`/usr/bin/true` is an absolute path that prints no keys, so only `authorized_keys` is used. sshd runs it as `AuthorizedKeysCommandUser`, `nobody`, which is safe. With it, the same login logs only `Connection closed by authenticating user`, and a login with the right key logs nothing about the command.

This was confirmed on a VPS built by uc-node: `sshd -T` showed `authorizedkeyscommand /usr/bin/true` and `authorizedkeyscommanduser nobody`.

## Upstream

Asking the role to leave the line out when the value is `none` is in the [ROADMAP](../../../ROADMAP.md#raise-authorizedkeyscommand-none-with-robertdebockopenssh).

## Changelog

| Version | Date | Change |
| :-- | :-- | :-- |
| 0.1.0 | 2026-11-24 | First version |
