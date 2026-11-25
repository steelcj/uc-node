---
title: robertdebock.reboot Reports Changed Without Rebooting
description: robertdebock.reboot 3.4.1 can report a reboot that never happened. Why, how to confirm it, and what uc-node uses instead.
version: 0.1.0
status: provisional
date: 2026-11-24
language: en-CA
---

# robertdebock.reboot Reports Changed Without Rebooting

## Symptom

The build's reboot task reports `changed`, and the play goes on, but the node did not reboot. It was found on the first manual run against a VPS. Incus builds that used the role may never have rebooted either.

## Cause

`robertdebock.reboot` 3.4.1 starts the reboot as a shell command in the background, without waiting for it:

```yaml
- name: reboot | Reboot the machine
  ansible.builtin.shell:
    cmd: "(sleep {{ reboot_delay }} && {{ reboot_command }} &)"
  async: 1
  poll: 0
  failed_when:
    - false
```

The command sleeps for `reboot_delay` seconds before the shutdown. Its asynchronous job ends, and can be killed with its child processes, before the sleep is over, so the shutdown never runs. The task reports `changed` whatever happened, and `failed_when: false` hides any error. The role then pauses and waits for a connection, which succeeds at once if the host never went down. Nothing checks that the host rebooted.

## How to confirm it

On the node, list the boots:

```sh
sudo journalctl --list-boots
```

A build that rebooted the node adds a boot that starts at the reboot. The uptime also shows it:

```sh
uptime
```

## What uc-node does

uc-node uses `ansible.builtin.reboot`, and `robertdebock.reboot` is no longer in `requirements.yml`. The module reads the boot ID from `/proc/sys/kernel/random/boot_id` before the reboot, and fails if it has not changed within `reboot_timeout`, 600 seconds in `build.yml`. A reboot that did not happen is never reported as done.

The boot ID changes in an Incus container too, since lxcfs gives each container its own, so the same check works on both platforms.

## Changelog

| Version | Date | Change |
| :-- | :-- | :-- |
| 0.1.0 | 2026-11-24 | First version |
