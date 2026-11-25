---
title: Foomuuri and cloud-init Ordering Cycle
description: On Debian 13, Foomuuri and cloud-init 25 form a systemd ordering cycle, so systemd skips a unit at boot and the node may never finish booting. What it looks like, how to confirm it, and what uc-node does about it.
version: 0.1.0
status: provisional
date: 2026-11-24
language: en-CA
---

# Foomuuri and cloud-init Ordering Cycle

## Symptom

A Debian 13 host that runs cloud-init, with Foomuuri installed, never finishes booting after its next reboot:

- `systemctl is-system-running` says `starting`, and `systemctl is-system-running --wait` never returns
- `systemctl list-jobs` shows `cloud-config.service` running, and `cloud-final.service` and `cloud-init.target` waiting
- network and SSH still come up, from the configuration cloud-init wrote at the first boot

Before uc-node had a boot timeout, a build of such a node hung in its boot wait.

## Cause

cloud-init 25 orders its network stage before `sysinit.target`, and Foomuuri's units keep systemd's default dependencies, so they are ordered after it. Together they form a cycle:

```text
cloud-init-network.service
  after systemd-networkd-wait-online.service
  after systemd-networkd.service
  after network-pre.target
  after foomuuri.service
  after foomuuri-boot.service
  after sysinit.target
  after cloud-init-network.service, which is ordered before sysinit.target
```

systemd breaks the cycle at boot by deleting one job. On the Debian 13 cloud image it deleted `cloud-init-network.service`, so cloud-init's single process waited for its network stage forever. systemd may choose either side of a cycle, so another boot could delete a Foomuuri job instead, and leave the node without its firewall.

It was reproduced on the Debian 13 cloud image, in an Incus container and in an Incus VM, with nothing installed but Foomuuri: cloud-init 25.1.4 and Foomuuri 0.27.

## How to confirm it

On the node, as root, since the initial user cannot read systemd's messages:

```sh
sudo journalctl -b SYSLOG_IDENTIFIER=systemd | grep -i "ordering cycle"
```

A cycle shows as lines such as:

```text
sysinit.target: Found ordering cycle on cloud-init-network.service/start
sysinit.target: Job cloud-init-network.service/start deleted to break ordering cycle starting with sysinit.target/start
```

The filter on `SYSLOG_IDENTIFIER=systemd` matters: Ansible logs each task's command line to the journal, and uc-node's own check holds the search text, so an unfiltered search finds it. systemd's early boot messages reach the journal from the kernel log, so a filter on `_PID=1` misses them.

In an Incus container, systemd's early boot messages never reach the journal, since a container has no kernel log. Read them from the controller with `incus console --show-log <instance>`, which empties the log it shows.

## What uc-node does

- On the ssh platform, when cloud-init is installed, `platforms/ssh/prepare.yml` creates `/etc/cloud/cloud-init.disabled` before the build's first reboot, so cloud-init does not run again and the cycle never forms. It also writes `/etc/cloud/cloud.cfg.d/99-uc-raw-node.cfg` with `preserve_hostname: true` and `manage_etc_hosts: false`, in case cloud-init is turned back on. Changes the provider makes to the network later are not picked up.
- On every platform, the boot wait stops after `boot_timeout` seconds, 300 by default, and shows `systemctl list-jobs` and any ordering cycle lines, instead of hanging.
- After the reboot, the build fails if `journalctl -b`, filtered on `SYSLOG_IDENTIFIER=systemd`, holds an ordering cycle, and on Incus also if the console log does.

A node that is already stuck in `starting` needs cloud-init disabled by hand and a reboot, as [Build a Node on an SSH Host](../guides/3-build-a-node-on-an-ssh-host.md#the-node-never-finished-booting) shows.

## Upstream

The cycle is recorded for the role in [Foomuuri and cloud-init ordering cycle](https://github.com/steelcj/ansible-role-foomuuri/blob/main/en/docs/known-issues/cloud-init-ordering-cycle.md), in steelcj.foomuuri. Raising it with Foomuuri upstream is in the [ROADMAP](../../../ROADMAP.md#raise-the-cloud-init-and-foomuuri-ordering-cycle-upstream).

## Changelog

| Version | Date | Change |
| :-- | :-- | :-- |
| 0.1.0 | 2026-11-24 | First version |
